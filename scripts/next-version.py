#!/usr/bin/env python3
"""next-version.py — is main due a release, and at what version?

The release-trigger half of the policy in RELEASING.md. `bump-version.py` writes a
version once someone has decided on one; this script makes that decision, so the
workflow never has to.

Policy (the "why" lives in RELEASING.md; this is the executable form):

  0. PREMISE — **main is always releasable.** An unfinished feature never lands on main;
     it grows on a feature branch and merges when complete. That premise is what lets
     every rule below ignore the question "is the feature done yet?" — it is, always.
     Without it no trigger is safe, and the backstop below would be actively dangerous.

  1. PRIMARY trigger — a PR merged carrying the `release` label. The decision rides on
     the merge the maintainer is already making, so it can never become a separate
     ritual to forget. An explicit label always releases (even a docs-only PR — an
     explicit human "ship this" outranks the default below).

  2. BACKSTOP — N (default 10) unreleased USER-VISIBLE commits. Releases with no label
     at all, so drift cannot silently accumulate. This is the rule that makes v3.0.0's
     failure structurally impossible: it sat 79 commits behind main, three of them
     breaking, because nothing ever forced the question.

  User-visible = `feat` / `fix` / `perf` / `refactor`, plus anything breaking.
  `docs` / `chore` / `test` / `ci` / `build` / `style` are NOT counted toward the
  backstop and never trigger on their own — they ride along in the next release.

Bump, from the same commits, largest change wins (RELEASING.md's SemVer rule):

    breaking (`!` or a BREAKING CHANGE: body)  -> major
    feat                                       -> minor
    any other user-visible commit              -> patch

Usage:
    python3 scripts/next-version.py [--labeled] [--backstop 10] [--to HEAD]
    python3 scripts/next-version.py --self-test

Writes `key=value` lines on stdout, ready for GitHub Actions' $GITHUB_OUTPUT:
    release=true|false
    version=X.Y.Z        (empty when release=false)
    reason=<one line, why it did or didn't fire>
    visible=<count of unreleased user-visible commits>

Exit codes: 0 = decided (release true or false — both are success), 2 = usage/IO error.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Reuse gen-release-notes' Conventional-Commit parsing rather than re-deriving it —
# a second, subtly-different parser is how the two would drift apart.
_spec = importlib.util.spec_from_file_location(
    "gen_release_notes", _REPO_ROOT / "scripts" / "gen-release-notes.py"
)
_grn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_grn)

_HEADER_RE = _grn._HEADER_RE

# Types a user of the marketplace can actually observe. Everything else is internal.
USER_VISIBLE_TYPES = {"feat", "fix", "perf", "refactor"}

DEFAULT_BACKSTOP = 10


def _is_breaking(commit: dict) -> bool:
    m = _HEADER_RE.match(commit.get("subject", ""))
    return bool(m and m.group("bang")) or "BREAKING CHANGE" in (commit.get("body") or "")


def _ctype(commit: dict) -> str | None:
    m = _HEADER_RE.match(commit.get("subject", ""))
    return m.group("type") if m else None


def is_user_visible(commit: dict) -> bool:
    return _ctype(commit) in USER_VISIBLE_TYPES or _is_breaking(commit)


def bump(current: str, commits: list[dict]) -> str:
    """Largest change in the set wins. `current` is the last released version."""
    major, minor, patch = (int(p) for p in current.split(".")[:3])
    if any(_is_breaking(c) for c in commits):
        return f"{major + 1}.0.0"
    if any(_ctype(c) == "feat" for c in commits):
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def decide(commits: list[dict], current: str, labeled: bool,
           backstop: int = DEFAULT_BACKSTOP) -> dict:
    """The whole policy, as a pure function — this is what the self-test pins."""
    visible = [c for c in commits if is_user_visible(c)]

    # Nothing at all since the last tag: there is no release to cut. This is also what
    # keeps the workflow from looping on its own `chore(release):` push.
    if not commits:
        return {"release": False, "version": "", "visible": 0,
                "reason": "no commits since the last tag"}

    if labeled:
        return {"release": True, "version": bump(current, commits), "visible": len(visible),
                "reason": "a PR merged with the `release` label"}

    if len(visible) >= backstop:
        return {"release": True, "version": bump(current, commits), "visible": len(visible),
                "reason": f"backstop: {len(visible)} unreleased user-visible commits (>= {backstop})"}

    return {"release": False, "version": "", "visible": len(visible),
            "reason": (f"no `release` label, and only {len(visible)} user-visible commit(s) "
                       f"since the last tag (backstop is {backstop})")}


def _last_tag(to_ref: str) -> str | None:
    """The last RELEASED tag, inclusive of `to_ref` itself.

    Deliberately not gen-release-notes' `previous_tag()`, which resolves `<ref>^` — it
    wants the tag *before* the one being cut. Here, a tag ON HEAD means everything is
    already released, and treating it as unreleased would re-cut the same commits.
    """
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", to_ref],
            cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except subprocess.CalledProcessError:
        return None  # no tag reachable — the very first release


def _current_version(tag: str | None) -> str:
    """The version we are bumping FROM: the last tag, else the manifest (first release)."""
    if tag:
        m = re.match(r"^v?(\d+\.\d+\.\d+)", tag)
        if m:
            return m.group(1)
    manifest = _REPO_ROOT / ".claude-plugin" / "marketplace.json"
    return json.loads(manifest.read_text())["version"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labeled", action="store_true",
                    help="a PR carrying the `release` label was just merged")
    ap.add_argument("--backstop", type=int, default=DEFAULT_BACKSTOP)
    ap.add_argument("--to", default="HEAD")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        tag = _last_tag(args.to)
        commits = _grn.collect_commits(tag, args.to, cwd=_REPO_ROOT)
    except subprocess.CalledProcessError as exc:
        print(f"error: git failed: {exc}", file=sys.stderr)
        return 2

    result = decide(commits, _current_version(tag), args.labeled, args.backstop)

    for key in ("release", "version", "reason", "visible"):
        value = result[key]
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    print(f"\n{'RELEASE' if result['release'] else 'HOLD'} — {result['reason']}"
          f" (since {tag or '<no tag>'}: {len(commits)} commit(s), "
          f"{result['visible']} user-visible)", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Self-test — the policy is the thing worth pinning, so it is tested as a pure
# function over synthetic commit lists (no git, no network).
# ---------------------------------------------------------------------------

def _c(subject: str, body: str = "") -> dict:
    return {"subject": subject, "body": body}


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def check(name: str, got, want):
        cases.append((f"{name}: got {got!r}, want {want!r}", got == want))

    fix = _c("fix(x): a")
    feat = _c("feat(x): b")
    docs = _c("docs: c")
    chore = _c("chore: d")
    breaking = _c("feat(x)!: e")
    breaking_body = _c("fix(x): f", "BREAKING CHANGE: gone")

    # --- classification ---
    check("fix is user-visible", is_user_visible(fix), True)
    check("feat is user-visible", is_user_visible(feat), True)
    check("docs is NOT user-visible", is_user_visible(docs), False)
    check("chore is NOT user-visible", is_user_visible(chore), False)
    check("breaking `!` is user-visible", is_user_visible(breaking), True)
    check("BREAKING CHANGE body is user-visible", is_user_visible(breaking_body), True)
    check("a non-conventional subject is not user-visible", is_user_visible(_c("wip")), False)

    # --- bump: largest change wins ---
    check("fixes only -> patch", bump("4.0.1", [fix, fix]), "4.0.2")
    check("a feat -> minor", bump("4.0.1", [fix, feat]), "4.1.0")
    check("a breaking `!` -> major", bump("4.0.1", [fix, feat, breaking]), "5.0.0")
    check("a BREAKING CHANGE body -> major", bump("4.0.1", [breaking_body]), "5.0.0")

    # --- the label: primary trigger, always wins ---
    check("labeled + one fix -> release",
          decide([fix], "4.0.1", labeled=True)["version"], "4.0.2")
    check("labeled + docs only -> release anyway (explicit human intent)",
          decide([docs], "4.0.1", labeled=True)["release"], True)
    check("labeled but NOTHING since the tag -> no release (this is the anti-loop guard)",
          decide([], "4.0.1", labeled=True)["release"], False)

    # --- the backstop: fires without a label, counts only user-visible ---
    check("9 fixes, no label -> hold (below the backstop)",
          decide([fix] * 9, "4.0.1", labeled=False)["release"], False)
    check("10 fixes, no label -> release (backstop)",
          decide([fix] * 10, "4.0.1", labeled=False)["release"], True)
    check("10 fixes -> patch bump",
          decide([fix] * 10, "4.0.1", labeled=False)["version"], "4.0.2")
    check("50 docs commits, no label -> hold (docs never count toward the backstop)",
          decide([docs] * 50, "4.0.1", labeled=False)["release"], False)
    check("9 fixes + 50 chores -> still hold (chores don't pad the count)",
          decide([fix] * 9 + [chore] * 50, "4.0.1", labeled=False)["release"], False)
    check("backstop counts breaking commits too",
          decide([breaking] * 10, "4.0.1", labeled=False)["release"], True)
    check("a breaking commit reached via the backstop still majors",
          decide([breaking] + [fix] * 9, "4.0.1", labeled=False)["version"], "5.0.0")
    check("custom backstop respected",
          decide([fix] * 3, "4.0.1", labeled=False, backstop=3)["release"], True)

    # --- docs/chore ride along when something else triggers ---
    check("a labeled release carries the docs commits with it (bump ignores them)",
          decide([docs, chore, feat], "4.0.1", labeled=True)["version"], "4.1.0")

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
