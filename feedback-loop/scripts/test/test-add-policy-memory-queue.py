#!/usr/bin/env python3
"""Regression test: add-policy's read-only memory queue review (#867).

§6-memory-contract calls native `feedback` memories a promotion queue, but before #867 the queue
emptied only when a user happened to land a matching rule. reference.md §6-queue-contract is the
entry that lists the whole queue; this pins what it promises:

1. SKILL.md §1 points at §6-queue-contract with "as written" (a bare citation decays), and
   codex.md states the review is unsupported on Codex.
2. The section reuses §6-snippet (no second scan block of its own), is read-only until a §3
   confirmation, keys items by file path (a basename/`name:` mismatch is still one item), turns
   every stderr-named path into 미확인, gives each item one of three verdicts with its 근거,
   refuses a 매립 후보 without an evidence pointer, and marks a cross-project repeat as a
   machine-global priority signal.
3. EXECUTED: §6-snippet, run against a temp HOME, lists a `metadata:`-nested `type: feedback`
   whose filename differs from its slug in two projects, and an unreadable file or directory
   surfaces on stderr NAMING the path — the property "unread is 미확인, not empty" rests on.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-memory-queue.py
    python3 feedback-loop/scripts/test/test-add-policy-memory-queue.py --self-test
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SKILL_DIR = _HERE.parents[1] / "skills" / "add-policy"

# Reuse the routing suite's snippet extractor and runner: one scan, one way to run it.
_spec = importlib.util.spec_from_file_location("routing", _HERE / "test-add-policy-routing.py")
assert _spec and _spec.loader
_routing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_routing)

_QUEUE_RE = re.compile(r"^## §6-queue-contract\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)

# (claim, phrase that must appear in §6-queue-contract, whitespace-normalised)
_QUEUE_CLAIMS = [
    ("reuses §6-snippet", "Run §6-snippet as written"),
    ("read-only", "Read-only until a §3 confirmation."),
    ("no counters / auto-promotion", "No counters, no registry, no automatic promotion."),
    ("keyed by path, not slug", "Key every item by its **file path**"),
    ("slug mismatch visible", "reported with both so the mismatch is visible"),
    ("unread is unverified", "**Unread is unverified, not empty.**"),
    ("stderr path -> 미확인", "goes in the output as **미확인** with that stderr line"),
    ("verdict: already landed", "**이미 매립됨** — 삭제 후보"),
    ("verdict: candidate", "**매립 후보** — 사이트 제안"),
    ("verdict: project fact", "**프로젝트 고유 사실** — 유지"),
    ("every verdict has 근거", "every verdict with its 근거"),
    ("no evidence, no candidate", "**No evidence pointer, no candidate.**"),
    ("unsupported item is held", "**근거 없음 — 보류**"),
    ("cross-project signal", "**여러 프로젝트 (n곳)**: a priority signal for a machine-global site"),
    ("delete needs confirmation", "Never delete or write without it."),
    ("delete uses §3 shape", "Deleting 이미 매립됨 items uses the §3 confirmation shape"),
    ("zero is printed", "never end the review silently"),
    ("Codex unsupported", "on Codex report the review as unsupported"),
]


def _norm(text: str) -> str:
    return " ".join(text.split())


def check_static(skill: str, ref: str, codex: str) -> list[str]:
    errors = []
    if "apply reference §6-queue-contract as written" not in _norm(skill):
        errors.append("SKILL.md does not point at §6-queue-contract 'as written'")
    m = _QUEUE_RE.search(ref)
    if m is None:
        return errors + ["reference.md has no `## §6-queue-contract` section"]
    section = _norm(m.group(0))
    errors += [f"§6-queue-contract lost: {name}" for name, phrase in _QUEUE_CLAIMS if _norm(phrase) not in section]
    if "```bash" in m.group(0):
        errors.append("§6-queue-contract ships its own bash block — reuse §6-snippet, do not fork the scan")
    if "§6-queue-contract" not in codex or "unsupported on Codex" not in _norm(codex):
        errors.append("codex.md does not state the queue review is unsupported on Codex")
    return errors


def check_snippet(ref: str) -> list[str]:
    snippet = _routing._extract_memory_snippet(ref)
    if snippet is None:
        return ["no §6-snippet bash block to run"]
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        for proj in ("-proj-a", "-proj-b"):
            mem = home / ".claude" / "projects" / proj / "memory"
            mem.mkdir(parents=True)
            # The 2026-10-13 shape: `feedback_*` filename, `feedback-*` slug, type under metadata.
            (mem / "feedback_model_choice.md").write_text(
                "---\nname: feedback-model-choice\nmetadata:\n  type: feedback\n---\nUse Sonnet.\n"
            )
            (mem / "MEMORY.md").write_text("- [x](feedback_model_choice.md) — hook\n")
        listed = _routing._run_snippet(snippet, home, "/bin/sh").stdout.split()
        want = {str(home / ".claude/projects" / p / "memory/feedback_model_choice.md") for p in ("-proj-a", "-proj-b")}
        if set(listed) != want:
            errors.append(f"nested-type / slug-mismatch memories not both listed: {listed}")

        if os.geteuid() != 0:  # root reads 000 anyway
            bad_file = home / ".claude/projects/-proj-a/memory/locked.md"
            bad_file.write_text("---\nmetadata:\n  type: feedback\n---\n")
            bad_file.chmod(0o000)
            bad_dir = home / ".claude/projects/-proj-c/memory"
            bad_dir.mkdir(parents=True)
            bad_dir.chmod(0o000)
            try:
                p = _routing._run_snippet(snippet, home, "/bin/sh")
            finally:
                bad_file.chmod(0o644)
                bad_dir.chmod(0o755)
            for path in (bad_file, bad_dir):
                if str(path) not in p.stderr:
                    errors.append(f"unreadable {path.name} not NAMED on stderr — it would read as empty: {p.stderr!r}")
            if set(p.stdout.split()) != want:
                errors.append("an unreadable path changed the readable results")
    return errors


def _load() -> tuple[str, str, str]:
    skill, ref, codex = ((_SKILL_DIR / f).read_text(encoding="utf-8") for f in ("SKILL.md", "reference.md", "codex.md"))
    return skill, ref, codex


def _self_test() -> int:
    skill, ref, codex = _load()
    mutations = [
        ("pointer decays to a citation", skill.replace("apply reference §6-queue-contract as written", "see §6-queue-contract"), ref, codex),
        ("evidence rule dropped", skill, ref.replace("**No evidence pointer, no candidate.**", ""), codex),
        ("미확인 rule dropped", skill, ref.replace("**Unread is unverified, not empty.**", ""), codex),
        ("cross-project signal dropped", skill, ref.replace("**여러 프로젝트 (n곳)**", "여러 프로젝트"), codex),
        ("forked scan", skill, ref.replace("## §6-queue-contract", "## §6-queue-contract\n```bash\nfind ~ -name '*.md'\n```\n", 1), codex),
        ("codex note dropped", skill, ref, codex.replace("unsupported on Codex", "")),
        ("section renamed", skill, ref.replace("## §6-queue-contract", "## §6-queue"), codex),
    ]
    failed = 0
    ok = not check_static(skill, ref, codex)
    print(f"  [{'OK' if ok else 'FAIL'}] real files pass")
    failed += not ok
    for name, s, r, c in mutations:
        assert (s, r, c) != (skill, ref, codex), f"mutation no-opped: {name}"
        ok = bool(check_static(s, r, c))
        print(f"  [{'OK' if ok else 'FAIL'}] {name} (expect FAIL)")
        failed += not ok
    ok = bool(check_snippet(ref.replace("## §6-snippet", "## §6-scan")))
    print(f"  [{'OK' if ok else 'FAIL'}] snippet heading orphaned (expect FAIL)")
    failed += not ok
    if failed:
        print(f"\nSELF-TEST FAILED: {failed} case(s)")
        return 1
    print(f"\nOK: all {len(mutations) + 2} self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--self-test"]:
        return _self_test()
    skill, ref, codex = _load()
    errors = check_static(skill, ref, codex) + check_snippet(ref)
    for e in errors:
        print(f"  [FAIL] {e}")
    if errors:
        print(f"\nRESULT: {len(errors)} check(s) FAILED")
        return 1
    print("OK: all add-policy-memory-queue checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
