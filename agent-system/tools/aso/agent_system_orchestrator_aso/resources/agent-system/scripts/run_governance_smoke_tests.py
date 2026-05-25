#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_SHELL_RUNNER = SCRIPT_DIR / "run_governance_smoke_tests.sh"
STATUS_VALUES = ("passed", "failed", "timeout", "skipped")


@dataclass
class FixtureResult:
    name: str
    status: str
    returncode: int | None
    duration_seconds: float
    duration_ms: int
    log_path: str
    started_at: str
    finished_at: str


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number") from exc
    if timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return timeout


def runner_command(runner: Path, *args: str) -> list[str]:
    if runner.suffix == ".py":
        return [sys.executable, str(runner), *args]
    return ["bash", str(runner), *args]


def output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def discover_fixtures(runner: Path) -> list[str]:
    result = subprocess.run(
        runner_command(runner, "--list-fixtures"),
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    fixtures = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not fixtures:
        raise RuntimeError("smoke runner did not return any fixtures")
    return fixtures


def stop_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait()


def run_fixture(
    runner: Path,
    fixture: str,
    timeout: float | None,
    log_dir: Path,
) -> FixtureResult:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{fixture}.log"
    started_at = utc_now()
    start = time.monotonic()
    command = runner_command(runner, "--run-fixture", fixture)
    status = "failed"
    returncode: int | None = None
    output = ""

    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
        returncode = process.returncode
        status = "passed" if returncode == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        output = output_text(exc.output)
        stop_process_group(process)
        returncode = process.returncode
        remaining, _ = process.communicate()
        output += output_text(remaining)

    finished_at = utc_now()
    duration = time.monotonic() - start
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"fixture: {fixture}\n")
        handle.write(f"status: {status}\n")
        handle.write(f"returncode: {returncode}\n")
        handle.write(f"started_at: {started_at}\n")
        handle.write(f"finished_at: {finished_at}\n")
        handle.write(f"duration_seconds: {duration:.3f}\n")
        handle.write(f"command: {' '.join(command)}\n")
        handle.write("\n")
        handle.write(output)

    return FixtureResult(
        name=fixture,
        status=status,
        returncode=returncode,
        duration_seconds=round(duration, 3),
        duration_ms=round(duration * 1000),
        log_path=str(log_path),
        started_at=started_at,
        finished_at=finished_at,
    )


def skipped_fixture(fixture: str, log_dir: Path) -> FixtureResult:
    now = utc_now()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{fixture}.log"
    log_path.write_text(
        "\n".join(
            [
                f"fixture: {fixture}",
                "status: skipped",
                "returncode: None",
                f"started_at: {now}",
                f"finished_at: {now}",
                "duration_seconds: 0.000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return FixtureResult(
        name=fixture,
        status="skipped",
        returncode=None,
        duration_seconds=0.0,
        duration_ms=0,
        log_path=str(log_path),
        started_at=now,
        finished_at=now,
    )


def write_summary(
    json_out: Path,
    runner: Path,
    timeout: float | None,
    started_at: str,
    start_monotonic: float,
    results: Sequence[FixtureResult],
) -> None:
    counts = {status: 0 for status in STATUS_VALUES}
    for result in results:
        counts[result.status] += 1
    status = "failed" if counts["failed"] or counts["timeout"] else "passed"
    summary = {
        "schema_version": 1,
        "status": status,
        "runner": str(runner),
        "timeout_per_fixture_seconds": timeout,
        "status_values": list(STATUS_VALUES),
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": round(time.monotonic() - start_monotonic, 3),
        "counts": counts,
        "fixtures": [asdict(result) for result in results],
    }
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run governance smoke fixtures with diagnostics.")
    parser.add_argument(
        "--timeout-per-fixture",
        type=positive_timeout,
        default=None,
        help="seconds before a fixture process group is terminated",
    )
    parser.add_argument("--json-out", type=Path, help="write a JSON run summary to this path")
    parser.add_argument("--log-dir", type=Path, help="directory for per-fixture logs")
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="fixture to run; may be repeated. Unselected known fixtures are marked skipped.",
    )
    parser.add_argument(
        "--runner",
        type=Path,
        default=DEFAULT_SHELL_RUNNER,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    runner = args.runner.resolve()
    started_at = utc_now()
    start_monotonic = time.monotonic()
    json_out = args.json_out
    log_dir = args.log_dir
    if log_dir is None:
        if json_out is not None:
            log_dir = json_out.with_suffix("").parent / f"{json_out.with_suffix('').name}_logs"
        else:
            log_dir = REPO_ROOT / "project-runtime" / "reports" / "smoke_logs"

    try:
        fixtures = discover_fixtures(runner)
    except RuntimeError as exc:
        print(f"FAIL: unable to discover smoke fixtures: {exc}", file=sys.stderr)
        return 2

    selected = set(args.fixture)
    unknown = sorted(selected.difference(fixtures))
    if unknown:
        print(f"FAIL: unknown smoke fixture(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    run_all = not selected
    results: list[FixtureResult] = []
    for fixture in fixtures:
        if not run_all and fixture not in selected:
            results.append(skipped_fixture(fixture, log_dir))
            continue
        print(f"RUN: {fixture}", flush=True)
        result = run_fixture(runner, fixture, args.timeout_per_fixture, log_dir)
        print(f"{result.status.upper()}: {fixture} ({result.duration_seconds:.3f}s) log={result.log_path}", flush=True)
        results.append(result)

    if json_out is not None:
        write_summary(json_out, runner, args.timeout_per_fixture, started_at, start_monotonic, results)
        print(f"JSON_SUMMARY: {json_out}")

    return 1 if any(result.status in {"failed", "timeout"} for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
