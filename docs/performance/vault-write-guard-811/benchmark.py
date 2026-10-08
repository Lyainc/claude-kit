#!/usr/bin/env python3
"""#811: interleaved hook-only timings and separately traced executable calls.

No proposed Write/Edit/Bash action is executed. Only disposable fixture directories
and instrumentation logs are written. No dependencies beyond the hook's own tools.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ENV_KEYS = ("VAULT_BRIDGE_DISABLE", "VAULT_BRIDGE_STRICT_NAMING", "VAULT_BRIDGE_WRITE_CONTRACT",
            "VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH")


def fixtures(vault: Path):
    def write(name="notes/valid-note.md", tool="Write", agent=None):
        payload = {"tool_name": tool, "tool_input": {"file_path": str(vault / name)}}
        if agent is not None:
            payload["subagent_type"] = agent
        return json.dumps(payload)
    def bash(command, agent=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(vault)}
        if agent is not None:
            payload["subagent_type"] = agent
        return json.dumps(payload)
    return [
        ("write_valid", write(), {}),
        ("edit_valid", write(tool="Edit"), {}),
        ("write_deny", write(agent="executor"), {}),
        ("warn_bad_name", write("sources/bad.md", agent="executor"), {"VAULT_BRIDGE_WRITE_CONTRACT": "warn"}),
        ("strict_bad_name", write("sources/bad.md"), {"VAULT_BRIDGE_STRICT_NAMING": "1"}),
        ("assets", write("assets/Photo.PNG", agent="executor"), {}),
        ("contract_off", write(agent="executor"), {"VAULT_BRIDGE_WRITE_CONTRACT": "off"}),
        ("bash_deny", bash("echo x > notes/x.md", "executor"), {}),
        ("bash_read", bash("cat notes/x.md", "executor"), {}),
        ("bash_main", bash("echo x > notes/x.md"), {}),
        ("irrelevant", '{"tool_name":"Read"}', {}),
        ("disabled", write(agent="executor"), {"VAULT_BRIDGE_DISABLE": "1"}),
        ("missing_vault", write(), {"VAULT_BRIDGE_VAULT_ROOT": str(vault / "missing")}),
        ("malformed", '{', {}),
    ]


def invoke(hook, payload, env):
    started = time.perf_counter_ns()
    proc = subprocess.run(["bash", str(hook)], input=payload, text=True,
                          capture_output=True, env=env)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    # The recorded samples include process startup and stdout/stderr capture.
    signature = [proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else None, proc.stderr]
    return elapsed, signature


def summary(samples):
    ordered = sorted(samples)
    return {"n": len(samples), "median_ms": statistics.median(samples),
            "p95_ms": ordered[math.ceil(len(samples) * .95) - 1], "max_ms": max(samples)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=6)
    parser.add_argument("--repetitions", type=int, default=120)
    parser.add_argument("--sessions", type=int, default=2)
    args = parser.parse_args()
    assert args.warmup >= 0 and args.repetitions > 0 and args.sessions > 0
    hooks = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    env_base = os.environ.copy()
    for key in ENV_KEYS:
        env_base.pop(key, None)
    report = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "platform": platform.platform(), "runner_python": sys.version,
              "binaries": {name: shutil.which(name) for name in ("bash", "cat", "jq", "python3", "cut", "basename")},
              "hook_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in hooks.items()},
              "warmup_pairs_per_case_per_session": args.warmup,
              "timed_pairs_per_case_per_session": args.repetitions,
              "sessions": [], "external_executable_invocations": {},
              "count_scope": "Includes outer bash and traced cat/jq/python3/cut/basename executions; excludes shell subshell/fork count. Instrumented samples are never timed.",
              "order": "Case order reverses in session 2; baseline/candidate pair order alternates by session + case + iteration.",
              "versions": {name: subprocess.check_output(command, text=True).strip() for name, command in {
                  "hook_python": [shutil.which("python3"), "--version"], "jq": [shutil.which("jq"), "--version"],
                  "bash": [shutil.which("bash"), "--version"]}.items()}}
    with tempfile.TemporaryDirectory(prefix="vb-811-") as tmp:
        vault = Path(tmp) / "vault"
        for name in (".obsidian", "sources", "notes", "wiki", "assets"):
            (vault / name).mkdir(parents=True)
        env_base["VAULT_BRIDGE_VAULT_ROOT"] = str(vault)
        cases = fixtures(vault)
        report["inputs"] = [{"case": name, "payload": payload.replace(tmp, "<TEMP>"),
                             "env": {k: v.replace(tmp, "<TEMP>") for k, v in overrides.items()}}
                            for name, payload, overrides in cases]
        for session in range(args.sessions):
            entry = {"start_loadavg": os.getloadavg(), "cases": {}}
            indexed = list(enumerate(cases))
            if session % 2:
                indexed.reverse()
            for index, (name, payload, overrides) in indexed:
                env = dict(env_base, **overrides)
                samples = {key: [] for key in hooks}
                expected = None
                for i in range(args.warmup + args.repetitions):
                    order = ["baseline", "candidate"]
                    if (session + index + i) % 2:
                        order.reverse()
                    for key in order:
                        elapsed, signature = invoke(hooks[key], payload, env)
                        if expected is None:
                            expected = signature
                        assert signature == expected, f"decision drift: {session}/{name}/{key}: {signature!r} != {expected!r}"
                        if i >= args.warmup:
                            samples[key].append(elapsed)
                entry["cases"][name] = {key: dict(summary(values), samples_ms=values) for key, values in samples.items()}
                print(f"session {session + 1} {name}: " + ", ".join(
                    f"{key} median={summary(values)['median_ms']:.2f}ms p95={summary(values)['p95_ms']:.2f}ms" for key, values in samples.items()), flush=True)
            entry["end_loadavg"] = os.getloadavg()
            report["sessions"].append(entry)
        # Count real external tool launches through private PATH wrappers. Timing above
        # uses the unmodified PATH; wrappers would distort the performance comparison.
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        log = Path(tmp) / "calls"
        for name in ("cat", "jq", "python3", "cut", "basename"):
            real = report["binaries"][name]
            wrapper = bindir / name
            wrapper.write_text(f"#!/bin/sh\nprintf '%s\\n' {shlex.quote(name)} >> {shlex.quote(str(log))}\nexec {shlex.quote(real)} \"$@\"\n")
            wrapper.chmod(0o755)
        for name, payload, overrides in cases:
            report["external_executable_invocations"][name] = {}
            for key, hook in hooks.items():
                counts = []
                for _ in range(3):
                    log.write_text("")
                    invoke(hook, payload, dict(env_base, **overrides, PATH=str(bindir) + os.pathsep + env_base["PATH"]))
                    counter = Counter(log.read_text().splitlines())
                    counter["bash"] = 1
                    counts.append(dict(counter))
                assert counts[0] == counts[1] == counts[2], f"unstable executable count: {name}/{key}"
                report["external_executable_invocations"][name][key] = {"counts": counts[0], "total": sum(counts[0].values()), "n": 3}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
