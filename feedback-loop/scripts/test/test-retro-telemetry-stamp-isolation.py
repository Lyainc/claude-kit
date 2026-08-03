#!/usr/bin/env python3
"""Regression for retro-telemetry.sh's sid-less stamp path (#529).

Two concurrent sessions with no CLAUDE_SESSION_ID must NOT collide on the
same /tmp/retro-start-*.ms file. Before the fix both fell back to the literal
string `unknown`, so one session's `emit` could delete the stamp the other
was still using. Measured live 2026-08-03: two sid-less emits, one
duration_ms null.

This test forces the exact interleaving that exposes the bug — A stamps, B
stamps, A emits, B emits — instead of running each session start-to-finish
before the next starts. A fully sequential session pair never overlaps on
the shared file at all, so it would pass identically whether or not the fix
is in place (that gap was caught in review before this version).

Each "session" is a long-lived `bash -c` process fed one command at a time
over its stdin, so this test controls the interleaving directly rather than
relying on OS scheduling — deterministic, no sleeps, no flakiness. Each
session is its own process (own PID), which is what makes it a stand-in for
two genuinely concurrent harness sessions under the $PPID fallback.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "retro-telemetry.sh")
SENTINEL = "__CMD_DONE__"


class Session:
    def __init__(self, script, events_dir):
        env = dict(os.environ)
        env.pop("CLAUDE_SESSION_ID", None)
        env["CLAUDE_KIT_TELEMETRY"] = "1"
        env["CLAUDE_KIT_TELEMETRY_DIR"] = events_dir
        self.proc = subprocess.Popen(
            ["bash", "-c",
             f'echo "$$"; SCRIPT="{script}"; '
             f'while IFS= read -r line; do eval "$line"; echo {SENTINEL}; done'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env, bufsize=1,
        )
        self.pid = self.proc.stdout.readline().strip()

    def run(self, cmd, timeout=5):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise AssertionError(f"session {self.pid} closed unexpectedly")
            if line.strip() == SENTINEL:
                return

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def main():
    tmp = tempfile.mkdtemp()
    events_dir = os.path.join(tmp, "events")
    os.makedirs(events_dir)
    try:
        session_a = Session(SCRIPT, events_dir)
        session_b = Session(SCRIPT, events_dir)

        if session_a.pid == session_b.pid:
            print("FAIL: test harness gave both sessions the same PID, can't assert isolation")
            sys.exit(1)

        # Forced interleaving: A stamps, B stamps, A emits, B emits.
        # Pre-fix (shared "unknown" path): B's stamp overwrites A's, then A's
        # emit deletes the shared file, so B's emit finds no stamp -> null.
        session_a.run('"$SCRIPT" stamp')
        session_b.run('"$SCRIPT" stamp')
        session_a.run('"$SCRIPT" emit 3 1 3')
        session_b.run('"$SCRIPT" emit 7 2 7')
        session_a.close()
        session_b.close()

        stamp_a = f"/tmp/retro-start-{session_a.pid}.ms"
        stamp_b = f"/tmp/retro-start-{session_b.pid}.ms"
        for stamp in (stamp_a, stamp_b):
            if os.path.exists(stamp):
                os.remove(stamp)
                print(f"FAIL: stamp ({stamp}) was not cleaned up by its own session's emit")
                sys.exit(1)

        today = subprocess.check_output(["date", "-u", "+%Y-%m-%d"], text=True).strip()
        log_path = os.path.join(events_dir, f"events-{today}.jsonl")
        lines = [json.loads(l) for l in open(log_path) if l.strip()]
        if len(lines) != 2:
            print(f"FAIL: expected 2 emitted lines, got {len(lines)}")
            sys.exit(1)

        for line, expect_processed in zip(lines, (3, 7)):
            if line["meta"]["retro_items_processed"] != expect_processed:
                print(f"FAIL: line mismatch, expected processed={expect_processed}, got {line}")
                sys.exit(1)
            if line["meta"]["duration_ms"] is None:
                print(f"FAIL: duration_ms null under interleaved sid-less sessions (stamp collision): {line}")
                sys.exit(1)

        print("OK: interleaved sid-less sessions get isolated stamp paths, no cross-session null")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
