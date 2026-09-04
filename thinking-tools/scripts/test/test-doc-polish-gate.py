#!/usr/bin/env python3
"""Regression test: doc-polish Layer 4 gate false-positive fixes (#705).

`thinking-tools/skills/doc-polish/reference.md`'s Layer 4 gate table (§Layer 4: Fact
Cross-Check Details) is prose an LLM follows, not code — so this executes the same three
narrowed rules against fixtures and pins the wording that encodes them, the same shape as
test-persona-selection.py.

#705 found three false positives:
1. path gate — any `/` fired it ("read/write 권한"), sending it into a `test -e` that
   was never going to find a file.
2. SHA gate — a pure decimal number (a line count, a timestamp) matched "7-40 hex" and
   sent `git log` into `fatal: bad revision`, with no rule mapping that command failure
   to 저장소로 확인 불가 instead of 어긋남.
3. status-assertion gate — ordinary Korean sentences ("알려진 버그는 없음") fired it with
   no companion signal, defeating the gate's stated purpose (keep gh/git off an ordinary
   polish call).

Checks:
1. Each gate row's narrowing clause is present verbatim in the live reference.md.
2. The "command error is not a mismatch" verdict-mapping rule is present.
3. Independently-implemented matchers for the three narrowed rules fire on #705's real
   examples and do NOT fire on its false-positive examples.

Usage:
    python3 thinking-tools/scripts/test/test-doc-polish-gate.py
    python3 thinking-tools/scripts/test/test-doc-polish-gate.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REF_PATH = _REPO_ROOT / "thinking-tools" / "skills" / "doc-polish" / "reference.md"

# ---------------------------------------------------------------------------
# The three narrowed rules (reference.md §Layer 4 Gate), executed
# ---------------------------------------------------------------------------

_KNOWN_DIRS = {
    "scripts", "thinking-tools", "obsidian-vault-manager", "vault-bridge",
    "feedback-loop", "docs", "rules", "reference", ".github",
}
_PATH_TOKEN = re.compile(r"[\w.\-]+(?:/[\w.\-]+)+")


def path_gate_fires(text: str) -> bool:
    """Fires only on a token with a file extension or a known top-level dir prefix."""
    for token in _PATH_TOKEN.findall(text):
        segments = [s for s in token.split("/") if s]
        if not segments:
            continue
        if "." in segments[-1]:
            return True
        if segments[0] in _KNOWN_DIRS:
            return True
    return False


_HEX_TOKEN = re.compile(r"\b[0-9a-fA-F]{7,40}\b")


def sha_gate_fires(text: str) -> bool:
    """Fires only on a hex string with at least one a-f letter — not an all-digit number."""
    return any(re.search(r"[a-fA-F]", tok) for tok in _HEX_TOKEN.findall(text))


_STATUS_KEYWORDS = ("미구현", "없음", "아직", "지원 안 함", "not implemented")
_COMPANION = re.compile(r"#\d+|`[^`]+`")


def status_gate_fires(text: str) -> bool:
    """Fires only when a status keyword shares a sentence with #N / a path / a backticked name."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for sentence in sentences:
        if any(kw in sentence for kw in _STATUS_KEYWORDS):
            if _COMPANION.search(sentence) or path_gate_fires(sentence):
                return True
    return False


# ---------------------------------------------------------------------------
# Fixtures: #705's false positives must NOT fire, its real examples must
# ---------------------------------------------------------------------------

_PATH_FIXTURES = [
    ("read/write 권한", False),
    ("pass/fail 기준", False),
    ("scripts/check-test-exitcode.py", True),
    ("thinking-tools/skills/", True),
]

_SHA_FIXTURES = [
    ("1234567", False),          # 7-digit line count / timestamp
    ("2222222 lines changed", False),
    ("3b82292", True),           # real SHA example from the doc
]

_STATUS_FIXTURES = [
    ("알려진 버그는 없음", False),
    ("이 기능은 아직 베타", False),
    ("PR #693은 아직 머지 안 됨", True),
    ("`create_inline_comment`는 아직 미구현", True),
]

# Wording pins: each must be a substring of the live Gate row / Checks section once
# whitespace runs (including a hard-wrap newline) are collapsed to a single space — so a
# reflow at a different column doesn't spuriously break the pin.
_WORDING_PINS = [
    "a bare word with a slash",
    "at least one a-f letter",
    "isn't a SHA",
    "only when it names a concrete target",
    "Command error is not a mismatch",
    "저장소로 확인 불가, not 어긋남",
]


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def run_checks(text: str) -> list[str]:
    failures: list[str] = []

    norm_text = _normalize_ws(text)
    for pin in _WORDING_PINS:
        if _normalize_ws(pin) not in norm_text:
            failures.append(f"wording pin missing from reference.md: {pin!r}")

    for value, expected in _PATH_FIXTURES:
        got = path_gate_fires(value)
        if got is not expected:
            failures.append(f"path_gate_fires({value!r}) = {got}, expected {expected}")

    for value, expected in _SHA_FIXTURES:
        got = sha_gate_fires(value)
        if got is not expected:
            failures.append(f"sha_gate_fires({value!r}) = {got}, expected {expected}")

    for value, expected in _STATUS_FIXTURES:
        got = status_gate_fires(value)
        if got is not expected:
            failures.append(f"status_gate_fires({value!r}) = {got}, expected {expected}")

    return failures


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run_self_test() -> int:
    """A reference.md missing the narrowing clauses must fail; the live wording must pass."""
    dirty = "Layer 4 gate with no narrowing at all.\n"
    failures = run_checks(dirty)
    if len(failures) != len(_WORDING_PINS):
        print(f"FAIL: planted-violation text expected {len(_WORDING_PINS)} wording-pin "
              f"failures, got {len(failures)}: {failures}")
        return 1

    # matcher semantics, independent of any file on disk
    matcher_failures = []
    for fn, fixtures, name in (
        (path_gate_fires, _PATH_FIXTURES, "path_gate_fires"),
        (sha_gate_fires, _SHA_FIXTURES, "sha_gate_fires"),
        (status_gate_fires, _STATUS_FIXTURES, "status_gate_fires"),
    ):
        for value, expected in fixtures:
            got = fn(value)
            if got is not expected:
                matcher_failures.append(f"{name}({value!r}) = {got}, expected {expected}")

    if matcher_failures:
        for f in matcher_failures:
            print(f"FAIL: {f}")
        return 1

    total = len(_WORDING_PINS) + len(_PATH_FIXTURES) + len(_SHA_FIXTURES) + len(_STATUS_FIXTURES)
    print(f"OK: all {total} test-doc-polish-gate self-test cases passed")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        return run_self_test()

    if not _REF_PATH.is_file():
        print(f"FAIL: reference.md not found at {_REF_PATH}")
        return 1
    text = _REF_PATH.read_text(encoding="utf-8")

    failures = run_checks(text)
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    total = len(_WORDING_PINS) + len(_PATH_FIXTURES) + len(_SHA_FIXTURES) + len(_STATUS_FIXTURES)
    print(f"OK: all {total} doc-polish-gate checks passed against the live reference.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
