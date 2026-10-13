#!/usr/bin/env python3
"""Run the Godot 4.7.2 regression suite without trusting its exit code alone."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ENGINE_VERSION = "4.7.2"
PROJECT = Path(__file__).resolve().parents[1]
ENGINE_ERROR = re.compile(r"^\s*(?:SCRIPT ERROR|ERROR):", re.MULTILINE)
ANSI = re.compile(r"\x1b\[[0-9;]*m")
SUITE = (
    ("smoke", "res://tests/smoke.tscn", "SMOKE PASS:"),
    ("hunter rules", "res://tests/hunter_rules.tscn", "HUNTER RULES PASS:"),
    ("audit regressions", "res://tests/audit_regressions.tscn", "AUDIT REGRESSIONS PASS:"),
    ("research progression", "res://tests/progression_contract.tscn", "PROGRESSION CONTRACT PASS:"),
    ("skill dispatch", "res://tests/skills_contract.tscn", "SKILLS CONTRACT PASS:"),
    ("report world flow", "res://tests/progression_world.tscn", "PROGRESSION WORLD PASS:"),
    ("spectrum gameplay", "res://tests/spectrum_gameplay_contract.tscn", "SPECTRUM GAMEPLAY PASS:"),
    ("native UI", "res://tests/ui_contract.tscn", "UI CONTRACT PASS:"),
    ("runtime asset readiness", "res://tests/asset_readiness_contract.tscn", "ASSET READINESS PASS:"),
    ("static asset integration", "res://tests/static_assets_contract.tscn", "STATIC ASSETS PASS:"),
    ("environment geometry", "res://tests/environment_quality_contract.tscn", "ENVIRONMENT QUALITY PASS:"),
    ("equipment vehicle geometry", "res://tests/high_fidelity_assets_contract.tscn", "HIGH FIDELITY GEOMETRY/API GUARDS PASS:"),
    ("hand anatomy and grip motion", "res://tests/hand_anatomy_contract.tscn", "HAND ANATOMY PASS:"),
    ("naifrog skin animation", "res://tests/naifrog_model_contract.tscn", "NAIFROG_MODEL_CONTRACT"),
)


@dataclass
class Result:
    returncode: int | None
    output: str
    elapsed: float
    timed_out: bool = False


def run(command: list[str], timeout: float) -> Result:
    started = time.monotonic()
    try:
        # Every process gets a disposable archive, including older game scenes.
        # A test must never add knowledge to the user's real saved research.
        with tempfile.TemporaryDirectory(prefix="rainfield-test-archive-") as directory:
            environment = os.environ.copy()
            environment["HDF_ARCHIVE_PATH"] = str(Path(directory) / "archive.json")
            process = subprocess.run(
                command, cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False,
                env=environment,
            )
        return Result(process.returncode, ANSI.sub("", process.stdout), time.monotonic() - started)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return Result(None, ANSI.sub("", output), time.monotonic() - started, True)


def failure_reason(result: Result, marker: str | None = None) -> str | None:
    if result.timed_out:
        return "timeout"
    if result.returncode != 0:
        return f"process exited {result.returncode}"
    if ENGINE_ERROR.search(result.output):
        return "Godot reported an engine or script error"
    if marker and marker not in result.output:
        return f"missing success marker {marker!r}"
    return None


def check(name: str, command: list[str], timeout: float, marker: str | None = None) -> bool:
    result = run(command, timeout)
    reason = failure_reason(result, marker)
    if reason:
        print(f"FAIL {name}: {reason} ({result.elapsed:.2f}s)", file=sys.stderr)
        print(result.output.rstrip(), file=sys.stderr)
        return False
    print(f"PASS {name} ({result.elapsed:.2f}s)")
    return True


def check_error_gate(godot: str, timeout: float) -> bool:
    # A PASS marker before the failing assertion deliberately defeats marker-only checks.
    # Godot's --quit-after exits normally despite the SCRIPT ERROR in this fixture.
    marker = "INTENTIONAL FAILURE FIXTURE PASS: marker alone is insufficient"
    with tempfile.TemporaryDirectory(prefix="rainfield-test-gate-") as directory:
        fixture = Path(directory) / "intentional_failure.gd"
        fixture.write_text(
            'extends SceneTree\nfunc _initialize() -> void:\n'
            f'\tprint("{marker}")\n'
            '\tassert(false, "intentional assertion for runner self-test")\n',
            encoding="utf-8",
        )
        result = run(
            [godot, "--headless", "--path", str(PROJECT), "--script", str(fixture), "--quit-after", "2"],
            timeout,
        )
    caught = (
        result.returncode == 0 and not result.timed_out and marker in result.output
        and "SCRIPT ERROR:" in result.output and failure_reason(result, marker) is not None
    )
    # Exercise the other gates independently; each must reject a superficially normal result.
    caught = caught and all((
        failure_reason(Result(0, "", 0.0), marker) is not None,
        failure_reason(Result(1, marker, 0.0), marker) is not None,
        failure_reason(Result(None, marker, 0.0, True), marker) is not None,
        failure_reason(Result(0, "ERROR: fixture engine failure\n" + marker, 0.0), marker) is not None,
    ))
    if not caught:
        print("FAIL runner self-test: intentional zero-exit assertion was not rejected", file=sys.stderr)
        print(result.output.rstrip(), file=sys.stderr)
        return False
    print(f"PASS runner self-test: rejected SCRIPT ERROR with exit 0 and a PASS marker ({result.elapsed:.2f}s)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default="godot", help="Godot 4.7.2 executable (default: godot)")
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds allowed per check (default: 120)")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        version = run([args.godot, "--version"], min(args.timeout, 15.0))
        if failure_reason(version) or not re.search(r"^4\.7\.2(?:\.|\s|$)", version.output.strip()):
            print(f"FAIL version: require Godot {ENGINE_VERSION}, received {version.output.strip()!r}", file=sys.stderr)
            return 1
        print(f"Godot {version.output.strip()}")
        base = [args.godot, "--headless", "--path", str(PROJECT)]
        if not check("import", base + ["--editor", "--import"], args.timeout):
            return 1
        success = check_error_gate(args.godot, args.timeout)
        for name, scene, marker in SUITE:
            success = check(name, base + [scene], args.timeout, marker) and success
        # These two separate Godot processes must share the same isolated file.
        with tempfile.TemporaryDirectory(prefix="rainfield-test-restart-") as directory:
            archive = str(Path(directory) / "restart-archive.json")
            scene = "res://tests/progression_contract.tscn"
            for phase in ("write", "read"):
                success = check(
                    f"archive process restart {phase}",
                    base + [scene, "--", f"--restart-{phase}", archive],
                    args.timeout, f"RESTART CONTRACT PASS --restart-{phase}:",
                ) and success
        if success:
            print(f"ALL TESTS PASS: import, failure gate, {len(SUITE)} scene contracts, two archive restart processes")
        return 0 if success else 1
    except OSError as error:
        print(f"FAIL invoking Godot: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
