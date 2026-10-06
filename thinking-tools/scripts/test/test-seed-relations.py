#!/usr/bin/env python3
"""Unit tests for seed-relations.py (#780) — tree/check over fixture Seeds.

Covers the fixtures the design names (acceptance items of docs/specs/seed-relations-graph.yaml):
same-repo parent + two children with the refines mapping (acceptance-1), `-vN` resolution
(acceptance-3), the three mismatch kinds plus a refines pointing at a missing id (acceptance-4,
acceptance-8), a failing `gh` (acceptance-6), and depends_on same-repo vs cross-repo
(acceptance-7).
Cross-repo reads go through a `gh` shim written into the temp dir (GH_BIN); every run
defaults GH_BIN to a path that does not exist, so an unintended remote read shows up as a
FAILED line instead of passing silently.

The #792 additions: SOURCE/TRACKING/LINK/ITEM lines in tree, UNRECORDED lines in check (never a
mismatch), and the `walk` subcommand (relation kinds, depth/node caps, cycles, duplicates,
other-repo nodes, JSON/text agreement, walk id and fingerprint).

The identifier convention (thinking-tools/reference/identifiers.md): fixtures use the new
`constraint-N`/`acceptance-N` ids, tree prints `<seed-slug>/<id> · <description>`, and the
explicit legacy fixtures prove an unmigrated `c<N>`/`ac<N>` Seed still tree/check/walks, that
check prints an informational LEGACY line, a refines mismatch caused only by the id form carries
a seed-id-migrate.py hint, and a duplicate item id is a MISMATCH.

Usage: python3 thinking-tools/scripts/test/test-seed-relations.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import atexit
import base64
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = _REPO_ROOT / "thinking-tools" / "scripts" / "seed-relations.py"

_spec = importlib.util.spec_from_file_location("seed_relations", _SCRIPT_PATH)
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)

NO_GH = "/nonexistent/gh"


def _tmp(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    atexit.register(shutil.rmtree, d, ignore_errors=True)
    return d


def _repo(origin=None):
    d = _tmp("test-seed-relations-")
    subprocess.run(["git", "init", "-q"], cwd=d, check=True, capture_output=True)
    if origin:
        subprocess.run(["git", "remote", "add", "origin", origin], cwd=d, check=True,
                       capture_output=True)
    (Path(d) / "docs" / "specs").mkdir(parents=True)
    return d


_AUTO = object()


def _seed_text(target, parent=None, refines=(), depends_on=(), children=(),
               constraints=(), criteria=(), block_lists=False, relations=True,
               source="#1", tracking=(), link_reason=_AUTO):
    """Compose a Seed. Lists go out as flow lists, or as block lists when block_lists is set.

    A recorded `issues.source` ("#1") is the default, and a Seed with a parent gets a recorded
    link_reason; pass source=None / link_reason=None for "not recorded". relations=False is an
    old Seed: no issues block and no relations block at all.
    """
    if link_reason is _AUTO:
        link_reason = "because" if parent else None
    def lst(name, vals):
        if not vals:
            return f"  {name}: []"
        if block_lists:
            return f"  {name}:\n" + "\n".join(f"    - {v}" for v in vals)
        return f"  {name}: [{', '.join(vals)}]"

    lines = ["# Seed Spec", "---", "skill: build-spec", "input:", "  target: not the top-level one",
             f"target: {target}", ""]
    if relations:
        quoted = ", ".join(f'"{t}"' for t in tracking)
        lines += ["issues:",
                  f'  source: {json.dumps(source) if source else "null"}',
                  f"  tracking: [{quoted}]", ""]
        lines += ["relations:            # edges only, never a status",
                  f"  parent: {parent if parent else 'null'}        # parent Seed or null",
                  lst("refines", list(refines)),
                  f"  link_reason: {link_reason if link_reason else 'null'}",
                  lst("depends_on", list(depends_on)),
                  lst("children", list(children)), ""]
    for name, items in (("constraints", constraints), ("success_criteria", criteria)):
        lines.append(f"{name}:")
        for iid, desc in items:
            lines.append(f"  - id: {iid}")
            if len(desc) > 60:
                cut = desc.rfind(" ", 0, 50)  # fold at a word boundary, like a real `>-` block
                lines += ["    description: >-", f"      {desc[:cut]}", f"      {desc[cut + 1:]}"]
            else:
                lines.append(f"    description: {desc}")
            lines.append("    hard: true")
        lines.append("")
    return "\n".join(lines) + "\n"


def _write(repo, name, **kw):
    p = Path(repo) / "docs" / "specs" / name
    p.write_text(_seed_text(**kw))
    return f"docs/specs/{name}"


def _run(repo, cmd, rel, gh=NO_GH):
    env = dict(os.environ, GH_BIN=gh)
    p = subprocess.run([sys.executable, str(_SCRIPT_PATH), cmd, rel], cwd=repo, env=env,
                       capture_output=True, text=True)
    return p.returncode, p.stdout.splitlines(), p.stderr


def _snapshot(repo):
    snap = {}
    for f in sorted(Path(repo).rglob("*")):
        if f.is_file() and ".git" not in f.parts:
            snap[str(f.relative_to(repo))] = f.read_bytes()
    return snap


def _gh_shim(files, listing=None):
    """A `gh` that answers `gh api repos/o/r/contents/<path>` from a fixture map.

    files: {"owner/repo:docs/specs/p.yaml": text}. A directory listing is derived from the
    files unless given. Calls are appended to calls.log so a test can assert read-only use.
    """
    d = _tmp("test-seed-relations-gh-")
    table = {}
    for coord, text in files.items():
        repo, path = coord.split(":", 1)
        table[f"repos/{repo}/contents/{path}"] = {
            "content": base64.encodebytes(text.encode()).decode(), "encoding": "base64"}
        dirpath, name = path.rsplit("/", 1)
        table.setdefault(f"repos/{repo}/contents/{dirpath}", []).append({"name": name})
    (Path(d) / "table.json").write_text(json.dumps(table))
    shim = Path(d) / "gh"
    shim.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "here = os.path.dirname(os.path.abspath(__file__))\n"
        "open(os.path.join(here, 'calls.log'), 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        "table = json.load(open(os.path.join(here, 'table.json')))\n"
        "ep = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == 'api' else ''\n"
        "if ep in table:\n"
        "    print(json.dumps(table[ep]))\n"
        "else:\n"
        "    sys.stderr.write('gh: Not Found (HTTP 404)\\n')\n"
        "    sys.exit(1)\n")
    shim.chmod(0o755)
    return str(shim), Path(d) / "calls.log"


def _gh_fail_shim():
    d = _tmp("test-seed-relations-ghfail-")
    shim = Path(d) / "gh"
    shim.write_text("#!/bin/sh\necho 'gh: HTTP 401: Bad credentials' >&2\necho 'second line' >&2\nexit 1\n")
    shim.chmod(0o755)
    return str(shim)


LONG = ("The parent constraint is deliberately long so that the tree output has to cut its "
        "description at one hundred characters and mark the cut")

PARENT_FIXTURE = dict(
    target="Parent feature",
    children=["docs/specs/child-a.yaml", "docs/specs/child-b.yaml"],
    constraints=[("constraint-1", LONG), ("constraint-2", "Second constraint")],
    criteria=[("acceptance-1", "First criterion"), ("acceptance-2", "Second criterion")],
)


def check_tree_same_repo() -> list[str]:
    """acceptance-1: one named child yields parent, refines mapping, sibling, and PARENT-ITEM refiners."""
    failures = []
    repo = _repo()
    _write(repo, "parent.yaml", **PARENT_FIXTURE)
    _write(repo, "child-a.yaml", target="Child A", parent="docs/specs/parent.yaml",
           refines=["constraint-1", "acceptance-1", "constraint-9"])
    _write(repo, "child-b.yaml", target="Child B", parent="docs/specs/parent.yaml",
           refines=["constraint-2"], block_lists=True)
    before = _snapshot(repo)
    code, out, err = _run(repo, "tree", "docs/specs/child-a.yaml")
    long_cut = LONG[:100] + "..."
    expected = [
        "SEED      docs/specs/child-a.yaml  (target: Child A)",
        "SOURCE    #1",
        "TRACKING  (없음)",
        "PARENT    docs/specs/parent.yaml",
        f"REFINES   parent/constraint-1 · {long_cut}",
        "REFINES   parent/acceptance-1 · First criterion",
        "REFINES   parent/constraint-9 · [missing in parent]",
        "LINK      because",
        "SIBLING   docs/specs/child-b.yaml  (target: Child B)",
        f"PARENT-ITEM parent/constraint-1 · {long_cut}  refined by: docs/specs/child-a.yaml",
        "PARENT-ITEM parent/constraint-2 · Second constraint  refined by: docs/specs/child-b.yaml",
        "PARENT-ITEM parent/acceptance-1 · First criterion  refined by: docs/specs/child-a.yaml",
        "PARENT-ITEM parent/acceptance-2 · Second criterion  refined by: (none)",
    ]
    if code != 0 or out != expected:
        failures.append(f"tree same repo: exit {code}, err {err!r}\nexpected:\n  " +
                        "\n  ".join(expected) + "\ngot:\n  " + "\n  ".join(out))
    if any("FAILED" in ln for ln in out):
        failures.append("tree same repo: a same-repo read must never touch gh")
    if _snapshot(repo) != before:
        failures.append("tree same repo: the script changed files (it must be read-only)")

    # Block-list child seen from the other side: block lists parse the same as flow lists.
    code, out, _ = _run(repo, "tree", "docs/specs/child-b.yaml")
    if "REFINES   parent/constraint-2 · Second constraint" not in out:
        failures.append(f"tree block-list child: REFINES constraint-2 missing: {out}")
    if "SIBLING   docs/specs/child-a.yaml  (target: Child A)" not in out:
        failures.append(f"tree block-list child: sibling child-a missing: {out}")

    # The parent itself: children are listed, no PARENT, and no status-like value anywhere.
    code, out, _ = _run(repo, "tree", "docs/specs/parent.yaml")
    if "PARENT    (none)" not in out or not any(
            ln.startswith("CHILD     docs/specs/child-a.yaml") for ln in out):
        failures.append(f"tree parent: expected PARENT (none) and CHILD lines: {out}")
    for ln in out:
        if any(w in ln.lower() for w in ("done", "pending", "satisfied", "status")):
            failures.append(f"tree parent: output must carry no status value: {ln!r}")
    return failures


def check_tree_no_relations_block() -> list[str]:
    """A Seed with no relations block reads as PARENT (none) without crashing."""
    failures = []
    repo = _repo()
    _write(repo, "old.yaml", target="Old seed", relations=False)
    code, out, err = _run(repo, "tree", "docs/specs/old.yaml")
    want = ["SEED      docs/specs/old.yaml  (target: Old seed)",
            "SOURCE    (기록 없음 — 미확인)", "TRACKING  (없음)", "PARENT    (none)"]
    if code != 0 or out != want:
        failures.append(f"no relations block: exit {code}, out {out}, err {err!r}")
    return failures


def check_version_resolution() -> list[str]:
    """acceptance-3: foo.yaml + foo-v2.yaml both present, the child's parent edge resolves to -v2."""
    failures = []
    repo = _repo()
    _write(repo, "foo.yaml", target="Foo v1", children=["docs/specs/kid.yaml"],
           constraints=[("constraint-1", "Old wording")])
    _write(repo, "foo-v2.yaml", target="Foo v2", children=["docs/specs/kid.yaml"],
           constraints=[("constraint-1", "New wording")])
    _write(repo, "kid.yaml", target="Kid", parent="docs/specs/foo.yaml", refines=["constraint-1"])
    code, out, _ = _run(repo, "tree", "docs/specs/kid.yaml")
    for want in ("PARENT    docs/specs/foo.yaml -> docs/specs/foo-v2.yaml",
                 "REFINES   foo/constraint-1 · New wording"):
        if want not in out:
            failures.append(f"version resolution: missing {want!r} in {out}")
    code, out, _ = _run(repo, "check", "docs/specs/kid.yaml")
    if (code, out) != (0, ["OK: 2 edge(s) consistent"]):
        failures.append(f"version resolution check: expected consistent via -v2, got {code} {out}")

    names = ["foo.yaml", "foo-v2.yaml", "foo-v10.yaml", "foobar.yaml", "foo-v2-x.yaml"]
    cases = [
        (("docs/specs/foo.yaml"), "docs/specs/foo-v10.yaml"),
        (("docs/specs/foo-v2.yaml"), "docs/specs/foo-v10.yaml"),
        (("docs/specs/other.yaml"), "docs/specs/other.yaml"),
    ]
    for path, want in cases:
        got = sr.pick_latest(names, path)
        if got != want:
            failures.append(f"pick_latest({path!r}): expected {want!r}, got {got!r}")
    if sr.pick_latest(["foo.yaml"], "docs/specs/foo.yaml") != "docs/specs/foo.yaml":
        failures.append("pick_latest: an unversioned file alone must resolve to itself")
    return failures


def _cross_fixture():
    """A repo whose origin is acme/child-repo, plus a Seed naming a cross-repo parent."""
    repo = _repo(origin="https://github.com/acme/child-repo.git")
    _write(repo, "c3.yaml", target="Cross child", parent="acme/parent-repo:docs/specs/p.yaml",
           refines=["constraint-1"])
    return repo


def check_mismatch_kinds() -> list[str]:
    """acceptance-4, acceptance-8: the three mismatch kinds and a refines pointing at a missing id."""
    failures = []
    repo = _cross_fixture()

    # 1. child names parent, parent's children lacks the child.
    _write(repo, "p1.yaml", target="P1", children=[], constraints=[("constraint-1", "x")])
    _write(repo, "c1.yaml", target="C1", parent="docs/specs/p1.yaml", refines=["constraint-1"])
    code, out, _ = _run(repo, "check", "docs/specs/c1.yaml")
    want = ["MISMATCH  docs/specs/p1.yaml children is missing docs/specs/c1.yaml",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"mismatch child->parent: expected (1, {want}), got ({code}, {out})")

    # 2. parent lists the child, the child's parent does not point back.
    _write(repo, "p2.yaml", target="P2", children=["docs/specs/c2.yaml"])
    _write(repo, "c2.yaml", target="C2", parent=None)
    code, out, _ = _run(repo, "check", "docs/specs/p2.yaml")
    want = ["MISMATCH  docs/specs/c2.yaml parent does not point back to docs/specs/p2.yaml",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"mismatch parent->child: expected (1, {want}), got ({code}, {out})")

    # 3. cross-repo parent whose children lacks this child (read through the gh shim).
    p_text = _seed_text("Remote parent", children=["docs/specs/other.yaml"],
                        constraints=[("constraint-1", "Remote c1")])
    gh, calls = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_text})
    code, out, _ = _run(repo, "check", "docs/specs/c3.yaml", gh=gh)
    want = ["MISMATCH  acme/parent-repo:docs/specs/p.yaml children is missing "
            "acme/child-repo:docs/specs/c3.yaml — 부모 레포에서 추가 필요",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"mismatch cross-repo: expected (1, {want}), got ({code}, {out})")
    for ln in calls.read_text().splitlines() if calls.exists() else []:
        if not ln.startswith("api repos/") or "-X" in ln or "--method" in ln or "-f " in ln:
            failures.append(f"cross-repo read must be plain GET api calls, saw: {ln!r}")

    # ...and the same parent, once it lists the child by coordinate, is consistent.
    p_ok = _seed_text("Remote parent", children=["acme/child-repo:docs/specs/c3.yaml"],
                      constraints=[("constraint-1", "Remote c1")])
    gh, _ = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_ok})
    code, out, _ = _run(repo, "check", "docs/specs/c3.yaml", gh=gh)
    if (code, out) != (0, ["OK: 2 edge(s) consistent"]):
        failures.append(f"cross-repo consistent: expected (0, OK 2), got ({code}, {out})")

    # 4. refines pointing at an id the parent does not define (acceptance-8).
    _write(repo, "p4.yaml", target="P4", children=["docs/specs/c4.yaml"],
           constraints=[("constraint-1", "x")])
    _write(repo, "c4.yaml", target="C4", parent="docs/specs/p4.yaml", refines=["constraint-1", "constraint-9"])
    code, out, _ = _run(repo, "check", "docs/specs/c4.yaml")
    want = ["MISMATCH  docs/specs/c4.yaml refines constraint-9, which docs/specs/p4.yaml does not define",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"mismatch refines: expected (1, {want}), got ({code}, {out})")

    # A consistent same-repo pair is OK with exit 0.
    _write(repo, "p5.yaml", target="P5", children=["docs/specs/c5.yaml"],
           constraints=[("constraint-1", "x")])
    _write(repo, "c5.yaml", target="C5", parent="docs/specs/p5.yaml", refines=["constraint-1"])
    for name in ("c5", "p5"):
        code, out, _ = _run(repo, "check", f"docs/specs/{name}.yaml")
        n = 2 if name == "c5" else 1
        if (code, out) != (0, [f"OK: {n} edge(s) consistent"]):
            failures.append(f"consistent pair ({name}): got ({code}, {out})")
    return failures


def check_gh_failure() -> list[str]:
    """acceptance-6: a failing gh prints an explicit FAILED line; the section is never empty."""
    failures = []
    repo = _cross_fixture()
    _write(repo, "sib.yaml", target="Sibling", parent="docs/specs/local-parent.yaml")
    gh = _gh_fail_shim()
    line = ("[seed-relations FAILED] acme/parent-repo:docs/specs/p.yaml — "
            "gh api: gh: HTTP 401: Bad credentials")

    code, out, _ = _run(repo, "tree", "docs/specs/c3.yaml", gh=gh)
    want = ["SEED      docs/specs/c3.yaml  (target: Cross child)",
            "SOURCE    #1",
            "TRACKING  (없음)",
            "PARENT    acme/parent-repo:docs/specs/p.yaml" + sr.LINK_ONLY,
            line,
            "REFINES   acme/parent-repo:p/constraint-1 · [parent unreadable]",
            "LINK      because"]
    if code != 0 or out != want:
        failures.append(f"gh failure tree: exit {code}\nexpected:\n  " + "\n  ".join(want) +
                        "\ngot:\n  " + "\n  ".join(out))

    code, out, _ = _run(repo, "check", "docs/specs/c3.yaml", gh=gh)
    if code != 2 or out != [line, "OK: 0 edge(s) consistent"]:
        failures.append(f"gh failure check: expected exit 2 with the FAILED line, got {code} {out}")

    # gh missing entirely is a failure line too, not an empty result.
    code, out, _ = _run(repo, "tree", "docs/specs/c3.yaml", gh=NO_GH)
    if not any(ln.startswith("[seed-relations FAILED] acme/parent-repo:docs/specs/p.yaml — gh api: ")
               and "not found" in ln for ln in out):
        failures.append(f"gh missing: expected a FAILED line mentioning 'not found', got {out}")

    # A failure on one edge does not stop the remaining edges from being read.
    _write(repo, "mixed.yaml", target="Mixed", parent="acme/parent-repo:docs/specs/p.yaml",
           children=["docs/specs/sib.yaml"])
    code, out, _ = _run(repo, "tree", "docs/specs/mixed.yaml", gh=gh)
    if line not in out or not any(ln.startswith("CHILD     docs/specs/sib.yaml") for ln in out):
        failures.append(f"gh failure keeps going: expected FAILED line and the CHILD line, got {out}")
    return failures


def check_depends_on() -> list[str]:
    """acceptance-7: a sibling's depends_on prints `requires`, tagged same-repo or cross-repo."""
    failures = []
    repo = _repo()
    kids = [f"docs/specs/child-{c}.yaml" for c in "abcd"]
    _write(repo, "parent.yaml", target="Parent", children=kids)
    _write(repo, "child-a.yaml", target="Child A", parent="docs/specs/parent.yaml",
           depends_on=["docs/specs/other.yaml"])
    _write(repo, "child-b.yaml", target="Child B", parent="docs/specs/parent.yaml")
    _write(repo, "child-c.yaml", target="Child C", parent="docs/specs/parent.yaml",
           depends_on=["docs/specs/child-b.yaml"])
    _write(repo, "child-d.yaml", target="Child D", parent="docs/specs/parent.yaml",
           depends_on=["acme/other:docs/specs/x.yaml"])
    _write(repo, "other.yaml", target="Other")
    code, out, _ = _run(repo, "tree", "docs/specs/child-a.yaml")
    want = [
        "SIBLING   docs/specs/child-b.yaml  (target: Child B)",
        "SIBLING   docs/specs/child-c.yaml  (target: Child C)",
        "SIBLING   docs/specs/child-c.yaml  requires docs/specs/child-b.yaml "
        "(same repo — next-goal judges whether it is finished)",
        "SIBLING   docs/specs/child-d.yaml  (target: Child D)",
        "SIBLING   docs/specs/child-d.yaml  requires acme/other:docs/specs/x.yaml "
        "(다른 레포 — 확인 못 함)",
        "SIBLING   docs/specs/other.yaml  (target: Other)",
    ]
    sib = [ln for ln in out if ln.startswith("SIBLING")]
    if sib != want:
        failures.append("depends_on: expected\n  " + "\n  ".join(want) + "\ngot\n  " + "\n  ".join(sib))
    if any("FAILED" in ln for ln in out):
        failures.append(f"depends_on: a cross-repo `requires` must not trigger a gh read: {out}")
    if any(w in ln.lower() for ln in out for w in ("finished:", "pending", "done ")):
        failures.append("depends_on: the script must not print a finished/pending verdict")
    return failures


def check_self_repo_detection() -> list[str]:
    """An scp-style ssh alias origin and a differently-cased coordinate still mean this repo."""
    failures = []
    repo = _repo(origin="git@github-work:Owner/Repo.git")
    _write(repo, "p.yaml", target="Local parent", children=["docs/specs/kid.yaml"],
           constraints=[("constraint-1", "Parent c1")])
    _write(repo, "kid.yaml", target="Kid", parent="owner/repo:docs/specs/p.yaml", refines=["constraint-1"])
    code, out, err = _run(repo, "check", "docs/specs/kid.yaml")
    if (code, out) != (0, ["OK: 2 edge(s) consistent"]):
        failures.append(f"ssh alias origin check: expected (0, OK 2), got ({code}, {out}) {err!r}")
    code, out, _ = _run(repo, "tree", "docs/specs/kid.yaml")
    if "PARENT    docs/specs/p.yaml" not in out or any(
            "FAILED" in ln or sr.LINK_ONLY in ln for ln in out):
        failures.append(f"ssh alias origin tree: the coordinate must read as local, got {out}")

    forms = {
        "https://github.com/Owner/Repo.git": "Owner/Repo",
        "https://ghe.example.com/team/tool": "team/tool",
        "ssh://git@github-alias/owner/repo.git": "owner/repo",
        "ssh://git@host.example.com:2222/owner/repo": "owner/repo",
        "git@github-work:Owner/Repo.git": "Owner/Repo",
        "git@github.com:owner/re.po/": "owner/re.po",
    }
    for url, want in forms.items():
        m = sr.REMOTE_URL.match(url)
        got = f"{m.group(1)}/{m.group(2)}" if m else None
        if got != want:
            failures.append(f"REMOTE_URL({url!r}): expected {want!r}, got {got!r}")
    if sr.REMOTE_URL.match("/some/local/path"):
        failures.append("REMOTE_URL: a bare filesystem path must not parse as owner/repo")

    # Unparseable origin -> `gh repo view` in the repo root; failure -> None, no crash.
    odd = _repo(origin="/some/local/path")
    saved = os.environ.get("GH_BIN")
    try:
        d = _tmp("test-seed-relations-ghview-")
        view = Path(d) / "gh"
        view.write_text("#!/bin/sh\n[ \"$1 $2\" = \"repo view\" ] && echo Acme/Widgets && exit 0\nexit 1\n")
        view.chmod(0o755)
        os.environ["GH_BIN"] = str(view)
        got = sr.origin_coordinate(odd)
        if got != "Acme/Widgets":
            failures.append(f"gh repo view fallback: expected 'Acme/Widgets', got {got!r}")
        os.environ["GH_BIN"] = _gh_fail_shim()
        if sr.origin_coordinate(odd) is not None:
            failures.append("gh repo view fallback: a failing gh must give None")
        os.environ["GH_BIN"] = NO_GH
        if sr.origin_coordinate(odd) is not None:
            failures.append("gh repo view fallback: a missing gh must give None")
    finally:
        if saved is None:
            os.environ.pop("GH_BIN", None)
        else:
            os.environ["GH_BIN"] = saved
    return failures


def check_cross_repo_link_only() -> list[str]:
    """Lines whose Seed lives in another repo carry the link-only mark; same-repo ones do not."""
    failures = []
    repo = _cross_fixture()
    p_text = _seed_text("Remote parent",
                        children=["acme/child-repo:docs/specs/c3.yaml", "docs/specs/sib.yaml"],
                        constraints=[("constraint-1", "Remote c1")])
    sib_text = _seed_text("Remote sibling", parent="docs/specs/p.yaml")
    gh, _ = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_text,
                      "acme/parent-repo:docs/specs/sib.yaml": sib_text})
    code, out, _ = _run(repo, "tree", "docs/specs/c3.yaml", gh=gh)
    mark = sr.LINK_ONLY
    want = [
        f"PARENT    acme/parent-repo:docs/specs/p.yaml{mark}",
        f"SIBLING   acme/parent-repo:docs/specs/sib.yaml  (target: Remote sibling){mark}",
        f"PARENT-ITEM acme/parent-repo:p/constraint-1 · Remote c1  refined by: docs/specs/c3.yaml{mark}",
    ]
    for w in want:
        if w not in out:
            failures.append(f"link-only mark: missing {w!r} in {out}")
    if any(mark in ln for ln in out if ln.startswith(("SEED", "REFINES", "CHILD"))):
        failures.append(f"link-only mark: only PARENT/PARENT-ITEM/SIBLING lines carry it: {out}")

    # Same-repo lines never carry it.
    local = _repo()
    _write(local, "parent.yaml", target="Parent", children=["docs/specs/kid.yaml", "docs/specs/sib.yaml"],
           constraints=[("constraint-1", "x")])
    _write(local, "kid.yaml", target="Kid", parent="docs/specs/parent.yaml", refines=["constraint-1"])
    _write(local, "sib.yaml", target="Sib", parent="docs/specs/parent.yaml")
    code, out, _ = _run(local, "tree", "docs/specs/kid.yaml")
    if any(sr.LINK_ONLY in ln for ln in out):
        failures.append(f"link-only mark: a same-repo tree must not carry it: {out}")
    return failures


def check_newer_generation_note() -> list[str]:
    """Naming foo.yaml while foo-v2.yaml exists: a NOTE line, and foo.yaml stays the Seed described."""
    failures = []
    repo = _repo()
    _write(repo, "foo.yaml", target="Foo v1", constraints=[("constraint-1", "Old")])
    _write(repo, "foo-v2.yaml", target="Foo v2", constraints=[("constraint-1", "New")])
    want = "NOTE      newer generation exists: docs/specs/foo-v2.yaml"
    code, out, _ = _run(repo, "tree", "docs/specs/foo.yaml")
    if code != 0 or out[:5] != ["SEED      docs/specs/foo.yaml  (target: Foo v1)", want,
                                "SOURCE    #1", "TRACKING  (없음)", "PARENT    (none)"]:
        failures.append(f"newer generation tree: expected SEED foo.yaml then NOTE, got {out}")
    code, out, _ = _run(repo, "check", "docs/specs/foo.yaml")
    if (code, out) != (0, [want, "OK: 0 edge(s) consistent"]):
        failures.append(f"newer generation check: expected the NOTE line first, got {code} {out}")
    code, out, _ = _run(repo, "tree", "docs/specs/foo-v2.yaml")
    if any(ln.startswith("NOTE") for ln in out):
        failures.append(f"newer generation: the latest file must carry no NOTE, got {out}")
    return failures


def check_usage_and_parser() -> list[str]:
    """A named Seed is required (seed-relations-graph/constraint-7); the reader handles comments, quotes and block scalars."""
    failures = []
    repo = _repo()
    for argv in ([], ["tree"], ["bogus", "x"], ["tree", "docs/specs/missing.yaml"],
                 ["walk"], ["walk", "docs/specs/missing.yaml"], ["walk", "--json"],
                 ["tree", "docs/specs/missing.yaml", "--json"]):
        p = subprocess.run([sys.executable, str(_SCRIPT_PATH), *argv], cwd=repo,
                           capture_output=True, text=True)
        if p.returncode != 2 or p.stdout:
            failures.append(f"usage {argv}: expected exit 2 and empty stdout, got {p.returncode} {p.stdout!r}")

    text = ("target: 'Quoted: target'\n"
            "relations:\n"
            "  parent: \"docs/specs/p.yaml\"   # trailing comment\n"
            "  refines:\n"
            "    - c1   # first\n"
            "    - 'ac2'\n"
            "  depends_on: [a.yaml, \"b.yaml\"]\n"
            "  children: []\n"
            "constraints:\n"
            "  - id: c1\n"
            "    description: >-\n"
            "      folded line one\n"
            "      folded line two\n"
            "    hard: true\n"
            "success_criteria:\n"
            "  - id: ac2\n"
            "    description: plain\n")
    s = sr.parse_seed(text)
    got = (s.target, s.parent, s.refines, s.depends_on, s.children, s.items)
    want = ("Quoted: target", "docs/specs/p.yaml", ["c1", "ac2"], ["a.yaml", "b.yaml"], [],
            [("c1", "folded line one folded line two"), ("ac2", "plain")])
    if got != want:
        failures.append(f"parse_seed: expected {want}, got {got}")
    if (s.link_reason, s.source, s.tracking) != (None, None, []):
        failures.append("parse_seed: an old Seed (no issues/link_reason) must read as not recorded")

    text = ("target: t\n"
            "issues:\n"
            "  source: \"acme/repo#7\"   # the issue that asked for it\n"
            "  tracking:\n"
            "    - \"#8\"\n"
            "    - acme/other#9\n"
            "relations:\n"
            "  parent: null\n"
            "  link_reason: >-\n"
            "    first half\n"
            "    second half\n"
            "  children: []\n")
    s = sr.parse_seed(text)
    got = (s.source, s.tracking, s.link_reason)
    want = ("acme/repo#7", ["#8", "acme/other#9"], "first half second half")
    if got != want:
        failures.append(f"parse_seed issues/link_reason: expected {want}, got {got}")
    s = sr.parse_seed("issues:\n  source: null\n  tracking: []\nrelations:\n  link_reason: null\n")
    if (s.source, s.tracking, s.link_reason) != (None, [], None):
        failures.append("parse_seed: null source/link_reason must read as None")
    return failures


def check_tree_item_mapping() -> list[str]:
    """Tree from a parent: each own item maps to the child Seeds refining it (parent -> child)."""
    failures = []
    repo = _repo()
    _write(repo, "parent.yaml", target="Parent",
           children=["docs/specs/child-a.yaml", "docs/specs/child-b.yaml", "docs/specs/gone.yaml"],
           constraints=[("constraint-1", "First"), ("constraint-2", "Second")], criteria=[("acceptance-1", "Third")])
    _write(repo, "child-a.yaml", target="A", parent="docs/specs/parent.yaml", refines=["constraint-1"])
    _write(repo, "child-b.yaml", target="B", parent="docs/specs/parent.yaml", refines=["constraint-1", "acceptance-1"])
    before = _snapshot(repo)
    code, out, err = _run(repo, "tree", "docs/specs/parent.yaml")
    want = [
        "CHILD     docs/specs/child-a.yaml  refines: parent/constraint-1",
        "CHILD     docs/specs/child-b.yaml  refines: parent/constraint-1, parent/acceptance-1",
        "CHILD     docs/specs/gone.yaml  [file not found]",
        "ITEM      parent/constraint-1 · First  refined by: docs/specs/child-a.yaml, "
        "docs/specs/child-b.yaml",
        "ITEM      parent/constraint-2 · Second  refined by: (none)",
        "ITEM      parent/acceptance-1 · Third  refined by: docs/specs/child-b.yaml",
        "ITEM      (unreadable child docs/specs/gone.yaml — 대응 미확인)",
    ]
    got = [ln for ln in out if ln.startswith(("CHILD", "ITEM"))]
    if code != 0 or got != want:
        failures.append("tree item mapping: expected\n  " + "\n  ".join(want) + "\ngot\n  " +
                        "\n  ".join(got) + f"\nexit {code} {err!r}")
    if any(ln.startswith("LINK") for ln in out):
        failures.append(f"tree item mapping: a Seed with no parent prints no LINK line: {out}")
    if _snapshot(repo) != before:
        failures.append("tree item mapping: the script changed files")

    # A child with no children prints no ITEM line at all.
    code, out, _ = _run(repo, "tree", "docs/specs/child-a.yaml")
    if any(ln.startswith("ITEM") for ln in out):
        failures.append(f"tree item mapping: a leaf Seed has no ITEM lines: {out}")
    return failures


def check_tree_link_source_tracking() -> list[str]:
    """Tree from a child: SOURCE, TRACKING and LINK are printed; a missing reason says 미확인."""
    failures = []
    repo = _repo()
    _write(repo, "parent.yaml", target="Parent", constraints=[("constraint-1", "x")],
           children=["docs/specs/ok.yaml", "docs/specs/noreason.yaml", "docs/specs/empty.yaml"])
    _write(repo, "ok.yaml", target="Ok", parent="docs/specs/parent.yaml", refines=["constraint-1"],
           source="#12", tracking=["#13", "acme/x#4"], link_reason="spells out constraint-1 for the API")
    _write(repo, "noreason.yaml", target="NoReason", parent="docs/specs/parent.yaml",
           refines=["constraint-1"], link_reason=None, source=None)
    _write(repo, "empty.yaml", target="Empty", parent="docs/specs/parent.yaml", link_reason=None)

    code, out, _ = _run(repo, "tree", "docs/specs/ok.yaml")
    for want in ("SOURCE    #12", "TRACKING  #13, acme/x#4", "LINK      spells out constraint-1 for the API"):
        if want not in out:
            failures.append(f"tree link/source: missing {want!r} in {out}")

    code, out, _ = _run(repo, "tree", "docs/specs/noreason.yaml")
    for want in ("SOURCE    (기록 없음 — 미확인)", "LINK      (기록 없음 — 미확인)"):
        if want not in out:
            failures.append(f"tree no reason: missing {want!r} in {out}")

    code, out, _ = _run(repo, "tree", "docs/specs/empty.yaml")
    if "LINK      (기록 없음 — 미확인; 대응 부모 항목도 비어 있음)" not in out:
        failures.append(f"tree empty refines + no reason: expected the double-empty LINK line: {out}")

    # LINK sits right after the REFINES lines (and before SIBLING).
    code, out, _ = _run(repo, "tree", "docs/specs/ok.yaml")
    tags = [ln.split()[0] for ln in out]
    if tags.index("LINK") != max(i for i, t in enumerate(tags) if t == "REFINES") + 1:
        failures.append(f"tree link/source: LINK must follow the REFINES lines: {out}")
    return failures


def check_unrecorded() -> list[str]:
    """check reports unrecorded link_reason / issues.source, and the exit code is unchanged."""
    failures = []
    repo = _repo()
    _write(repo, "p.yaml", target="P", children=["docs/specs/c.yaml"], constraints=[("constraint-1", "x")])
    _write(repo, "c.yaml", target="C", parent="docs/specs/p.yaml", refines=["constraint-1"])
    code, base, _ = _run(repo, "check", "docs/specs/c.yaml")
    if (code, base) != (0, ["OK: 2 edge(s) consistent"]):
        failures.append(f"unrecorded baseline: expected a clean OK, got {code} {base}")

    _write(repo, "c.yaml", target="C", parent="docs/specs/p.yaml", refines=["constraint-1"],
           link_reason=None, source=None)
    code, out, _ = _run(repo, "check", "docs/specs/c.yaml")
    want = ["UNRECORDED docs/specs/c.yaml link_reason is not recorded (미확인 — 추측해 채우지 않음)",
            "UNRECORDED docs/specs/c.yaml issues.source is not recorded",
            "OK: 2 edge(s) consistent"]
    if (code, out) != (0, want):
        failures.append(f"unrecorded: expected (0, {want}), got ({code}, {out})")

    # A Seed with no parent has no link_reason to record; only the source line shows.
    code, out, _ = _run(repo, "check", "docs/specs/p.yaml")
    if (code, out) != (0, ["OK: 1 edge(s) consistent"]):
        failures.append(f"unrecorded parent-less recorded source: got {code} {out}")
    _write(repo, "old.yaml", target="Old", relations=False)
    code, out, _ = _run(repo, "check", "docs/specs/old.yaml")
    if (code, out) != (0, ["UNRECORDED docs/specs/old.yaml issues.source is not recorded",
                           "OK: 0 edge(s) consistent"]):
        failures.append(f"unrecorded old seed: got {code} {out}")

    # With a real mismatch the exit code is still 1, and the UNRECORDED lines are still there.
    _write(repo, "p.yaml", target="P", children=[], constraints=[("constraint-1", "x")])
    code, out, _ = _run(repo, "check", "docs/specs/c.yaml")
    if code != 1 or out[-1] != "FOUND: 1 mismatch(es)" or sum(
            ln.startswith("UNRECORDED") for ln in out) != 2:
        failures.append(f"unrecorded + mismatch: expected exit 1 with both UNRECORDED lines: {code} {out}")
    return failures


# ---------------------------------------------------------------------------
# walk
# ---------------------------------------------------------------------------

SP = "docs/specs/"


def _walk_specs():
    """gp -> p -> s (start) -> gc; sib under p; aunt under gp; predecessors off s/sib/gc/aunt."""
    def at(*names):
        return [f"{SP}{n}.yaml" for n in names]

    return {
        "gp": dict(target="Grandparent", children=at("p", "aunt"), constraints=[("constraint-1", "gp item")]),
        "p": dict(target="Parent", parent=SP + "gp.yaml", refines=["constraint-1"], children=at("s", "sib"),
                  constraints=[("constraint-1", "p c1")], criteria=[("acceptance-1", "p ac1")]),
        "s": dict(target="Start", parent=SP + "p.yaml", refines=["constraint-1"], children=at("gc"),
                  depends_on=at("pre"), constraints=[("constraint-1", "s c1")], criteria=[("acceptance-1", "s ac1")]),
        "gc": dict(target="Grandchild", parent=SP + "s.yaml", refines=["acceptance-1"],
                   depends_on=at("pre3")),
        "sib": dict(target="Sibling", parent=SP + "p.yaml", depends_on=at("pre2"), link_reason=None),
        "aunt": dict(target="Aunt", parent=SP + "gp.yaml", depends_on=at("pre")),
        "pre": dict(target="Predecessor v1"),
        "pre-v2": dict(target="Predecessor v2", depends_on=at("pprev")),
        "pprev": dict(target="Predecessor of predecessor"),
        "pre2": dict(target="Predecessor two"),
        "pre3": dict(target="Predecessor three"),
    }


def _walk_fixture(origin=None, **override):
    repo = _repo(origin=origin)
    for name, kw in _walk_specs().items():
        _write(repo, f"{name}.yaml", **dict(kw, **override.get(name, {})))
    return repo


def _walk(repo, rel, *flags, gh=NO_GH):
    env = dict(os.environ, GH_BIN=gh)
    p = subprocess.run([sys.executable, str(_SCRIPT_PATH), "walk", rel, *flags], cwd=repo,
                       env=env, capture_output=True, text=True)
    return p.returncode, p.stdout.splitlines(), p.stderr


def _recs(lines):
    """Text output -> {tag: [fields...]} with each record's tab-separated fields."""
    out = {}
    for ln in lines:
        f = ln.split("\t")
        out.setdefault(f[0], []).append(f)
    return out


def _walk_json(repo, rel, *flags, gh=NO_GH):
    code, out, err = _walk(repo, rel, "--json", *flags, gh=gh)
    return code, (json.loads("\n".join(out)) if out else None), err


def check_walk_kinds() -> list[str]:
    """Relation kinds, depths, via paths, -vN resolution, ITEM mapping, DUP on the full fixture."""
    failures = []
    repo = _walk_fixture()
    # `pre.yaml` and `pre-v2.yaml` both exist: every edge to pre.yaml must land on -v2.
    before = _snapshot(repo)
    code, out, err = _walk(repo, SP + "s.yaml")
    if code != 0:
        return [f"walk kinds: exit {code} {err!r}"]
    r = _recs(out)
    nodes = {f[3]: f for f in r["NODE"]}

    def n(name):
        return SP + name + ".yaml"

    want = {  # key -> (depth, relation, via steps)
        "s": (0, "start", []),
        "p": (1, "ancestor", ["parent", n("p")]),
        "gc": (1, "descendant", ["children", n("gc")]),
        "pre-v2": (1, "predecessor", ["depends_on", n("pre-v2")]),
        "gp": (2, "ancestor", ["parent", n("p"), "parent", n("gp")]),
        "sib": (2, "ancestor-child", ["parent", n("p"), "children", n("sib")]),
        "pre3": (2, "predecessor", ["children", n("gc"), "depends_on", n("pre3")]),
        "pprev": (2, "predecessor", ["depends_on", n("pre-v2"), "depends_on", n("pprev")]),
        "aunt": (3, "ancestor-child",
                 ["parent", n("p"), "parent", n("gp"), "children", n("aunt")]),
        "pre2": (3, "predecessor", ["parent", n("p"), "children", n("sib"), "depends_on", n("pre2")]),
    }
    if sorted(nodes) != sorted(n(k) for k in want):
        failures.append(f"walk kinds: visited {sorted(nodes)} != expected {sorted(n(k) for k in want)}")
    if n("pre") in nodes:
        failures.append("walk kinds: edges must resolve to the latest -vN (pre.yaml -> pre-v2.yaml)")
    for name, (depth, relation, via) in want.items():
        f = nodes.get(n(name))
        if f is None:
            continue
        via_text = ">".join(via) if via else "-"
        if (f[1], f[2], f[4], f[5]) != (str(depth), relation, "ok", "via=" + via_text):
            failures.append(f"walk kinds {name}: got {f[1:6]}, expected "
                            f"{(depth, relation, 'ok', 'via=' + via_text)}")
    # the sibling is never expanded beyond depends_on; its own parent/children are not followed.
    if r["NODE"][0][3] != n("s") or len(r["NODE"]) != 10:
        failures.append(f"walk kinds: start must come first and 10 nodes expected: {r['NODE']}")

    start = nodes[n("s")]
    if start[6:] != ["target=Start", "refines=constraint-1", "link_reason=because", "source=#1", "tracking=-",
                     "items=constraint-1,acceptance-1", "children=" + n("gc")]:
        failures.append(f"walk kinds: start node fields wrong: {start[6:]}")
    if nodes[n("gp")][8] != "link_reason=-":
        failures.append(f"walk kinds: a root has no link to explain, so '-': {nodes[n('gp')]}")
    unrecorded = [f for f in r["NODE"] if f[8] == "link_reason=미확인"]
    if not unrecorded:
        failures.append("walk kinds: a Seed with a parent and no link_reason must read 미확인")

    items = [tuple(f[1:]) for f in r["ITEM"]]
    want_items = [
        (n("s"), "constraint-1", "refined_by=(none)"), (n("s"), "acceptance-1", "refined_by=" + n("gc")),
        (n("p"), "constraint-1", "refined_by=" + n("s")), (n("p"), "acceptance-1", "refined_by=(none)"),
        (n("gp"), "constraint-1", "refined_by=" + n("p")),
    ]
    if items != want_items:
        failures.append(f"walk ITEM mapping: expected {want_items}, got {items}")

    # aunt -> pre-v2 is already visited and not on aunt's own path: a DUP, not a CYCLE.
    if r.get("DUP") != [["DUP", n("aunt"), "depends_on", n("pre-v2")]] or "CYCLE" in r:
        failures.append(f"walk kinds: expected one DUP and no CYCLE, got {r.get('DUP')} {r.get('CYCLE')}")
    if "STOP" in r or "FAILED" in r:
        failures.append(f"walk kinds: no STOP/FAILED expected: {r.get('STOP')} {r.get('FAILED')}")
    if r["SUMMARY"] != [["SUMMARY", "visited=10", "stopped=0", "failed=0", "cycles=0",
                         "external=0", "notfound=0"]]:
        failures.append(f"walk kinds: summary {r['SUMMARY']}")
    if _snapshot(repo) != before:
        failures.append("walk kinds: the script changed files (it must be read-only)")
    tags = [ln.split("\t")[0] for ln in out]
    order = ["WALK", "NODE", "ITEM", "DUP", "SUMMARY"]
    if [t for i, t in enumerate(tags) if i == 0 or t != tags[i - 1]] != order:
        failures.append(f"walk kinds: record order must be {order}, got {tags}")

    # Walking from the child shows the parent-side mapping too (parent item -> child Seed).
    code, out, _ = _walk(repo, SP + "gc.yaml")
    items = [tuple(f[1:]) for f in _recs(out)["ITEM"]]
    if (n("s"), "acceptance-1", "refined_by=" + n("gc")) not in items:
        failures.append(f"walk from child: the parent's item mapping is missing: {items}")
    return failures


def check_walk_start_generation() -> list[str]:
    """An edge naming the start's old generation lands on the start (not a second node)."""
    failures = []
    repo = _repo()
    _write(repo, "a.yaml", target="A v1", children=[SP + "b.yaml"])
    _write(repo, "a-v2.yaml", target="A v2", children=[SP + "b.yaml"])
    _write(repo, "b.yaml", target="B", parent=SP + "a.yaml", depends_on=[SP + "a.yaml"])
    code, out, _ = _walk(repo, SP + "a.yaml")
    r = _recs(out)
    keys = [f[3] for f in r["NODE"]]
    if keys != [SP + "a.yaml", SP + "b.yaml"]:
        failures.append(f"walk generation: expected only the named start and b, got {keys}")
    if r.get("DUP") != [["DUP", SP + "b.yaml", "depends_on", SP + "a-v2.yaml"]] \
            and r.get("DUP") != [["DUP", SP + "b.yaml", "depends_on", SP + "a.yaml"]]:
        failures.append(f"walk generation: the edge to a.yaml must resolve onto the start: "
                        f"{r.get('DUP')}")
    return failures


def check_walk_cycle() -> list[str]:
    """A back edge is recorded as CYCLE and the walk terminates."""
    failures = []
    repo = _repo()
    _write(repo, "a.yaml", target="A", depends_on=[SP + "b.yaml"])
    _write(repo, "b.yaml", target="B", depends_on=[SP + "a.yaml"])
    code, out, err = _walk(repo, SP + "a.yaml", "--max-depth", "9", "--max-nodes", "99")
    r = _recs(out)
    if code != 0 or r.get("CYCLE") != [["CYCLE", SP + "b.yaml", "depends_on", SP + "a.yaml"]]:
        failures.append(f"walk cycle (depends_on): got {code} {r.get('CYCLE')} {err!r}")
    if len(r["NODE"]) != 2 or "cycles=1" not in r["SUMMARY"][0]:
        failures.append(f"walk cycle (depends_on): expected 2 nodes and cycles=1: {r}")

    # An ancestor's own predecessor is walked: it is what holds the ancestor's items.
    repo = _repo()
    _write(repo, "p.yaml", target="P", children=[SP + "s.yaml"], depends_on=[SP + "q.yaml"])
    _write(repo, "s.yaml", target="S", parent=SP + "p.yaml")
    _write(repo, "q.yaml", target="Q")
    code, out, _ = _walk(repo, SP + "s.yaml")
    r = _recs(out)
    q = [f for f in r["NODE"] if f[3] == SP + "q.yaml"]
    if not q or q[0][1:3] != ["2", "predecessor"] \
            or q[0][5] != f"via=parent>{SP}p.yaml>depends_on>{SP}q.yaml":
        failures.append(f"walk ancestor predecessor: {q}")

    # A sibling that depends on the start is an ordinary edge to a listed Seed, not a cycle.
    repo = _repo()
    _write(repo, "p.yaml", target="P", children=[SP + "s.yaml", SP + "t.yaml"])
    _write(repo, "s.yaml", target="S", parent=SP + "p.yaml")
    _write(repo, "t.yaml", target="T", parent=SP + "p.yaml", depends_on=[SP + "s.yaml"])
    code, out, _ = _walk(repo, SP + "s.yaml")
    r = _recs(out)
    if r.get("CYCLE") or ["DUP", SP + "t.yaml", "depends_on", SP + "s.yaml"] not in r.get("DUP", []):
        failures.append(f"walk sibling depends on start: want DUP, no CYCLE: {r.get('CYCLE')} {r.get('DUP')}")

    # Two Seeds naming each other as parent: walking up must stop at the repeat.
    repo = _repo()
    _write(repo, "x.yaml", target="X", parent=SP + "y.yaml")
    _write(repo, "y.yaml", target="Y", parent=SP + "x.yaml")
    code, out, _ = _walk(repo, SP + "x.yaml", "--max-depth", "9")
    r = _recs(out)
    if r.get("CYCLE") != [["CYCLE", SP + "y.yaml", "parent", SP + "x.yaml"]] or len(r["NODE"]) != 2:
        failures.append(f"walk cycle (parent): got {r.get('CYCLE')} nodes {len(r['NODE'])}")

    # A Seed naming itself as a child.
    repo = _repo()
    _write(repo, "z.yaml", target="Z", children=[SP + "z.yaml"])
    code, out, _ = _walk(repo, SP + "z.yaml")
    r = _recs(out)
    if r.get("CYCLE") != [["CYCLE", SP + "z.yaml", "children", SP + "z.yaml"]]:
        failures.append(f"walk cycle (self): got {r.get('CYCLE')}")
    return failures


def check_walk_caps() -> list[str]:
    """--max-depth records STOP depth; --max-nodes records STOP nodes without loading."""
    failures = []
    repo = _walk_fixture()
    code, out, _ = _walk(repo, SP + "s.yaml", "--max-depth", "1")
    r = _recs(out)
    keys = sorted(f[3] for f in r["NODE"])
    want_keys = sorted(SP + k + ".yaml" for k in ("s", "p", "gc", "pre-v2"))
    if keys != want_keys or max(int(f[1]) for f in r["NODE"]) != 1:
        failures.append(f"walk depth cap: expected {want_keys}, got {keys}")
    stops = sorted(tuple(f[1:]) for f in r.get("STOP", []))
    want = sorted([
        (SP + "p.yaml", "parent", SP + "gp.yaml", "reason=depth"),
        (SP + "p.yaml", "children", SP + "sib.yaml", "reason=depth"),
        (SP + "gc.yaml", "depends_on", SP + "pre3.yaml", "reason=depth"),
        (SP + "pre-v2.yaml", "depends_on", SP + "pprev.yaml", "reason=depth"),
    ])
    if stops != want:
        failures.append(f"walk depth cap: STOP expected {want}, got {stops}")
    if "stopped=4" not in r["SUMMARY"][0] or "visited=4" not in r["SUMMARY"][0]:
        failures.append(f"walk depth cap: summary {r['SUMMARY']}")

    code, out, _ = _walk(repo, SP + "s.yaml", "--max-nodes", "3")
    r = _recs(out)
    keys = [f[3] for f in r["NODE"]]
    if keys != [SP + "s.yaml", SP + "p.yaml", SP + "gc.yaml"]:
        failures.append(f"walk node cap: expected s, p, gc in BFS order, got {keys}")
    stops = r.get("STOP", [])
    if not stops or any(f[4] != "reason=nodes" for f in stops):
        failures.append(f"walk node cap: every STOP must be reason=nodes, got {stops}")
    targets = {f[3] for f in stops}
    if SP + "gp.yaml" not in targets or SP + "pre.yaml" not in targets or targets & set(keys):
        failures.append(f"walk node cap: STOP targets wrong (as-written keys, never visited): {targets}")
    if "visited=3" not in r["SUMMARY"][0]:
        failures.append(f"walk node cap: summary {r['SUMMARY']}")

    # Defaults and bad values.
    code, out, _ = _walk(repo, SP + "s.yaml")
    if _recs(out)["WALK"][0][4:6] != ["max_depth=3", "max_nodes=25"]:
        failures.append(f"walk defaults: {out[0]}")
    for flags in (["--max-depth", "0"], ["--max-nodes", "0"], ["--max-depth", "x"],
                  ["--max-depth"], ["--max-nodes=-1"], ["--bogus"], ["extra"]):
        code, out, err = _walk(repo, SP + "s.yaml", *flags)
        if code != 2 or out:
            failures.append(f"walk flags {flags}: expected exit 2 and no stdout, got {code} {out}")
    code, out, _ = _walk(repo, SP + "s.yaml", "--max-depth=1", "--max-nodes=2")
    if code != 0 or _recs(out)["WALK"][0][4:6] != ["max_depth=1", "max_nodes=2"]:
        failures.append(f"walk flags: the --name=value form must work: {code} {out[:1]}")
    p = subprocess.run([sys.executable, str(_SCRIPT_PATH), "walk", str(Path(repo) / "docs" / "specs")],
                       cwd=repo, capture_output=True, text=True)
    if p.returncode != 2 or p.stdout:
        failures.append(f"walk of a directory: a named Seed file is required, got {p.returncode}")
    return failures


def check_walk_notfound_and_external() -> list[str]:
    """notfound is a status; an other-repo node is read but never expanded; gh failures surface."""
    failures = []
    repo = _repo()
    _write(repo, "a.yaml", target="A", children=[SP + "ghost.yaml", SP + "b.yaml"])
    _write(repo, "b.yaml", target="B", parent=SP + "a.yaml")
    code, out, _ = _walk(repo, SP + "a.yaml")
    r = _recs(out)
    ghost = [f for f in r["NODE"] if f[3] == SP + "ghost.yaml"]
    if not ghost or ghost[0][4] != "notfound" or ghost[0][6:9] != ["target=-", "refines=-", "link_reason=-"]:
        failures.append(f"walk notfound: expected a notfound node with empty fields, got {ghost}")
    if "\t".join(r["SUMMARY"][0]) != (
            "SUMMARY\tvisited=3\tstopped=0\tfailed=0\tcycles=0\texternal=0\tnotfound=1"):
        failures.append(f"walk notfound: summary {r['SUMMARY']}")

    # Other-repo parent behind a failing gh.
    repo = _cross_fixture()
    gh = _gh_fail_shim()
    code, out, _ = _walk(repo, SP + "c3.yaml", gh=gh)
    r = _recs(out)
    rkey = "acme/parent-repo:docs/specs/p.yaml"
    parent = [f for f in r["NODE"] if f[3] == rkey]
    if not parent or parent[0][1:5] != ["1", "ancestor", rkey, "external-failed"]:
        failures.append(f"walk external-failed: got {parent}")
    if r.get("FAILED") != [["FAILED", rkey, "gh: HTTP 401: Bad credentials"]]:
        failures.append(f"walk external-failed: expected one FAILED record, got {r.get('FAILED')}")
    if "\t".join(r["SUMMARY"][0]) != (
            "SUMMARY\tvisited=2\tstopped=0\tfailed=1\tcycles=0\texternal=1\tnotfound=0"):
        failures.append(f"walk external-failed: summary {r['SUMMARY']}")
    if "[seed-relations FAILED]" in "\n".join(out):
        failures.append("walk external-failed: the FAILED record is the only failure form")
    code, data, _ = _walk_json(repo, SP + "c3.yaml", gh=gh)
    if data["failures"] != [{"key": rkey, "error": "gh: HTTP 401: Bad credentials"}]:
        failures.append(f"walk external-failed json: {data['failures']}")

    # Readable other-repo parent: status external, never expanded (no read of its children).
    p_text = _seed_text("Remote parent", children=["acme/child-repo:docs/specs/c3.yaml",
                                                    "docs/specs/sib.yaml"],
                        constraints=[("constraint-1", "Remote c1")])
    sib_text = _seed_text("Remote sibling", parent="docs/specs/p.yaml")
    gh, calls = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_text,
                          "acme/parent-repo:docs/specs/sib.yaml": sib_text})
    code, out, _ = _walk(repo, SP + "c3.yaml", gh=gh)
    r = _recs(out)
    keys = [f[3] for f in r["NODE"]]
    if keys != [SP + "c3.yaml", rkey] or r["NODE"][1][4] != "external":
        failures.append(f"walk external: expected c3 then the remote parent as external, got {r['NODE']}")
    if r["NODE"][1][6] != "target=Remote parent":
        failures.append(f"walk external: the loaded remote Seed's fields should show: {r['NODE'][1]}")
    log = calls.read_text() if calls.exists() else ""
    if "sib.yaml" in log:
        failures.append(f"walk external: the other-repo node must never be expanded, gh saw:\n{log}")
    if "external=1" not in r["SUMMARY"][0] or "failed=0" not in r["SUMMARY"][0]:
        failures.append(f"walk external: summary {r['SUMMARY']}")
    return failures


def check_walk_json_text_agree() -> list[str]:
    """The JSON object and the text records are two renderings of the same data."""
    failures = []
    repo = _walk_fixture()
    for flags in ([], ["--max-depth", "1"], ["--max-nodes", "3"]):
        code, out, _ = _walk(repo, SP + "s.yaml", *flags)
        jcode, data, _ = _walk_json(repo, SP + "s.yaml", *flags)
        if code != 0 or jcode != 0:
            failures.append(f"walk json/text {flags}: exit {code}/{jcode}")
            continue
        r = _recs(out)
        if sorted(data) != sorted(["walk", "nodes", "items", "dups", "cycles", "stops", "failures",
                                   "summary"]):
            failures.append(f"walk json {flags}: unexpected top-level keys {sorted(data)}")
        if [f[3] for f in r["NODE"]] != [x["key"] for x in data["nodes"]]:
            failures.append(f"walk json/text {flags}: node keys differ")
            continue
        for i, x in enumerate(data["nodes"]):
            f = r["NODE"][i]
            via = ">".join(p for step in x["via"] for p in step) or "-"
            if (f[1], f[2], f[4], f[5]) != (str(x["depth"]), x["relation"], x["status"], "via=" + via):
                failures.append(f"walk json/text {flags}: node {x['key']} differs: {f} vs {x}")
            if f[7] != "refines=" + (",".join(x["refines"]) or "-") or f[11] != "items=" + (
                    ",".join(x["items"]) or "-") or f[12] != "children=" + (
                    ",".join(x["children"]) or "-"):
                failures.append(f"walk json/text {flags}: node {x['key']} list fields differ")
        counts = {"ITEM": len(data["items"]), "DUP": len(data["dups"]),
                  "CYCLE": len(data["cycles"]), "STOP": len(data["stops"])}
        for tag, want in counts.items():
            if len(r.get(tag, [])) != want:
                failures.append(f"walk json/text {flags}: {tag} count {len(r.get(tag, []))} != {want}")
        sm = data["summary"]
        if r["SUMMARY"][0][1:] != [f"{k}={sm[k]}" for k in (
                "visited", "stopped", "failed", "cycles", "external", "notfound")]:
            failures.append(f"walk json/text {flags}: summary differs {r['SUMMARY']} vs {sm}")
        w = data["walk"]
        head = r["WALK"][0]
        # `at` is the one field two separate runs may disagree on (the clock), so it is only
        # format-checked in each rendering.
        if head[1:2] + head[3:] != [f"id={w['id']}", f"start={w['start']}",
                                    f"max_depth={w['max_depth']}", f"max_nodes={w['max_nodes']}",
                                    f"fingerprint={w['fingerprint']}"]:
            failures.append(f"walk json/text {flags}: WALK header differs: {head} vs {w}")
        if not re.match(r"^at=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", head[2]):
            failures.append(f"walk text: `at` is not UTC ISO seconds: {head[2]!r}")
        if not re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", w["at"]):
            failures.append(f"walk json: `at` is not UTC ISO seconds: {w['at']!r}")
        for rec in data["items"]:
            if sorted(rec) != ["id", "owner", "refined_by"]:
                failures.append(f"walk json: item record keys {sorted(rec)}")
    code, data, _ = _walk_json(repo, SP + "s.yaml")
    if "미확인" in json.dumps(data, ensure_ascii=False) or not data["nodes"][0]["via"] == []:
        failures.append("walk json: a not-recorded value is null in JSON; the start's via is []")
    gp = next(x for x in data["nodes"] if x["key"] == SP + "gp.yaml")
    if gp["link_reason"] is not None or gp["source"] != "#1":
        failures.append(f"walk json: gp link_reason must be null, source '#1': {gp}")

    # The module function returns the same structure, and a script can import and call it.
    mod = sr.walk(str(Path(repo) / "docs" / "specs" / "s.yaml"), max_depth=1, max_nodes=25)
    if [x["key"] for x in mod["nodes"]] != [SP + k + ".yaml" for k in ("s", "p", "gc", "pre-v2")]:
        failures.append(f"walk(): unexpected nodes {[x['key'] for x in mod['nodes']]}")
    return failures


def check_walk_identification() -> list[str]:
    """walk_id follows HEAD, the start file and (through the fingerprint) every visited Seed."""
    failures = []
    repo = _walk_fixture()
    start = SP + "s.yaml"
    _, a, _ = _walk_json(repo, start)
    _, a2, _ = _walk_json(repo, start)
    if not re.match(r"^local@nohead:docs/specs/s\.yaml#[0-9a-f]{8}\.[0-9a-f]{8}~d3n25$", a["walk"]["id"]):
        failures.append(f"walk id format (no origin, no commit): {a['walk']['id']!r}")
    if not re.match(r"^[0-9a-f]{12}$", a["walk"]["fingerprint"]):
        failures.append(f"walk fingerprint format: {a['walk']['fingerprint']!r}")
    if (a["walk"]["id"], a["walk"]["fingerprint"]) != (a2["walk"]["id"], a2["walk"]["fingerprint"]):
        failures.append("walk id/fingerprint must be stable when nothing changed")

    # A visited Seed changes: fingerprint and id both change, so a judgment on the old walk is stale.
    _write(repo, "gc.yaml", **dict(_walk_specs()["gc"], target="Grandchild, reworded"))
    _, b, _ = _walk_json(repo, start)
    if b["walk"]["fingerprint"] == a["walk"]["fingerprint"]:
        failures.append("walk fingerprint must change when a visited Seed changes")
    if b["walk"]["id"] == a["walk"]["id"]:
        failures.append("walk id must change when a visited Seed changes")

    # A Seed that is not reachable does not move the fingerprint.
    _write(repo, "unrelated.yaml", target="Unrelated")
    _, b2, _ = _walk_json(repo, start)
    if b2["walk"]["fingerprint"] != b["walk"]["fingerprint"]:
        failures.append("walk fingerprint must ignore Seeds the walk never visited")

    # The start file changes: the id changes.
    _write(repo, "s.yaml", **dict(_walk_specs()["s"], target="Start, reworded"))
    _, c, _ = _walk_json(repo, start)
    if c["walk"]["id"] == a["walk"]["id"]:
        failures.append("walk id must change when the start file's content changes")

    # With an origin and a commit the id carries owner/repo and the first 12 chars of HEAD.
    repo = _walk_fixture(origin="https://github.com/acme/widgets.git")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit",
                    "--allow-empty", "-q", "-m", "x"], cwd=repo, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True,
                          text=True).stdout.strip()
    _, d, _ = _walk_json(repo, start)
    if not d["walk"]["id"].startswith(f"acme/widgets@{head[:12]}:docs/specs/s.yaml#"):
        failures.append(f"walk id with origin and HEAD: {d['walk']['id']!r}")
    return failures


def check_walk_value_cleaning() -> list[str]:
    """Tabs/newlines inside values never split a record; long values are cut at 100 chars."""
    failures = []
    repo = _repo()
    reason = "tab\there " + "x" * 150
    _write(repo, "p.yaml", target="P", children=[SP + "c.yaml"])
    _write(repo, "c.yaml", target="T\tab " + "y" * 150, parent=SP + "p.yaml", link_reason=reason)
    code, out, _ = _walk(repo, SP + "c.yaml")
    node = next(ln.split("\t") for ln in out if ln.startswith("NODE\t0"))
    if len(node) != 13:
        failures.append(f"walk cleaning: a tab inside a value must not add fields: {node}")
    link = node[8]
    if not link.startswith("link_reason=tab here x") or not link.endswith("...") or len(
            link) != len("link_reason=") + 103:
        failures.append(f"walk cleaning: link_reason must be cleaned and cut at 100: {link!r}")
    if not node[6].endswith("...") or "\t" in node[6]:
        failures.append(f"walk cleaning: target must be cut at 100: {node[6]!r}")
    _, data, _ = _walk_json(repo, SP + "c.yaml")
    if data["nodes"][0]["link_reason"] != reason:
        failures.append("walk json: link_reason must be kept whole (no cut, no cleaning)")
    return failures


def check_walk_reexpand_second_route() -> list[str]:
    """A Seed found first as a predecessor and again as a descendant is also expanded as one."""
    failures = []
    repo = _repo()
    at = lambda *ns: [f"{SP}{n}.yaml" for n in ns]
    _write(repo, "a.yaml", target="A", children=at("b"), depends_on=at("c"))
    _write(repo, "b.yaml", target="B", parent=SP + "a.yaml", children=at("c"))
    _write(repo, "c.yaml", target="C", parent=SP + "b.yaml", children=at("d"))
    _write(repo, "d.yaml", target="D", parent=SP + "c.yaml")
    code, data, _ = _walk_json(repo, SP + "a.yaml")
    got = {n["key"]: (n["depth"], n["relation"]) for n in data["nodes"]}
    want = {SP + "a.yaml": (0, "start"), SP + "b.yaml": (1, "descendant"),
            SP + "c.yaml": (1, "predecessor"), SP + "d.yaml": (3, "descendant")}
    if got != want:
        failures.append(f"walk re-expand: expected {want}, got {got}")
    d = [n for n in data["nodes"] if n["key"] == SP + "d.yaml"]
    if d and d[0]["via"] != [["children", SP + "b.yaml"], ["children", SP + "c.yaml"],
                             ["children", SP + "d.yaml"]]:
        failures.append(f"walk re-expand: D via should be the descendant path, got {d[0]['via']}")
    s = data["summary"]
    if (s["visited"], s["stopped"], s["cycles"]) != (4, 0, 0) or len(data["dups"]) != 1:
        failures.append(f"walk re-expand: summary {s}, dups {data['dups']}")
    # The caps still bind the re-expanded route and report it.
    code, data, _ = _walk_json(repo, SP + "a.yaml", "--max-depth", "2")
    if [n["key"] for n in data["nodes"]].count(SP + "d.yaml") or data["stops"] != [
            {"from": SP + "c.yaml", "edge": "children", "target": SP + "d.yaml", "reason": "depth"}]:
        failures.append(f"walk re-expand depth cap: nodes/stops {data['stops']}")
    code, data, _ = _walk_json(repo, SP + "a.yaml", "--max-nodes", "3")
    if len(data["nodes"]) != 3 or data["stops"] != [
            {"from": SP + "c.yaml", "edge": "children", "target": SP + "d.yaml", "reason": "nodes"}]:
        failures.append(f"walk re-expand node cap: {len(data['nodes'])} nodes, stops {data['stops']}")
    # A second route already past max_depth is not expanded: C is a depth-1 predecessor, and
    # the B→C route (depth 2) must not follow children or report stops from beyond the cap.
    code, data, _ = _walk_json(repo, SP + "a.yaml", "--max-depth", "1")
    if sorted(n["key"] for n in data["nodes"]) != at("a", "b", "c") or data["stops"]:
        failures.append(f"walk re-expand past max-depth: nodes/stops {data['stops']}")
    # A cycle through the re-expanded edge terminates and is reported, not looped.
    _write(repo, "d.yaml", target="D", parent=SP + "c.yaml", children=at("c"))
    code, data, _ = _walk_json(repo, SP + "a.yaml")
    if code != 0 or len(data["nodes"]) != 4 or data["summary"]["cycles"] < 1:
        failures.append(f"walk re-expand cycle: {code} {data['summary'] if data else None}")
    return failures


def check_identifier_helpers() -> list[str]:
    """canonical_id / legacy_form / seed_slug / qualified_id are the code form of identifiers.md."""
    failures = []
    cases = [
        (sr.canonical_id("c3"), "constraint-3"), (sr.canonical_id("ac12"), "acceptance-12"),
        (sr.canonical_id("constraint-3"), "constraint-3"), (sr.canonical_id("g1"), "g1"),
        (sr.canonical_id("cx1"), "cx1"), (sr.legacy_form("constraint-3"), "c3"),
        (sr.legacy_form("acceptance-2"), "ac2"), (sr.legacy_form("c1"), "c1"),
        (sr.seed_slug("docs/specs/foo-v3.yaml"), "foo"), (sr.seed_slug("docs/specs/foo.yaml"), "foo"),
        (sr.seed_slug("foo-v2-x.yaml"), "foo-v2-x"),
        (sr.qualified_id("docs/specs/foo-v3.yaml", "constraint-1"), "foo/constraint-1"),
        (sr.qualified_id("acme/repo:docs/specs/foo.yaml", "acceptance-2"),
         "acme/repo:foo/acceptance-2"),
    ]
    for got, want in cases:
        if got != want:
            failures.append(f"identifier helper: expected {want!r}, got {got!r}")
    return failures


def _legacy_pair(repo, parent_ids=("c1", "ac1"), child_refines=("c1", "ac1")):
    crit = [i for i in parent_ids if i.startswith(("ac", "acceptance"))]
    cons = [i for i in parent_ids if i not in crit]
    _write(repo, "parent.yaml", target="Parent", children=[SP + "kid.yaml"],
           constraints=[(i, f"desc {i}") for i in cons], criteria=[(i, f"desc {i}") for i in crit])
    _write(repo, "kid.yaml", target="Kid", parent=SP + "parent.yaml", refines=list(child_refines))


def check_legacy_compat() -> list[str]:
    """An unmigrated c<N>/ac<N> Seed still tree/check/walks; check adds an informational LEGACY."""
    failures = []
    repo = _repo()
    _legacy_pair(repo)
    legacy = ("LEGACY    docs/specs/parent.yaml still uses legacy item ids c1, ac1 — "
              "run: seed-id-migrate.py docs/specs/parent.yaml")

    code, out, err = _run(repo, "check", SP + "kid.yaml")
    if code != 0 or out != [legacy, "OK: 3 edge(s) consistent"]:
        failures.append(f"legacy check (child): LEGACY must not change the exit code: {code} {out} {err!r}")
    code, out, _ = _run(repo, "check", SP + "parent.yaml")
    if code != 0 or out != [legacy, "OK: 1 edge(s) consistent"] or out.count(legacy) != 1:
        failures.append(f"legacy check (parent): the named Seed's LEGACY once, exit 0: {code} {out}")

    code, out, _ = _run(repo, "tree", SP + "kid.yaml")
    for want in ("REFINES   parent/c1 · desc c1", "REFINES   parent/ac1 · desc ac1",
                 "PARENT-ITEM parent/c1 · desc c1  refined by: docs/specs/kid.yaml"):
        if want not in out:
            failures.append(f"legacy tree: missing {want!r} in {out}")
    code, data, _ = _walk_json(repo, SP + "parent.yaml")
    node = data["nodes"][0]
    if code != 0 or node["items"] != ["c1", "ac1"] or node["item_desc"] != {
            "c1": "desc c1", "ac1": "desc ac1"}:
        failures.append(f"legacy walk: items/item_desc must read the old ids: {node}")
    if [(i["id"], i["refined_by"]) for i in data["items"]] != [
            ("c1", [SP + "kid.yaml"]), ("ac1", [SP + "kid.yaml"])]:
        failures.append(f"legacy walk: ITEM mapping: {data['items']}")

    # A new-form Seed never prints LEGACY.
    new = _repo()
    _legacy_pair(new, ("constraint-1", "acceptance-1"), ("constraint-1", "acceptance-1"))
    code, out, _ = _run(new, "check", SP + "kid.yaml")
    if (code, out) != (0, ["OK: 3 edge(s) consistent"]):
        failures.append(f"new-form check must stay quiet: {code} {out}")

    # A legacy Seed read through another repo: the LEGACY line says to migrate it there.
    cross = _cross_fixture()
    _write(cross, "c3.yaml", target="Cross child", parent="acme/parent-repo:docs/specs/p.yaml",
           refines=["c1"])
    p_text = _seed_text("Remote parent", children=["acme/child-repo:docs/specs/c3.yaml"],
                        constraints=[("c1", "Remote c1")])
    gh, _ = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_text})
    code, out, _ = _run(cross, "check", SP + "c3.yaml", gh=gh)
    want = ["LEGACY    acme/parent-repo:docs/specs/p.yaml still uses legacy item ids c1 — "
            "migrate it in that repo (seed-id-migrate.py docs/specs/p.yaml)",
            "OK: 2 edge(s) consistent"]
    if (code, out) != (0, want):
        failures.append(f"legacy cross-repo check: expected (0, {want}), got ({code}, {out})")
    return failures


def check_refines_form_hint() -> list[str]:
    """A refines that fails only on the id form stays a MISMATCH and names seed-id-migrate.py."""
    failures = []
    repo = _repo()
    _legacy_pair(repo, ("constraint-1",), ("c1",))  # parent migrated, child not
    code, out, _ = _run(repo, "check", SP + "kid.yaml")
    want = [f"MISMATCH  {SP}kid.yaml refines c1, which {SP}parent.yaml does not define — "
            f"{SP}parent.yaml has constraint-1: the id form differs, "
            f"run seed-id-migrate.py {SP}parent.yaml",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"hint (parent migrated): expected (1, {want}), got ({code}, {out})")

    repo = _repo()
    _legacy_pair(repo, ("c1",), ("constraint-1",))  # child migrated, parent not
    code, out, _ = _run(repo, "check", SP + "kid.yaml")
    want = [f"MISMATCH  {SP}kid.yaml refines constraint-1, which {SP}parent.yaml does not define — "
            f"{SP}parent.yaml has c1: the id form differs, run seed-id-migrate.py {SP}parent.yaml",
            f"LEGACY    {SP}parent.yaml still uses legacy item ids c1 — "
            f"run: seed-id-migrate.py {SP}parent.yaml",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"hint (child migrated): expected (1, {want}), got ({code}, {out})")

    # A genuinely missing id gets no hint.
    repo = _repo()
    _legacy_pair(repo, ("constraint-1",), ("constraint-7",))
    code, out, _ = _run(repo, "check", SP + "kid.yaml")
    if code != 1 or any("seed-id-migrate" in ln for ln in out):
        failures.append(f"hint: a refines missing in both forms must carry no hint: {out}")
    return failures


def check_duplicate_item_ids() -> list[str]:
    """The same item id twice in one Seed is a MISMATCH (item_map would collapse it silently)."""
    failures = []
    repo = _repo()
    _write(repo, "dup.yaml", target="Dup", constraints=[("constraint-1", "one"),
                                                         ("constraint-1", "again")])
    code, out, _ = _run(repo, "check", SP + "dup.yaml")
    want = [f"MISMATCH  {SP}dup.yaml defines item id constraint-1 more than once",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"duplicate ids (named): expected (1, {want}), got ({code}, {out})")
    s = sr.parse_seed(_seed_text("Dup", constraints=[("constraint-1", "a"), ("constraint-2", "b"),
                                                      ("constraint-1", "c")]))
    if s.duplicate_ids != ["constraint-1"]:
        failures.append(f"duplicate ids: parse_seed.duplicate_ids {s.duplicate_ids}")

    # A duplicated parent id is reported against the parent, as the child reads it.
    _write(repo, "parent.yaml", target="Parent", children=[SP + "kid.yaml"],
           constraints=[("constraint-1", "one"), ("constraint-1", "again")])
    _write(repo, "kid.yaml", target="Kid", parent=SP + "parent.yaml", refines=["constraint-1"])
    code, out, _ = _run(repo, "check", SP + "kid.yaml")
    if code != 1 or f"MISMATCH  {SP}parent.yaml defines item id constraint-1 more than once" not in out:
        failures.append(f"duplicate ids (parent): {code} {out}")
    return failures


def check_walk_item_desc() -> list[str]:
    """walk JSON carries item_desc; the text records keep their fields (seed-board parses them)."""
    failures = []
    repo = _walk_fixture()
    _, data, _ = _walk_json(repo, SP + "s.yaml")
    start = data["nodes"][0]
    if start["item_desc"] != {"constraint-1": "s c1", "acceptance-1": "s ac1"}:
        failures.append(f"walk item_desc: {start['item_desc']}")
    if any(isinstance(n["item_desc"], dict) is False for n in data["nodes"]):
        failures.append("walk item_desc: every node carries an item_desc object")
    code, out, _ = _walk(repo, SP + "s.yaml")
    node = _recs(out)["NODE"][0]
    if len(node) != 13 or "item_desc" in "\t".join(node):
        failures.append(f"walk text: NODE record must keep its 13 fields, got {node}")
    return failures


def main() -> int:
    checks = [
        check_tree_same_repo,
        check_tree_no_relations_block,
        check_version_resolution,
        check_mismatch_kinds,
        check_gh_failure,
        check_depends_on,
        check_self_repo_detection,
        check_cross_repo_link_only,
        check_newer_generation_note,
        check_usage_and_parser,
        check_tree_item_mapping,
        check_tree_link_source_tracking,
        check_unrecorded,
        check_walk_kinds,
        check_walk_start_generation,
        check_walk_cycle,
        check_walk_caps,
        check_walk_notfound_and_external,
        check_walk_json_text_agree,
        check_walk_identification,
        check_walk_value_cleaning,
        check_walk_reexpand_second_route,
        check_identifier_helpers,
        check_legacy_compat,
        check_refines_form_hint,
        check_duplicate_item_ids,
        check_walk_item_desc,
    ]
    failures = []
    for check in checks:
        failures += check()

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: all {len(checks)} test-seed-relations checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
