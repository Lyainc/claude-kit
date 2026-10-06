#!/usr/bin/env python3
"""seed-id-migrate.py — rename a Seed's legacy item ids to the identifier convention.

Why this exists: thinking-tools/reference/identifiers.md names Seed items `constraint-<N>` and
`acceptance-<N>`. Seeds written earlier carry `c<N>` and `ac<N>`, and other Seeds point at them
through `relations.refines`. Readers still accept the old form, but nothing renames it, and the
Seed edit guard (hooks/seed-append-guard.sh) denies an id vanishing in an ordinary edit, a
hand-made rename included. This script is the only rename path.

The rule is fixed, so there is no mapping table to keep or lose: the number is kept.

    c<N>  -> constraint-<N>    in `constraints[]`
    ac<N> -> acceptance-<N>    in `success_criteria[]`

Any other id is left alone (a NOTE lists it). Nothing else changes: the script edits only the
`id:` line of those items and the values of the affected `refines` lists, line by line, so
comments, quoting, block scalars and every other field stay byte-identical.

Usage:
    seed-id-migrate.py <seed-path>            # dry run: print the plan, write nothing
    seed-id-migrate.py <seed-path> --apply    # write it

Scope, written together (an id renamed without its references would break the graph):
  - the named local Seed's own item ids;
  - `relations.refines` of its LOCAL children (its `children:` list; each child's `parent` must
    point back, else the run is refused), mapped against the named Seed's post-migration ids;
  - the named Seed's own `refines`, when its parent is local and already carries the new id.
    (A parent that still has the old ids keeps the old entries valid, so they are not touched.)
A child or parent in another repository is never written: a `FOLLOW-UP` line gives the exact
replacements to apply there. Prose that mentions the Seed together with a legacy id is reported
as `REF <path>:<line>` (from `git ls-files`) for a person to convert deliberately; next-goal
targets and START-PROMPT files outside the repository are not scanned.

Before anything is written, every new text is re-parsed and verified: the same items in the same
order with the same descriptions, every other line and field byte-identical, `refines` mapped by
the rule, and every child entry resolving in the parent's post-migration id set. Any unresolved
`refines` (a pre-existing broken one too), a collision (`c2` and `constraint-2` both present: a
reused number), a duplicate id or a child that does not point back refuses the whole run with
exit 1 and writes nothing. Each file is written atomically (temp file + os.replace). A re-run is
safe: a migrated Seed reports "nothing to migrate". An interrupted run (parent written, child
not, or the reverse) converges when run again, because a child's entry is accepted in either id
form against the parent's post-migration set.

Output lines: SEED, RENAME, REFINES, NOTE, FOLLOW-UP, PROBLEM, REF, WRITTEN, then one summary
line (DRY-RUN / OK / REFUSED / nothing to migrate).
Exit codes: 0 migrated, dry run planned, or nothing to do; 1 refused (problems); 2 bad usage.

Stdlib only; runs on Python 3.9.
"""

from __future__ import annotations

import importlib.util
import os
import posixpath
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
USAGE = "usage: seed-id-migrate.py <seed-path> [--apply]"
MAX_REF = 100
MAX_BYTES = 1_000_000
LIST_KEYS = ("constraints", "success_criteria")
TARGET_FORM = {"constraints": re.compile(r"^constraint-\d+$"),
               "success_criteria": re.compile(r"^acceptance-\d+$")}
ID_LINE = re.compile(r"^(?P<pre>\s*(?:-\s+)?id:[ \t]+)"
                     r"(?P<val>'[^']*'|\"[^\"]*\"|[^\s#'\"][^\s#]*)(?P<post>[ \t]*(?:#.*)?)$")
DASH_LINE = re.compile(r"^(?P<pre>\s*-\s+)"
                       r"(?P<val>'[^']*'|\"[^\"]*\"|[^\s#'\"][^\s#]*)(?P<post>[ \t]*(?:#.*)?)$")
REFINES_FLOW = re.compile(r"^(?P<pre>\s*refines:[ \t]*)\[")
LEGACY_TOKEN = re.compile(r"\b(?:c|ac)\d+\b")


def _load_relations():
    spec = importlib.util.spec_from_file_location("seed_relations",
                                                  os.path.join(HERE, "seed-relations.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sr = _load_relations()


# ---------------------------------------------------------------------------
# Line-level reading of a Seed file
# ---------------------------------------------------------------------------

def rename_of(list_key, item_id):
    """The fixed rule: c<N> -> constraint-<N> in constraints, ac<N> -> acceptance-<N> in criteria."""
    m = sr.LEGACY_ID.match(item_id)
    if m and (m.group(1), list_key) in (("c", "constraints"), ("ac", "success_criteria")):
        return sr.canonical_id(item_id)
    return item_id


def _unq(val):
    return val[1:-1] if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"" else val


def _requote(val, new):
    return val[0] + new + val[0] if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"" else new


def top_blocks(bodies):
    """{top-level key: (key line, first body line, end)}; the last duplicate wins, as in the reader."""
    blocks, cur = {}, None
    for i, ln in enumerate(bodies):
        if sr._skip(ln):
            continue
        if sr._indent(ln) == 0 and not ln.startswith("- "):
            m = sr.KEY_RE.match(ln.strip())
            if m:
                if cur is not None:
                    cur[2] = i
                cur = [i, i + 1, len(bodies)]
                blocks[m.group(1)] = cur
    return {k: tuple(v) for k, v in blocks.items()}


def item_slots(bodies, blocks):
    """Every item entry of constraints[]/success_criteria[] -> dicts with the id line and chunk."""
    slots = []
    for list_key in LIST_KEYS:
        if list_key not in blocks:
            continue
        _, start, end = blocks[list_key]
        body = bodies[start:end]
        starts = [(i, m) for i, m in ((i, sr.ITEM_RE.match(ln)) for i, ln in enumerate(body)) if m]
        if not starts:
            continue
        dash = min(len(m.group(1)) for _, m in starts)
        idx = [i for i, m in starts if len(m.group(1)) == dash]
        for n, i in enumerate(idx):
            e = idx[n + 1] if n + 1 < len(idx) else len(body)
            chunk = list(body[i:e])
            chunk[0] = chunk[0][:dash] + " " + chunk[0][dash + 1:]
            content = [ln for ln in chunk if not sr._skip(ln)]
            base = min(sr._indent(ln) for ln in content)
            id_rel = None
            for j, ln in enumerate(chunk):
                st = ln.strip()
                if sr._skip(ln) or sr._indent(ln) != base or st.startswith("- "):
                    continue
                m = sr.KEY_RE.match(st)
                if m and m.group(1) == "id":
                    id_rel = j
            if id_rel is None:
                continue  # the reader skips an entry without an id as well
            line = start + i + id_rel
            m = ID_LINE.match(bodies[line])
            slots.append({"list": list_key, "line": line, "chunk": (start + i, start + e),
                          "id": _unq(m.group("val")) if m else None})
    return slots


def refines_region(bodies, blocks):
    """-> (refines key line, [following body line indexes]) or None."""
    if "relations" not in blocks:
        return None
    _, start, end = blocks["relations"]
    content = [bodies[i] for i in range(start, end) if not sr._skip(bodies[i])]
    if not content:
        return None
    base = min(sr._indent(ln) for ln in content)
    found = None
    for i in range(start, end):
        ln = bodies[i]
        if sr._skip(ln) or sr._indent(ln) != base or ln.strip().startswith("- "):
            continue
        m = sr.KEY_RE.match(ln.strip())
        if m and m.group(1) == "refines":
            found = i
    if found is None:
        return None
    sub = []
    for i in range(found + 1, end):
        ln = bodies[i]
        if not sr._skip(ln) and sr._indent(ln) == base and not ln.strip().startswith("- "):
            break
        sub.append(i)
    return found, sub


def rewrite_refines(bodies, blocks, fn):
    """Apply fn(entry) -> entry to the refines list in place, touching only the entry text.

    Returns (changes [(old, new)], touched line indexes, problems).
    """
    region = refines_region(bodies, blocks)
    if region is None:
        return [], set(), []
    key_line, sub = region
    changes, touched, problems = [], set(), []
    m = sr.KEY_RE.match(bodies[key_line].strip())
    inline = sr._strip_comment(m.group(2) or "")
    if inline.startswith("["):
        ln = bodies[key_line]
        fm = REFINES_FLOW.match(ln)
        pos = fm.end() if fm else None
        end = None
        if pos is not None:
            q = None
            for i in range(pos, len(ln)):
                ch = ln[i]
                if q:
                    if ch == q:
                        q = None
                elif ch in "'\"" and ln[i - 1] in " \t[,":
                    q = ch
                elif ch == "]":
                    end = i
                    break
        if end is None:
            entries = sr._list(m.group(2) or "", [bodies[i] for i in sub])
            if any(fn(e) != e for e in entries):
                problems.append(f"refines list at line {key_line + 1} spans several lines "
                                "or is not plain; edit it by hand")
            return [], set(), problems
        pieces = sr._split_commas(ln[pos:end])
        out = []
        for piece in pieces:
            core = piece.strip()
            if not core:
                out.append(piece)
                continue
            lead = piece[:len(piece) - len(piece.lstrip())]
            trail = piece[len(piece.rstrip()):]
            old = _unq(core)
            new = fn(old)
            if new != old:
                changes.append((old, new))
                core = _requote(core, new)
            out.append(lead + core + trail)
        if changes:
            bodies[key_line] = ln[:pos] + ",".join(out) + ln[end:]
            touched.add(key_line)
        return changes, touched, problems
    if inline:
        return [], set(), []  # a scalar value is not a list; the reader sees no entries
    for i in sub:
        ln = bodies[i]
        if sr._skip(ln):
            continue
        s = sr._strip_comment(ln.strip())
        if not s.startswith("- "):
            continue
        old = sr._unquote(s[2:])
        new = fn(old)
        if new == old:
            continue
        dm = DASH_LINE.match(ln)
        if not dm or _unq(dm.group("val")) != old:
            problems.append(f"refines entry {old!r} at line {i + 1} is not a plain value; "
                            "edit it by hand")
            continue
        bodies[i] = dm.group("pre") + _requote(dm.group("val"), new) + dm.group("post")
        changes.append((old, new))
        touched.add(i)
    return changes, touched, problems


class Doc:
    """One Seed file: its lines (with their endings), parse, and line-level item slots."""

    def __init__(self, root, rel):
        self.rel = rel
        self.path = os.path.join(root, rel)
        with open(self.path, encoding="utf-8", newline="") as f:
            self.text = f.read()
        raw = self.text.splitlines(keepends=True)
        self.bodies = [ln.rstrip("\r\n") for ln in raw]
        self.eols = [ln[len(b):] for ln, b in zip(raw, self.bodies)]
        self.seed = sr.parse_seed(self.text)
        self.blocks = top_blocks(self.bodies)
        self.slots = item_slots(self.bodies, self.blocks)
        self.new_bodies = list(self.bodies)
        self.touched = set()
        self.id_changes = []   # [(old, new)]
        self.ref_changes = []  # [(old, new)]
        self.problems = []
        self.rename_ids = False  # only the named Seed's own ids are renamed
        if [s["id"] for s in self.slots] != [i for i, _ in self.seed.items]:
            self.problems.append(f"{rel}: cannot locate the item id lines (the reader and the "
                                 "line scan disagree); migrate by hand")

    def ids(self):
        return [s["id"] for s in self.slots]

    def post_ids(self):
        if not self.rename_ids:
            return self.ids()
        return [rename_of(s["list"], s["id"]) for s in self.slots]

    def apply_ids(self):
        for s in self.slots:
            new = rename_of(s["list"], s["id"])
            if new == s["id"]:
                continue
            m = ID_LINE.match(self.bodies[s["line"]])
            if not m:
                self.problems.append(f"{self.rel}: line {s['line'] + 1} id is not a plain value")
                continue
            self.new_bodies[s["line"]] = (m.group("pre") + _requote(m.group("val"), new)
                                          + m.group("post"))
            self.touched.add(s["line"])
            self.id_changes.append((s["id"], new))

    def apply_refines(self, fn):
        changes, touched, problems = rewrite_refines(self.new_bodies, self.blocks, fn)
        self.ref_changes += changes
        self.touched |= touched
        self.problems += [f"{self.rel}: {p}" for p in problems]

    def new_text(self):
        return "".join(b + e for b, e in zip(self.new_bodies, self.eols))

    def changed(self):
        return bool(self.touched)


def resolver(defined):
    """entry -> the entry that resolves in `defined` (as is, else its canonical form), else as is."""
    def fn(entry):
        if entry in defined:
            return entry
        cand = sr.canonical_id(entry)
        return cand if cand != entry and cand in defined else entry
    return fn


def verify(doc, expect_refines):
    """Re-parse the new text and compare it with the old one; -> list of problem strings."""
    text = doc.new_text()
    out = []
    if len(doc.new_bodies) != len(doc.bodies):
        return [f"{doc.rel}: line count changed"]
    stray = [i + 1 for i in range(len(doc.bodies))
             if doc.new_bodies[i] != doc.bodies[i] and i not in doc.touched]
    if stray:
        out.append(f"{doc.rel}: unexpected change at line(s) {stray}")
    old, new = doc.seed, sr.parse_seed(text)
    if [d for _, d in new.items] != [d for _, d in old.items]:
        out.append(f"{doc.rel}: item descriptions or order changed")
    if [i for i, _ in new.items] != doc.post_ids():
        out.append(f"{doc.rel}: item ids are not the planned ones")
    if new.refines != [expect_refines(e) for e in old.refines]:
        out.append(f"{doc.rel}: refines are not the planned ones")
    for attr in ("target", "parent", "depends_on", "children", "link_reason", "source",
                 "tracking"):
        if getattr(new, attr) != getattr(old, attr):
            out.append(f"{doc.rel}: {attr} changed")
    rebodies = [ln.rstrip("\r\n") for ln in text.splitlines(keepends=True)]
    new_slots = item_slots(rebodies, top_blocks(rebodies))
    if [s["id"] for s in new_slots] != doc.post_ids():
        out.append(f"{doc.rel}: re-scanned item ids differ from the plan")
    for before, after in zip(doc.slots, new_slots):
        a, b = before["chunk"], after["chunk"]
        keep = before["line"]
        old_chunk = [ln for i, ln in enumerate(doc.bodies[a[0]:a[1]], a[0]) if i != keep]
        new_chunk = [ln for i, ln in enumerate(doc.new_bodies[b[0]:b[1]], b[0])
                     if i != after["line"]]
        if old_chunk != new_chunk:
            out.append(f"{doc.rel}: an item changed beyond its id line")
    return out


def write_atomic(doc):
    d = os.path.dirname(doc.path)
    mode = os.stat(doc.path).st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(prefix=".seed-id-migrate-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(doc.new_text())
        os.chmod(tmp, mode)
        os.replace(tmp, doc.path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Reference candidates (reported, never rewritten)
# ---------------------------------------------------------------------------

def scan_refs(root, slug, skip):
    """-> (lines, note). Lines `REF <path>:<line>` mentioning the slug with a legacy id token."""
    listing = sr._run_git(root, "ls-files", "-z")
    if listing is None:
        return [], "not a git repository (or nothing tracked): the REF scan was skipped"
    hits = []
    for path in sorted(p for p in listing.split("\0") if p):
        norm = posixpath.normpath(path)
        full = os.path.join(root, path)
        if norm in skip or not os.path.isfile(full):
            continue
        try:
            if os.path.getsize(full) > MAX_BYTES:
                continue
            with open(full, "rb") as f:
                data = f.read()
            if b"\0" in data:
                continue
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, ln in enumerate(text.splitlines(), 1):
            if slug in ln and LEGACY_TOKEN.search(ln):
                hits.append(f"REF {path}:{n}")
    note = None
    if len(hits) > MAX_REF:
        note = f"{len(hits) - MAX_REF} more REF candidate(s) not shown"
        hits = hits[:MAX_REF]
    return hits, note


# ---------------------------------------------------------------------------

def run(seed_file, apply):
    root = sr.find_root(seed_file)
    rel = posixpath.normpath(os.path.relpath(os.path.realpath(seed_file), root).replace(os.sep, "/"))
    rd = sr.Reader(root)
    out, problems = [], []
    named = Doc(root, rel)
    named.rename_ids = True
    problems += named.problems
    self_res = rd.resolve_quiet((None, rel))

    # -- the named Seed's own ids -------------------------------------------------
    ids = named.ids()
    for iid in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"{rel}: duplicate item id {iid}")
    idset = set(ids)
    for iid in ids:
        cand = sr.canonical_id(iid)
        if cand != iid and cand in idset:
            problems.append(f"{rel}: {iid} and {cand} both exist (a reused number)")
    post = named.post_ids()
    for iid in sorted({i for i in post if post.count(i) > 1} - {i for i in ids if ids.count(i) > 1}):
        problems.append(f"{rel}: renaming would make {iid} a duplicate")
    post_set = set(post)
    for s, new in zip(named.slots, post):
        if not TARGET_FORM[s["list"]].match(new):
            out.append(sr._row("NOTE", f"{rel}: id {s['id']} in {s['list']}[] is not "
                                       f"c<N>/ac<N> or the new form — left as is"))
    if not problems:
        named.apply_ids()
    problems += [p for p in named.problems if p not in problems]

    # -- the named Seed's own refines (parent local and already canonical) ---------
    follow, docs = [], [(named, None)]
    own_fn = lambda e: e
    if named.seed.parent and named.seed.refines:
        ploc = rd.norm(named.seed.parent, None)
        legacy = [e for e in named.seed.refines if sr.LEGACY_ID.match(e)]
        if ploc[0] is not None:
            if legacy:
                follow.append(f"FOLLOW-UP {rel} relations.refines [{', '.join(legacy)}] point into "
                              f"{sr.key(ploc)} (another repo, not written): once that Seed uses the "
                              f"new ids, replace "
                              f"{', '.join(f'{e} -> {sr.canonical_id(e)}' for e in legacy)}")
        else:
            pres = rd.resolve_quiet(ploc)
            pfile = os.path.join(root, pres[1])
            if not os.path.isfile(pfile):
                problems.append(f"{rel}: parent {sr.key(pres)} does not exist, so its refines "
                                "cannot be checked")
            else:
                with open(pfile, encoding="utf-8") as f:
                    pset = {i for i, _ in sr.parse_seed(f.read()).items}
                own_fn = resolver(pset)
                for e in named.seed.refines:
                    if own_fn(e) not in pset:
                        problems.append(f"{rel} refines {e}, which {sr.key(pres)} does not define")
                if not problems:
                    named.apply_refines(own_fn)
                    problems += [p for p in named.problems if p not in problems]

    # -- local children ------------------------------------------------------------
    children = []
    if self_res != (None, rel):
        out.append(sr._row("NOTE", f"newer generation exists: {sr.key(self_res)} — children's "
                                   "refines belong to it; migrate that file for them"))
    else:
        seen = {(None, rel)}
        for c in named.seed.children:
            cloc = rd.norm(c, None)
            if cloc[0] is not None:
                reps = [f"{legacy} -> {new}" for legacy, new in
                        ((sr.legacy_form(i), i) for i in post if sr.CANONICAL_ID.match(i))]
                if reps:
                    follow.append(f"FOLLOW-UP {sr.key(cloc)} relations.refines (another repo, not "
                                  f"written): for any of these it lists, replace "
                                  f"{', '.join(reps)}")
                continue
            cres = rd.resolve_quiet(cloc)
            if cres in seen:
                continue
            seen.add(cres)
            if not os.path.isfile(os.path.join(root, cres[1])):
                problems.append(f"{rel}: child {sr.key(cres)} does not exist")
                continue
            child = Doc(root, cres[1])
            problems += child.problems
            back = child.seed.parent
            if not back or rd.resolve_quiet(rd.norm(back, None)) != self_res:
                problems.append(f"{child.rel}: parent does not point back to {rel}; fix the "
                                "relation before migrating")
                continue
            fn = resolver(post_set)
            for e in child.seed.refines:
                if fn(e) not in post_set:
                    problems.append(f"{child.rel} refines {e}, which {rel} does not define")
            if not problems:
                child.apply_refines(fn)
                problems += [p for p in child.problems if p not in problems]
            children.append((child, fn))
            docs.append((child, fn))
    named_fn = own_fn

    # -- verify everything before any write ---------------------------------------
    if not problems:
        for doc, fn in docs:
            problems += verify(doc, named_fn if doc is named else fn)
        new_named = sr.parse_seed(named.new_text())
        new_set = {i for i, _ in new_named.items}
        for child, _ in children:
            for e in sr.parse_seed(child.new_text()).refines:
                if e not in new_set:
                    problems.append(f"{child.rel} refines {e}, which {rel} would not define")

    if problems:
        out += [sr._row("PROBLEM", p) for p in problems]
        out.append(f"REFUSED: {len(problems)} problem(s); nothing written")
        return out, 1

    changed = [doc for doc, _ in docs if doc.changed()]
    out.insert(0, sr._row("SEED", f"{rel}  (own ids: {len(named.id_changes)} to rename, own "
                                  f"refines: {len(named.ref_changes)}, local children: "
                                  f"{len(children)})"))
    for doc, _ in docs:
        out += [sr._row("RENAME", f"{doc.rel}  {a} -> {b}") for a, b in doc.id_changes]
        out += [sr._row("REFINES", f"{doc.rel}  {a} -> {b}") for a, b in doc.ref_changes]
    out += follow
    skip = {posixpath.normpath(doc.rel) for doc, _ in docs}
    refs, note = scan_refs(root, sr.seed_slug(rel), skip)
    out += refs
    if note:
        out.append(sr._row("NOTE", note))
    out.append(sr._row("NOTE", "next-goal targets and START-PROMPT files outside this repo are not "
                               "scanned; convert their c<N>/ac<N> references by hand"))
    if not changed:
        out.append(f"nothing to migrate: {rel} and its local children already use the new ids")
        return out, 0
    if not apply:
        out.append(f"DRY-RUN: {len(changed)} file(s) would change; re-run with --apply to write")
        return out, 0
    for doc in changed:
        write_atomic(doc)
        out.append(sr._row("WRITTEN", doc.rel))
    out.append(f"OK: migrated {len(changed)} file(s)")
    return out, 0


def main(argv):
    args = argv[1:]
    apply = "--apply" in args
    rest = [a for a in args if a != "--apply"]
    if len(rest) != 1 or rest[0].startswith("--") or len(args) - len(rest) > 1:
        print(USAGE, file=sys.stderr)
        return 2
    if not os.path.isfile(rest[0]):
        print(f"seed-id-migrate: not a file: {rest[0]}", file=sys.stderr)
        return 2
    lines, code = run(rest[0], apply)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
