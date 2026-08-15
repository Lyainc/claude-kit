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

A bare (unqualified) name in a call is checked inside this repo only, where a sibling skill is the
only thing it can mean. Outside, a bare name is more often a machine-level skill this repo knows
nothing about, so it is skipped.

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

# Matches `Skill(skill: "x")` and `Skill(skill: 'x', args: ...)` alike.
CALL_RE = re.compile(r"""Skill\(\s*skill:\s*["']([^"']+)["']""")
NAME_KEY_RE = re.compile(r"^name:[ \t]*(\S+)", re.MULTILINE)


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


def scan_text(text, qual_re, wide, is_shell):
    """Yield (lineno, ref) for every skill reference in one file's text.

    `wide` (external roots) counts every qualified token, prose included. Inside the repo it is
    off, so only the call form plus — in a shell file — the matcher surface counts.
    """
    for lineno, line in enumerate(text.splitlines(), 1):
        seen = set()
        for m in CALL_RE.finditer(line):
            seen.add(m.group(1))
        if qual_re is not None and (wide or is_shell):
            for m in qual_re.finditer(line):
                seen.add(m.group(0))
        for ref in sorted(seen):
            yield lineno, ref


def resolve(ref, catalog, allow_bare):
    """Return None when the reference resolves, else a reason string."""
    if ":" in ref:
        plugin, _, name = ref.partition(":")
        if plugin not in catalog:
            return None  # another marketplace's plugin — not this repo's to judge
        if name in catalog[plugin]:
            return None
        return f"no {plugin}/skills/*/SKILL.md declares `name: {name}`"
    if not allow_bare:
        return None
    if any(ref in names for names in catalog.values()):
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

    findings, fired, files, refs = [], set(), 0, 0
    scanned_paths = []
    for top, wide in surfaces:
        for path in iter_files(top):
            files += 1
            scanned_paths.append(path)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for lineno, ref in scan_text(text, qual_re, wide, path.endswith(".sh")):
                refs += 1
                problem = resolve(ref, catalog, allow_bare=not wide)
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

    def case(label, got, want):
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

    if failures:
        print("FAIL: check-skill-reference-drift self-test")
        print("\n".join(failures))
        return 1
    print("OK: all 13 check-skill-reference-drift self-test cases passed")
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
