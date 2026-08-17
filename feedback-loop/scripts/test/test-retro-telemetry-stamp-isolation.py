#!/usr/bin/env python3
"""Regression for retro-telemetry.sh's concurrent-session isolation (#529, #580).

History: two concurrent sessions with no CLAUDE_SESSION_ID used to collide on
the same /tmp/retro-start-*.ms file keyed by $PPID — one session's `emit`
deleted the stamp the other was still using (measured live 2026-08-03: two
sid-less emits, one duration_ms null). #580 found $PPID itself is not even
stable WITHIN one session (Phase 1's `stamp` and Phase 3's `emit` run as
separate Bash-tool calls, each a fresh shell), so the whole file-keyed-by-pid
design was unsound in both directions.

The fix (#580) removes the shared file entirely: `stamp` prints the start
time to stdout instead of writing it anywhere, and the retro skill carries
that value forward as a literal argument to `emit`. There is no longer any
file for two sessions to collide on, so the original collision this test
pinned is now structurally impossible — proven directly below (no /tmp file
ever appears). What genuine concurrency remains is N processes appending to
the SAME events-*.jsonl log at once; this test drives that with real OS
processes (not a forced interleaving of file operations, since there is no
longer any file state to force an interleaving of) and asserts every line
survives intact with its own correct, non-null duration_ms.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "retro-telemetry.sh")
N = 6


def main():
    with tempfile.TemporaryDirectory() as tmp:
        events_dir = os.path.join(tmp, "events")
        os.makedirs(events_dir)
        env = dict(os.environ)
        env.pop("CLAUDE_SESSION_ID", None)
        env["CLAUDE_KIT_TELEMETRY"] = "1"
        env["CLAUDE_KIT_TELEMETRY_DIR"] = events_dir

        # N concurrent `stamp` calls (real OS processes, genuinely overlapping).
        before = set(glob.glob("/tmp/retro-start-*"))
        stamp_procs = [
            subprocess.Popen(["bash", SCRIPT, "stamp"], env=env, stdout=subprocess.PIPE, text=True)
            for _ in range(N)
        ]
        starts = [p.communicate()[0].strip() for p in stamp_procs]
        after = set(glob.glob("/tmp/retro-start-*"))
        if after != before:
            print(f"FAIL: #580 regressed — stamp wrote /tmp file(s): {after - before}")
            sys.exit(1)
        for i, s in enumerate(starts):
            if not s.isdigit():
                print(f"FAIL: session {i} stamp did not print a numeric epoch-ms value (got: {s!r})")
                sys.exit(1)

        # N concurrent `emit` calls, each keyed only by its own start_ms argument
        # (no shared state at all) — the events log append is the one thing
        # that is genuinely still shared, so this is what actually needs
        # concurrent-safety proof.
        emit_procs = [
            subprocess.Popen(["bash", SCRIPT, "emit", starts[i], str(i), "0"], env=env)
            for i in range(N)
        ]
        for p in emit_procs:
            p.wait(timeout=10)

        today = subprocess.check_output(["date", "-u", "+%Y-%m-%d"], text=True).strip()
        log_path = os.path.join(events_dir, f"events-{today}.jsonl")
        with open(log_path) as fh:
            raw_lines = [l for l in fh if l.strip()]

        if len(raw_lines) != N:
            print(f"FAIL: expected {N} emitted lines, got {len(raw_lines)} (concurrent append corrupted/dropped a line)")
            sys.exit(1)

        seen_processed = set()
        for raw in raw_lines:
            try:
                line = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"FAIL: a line failed to parse as JSON (torn concurrent write): {exc}\n  {raw!r}")
                sys.exit(1)
            processed = line["meta"]["retro_items_processed"]
            seen_processed.add(processed)
            if line["meta"]["duration_ms"] is None:
                print(f"FAIL: duration_ms null for session {processed} — start_ms argument lost isolation: {line}")
                sys.exit(1)

        if seen_processed != set(range(N)):
            print(f"FAIL: expected sessions 0..{N-1} all present, got {sorted(seen_processed)}")
            sys.exit(1)

        print(f"OK: {N} concurrent stamp+emit sessions isolated, no /tmp file, no cross-session null, no torn writes")


if __name__ == "__main__":
    main()
