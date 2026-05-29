#!/usr/bin/env python3
"""Detect trigger-phrase regressions in thinking-tools SKILL.md descriptions.

When a SKILL.md `description:` is slimmed, individual trigger phrases can be
silently dropped — which removes the skill from auto-invocation for those
utterances. A char-count check does NOT catch this (a description can shrink
while losing a critical trigger). This script extracts the trigger set from
each skill's description and compares a base git ref against the working tree
(or a head ref), reporting any trigger that disappeared.

Output is a WARNING report, not a hard gate: some removals are intentional
synonym cleanup. The reviewer decides. Exit code 1 signals "removals found"
so a workflow verify stage can surface them for human judgment.

Usage:
    # compare base ref against the working tree
    python3 check-trigger-regression.py <BASE_REF>

    # compare two refs explicitly
    python3 check-trigger-regression.py <BASE_REF> <HEAD_REF>

    # validate the extraction logic
    python3 check-trigger-regression.py --self-test

Examples:
    python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
    python3 thinking-tools/scripts/test/check-trigger-regression.py HEAD~3 HEAD
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILL_GLOB = "thinking-tools/skills/*/SKILL.md"

# Repo root resolved relative to this file (test/ -> scripts/ -> thinking-tools/ -> root),
# so the script behaves identically regardless of the caller's CWD.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _git(*args: str) -> subprocess.CompletedProcess:
    """Run a git command anchored at the repo root (CWD-independent)."""
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


# Connector phrases that introduce more triggers but are not triggers themselves.
_CONNECTOR_RE = re.compile(r"\bor (?:requests|explicitly|mentions):")
# Lines inside the description that are guidance, not triggers.
_NON_TRIGGER_PREFIXES = ("Routing:", "Skip for:", "Use when", "Structure:")


def extract_triggers(skill_text: str, label: str = "") -> set[str]:
    """Pull the set of trigger phrases out of a SKILL.md's description block.

    Returns normalized phrases (quotes/trailing punctuation stripped). Routing
    and Skip-for guidance lines are excluded — only the "Trigger when user
    mentions:" enumeration is parsed.

    NOTE: Only handles `description: |` block-scalar style (every current
    thinking-tools skill uses it). Folded (>) or quoted single-line
    descriptions return an empty set silently — extend the regex if a skill
    ever switches style, otherwise its triggers would be invisible here.
    """
    fm_match = re.match(r"^---\n(.*?)\n---", skill_text, re.DOTALL)
    if not fm_match:
        return set()
    frontmatter = fm_match.group(1)

    desc_match = re.search(
        r"description:\s*\|\n(.*?)(?=\n[a-zA-Z_-]+:\s|\Z)", frontmatter, re.DOTALL
    )
    if not desc_match:
        if label:
            print(
                f"  WARNING: {label}: no `description: |` block-scalar found — "
                f"triggers not extracted (folded/quoted style?)",
                file=sys.stderr,
            )
        return set()
    description = desc_match.group(1)

    trig_match = re.search(
        r"Trigger when user mentions:(.*?)(?=\n\s*(?:Routing|Skip for):|\Z)",
        description,
        re.DOTALL,
    )
    if not trig_match:
        return set()

    blob = _CONNECTOR_RE.sub(",", trig_match.group(1))
    triggers = set()
    for raw in blob.split(","):
        token = raw.strip('". \t')
        # Drop stray guidance fragments and single-char noise.
        if not token or len(token) < 2:
            continue
        if any(token.startswith(p) for p in _NON_TRIGGER_PREFIXES):
            continue
        triggers.add(token)
    return triggers


def _ref_exists(ref: str) -> bool:
    """True if `ref` resolves to a commit in this repo."""
    return _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0


def _git_show(ref: str, path: str) -> str | None:
    """Return file contents at a git ref, or None if the path is absent there."""
    result = _git("show", f"{ref}:{path}")
    if result.returncode != 0:
        return None
    return result.stdout


def _read_working_tree(path: str) -> str | None:
    p = _REPO_ROOT / path
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _disk_glob() -> list[str]:
    """Skill paths globbed from disk, returned repo-relative (CWD-independent)."""
    return sorted(str(p.relative_to(_REPO_ROOT)) for p in _REPO_ROOT.glob(SKILL_GLOB))


def _list_skill_paths(ref: str | None) -> list[str]:
    """Skill paths tracked at a ref (or globbed from disk when ref is None)."""
    if ref is None:
        return _disk_glob()
    result = _git("ls-tree", "-r", "--name-only", ref)
    if result.returncode != 0:
        print(
            f"WARNING: `git ls-tree {ref}` failed; falling back to disk glob. "
            f"stderr: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return _disk_glob()
    pat = re.compile(r"^thinking-tools/skills/[^/]+/SKILL\.md$")
    return sorted(line for line in result.stdout.splitlines() if pat.match(line))


def compare(base_ref: str, head_ref: str | None) -> int:
    """Report triggers present at base_ref but missing at head_ref/working tree."""
    if not _ref_exists(base_ref):
        print(f"ERROR: base ref '{base_ref}' not found in this repo.", file=sys.stderr)
        return 2
    if head_ref is not None and not _ref_exists(head_ref):
        print(f"ERROR: head ref '{head_ref}' not found in this repo.", file=sys.stderr)
        return 2
    paths = _list_skill_paths(base_ref) or _list_skill_paths(None)
    total_removed = 0
    print(f"Trigger regression check: {base_ref} -> {head_ref or 'working tree'}\n")
    for path in paths:
        base_text = _git_show(base_ref, path)
        if base_text is None:
            continue  # skill did not exist at base — nothing to regress
        head_text = _git_show(head_ref, path) if head_ref else _read_working_tree(path)
        if head_text is None:
            print(f"  {path}: REMOVED FILE (skill deleted)")
            total_removed += 1
            continue
        removed = extract_triggers(base_text, path) - extract_triggers(head_text, path)
        if removed:
            skill = path.split("/")[-2]
            print(f"  [{skill}] {len(removed)} trigger(s) dropped:")
            for t in sorted(removed):
                print(f"      - {t}")
            total_removed += len(removed)

    print()
    if total_removed:
        print(f"RESULT: {total_removed} trigger removal(s) found — review whether intentional.")
        return 1
    print("RESULT: no trigger removals.")
    return 0


def _self_test() -> int:
    before = """---
name: demo
description: |
  Some purpose line.

  Trigger when user mentions: 반증해줘, 주장 검증, 약점 찾아줘,
  devil's advocate, adversarial review,
  or requests: "이 주장 검증해줘", "살아남을 수 있어?".

  Skip for: consensus building (use expert-panel).
allowed-tools: Read
---
body
"""
    after = """---
name: demo
description: |
  Some purpose line.

  Trigger when user mentions: 반증해줘, 약점 찾아줘,
  devil's advocate, adversarial review, "살아남을 수 있어?".
  Routing: 합의는 expert-panel.
allowed-tools: Read
---
body
"""
    cases = []

    b = extract_triggers(before)
    a = extract_triggers(after)

    # Connector phrases must not leak in as triggers.
    cases.append(("no 'or requests' leak", "or requests:" not in " ".join(b)))
    # Quoted triggers are captured without quotes.
    cases.append(("quoted trigger captured", "이 주장 검증해줘" in b))
    cases.append(("question-mark trigger kept", "살아남을 수 있어?" in b))
    # Routing / Skip-for lines are not triggers.
    cases.append(("routing line excluded", not any("expert-panel" in t for t in a)))
    cases.append(("skip-for line excluded", not any(t.startswith("Skip for") for t in b)))
    # Regression detection: dropped triggers surface in the diff.
    removed = b - a
    cases.append(("detects 주장 검증 removal", "주장 검증" in removed))
    cases.append(("detects 이 주장 검증해줘 removal", "이 주장 검증해줘" in removed))
    # Retained triggers are not falsely flagged.
    cases.append(("retained trigger not flagged", "반증해줘" not in removed))
    cases.append(("retained quoted not flagged", "살아남을 수 있어?" not in removed))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return _self_test()
    base_ref = argv[0]
    head_ref = argv[1] if len(argv) > 1 else None
    return compare(base_ref, head_ref)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
