#!/usr/bin/env python3
"""check-skill-reference-drift.py — a hardcoded skill name must resolve to a real skill (#637).

RULE: every reference of the form `Skill(skill: "<plugin>:<name>")` — and every `<plugin>:<name>`
token in a shell hook's matcher — must name a skill this repo actually ships, i.e. a
`<plugin>/skills/*/SKILL.md` whose frontmatter says `name: <name>`.

## Why this exists, and why an in-repo scan is not enough

#562 renamed `completion-condition` -> `next-goal`. Every reference INSIDE claude-kit was
updated; the one that crossed the repo boundary — local-harness's `skills/session-close/SKILL.md`,
which calls the skill by hardcoded qualified name — was not, and sat broken for 7 days before
being found by hand (local-harness `9ac0f03`). It stayed invisible for two compounding reasons:
`check-trigger-regression.py` and every sibling guard scan this checkout only, and the break
itself was latent — installs are pinned at v4.6.0 where the OLD name still resolves, so nothing
failed at runtime either. The documented fallback text had gone stale in the same edit, so the
recovery path pointed at the dead name too.

So the external consumer is not an optional extra surface, it is the whole point. EXTERNAL_ROOTS
is the configurable list; a root that does not exist is skipped silently, because no other
machine has local-harness checked out.

## Two failure modes, two matching rules

  CALL — `Skill(skill: "thinking-tools:next-goal")`. Fails loudly at runtime (`Unknown skill`),
    but only once an install carrying the rename is actually released.

  MATCHER — `case "$skill" in thinking-tools:next-goal|next-goal)` in a hook. Fails OPEN and
    SILENT: the case arm simply stops matching, the hook keeps exiting 0, and nothing anywhere
    reports that its whole reason for existing has been switched off.

## Why the scan is wider outside this repo than inside it

Inside claude-kit, only the call form (any file) and qualified names in `*.sh` (the matcher
surface) count. A qualified name in prose does NOT, and that asymmetry was measured, not assumed:
a repo-wide prose scan flags 6 mentions, and all 6 are legitimate past-tense records — a CHANGELOG
line for a retired skill, two dated `docs/discussions/**` transcripts, and a reference doc
explaining what a since-deleted agent used to be. Those are history, and history is allowed to
name dead things.

Outside, EVERY qualified `<plugin>:<name>` token counts, prose included. A consumer's skill file
is live instruction with no historical archive behind it, so a qualified name there is something
the model is being told to invoke however it is punctuated — which is exactly the shape of the
#562 break (the stale fallback sentence read "retry once as `thinking-tools:completion-condition`",
prose, no call syntax). Measured on the live external root: 3 references, 1 finding, and that one
is the deliberate bridge below.

One surface is scanned identically on both sides: a frontmatter `description:` block. The reason
in-repo prose is read narrowly is that history is allowed to name dead things, and a description
is not history — it is the live routing string the model reads, so a stale name there misroutes
just as it would in a consumer's file.

A bare (unqualified) name in a `Skill()` call is checked inside this repo only, where a sibling
skill is the only thing it can mean. Outside, a bare name is more often a machine-level skill this
repo knows nothing about, so it is skipped. A bare `subagent_type:` is different again (#719): the
harness's own built-in agents (`general-purpose`, `Explore`, `Plan`, `claude-code-guide`,
`statusline-setup`, `claude`) are the only things a bare agent name can mean, so those resolve and
nothing else does — this repo's catalogue only ever grants a `subagent_type:` in qualified
`<plugin>:<name>` form.

Agents are in the catalogue alongside skills: `<plugin>:<name>` is the qualified form for both,
so an agent reference must resolve rather than read as a dangling skill.

## The deliberate fallback

A rename that crosses this boundary can legitimately leave BOTH names live for a while: while
installs are pinned at a release predating the rename, only the OLD name resolves there, so a
consumer that names just one of them is wrong on one side of the release no matter which it
picks. local-harness's session-close carried exactly that bridge — a documented one-time retry
under the pre-#562 name — and dropped it once this guard existed. A bridge like that is not
drift, so DELIBERATE_FALLBACKS below exempts it, with the reason and the retirement condition
written next to the entry and never as a hidden special case.

The allowlist is self-cleaning: an entry that does NOT fire, while the file it names WAS scanned,
is reported as STALE. So the exemption cannot outlive its reason — which is not theoretical, it
is how the one entry this guard shipped with was retired, minutes after the bridge came out.

Usage:
    python3 scripts/check-skill-reference-drift.py [--root DIR] [--json] [--self-test]

    --root DIR    Repo root to check (default: git toplevel, else CWD).
    --json        Emit a machine-readable JSON report instead of text.
    --self-test   Run the matching logic against temp-directory fixtures and exit 0 only if
                  every case behaves as expected.

Exit codes: 0 = every reference resolves (or --self-test passed),
            1 = at least one dangling reference or stale exemption,
            2 = usage error / no plugins found to build a catalogue from.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

# Consumers outside this repo that hardcode claude-kit skill names. A path that does not exist
# is skipped silently — most machines have no local-harness checkout. `~` is expanded.
EXTERNAL_ROOTS = ["~/dev/prj/local-harness/skills"]

# (path suffix, "<plugin>:<name>", reason). A dangling reference matching an entry is exempt.
# Keyed by path suffix so an entry holds wherever the consumer happens to be checked out.
#
# Empty today, and that is a live fact rather than an unused hook: local-harness's session-close
# carried exactly one such entry — a documented one-time retry under the pre-#562 name, because
# installs were pinned at v4.6.0 where only the old name resolved — and dropped it once this
# guard existed to catch the next rename. An entry is warranted only for a bridge of that shape
# (both names deliberately live during a version skew); write the reason and the condition that
# retires it in the entry itself, the way that one read:
#
#   ("skills/session-close/SKILL.md", "thinking-tools:completion-condition",
#    "version-skew bridge: #562 renamed this on main but no tagged release carries the new "
#    "name yet. Remove once no pre-4.6.1 install remains."),
DELIBERATE_FALLBACKS = []

SCAN_EXTENSIONS = (".md", ".sh")
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}

# Matches `Skill(skill: "x")` and `Skill(skill: 'x', args: ...)` alike, plus the agent form
# `subagent_type: "<plugin>:<name>"`. Both are CALL surfaces for the same reason: the harness
# resolves the hardcoded name at spawn time and refuses an unknown one outright (measured
# 2026-08-31 — `Agent type '...' not found`, no spawn, no fallthrough), so a renamed or deleted
# agent breaks the caller loudly but only after a release carries the change. #706 wired the
# first two `subagent_type:` references in this repo, and they were the only qualified names
# here sitting outside every guard.
CALL_RE = re.compile(
    r"""(?:Skill\(\s*skill:|subagent_type:)\s*["']([^"']+)["']"""
)
NAME_KEY_RE = re.compile(r"^name:[ \t]*(\S+)", re.MULTILINE)

# The harness's own reserved bare agent names (#719). A plugin agent is only ever addressed in
# qualified `<plugin>:<name>` form — see every agent in this session's own catalogue — so a bare
# `subagent_type:` can mean one of these built-ins and nothing else. Checked against this fixed
# set instead of the plugin catalogue: a bare name that happens to collide with some plugin's
# skill (e.g. `subagent_type: "next-goal"`) is still wrong, since `Agent()` would resolve it as a
# built-in or fail, never as a bare lookup into this repo's skills.
HARNESS_BUILTIN_AGENTS = {
    "general-purpose", "Explore", "Plan", "claude-code-guide", "statusline-setup", "claude",
}

# An agent's `skills:` frontmatter list — the third hardcoded-name surface, and it fails the
# same way a hook matcher does: rename the skill and the entry simply stops granting anything,
# with no error and no log line. Structured, so it is parsed rather than pattern-matched off
# prose, which is why it carries none of the history/prose ambiguity the slash form below does.
#
# Parsed line by line rather than by one block regex. A `(?:…)+` block stops at the first item
# it cannot match, which does not merely skip that entry — it drops EVERY entry after it while
# the run still prints `OK: … resolve` with a plausible count. Measured: a quoted entry or a
# trailing `# comment` on the second item truncated the list silently. A half-scan reported as
# success is worse than no scan, because the count is the only signal a reader gets.
SKILLS_KEY_RE = re.compile(r"^skills:[ \t]*(.*)$")
# One list item: optional quotes, optional trailing comment. `---` cannot match, since a name
# must start alphanumeric.
SKILLS_ITEM_RE = re.compile(
    r"""^[ \t]*-[ \t]+(?:(["'])(?P<q>[A-Za-z0-9][A-Za-z0-9_-]*)\1"""
    r"""|(?P<b>[A-Za-z0-9][A-Za-z0-9_-]*))[ \t]*(?:\#.*)?$"""
)
# The inline flow form, `skills: [a, b]`.
SKILLS_FLOW_RE = re.compile(r"^\[(.*)\]$")

# A slash-command mention in an external consumer: `` `/next-goal` ``. The whole backtick span
# must be one path-free segment, so `` `/Users/x` `` and `` `skills/wrap/` `` cannot match.
SLASH_RE = re.compile(r"`/([a-z0-9][a-z0-9_-]*)`")

# The backtick requirement above buys precision in prose at the cost of one blind spot (#646):
# a SKILL.md frontmatter `description:` is prose where nobody writes backticks, so every skill
# named there was invisible. It is also the routing string the model reads, so a stale name
# there misroutes for real. Measured live: `skills/wrap/SKILL.md:3` names /wiki and /retro twice
# each with no backticks, and stayed green only because lines 29/45 happen to repeat them in
# backtick form — fix those two and the dead name in line 3 survives, which is the #562 shape.
#
# Inside the description block the backticks are dropped and the path guard moves into the
# pattern instead: a `/name` counts only when nothing word-like, slash-like, `~`, or `.` touches
# either end, so `/usr/bin`, `/Users/foo`, `skills/wrap/`, `~/vault`, `./scripts`, and `../lib`
# cannot match while `/wiki,` and `→ /retro` can. Safe here precisely because frontmatter is
# structured — the block is bounded, so this never widens to the free prose the backtick rule
# still governs.
#
# `~` and `.` were missing from the lookbehind at first, which read `~/vault` as the skill
# `vault` and `./scripts` as `scripts`. Only a trailing slash saved such a token, so one
# `~/vault` in any scanned description would have blocked every commit touching a SKILL.md.
BARE_SLASH_RE = re.compile(r"(?<![\w/~.])/([a-z0-9][a-z0-9_-]*)(?![\w/])")
# A top-level frontmatter key — i.e. the thing that ends a `description:` block. #686 added an
# identical regex under this same leading-underscore name to check-skill-token-budget.py, but
# only on an unmerged branch (not main, not this branch, as of this writing) — named to match
# now so that whichever PR lands second only has to delete its own copy, not rename anything.
_FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:")

# Slash names a scanned file may legitimately write that this repo does not ship. Without this
# the slash scan is unusable: measured on the live external root, 7 distinct slash names appear
# and 4 of them are of exactly these two kinds. Both kinds are permanent — a native command is
# never this repo's to declare, and a retired skill's history is allowed to name a dead thing,
# which is the same rule the in-repo prose exclusion already runs on. Named EXTERNAL_ for the
# consumer scan it was written for; it applies to in-repo descriptions too, since `/capture` and
# `/note` are named there by the very skill that replaced them.
EXTERNAL_SLASH_IGNORE = {
    # native Claude Code commands
    "goal": "native /goal completion conditions",
    "code-review": "native /code-review",
    # skills this repo retired; the mentions are past-tense records, not invocations
    "handoff": "retired; named only as the format session-close replaced",
    "capture": "retired by #480, superseded by /vault-save",
    "note": "retired by #480, superseded by /vault-save",
}


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build_catalog(root):
    """Return {plugin: {declared names}} from this repo's skills and agents."""
    catalog = {}
    patterns = (
        os.path.join(root, "*", "skills", "*", "SKILL.md"),
        os.path.join(root, "*", "agents", "*.md"),
    )
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            plugin = os.path.relpath(path, root).split(os.sep)[0]
            with open(path, encoding="utf-8", errors="replace") as fh:
                m = NAME_KEY_RE.search(fh.read())
            if m:
                catalog.setdefault(plugin, set()).add(m.group(1))
    return catalog


def qualified_re(plugins):
    """A `<plugin>:<name>` token, anchored on a plugin this repo actually ships.

    Anchoring on the known plugin list is what keeps this free of false positives: a generic
    `word:word` pattern would fire on YAML keys, URLs, and every `Trigger: ...` label.
    """
    if not plugins:
        return None
    alt = "|".join(re.escape(p) for p in sorted(plugins))
    return re.compile(r"\b(?:" + alt + r"):[A-Za-z0-9][A-Za-z0-9_-]*")


def scan_agent_skills(text):
    """Yield (lineno, name) for every entry of an agent's `skills:` frontmatter list.

    Walks the whole list instead of matching it as one block, so an entry this parser cannot
    read costs only that entry — never the rest of the list — and it never yields a name it
    did not actually read.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        key = SKILLS_KEY_RE.match(line)
        if not key:
            continue
        flow = SKILLS_FLOW_RE.match(key.group(1).strip())
        if flow:
            for entry in flow.group(1).split(","):
                entry = entry.strip().strip("\"'")
                if entry:
                    yield i + 1, entry
            return
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip() or nxt.lstrip().startswith("#"):
                continue  # a blank line or comment inside the list does not end it
            item = SKILLS_ITEM_RE.match(nxt)
            if not item:
                if nxt.lstrip().startswith("-"):
                    continue  # an item shape this parser cannot read: skip it, keep going
                return  # the next key, or the frontmatter fence — the list is over
            yield j + 1, item.group("q") or item.group("b")
        return


def _is_top_level_fence(line):
    """True for a REAL frontmatter/block-scalar-closing fence: an UNINDENTED --- or ... (#720).

    A `description: |`/`>-` block scalar's own content can legitimately contain an indented
    '---' or '...' line (a markdown rule, an embedded YAML example) — only an unindented
    occurrence ends frontmatter, matching real YAML's indentation-based scoping. Checking
    `line.strip() in (...)` without this guard treats indented literal content as a fence and
    truncates the scan early (found reviewing #686, which hit and fixed the same bug in
    check-skill-token-budget.py's own frontmatter scan).
    """
    return line[:1] not in (" ", "\t") and line.strip() in ("---", "...")


def description_lines(text):
    """Yield (lineno, line) for every line of the frontmatter `description:` block.

    Covers the three shapes this repo's SKILL.md files actually use — a quoted one-liner, a
    `>-`/`|` block scalar, and a plain unquoted continuation — by treating the block as "the
    `description:` line plus every line after it until the next top-level key or the closing
    fence". Nothing yielded outside frontmatter, so the backtick rule still owns the body.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return
    for i in range(1, len(lines)):
        if _is_top_level_fence(lines[i]):
            return  # frontmatter closed without a description
        if not lines[i].startswith("description:"):
            continue
        yield i + 1, lines[i]
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if _is_top_level_fence(nxt) or _FRONTMATTER_KEY_RE.match(nxt):
                return
            yield j + 1, nxt
        return


def scan_text(text, qual_re, wide, is_shell, is_agent=False):
    """Yield (lineno, ref, is_agent_call) for every skill/agent reference in one file's text.

    `wide` (external roots) counts every qualified token, prose included, plus the backtick-
    wrapped slash form. Inside the repo those are off, so only the call form, a shell file's
    matcher surface, and an agent's `skills:` list count.

    `is_agent_call` is True only for a `subagent_type:` match (#719): it is the one surface
    whose bare-name space is the harness's own built-in agents, never this repo's catalogue,
    so `resolve()` needs to know which rule applies to a given bare ref.

    The bare slash form inside a frontmatter `description:` block is scanned on BOTH sides. The
    reason in-repo prose is read narrowly — history is allowed to name dead things — does not
    reach a `description:`, which is not an archive but the live routing string the model reads.
    Measured in-repo: three descriptions name a skill of another plugin with no backticks and no
    second mention anywhere, so a rename would have gone through unseen — the #646 shape exactly.
    """
    if is_agent:
        for lineno, name in scan_agent_skills(text):
            yield lineno, name, False
    # Merged into the per-line `seen` set below rather than yielded separately, so a name
    # written BOTH ways on one description line is still one reference, not two.
    bare = {}
    for lineno, line in description_lines(text):
        bare.setdefault(lineno, set()).update(
            m.group(1) for m in BARE_SLASH_RE.finditer(line)
            if m.group(1) not in EXTERNAL_SLASH_IGNORE
        )
    for lineno, line in enumerate(text.splitlines(), 1):
        seen, agent_seen = set(), set()
        for m in CALL_RE.finditer(line):
            ref = m.group(1)
            # A QUALIFIED subagent_type ref resolves exactly like a qualified Skill() ref (the
            # `":" in ref` branch in resolve() never looks at agent_call), so it stays in `seen`
            # — critically, the SAME set qual_re also feeds on this line, so the two surfaces
            # matching the identical qualified token dedupe against each other as one reference,
            # not two. Only a BARE subagent_type is agent_call-only territory (#719): qual_re can
            # never match a bare token, so agent_seen never needs to dedupe against anything.
            if m.group(0).startswith("subagent_type") and ":" not in ref:
                agent_seen.add(ref)
            else:
                seen.add(ref)
        if qual_re is not None and (wide or is_shell):
            for m in qual_re.finditer(line):
                seen.add(m.group(0))
        if wide:
            for m in SLASH_RE.finditer(line):
                if m.group(1) not in EXTERNAL_SLASH_IGNORE:
                    seen.add(m.group(1))
        seen |= bare.get(lineno, set())
        for ref in sorted(seen):
            yield lineno, ref, False
        for ref in sorted(agent_seen):
            yield lineno, ref, True


def resolve(ref, catalog, allow_bare, extra_bare=(), agent_call=False):
    """Return None when the reference resolves, else a reason string.

    `extra_bare` is the scanned consumer's own skill names, and it applies only to references
    read from that consumer — never to in-repo ones, or the answer would depend on whether a
    sibling checkout happens to exist on the machine.

    `agent_call` marks a bare `subagent_type:` reference (#719): inside this repo its bare-name
    space is the harness's own built-in agents, never this repo's plugin catalogue — a plugin
    agent is only ever addressed in qualified `<plugin>:<name>` form, so a bare name colliding
    with some plugin's skill (e.g. `subagent_type: "next-goal"`) must still dangle in-repo, not
    resolve by coincidence. `extra_bare` is still honored here too: a scanned external consumer
    may have its own project-local agent this scanner cannot see, and denying that the same
    leniency a bare Skill() reference already gets there would be a new false positive on a
    surface #719 never asked to tighten.
    """
    if ":" in ref:
        plugin, _, name = ref.partition(":")
        if plugin not in catalog:
            return None  # another marketplace's plugin — not this repo's to judge
        if name in catalog[plugin]:
            return None
        # The catalogue holds skills AND agents, so name both — a `subagent_type:`
        # reference sent the reader to skills/ only, which is the wrong directory.
        return (f"no {plugin}/skills/*/SKILL.md or {plugin}/agents/*.md "
                f"declares `name: {name}`")
    if not allow_bare:
        return None
    if agent_call:
        if ref in HARNESS_BUILTIN_AGENTS or ref in extra_bare:
            return None
        return f"`{ref}` is not a harness built-in agent — subagent_type needs `<plugin>:<name>`"
    if ref in extra_bare or any(ref in names for names in catalog.values()):
        return None
    return f"no skill or agent named `{ref}` in any plugin"


def _display(path, root):
    if os.path.commonpath([os.path.abspath(path), root]) == root:
        return os.path.relpath(path, root)
    home = os.path.expanduser("~")
    return path.replace(home, "~", 1) if path.startswith(home) else path


def iter_files(top):
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(SCAN_EXTENSIONS):
                yield os.path.join(dirpath, fn)


def check_all(root, external_roots=None, allowlist=None):
    """Return (findings, stats). A finding is a dict with file/line/ref/problem."""
    root = os.path.abspath(root)
    external_roots = EXTERNAL_ROOTS if external_roots is None else external_roots
    allowlist = DELIBERATE_FALLBACKS if allowlist is None else allowlist
    catalog = build_catalog(root)
    qual_re = qualified_re(catalog.keys())

    surfaces = [(root, False)]
    absent = []
    for raw in external_roots:
        path = os.path.abspath(os.path.expanduser(raw))
        if os.path.isdir(path):
            surfaces.append((path, True))
        else:
            absent.append(raw)  # fail open: nobody else has this checked out

    # A consumer naming its OWN skill is not drift, so its declarations resolve too. Kept in a
    # SEPARATE set rather than merged into the catalogue: merging let an in-repo bare name
    # resolve against a skill this repo does not ship, which made the pre-commit hook laxer
    # than CI (where the consumer is absent) and the verdict machine-dependent.
    consumer_names = set()
    for top, wide in surfaces:
        if not wide:
            continue
        for path in glob.glob(os.path.join(top, "*", "SKILL.md")):
            with open(path, encoding="utf-8", errors="replace") as fh:
                m = NAME_KEY_RE.search(fh.read())
            if m:
                consumer_names.add(m.group(1))

    findings, fired, files, refs = [], set(), 0, 0
    scanned_paths = []
    for top, wide in surfaces:
        for path in iter_files(top):
            files += 1
            scanned_paths.append(path)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            is_agent = not wide and f"{os.sep}agents{os.sep}" in path and path.endswith(".md")
            for lineno, ref, is_agent_call in scan_text(
                text, qual_re, wide, path.endswith(".sh"), is_agent
            ):
                refs += 1
                problem = resolve(
                    ref, catalog, allow_bare=True,
                    extra_bare=consumer_names if wide else (),
                    agent_call=is_agent_call,
                )
                if problem is None:
                    continue
                exempt = next(
                    (e for e in allowlist if path.endswith(e[0]) and e[1] == ref), None
                )
                if exempt:
                    fired.add((exempt[0], exempt[1]))
                    continue
                findings.append({
                    "file": _display(path, root), "line": lineno,
                    "ref": ref, "problem": problem,
                })

    for suffix, ref, reason in allowlist:
        if (suffix, ref) in fired:
            continue
        # Only a scanned file can prove an entry is dead; an absent external root proves nothing.
        stale = [p for p in scanned_paths if p.endswith(suffix)]
        if stale:
            findings.append({
                "file": _display(stale[0], root), "line": 0, "ref": ref,
                "problem": f"stale exemption — nothing to exempt any more. Remove it: {reason}",
            })

    # The slash ignore list is keyed on a name alone, everywhere and forever, so unlike the
    # allowlist above it has no natural expiry. The one expiry that IS detectable: every entry
    # claims the name is not this repo's to declare (a native command, or a skill it retired).
    # The moment this repo ships that name the claim is false — a retired skill re-introduced,
    # or a new skill colliding with a native command, which is not hypothetical since an agent
    # already routes work to the native `/code-review`. Left undetected the entry would go on
    # silently exempting a name that has become ours to check.
    for name, reason in sorted(EXTERNAL_SLASH_IGNORE.items()):
        if any(name in names for names in catalog.values()):
            findings.append({
                "file": os.path.relpath(__file__, root), "line": 0, "ref": name,
                "problem": f"stale EXTERNAL_SLASH_IGNORE entry — this repo now ships `{name}`, "
                           f"so it is ours to check. Remove it: {reason}",
            })

    stats = {"files": files, "refs": refs, "roots": len(surfaces),
             "absent_roots": absent, "exempt": len(fired), "catalog": len(catalog)}
    return findings, stats


# --------------------------------------------------------------------------- self-test

SKILL_MD = "---\nname: {name}\nallowed-tools: Read\n---\nbody\n"


def _materialise(base, files):
    for rel, content in files.items():
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    return base


def _fixture_repo(base):
    return _materialise(base, {
        ".claude-plugin/marketplace.json": "{}",
        "tt/.claude-plugin/plugin.json": '{"name": "tt"}',
        "tt/skills/next-goal/SKILL.md": SKILL_MD.format(name="next-goal"),
        "tt/agents/facilitator.md": "---\nname: facilitator\ntools: Read\n---\nbody\n",
    })


def run_self_test():
    failures = []
    ran = []

    def case(label, got, want):
        # Counted, not hardcoded: docs/VALIDATION.md pins this script's stdout, so a literal
        # would keep asserting the old number after a case is added or — worse — deleted.
        ran.append(label)
        if got != want:
            failures.append(f"  {label}: got {got}, want {want}")

    def refs_of(findings):
        return sorted((f["ref"], f["line"]) for f in findings)

    with tempfile.TemporaryDirectory() as tmp:
        repo = _fixture_repo(os.path.join(tmp, "repo"))

        # 1. a valid reference resolves, and a bare in-repo name resolves too
        _materialise(repo, {
            "tt/skills/next-goal/SKILL.md": SKILL_MD.format(name="next-goal")
            + '\nCall Skill(skill: "tt:next-goal") and Skill(skill: "facilitator").\n',
        })
        found, stats = check_all(repo, external_roots=[], allowlist=[])
        case("valid reference", refs_of(found), [])
        case("valid reference counted", stats["refs"] >= 2, True)

        # 2. a dangling reference is reported with its line
        _materialise(repo, {"docs/guide.md": 'x\nSkill(skill: "tt:completion-condition")\n'})

        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("dangling call", refs_of(found), [("tt:completion-condition", 2)])

        # 2b. the agent CALL surface: `subagent_type:` resolves against the same catalogue,
        # so a shipped agent passes and one deleted the way #593 deleted code-reviewer is caught
        _materialise(repo, {"docs/guide.md": 'subagent_type: "tt:facilitator"\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("subagent_type resolves", refs_of(found), [])
        _materialise(repo, {"docs/guide.md": 'subagent_type: "tt:code-reviewer"\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("dangling subagent_type", refs_of(found), [("tt:code-reviewer", 1)])

        # 2c. a BARE `subagent_type:` is a harness built-in or nothing (#719) — it must not be
        #     checked against this repo's skill catalogue the way a bare Skill() name is.
        _materialise(repo, {"docs/guide.md": 'subagent_type: "general-purpose"\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("bare subagent_type harness built-in resolves", refs_of(found), [])
        _materialise(repo, {"docs/guide.md": 'subagent_type: "no-such-agent"\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("bare subagent_type non-built-in dangles", refs_of(found), [("no-such-agent", 1)])
        # A bare name that happens to match a real skill must still dangle — subagent_type never
        # resolves a bare name against this repo's catalogue, only against the built-in list.
        _materialise(repo, {"docs/guide.md": 'subagent_type: "next-goal"\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("bare subagent_type matching a skill name still dangles", refs_of(found),
             [("next-goal", 1)])

        # 3. a hook matcher label is scanned; the same token in repo PROSE is not (history)
        _materialise(repo, {
            "docs/guide.md": "The retired `tt:save-session` skill was removed in v3.\n",
            "tt/hooks/ctx.sh": 'case "$skill" in\n  tt:next-goal|next-goal) ;;\nesac\n',
        })
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("prose history not scanned, live matcher clean", refs_of(found), [])
        _materialise(repo, {
            "tt/hooks/ctx.sh": 'case "$skill" in\n  tt:completion-condition) ;;\nesac\n',
        })
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("dangling matcher label", refs_of(found), [("tt:completion-condition", 2)])
        _materialise(repo, {"tt/hooks/ctx.sh": 'case "$skill" in\n  tt:next-goal) ;;\nesac\n'})

        # 4. a missing external path is skipped silently — fail open
        missing = os.path.join(tmp, "not-a-real-checkout")
        found, stats = check_all(repo, external_roots=[missing], allowlist=[])
        case("missing external root fails open", refs_of(found), [])
        case("missing external root is counted, not hidden", stats["absent_roots"], [missing])
        case("missing external root is not scanned", stats["roots"], 1)

        # 5. an external consumer IS scanned, prose included (the #562 shape)
        ext = _materialise(os.path.join(tmp, "harness", "skills"), {
            "session-close/SKILL.md":
                'Skill(skill: "tt:next-goal")\n'
                "On failure, retry once as `tt:completion-condition` before falling back.\n"
                "A bare `session-close` is a machine skill, not this repo's to judge.\n",
        })
        found, stats = check_all(repo, external_roots=[ext], allowlist=[])
        case("external prose reference is caught", refs_of(found), [("tt:completion-condition", 2)])
        case("external root scanned", stats["roots"], 2)

        # 6. the deliberate fallback is exempt, and the exemption is not silent
        allow = [("skills/session-close/SKILL.md", "tt:completion-condition", "documented bridge")]
        found, stats = check_all(repo, external_roots=[ext], allowlist=allow)
        case("deliberate fallback exempt", refs_of(found), [])
        case("exemption is reported in stats", stats["exempt"], 1)

        # 7. an exemption whose file no longer needs it is STALE — and an absent root, which
        #    proves nothing either way, must not trigger that.
        _materialise(ext, {"session-close/SKILL.md": 'Skill(skill: "tt:next-goal")\n'})
        found, _ = check_all(repo, external_roots=[ext], allowlist=allow)
        case("stale exemption reported", [f["ref"] for f in found], ["tt:completion-condition"])
        found, _ = check_all(repo, external_roots=[missing], allowlist=allow)
        case("absent root does not make an exemption look stale", refs_of(found), [])

        # 8. another marketplace's plugin is not this repo's to judge
        _materialise(repo, {"docs/guide.md": 'Skill(skill: "other-kit:whatever")\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("unknown plugin is skipped", refs_of(found), [])

        # 9. an agent's `skills:` list is the third hardcoded-name surface. It fails open and
        #    silent — the entry simply stops granting the skill — so a dangling one is a
        #    finding, and the `---` closing the frontmatter must not parse as a list item.
        _materialise(repo, {"docs/guide.md": "clean\n"})
        agent = "---\nname: f2\ntools: Skill\nskills:\n  - next-goal\n  - gone-skill\n---\nbody\n"
        _materialise(repo, {"tt/agents/f2.md": agent})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("dangling agent skills entry", refs_of(found), [("gone-skill", 6)])
        _materialise(repo, {"tt/agents/f2.md": agent.replace("  - gone-skill\n", "")})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("resolving agent skills list is quiet", refs_of(found), [])

        # 10. the slash form is how a consumer actually names a skill in prose — the stale
        #     half of #562 was exactly that shape. Native commands and retired skills named as
        #     history are permanently exempt; the consumer's own skills resolve against itself.
        _materialise(ext, {
            "session-close/SKILL.md":
                "Run `/next-goal`, then `/goal` evaluates it.\n"
                "The retired `/handoff` is named as history.\n"
                "`/wrap` is this consumer's own skill.\n"
                "But `/no-such-skill` is drift.\n"
                "A path like `/Users/x` and `skills/wrap/` must not match.\n",
            "wrap/SKILL.md": SKILL_MD.format(name="wrap"),
        })
        found, _ = check_all(repo, external_roots=[ext], allowlist=[])
        case("slash drift caught", refs_of(found), [("no-such-skill", 4)])

        #     Inside a frontmatter `description:` block the backticks come off (#646): that
        #     block is the routing string the model reads and nobody punctuates it, so every
        #     name in it was invisible — green only because the body happened to repeat the
        #     same names in backtick form. Each YAML shape is pinned, since the block boundary
        #     is what keeps this from widening into free prose.
        def desc_probe(block, body="body\n"):
            _materialise(ext, {"session-close/SKILL.md":
                               "---\nname: session-close\n" + block + "model: inherit\n---\n" + body})
            hits, _ = check_all(repo, external_roots=[ext], allowlist=[])
            return [f["ref"] for f in hits]

        case("bare slash in description is caught",
             desc_probe('description: "Run /gone-a next."\n'), ["gone-a"])
        case("bare slash outside frontmatter is not (backtick rule unchanged)",
             desc_probe('description: "clean"\n', "Run /gone-b next.\n"), [])
        case("ignored name stays ignored inside a description",
             desc_probe('description: "/goal evaluates the condition."\n'), [])
        case("a path in a description is not a skill reference",
             desc_probe('description: "see /Users/foo and /usr/bin"\n'), [])
        # A lookbehind of `[\w/]` alone let `~` and `.` through, so the FIRST segment of a
        # home- or dot-relative path was read as a skill name (`~/vault` -> `vault`). Only a
        # trailing slash saved one, so a single `~/vault` in any scanned description would have
        # blocked every commit touching a SKILL.md, with the offending file in another repo.
        case("a home- or dot-relative path is not a skill reference",
             desc_probe('description: "writes ~/vault, runs ./scripts and ../lib/x"\n'), [])
        case("block scalar description is read to its last line",
             desc_probe("description: >-\n  first /next-goal\n  second /gone-c\n"), ["gone-c"])
        case("plain unquoted continuation is read too",
             desc_probe("description: plain /next-goal\n  continued /gone-e\n"), ["gone-e"])
        case("the block ends at the next top-level key",
             desc_probe("description: |\n  ok\nprovenance: /gone-d\n"), [])
        # An INDENTED '---'/'...' inside the block scalar's own value is literal content (a
        # markdown rule, an embedded YAML example), not the frontmatter fence (#720) — the scan
        # must read past it rather than stop early and lose every reference after it.
        case("an indented fence inside a block scalar is not the frontmatter close",
             desc_probe("description: |\n  first /next-goal\n  ---\n  second /gone-g\n"),
             ["gone-g"])

        #     The same block is scanned IN-REPO, where the description scan was gated on `wide`
        #     at first and so kept the exact blind spot #646 was filed about. The narrow-prose
        #     rule does not reach here: three in-repo descriptions name another plugin's skill
        #     with no backticks and no second mention, so a rename would pass unseen.
        _materialise(repo, {"tt/skills/probe/SKILL.md":
                            "---\nname: probe\ndescription: routes to /gone-f\n---\nbody\n"})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("in-repo description is scanned too", refs_of(found), [("gone-f", 3)])
        _materialise(repo, {"tt/skills/probe/SKILL.md": SKILL_MD.format(name="probe")})

        # 11. every list shape a human writes is walked to the END. A block regex stopped at
        #     the first unreadable item and silently dropped the rest while still printing OK,
        #     so each shape is pinned rather than assumed.
        shapes = {
            "block": "skills:\n  - live\n  - gone\n",
            "flow": "skills: [live, gone]\n",
            "quoted first": 'skills:\n  - "gone"\n',
            "quoted second": 'skills:\n  - live\n  - "gone"\n',
            "trailing comment": "skills:\n  - live\n  - gone  # why\n",
            "blank line": "skills:\n\n  - gone\n",
        }
        _materialise(repo, {
            "docs/guide.md": "clean\n",
            "tt/agents/f2.md": "---\nname: f2\n---\n",
            "tt/skills/live/SKILL.md": SKILL_MD.format(name="live"),
        })
        _materialise(ext, {"session-close/SKILL.md": "clean\n"})
        for label, block in shapes.items():
            _materialise(repo, {"tt/agents/f4.md": f"---\nname: f4\n{block}---\nbody\n"})
            found, _ = check_all(repo, external_roots=[], allowlist=[])
            case(f"skills list shape: {label}", [f["ref"] for f in found], ["gone"])
        _materialise(repo, {"tt/agents/f4.md": "---\nname: f4\n---\nbody\n"})

        # 12. a consumer's own skills resolve for ITS references only. Merging them into the
        #     catalogue made an in-repo bare name resolve against a skill this repo does not
        #     ship, so the same tree got different verdicts depending on whether the sibling
        #     checkout existed — and the pre-commit hook came out laxer than CI.
        _materialise(repo, {"tt/agents/f5.md": "---\nname: f5\nskills:\n  - wrap\n---\nbody\n"})
        _materialise(ext, {"wrap/SKILL.md": SKILL_MD.format(name="wrap")})
        with_ext, _ = check_all(repo, external_roots=[ext], allowlist=[])
        without, _ = check_all(repo, external_roots=[], allowlist=[])
        case("consumer name does not leak in-repo", [f["ref"] for f in with_ext], ["wrap"])
        case("verdict independent of the sibling checkout",
             [f["ref"] for f in with_ext], [f["ref"] for f in without])
        _materialise(repo, {"tt/agents/f5.md": "---\nname: f5\n---\nbody\n"})

        # 12b. a BARE subagent_type in an external consumer's own file may still legitimately
        #      name a project-local agent this scanner cannot see (#719 fix review) — the same
        #      extra_bare leniency a bare Skill() reference already gets there, so tightening
        #      subagent_type's bare path to HARNESS_BUILTIN_AGENTS only must not also revoke it.
        _materialise(ext, {"session-close/SKILL.md": 'subagent_type: "wrap"\n'})
        found, _ = check_all(repo, external_roots=[ext], allowlist=[])
        case("bare subagent_type resolves via the consumer's own extra_bare", refs_of(found), [])
        _materialise(ext, {"session-close/SKILL.md": 'subagent_type: "no-such-agent"\n'})
        found, _ = check_all(repo, external_roots=[ext], allowlist=[])
        case("bare subagent_type outside extra_bare and built-ins still dangles",
             refs_of(found), [("no-such-agent", 1)])
        _materialise(ext, {"session-close/SKILL.md": "clean\n"})

        # 12c. a QUALIFIED subagent_type ref is also a qualified token qual_re matches on a .sh/
        #      wide surface — splitting bare subagent_type into its own set (#719) must not also
        #      make the qualified form double-count against the SAME line's qual_re match.
        _materialise(repo, {"tt/hooks/ctx2.sh": 'subagent_type: "tt:code-reviewer"\n'})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("qualified subagent_type in a .sh file is not double-counted",
             refs_of(found), [("tt:code-reviewer", 1)])
        _materialise(repo, {"tt/hooks/ctx2.sh": "clean\n"})

        # 13. an ignore entry claims the name is not this repo's to declare. Ship it and the
        #     claim is false, so the entry must be reported rather than go on exempting a name
        #     that became ours to check.
        ignored = sorted(EXTERNAL_SLASH_IGNORE)[0]
        _materialise(repo, {f"tt/skills/{ignored}/SKILL.md": SKILL_MD.format(name=ignored)})
        found, _ = check_all(repo, external_roots=[], allowlist=[])
        case("ignore entry goes stale when shipped", [f["ref"] for f in found], [ignored])

    if failures:
        print("FAIL: check-skill-reference-drift self-test")
        print("\n".join(failures))
        return 1
    print(f"OK: all {len(ran)} check-skill-reference-drift self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    findings, stats = check_all(root)

    if not stats["catalog"]:
        print(f"ERROR: no */skills/*/SKILL.md found under {root} — nothing to resolve against",
              file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"findings": findings, **stats}, ensure_ascii=False, indent=2))
    elif findings:
        print("FAIL: skill references that do not resolve:")
        for f in findings:
            print(f"  {f['file']}:{f['line']}  {f['ref']} — {f['problem']}")
    else:
        print(
            f"OK: all {stats['refs']} skill reference(s) resolve — {stats['files']} file(s) "
            f"across {stats['roots']} root(s), {len(stats['absent_roots'])} external root(s) "
            f"absent, {stats['exempt']} deliberate fallback(s) exempt"
        )

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
