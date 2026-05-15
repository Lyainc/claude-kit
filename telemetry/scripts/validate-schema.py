#!/usr/bin/env python3
"""Validate telemetry jsonl schema.

Phase 1 deliverable: detect required-field omissions, type errors, and
line-size approach to PIPE_BUF (which would force a lock strategy revisit).

Usage:
    validate-schema.py [--since=Nd] [--strict] [--self-test]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TELEMETRY_DIR = SCRIPT_DIR.parent
EVENTS_DIR = TELEMETRY_DIR / "events"

REQUIRED_FIELDS = {
    "ts": str,
    "session_id": str,
    "cwd": str,
    "plugin": str,
    "event": str,
    "name": str,
    "qualified_name": str,
    "trigger": str,
    "outcome": str,
    "tool_use_id": str,
    "meta": dict,
}

VALID_EVENTS = {
    "skill_invoke", "agent_spawn", "command_run",
    "session_start", "session_end", "stop",
}

# PIPE_BUF safety threshold. POSIX guarantees atomic O_APPEND for writes <=
# PIPE_BUF (4096 on macOS/Linux). We warn at 3500B to leave headroom; if we
# ever exceed, the lockless append strategy needs to be revisited.
PIPE_BUF_WARN_BYTES = 3500


def find_event_files(since_days: int | None) -> list[Path]:
    if not EVENTS_DIR.is_dir():
        return []
    files = sorted(EVENTS_DIR.glob("events-*.jsonl"))
    if since_days is None:
        return files
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date()
    return [p for p in files if _date_from_filename(p) >= cutoff]


def _date_from_filename(p: Path):
    stem = p.stem  # events-YYYY-MM-DD
    try:
        return datetime.strptime(stem[len("events-"):], "%Y-%m-%d").date()
    except ValueError:
        return datetime.min.date()


def validate_line(raw: str, lineno: int, path: Path) -> list[str]:
    errors: list[str] = []
    line_bytes = len(raw.encode("utf-8"))
    if line_bytes > PIPE_BUF_WARN_BYTES:
        errors.append(
            f"{path.name}:{lineno} line size {line_bytes}B approaches PIPE_BUF "
            f"({PIPE_BUF_WARN_BYTES}B warn threshold) — revisit lock strategy"
        )

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"{path.name}:{lineno} JSON parse error: {e.msg}")
        return errors

    if not isinstance(obj, dict):
        errors.append(f"{path.name}:{lineno} not a JSON object")
        return errors

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in obj:
            errors.append(f"{path.name}:{lineno} missing required field '{field}'")
            continue
        if not isinstance(obj[field], expected_type):
            errors.append(
                f"{path.name}:{lineno} field '{field}' has wrong type "
                f"(expected {expected_type.__name__}, got {type(obj[field]).__name__})"
            )

    if "event" in obj and obj["event"] not in VALID_EVENTS:
        errors.append(
            f"{path.name}:{lineno} event '{obj['event']}' not in {sorted(VALID_EVENTS)}"
        )

    return errors


def run_self_test() -> int:
    # Synthesize one valid + one invalid line and run validator inline.
    good = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "claude-kit",
        "event": "stop", "name": "", "qualified_name": "",
        "trigger": "auto", "outcome": "success",
        "tool_use_id": "", "meta": {},
    })
    bad = '{"ts":"x","event":"not-an-event"}'

    good_errs = validate_line(good, 1, Path("self-test.jsonl"))
    bad_errs = validate_line(bad, 1, Path("self-test.jsonl"))

    if good_errs:
        print(f"FAIL: good line flagged: {good_errs}", file=sys.stderr)
        return 1
    if not bad_errs:
        print("FAIL: bad line not flagged", file=sys.stderr)
        return 1
    print(f"OK: self-test passed ({len(bad_errs)} expected errors on bad line)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", help="time window: '7d', '30d', etc.", default=None)
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero on any violation")
    p.add_argument("--self-test", action="store_true",
                   help="run inline schema validator on synthetic input and exit")
    args = p.parse_args()

    if args.self_test:
        return run_self_test()

    since_days: int | None = None
    if args.since:
        if not args.since.endswith("d"):
            print("--since must be in form 'Nd' (days)", file=sys.stderr)
            return 2
        try:
            since_days = int(args.since[:-1])
        except ValueError:
            print(f"invalid --since: {args.since}", file=sys.stderr)
            return 2

    files = find_event_files(since_days)
    if not files:
        print(f"No event files in {EVENTS_DIR} (since_days={since_days})")
        return 0

    total_lines = 0
    all_errors: list[str] = []
    for path in files:
        with path.open(encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                raw = raw.rstrip("\n")
                if not raw.strip():
                    continue
                total_lines += 1
                all_errors.extend(validate_line(raw, lineno, path))

    print(f"Scanned {total_lines} lines across {len(files)} files")
    if all_errors:
        print(f"Violations: {len(all_errors)}")
        for err in all_errors[:50]:
            print(f"  {err}")
        if len(all_errors) > 50:
            print(f"  ... and {len(all_errors) - 50} more")
        return 1 if args.strict else 0
    print("All schema checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
