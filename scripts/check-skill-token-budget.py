#!/usr/bin/env python3
"""check-skill-token-budget.py — a SKILL.md must fit in the compaction re-attach window.

RULE (deterministic): every `*/skills/*/SKILL.md` in a source plugin must estimate to at
most 5,000 tokens, and every compaction-critical anchor inside it (the `## Rules` heading,
each `AskUserQuestion` gate) must sit inside that same 5,000-token prefix.

OBJECTIVE DAMAGE (#447, not taste): Claude Code keeps an invoked skill's body in context
across turns, and auto-compaction re-attaches only **the first 5,000 tokens of each skill**.
Everything past that is dropped, and dropped silently — no error, no warning, no STATE
trace. Measured on 2026-07-30, `add-policy` (7,322 tok) lost `## 8. Post-write self-check`
and `## Rules`; `audit` (7,419 tok) lost `## Phase 4 — OPTIONAL-FIX` — the E2 auto-fix
**user confirmation gate** — and `## Rules`. Invoke either skill a second time in a
compacted session and it runs with its safety gate missing from the instructions, producing
output indistinguishable from a correct run. Same failure class as #443/#433: a safeguard
turns itself off quietly.

HOW IT COUNTS: `tiktoken`'s `o200k_base` when it is importable, the char-class estimator
below when it is not. #454 preferred a dependency-free byte/char proxy, and that was tried
first — it does not work. Fitted over this repo's 26 SKILL.md + reference/*.md files, the
best two-parameter char model still lands anywhere in 0.86x-1.14x of the real count, because
markdown structure (tables, fences, URLs) drives tokenization more than character class
does. At that width the guard passed `add-policy` at a measured 5,304 tokens and `audit` at
5,286 — both genuinely over — while reporting them as ~4,990 and ~4,870. A guard that cannot
tell 5,300 from 4,900 is not guarding, so the accurate backend wins and CI installs it.

`o200k_base` is NOT Claude's tokenizer, and that caveat is real: expect the true Claude count
to sit within roughly ±10-20% of what this reports. It is, however, the tokenizer #447's own
measurements were taken with, so the numbers here are comparable to the ones in that issue.
The budget is left at a flat 5,000 rather than discounted for that uncertainty — the fix for a
file near the line is to move rationale out, not to tune the threshold. Two consequences worth
knowing before you edit a skill that is already close: a pass at 4,990 is NOT proof the real
Claude count is under 5,000, and a file with only tens of tokens of headroom turns the next
one-paragraph edit into a CI failure. After the #447 split the three fixed files sit at
4,930 / 4,840 / 4,736 — 1.4% to 5.3% of headroom, deliberately not more, because the material
left in them is contract text pinned by regression suites rather than prose that can be moved.

The fallback estimator (~4.4 ASCII chars per token, ~1.2 tokens per non-ASCII char) is NOT a
silent fallback. Without `tiktoken` the real mode **exits 2 and refuses to report a verdict**,
because a guard that quietly degrades to a backend this file just called "not guarding" is the
same silent-safeguard-off failure #447 is about. Pass `--allow-estimate` to opt into an
indicative run; it labels every line and stays non-authoritative.

ponytail: `## Rules` is the only invariant heading recognised, so skills that park invariants
under another name (`## Core Principle`, `### Constraints`) get the budget check but not the
anchor check. Widening the heading list is the upgrade if a gate is ever found under one.

WHY BOTH CHECKS: the budget check subsumes the anchor check today (a file under budget
cannot have an anchor past the boundary). The anchor check is still reported, because it is
the claim #447 actually makes — it names WHICH gate survives compaction, and it keeps its
meaning if the budget is ever raised or scoped.

Usage:
    python3 scripts/check-skill-token-budget.py [--root DIR] [--self-test]

Exit codes: 0 = clean, 1 = violation(s) found.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Claude Code re-attaches the first 5,000 tokens of each invoked skill after compaction.
TOKEN_BUDGET = 5000

# Rule-of-thumb tokenizer: English/code ~4.4 chars per token, CJK ~1.2 tokens per char.
# The 1.2 matters: at 1.0 the estimate ran 9% under on Hangul-dense skills, which is the
# direction that lets a genuinely over-budget file pass.
ASCII_CHARS_PER_TOKEN = 4.4
NON_ASCII_TOKENS_PER_CHAR = 1.2

# Content that must survive compaction. `## Rules` is where both offending skills park their
# invariants; `AskUserQuestion` is how a skill asks for confirmation, so its every occurrence
# is a gate. Both are literal, greppable anchors — no heuristic guessing at "is this a gate".
RULES_HEADING_RE = re.compile(r"^#{2,}\s+Rules\s*$", re.MULTILINE)
GATE_TOKEN = "AskUserQuestion"


try:  # accurate path — CI installs it; absent on a bare machine
    import tiktoken

    _ENCODING = tiktoken.get_encoding("o200k_base")
    BACKEND = "o200k_base"
except Exception:  # ImportError, or a BPE download failure on first use
    _ENCODING = None
    BACKEND = "char-estimate"


def backend_verdict(backend: str, allow_estimate: bool):
    """Return (exit_code, message) for a backend choice. None exit code = proceed."""
    if backend == "o200k_base":
        return None, ""
    if allow_estimate:
        return None, (
            "NOTE: counting with the char-class ESTIMATE (0.86x-1.14x measured error) because "
            "tiktoken is unavailable. Indicative only — not the gate CI applies."
        )
    return 2, (
        "FATAL: tiktoken is unavailable, so this guard cannot measure and will not report a "
        "verdict.\n  Reproduce the CI run:  uv run --with tiktoken python3 "
        "scripts/check-skill-token-budget.py\n  Or accept an indicative estimate:  "
        "python3 scripts/check-skill-token-budget.py --allow-estimate"
    )


def measure(text: str) -> float:
    """Token count via the best available backend."""
    if _ENCODING is not None:
        return float(len(_ENCODING.encode(text)))
    return _estimate_tokens(text)


def _estimate_tokens(text: str) -> float:
    """Dependency-free fallback. See the module docstring for its measured error band."""
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    return (
        ascii_chars / ASCII_CHARS_PER_TOKEN
        + (len(text) - ascii_chars) * NON_ASCII_TOKENS_PER_CHAR
    )


FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def find_anchors(text: str):
    """Yield (label, offset_in_tokens) for every compaction-critical anchor.

    The frontmatter is skipped: `allowed-tools: ... AskUserQuestion` declares a capability, not
    a confirmation gate, and counting it made every skill look like it had one.
    """
    fm = FRONTMATTER_RE.match(text)
    body_start = fm.end() if fm else 0
    prefix, text = text[:body_start], text[body_start:]
    base = measure(prefix) if prefix else 0.0
    line_offset = prefix.count("\n")
    for match in RULES_HEADING_RE.finditer(text):
        yield match.group(0).strip(), base + measure(text[: match.start()])
    start = 0
    while (idx := text.find(GATE_TOKEN, start)) != -1:
        line = line_offset + text.count("\n", 0, idx) + 1
        yield f"{GATE_TOKEN} (line {line})", base + measure(text[:idx])
        start = idx + len(GATE_TOKEN)


def check_text(text: str):
    """Return (total_tokens, [violation strings]) for one SKILL.md body."""
    total = measure(text)
    violations = []
    if total > TOKEN_BUDGET:
        violations.append(
            f"over budget: ~{total:.0f} tokens > {TOKEN_BUDGET} "
            f"({total / TOKEN_BUDGET:.2f}x) — the tail is dropped after compaction"
        )
    for label, offset in find_anchors(text):
        if offset > TOKEN_BUDGET:
            violations.append(
                f"compaction-critical anchor past the boundary: {label} "
                f"starts at ~{offset:.0f} tokens"
            )
    return total, violations


def _git_toplevel() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def check(root: Path):
    """Scan source plugins only (a directory holding .claude-plugin/plugin.json)."""
    results = []
    for manifest in sorted(root.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent
        for skill in sorted(plugin.glob("skills/*/SKILL.md")):
            text = skill.read_text(encoding="utf-8")
            total, violations = check_text(text)
            results.append((skill.relative_to(root), total, violations))
    return results


_CLEAN = "# Skill\n\nShort body.\n\n## Rules\n\n- Stay small.\n"
_BIG_ASCII = "word " * 30000  # ~34k tokens of filler, well past the budget


def run_self_test() -> int:
    cases = [
        ("clean file", _CLEAN, 0),
        ("over budget, no anchors", _BIG_ASCII, 1),
        # Budget violation only: the file is huge but its gate sits in the first lines.
        ("over budget, early gate", "AskUserQuestion\n" + _BIG_ASCII, 1),
        # Budget + anchor violations: the same content with the gate pushed past 5,000.
        ("over budget, late gate", _BIG_ASCII + "\nAskUserQuestion\n", 2),
        ("over budget, late Rules heading", _BIG_ASCII + "\n## Rules\n", 2),
    ]
    failures = []
    for name, text, expected in cases:
        _, violations = check_text(text)
        if len(violations) != expected:
            failures.append(f"{name}: expected {expected} violation(s), got {len(violations)}: {violations}")

    # The estimator itself: a pure-ASCII string and a pure-Hangul string must land on the
    # documented constants, or the calibration in the docstring silently stops describing it.
    if abs(_estimate_tokens("a" * 4400) - 1000) > 1:
        failures.append("estimator: 4,400 ASCII chars should be ~1,000 tokens")
    if abs(_estimate_tokens("가" * 1000) - 1200) > 1:
        failures.append("estimator: 1,000 Hangul chars should be ~1,200 tokens")

    # A file just under the budget passes; one just over fails. Built by bisection against the
    # ACTIVE backend, so the case pins the boundary under tiktoken and under the estimator alike.
    unit = "landfill policy word "
    hi = 1
    while measure(unit * hi) <= TOKEN_BUDGET:
        hi *= 2
    lo = hi // 2
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if measure(unit * mid) <= TOKEN_BUDGET:
            lo = mid
        else:
            hi = mid
    if check_text(unit * lo)[1]:
        failures.append("boundary: a file just under the budget must pass")
    if not check_text(unit * hi)[1]:
        failures.append("boundary: a file just over the budget must fail")

    # The backend gate is the #447 failure class turned on itself: an unmeasurable run must
    # refuse a verdict, not quietly downgrade to a backend this guard calls insufficient.
    for backend, allow, expected in [
        ("o200k_base", False, None),
        ("o200k_base", True, None),
        ("char-estimate", False, 2),
        ("char-estimate", True, None),
    ]:
        code, msg = backend_verdict(backend, allow)
        if code != expected:
            failures.append(f"backend gate ({backend}, allow={allow}): expected {expected}, got {code}")
        if backend == "char-estimate" and not msg:
            failures.append(f"backend gate ({backend}, allow={allow}): must say something")

    # `allowed-tools: ... AskUserQuestion` in the frontmatter is a capability, not a gate.
    fm_only = "---\nname: x\nallowed-tools: Read AskUserQuestion\n---\n\n# Body\n"
    if list(find_anchors(fm_only)):
        failures.append("frontmatter AskUserQuestion must not count as a gate")
    if len(list(find_anchors(fm_only + "\nAskUserQuestion\n"))) != 1:
        failures.append("a body AskUserQuestion must still count as a gate")

    # Anchor OFFSET math, not just the threshold: an anchor must report the token distance from
    # the start of the FILE (frontmatter included), so a wrong base would misplace every gate.
    body = unit * lo
    anchors = dict(find_anchors(fm_only.rstrip("\n") + "\n" + body + "\n## Rules\n"))
    reported = anchors.get("## Rules")
    expected_at = measure(fm_only.rstrip("\n") + "\n" + body)
    if reported is None or abs(reported - expected_at) > max(2.0, expected_at * 0.01):
        failures.append(
            f"anchor offset: ## Rules should report ~{expected_at:.0f}, got {reported}"
        )

    if failures:
        print(f"FAIL: {len(failures)} check-skill-token-budget self-test case(s) failed", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"OK: all {len(cases) + 12} check-skill-token-budget self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true", help="run in-memory fixtures")
    parser.add_argument("--list", action="store_true", help="print every file's count and anchors")
    parser.add_argument(
        "--allow-estimate",
        action="store_true",
        help="proceed with the char-class estimate when tiktoken is unavailable (indicative only)",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    code, message = backend_verdict(BACKEND, args.allow_estimate)
    if message:
        print(message, file=sys.stderr)
    if code is not None:
        return code

    root = args.root or _git_toplevel()
    results = check(root)

    # A guard that finds nothing must not report success: a wrong --root or a moved
    # .claude-plugin/ layout would otherwise pass vacuously.
    if not results:
        print(
            f"FATAL: no SKILL.md found under {root} — expected */skills/*/SKILL.md inside a "
            f"directory holding .claude-plugin/plugin.json. Wrong --root, or the layout moved.",
            file=sys.stderr,
        )
        return 2

    if args.list:
        for rel, total, _ in results:
            text = (root / rel).read_text(encoding="utf-8")
            anchors = list(find_anchors(text))
            last = max((o for _, o in anchors), default=0)
            print(f"{str(rel):56} ~{total:5.0f} tok  anchors={len(anchors):2} last@~{last:.0f}")

    offenders = [(rel, total, v) for rel, total, v in results if v]
    if offenders:
        print(
            f"FAIL: {len(offenders)} SKILL.md exceed(s) the {TOKEN_BUDGET}-token compaction "
            f"re-attach window — content past it is dropped silently (#447):",
            file=sys.stderr,
        )
        for rel, _, violations in offenders:
            for line in violations:
                print(f"  {rel}: {line}", file=sys.stderr)
        print(
            "\nFix: move the rationale/narrative out to a reference doc the skill reads on "
            "demand; keep the gates and invariants in SKILL.md.",
            file=sys.stderr,
        )
        return 1

    worst = max(results, key=lambda r: r[1], default=None)
    worst_note = f"largest {worst[0]} at ~{worst[1]:.0f}" if worst else "none found"
    print(
        f"OK: skill-token-budget clean — {len(results)} SKILL.md checked, every one within "
        f"{TOKEN_BUDGET} tokens with its gates inside the window "
        f"[{BACKEND}] ({worst_note})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
