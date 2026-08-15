#!/usr/bin/env python3
"""check-agent-tools-usage.py — declared tools must match what the body says (#577, #611).

RULE: for every `*/agents/*.md` (`tools:`) and every `*/skills/*/SKILL.md` (`allowed-tools:`),
the tools declared in frontmatter and the tools the body actually reaches for must be the same
set. Four findings, four different harms:

  UNDECLARED — the body directs the file to call a tool the declaration omits. The call cannot
    happen, so that branch is dead prose. Found live in vault-searcher.md, whose `.vault-link`
    path-resolution recovery said "use AskUserQuestion" while `tools:` listed only
    Read/Bash/Glob/Grep (#577).

    One narrow exception to "never infer a tool from a shell command" (#634). #611's headline
    pair — adversarial-review and expert-panel directing a mandatory backlog-prefilter step with
    no `Bash` grant — was found by hand, not by this rule, because the `python3 …` call sat
    inside a fenced block that `strip_noise` drops; both became machine-checkable only once
    their prose was rewritten to name `Bash`, which left the recurrence path wide open. So a
    SKILL.md that has a ```bash / ```sh / ```shell tagged fence anywhere and no `Bash` grant is
    reported as UNDECLARED `Bash` on the fence alone. Only *tagged* fences count — an untagged
    one is usually YAML or an output template, and honouring those is an FP field. The prose
    rule is otherwise unchanged: a shell command still never evidences a grant, it only exposes
    a missing one. Measured at introduction: 11 of 19 skills carry a tagged shell fence, all 11
    already declared `Bash`, so the rule flags nothing today — a floor against the next skill.
    Skills only for now; the same scan over agents also flagged nothing (2 of 4 carry a tagged
    fence, both with `Bash`), so extending it is a one-line change backed by that measurement,
    deliberately left for whoever needs it.

  UNUSED — the declaration grants a tool the body never reaches for. That is the
    over-permission #472 introduced the field to prevent, just re-created one entry at a time.
    Found live in vault-file-organizer.md, which held Write and Grep while its body only moves
    files and edits named frontmatter fields (#577), and across 17 of this repo's 19 skills in
    #611 — retro/SKILL.md's `Edit` the sharpest, since its own body forbids editing rule files.

  MISSING — a SKILL.md declares no usable `allowed-tools:` — the key is absent, or present with
    an empty value — so the skill inherits every tool in the harness. Same harm
    `check-agent-tools-field.py` blocks for agents, and its "exists AND is non-empty" bar is
    matched here on purpose; skills had no equivalent until #611. No skill in this repo trips it
    today, so it is a floor against the next one, not a live find. Agents are exempt because
    that sibling guard already owns their side.

  CONTRACT — the body declares itself read-only (the Write Role Contract) yet holds a write
    tool. UNUSED cannot catch this on its own: the very sentence stating the prohibition
    ("no access to the Write tool") contains the word `Write`, which satisfies a bare-mention
    check. This is the repo's central write-safety invariant, so it gets its own rule.
    **Agents only.** The contract binds subagents, and the skills that name it are the
    main-context writers it authorises — firing there would block exactly the right holders.

  UNCONTRACTED — CONTRACT's inverse, and the harm it misses (#620). CONTRACT only fires on a
    body that *claims* the contract, so an agent that never heard of it is invisible: it holds
    a write tool, documents a vault procedure the hook denies at runtime, and every check stays
    green. That is not hypothetical — vault-file-organizer.md documented `Edit` on frontmatter
    and `mv` on vault files, both denied by pre-write-guard.sh in its default `enforce` mode,
    with zero mentions of the contract in the whole file, while its sibling
    vault-knowledge-manager.md opened with it. So: an agent holding Write/Edit/NotebookEdit
    whose body names a vault ROOT and never names the contract is reported.

    The vault condition is what keeps this narrow, and it is load-bearing rather than
    incidental: the Write Role Contract governs vault writes specifically, so a non-vault agent
    holding `Write` has no contract to name and must not be flagged for silence about one. It
    matches a root *spelling* (`~/vault`, `$VAULT_ROOT`, `VAULT_BRIDGE_VAULT_…`) and not the
    bare word `vault`, which fires on an agent that only routes vault work elsewhere ("for
    vault lookups delegate to vault-searcher") and leaves it no way to go green but to recite a
    contract it has no duty under. The cost is the other direction: an agent that documents its
    root some third way is missed. All three live vault agents spell it `~/vault`, so widen the
    list when a real one does not — do not fall back to the bare word.
    Agents only, for CONTRACT's reason — a skill is the main-context writer the contract
    authorises, so its silence carries no obligation.

`check-agent-tools-field.py` is the sibling guard for agents and deliberately stops at "the key
exists and is non-empty" — its docstring calls this comparison a manual judgment call. This
script is that judgment call, made mechanical.

## The two declaration forms

Agents write `tools:` comma-separated, skills write `allowed-tools:` space-separated, and both
forms also appear as YAML flow sequences or block lists. One splitter reads all of them: it
breaks on commas *and* whitespace outside parentheses, so `Bash(git add:*, git commit:*)`
survives intact under either convention.

## How usage is detected, and why the directions read differently

The body is prose, so neither direction can be inferred perfectly. Each is matched by the
narrowest signal its own harm needs, and the asymmetry is deliberate:

  UNDECLARED looks only for an *imperative* mention — `use X`, `call X`, `via X`, `X(` — because
    the harm is a directive that cannot execute. A tool merely named in passing ("the Write Role
    Contract", "vault writes are user-initiated") is not a directive and must not be flagged.
    The verb is matched case-insensitively so a numbered step beginning "Use Glob to…" counts,
    but the tool name itself stays case-exact so the verb `write` never reads as the tool
    `Write`. Negations are excluded within the sentence leading up to the verb: an agent body
    saying "do not use the `Agent` tool" is a prohibition, not a call.

  UNUSED looks for the tool name appearing *anywhere* in the body, imperative or not. A weaker
    signal is correct here because the direction is inverted: any mention at all shows the grant
    was considered, and demanding an imperative would flag a dozen legitimate grants across this
    repo's agents. The residual cost is that a tool used only through an unnamed shell command
    reads as unused — so a body must name the tools it relies on, which is what CLAUDE.md's
    "Adding a New Agent" §2 already asks for. Where that weak signal is not good enough to
    protect an invariant, CONTRACT above covers the gap.

Neither direction infers usage from a code fence. `mv` in a bash fence is Bash, but `ls` in a
sentence is not, and the guard does not try to tell them apart — the body says `Bash` or the
grant is not evidenced.

Usage:
    python3 scripts/check-agent-tools-usage.py [--root DIR] [--json] [--self-test]

    --root DIR    Repo root to check (default: git toplevel, else CWD). Scans
                  DIR/*/agents/*.md and DIR/*/skills/*/SKILL.md.
    --json        Emit a machine-readable JSON report instead of text.
    --self-test   Validate the matching logic in-memory against fixture strings and exit 0 only
                  if every case is detected as expected.

Exit codes: 0 = every declared tool set matches its body (or --self-test passed),
            1 = at least one mismatch, 2 = usage error / nothing found to check.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)


# `[ \t]*` and not `\s*`: with re.MULTILINE, `\s*` eats the newline and swallows the first
# entry of a YAML block list, so `tools:\n  - Read` would capture the literal `- Read`.
# `^` and not `\b`: `allowed-tools:` must not be matched by the agent key `tools:`.
def _tools_key_re(key):
    return re.compile(r"^" + re.escape(key) + r":[ \t]*(.*)$", re.MULTILINE)


TOOLS_BLOCK_ITEM_RE = re.compile(r"^[ \t]*-[ \t]*(\S.*?)[ \t]*$")

# Tool names this guard knows about. A name outside this set is reported as unknown rather than
# silently ignored — a typo'd grant is still a grant that does nothing. `mcp__*` names and the
# scoped `Tool(pattern)` form are normalised before the lookup, not rejected.
KNOWN_TOOLS = [
    "Agent", "Artifact", "AskUserQuestion", "Bash", "BashOutput", "Edit", "ExitPlanMode",
    "Glob", "Grep", "KillShell", "ListAgents", "Monitor", "NotebookEdit", "Read",
    "SendMessage", "Skill", "SlashCommand", "Task", "TodoWrite", "ToolSearch", "WebFetch",
    "WebSearch", "Write",
]

# Tools that can create or modify a file. A body claiming the Write Role Contract may hold none.
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
# Self-directed phrasings only. A bare "read-only" was tried and removed: it is a substring
# test over the whole body, so it fires on an agent describing something *else* as read-only
# ("the manifest is a read-only input", "delegate to vault-searcher, which is read-only") and
# hard-blocks a legitimate writer. It also caught nothing the specific markers miss.
READONLY_MARKERS = (
    "write role contract",
    "cannot write",
    "no access to the write tool",
)
# UNCONTRACTED's scope condition: the contract governs vault writes, so an agent that never
# talks about the vault has no contract to be silent about. The marker is the vault PATH, not
# the bare word — `vault` alone fires on an agent that merely routes vault work elsewhere
# ("for vault lookups delegate to vault-searcher"), which then has no way to go green except by
# reciting a contract it has no duty under. Matched on the raw body, fences included: a vault
# path in a shell example is still this agent operating on the vault.
VAULT_MARKERS = ("~/vault", "$vault_root", "vault_bridge_vault_")

# `bash`/`sh`/`shell` only, and the tag is required: an untagged fence in these files is far
# more often YAML, an output template, or a markdown sample than a command to run.
FENCE_LINE_RE = re.compile(r"^[ \t]*(`{3,})[ \t]*(\S*)")
# The info string's leading letters are the language; everything after is decoration. Renderers
# and doc tools attach it with no separating space (```bash{.copy}, ```bash,ignore,
# ```bash:no-run, ```sh#run), so splitting on whitespace alone drops that whole family.
# Pandoc/Quarto put the attribute block FIRST instead (```{.bash}, ```{.sh .numberLines}), so an
# optional leading `{`/`.` is skipped before the language is read (#636). Anything else in that
# leading position (```{=html}) still fails to match and stays non-shell.
FENCE_LANG_RE = re.compile(r"^\{?\.?([A-Za-z]+)")
SHELL_FENCE_LANGS = ("bash", "sh", "shell")


def _is_shell_lang(info):
    m = FENCE_LANG_RE.match(info)
    return bool(m) and m.group(1).lower() in SHELL_FENCE_LANGS


def has_shell_fence(body):
    """True when a tagged shell fence stands as a real, reachable block.

    Two things a plain line-by-line regex gets wrong, both verified as false positives before
    this existed: a fence inside an HTML comment is a commented-out step, and a ```bash inside a
    longer ````markdown block is sample text, not a command. So comments come out first, then
    fences are walked in order — CommonMark closes a fence only on a bare run at least as long
    as the opener, which is what makes the nested shorter fence read as content.

    Walking has its own failure mode, and it is resolved toward detecting more. One unclosed
    non-shell fence would otherwise swallow every fence after it to EOF, so a file that simply
    forgot a closing fence would go silent — the exact shape #634 exists to close. When the walk
    ends inside an open fence the document is malformed, the nesting argument no longer holds,
    and the flat scan runs instead.
    """
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    lines = body.split("\n")
    open_len = 0
    for line in lines:
        m = FENCE_LINE_RE.match(line)
        if not m:
            continue
        ticks, info = len(m.group(1)), m.group(2)
        if open_len:
            if not info and ticks >= open_len:
                open_len = 0
            continue
        if _is_shell_lang(info):
            return True
        open_len = ticks
    if not open_len:
        return False
    return any(
        _is_shell_lang(m.group(2))
        for m in (FENCE_LINE_RE.match(line) for line in lines)
        if m
    )

_VERBS = r"(?:use|uses|using|call|calls|calling|invoke|invokes|invoking|via|through)"
# Up to two filler words between verb and tool ("use the `X` tool", "call into X").
_FILLER = r"(?:\s+(?:a|an|the|into|to|with|by)){0,2}"
NEGATORS = ("not", "never", "without", "cannot", "no", "neither", "nor")
# How far back to read for a negation, and where that read stops. The trim is at CLAUSE
# boundaries, not sentence boundaries: agent prose is full of conditionals that negate
# something other than the verb ("...or returns no useful candidates, use Grep instead"), and
# a sentence-wide window lets that stray `no` suppress a genuine directive — silently, since
# a suppressed UNDECLARED finding prints nothing at all.
# A newline is deliberately NOT a boundary: these bodies are hard-wrapped, so a wrap can land
# anywhere, including between the negator and its verb.
_LOOKBACK = 160
_CLAUSE_END_RE = re.compile(r"[.!?;:,]")


def _imperative_re(tool):
    """Match an imperative reach for `tool`.

    The verb and filler are case-insensitive via an inline group so a numbered step starting
    "Use Glob to…" matches; the tool name stays case-exact, which is what keeps the ordinary
    verb `write` from reading as the tool `Write`. The second alternative is call syntax with
    no space before the paren — `Write (v5 §5)` is a prose parenthetical, not a call.
    """
    return re.compile(
        r"(?i:" + _VERBS + _FILLER + r")\s+`?" + re.escape(tool) + r"`?\b"
        r"|\b" + re.escape(tool) + r"\("
    )


def _mention_re(tool):
    return re.compile(r"\b" + re.escape(tool) + r"\b")


def _is_negated(body, start):
    """True when the clause leading up to `start` negates the reach.

    Reads backwards from the match to the nearest clause boundary, so a newline between the
    negator and the verb is crossed ("do not re-invoke yourself, do\\nnot use the `Agent`
    tool") while a negator belonging to an earlier clause is not ("...or returns no useful
    candidates, use Grep instead" is a directive, not a prohibition).
    """
    window = body[max(0, start - _LOOKBACK):start]
    ends = list(_CLAUSE_END_RE.finditer(window))
    if ends:
        window = window[ends[-1].end():]
    lowered = window.lower()
    if "n't" in lowered:
        return True
    return any(re.search(r"\b" + n + r"\b", lowered) for n in NEGATORS)


def split_frontmatter(text):
    """Return (frontmatter, body) or (None, None) when there is no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _split_outside_parens(value):
    """Split on commas AND whitespace that are not inside a scoped `Bash(git add:*)` suffix.

    Both separators at once, because the two keys disagree: agents write `tools:` comma-
    separated and skills write `allowed-tools:` space-separated. Treating each as a separator
    makes `Read, Bash` yield an empty part between them, which the filter drops — so the comma
    form reads identically to before.
    """
    # Close the gap in `Bash (git add:*)` first. Whitespace is a separator now, so a space
    # before the scoped suffix would split one declaration into `Bash` plus a `(git add:*)`
    # fragment that normalises to the empty string and gets reported as an unnamed unknown tool.
    value = re.sub(r"\s+\(", "(", value)
    parts, depth, current = [], 0, []
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and (ch == "," or ch.isspace()):
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p for p in (p.strip() for p in parts) if p]


def declared_tools(frontmatter, key="tools"):
    """Read the declaration in the inline form, a YAML flow sequence, or a block list.

    Returns None when the key is absent, which is a different fact from an empty list — the
    MISSING finding needs to tell "no key at all" apart from "key present, nothing usable".
    """
    tm = _tools_key_re(key).search(frontmatter or "")
    if not tm:
        return None
    # Strip a `# comment` tail before splitting: whitespace is a separator now, so the tail
    # would otherwise arrive as three bogus `unknown` tools instead of one discarded suffix.
    inline = tm.group(1).split("#", 1)[0].strip()
    if inline:
        return _split_outside_parens(inline)
    tools = []
    for line in frontmatter[tm.end():].lstrip("\r\n").split("\n"):
        # Blank and comment lines are valid inside a YAML block list; stopping at one would
        # read a correctly-commented declaration as empty. The scan still stops at the next
        # real key, which is what keeps an empty declaration from borrowing the line below it.
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = TOOLS_BLOCK_ITEM_RE.match(line)
        if not item:
            break
        tools.append(item.group(1))
    return tools


def normalise(tool):
    """Reduce a declaration to its bare tool name.

    Strips what valid YAML and this repo's own conventions can wrap around it — a `#` comment
    tail, a CR from CRLF frontmatter, flow-sequence brackets, surrounding quotes, and the
    scoped `Bash(git diff:*)` suffix. Anything left that is not a real tool name is a typo,
    which is what the `unknown` finding is for.
    """
    tool = tool.split("#", 1)[0]
    tool = tool.strip().strip("\r").strip("[]").strip()
    if len(tool) >= 2 and tool[0] == tool[-1] and tool[0] in "\"'":
        tool = tool[1:-1]
    return tool.split("(", 1)[0].strip()


def is_known(tool):
    base = normalise(tool)
    return base in KNOWN_TOOLS or base.startswith("mcp__")


def strip_noise(body):
    """Drop spans that name tools without reaching for them.

    Fenced code blocks are shell/YAML samples, and an HTML comment is authoring scaffolding —
    a tool name in either is not the body directing itself.
    """
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    return body


def check_agent(text, key="tools", require_key=False, check_contract=True,
                shell_fence_implies_bash=False):
    """Return (undeclared, unused, unknown, contract, missing, uncontracted) for one .md."""
    frontmatter, raw_body = split_frontmatter(text)
    if frontmatter is None:
        return [], [], [], [], False, []
    declared = declared_tools(frontmatter, key)
    # `not declared` and not `declared is None`: a key present with an empty value grants
    # nothing and inherits everything, exactly like an absent key. But only the skills side
    # returns here — an agent must fall through with an empty set so UNDECLARED still reports
    # what its body reaches for. Short-circuiting both scopes would let an agent declaring a
    # bare `tools:` pass this guard silently while inheriting every tool in the harness.
    if not declared:
        if require_key:
            return [], [], [], [], True, []
        declared = []
    unknown = [t for t in declared if not is_known(t)]
    known_declared = [normalise(t) for t in declared if is_known(t) and not normalise(t).startswith("mcp__")]
    declared_bases = {normalise(t) for t in declared}
    raw_body = raw_body or ""
    body = strip_noise(raw_body)

    undeclared = []
    for tool in KNOWN_TOOLS:
        if tool in declared_bases:
            continue
        for m in _imperative_re(tool).finditer(body):
            if not _is_negated(body, m.start()):
                undeclared.append(tool)
                break

    # The fence rule reads the RAW body on purpose — strip_noise removes the very fences it
    # looks for. Guarded on `Bash` not already being reported so a body that both names Bash
    # imperatively and shows a fence yields one finding, not two.
    if (shell_fence_implies_bash and "Bash" not in declared_bases
            and "Bash" not in undeclared and has_shell_fence(raw_body)):
        undeclared.append("Bash")

    unused = [t for t in known_declared if not _mention_re(t).search(body)]

    lowered = body.lower()
    names_contract = any(marker in lowered for marker in READONLY_MARKERS)
    contract, uncontracted = [], []
    if check_contract:
        held_writes = [t for t in WRITE_TOOLS if t in declared_bases]
        if names_contract:
            contract = held_writes
        elif held_writes and any(v in raw_body.lower() for v in VAULT_MARKERS):
            uncontracted = held_writes

    return undeclared, unused, unknown, contract, False, uncontracted


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_agent_files(root):
    return sorted(glob.glob(os.path.join(root, "*", "agents", "*.md")))


def find_skill_files(root):
    return sorted(glob.glob(os.path.join(root, "*", "skills", "*", "SKILL.md")))


SCOPES = (
    {"label": "agent", "finder": find_agent_files, "key": "tools",
     "require_key": False, "check_contract": True, "shell_fence_implies_bash": False},
    {"label": "skill", "finder": find_skill_files, "key": "allowed-tools",
     "require_key": True, "check_contract": False, "shell_fence_implies_bash": True},
)


SELF_TEST_CASES = [
    # (label, text, undeclared, unused, unknown, contract)
    (
        "imperative mention of an undeclared tool",
        "---\nname: a\ntools: Read\n---\nuse AskUserQuestion to confirm the path.\nRead it.",
        ["AskUserQuestion"], [], [], [],
    ),
    (
        "a numbered step starting with a capitalised verb still counts",
        "---\nname: a\ntools: Read\n---\n1. Use Glob to find session files.\n2. Read them.",
        ["Glob"], [], [], [],
    ),
    (
        "backticked imperative, filler words",
        "---\nname: a\ntools: Read\n---\nThen call the `Skill` tool. Read the file.",
        ["Skill"], [], [], [],
    ),
    (
        "a negator wrapped onto the previous line still suppresses",
        "---\nname: a\ntools: Read\n---\nDo not\nuse the `Agent` tool. Read the diff.",
        [], [], [], [],
    ),
    (
        "a negator in an EARLIER CLAUSE does not suppress",
        "---\nname: a\ntools: Read\n---\nIf the search returns no useful candidates, use Grep instead. Read the hits.",
        ["Grep"], [], [], [],
    ),
    (
        "a negator in the PREVIOUS sentence does not suppress",
        "---\nname: a\ntools: Read\n---\nThis is not a review tool. Use Grep for the scan. Read on.",
        ["Grep"], [], [], [],
    ),
    (
        "negation applies to the call-syntax alternative too",
        "---\nname: a\ntools: Read\n---\nDo not call Artifact(path) here. Read only.",
        [], [], [], [],
    ),
    (
        "passing mention is not a call",
        "---\nname: a\ntools: Read\n---\nThe Write Role Contract forbids that. Read only.",
        [], [], [], [],
    ),
    (
        "a prose parenthetical is not call syntax",
        "---\nname: a\ntools: Read\n---\nThe Write (v5) contract forbids it. Read only.",
        [], [], [], [],
    ),
    (
        "call syntax with no space is a call",
        "---\nname: a\ntools: Read\n---\nEmit Artifact(path) at the end. Read first.",
        ["Artifact"], [], [], [],
    ),
    (
        "declared but never mentioned",
        "---\nname: a\ntools: Read, Write, Grep\n---\nRead the frontmatter and report.",
        [], ["Write", "Grep"], [], [],
    ),
    (
        "tool named only inside a fence does not count as used",
        "---\nname: a\ntools: Bash\n---\nRun it:\n```\nBash\n```\n",
        [], ["Bash"], [], [],
    ),
    (
        "a YAML block list is read like the inline form",
        "---\nname: a\ntools:\n  - Read\n  - Bash\nmodel: haiku\n---\nRead the file, then use Bash to move it.",
        [], [], [], [],
    ),
    (
        "a comment inside a block list does not truncate it",
        "---\nname: a\ntools:\n  # the list\n  - Read\n  - Bash\n---\nRead the file, then use Bash to move it.",
        [], [], [], [],
    ),
    (
        "a scoped suffix containing a comma is one declaration, not two",
        "---\nname: a\ntools: Read, Bash(git add:*, git commit:*)\n---\nRead it, then use Bash.",
        [], [], [], [],
    ),
    (
        "quotes, flow sequences, comment tails and CRLF are all just YAML",
        "---\r\nname: a\r\ntools: [\"Read\", 'Bash']  # both needed\r\n---\r\nRead it, then use Bash.",
        [], [], [], [],
    ),
    (
        "an unknown tool name is reported, mcp__ and scoped forms are not",
        "---\nname: a\ntools: Read, Bash(git diff:*), mcp__foo__bar, Reed\n---\nRead it, then use Bash.",
        [], [], ["Reed"], [],
    ),
    (
        "a read-only body may not hold a write tool",
        "---\nname: a\ntools: Read, Write\n---\nThis agent is read-only by the Write Role Contract. Read and report.",
        [], [], [], ["Write"],
    ),
    (
        "calling something ELSE read-only does not make this agent read-only",
        "---\nname: a\ntools: Read, Write\n---\nThe manifest is a read-only input. Read it, then use Write to emit the report.",
        [], [], [], [],
    ),
    (
        "clean agent",
        "---\nname: a\ntools: Read, Bash\n---\nRead the file, then use Bash to move it.",
        [], [], [], [],
    ),
    (
        "no frontmatter is not this guard's problem",
        "just a reference doc",
        [], [], [], [],
    ),
    (
        # If `^tools:` also matched `allowed-tools:`, Write would read as declared and nothing
        # would fire. UNDECLARED firing is what proves the two keys stay separate.
        "the agent key does not read a skill's `allowed-tools:`",
        "---\nname: a\nallowed-tools: Read Write\n---\nRead it, then use Write.",
        ["Write"], [], [], [],
    ),
    (
        "a space before the scoped suffix does not split the declaration",
        "---\nname: a\ntools: Read, Bash (git diff:*)\n---\nRead it, then use Bash.",
        [], [], [], [],
    ),
    (
        "a bare `tools:` grants nothing, so the body's reaches are all UNDECLARED",
        "---\nname: a\ntools:\nmodel: x\n---\nUse Write to emit the report, then use Bash to move it.",
        ["Write", "Bash"], [], [], [],
    ),
    (
        "a vault agent holding a write tool must name the contract (#620)",
        "---\nname: a\ntools: Read, Edit\n---\nMove files under ~/vault/. Read each one, then use Edit on its frontmatter.",
        [], [], [], [], False, ["Edit"],
    ),
    (
        "routing vault work elsewhere is not a vault duty — the word alone must not fire",
        "---\nname: a\ntools: Read, Write\n---\nFor vault lookups delegate to vault-searcher. Read the diff, then use Write to emit the report.",
        [], [], [], [], False, [],
    ),
    (
        "naming the contract answers UNCONTRACTED — CONTRACT then judges the grant",
        "---\nname: a\ntools: Read, Edit\n---\nThe Write Role Contract denies vault writes here. Read and use Edit on the draft instead.",
        [], [], [], ["Edit"], False, [],
    ),
    (
        "a non-vault agent holding a write tool has no contract to name",
        "---\nname: a\ntools: Read, Write\n---\nRead the diff, then use Write to emit the report.",
        [], [], [], [], False, [],
    ),
    (
        "a vault agent with no write tool is silent about the contract legitimately",
        "---\nname: a\ntools: Read, Bash\n---\nSearch ~/vault/ read-only. Read the hits, use Bash to list them.",
        [], [], [], [], False, [],
    ),
    (
        # One case per VAULT_MARKERS entry, so a typo in any single spelling fails here rather
        # than silently narrowing the scope condition to whichever spelling the live agents use.
        "the $VAULT_ROOT spelling is a vault root too (#636)",
        "---\nname: a\ntools: Read, Edit\n---\nMove files under $VAULT_ROOT/notes. Read each one, then use Edit on its frontmatter.",
        [], [], [], [], False, ["Edit"],
    ),
    (
        "the VAULT_BRIDGE_VAULT_ env prefix is a vault root too (#636)",
        "---\nname: a\ntools: Read, Edit\n---\nResolve VAULT_BRIDGE_VAULT_ROOT first. Read each note, then use Edit on its frontmatter.",
        [], [], [], [], False, ["Edit"],
    ),
    (
        "the shell-fence rule is skills-only — an agent fence does not imply Bash",
        "---\nname: a\ntools: Read\n---\nRead it, then run:\n```bash\nmv a b\n```\n",
        [], [], [], [],
    ),
]

# Checked with key="allowed-tools", require_key=True, check_contract=False.
# (label, text, undeclared, unused, unknown, contract, missing)
SKILL_SELF_TEST_CASES = [
    (
        "space-separated declarations read like the comma form",
        "---\nname: s\nallowed-tools: Read Bash Glob\n---\nRead it, use Bash to move it, use Glob to list.",
        [], [], [], [], False,
    ),
    (
        "a space-separated grant the body never names is UNUSED",
        "---\nname: s\nallowed-tools: Read Write Glob\n---\nRead the file and report.",
        [], ["Write", "Glob"], [], [], False,
    ),
    (
        "the mandated shell step with no Bash grant is UNDECLARED (#611)",
        "---\nname: s\nallowed-tools: Read Write\n---\nRun `python3 scripts/backlog-prefilter.py` via Bash. Read and Write the report.",
        ["Bash"], [], [], [], False,
    ),
    (
        "no allowed-tools at all is MISSING",
        "---\nname: s\ndescription: x\n---\nRead the file.",
        [], [], [], [], True,
    ),
    (
        "an empty allowed-tools value is MISSING too — it grants nothing",
        "---\nname: s\nallowed-tools:\neffort: low\n---\nRead the file.",
        [], [], [], [], True,
    ),
    (
        "a `tools:` line inside a description block scalar is not the declaration",
        "---\nname: s\ndescription: |\n  Lists the tools: Read and Write.\nallowed-tools: Read\n---\nRead the file.",
        [], [], [], [], False,
    ),
    (
        "a tagged shell fence with no Bash grant is UNDECLARED on the fence alone (#634)",
        "---\nname: s\nallowed-tools: Read\n---\nRead it, then run:\n```bash\npython3 scripts/backlog-prefilter.py\n```\n",
        ["Bash"], [], [], [], False,
    ),
    (
        "an UNTAGGED fence does not imply Bash — it is usually YAML or an output template",
        "---\nname: s\nallowed-tools: Read\n---\nRead it, then emit:\n```\nname: value\n```\n",
        [], [], [], [], False,
    ),
    (
        # The asymmetry #634 deliberately keeps: a fence exposes a MISSING grant but never
        # evidences a declared one, so this still reports UNUSED. Naming Bash in prose is what
        # clears it, exactly as before.
        "a fence does not evidence a declared Bash — UNUSED still fires",
        "---\nname: s\nallowed-tools: Read Bash\n---\nRead it, then run:\n```sh\nls\n```\n",
        [], ["Bash"], [], [], False,
    ),
    (
        "prose names Bash, so the same fenced skill is clean",
        "---\nname: s\nallowed-tools: Read Bash\n---\nRead it, then use Bash to run:\n```sh\nls\n```\n",
        [], [], [], [], False,
    ),
    (
        "a fence inside an HTML comment is a commented-out step, not a call",
        "---\nname: s\nallowed-tools: Read\n---\nRead it.\n<!--\n```bash\nls\n```\n-->\n",
        [], [], [], [], False,
    ),
    (
        "a ```bash nested in a longer ````markdown block is sample text",
        "---\nname: s\nallowed-tools: Read\n---\nRead it, then emit:\n````markdown\n```bash\nls\n```\n````\n",
        [], [], [], [], False,
    ),
    (
        "a tag suffix does not hide the language",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```bash title=\"run me\"\nls\n```\n",
        ["Bash"], [], [], [], False,
    ),
    (
        "an info-string suffix attached with no space does not hide it either",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```bash{.copy}\nls\n```\n",
        ["Bash"], [], [], [], False,
    ),
    (
        "a leading attribute block does not hide the language either (Pandoc/Quarto, #636)",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```{.bash}\nls\n```\n",
        ["Bash"], [], [], [], False,
    ),
    (
        "a leading attribute block naming a NON-shell language stays non-shell",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```{.python}\nprint(1)\n```\n",
        [], [], [], [], False,
    ),
    (
        "a comma-attached suffix is the same case (mdBook)",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```sh,ignore\nls\n```\n",
        ["Bash"], [], [], [], False,
    ),
    (
        # CommonMark closes on the FIRST bare run of >= length, so the trailing ``` closes the
        # yaml block and the ```bash line was its content all along. Nothing to report.
        "a same-length fence run wraps what follows — that is one block, not two",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```yaml\na: b\n```bash\nls\n```\n",
        [], [], [], [], False,
    ),
    (
        # Same shape with the closer missing: the document is malformed, the nesting argument
        # no longer holds, and the flat scan runs so the shell fence is not lost to EOF.
        "an unterminated fence falls back to the flat scan instead of going silent",
        "---\nname: s\nallowed-tools: Read\n---\nRead it:\n```yaml\na: b\n```bash\nls\n",
        ["Bash"], [], [], [], False,
    ),
    (
        "prose and fence together yield one Bash finding, not two",
        "---\nname: s\nallowed-tools: Read\n---\nRead it, then use Bash to run:\n```shell\nls\n```\n",
        ["Bash"], [], [], [], False,
    ),
    (
        "a skill naming the Write Role Contract is its authorised writer, not a violator",
        "---\nname: s\nallowed-tools: Read Write\n---\nVault writes are main-context only (the Write Role Contract), so use Write here. Read first.",
        [], [], [], [], False,
    ),
    (
        "a scoped suffix survives whitespace splitting",
        "---\nname: s\nallowed-tools: Read Bash(git add:*, git commit:*)\n---\nRead it, then use Bash.",
        [], [], [], [], False,
    ),
]


def _norm(values):
    return [sorted(v) if isinstance(v, list) else v for v in values]


# (undeclared, unused, unknown, contract, missing, uncontracted). A case states only the
# leading fields it cares about and the rest fill in from here, so adding a finding at the end
# never touches an existing case.
WANT_DEFAULTS = ([], [], [], [], False, [])
SKILL_KWARGS = {"key": "allowed-tools", "require_key": True, "check_contract": False,
                "shell_fence_implies_bash": True}


def run_self_test():
    cases = [(label, text, {}, list(want) + list(WANT_DEFAULTS[len(want):]))
             for label, text, *want in SELF_TEST_CASES]
    cases += [
        (label, text, SKILL_KWARGS, list(want) + list(WANT_DEFAULTS[len(want):]))
        for label, text, *want in SKILL_SELF_TEST_CASES
    ]
    failures = []
    for label, text, kwargs, want in cases:
        got = check_agent(text, **kwargs)
        if _norm(got) != _norm(want):
            failures.append((label, got, tuple(want)))
    if failures:
        print("FAIL: check-agent-tools-usage self-test")
        for label, got, want in failures:
            print(f"  {label}: got {got}, want {want}")
        return 1
    print(f"OK: all {len(cases)} check-agent-tools-usage self-test cases passed")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    root = args.root or _git_toplevel() or os.getcwd()

    checked, findings = 0, []
    for scope in SCOPES:
        kwargs = {k: v for k, v in scope.items() if k not in ("label", "finder")}
        for path in scope["finder"](root):
            checked += 1
            with open(path, encoding="utf-8") as fh:
                undeclared, unused, unknown, contract, missing, uncontracted = check_agent(
                    fh.read(), **kwargs
                )
            if undeclared or unused or unknown or contract or missing or uncontracted:
                findings.append({
                    "file": os.path.relpath(path, root),
                    "kind": scope["label"],
                    "key": scope["key"],
                    "undeclared": undeclared,
                    "unused": unused,
                    "unknown": unknown,
                    "contract": contract,
                    "missing": missing,
                    "uncontracted": uncontracted,
                })

    if not checked:
        print(
            f"ERROR: no */agents/*.md or */skills/*/SKILL.md files found under {root}",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps({"checked": checked, "findings": findings}, indent=2))
    elif findings:
        print("FAIL: declared tools do not match body usage:")
        for f in findings:
            key = f["key"]
            print(f"  {f['file']}")
            if f["missing"]:
                print(f"    no `{key}:` — inherits every tool in the harness")
            if f["undeclared"]:
                print(f"    body calls but {key}: omits — {', '.join(f['undeclared'])}")
            if f["unused"]:
                print(f"    {key}: grants but body never names — {', '.join(f['unused'])}")
            if f["unknown"]:
                print(f"    unknown tool name — {', '.join(f['unknown'])}")
            if f["contract"]:
                print(f"    body claims read-only but grants — {', '.join(f['contract'])}")
            if f["uncontracted"]:
                print("    vault agent never names the Write Role Contract but grants — "
                      f"{', '.join(f['uncontracted'])}")
    else:
        print(f"OK: all {checked} agent(s)/skill(s) declare exactly the tools their body uses")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
