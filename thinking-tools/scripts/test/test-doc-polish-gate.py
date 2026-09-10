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
2. The "command error vs. mismatch" verdict-mapping rule is present.
3. Independently-implemented matchers for the three narrowed rules fire on #705's real
   examples and do NOT fire on its false-positive examples.
4. The SHA gate's premise is real, not assumed: a nonexistent SHA actually makes `git log`
   fail (command error), and a real SHA (HEAD's own) actually resolves — proven by running
   both, not by reading the doc's wording.

Usage:
    python3 thinking-tools/scripts/test/test-doc-polish-gate.py
    python3 thinking-tools/scripts/test/test-doc-polish-gate.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REF_PATH = _REPO_ROOT / "thinking-tools" / "skills" / "doc-polish" / "reference.md"

# ---------------------------------------------------------------------------
# The three narrowed rules (reference.md §Layer 4 Gate), executed
# ---------------------------------------------------------------------------

# The repo's actual top-level directories (`ls` the repo root) — the gate treats a path
# token as real only when its first segment names one of these, or its last segment has
# a file extension.
_KNOWN_DIRS = {
    "scripts", "thinking-tools", "obsidian-vault-manager", "vault-bridge",
    "feedback-loop", "docs", "rules", ".github", ".claude-plugin",
}
_PATH_TOKEN = re.compile(r"[\w.\-]+(?:/[\w.\-]+)+")


def path_gate_fires(text: str) -> bool:
    """Fires only on a token with a file extension or a known top-level dir prefix.

    "Extension" requires a letter in the suffix — a bare `.0`/`.2` off a version number or
    ratio (`v1.2/v2.0`, `0.5/1.0`) is a decimal point, not an extension.
    """
    for token in _PATH_TOKEN.findall(text):
        segments = [s for s in token.split("/") if s]
        if not segments:
            continue
        last = segments[-1]
        if "." in last and re.search(r"[A-Za-z]", last.rsplit(".", 1)[1]):
            return True
        if segments[0] in _KNOWN_DIRS:
            return True
    return False


# ASCII-alnum boundaries, not `\w` boundaries and not "any other hex digit": Korean particles
# attach directly to a token with no space ("3b82292가"), and `\b`'s `\w` treats Hangul as a
# word character, so no boundary exists there and a plain `\b`-bounded token silently fails to
# match. But the boundary can't be "not another hex digit" either — that lets the token match
# INSIDE an ordinary Latin word ("commit3b82292x") where the surrounding letters just don't
# happen to be hex ones. Hangul isn't ASCII alnum, so this rejects the Latin case while still
# allowing the Korean-particle case through.
_HEX_TOKEN = re.compile(r"(?<![0-9a-zA-Z])[0-9a-fA-F]{7,40}(?![0-9a-zA-Z])")


def sha_gate_fires(text: str) -> bool:
    """Fires only on a hex string with at least one a-f letter — not an all-digit number."""
    return any(re.search(r"[a-fA-F]", tok) for tok in _HEX_TOKEN.findall(text))


_STATUS_KEYWORDS = ("미구현", "없음", "아직", "지원 안 함", "not implemented")
_COMPANION = re.compile(r"#\d+|`[^`]+`")


def status_gate_fires(text: str) -> bool:
    """Fires only when a status keyword shares a SENTENCE with #N / a path / a backticked name.

    Sentence, not clause: reference.md's rule is scoped to the sentence on purpose (#705
    round 2) — a Korean run-on joining two clauses with a connective (~는데/~지만) and no
    terminal punctuation is still one sentence about one topic, and requiring an even
    narrower "same clause" missed exactly that ordinary construction.
    """
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
    ("v1.2/v2.0", False),                    # version numbers, not a path (round 2)
    ("설정값은 0.5/1.0 입니다", False),       # a ratio, not a path (round 2)
]

_SHA_FIXTURES = [
    ("1234567", False),          # 7-digit line count / timestamp
    ("2222222 lines changed", False),
    ("3b82292", True),           # real SHA example from the doc
    ("3b82292가 그 예시다", True),  # Korean particle attached with no space (round 2)
    ("commit3b82292x", False),   # hex run glued to ordinary Latin letters, not a token (round 3)
]

_STATUS_FIXTURES = [
    ("알려진 버그는 없음", False),
    ("이 기능은 아직 베타", False),
    ("PR #693은 아직 머지 안 됨", True),
    ("`--fix`는 아직 미구현", True),   # doc's own canonical example
    ("`--foo` 플래그가 있는데 구현은 아직 안 됨", True),  # one run-on sentence, same rule (round 2)
]

# Wording pins: each must be a substring of the live Gate row / Checks section once
# whitespace runs (including a hard-wrap newline) are collapsed to a single space — so a
# reflow at a different column doesn't spuriously break the pin.
_WORDING_PINS = [
    "not a bare slash",
    "pure decimal digits aren't a SHA",
    "directly predicates a named target in the same sentence",
    "Command error vs. mismatch",
    "the tool being unable to answer",
    "rebased away or never existed",
    "is-shallow-repository",
    "None of these fire on ordinary prose",
]


def git_log_command_errors(sha: str, cwd: Path) -> bool:
    """True if `git log -1 --format=%s <sha>` fails to even run (the 저장소로 확인 불가
    case) rather than resolving to a subject line (확인됨, or 어긋남 if it's the wrong one)."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s", sha],
        cwd=cwd, capture_output=True, text=True,
    )
    return result.returncode != 0


def _git_command_error_checks(repo_root: Path) -> list[str]:
    """Proves the premise the 'command error vs. mismatch' rule depends on: a bad SHA makes
    `git log` fail outright, and this is distinguishable from a real SHA resolving fine —
    not just a wording pin, since #705's SHA gate problem was reproduced by actually running
    `git log` into `fatal: bad revision`, not by reading the doc."""
    failures = []
    if not git_log_command_errors("ffffffffffffffffffffffffffffffffffffff", repo_root):
        failures.append(
            "expected git log to fail (command error) on a nonexistent 40-hex SHA, it did not"
        )
    real_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True,
    ).stdout.strip()
    if real_sha and git_log_command_errors(real_sha, repo_root):
        failures.append("expected git log to resolve HEAD's own real SHA, it errored instead")
    return failures


def _write(base: str, rel: str, content: str) -> None:
    Path(base, rel).write_text(content, encoding="utf-8")


def is_shallow_clone(cwd: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=cwd, capture_output=True, text=True,
    )
    return result.stdout.strip() == "true"


def _shallow_clone_checks() -> list[str]:
    """Proves the premise the shallow-clone carve-out depends on: a real, valid, OLD commit
    genuinely fails `git log` in a depth-1 clone that doesn't have it — the exact ambiguity
    (indistinguishable from a fabricated SHA) round-2's blanket rule missed — and that
    `git rev-parse --is-shallow-repository` correctly tells the shallow clone from the full one."""
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        full = str(Path(tmp, "full"))
        subprocess.run(["git", "init", "-q", full], check=True)
        subprocess.run(["git", "-C", full, "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", full, "config", "user.name", "t"], check=True)
        _write(full, "a.txt", "1\n")
        subprocess.run(["git", "-C", full, "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", full, "commit", "-q", "-m", "old"], check=True)
        old_sha = subprocess.run(
            ["git", "-C", full, "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()
        _write(full, "a.txt", "2\n")
        subprocess.run(["git", "-C", full, "commit", "-q", "-am", "new"], check=True)

        if is_shallow_clone(Path(full)):
            failures.append("expected the full repo to NOT report as shallow, it did")
        if git_log_command_errors(old_sha, Path(full)):
            failures.append("expected the full repo to resolve its own old commit, it errored")

        shallow = str(Path(tmp, "shallow"))
        subprocess.run(
            ["git", "clone", "-q", "--depth", "1", f"file://{full}", shallow], check=True
        )
        if not is_shallow_clone(Path(shallow)):
            failures.append("expected the depth-1 clone to report as shallow, it did not")
        if not git_log_command_errors(old_sha, Path(shallow)):
            failures.append(
                "expected a real, valid, old commit to fail git log in a depth-1 clone that "
                "never fetched it — the exact ambiguity the shallow-clone carve-out exists for"
            )
    return failures


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

    git_failures = _git_command_error_checks(_REPO_ROOT)
    git_failures += _shallow_clone_checks()
    if git_failures:
        for f in git_failures:
            print(f"FAIL: {f}")
        return 1

    total = (
        len(_WORDING_PINS) + len(_PATH_FIXTURES) + len(_SHA_FIXTURES) + len(_STATUS_FIXTURES) + 6
    )
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
    failures += _git_command_error_checks(_REPO_ROOT)
    failures += _shallow_clone_checks()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    total = (
        len(_WORDING_PINS) + len(_PATH_FIXTURES) + len(_SHA_FIXTURES) + len(_STATUS_FIXTURES) + 6
    )
    print(f"OK: all {total} doc-polish-gate checks passed against the live reference.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
