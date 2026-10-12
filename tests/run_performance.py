#!/usr/bin/env python3
"""Serial, graphical Godot workload; stdlib only. Keep other GPU apps idle."""
import argparse
import csv
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import time
from pathlib import Path

ERROR = re.compile(r"(?:SCRIPT ERROR:|\bERROR:|Parse Error:)")


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def summarize(csv_path):
    with csv_path.open() as source:
        rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(source)]
    fields = ("frame_interval_ms", "time_process_ms", "physics_process_ms", "draw_calls", "static_memory_bytes", "video_memory_bytes")
    result = {"frame_samples": len(rows), "sampled_seconds": rows[-1]["elapsed_s"] if rows else 0}
    for field in fields:
        values = [row[field] for row in rows]
        result[field] = {"p50": percentile(values, 50), "p95": percentile(values, 95), "p99": percentile(values, 99), "max": max(values) if values else None, "mean": statistics.fmean(values) if values else None}
    for active in (0, 1):
        values = [row["frame_interval_ms"] for row in rows if row["lightning_active"] == active]
        result["lightning_on" if active else "lightning_off"] = {"frame_samples": len(values), "p95_frame_interval_ms": percentile(values, 95), "p99_frame_interval_ms": percentile(values, 99)}
    return result


def rss_bytes(pid):
    try:
        value = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)], text=True, stderr=subprocess.DEVNULL).strip()
        return int(value) * 1024 if value else None
    except (subprocess.CalledProcessError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", required=True)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", default="current")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--duration", type=float, default=60)
    parser.add_argument("--warmup", type=float, default=5)
    parser.add_argument("--restarts", type=int, default=10)
    args = parser.parse_args()
    if args.runs < 1 or args.duration <= 0 or args.warmup < 0 or args.restarts < 0:
        parser.error("runs/duration must be positive and warmup/restarts nonnegative")
    project, destination = args.project.resolve(), args.output.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output([args.godot,"--version"], text=True).strip()
    if not version.startswith("4.7.2."):
        parser.error("This benchmark requires Godot 4.7.2; found " + version)
    source = Path(__file__).resolve().parent
    target = project / "tests"
    target.mkdir(exist_ok=True)
    for filename in ("performance_benchmark.gd","performance_benchmark.gd.uid","performance_benchmark.tscn"):
        if (source / filename).exists() and (source / filename).resolve() != (target / filename).resolve():
            shutil.copy2(source / filename,target / filename)
    imported = subprocess.run([args.godot,"--headless","--editor","--path",str(project),"--import"],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (destination / "import.log").write_text(imported.stdout)
    if imported.returncode or ERROR.search(imported.stdout):
        raise SystemExit("Benchmark import failed; see import.log")
    report = {"label":args.label,"host":platform.platform(),"engine":version,"project":str(project),"configuration":{"runs":args.runs,"duration_seconds":args.duration,"warmup_seconds":args.warmup,"restarts":args.restarts,"window":[640,360],"vsync":"disabled","frame_cap":"disabled"},"runs":[]}
    for index in range(1,args.runs + 1):
        csv_path = destination / f"{args.label}-{index}.csv"
        env = dict(os.environ, MIDNIGHT_BENCH_OUTPUT=str(csv_path), MIDNIGHT_BENCH_SECONDS=str(args.duration), MIDNIGHT_BENCH_WARMUP=str(args.warmup), MIDNIGHT_BENCH_RESTARTS=str(args.restarts if index == 1 else 0))
        command = [args.godot,"--path",str(project),"--scene","res://tests/performance_benchmark.tscn","--resolution","640x360","--position","120,120","--rendering-method","forward_plus","--max-fps","0","--disable-vsync"]
        samples, started = [], time.monotonic()
        with (destination / f"{args.label}-{index}.log").open("w") as log:
            process = subprocess.Popen(command, env=env, text=True,stdout=log,stderr=subprocess.STDOUT)
            print(f"PERFORMANCE RUN {index}/{args.runs}: pid={process.pid}, {csv_path}", flush=True)
            try:
                while process.poll() is None:
                    value = rss_bytes(process.pid)
                    if value is not None:
                        samples.append({"elapsed_s":time.monotonic()-started,"rss_bytes":value})
                    if time.monotonic() - started > args.duration + args.warmup + 2.5*args.restarts + 120:
                        raise TimeoutError("benchmark timed out")
                    time.sleep(1)
            except BaseException:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise
        log_text = (destination / f"{args.label}-{index}.log").read_text()
        if process.returncode or ERROR.search(log_text) or "PERFORMANCE PASS:" not in log_text:
            raise SystemExit(f"Benchmark run {index} failed; see log")
        summary = summarize(csv_path)
        if summary["sampled_seconds"] < args.duration - 1:
            raise SystemExit(f"Incomplete sample duration in run {index}")
        metadata = json.loads(Path(str(csv_path)+".metadata.json").read_text())
        if metadata["renderer"] != "forward_plus" or metadata["window_size"] != [640,360]:
            raise SystemExit("Renderer or window configuration mismatch")
        summary.update({"index":index,"metadata":metadata,"rss_samples":samples,"restarts":json.loads(Path(str(csv_path)+".restarts.json").read_text())})
        report["runs"].append(summary)
        (destination / "summary.json").write_text(json.dumps(report,indent=2))
        print(f"PERFORMANCE COMPLETE {index}/{args.runs}: frame p95={summary['frame_interval_ms']['p95']:.2f} ms",flush=True)
    print("PERFORMANCE SERIES PASS",flush=True)


if __name__ == "__main__":
    main()
