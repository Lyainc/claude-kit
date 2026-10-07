#!/usr/bin/env python3
"""Unit tests for seed-id-migrate.py — legacy c<N>/ac<N> -> constraint-<N>/acceptance-<N>.

Fixtures are throwaway git repos. They pin: a legacy Seed + its local children migrated together
and `seed-relations.py check` passing afterwards; the dry run writing nothing; a re-run changing
nothing; a mixed Seed completing; the refusals (reused number, unresolved refines, duplicate id,
child not pointing back) writing nothing; interrupted runs converging in either direction; the
same `c1` in two unrelated Seeds staying independent; sibling children; cross-repo parent/child
being reported as FOLLOW-UP and never written; byte-level preservation of comments, quoting, block
scalars and line endings; the REF candidate scan; and usage errors.

Every run sets GH_BIN to a path that does not exist, so an unintended `gh` call fails loudly.

Usage: python3 thinking-tools/scripts/test/test-seed-id-migrate.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import atexit
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
_MIGRATE = _SCRIPTS / "seed-id-migrate.py"
_RELATIONS = _SCRIPTS / "seed-relations.py"

NO_GH = "/nonexistent/gh"
os.environ["GH_BIN"] = NO_GH
SP = "docs/specs/"

_spec = importlib.util.spec_from_file_location("seed_id_migrate", _MIGRATE)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)


def _repo(origin=None):
    d = tempfile.mkdtemp(prefix="test-seed-id-migrate-")
    atexit.register(shutil.rmtree, d, ignore_errors=True)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True, capture_output=True)
    if origin:
        subprocess.run(["git", "remote", "add", "origin", origin], cwd=d, check=True,
                       capture_output=True)
    (Path(d) / "docs" / "specs").mkdir(parents=True)
    return d


def seed(target, *, parent=None, refines=(), children=(), cons=(), crit=(), style="flow"):
    """A Seed with comments, folded descriptions and trailing comments on the lines we edit.

    cons/crit hold raw id tokens (a quoted id is given with its quotes). style picks the refines
    list form: "flow" (`[a, b]`) or "block".
    """
    out = ["# Seed Spec", "# note: c1 and ac1 appear in this comment only", "---", "skill: build-spec",
           f"target: {target}", "", "relations:            # edges only, never a status",
           f"  parent: {parent if parent else 'null'}        # parent Seed or null"]
    if not refines:
        out.append("  refines: []")
    elif style == "flow":
        out.append("  refines: [" + ", ".join(refines) + "]   # parent items")
    else:
        out.append("  refines:   # parent items")
        out += [f"    - {r}   # item" for r in refines]
    out.append("  link_reason: spells out c1 for the API")
    out.append("  depends_on: []")
    out.append("  children: [" + ", ".join(children) + "]" if children else "  children: []")
    out.append("")
    for name, ids in (("constraints", cons), ("success_criteria", crit)):
        out.append(f"{name}:")
        out.append("  # a comment between items")
        for tok in ids:
            out += [f"  - id: {tok}   # keep this comment",
                    "    type: technical",
                    "    description: >-",
                    f"      Folded description of {tok.strip(chr(34) + chr(39))}, mentioning c1",
                    "      and continuing on a second line",
                    "    hard: true",
                    '    rationale: "quoted: still here"']
        out.append("")
    return "\n".join(out) + "\n"


def put(repo, name, text):
    (Path(repo) / "docs" / "specs" / name).write_bytes(text.encode("utf-8"))
    return SP + name


def read(repo, rel):
    return (Path(repo) / rel).read_bytes().decode("utf-8")


def snapshot(repo):
    return {str(f.relative_to(repo)): f.read_bytes() for f in sorted(Path(repo).rglob("*"))
            if f.is_file() and ".git" not in f.parts}


def run(repo, rel, *flags):
    env = dict(os.environ, GH_BIN=NO_GH)
    p = subprocess.run([sys.executable, str(_MIGRATE), rel, *flags], cwd=repo, env=env,
                       capture_output=True, text=True)
    return p.returncode, p.stdout.splitlines(), p.stderr


def relations_check(repo, rel):
    env = dict(os.environ, GH_BIN=NO_GH)
    p = subprocess.run([sys.executable, str(_RELATIONS), "check", rel], cwd=repo, env=env,
                       capture_output=True, text=True)
    return p.returncode, p.stdout.splitlines()


def changed_lines(old, new):
    """[(old line, new line)] for lines that differ; None when the line counts differ."""
    a, b = old.split("\n"), new.split("\n")
    if len(a) != len(b):
        return None
    return [(x, y) for x, y in zip(a, b) if x != y]


def git_add(repo):
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)


def _family(repo, parent_cons=("c1", "c2"), parent_crit=("ac1",), kid_a=("c1", "ac1"),
            kid_b=("c2",)):
    put(repo, "parent.yaml", seed("Parent", children=[SP + "kid-a.yaml", SP + "kid-b.yaml"],
                                  cons=parent_cons, crit=parent_crit))
    put(repo, "kid-a.yaml", seed("Kid A", parent=SP + "parent.yaml", refines=list(kid_a),
                                 style="block"))
    put(repo, "kid-b.yaml", seed("Kid B", parent=SP + "parent.yaml", refines=list(kid_b)))


def check_basic_migration() -> list[str]:
    """Legacy Seed + two local children migrate together; check passes; dry run writes nothing."""
    failures = []
    repo = _repo()
    _family(repo)
    before = snapshot(repo)
    code, out, err = run(repo, SP + "parent.yaml")
    if code != 0 or snapshot(repo) != before:
        failures.append(f"dry run: exit {code}, must write nothing: {out} {err!r}")
    for want in (f"RENAME    {SP}parent.yaml  c1 -> constraint-1",
                 f"RENAME    {SP}parent.yaml  c2 -> constraint-2",
                 f"RENAME    {SP}parent.yaml  ac1 -> acceptance-1",
                 f"REFINES   {SP}kid-a.yaml  c1 -> constraint-1",
                 f"REFINES   {SP}kid-a.yaml  ac1 -> acceptance-1",
                 f"REFINES   {SP}kid-b.yaml  c2 -> constraint-2",
                 "DRY-RUN: 3 file(s) would change; re-run with --apply to write"):
        if want not in out:
            failures.append(f"dry run plan: missing {want!r} in {out}")
    if not any(ln.startswith("NOTE") and "START-PROMPT" in ln for ln in out):
        failures.append(f"dry run: the out-of-repo reminder is missing: {out}")

    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    if code != 0 or "OK: migrated 3 file(s)" not in out:
        failures.append(f"apply: exit {code} {out} {err!r}")
    for name in ("parent", "kid-a", "kid-b"):
        new = read(repo, f"{SP}{name}.yaml")
        old = before[f"{SP}{name}.yaml"].decode()
        diff = changed_lines(old, new)
        if diff is None:
            failures.append(f"apply: {name} line count changed")
            continue
        # only `id:` lines of the items and `refines` entries differ; never anything else
        for x, y in diff:
            ok = ("id:" in x and "id:" in y) or "refines: [" in x or x.strip().startswith("- ")
            if not ok:
                failures.append(f"apply: {name} unexpected change {x!r} -> {y!r}")
    parent = read(repo, SP + "parent.yaml")
    for want in ("  - id: constraint-1   # keep this comment", "  - id: constraint-2   # keep",
                 "  - id: acceptance-1   # keep"):
        if want not in parent:
            failures.append(f"apply: parent missing {want!r}")
    if "    - constraint-1   # item" not in read(repo, SP + "kid-a.yaml") or \
            "    - acceptance-1   # item" not in read(repo, SP + "kid-a.yaml"):
        failures.append("apply: block-list refines of kid-a not rewritten in place")
    if "  refines: [constraint-2]   # parent items" not in read(repo, SP + "kid-b.yaml"):
        failures.append("apply: flow refines of kid-b not rewritten in place")
    for rel in (SP + "parent.yaml", SP + "kid-a.yaml", SP + "kid-b.yaml"):
        code, out = relations_check(repo, rel)
        if code != 0 or any(ln.startswith(("LEGACY", "MISMATCH")) for ln in out):
            failures.append(f"post-migration check {rel}: expected clean, got {code} {out}")
    if any(f.name.startswith(".seed-id-migrate-") for f in (Path(repo) / "docs" / "specs").iterdir()):
        failures.append("apply: a temp file was left behind")

    after = snapshot(repo)
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    if code != 0 or snapshot(repo) != after or not any(ln.startswith("nothing to migrate") for ln in out):
        failures.append(f"re-run: expected 'nothing to migrate' and no write: {code} {out}")
    code, out, _ = run(repo, SP + "kid-a.yaml", "--apply")
    if code != 0 or snapshot(repo) != after:
        failures.append(f"re-run on a migrated child: {code} {out}")
    return failures


def check_mixed_seed() -> list[str]:
    """Some ids already new, some legacy: the rest is completed; no mapping table is needed."""
    failures = []
    repo = _repo()
    _family(repo, parent_cons=("constraint-1", "c2"), parent_crit=("ac1", "acceptance-2"),
            kid_a=("constraint-1", "ac1"), kid_b=("c2",))
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    if code != 0:
        return [f"mixed: exit {code} {out} {err!r}"]
    parent = read(repo, SP + "parent.yaml")
    ids = [ln.split("id:")[1].split("#")[0].strip() for ln in parent.split("\n")
           if ln.strip().startswith("- id:")]
    if ids != ["constraint-1", "constraint-2", "acceptance-1", "acceptance-2"]:
        failures.append(f"mixed: ids {ids}")
    kid = read(repo, SP + "kid-a.yaml")
    if "    - constraint-1   # item" not in kid or "    - acceptance-1   # item" not in kid:
        failures.append(f"mixed: kid-a refines: {kid}")
    code, out = relations_check(repo, SP + "kid-a.yaml")
    if code != 0:
        failures.append(f"mixed: check after migration: {code} {out}")
    return failures


def check_refusals() -> list[str]:
    """Each refusal exits 1 with PROBLEM lines and leaves every file byte-identical."""
    failures = []

    def refused(name, repo, rel, expect):
        before = snapshot(repo)
        code, out, err = run(repo, rel, "--apply")
        text = "\n".join(out)
        if code != 1 or snapshot(repo) != before:
            failures.append(f"{name}: expected exit 1 and nothing written, got {code}: {out} {err!r}")
        if not any(ln.startswith("PROBLEM") and expect in ln for ln in out) or \
                not any(ln.startswith("REFUSED:") for ln in out):
            failures.append(f"{name}: missing PROBLEM mentioning {expect!r}: {text}")

    # a reused number: c1 and constraint-1 together
    repo = _repo()
    _family(repo, parent_cons=("c1", "constraint-1"), parent_crit=(), kid_a=("c1",), kid_b=())
    refused("collision", repo, SP + "parent.yaml", "reused number")

    # a child refining an item the parent does not have (pre-existing broken edge)
    repo = _repo()
    _family(repo, kid_a=("c1", "c9"))
    refused("unresolved refines", repo, SP + "parent.yaml", "kid-a.yaml refines c9")

    # a duplicate id
    repo = _repo()
    _family(repo, parent_cons=("c1", "c1"), parent_crit=(), kid_a=("c1",), kid_b=())
    refused("duplicate id", repo, SP + "parent.yaml", "duplicate item id c1")

    # a child whose parent edge does not point back
    repo = _repo()
    _family(repo)
    put(repo, "kid-b.yaml", seed("Kid B", parent=SP + "elsewhere.yaml", refines=["c2"]))
    refused("child not pointing back", repo, SP + "parent.yaml", "does not point back")

    # a listed child that is missing
    repo = _repo()
    _family(repo)
    (Path(repo) / SP / "kid-b.yaml").unlink()
    refused("missing child", repo, SP + "parent.yaml", "does not exist")

    # the named Seed's own refines vs its local parent, unresolved in both forms
    repo = _repo()
    put(repo, "up.yaml", seed("Up", children=[SP + "me.yaml"], cons=["constraint-1"]))
    put(repo, "me.yaml", seed("Me", parent=SP + "up.yaml", refines=["c7"], cons=["c1"]))
    refused("own refines unresolved", repo, SP + "me.yaml", "me.yaml refines c7")
    return failures


def check_interrupted_runs_converge() -> list[str]:
    """Parent written/child not, and child written/parent not: a re-run completes both."""
    failures = []
    for name in ("parent written first", "child written first"):
        repo = _repo()
        _family(repo, kid_b=("c2",))
        full = _repo()
        _family(full)
        run(full, SP + "parent.yaml", "--apply")
        if name == "parent written first":
            # as if the run died after the parent: only the parent file is new
            put(repo, "parent.yaml", read(full, SP + "parent.yaml"))
            expect_change = {SP + "kid-a.yaml", SP + "kid-b.yaml"}
        else:
            # as if the run died after the children: only the children are new
            put(repo, "kid-a.yaml", read(full, SP + "kid-a.yaml"))
            put(repo, "kid-b.yaml", read(full, SP + "kid-b.yaml"))
            expect_change = {SP + "parent.yaml"}
        before = snapshot(repo)
        code, out, err = run(repo, SP + "parent.yaml", "--apply")
        if code != 0:
            failures.append(f"{name}: re-run exit {code} {out} {err!r}")
            continue
        for rel in (SP + "parent.yaml", SP + "kid-a.yaml", SP + "kid-b.yaml"):
            if read(repo, rel) != read(full, rel):
                failures.append(f"{name}: {rel} did not converge to the full migration")
            moved = before[rel] != (Path(repo) / rel).read_bytes()
            if moved != (rel in expect_change):
                failures.append(f"{name}: {rel} changed={moved}, expected {rel in expect_change}")
        code, out = relations_check(repo, SP + "kid-a.yaml")
        if code != 0:
            failures.append(f"{name}: check after convergence: {code} {out}")

    # A real interruption: the process dies while writing the second file.
    repo = _repo()
    _family(repo)
    full = _repo()
    _family(full)
    run(full, SP + "parent.yaml", "--apply")
    real, calls = mig.write_atomic, []

    def flaky(doc):
        calls.append(doc.rel)
        if len(calls) == 2:
            raise OSError("simulated crash")
        real(doc)

    mig.write_atomic = flaky
    try:
        try:
            mig.run(str(Path(repo) / SP / "parent.yaml"), True)
            failures.append("interrupt: the simulated crash did not surface")
        except OSError:
            pass
    finally:
        mig.write_atomic = real
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    if code != 0 or any(read(repo, r) != read(full, r) for r in (
            SP + "parent.yaml", SP + "kid-a.yaml", SP + "kid-b.yaml")):
        failures.append(f"interrupt: re-run must converge: {code} {out} {err!r}")
    if any(f.name.startswith(".seed-id-migrate-") for f in (Path(repo) / "docs" / "specs").iterdir()):
        failures.append("interrupt: a temp file was left behind")
    return failures


def check_same_id_in_unrelated_seeds() -> list[str]:
    """`c1` in two unrelated Seeds: migrating one leaves the other and its refines alone."""
    failures = []
    repo = _repo()
    put(repo, "alpha.yaml", seed("Alpha", children=[SP + "alpha-kid.yaml"], cons=["c1"]))
    put(repo, "alpha-kid.yaml", seed("Alpha kid", parent=SP + "alpha.yaml", refines=["c1"]))
    put(repo, "beta.yaml", seed("Beta", children=[SP + "beta-kid.yaml"], cons=["c1"]))
    put(repo, "beta-kid.yaml", seed("Beta kid", parent=SP + "beta.yaml", refines=["c1"]))
    before = snapshot(repo)
    code, out, err = run(repo, SP + "alpha.yaml", "--apply")
    after = snapshot(repo)
    if code != 0:
        return [f"unrelated: exit {code} {out} {err!r}"]
    for name in ("beta", "beta-kid"):
        if after[f"{SP}{name}.yaml"] != before[f"{SP}{name}.yaml"]:
            failures.append(f"unrelated: {name} must not be touched")
    for name in ("alpha", "alpha-kid"):
        if after[f"{SP}{name}.yaml"] == before[f"{SP}{name}.yaml"]:
            failures.append(f"unrelated: {name} should have been migrated")
    if relations_check(repo, SP + "beta-kid.yaml")[0] != 0 or \
            relations_check(repo, SP + "alpha-kid.yaml")[0] != 0:
        failures.append("unrelated: both families must still check clean")
    return failures


def check_siblings_and_own_refines() -> list[str]:
    """Siblings both refining the parent are rewritten; the named child's own refines follow a
    parent that already carries the new id, and stay while the parent is still legacy."""
    failures = []
    repo = _repo()
    put(repo, "parent.yaml", seed("Parent", children=[SP + "s1.yaml", SP + "s2.yaml"],
                                  cons=["c1"]))
    put(repo, "s1.yaml", seed("S1", parent=SP + "parent.yaml", refines=["c1"]))
    put(repo, "s2.yaml", seed("S2", parent=SP + "parent.yaml", refines=["c1"]))
    code, out, _ = run(repo, SP + "parent.yaml", "--apply")
    if code != 0 or "refines: [constraint-1]" not in read(repo, SP + "s1.yaml") or \
            "refines: [constraint-1]" not in read(repo, SP + "s2.yaml"):
        failures.append(f"siblings: both must be rewritten: {code} {out}")

    # named child with its own legacy ids and a legacy refines
    repo = _repo()
    put(repo, "up.yaml", seed("Up", children=[SP + "me.yaml"], cons=["constraint-1"]))
    put(repo, "me.yaml", seed("Me", parent=SP + "up.yaml", refines=["c1"], cons=["c1"],
                              crit=["ac1"]))
    code, out, err = run(repo, SP + "me.yaml", "--apply")
    me = read(repo, SP + "me.yaml")
    if code != 0 or "refines: [constraint-1]" not in me or "- id: constraint-1" not in me or \
            "- id: acceptance-1" not in me:
        failures.append(f"own refines (parent migrated): {code} {out} {err!r}")
    if read(repo, SP + "up.yaml") != (Path(repo) / SP / "up.yaml").read_text():
        failures.append("own refines: the parent must not be written")

    repo = _repo()
    put(repo, "up.yaml", seed("Up", children=[SP + "me.yaml"], cons=["c1"]))
    put(repo, "me.yaml", seed("Me", parent=SP + "up.yaml", refines=["c1"], cons=["c1"]))
    up_before = read(repo, SP + "up.yaml")
    code, out, _ = run(repo, SP + "me.yaml", "--apply")
    me = read(repo, SP + "me.yaml")
    if code != 0 or "refines: [c1]" not in me or "- id: constraint-1" not in me or \
            read(repo, SP + "up.yaml") != up_before:
        failures.append(f"own refines (parent still legacy): refines stay, ids migrate: {code} {out}")
    return failures


def check_cross_repo_follow_up() -> list[str]:
    """Another repo's child/parent is never written: an explicit FOLLOW-UP line instead."""
    failures = []
    repo = _repo(origin="https://github.com/acme/here.git")
    put(repo, "parent.yaml", seed("Parent", parent="acme/up:docs/specs/top.yaml", refines=["c1"],
                                  children=[SP + "kid.yaml", "acme/other:docs/specs/x.yaml",
                                            "acme/here:docs/specs/kid2.yaml"],
                                  cons=["c1", "c2"], crit=["ac1"]))
    put(repo, "kid.yaml", seed("Kid", parent=SP + "parent.yaml", refines=["c2"]))
    put(repo, "kid2.yaml", seed("Kid2", parent="acme/here:docs/specs/parent.yaml", refines=["c1"]))
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    if code != 0:
        return [f"cross-repo: exit {code} {out} {err!r}"]
    kid = ("FOLLOW-UP acme/other:docs/specs/x.yaml relations.refines (another repo, not written): "
           "for any of these it lists, replace c1 -> constraint-1, c2 -> constraint-2, "
           "ac1 -> acceptance-1")
    if kid not in out:
        failures.append(f"cross-repo child FOLLOW-UP missing: {out}")
    par = (f"FOLLOW-UP {SP}parent.yaml relations.refines [c1] point into "
           "acme/up:docs/specs/top.yaml (another repo, not written): once that Seed uses the new "
           "ids, replace c1 -> constraint-1")
    if par not in out:
        failures.append(f"cross-repo parent FOLLOW-UP missing: {out}")
    if "refines: [c1]   # parent items" not in read(repo, SP + "parent.yaml"):
        failures.append("cross-repo: the refines into another repo's parent must stay as written")
    if "constraint-1" not in read(repo, SP + "parent.yaml") or \
            "refines: [constraint-2]" not in read(repo, SP + "kid.yaml") or \
            "refines: [constraint-1]" not in read(repo, SP + "kid2.yaml"):
        failures.append("cross-repo: own ids and local children (also via this repo's coordinate) "
                        "must still migrate")
    if any("x.yaml" in ln and ln.startswith("WRITTEN") for ln in out):
        failures.append("cross-repo: nothing outside the repo may be written")
    return failures


def check_content_preservation() -> list[str]:
    """Comments, quoting, block scalars and CRLF endings survive; only the planned tokens move."""
    failures = []
    repo = _repo()
    parent = seed("Parent", children=[SP + "kid.yaml"], cons=['"c1"', "'c2'"], crit=["ac1"])
    kid = seed("Kid", parent=SP + "parent.yaml", refines=['"c1"', "'c2'", "ac1"], style="block")
    put(repo, "parent.yaml", parent)
    put(repo, "kid.yaml", kid)
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    if code != 0:
        return [f"preservation: exit {code} {out} {err!r}"]
    np, nk = read(repo, SP + "parent.yaml"), read(repo, SP + "kid.yaml")
    pd = changed_lines(parent, np)
    kd = changed_lines(kid, nk)
    want_p = [('  - id: "c1"   # keep this comment', '  - id: "constraint-1"   # keep this comment'),
              ("  - id: 'c2'   # keep this comment", "  - id: 'constraint-2'   # keep this comment"),
              ("  - id: ac1   # keep this comment", "  - id: acceptance-1   # keep this comment")]
    want_k = [('    - "c1"   # item', '    - "constraint-1"   # item'),
              ("    - 'c2'   # item", "    - 'constraint-2'   # item"),
              ("    - ac1   # item", "    - acceptance-1   # item")]
    if pd != want_p:
        failures.append(f"preservation: parent diff {pd}")
    if kd != want_k:
        failures.append(f"preservation: kid diff {kd}")
    for needle in ("# note: c1 and ac1 appear in this comment only", "link_reason: spells out c1",
                   "mentioning c1", '    rationale: "quoted: still here"', "      and continuing"):
        if needle not in np:
            failures.append(f"preservation: {needle!r} lost")

    # CRLF files keep CRLF; a trailing newline stays (or stays absent)
    repo = _repo()
    text = seed("Parent", children=[SP + "kid.yaml"], cons=["c1"]).replace("\n", "\r\n")
    ktext = seed("Kid", parent=SP + "parent.yaml", refines=["c1"]).replace("\n", "\r\n").rstrip("\r\n")
    put(repo, "parent.yaml", text)
    put(repo, "kid.yaml", ktext)
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    np, nk = read(repo, SP + "parent.yaml"), read(repo, SP + "kid.yaml")
    if code != 0 or np != text.replace("- id: c1", "- id: constraint-1") or \
            nk != ktext.replace("refines: [c1]", "refines: [constraint-1]") or \
            nk.endswith("\n"):
        failures.append(f"CRLF: endings must be preserved: {code} {out} {err!r}")

    # a non-conforming id is reported and left alone; the rest still migrates
    repo = _repo()
    put(repo, "parent.yaml", seed("Parent", children=[SP + "kid.yaml"], cons=["c1", "g7"],
                                  crit=["c3"]))
    put(repo, "kid.yaml", seed("Kid", parent=SP + "parent.yaml", refines=["g7", "c1"]))
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    np = read(repo, SP + "parent.yaml")
    notes = [ln for ln in out if ln.startswith("NOTE") and "left as is" in ln]
    if code != 0 or "- id: g7" not in np or "- id: c3" not in np or "- id: constraint-1" not in np \
            or len(notes) != 2:
        failures.append(f"non-conforming ids: {code} {out}")
    if "refines: [g7, constraint-1]" not in read(repo, SP + "kid.yaml"):
        failures.append("non-conforming ids: a refines entry that already resolves stays as is")
    return failures


def check_ref_scan() -> list[str]:
    """Prose mentioning the Seed slug with a legacy id is reported as REF, never rewritten."""
    failures = []
    repo = _repo()
    _family(repo)
    notes = Path(repo) / "docs"
    (notes / "plan.md").write_text("intro\nsee parent: c1 is open\nunrelated c2 line\n")
    (notes / "other.md").write_text("parent mentioned but no id here\n")
    (notes / "big.bin").write_bytes(b"parent c1\0\0binary")
    (notes / "huge.txt").write_text(("parent c1\n" * 200_000))
    git_add(repo)
    before = (notes / "plan.md").read_text()
    code, out, err = run(repo, SP + "parent.yaml", "--apply")
    refs = [ln for ln in out if ln.startswith("REF ")]
    if code != 0 or refs != ["REF docs/plan.md:2"]:
        failures.append(f"REF scan: expected only docs/plan.md:2, got {refs} (exit {code}, {err!r})")
    if (notes / "plan.md").read_text() != before:
        failures.append("REF scan: prose must never be rewritten")
    if not any("START-PROMPT" in ln for ln in out):
        failures.append("REF scan: the out-of-repo reminder is missing")
    return failures


def check_usage() -> list[str]:
    failures = []
    repo = _repo()
    _family(repo)
    for argv in ([], ["--apply"], [SP + "parent.yaml", "--bogus"], [SP + "parent.yaml", "extra"],
                 [SP + "parent.yaml", "--apply", "--apply"], [SP + "missing.yaml"]):
        p = subprocess.run([sys.executable, str(_MIGRATE), *argv], cwd=repo, capture_output=True,
                           text=True, env=dict(os.environ, GH_BIN=NO_GH))
        if p.returncode != 2 or p.stdout:
            failures.append(f"usage {argv}: expected exit 2 and empty stdout, got {p.returncode} "
                            f"{p.stdout!r}")
    return failures


def check_nothing_to_migrate_leaf() -> list[str]:
    """A Seed with no legacy ids, no parent and no children: nothing to migrate, exit 0."""
    failures = []
    repo = _repo()
    put(repo, "solo.yaml", seed("Solo", cons=["constraint-1"], crit=["acceptance-1"]))
    before = snapshot(repo)
    code, out, _ = run(repo, SP + "solo.yaml", "--apply")
    if code != 0 or snapshot(repo) != before or not any(ln.startswith("nothing to migrate") for ln in out):
        failures.append(f"solo: {code} {out}")
    return failures


def check_children_with_own_legacy_items() -> list[str]:
    """A child's own c<N> items are not the parent run's business: the parent run rewrites only
    the child's refines, and parent-first and child-first orders converge to the same files."""
    failures = []

    def fixture():
        repo = _repo()
        put(repo, "p.yaml", seed("P", children=[SP + "k1.yaml"], cons=["c1"], crit=["ac1"]))
        put(repo, "k1.yaml", seed("K1", parent=SP + "p.yaml", refines=["c1", "ac1"],
                                  cons=["c1"], crit=["ac1"]))
        return repo

    a = fixture()
    code, out, err = run(a, SP + "p.yaml")  # dry run must not be refused
    if code != 0 or "DRY-RUN: 2 file(s) would change; re-run with --apply to write" not in out:
        failures.append(f"child legacy items (dry run): {code} {out} {err!r}")
    code, out, err = run(a, SP + "p.yaml", "--apply")
    kid = read(a, SP + "k1.yaml")
    if code != 0 or "- id: c1   #" not in kid or "- id: ac1   #" not in kid or \
            "refines: [constraint-1, acceptance-1]" not in kid:
        failures.append(f"child legacy items (parent run): {code} {out} {err!r}")
    code, out = relations_check(a, SP + "p.yaml")
    if code != 0:
        failures.append(f"child legacy items: check after the parent run: {code} {out}")
    code, out, err = run(a, SP + "k1.yaml", "--apply")  # the child's own run
    if code != 0 or "- id: constraint-1   #" not in read(a, SP + "k1.yaml") or \
            "- id: acceptance-1   #" not in read(a, SP + "k1.yaml"):
        failures.append(f"child legacy items (child's own run): {code} {out} {err!r}")

    b = fixture()  # child first: its refines stay legacy while the parent is legacy
    code, out, err = run(b, SP + "k1.yaml", "--apply")
    kid = read(b, SP + "k1.yaml")
    if code != 0 or "- id: constraint-1   #" not in kid or "refines: [c1, ac1]" not in kid:
        failures.append(f"child-first (child run): {code} {out} {err!r}")
    code, out, err = run(b, SP + "p.yaml", "--apply")
    if code != 0:
        failures.append(f"child-first (parent run): {code} {out} {err!r}")
    for rel in (SP + "p.yaml", SP + "k1.yaml"):
        if read(a, rel) != read(b, rel):
            failures.append(f"child legacy items: {rel} differs between the two orders")
    if relations_check(b, SP + "k1.yaml")[0] != 0:
        failures.append("child-first: check must pass after both runs")
    return failures


def check_unwritable_refines_reported_as_such() -> list[str]:
    """A refines list the script cannot edit line-wise is refused with that reason, not a
    misleading 'would not define'."""
    failures = []
    repo = _repo()
    put(repo, "p.yaml", seed("P", children=[SP + "k.yaml"], cons=["c1", "c2"]))
    ktext = seed("K", parent=SP + "p.yaml", refines=["c1"]).replace(
        "refines: [c1]   # parent items", "refines: [c1,\n    c2]   # parent items")
    put(repo, "k.yaml", ktext)
    before = snapshot(repo)
    code, out, _ = run(repo, SP + "p.yaml", "--apply")
    problems = [ln for ln in out if ln.startswith("PROBLEM")]
    if code != 1 or snapshot(repo) != before or len(problems) != 1 or \
            "edit it by hand" not in problems[0] or any("would not define" in ln for ln in out):
        failures.append(f"multi-line child refines: {code} {out}")

    repo = _repo()
    put(repo, "up.yaml", seed("Up", children=[SP + "me.yaml"], cons=["constraint-1", "constraint-2"]))
    put(repo, "me.yaml", seed("Me", parent=SP + "up.yaml", refines=["c1"], cons=["c1"]).replace(
        "refines: [c1]   # parent items", "refines: [c1,\n    c2]   # parent items"))
    before = snapshot(repo)
    code, out, _ = run(repo, SP + "me.yaml", "--apply")
    problems = [ln for ln in out if ln.startswith("PROBLEM")]
    if code != 1 or snapshot(repo) != before or len(problems) != 1 or \
            "edit it by hand" not in problems[0] or any("would not define" in ln for ln in out):
        failures.append(f"multi-line own refines: {code} {out}")
    return failures


def check_lifecycle_migration_refusal():
    failures = []
    for structured in ("lifecycle:\n  state: paused\n",
                       "relations:\n  refines_map: []\n"):
        repo = _repo()
        rel = put(repo, "old.yaml", seed("Old", cons=["c1"]) + structured)
        before = snapshot(repo)
        code, out, _ = run(repo, rel, "--apply")
        if code != 1 or not any("coordinated id migration" in line for line in out) or snapshot(repo) != before:
            failures.append(f"structured references must not be orphaned: {code} {out}")
    return failures


def main() -> int:
    checks = [
        check_basic_migration,
        check_mixed_seed,
        check_refusals,
        check_interrupted_runs_converge,
        check_same_id_in_unrelated_seeds,
        check_siblings_and_own_refines,
        check_cross_repo_follow_up,
        check_content_preservation,
        check_ref_scan,
        check_usage,
        check_nothing_to_migrate_leaf,
        check_children_with_own_legacy_items,
        check_unwritable_refines_reported_as_such,
        check_lifecycle_migration_refusal,
    ]
    failures = []
    for check in checks:
        failures += check()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: all {len(checks)} test-seed-id-migrate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
