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

_FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:")

DESCRIPTION_CHAR_CAP = 1536  # harness listing-cap: changelog.md "raised the listing cap from 250 to 1,536 characters"


class _UnterminatedFrontmatter(Exception):
    """Raised by _description_span when a description: block scalar reads to EOF with no
    closing ---/... fence in sight — the frontmatter itself never closes."""


def _is_top_level_fence(line: str) -> bool:
    """True for a REAL frontmatter/block-scalar-closing fence: an UNINDENTED --- or ... .

    A block scalar's own content can legitimately contain an indented '---' or '...' line
    (a markdown rule, an embedded YAML example inside a description: | block) — only an
    unindented occurrence ends frontmatter or a block scalar, matching real YAML's
    indentation-based scoping. Checking `line.strip() in (...)` without this guard treats
    indented literal content as a fence and truncates the scan early (fresh-context review
    finding, reproduced live).

    Two other scripts read a frontmatter block on this same rule and each owns its own copy,
    because every check-*.py runs as a standalone CI line with no shared module between them:
    check-skill-reference-drift.py's identically-named helper, and check-type-optin.py's
    extract_frontmatter_keys. The bug was found live in all three, one at a time — fixing one
    copy is not fixing the rule, so change them together or not at all.
    """
    return line[:1] not in (" ", "\t") and line.strip() in ("---", "...")


def _description_span(text: str):
    """Raw description: VALUE text (key prefix stripped, quotes/block-scalar markers kept), or None.

    Mirrors scripts/check-skill-reference-drift.py's description_lines(): the block runs from the
    description: line to the next top-level frontmatter key or the closing ---/... fence. The
    "description:" key prefix on the first line is stripped (only the value after the colon is
    counted) — a DELIBERATE conservative raw-text approximation (#686): quotes/block markers stay
    in the count, so the measured total is always >= the harness's rendered listing length, never
    under it.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if _is_top_level_fence(lines[i]):
            return None
        if not lines[i].startswith("description:"):
            continue
        collected = [lines[i][len("description:"):]]
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if _is_top_level_fence(nxt) or _FRONTMATTER_KEY_RE.match(nxt):
                break
            collected.append(nxt)
        else:
            # EOF reached with no closing fence and no next key: frontmatter never closes, so
            # `collected` is bogus (the whole rest of the file, body included) rather than a
            # real description value. Without this guard the caller measured that whole-file
            # blob as the description's char count and reported "description is N chars",
            # which misdiagnoses a malformed file as an oversized one (#725-cluster).
            raise _UnterminatedFrontmatter("description: block never finds a closing fence")
        return "\n".join(collected).strip()
    return None


def _is_disabled(text: str) -> bool:
    """True when frontmatter sets disable-model-invocation: true (never listed, never truncated)."""
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return False
    return bool(re.search(r"^disable-model-invocation:\s*true\s*$", fm.group(0), re.MULTILINE))


def measure_descriptions(root: Path):
    """Return (results, malformed): results is (rel_path, char_count, is_skill) for every
    considered file whose frontmatter actually closes; malformed is the rel_path of every
    file whose frontmatter never closes (its description: value is unmeasurable garbage —
    the whole rest of the file — so it is reported as malformed instead of a bogus char count).

    Scope (#686): */skills/*/SKILL.md (is_skill=True) + */agents/*.md (is_skill=False) inside
    SOURCE plugins (dirs holding .claude-plugin/plugin.json) — same glob check() already uses.
    CLAUDE.md is excluded (no frontmatter, contributes nothing, and #686's own file-count table
    never includes it). disable-model-invocation: true files are excluded entirely. A file with
    no description: key contributes 0 chars but still appears (agents rarely carry one).
    """
    out = []
    malformed = []
    for manifest in sorted(root.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent
        for skill in sorted(plugin.glob("skills/*/SKILL.md")):
            text = skill.read_text(encoding="utf-8")
            if _is_disabled(text):
                continue
            try:
                span = _description_span(text)
            except _UnterminatedFrontmatter:
                malformed.append(skill.relative_to(root))
                continue
            out.append((skill.relative_to(root), len(span) if span else 0, True))
        for agent in sorted(plugin.glob("agents/*.md")):
            text = agent.read_text(encoding="utf-8")
            if _is_disabled(text):
                continue
            try:
                span = _description_span(text)
            except _UnterminatedFrontmatter:
                malformed.append(agent.relative_to(root))
                continue
            out.append((agent.relative_to(root), len(span) if span else 0, False))
    return out, malformed


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
    """Scan source plugins (skills/*/SKILL.md, agents/*.md) plus the repo's own CLAUDE.md."""
    results = []
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        text = claude_md.read_text(encoding="utf-8")
        total, violations = check_text(text)
        results.append((claude_md.relative_to(root), total, violations))
    for manifest in sorted(root.glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent
        for skill in sorted(plugin.glob("skills/*/SKILL.md")):
            text = skill.read_text(encoding="utf-8")
            total, violations = check_text(text)
            results.append((skill.relative_to(root), total, violations))
        for agent in sorted(plugin.glob("agents/*.md")):
            text = agent.read_text(encoding="utf-8")
            total, violations = check_text(text)
            results.append((agent.relative_to(root), total, violations))
    return results


_CLEAN = "# Skill\n\nShort body.\n\n## Rules\n\n- Stay small.\n"
_BIG_ASCII = "word " * 30000  # ~34k tokens of filler, well past the budget


def _write_fixture_plugin(root: Path, body: str) -> None:
    """A minimal source plugin, so the wiring cases never read the live tree."""
    plugin = root / "fixture-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "fixture-plugin"}')
    skill = plugin / "skills" / "x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body)
    agents = plugin / "agents"
    agents.mkdir(parents=True)
    (agents / "x.md").write_text(body)
    (root / "CLAUDE.md").write_text(body)


def _write_desc_fixture(root: Path, description: str, is_agent: bool = False) -> None:
    """A minimal source plugin with ONE file carrying the given raw description: value."""
    plugin = root / "fixture-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "fixture-plugin"}')
    fm = f"---\nname: x\ndescription: {description}\n---\n\nBody.\n"
    if is_agent:
        d = plugin / "agents"
        d.mkdir(parents=True, exist_ok=True)
        (d / "x.md").write_text(fm)
    else:
        d = plugin / "skills" / "x"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(fm)


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
        rels = {str(rel) for rel, _, _ in globals()["check"](Path(tmp))}
        check(
            rels == {"CLAUDE.md", "fixture-plugin/skills/x/SKILL.md", "fixture-plugin/agents/x.md"},
            f"scope (#473): expected CLAUDE.md + SKILL.md + agents/*.md, got {rels}",
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

    # WIRING, token-budget FAIL path: every other run_main case above feeds main() a clean or
    # description-only fixture, so nothing pinned that an over-budget file still reaches
    # `return 1`. That return sits under `if offenders or desc_offenders:` — one stray indent
    # into the desc_offenders branch and an over-budget SKILL.md exits 0 with this whole suite
    # green, which is the silent-guard-off class (#447) this file exists to catch. The same
    # case pins #686's other half: the description total must print on the FAIL path too, not
    # only ahead of `OK:`.
    # --allow-estimate, not a bare run: without it this case needs tiktoken importable, and on
    # a machine without it main() returns 2 at the backend gate, so all three checks below fail
    # with messages blaming the budget instead of the missing package. It is a no-op when
    # tiktoken IS present (backend_verdict passes o200k_base through), and _BIG_ASCII clears the
    # budget by orders of magnitude under either backend.
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixture_plugin(Path(tmp), _BIG_ASCII)
        rc, out = run_main(["--root", tmp, "--allow-estimate"])
        check(rc == 1, f"wiring: main() must exit 1 on a token-budget offender, got {rc}: {out}")
        check(f"exceed the {TOKEN_BUDGET}-token budget" in out,
              f"wiring: the token-budget FAIL must name the budget: {out}")
        check("description total:" in out,
              f"#686: the description total must print on the FAIL path too: {out}")

    # #686: description char-total measurement + per-skill 1,536-char cap.

    # Parser unit cases.
    check(_description_span('---\nname: x\ndescription: "abc"\n---\n') == '"abc"',
          "description span: quoted one-liner must keep quotes, drop key prefix")
    block = "---\nname: x\ndescription: |\n  line one\n  line two\nallowed-tools: Read\n---\n"
    check(_description_span(block) == "|\n  line one\n  line two",
          "description span: block scalar must stop before the next frontmatter key")
    check(_is_disabled("---\ndisable-model-invocation: true\n---\n") is True,
          "is_disabled: true must be detected")
    check(_is_disabled("---\nname: x\n---\n") is False,
          "is_disabled: absent key must be False")

    # Fence bug regression (fresh-context review, reproduced live): an INDENTED ---/...
    # inside a block scalar's own content must not be read as the fence that ends it —
    # only an UNINDENTED occurrence really ends a block scalar or frontmatter.
    indented_fence_in_description = (
        "---\ndescription: |\n  line one\n  ---\n  line three\nallowed-tools: Read\n---\n"
    )
    check(_description_span(indented_fence_in_description) == "|\n  line one\n  ---\n  line three",
          "description span: an indented --- inside a block scalar is content, not a fence")
    indented_fence_in_earlier_key = (
        '---\nallowed-tools: |\n  Read\n  ---\ndescription: "real trigger text"\n---\n'
    )
    check(_description_span(indented_fence_in_earlier_key) == '"real trigger text"',
          "description span: an indented --- inside an EARLIER key's block scalar must not "
          "be read as closing frontmatter before description: is reached")

    # EOF guard: a description: block scalar that never finds a closing fence must not read to
    # EOF and hand back the whole rest of the file as if it were the description value — that
    # silently mis-measures a malformed file as an oversized one. _description_span() must
    # flag the malformed frontmatter itself instead.
    never_closes = "---\nname: x\ndescription: |\n  line one\n\n## Rules\n\n- Stay small.\n"
    try:
        _description_span(never_closes)
        check(False, "description span: unterminated frontmatter must raise, not return a value")
    except _UnterminatedFrontmatter:
        check(True, "description span: unterminated frontmatter raises")

    with tempfile.TemporaryDirectory() as tmp:
        _write_desc_fixture(Path(tmp), '"short"')
        broken = Path(tmp, "fixture-plugin", "skills", "x", "SKILL.md")
        broken.write_text(never_closes)
        measured, malformed = measure_descriptions(Path(tmp))
        check((measured, [str(p) for p in malformed]) == ([], ["fixture-plugin/skills/x/SKILL.md"]),
              f"description sum: an unterminated file is reported malformed, not measured — "
              f"got measured={measured} malformed={malformed}")
        rc, out = run_main(["--root", tmp, "--allow-estimate"])
        check(rc == 1, f"wiring: an unterminated frontmatter must FAIL, got rc={rc}: {out}")
        check("frontmatter never closes" in out,
              f"wiring: the FAIL must name the real problem, not a char count: {out}")
        check("description is" not in out,
              f"wiring: an unterminated file must not print a bogus 'description is N chars': {out}")

    # Sum case (#686 "합산 1건").
    with tempfile.TemporaryDirectory() as tmp:
        _write_desc_fixture(Path(tmp), '"short"')
        measured, malformed = measure_descriptions(Path(tmp))
        expected_len = len('"short"')
        check(len(measured) == 1 and measured[0][1] == expected_len and not malformed,
              f"description sum: expected 1 entry of {expected_len} chars, got {measured}")

    # is_agent path (#686 scope: description totals include agents/*.md, but the 1,536-char
    # cap applies to SKILL.md only) — was never exercised (fresh-context review finding).
    with tempfile.TemporaryDirectory() as tmp:
        _write_desc_fixture(Path(tmp), '"agent desc"', is_agent=True)
        measured, _ = measure_descriptions(Path(tmp))
        check(len(measured) == 1 and measured[0][2] is False,
              f"description sum: agent file measured with is_skill=False (got: {measured})")
    with tempfile.TemporaryDirectory() as tmp:
        over_cap_agent_desc = '"' + "x" * (DESCRIPTION_CHAR_CAP - 1) + '"'
        _write_desc_fixture(Path(tmp), over_cap_agent_desc, is_agent=True)
        rc, out = run_main(["--root", tmp, "--allow-estimate"])
        check(rc == 0,
              f"description boundary: an agent description over {DESCRIPTION_CHAR_CAP} chars "
              f"must NOT fail (cap is SKILL.md-only, #686 scope (2)), got rc={rc}: {out}")

    # 1,536-char boundary, 2 cases (#686 "1,536 경계 2건").
    with tempfile.TemporaryDirectory() as tmp:
        desc = '"' + "x" * (DESCRIPTION_CHAR_CAP - 2) + '"'
        _write_desc_fixture(Path(tmp), desc)
        rc, out = run_main(["--root", tmp, "--allow-estimate"])
        check(rc == 0, f"description boundary: exactly {DESCRIPTION_CHAR_CAP} chars must pass, got rc={rc}: {out}")
    with tempfile.TemporaryDirectory() as tmp:
        desc = '"' + "x" * (DESCRIPTION_CHAR_CAP - 1) + '"'
        _write_desc_fixture(Path(tmp), desc)
        rc, out = run_main(["--root", tmp, "--allow-estimate"])
        check(rc == 1, f"description boundary: {DESCRIPTION_CHAR_CAP + 1} chars must fail, got rc={rc}: {out}")
        check(str(DESCRIPTION_CHAR_CAP) in out,
              f"description boundary: FAIL output must name {DESCRIPTION_CHAR_CAP}: {out}")

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
    results = check(root)

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

    desc_results, desc_malformed = measure_descriptions(root)
    total_desc_chars = sum(c for _, c, _ in desc_results)
    print(
        f"description total: {total_desc_chars} chars across {len(desc_results)} file(s) "
        f"(SKILL.md + agents/*.md description:, disable-model-invocation excluded)"
    )
    # This is the always-loaded axis only — the smallest of three real cost axes (a session's
    # own judgment, not #686's original scope): per-file BODY size is the token count this
    # script already prints per file (see --list, or "largest ... at ~N" below), and ACTUAL
    # invocation count lives in feedback-loop/scripts/report.py's skill_lifecycle_view (skills)
    # / agent_spawn_distribution_view (agents). Reading only the number above reads the
    # smallest surface — the other two answer "does this size actually matter in practice".
    print(
        "  ! description chars is the always-loaded axis only — per-file body size is this "
        "script's own token count (--list), actual invocation count is in "
        "feedback-loop/scripts/report.py (skill_lifecycle_view / agent_spawn_distribution_view)"
    )
    desc_offenders = [(rel, c) for rel, c, is_skill in desc_results if is_skill and c > DESCRIPTION_CHAR_CAP]

    if args.list:
        for rel, total, _ in results:
            text = (root / rel).read_text(encoding="utf-8")
            anchors = list(find_anchors(text))
            last = max((o for _, o in anchors), default=0)
            print(f"{str(rel):56} ~{total:5.0f} tok  anchors={len(anchors):2} last@~{last:.0f}")

    offenders = [(rel, total, v) for rel, total, v in results if v]
    if offenders or desc_offenders or desc_malformed:
        if desc_malformed:
            print(
                f"FAIL: {len(desc_malformed)} file(s) have frontmatter that never closes — no "
                f"unindented ---/... fence found before EOF, so description: cannot be measured:",
                file=sys.stderr,
            )
            for rel in desc_malformed:
                print(f"  {rel}: frontmatter never closes", file=sys.stderr)
            print("\nFix: close the frontmatter with an unindented --- or ....", file=sys.stderr)
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
                "(a reference.md for a skill, docs/REFERENCE.md for CLAUDE.md, the owning plugin's "
                "own reference doc for agents/*.md); keep gates and invariants in place. Always "
                "split, never trim.",
                file=sys.stderr,
            )
        if desc_offenders:
            print(
                f"FAIL: {len(desc_offenders)} SKILL.md description(s) exceed the "
                f"{DESCRIPTION_CHAR_CAP}-char harness listing cap — trigger text past it is "
                f"silently truncated from the model's skill listing (#686):",
                file=sys.stderr,
            )
            for rel, c in desc_offenders:
                print(f"  {rel}: description is {c} chars (> {DESCRIPTION_CHAR_CAP})", file=sys.stderr)
            print("\nFix: shorten the description — text past the cap never reaches the model.", file=sys.stderr)
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
