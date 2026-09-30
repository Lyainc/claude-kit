#!/usr/bin/env python3
"""Unit tests for seed-relations.py (#780) — tree/check over fixture Seeds.

Covers the fixtures the design names: same-repo parent + two children with the refines
mapping (ac1), `-vN` resolution (ac3), the three mismatch kinds plus a refines pointing at a
missing id (ac4, ac8), a failing `gh` (ac6), and depends_on same-repo vs cross-repo (ac7).
Cross-repo reads go through a `gh` shim written into the temp dir (GH_BIN); every run
defaults GH_BIN to a path that does not exist, so an unintended remote read shows up as a
FAILED line instead of passing silently.

Usage: python3 thinking-tools/scripts/test/test-seed-relations.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import atexit
import base64
import importlib.util
import json
import os
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


def _seed_text(target, parent=None, refines=(), depends_on=(), children=(),
               constraints=(), criteria=(), block_lists=False, relations=True):
    """Compose a Seed. Lists go out as flow lists, or as block lists when block_lists is set."""
    def lst(name, vals):
        if not vals:
            return f"  {name}: []"
        if block_lists:
            return f"  {name}:\n" + "\n".join(f"    - {v}" for v in vals)
        return f"  {name}: [{', '.join(vals)}]"

    lines = ["# Seed Spec", "---", "skill: build-spec", "input:", "  target: not the top-level one",
             f"target: {target}", ""]
    if relations:
        lines += ["relations:            # edges only, never a status",
                  f"  parent: {parent if parent else 'null'}        # parent Seed or null",
                  lst("refines", list(refines)), lst("depends_on", list(depends_on)),
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


LONG = ("The parent constraint c1 is deliberately long so that the tree output has to cut its "
        "description at one hundred characters and mark the cut")

PARENT_FIXTURE = dict(
    target="Parent feature",
    children=["docs/specs/child-a.yaml", "docs/specs/child-b.yaml"],
    constraints=[("c1", LONG), ("c2", "Second constraint")],
    criteria=[("ac1", "First criterion"), ("ac2", "Second criterion")],
)


def check_tree_same_repo() -> list[str]:
    """ac1: one named child yields parent, refines mapping, sibling, and PARENT-ITEM refiners."""
    failures = []
    repo = _repo()
    _write(repo, "parent.yaml", **PARENT_FIXTURE)
    _write(repo, "child-a.yaml", target="Child A", parent="docs/specs/parent.yaml",
           refines=["c1", "ac1", "c9"])
    _write(repo, "child-b.yaml", target="Child B", parent="docs/specs/parent.yaml",
           refines=["c2"], block_lists=True)
    before = _snapshot(repo)
    code, out, err = _run(repo, "tree", "docs/specs/child-a.yaml")
    long_cut = LONG[:100] + "..."
    expected = [
        "SEED      docs/specs/child-a.yaml  (target: Child A)",
        "PARENT    docs/specs/parent.yaml",
        f"REFINES   c1 — {long_cut}",
        "REFINES   ac1 — First criterion",
        "REFINES   c9 — [missing in parent]",
        "SIBLING   docs/specs/child-b.yaml  (target: Child B)",
        f"PARENT-ITEM c1 — {long_cut}  refined by: docs/specs/child-a.yaml",
        "PARENT-ITEM c2 — Second constraint  refined by: docs/specs/child-b.yaml",
        "PARENT-ITEM ac1 — First criterion  refined by: docs/specs/child-a.yaml",
        "PARENT-ITEM ac2 — Second criterion  refined by: (none)",
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
    if "REFINES   c2 — Second constraint" not in out:
        failures.append(f"tree block-list child: REFINES c2 missing: {out}")
    if "SIBLING   docs/specs/child-a.yaml  (target: Child A)" not in out:
        failures.append(f"tree block-list child: sibling child-a missing: {out}")

    # The parent itself: children are listed, no PARENT, and no status-like value anywhere.
    code, out, _ = _run(repo, "tree", "docs/specs/parent.yaml")
    if "PARENT    (none)" not in out or "CHILD     docs/specs/child-a.yaml" not in out:
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
    if code != 0 or out != ["SEED      docs/specs/old.yaml  (target: Old seed)", "PARENT    (none)"]:
        failures.append(f"no relations block: exit {code}, out {out}, err {err!r}")
    return failures


def check_version_resolution() -> list[str]:
    """ac3: foo.yaml + foo-v2.yaml both present, the child's parent edge resolves to -v2."""
    failures = []
    repo = _repo()
    _write(repo, "foo.yaml", target="Foo v1", children=["docs/specs/kid.yaml"],
           constraints=[("c1", "Old wording")])
    _write(repo, "foo-v2.yaml", target="Foo v2", children=["docs/specs/kid.yaml"],
           constraints=[("c1", "New wording")])
    _write(repo, "kid.yaml", target="Kid", parent="docs/specs/foo.yaml", refines=["c1"])
    code, out, _ = _run(repo, "tree", "docs/specs/kid.yaml")
    for want in ("PARENT    docs/specs/foo.yaml -> docs/specs/foo-v2.yaml",
                 "REFINES   c1 — New wording"):
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
           refines=["c1"])
    return repo


def check_mismatch_kinds() -> list[str]:
    """ac4, ac8: the three mismatch kinds and a refines pointing at a missing id."""
    failures = []
    repo = _cross_fixture()

    # 1. child names parent, parent's children lacks the child.
    _write(repo, "p1.yaml", target="P1", children=[], constraints=[("c1", "x")])
    _write(repo, "c1.yaml", target="C1", parent="docs/specs/p1.yaml", refines=["c1"])
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
                        constraints=[("c1", "Remote c1")])
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
                      constraints=[("c1", "Remote c1")])
    gh, _ = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_ok})
    code, out, _ = _run(repo, "check", "docs/specs/c3.yaml", gh=gh)
    if (code, out) != (0, ["OK: 2 edge(s) consistent"]):
        failures.append(f"cross-repo consistent: expected (0, OK 2), got ({code}, {out})")

    # 4. refines pointing at an id the parent does not define (ac8).
    _write(repo, "p4.yaml", target="P4", children=["docs/specs/c4.yaml"],
           constraints=[("c1", "x")])
    _write(repo, "c4.yaml", target="C4", parent="docs/specs/p4.yaml", refines=["c1", "c9"])
    code, out, _ = _run(repo, "check", "docs/specs/c4.yaml")
    want = ["MISMATCH  docs/specs/c4.yaml refines c9, which docs/specs/p4.yaml does not define",
            "FOUND: 1 mismatch(es)"]
    if (code, out) != (1, want):
        failures.append(f"mismatch refines: expected (1, {want}), got ({code}, {out})")

    # A consistent same-repo pair is OK with exit 0.
    _write(repo, "p5.yaml", target="P5", children=["docs/specs/c5.yaml"],
           constraints=[("c1", "x")])
    _write(repo, "c5.yaml", target="C5", parent="docs/specs/p5.yaml", refines=["c1"])
    for name in ("c5", "p5"):
        code, out, _ = _run(repo, "check", f"docs/specs/{name}.yaml")
        n = 2 if name == "c5" else 1
        if (code, out) != (0, [f"OK: {n} edge(s) consistent"]):
            failures.append(f"consistent pair ({name}): got ({code}, {out})")
    return failures


def check_gh_failure() -> list[str]:
    """ac6: a failing gh prints an explicit FAILED line; the section is never empty."""
    failures = []
    repo = _cross_fixture()
    _write(repo, "sib.yaml", target="Sibling", parent="docs/specs/local-parent.yaml")
    gh = _gh_fail_shim()
    line = ("[seed-relations FAILED] acme/parent-repo:docs/specs/p.yaml — "
            "gh api: gh: HTTP 401: Bad credentials")

    code, out, _ = _run(repo, "tree", "docs/specs/c3.yaml", gh=gh)
    want = ["SEED      docs/specs/c3.yaml  (target: Cross child)",
            "PARENT    acme/parent-repo:docs/specs/p.yaml" + sr.LINK_ONLY,
            line,
            "REFINES   c1 — [parent unreadable]"]
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
    if line not in out or "CHILD     docs/specs/sib.yaml" not in out:
        failures.append(f"gh failure keeps going: expected FAILED line and the CHILD line, got {out}")
    return failures


def check_depends_on() -> list[str]:
    """ac7: a sibling's depends_on prints `requires`, tagged same-repo or cross-repo."""
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
           constraints=[("c1", "Parent c1")])
    _write(repo, "kid.yaml", target="Kid", parent="owner/repo:docs/specs/p.yaml", refines=["c1"])
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
                        constraints=[("c1", "Remote c1")])
    sib_text = _seed_text("Remote sibling", parent="docs/specs/p.yaml")
    gh, _ = _gh_shim({"acme/parent-repo:docs/specs/p.yaml": p_text,
                      "acme/parent-repo:docs/specs/sib.yaml": sib_text})
    code, out, _ = _run(repo, "tree", "docs/specs/c3.yaml", gh=gh)
    mark = sr.LINK_ONLY
    want = [
        f"PARENT    acme/parent-repo:docs/specs/p.yaml{mark}",
        f"SIBLING   acme/parent-repo:docs/specs/sib.yaml  (target: Remote sibling){mark}",
        f"PARENT-ITEM c1 — Remote c1  refined by: docs/specs/c3.yaml{mark}",
    ]
    for w in want:
        if w not in out:
            failures.append(f"link-only mark: missing {w!r} in {out}")
    if any(mark in ln for ln in out if ln.startswith(("SEED", "REFINES", "CHILD"))):
        failures.append(f"link-only mark: only PARENT/PARENT-ITEM/SIBLING lines carry it: {out}")

    # Same-repo lines never carry it.
    local = _repo()
    _write(local, "parent.yaml", target="Parent", children=["docs/specs/kid.yaml", "docs/specs/sib.yaml"],
           constraints=[("c1", "x")])
    _write(local, "kid.yaml", target="Kid", parent="docs/specs/parent.yaml", refines=["c1"])
    _write(local, "sib.yaml", target="Sib", parent="docs/specs/parent.yaml")
    code, out, _ = _run(local, "tree", "docs/specs/kid.yaml")
    if any(sr.LINK_ONLY in ln for ln in out):
        failures.append(f"link-only mark: a same-repo tree must not carry it: {out}")
    return failures


def check_newer_generation_note() -> list[str]:
    """Naming foo.yaml while foo-v2.yaml exists: a NOTE line, and foo.yaml stays the Seed described."""
    failures = []
    repo = _repo()
    _write(repo, "foo.yaml", target="Foo v1", constraints=[("c1", "Old")])
    _write(repo, "foo-v2.yaml", target="Foo v2", constraints=[("c1", "New")])
    want = "NOTE      newer generation exists: docs/specs/foo-v2.yaml"
    code, out, _ = _run(repo, "tree", "docs/specs/foo.yaml")
    if code != 0 or out[:3] != ["SEED      docs/specs/foo.yaml  (target: Foo v1)", want,
                                "PARENT    (none)"]:
        failures.append(f"newer generation tree: expected SEED foo.yaml then NOTE, got {out}")
    code, out, _ = _run(repo, "check", "docs/specs/foo.yaml")
    if (code, out) != (0, [want, "OK: 0 edge(s) consistent"]):
        failures.append(f"newer generation check: expected the NOTE line first, got {code} {out}")
    code, out, _ = _run(repo, "tree", "docs/specs/foo-v2.yaml")
    if any(ln.startswith("NOTE") for ln in out):
        failures.append(f"newer generation: the latest file must carry no NOTE, got {out}")
    return failures


def check_usage_and_parser() -> list[str]:
    """A named Seed is required (c7); the reader handles comments, quotes and block scalars."""
    failures = []
    repo = _repo()
    for argv in ([], ["tree"], ["bogus", "x"], ["tree", "docs/specs/missing.yaml"]):
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
