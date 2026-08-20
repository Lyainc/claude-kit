#!/usr/bin/env python3
"""check-skill-token-budget.py — always-loaded/always-attached instruction files stay under budget.

RULE (deterministic): every `*/skills/*/SKILL.md`, every `*/agents/*.md` in a source plugin,
and the repo's own `CLAUDE.md` must count at most 5,000 tokens each. For SKILL.md specifically,
every compaction-critical anchor inside it (the `## Rules` heading, each `AskUserQuestion` in
the BODY) must also sit inside that same 5,000-token prefix.

SCOPE (#473): CLAUDE.md and agents/*.md were added to a guard that originally covered only
SKILL.md (#454/#461). The rationale differs by file — SKILL.md's is the compaction re-attach
window below; CLAUDE.md's is dilution (an always-loaded prefix that, left unguarded, only ever
grows, and every added line taxes compliance with every other instruction in the file —
measured live: obsidian-mind's CLAUDE.md swelled to 36KB/~9-10k tokens with no budget guarding
it). agents/*.md sits between the two: not proven to hit the compaction window the way SKILL.md
does, but resident for a run's duration the same way. Rather than invent a second number without
a measurement to justify it, all three share the existing 5,000-token line: agents/*.md already
passed it going in (5 files, 1,481-4,648 tokens, #473's own survey), so extending the guard to
them cost nothing; CLAUDE.md was the one file over (5,510), and came down by moving lookup-only
sections to docs/ (see docs/REFERENCE.md's abandon-priority table) rather than by trimming
content — `check()` runs the anchor check uniformly on all three file kinds (no kind-based
gating), but it only ever fires meaningfully on SKILL.md: `## Rules`/`AskUserQuestion` name a
SKILL.md gate specifically, CLAUDE.md/agents/*.md carry neither, and any anchor one of those two
did contain past the boundary would already be subsumed by that file's own over-budget
violation (see WHY BOTH CHECKS below).

OBJECTIVE DAMAGE (#447, not taste): Claude Code keeps an invoked skill's body in context
across turns, and auto-compaction re-attaches only **the first 5,000 tokens of each skill**.
Everything past that is dropped, and dropped silently — no error, no warning, no STATE
trace. Measured on 2026-07-30, `add-policy` (7,322 tok) lost `## 8. Post-write self-check`
and `## Rules`; `audit` (7,419 tok) lost `## Phase 4 — OPTIONAL-FIX` — the E2 auto-fix
**user confirmation gate** — and `## Rules`. Invoke either skill a second time in a
compacted session and it runs with its safety gate missing from the instructions, producing
output indistinguishable from a correct run. Same failure class as #443/#433: a safeguard
turns itself off quietly.

HOW IT COUNTS: `tiktoken`'s `o200k_base`, and nothing else. #454 preferred a dependency-free
byte/char proxy, and that was tried first — it does not work. Fitted over this repo's
SKILL.md + reference/*.md files, the best two-parameter char model still lands anywhere in
0.86x-1.14x of the real count, because markdown structure (tables, fences, URLs) drives
tokenization more than character class does. At that width the guard passed `add-policy` at a
measured 5,304 tokens and `audit` at 5,286 — both genuinely over — while reporting them as
~4,990 and ~4,870. A guard that cannot tell 5,300 from 4,900 is not guarding.

tiktoken is not installed anywhere: both `docs/VALIDATION.md` and `.github/workflows/validate.yml`
invoke this script through `uv run --with tiktoken`, which fetches it for that one command, so
it is a dependency of this guard and of no plugin. CI and local therefore run the identical
line, on purpose — see the exit-2 rule below for why they must not be able to drift.

`o200k_base` is NOT Claude's tokenizer, and that caveat is real: expect the true Claude count
to sit within roughly ±10-20% of what this reports. It is, however, the tokenizer #447's own
measurements were taken with, so the numbers here are comparable to the ones in that issue.
The budget is left at a flat 5,000 rather than discounted for that uncertainty — the fix for a
file near the line is to move rationale out, not to tune the threshold. Two consequences worth
knowing before you edit a skill that is already close: a pass at 4,990 is NOT proof the real
Claude count is under 5,000, and a file with only tens of tokens of headroom turns the next
one-paragraph edit into a CI failure. After the #447 split the three fixed files sat at
4,930 / 4,840 / 4,753 — 1.4% to 4.9% of headroom, deliberately not more, because the material
left in them is contract text pinned by regression suites rather than prose that can be moved.
#450/#429 then added two features to `add-policy` and paid for them by moving rationale to its
reference.md, landing at 4,936 — the same 1.3% of headroom, not a raised ceiling.
Treat a CI failure on one of them as "move rationale out", never as "raise the number".

There IS a char-class estimator (~4.4 ASCII chars per token, ~1.2 tokens per non-ASCII char),
but it is never reached by accident. Without `tiktoken` the real mode **exits 2 and refuses to
report a verdict at all**, because a guard that quietly degrades to a backend this file just
called "not guarding" is the same silent-safeguard-off failure #447 is about. `--allow-estimate`
is the only way in; it labels the run on stderr and stays non-authoritative.

ponytail: `## Rules` is the only invariant heading recognised, so skills that park invariants
under another name (`## Core Principle`, `### Constraints`) get the budget check but not the
anchor check. Widening the heading list is the upgrade if a gate is ever found under one.

WHY BOTH CHECKS: the budget check subsumes the anchor check today (a file under budget
cannot have an anchor past the boundary). The anchor check is still reported, because it is
the claim #447 actually makes — it names WHICH gate survives compaction, and it keeps its
meaning if the budget is ever raised or scoped.

Usage:
    uv run --with tiktoken python3 scripts/check-skill-token-budget.py
        [--root DIR] [--list] [--self-test] [--allow-estimate]

Exit codes: 0 = clean, 1 = violation(s) found, 2 = cannot measure (no tiktoken and no
--allow-estimate) or nothing to measure (no SKILL.md under --root).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Claude Code re-attaches the first 5,000 tokens of each invoked skill after compaction.
TOKEN_BUDGET = 5000

# Harness skill-listing truncation cap (`~/.claude/cache/changelog.md:2647`: "raised the
# listing cap from 250 to 1,536 characters and added a startup warning when descriptions are
# truncated"). Past it, trailing trigger phrases fall out of the model's skill listing while
# check-trigger-regression.py still reads the file text and stays green — same silent-
# safeguard-off shape as #447, applied to SKILL.md `description:` (#686). SKILL.md only: the
# changelog names the skill listing specifically, not agents/*.md.
DESCRIPTION_CHAR_BUDGET = 1536

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


try:  # the only counting path; `uv run --with tiktoken` supplies it at both call sites
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
    """Exact token count, or the estimate when `--allow-estimate` let an unmeasurable run in."""
    if _ENCODING is not None:
        return float(len(_ENCODING.encode(text)))
    return _estimate_tokens(text)


def _estimate_tokens(text: str) -> float:
    """Indicative count for `--allow-estimate` only. See the docstring for its error band."""
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    return (
        ascii_chars / ASCII_CHARS_PER_TOKEN
        + (len(text) - ascii_chars) * NON_ASCII_TOKENS_PER_CHAR
    )


FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:")
DISABLE_INVOCATION_RE = re.compile(r"^disable-model-invocation:\s*true\s*$", re.MULTILINE)


def description_text(text: str):
    """Raw `description:` value from frontmatter, per #686's measurement protocol.

    Everything from right after the `description:` key through the line before the next
    top-level key (or the closing `---`), joined with newlines and `strip()`ped. Covers the
    three shapes this repo's files use — quoted one-liner, `|`/`>-` block scalar, plain
    continuation — without a YAML parser, following `check-skill-reference-drift.py`'s
    `description_lines()` precedent. The count is intentionally the raw YAML text (quotes,
    block markers, indentation included), always >= the rendered value the harness truncates
    on, so a gate on this number fires no later than the harness would. Returns None when
    there is no frontmatter or no `description:` key.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        # Unindented only: a real fence/document-end marker sits at column 0 (same as
        # FRONTMATTER_RE's literal `^---\n`). `.strip()` here would also fire on an indented
        # `description: |` block-scalar line that merely CONTAINS the text "---" or "...".
        if lines[i].rstrip() in ("---", "..."):
            return None
        if not lines[i].startswith("description:"):
            continue
        parts = [lines[i][len("description:"):]]
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if nxt.rstrip() in ("---", "...") or FRONTMATTER_KEY_RE.match(nxt):
                break
            parts.append(nxt)
        return "\n".join(parts).strip()
    return None


def is_disabled_invocation(text: str) -> bool:
    """True when frontmatter sets `disable-model-invocation: true` — no listing/trigger
    surface exists, so the file is excluded from both the description sum and the
    per-skill char budget (#686)."""
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return False
    return bool(DISABLE_INVOCATION_RE.search(fm.group(0)))


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


def _iter_files(root: Path):
    """Yield (kind, rel_path, text) for CLAUDE.md + every source-plugin SKILL.md/agents/*.md.

    Read once in main() into a list; check() and description_stats() (#686) both consume
    that same list, so the two guards can never scan a different file set from each other
    and no file is read from disk twice.
    """
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        yield "claude_md", claude_md.relative_to(root), claude_md.read_text(encoding="utf-8")
    for manifest in sorted(root.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent
        for skill in sorted(plugin.glob("skills/*/SKILL.md")):
            yield "skill", skill.relative_to(root), skill.read_text(encoding="utf-8")
        for agent in sorted(plugin.glob("agents/*.md")):
            yield "agent", agent.relative_to(root), agent.read_text(encoding="utf-8")


def check(files):
    """Token-budget check over an already-read [(kind, rel_path, text), ...] list."""
    results = []
    for _, rel, text in files:
        total, violations = check_text(text)
        results.append((rel, total, violations))
    return results


def description_stats(files):
    """Sum `description:` chars across the same [(kind, rel_path, text), ...] list check() scans
    (#686).

    A file with `disable-model-invocation: true` is excluded entirely (no listing surface to
    guard); one with no frontmatter or no `description:` key contributes 0 — CLAUDE.md always
    falls in the latter, and is also structurally never a skill/agent, so it never enters
    either bucket below. Returns (skill_count, skill_chars, agent_count, agent_chars,
    skill_violations), where skill_violations lists (rel, chars) for every SKILL.md over
    DESCRIPTION_CHAR_BUDGET — the harness skill-listing truncation cap; agents/*.md carry no
    equivalent evidence, so they are summed but never flagged.
    """
    skill_count = skill_chars = agent_count = agent_chars = 0
    skill_violations = []
    for kind, rel, text in files:
        if kind == "claude_md" or is_disabled_invocation(text):
            continue
        desc = description_text(text)
        if desc is None:
            continue
        n = len(desc)
        if kind == "skill":
            skill_count += 1
            skill_chars += n
            if n > DESCRIPTION_CHAR_BUDGET:
                skill_violations.append((rel, n))
        else:  # agent
            agent_count += 1
            agent_chars += n
    return skill_count, skill_chars, agent_count, agent_chars, skill_violations


_CLEAN = "# Skill\n\nShort body.\n\n## Rules\n\n- Stay small.\n"
_BIG_ASCII = "word " * 30000  # ~34k tokens of filler, well past the budget


def _write_fixture_plugin(root: Path, body: str, skill_body=None, agent_body=None) -> None:
    """A minimal source plugin, so the wiring cases never read the live tree.

    `skill_body`/`agent_body` override `body` for just that file — the #686 description
    cases need SKILL.md and agents/x.md to carry different frontmatter, since a description
    over budget in one must not spuriously also count on the other.
    """
    plugin = root / "fixture-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "fixture-plugin"}')
    skill = plugin / "skills" / "x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body if skill_body is None else skill_body)
    agents = plugin / "agents"
    agents.mkdir(parents=True)
    (agents / "x.md").write_text(body if agent_body is None else agent_body)
    (root / "CLAUDE.md").write_text(body)


def run_self_test() -> int:
    failures = []
    checks = 0

    def check(ok: bool, msg: str) -> None:
        """Every assertion goes through here, so the printed count cannot drift from reality."""
        nonlocal checks
        checks += 1
        if not ok:
            failures.append(msg)

    for name, text, expected in [
        ("clean file", _CLEAN, 0),
        ("over budget, no anchors", _BIG_ASCII, 1),
        # Budget violation only: the file is huge but its gate sits in the first lines.
        ("over budget, early gate", "AskUserQuestion\n" + _BIG_ASCII, 1),
        # Budget + anchor violations: the same content with the gate pushed past 5,000.
        ("over budget, late gate", _BIG_ASCII + "\nAskUserQuestion\n", 2),
        ("over budget, late Rules heading", _BIG_ASCII + "\n## Rules\n", 2),
    ]:
        violations = check_text(text)[1]
        check(len(violations) == expected,
              f"{name}: expected {expected} violation(s), got {len(violations)}: {violations}")

    # The estimator's own constants: if these drift, the docstring's calibration stops
    # describing the code and `--allow-estimate` quietly means something else.
    check(abs(_estimate_tokens("a" * 4400) - 1000) <= 1,
          "estimator: 4,400 ASCII chars should be ~1,000 tokens")
    check(abs(_estimate_tokens("가" * 1000) - 1200) <= 1,
          "estimator: 1,000 Hangul chars should be ~1,200 tokens")

    # A file just under the budget passes, one just over fails. Bisected against the ACTIVE
    # backend, so the case pins the boundary under tiktoken and under the estimator alike.
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
    check(not check_text(unit * lo)[1], "boundary: a file just under the budget must pass")
    check(bool(check_text(unit * hi)[1]), "boundary: a file just over the budget must fail")

    # The backend gate is the #447 failure class turned on itself: an unmeasurable run must
    # refuse a verdict, not quietly downgrade to a backend this guard calls insufficient.
    for backend, allow, expected in [
        ("o200k_base", False, None),
        ("o200k_base", True, None),
        ("char-estimate", False, 2),
        ("char-estimate", True, None),
    ]:
        code, msg = backend_verdict(backend, allow)
        check(code == expected,
              f"backend gate ({backend}, allow={allow}): expected {expected}, got {code}")
        if backend == "char-estimate":
            check(bool(msg), f"backend gate ({backend}, allow={allow}): must say something")

    # `allowed-tools: ... AskUserQuestion` in the frontmatter is a capability, not a gate.
    fm_only = "---\nname: x\nallowed-tools: Read AskUserQuestion\n---\n\n# Body\n"
    check(not list(find_anchors(fm_only)),
          "frontmatter AskUserQuestion must not count as a gate")
    check(len(list(find_anchors(fm_only + "\nAskUserQuestion\n"))) == 1,
          "a body AskUserQuestion must still count as a gate")

    # Anchor OFFSET math, not just the threshold: an anchor reports its distance from the start
    # of the FILE, frontmatter included, so a wrong base misplaces every gate. The frontmatter is
    # deliberately large (a real `description:` runs hundreds of tokens) and the tolerance
    # absolute — with a 14-token stub and a percentage tolerance, zeroing the base still passed.
    big_fm = "---\nname: x\ndescription: " + ("policy word " * 400) + "\n---\n"
    reported = dict(find_anchors(big_fm + unit * lo + "\n## Rules\n")).get("## Rules")
    expected_at = measure(big_fm + unit * lo)
    check(reported is not None and abs(reported - expected_at) <= 2.0,
          f"anchor offset: ## Rules should report ~{expected_at:.0f}, got {reported} "
          f"(frontmatter contributes ~{measure(big_fm):.0f})")

    # Anchor THRESHOLD, separate from the budget boundary above: a gate past the line must be
    # named, one before it must not. Without this the comparison itself can drift unnoticed.
    filler = unit * (hi * 3)
    check(any("## Rules" in v for v in check_text(unit * (lo + 1) + "\n## Rules\n" + filler)[1]),
          "anchor threshold: a Rules heading past the budget must be named")
    check(not any("## Rules" in v for v in check_text("## Rules\n" + filler)[1]),
          "anchor threshold: a Rules heading at offset 0 must not be named")

    # WIRING: the refusals must be reachable from main(), not just correct as functions —
    # deleting either call from main() left this suite green before these cases existed. Each
    # runs against a tempdir fixture, never the live tree, so the suite stays hermetic and
    # cannot fail merely because it was invoked from outside a checkout.
    import contextlib
    import io
    import tempfile

    def run_main(argv):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
            return main(argv), buf.getvalue()

    with tempfile.TemporaryDirectory() as empty:
        rc, _ = run_main(["--root", empty])
        check(rc == 2, f"wiring: main() on a root with no SKILL.md must exit 2, got {rc}")

    # SCOPE (#473): check() must pick up CLAUDE.md and agents/*.md alongside SKILL.md, not
    # just the SKILL.md this guard originally covered.
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixture_plugin(Path(tmp), _CLEAN)
        rels = {str(rel) for rel, _, _ in globals()["check"](list(_iter_files(Path(tmp))))}
        check(
            rels == {"CLAUDE.md", "fixture-plugin/skills/x/SKILL.md", "fixture-plugin/agents/x.md"},
            f"scope (#473): expected CLAUDE.md + SKILL.md + agents/*.md, got {rels}",
        )

    # DESCRIPTION SUM + disable-model-invocation exclusion (#686): a SKILL.md description
    # counts, an agent description under disable-model-invocation does not — same fixture
    # pins both halves of the exclusion rule at once.
    skill_desc = "Fixture skill description for the #686 sum test."
    agent_desc = "Fixture agent description, excluded by disable-model-invocation (#686)."
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixture_plugin(
            Path(tmp), _CLEAN,
            skill_body=f"---\nname: x\ndescription: {skill_desc}\n---\n\n# Skill\n",
            agent_body=(
                f"---\nname: x\ndescription: {agent_desc}\n"
                f"disable-model-invocation: true\n---\n\n# Agent\n"
            ),
        )
        sc, schars, ac, achars, sviol = description_stats(list(_iter_files(Path(tmp))))
        check(
            (sc, schars, ac, achars, sviol) == (1, len(skill_desc), 0, 0, []),
            f"description sum (#686): expected (1, {len(skill_desc)}, 0, 0, []), "
            f"got {(sc, schars, ac, achars, sviol)}",
        )

    # DESCRIPTION_CHAR_BUDGET boundary (#686): a SKILL.md description at exactly the budget
    # passes; one char over fails and is named. An agent description past the SAME budget is
    # summed but never flagged — the changelog cap names the skill listing, not agents/*.md.
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixture_plugin(
            Path(tmp), _CLEAN,
            skill_body="---\nname: x\ndescription: " + "x" * DESCRIPTION_CHAR_BUDGET + "\n---\n",
        )
        _, _, _, _, sviol = description_stats(list(_iter_files(Path(tmp))))
        check(sviol == [], f"description boundary: a description AT the budget must pass, got {sviol}")

    with tempfile.TemporaryDirectory() as tmp:
        over = DESCRIPTION_CHAR_BUDGET + 1
        _write_fixture_plugin(
            Path(tmp), _CLEAN,
            skill_body="---\nname: x\ndescription: " + "x" * over + "\n---\n",
            agent_body="---\nname: x\ndescription: " + "x" * over + "\n---\n",
        )
        _, _, ac, achars, sviol = description_stats(list(_iter_files(Path(tmp))))
        check(
            len(sviol) == 1 and sviol[0][1] == over,
            f"description boundary: a description ONE OVER the budget must be named once "
            f"at {over} chars, got {sviol}",
        )
        check(
            ac == 1 and achars == over,
            f"description boundary: an over-budget agent description must still be summed, "
            f"got count={ac} chars={achars}",
        )
        rc, out = run_main(["--root", tmp])
        check(rc == 1, f"wiring (#686): main() with an over-budget description must exit 1, got {rc}")
        check(
            "DESCRIPTION TOTAL" in out,
            "wiring (#686): the description total line must print on the FAIL path too",
        )

    saved_backend, saved_encoding = globals()["BACKEND"], globals()["_ENCODING"]
    try:
        # Drop the encoding too, not just the label: otherwise --allow-estimate would still be
        # counting with tiktoken and the estimator path through main() would never run.
        globals()["BACKEND"], globals()["_ENCODING"] = "char-estimate", None
        with tempfile.TemporaryDirectory() as tmp:
            _write_fixture_plugin(Path(tmp), _CLEAN)
            rc, out = run_main(["--root", tmp])
            check(rc == 2, f"wiring: main() without an exact backend must exit 2, got {rc}")
            rc, out = run_main(["--root", tmp, "--allow-estimate"])
            check(rc == 0, f"wiring: --allow-estimate must let main() proceed, got {rc}")
            check("char-estimate" in out, "wiring: an estimated run must label itself")
    finally:
        globals()["BACKEND"], globals()["_ENCODING"] = saved_backend, saved_encoding

    if failures:
        print(f"FAIL: {len(failures)} check-skill-token-budget self-test case(s) failed", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"OK: all {checks} check-skill-token-budget self-test cases passed")
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
    files = list(_iter_files(root))  # one disk read per file, shared by every check below
    results = check(files)

    # A guard that finds nothing must not report success: a wrong --root or a moved
    # .claude-plugin/ layout would otherwise pass vacuously.
    if not results:
        print(
            f"FATAL: nothing to measure under {root} — expected a CLAUDE.md, or "
            f"*/skills/*/SKILL.md or */agents/*.md inside a directory holding "
            f".claude-plugin/plugin.json. Wrong --root, or the layout moved.",
            file=sys.stderr,
        )
        return 2

    if args.list:
        for (_, rel, text), (_, total, _) in zip(files, results):
            anchors = list(find_anchors(text))
            last = max((o for _, o in anchors), default=0)
            print(f"{str(rel):56} ~{total:5.0f} tok  anchors={len(anchors):2} last@~{last:.0f}")

    # #686: the description-char total prints unconditionally, on BOTH the OK and FAIL
    # paths below — hidden behind --list it would vanish from the flag-less CI call, and
    # printed only on the OK path it would go silent exactly when a budget is violated.
    skill_count, skill_chars, agent_count, agent_chars, skill_violations = description_stats(files)
    print(
        f"DESCRIPTION TOTAL: {skill_count} skill(s) {skill_chars} char(s) + "
        f"{agent_count} agent(s) {agent_chars} char(s) = {skill_chars + agent_chars} char(s) "
        f"(disable-model-invocation excluded)"
    )

    offenders = [(rel, total, v) for rel, total, v in results if v]
    if offenders or skill_violations:
        if offenders:
            print(
                f"FAIL: {len(offenders)} file(s) exceed the {TOKEN_BUDGET}-token budget — for "
                f"SKILL.md this is the compaction re-attach window, content past it is dropped "
                f"silently (#447); for CLAUDE.md/agents/*.md it is dilution (#473):",
                file=sys.stderr,
            )
            for rel, _, violations in offenders:
                for line in violations:
                    print(f"  {rel}: {line}", file=sys.stderr)
            print(
                "\nFix: move the rationale/narrative out to a doc the file points to on demand "
                "(a reference.md for a skill, docs/REFERENCE.md for CLAUDE.md, the owning "
                "plugin's own reference doc for agents/*.md); keep gates and invariants in "
                "place. Always split, never trim.",
                file=sys.stderr,
            )
        if skill_violations:
            print(
                f"FAIL: {len(skill_violations)} SKILL.md description(s) exceed the "
                f"{DESCRIPTION_CHAR_BUDGET}-char harness skill-listing truncation cap (#686):",
                file=sys.stderr,
            )
            for rel, n in skill_violations:
                print(f"  {rel}: description {n} chars > {DESCRIPTION_CHAR_BUDGET}", file=sys.stderr)
            print(
                "\nFix: trim the description — move rationale/examples to the skill body or "
                "reference.md; the trigger phrase itself must stay inside the harness's "
                f"{DESCRIPTION_CHAR_BUDGET}-char listing window.",
                file=sys.stderr,
            )
        return 1

    worst = max(results, key=lambda r: r[1], default=None)
    worst_note = f"largest {worst[0]} at ~{worst[1]:.0f}" if worst else "none found"
    print(
        f"OK: skill-token-budget clean — {len(results)} file(s) checked (SKILL.md/agents/*.md/"
        f"CLAUDE.md), every one within {TOKEN_BUDGET} tokens, SKILL.md gates inside the window "
        f"[{BACKEND}] ({worst_note})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
