#!/usr/bin/env python3
"""Check/download current runtime assets, then explicitly import with Godot 4.7.2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
MANIFEST = "assets/refined/RUNTIME_ASSET_PATHS.json"
LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
ENGINE_ERROR = re.compile(r"^\s*(?:SCRIPT ERROR|ERROR):", re.MULTILINE)


def run(command: list[str], project: Path, timeout: float = 30) -> str:
    try:
        result = subprocess.run(command, cwd=project, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout, check=False)
    except FileNotFoundError as error:
        raise RuntimeError(f"Executable not found: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Command timed out: {command[0]} ({timeout:g}s)") from error
    output = ANSI.sub("", result.stdout.decode("utf-8", errors="replace"))
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{output.rstrip()}")
    return output


def resources(project: Path) -> list[tuple[str, str]]:
    data = json.loads((project / MANIFEST).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("resources"), list):
        raise ValueError(f"Unsupported runtime manifest: {MANIFEST}")
    entries = []
    seen = set()
    for entry in data["resources"]:
        uri, kind = entry.get("path", ""), entry.get("kind", "")
        relative = uri.removeprefix("res://")
        parts = PurePosixPath(relative)
        if (not uri.startswith("res://assets/") or ".." in parts.parts or "\\" in relative
                or "," in relative or kind not in {"glb", "texture", "json"}
                or relative in seen):
            raise ValueError(f"Invalid/duplicate runtime manifest entry: {entry!r}")
        if not (project / relative).resolve().is_relative_to(project.resolve()):
            raise ValueError(f"Runtime resource leaves project directory: {relative}")
        seen.add(relative)
        entries.append((relative, kind))
    if not entries:
        raise ValueError("Runtime resource manifest is empty")
    return entries


def git_checkout(project: Path) -> bool:
    if not shutil.which("git"):
        return False
    try:
        top = Path(run(["git", "rev-parse", "--show-toplevel"], project).strip()).resolve()
        return top == project.resolve()
    except RuntimeError:
        return False


def import_scan_resources(project: Path, required: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Include tracked image companions which the editor scans beside active models.

    The shared manifest remains the runtime dependency list. This derives import
    scope from those asset roots and the checkout's actual files, not a second list.
    """
    roots = {PurePosixPath(*PurePosixPath(relative).parts[:2]) for relative, _ in required}
    if git_checkout(project):
        candidates = run(["git", "ls-files", "-z"], project).split("\0")
    else:
        candidates = [path.relative_to(project).as_posix() for root in roots
                      for path in (project / root).rglob("*") if path.is_file()]
    entries = dict(required)
    for relative in candidates:
        path = PurePosixPath(relative)
        if not relative or path.suffix.lower() not in {".glb", ".png", ".jpg", ".jpeg"}:
            continue
        if not any(root in path.parents for root in roots):
            continue
        if any((project / parent / ".gdignore").is_file() for parent in path.parents):
            continue
        if ".." in path.parts or "," in relative or not (project / relative).resolve().is_relative_to(project.resolve()):
            raise ValueError(f"Invalid importer-scanned asset path: {relative!r}")
        entries.setdefault(relative, "glb" if path.suffix.lower() == ".glb" else "texture")
    return list(entries.items())


def lfs_identity(project: Path, relative: str) -> tuple[str, int] | None:
    # LFS files are tiny pointer blobs in Git, even when the working file is binary.
    if run(["git", "check-attr", "filter", "--", relative], project).strip().endswith(": lfs"):
        try:
            pointer = run(["git", "show", f"HEAD:{relative}"], project)
        except RuntimeError:
            return None  # A newly authored, uncommitted resource has no HEAD identity.
        digest = re.search(r"^oid sha256:([0-9a-f]{64})$", pointer, re.MULTILINE)
        size = re.search(r"^size ([0-9]+)$", pointer, re.MULTILINE)
        if pointer.startswith(LFS_HEADER.decode()) and digest and size:
            return digest.group(1), int(size.group(1))
    return None


def check_glb(path: Path, size: int) -> None:
    with path.open("rb") as source:
        header = source.read(12)
        if len(header) != 12:
            raise ValueError("truncated GLB header")
        magic, version, total = struct.unpack("<4sII", header)
        if magic != b"glTF" or version != 2 or total != size:
            raise ValueError(f"invalid GLB header/version/length (header={total}, actual={size})")
        first = True
        while source.tell() < total:
            chunk = source.read(8)
            if len(chunk) != 8:
                raise ValueError("truncated GLB chunk header")
            length, kind = struct.unpack("<I4s", chunk)
            if length % 4 or source.tell() + length > total:
                raise ValueError("GLB chunk exceeds file or lacks 4-byte alignment")
            if first:
                if kind != b"JSON" or length > 64 * 1024 * 1024:
                    raise ValueError("GLB first chunk must be a bounded JSON document")
                data = json.loads(source.read(length))
                if data.get("asset", {}).get("version") != "2.0":
                    raise ValueError("GLB asset version is not 2.0")
                for item in data.get("buffers", []) + data.get("images", []):
                    if "uri" in item and not item["uri"].startswith("data:"):
                        raise ValueError("external GLB dependency is outside the runtime manifest")
            else:
                source.seek(length, os.SEEK_CUR)
            first = False
        if first:
            raise ValueError("GLB has no JSON chunk")


def check_sources(project: Path, entries: list[tuple[str, str]]) -> tuple[list[str], dict[str, str]]:
    issues, source_md5 = [], {}
    has_git = git_checkout(project)
    for relative, kind in entries:
        path = project / relative
        try:
            with path.open("rb") as source:
                prefix = source.read(1024)
            if prefix.startswith(LFS_HEADER):
                issues.append(f"LFS POINTER: {relative} (model/texture binary has not been downloaded)")
                continue
            size = path.stat().st_size
            if kind == "glb":
                check_glb(path, size)
            elif kind == "json":
                json.loads(path.read_text(encoding="utf-8"))
            elif not ((prefix.startswith(b"\x89PNG\r\n\x1a\n") and len(prefix) >= 33)
                      or (prefix.startswith(b"\xff\xd8\xff") and size >= 4)):
                raise ValueError("texture is not a PNG/JPEG binary")
            sha, md5 = hashlib.sha256(), hashlib.md5()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    sha.update(block)
                    md5.update(block)
            source_md5[relative] = md5.hexdigest()
            expected = lfs_identity(project, relative) if has_git and kind != "json" else None
            if expected and (sha.hexdigest(), size) != expected:
                raise ValueError("binary SHA256/size differs from this checkout's committed LFS object")
        except FileNotFoundError:
            issues.append(f"MISSING SOURCE: {relative}")
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            issues.append(f"INVALID SOURCE: {relative}: {error}")
    return issues, source_md5


def check_imports(project: Path, entries: list[tuple[str, str]], source_md5: dict[str, str]) -> list[str]:
    issues = []
    for relative, kind in entries:
        if kind == "json":
            continue  # These are read directly with FileAccess, not imported resources.
        sidecar = project / (relative + ".import")
        try:
            text = sidecar.read_text(encoding="utf-8")
            paths = set(re.findall(r'"(res://\.godot/imported/[^"\r\n]+)"', text))
            if f'source_file="res://{relative}"' not in text or not paths:
                raise ValueError("missing/mismatched importer metadata")
            for uri in paths:
                cached = project / uri.removeprefix("res://")
                if not cached.resolve().is_relative_to((project / ".godot/imported").resolve()):
                    raise ValueError("imported path leaves the cache directory")
                if not cached.is_file() or cached.stat().st_size == 0:
                    raise ValueError("generated .godot/imported resource is missing")
                md5_text = cached.with_suffix(".md5").read_text(encoding="utf-8")
                found = re.search(r'^source_md5="([0-9a-f]{32})"', md5_text, re.MULTILINE)
                if not found or found.group(1) != source_md5.get(relative):
                    raise ValueError("generated import belongs to a different source file")
        except (OSError, ValueError) as error:
            issues.append(f"IMPORT REQUIRED: {relative}: {error}")
    return issues


def download(project: Path, entries: list[tuple[str, str]], timeout: float) -> None:
    if not git_checkout(project):
        raise RuntimeError("--download requires a complete Git checkout. A GitHub Source ZIP has no .git; clone the project as described in docs/GETTING_STARTED.md.")
    try:
        run(["git", "lfs", "version"], project)
    except RuntimeError as error:
        raise RuntimeError("Git LFS is unavailable. Install Git LFS for your OS, then retry; this helper does not install global software.\n" + str(error)) from error
    # Establish the local clean filter before asking Git whether binary files changed.
    run(["git", "lfs", "install", "--local"], project)
    paths = [relative for relative, kind in entries if kind != "json"]
    changed = run(["git", "status", "--porcelain", "--untracked-files=all", "--", *paths], project)
    if changed.strip():
        raise RuntimeError("Runtime asset files have local edits. Preserve/commit those edits before downloading; this helper will not overwrite them.\n" + changed.rstrip())
    print(f"Downloading {len(paths)} active runtime models/textures and importer-scanned companions; ignored historical models, Blender sources and previews are excluded.", flush=True)
    try:
        output = run(["git", "lfs", "pull", "--include=" + ",".join(paths), "--exclude="], project, timeout)
        if output.strip():
            print(output.rstrip())
    except RuntimeError as error:
        message = str(error)
        if re.search(r"quota|bandwidth|exceeded|billing|budget", message, re.IGNORECASE):
            message += "\nGit LFS server reported a quota/bandwidth/billing limit. The repository owner must resolve that server limit; git pull or Godot import cannot restore the missing binary."
        raise RuntimeError(message) from error


def import_project(project: Path, godot: str, timeout: float) -> None:
    if godot.endswith(".app"):
        godot = str(Path(godot) / "Contents/MacOS/Godot")
    version = run([godot, "--version"], project, 15).strip()
    if ENGINE_ERROR.search(version) or not re.match(r"^4\.7\.2(?:\.|\s|$)", version):
        raise RuntimeError(f"Require the validated Godot 4.7.2 editor; received {version!r}")
    help_text = run([godot, "--help"], project, 15)
    if not re.search(r"--import(?:\s|$)", help_text):
        raise RuntimeError("This executable does not advertise --import. Use the Godot editor, not an export template.")
    print(f"Importing with Godot {version}; wait for completion before opening the game.", flush=True)
    output = run([godot, "--headless", "--path", str(project), "--editor", "--import"], project, timeout)
    if ENGINE_ERROR.search(output):
        raise RuntimeError("Godot import reported ERROR/SCRIPT ERROR even though its exit code was zero:\n" + output.rstrip())
    if output.strip():
        print(output.rstrip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Read-only source/cache check; never downloads or imports")
    mode.add_argument("--download", action="store_true", help="Download only resources in the shared runtime manifest with Git LFS")
    parser.add_argument("--godot", metavar="PATH", help="Explicitly import using this Godot 4.7.2 editor executable (or macOS .app)")
    parser.add_argument("--timeout", type=float, default=600, help="Godot import / LFS download timeout in seconds (default: 600)")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.check and args.godot:
        parser.error("--check is read-only. Omit --check when using --godot to generate the import cache.")
    try:
        required = resources(PROJECT)
        entries = import_scan_resources(PROJECT, required)
        if args.download:
            download(PROJECT, entries, args.timeout)
        issues, hashes = check_sources(PROJECT, entries)
        if issues:
            print("\n".join(issues), file=sys.stderr)
            print("FAIL source assets. Use --download in a Git checkout, then rerun. See docs/GETTING_STARTED.md.", file=sys.stderr)
            return 1
        print(f"PASS source assets: {len(required)} required runtime resources plus {len(entries) - len(required)} importer-scanned companions are real, structurally valid files.")
        if args.godot:
            import_project(PROJECT, args.godot, args.timeout)
        pending = check_imports(PROJECT, entries, hashes)
        if pending:
            print("\n".join(pending), file=sys.stderr)
            print("SOURCE OK, IMPORT NOT READY. Open project.godot in the Godot 4.7.2 editor and wait for import, or run this helper with --godot PATH. No import was verified.", file=sys.stderr)
            return 2
        print("PASS import cache: current runtime resources have generated imports matching their source files.")
        print("Ready to open project.godot with Godot 4.7.2 and press F5. This check does not test GPU/rendering quality.")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"FAIL bootstrap: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
