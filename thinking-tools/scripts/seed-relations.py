#!/usr/bin/env python3
"""seed-relations.py — read a build-spec Seed's edges to other Seeds (#780).

Why this exists: Seeds had no machine-readable edges. When a child Seed finished, next-goal
could not follow the parent, the sibling Seeds or the parent's still-open c*/ac* items — a
person had to find them by hand. Seeds now carry a `relations:` block (parent, refines,
depends_on, children; see thinking-tools/skills/build-spec/templates/SEED_SPEC.yaml). This
script reads those edges and prints them, deterministically, with no LLM.

What it does not do, on purpose:
  - It never judges whether a Seed is finished or a parent item is satisfied (c1). Relations
    hold no status; whether something is done is a judgment about the repository, and that
    stays with next-goal. Output carries edges and ids, never a done/pending value.
  - It never writes anything (c6). Another repo's Seed is only read, through `gh api`; a
    missing child in another repo's `children` is reported, not fixed.
  - It never runs without a named Seed (c7). The old "never glob a spec directory" rule stays;
    the only Seeds reached are the ones the named Seed's explicit edges point to.

Usage:
    seed-relations.py tree  <seed-path>   # parent / refines / siblings / children / parent items
    seed-relations.py check <seed-path>   # do the named Seed's edges agree in both directions?

`<seed-path>` is a local file. Same-repo edges are repo-root-relative paths; another repo's
Seed is a coordinate `owner/repo:docs/specs/x.yaml`. An edge names the file as written and is
followed to the latest `-vN` of the same slug (`foo.yaml` -> `foo-v3.yaml`; the unsuffixed
file counts as v1). `GH_BIN` overrides the `gh` executable (tests use a shim).

This repo's own `owner/repo` (so a coordinate that points here is read from disk, not `gh`) comes
from the origin URL in any form (https, ssh://, scp-like `git@alias:o/r`, any host), else from
`gh repo view`; owner/repo compare case-insensitively. If the named file has a newer `-vN`, it is
still the Seed described, and a `NOTE      newer generation exists: <path>` line says so.

If `gh api` fails, an explicit `[seed-relations FAILED] ...` line is printed instead of an
empty section, and the remaining edges are still read.

Exit codes: tree 0 (data, not a verdict; the FAILED line is the signal), 2 on bad usage.
            check 0 consistent, 1 any MISMATCH, 2 any FAILED with no MISMATCH (or bad usage).

Stdlib only; runs on Python 3.9 (the hook and next-goal use the system python3).
"""

from __future__ import annotations

import base64
import json
import os
import posixpath
import re
import subprocess
import sys
from urllib.parse import quote

TRUNC = 100
COORD = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+):(.+)$")
KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
ITEM_RE = re.compile(r"^(\s*)-\s+([A-Za-z_][\w-]*):(?:\s+(.*))?$")
VERSION_SUFFIX = re.compile(r"-v(\d+)$")
# Any origin URL that ends in owner/repo: https://host/o/r(.git), ssh://git@host[:port]/o/r(.git),
# and the scp-like `git@any-host-alias:o/r(.git)`. The host is not required to be github.com.
REMOTE_URL = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9+.-]*://(?:[^@/]+@)?[^/]+/|(?:[^@/:]+@)?[^/:]+:)"
    r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
NAME_WITH_OWNER = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
LINK_ONLY = " (다른 레포 — 여기서 판정 안 함, 링크만)"
_UNSET = object()


# ---------------------------------------------------------------------------
# Minimal YAML reader — exactly what a Seed needs, nothing more (no PyYAML).
# ---------------------------------------------------------------------------

def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _skip(line):
    s = line.strip()
    return not s or s.startswith("#") or s == "---"


def _strip_comment(s):
    """Drop a trailing ` # comment`, leaving quoted text alone."""
    quote_ch = None
    for i, ch in enumerate(s):
        if quote_ch:
            if ch == quote_ch:
                quote_ch = None
        elif ch in "'\"" and (i == 0 or s[i - 1] in " \t[,{"):
            quote_ch = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1]
    return s


def _mapping_blocks(lines):
    """Split lines into [(key, inline_value, body_lines)] for keys at the block's base indent."""
    content = [ln for ln in lines if not _skip(ln)]
    if not content:
        return []
    base = min(_indent(ln) for ln in content)
    blocks = []
    cur = None
    for ln in lines:
        if _skip(ln):
            if cur is not None:
                cur[2].append(ln)
            continue
        s = ln.strip()
        m = KEY_RE.match(s) if _indent(ln) == base and not s.startswith("- ") else None
        if m:
            cur = [m.group(1), m.group(2) or "", []]
            blocks.append(cur)
        elif cur is not None:
            cur[2].append(ln)
    return [tuple(b) for b in blocks]


def _scalar(inline, body):
    """A scalar value: inline text, a `>-`/`|` block scalar, or plain continuation lines."""
    block = inline.strip()[:1] in (">", "|")
    v = "" if block else _strip_comment(inline)
    parts = [v] if v else []
    for ln in body:
        if _skip(ln):
            continue
        parts.append(ln.strip() if block else _strip_comment(ln.strip()))
    return _unquote(" ".join(parts))


def _null(v):
    return v is None or v.strip() in ("", "null", "~", "Null", "NULL")


def _split_commas(s):
    out, cur, quote_ch = [], [], None
    for ch in s:
        if quote_ch:
            cur.append(ch)
            if ch == quote_ch:
                quote_ch = None
        elif ch in "'\"":
            quote_ch = ch
            cur.append(ch)
        elif ch == ",":
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def _list(inline, body):
    """A list value in flow (`[a, b]`) or block (`- a`) form; null / empty gives []."""
    v = _strip_comment(inline)
    if v.startswith("["):
        text = v + " " + " ".join(_strip_comment(ln.strip()) for ln in body if not _skip(ln))
        end = text.rfind("]")
        inner = text[1:end] if end > 0 else text[1:]
        return [_unquote(x) for x in _split_commas(inner) if x.strip()]
    if v:
        return []
    items = []
    for ln in body:
        if _skip(ln):
            continue
        s = _strip_comment(ln.strip())
        if s.startswith("- "):
            item = _unquote(s[2:])
            if not _null(item):
                items.append(item)
    return items


def _items(body):
    """`- id: c1 / description: ...` entries -> [(id, description)]."""
    starts = [(i, m) for i, m in ((i, ITEM_RE.match(ln)) for i, ln in enumerate(body)) if m]
    if not starts:
        return []
    dash = min(len(m.group(1)) for _, m in starts)
    idx = [i for i, m in starts if len(m.group(1)) == dash]
    out = []
    for n, i in enumerate(idx):
        end = idx[n + 1] if n + 1 < len(idx) else len(body)
        chunk = list(body[i:end])
        chunk[0] = chunk[0][:dash] + " " + chunk[0][dash + 1:]
        fields = {k: (inline, b) for k, inline, b in _mapping_blocks(chunk)}
        if "id" not in fields:
            continue
        cid = _scalar(*fields["id"])
        desc = _scalar(*fields["description"]) if "description" in fields else ""
        out.append((cid, desc))
    return out


class Seed:
    def __init__(self, target, parent, refines, depends_on, children, items):
        self.target = target
        self.parent = parent
        self.refines = refines
        self.depends_on = depends_on
        self.children = children
        self.items = items  # [(id, description)] constraints first, then success_criteria
        self.item_map = dict(items)


def parse_seed(text):
    top = {k: (inline, body) for k, inline, body in _mapping_blocks(text.splitlines())}
    target = _scalar(*top["target"]) if "target" in top else ""
    rel = {}
    if "relations" in top:
        rel = {k: (inline, body) for k, inline, body in _mapping_blocks(top["relations"][1])}
    parent = _scalar(*rel["parent"]) if "parent" in rel else None
    if _null(parent):
        parent = None

    def lst(key):
        return _list(*rel[key]) if key in rel else []

    items = []
    for key in ("constraints", "success_criteria"):
        if key in top:
            items += _items(top[key][1])
    return Seed(target, parent, lst("refines"), lst("depends_on"), lst("children"), items)


# ---------------------------------------------------------------------------
# Locations, -vN resolution, reading
# ---------------------------------------------------------------------------

def pick_latest(names, path):
    """Return `path` with its slug moved to the highest `-vN` present in `names`.

    `foo.yaml` counts as v1. Unrelated files (`foobar.yaml`, `foo-v2-x.yaml`) never match.
    If nothing in `names` matches the slug, `path` is returned unchanged.
    """
    d, base = posixpath.split(path)
    stem, ext = posixpath.splitext(base)
    slug = VERSION_SUFFIX.sub("", stem)
    pat = re.compile(r"^" + re.escape(slug) + r"(?:-v(\d+))?" + re.escape(ext) + r"$")
    best = None
    for name in names:
        m = pat.match(name)
        if m:
            cand = (int(m.group(1)) if m.group(1) else 1, name)
            if best is None or cand > best:
                best = cand
    if best is None:
        return path
    return posixpath.join(d, best[1]) if d else best[1]


def key(loc):
    repo, path = loc
    return path if repo is None else f"{repo}:{path}"


def disp(orig, resolved):
    return key(orig) if orig == resolved else f"{key(orig)} -> {key(resolved)}"


class Loaded:
    def __init__(self, orig, loc, seed, status, failed_line=None):
        self.orig = orig        # location as written (normalized)
        self.loc = loc          # after -vN resolution
        self.seed = seed        # Seed or None
        self.status = status    # "ok" | "failed" | "notfound"
        self.failed_line = failed_line


class Reader:
    def __init__(self, root):
        self.root = root
        self._self_repo = _UNSET
        self._lists = {}
        self._loaded = {}
        self._reported = set()

    # -- this repo's own `owner/repo` (looked up once, and only when an edge needs it) ----
    @property
    def self_repo(self):
        if self._self_repo is _UNSET:
            self._self_repo = origin_coordinate(self.root)
        return self._self_repo

    def is_self(self, repo):
        """GitHub ignores case in owner/repo, so this does too."""
        mine = self.self_repo
        return mine is not None and repo.lower() == mine.lower()

    # -- gh -----------------------------------------------------------------
    @staticmethod
    def _gh_api(endpoint):
        gh = os.environ.get("GH_BIN", "gh")
        try:
            p = subprocess.run([gh, "api", endpoint], capture_output=True, encoding="utf-8",
                               timeout=60)
        except (FileNotFoundError, PermissionError):
            return None, f"{gh} not found"
        except subprocess.TimeoutExpired:
            return None, "timed out"
        if p.returncode != 0:
            first = next((ln.strip() for ln in p.stderr.splitlines() if ln.strip()), "")
            return None, first or f"exit code {p.returncode}"
        try:
            return json.loads(p.stdout), None
        except ValueError:
            return None, "response was not JSON"

    @staticmethod
    def _endpoint(repo, path):
        return f"repos/{repo}/contents" + (f"/{quote(path, safe='/')}" if path else "")

    # -- edge paths ---------------------------------------------------------
    def norm(self, edge, ctx_repo):
        """Edge text -> (repo, path). repo None means this repo (root-relative path)."""
        m = COORD.match(edge)
        repo, path = (m.group(1), m.group(2)) if m else (ctx_repo, edge)
        path = posixpath.normpath(path.strip().lstrip("/"))
        if repo is not None and self.is_self(repo):
            repo = None
        return (repo, path)

    # -- listing / resolving ------------------------------------------------
    def _list_dir(self, repo, d):
        k = (repo, d)
        if k not in self._lists:
            if repo is None:
                try:
                    names = sorted(os.listdir(os.path.join(self.root, d)))
                except OSError:
                    names = []
                self._lists[k] = (names, None)
            else:
                data, err = self._gh_api(self._endpoint(repo, d))
                if err:
                    self._lists[k] = (None, err)
                elif isinstance(data, list):
                    self._lists[k] = ([e.get("name", "") for e in data if isinstance(e, dict)], None)
                else:
                    self._lists[k] = ([], None)
        return self._lists[k]

    def resolve(self, loc):
        """-> (resolved_loc, error). error only for a failed gh listing."""
        repo, path = loc
        names, err = self._list_dir(repo, posixpath.dirname(path))
        if err:
            return loc, err
        return (repo, pick_latest(names, path)), None

    def resolve_quiet(self, loc):
        """Resolve for comparison only; a listing failure falls back to the path as written."""
        return self.resolve(loc)[0]

    # -- loading ------------------------------------------------------------
    def load(self, loc):
        if loc in self._loaded:
            return self._loaded[loc]
        rloc, err = self.resolve(loc)
        if err:
            res = Loaded(loc, loc, None, "failed", self._fail_line(loc, err))
        else:
            repo, path = rloc
            if repo is None:
                try:
                    with open(os.path.join(self.root, path), encoding="utf-8") as f:
                        res = Loaded(loc, rloc, parse_seed(f.read()), "ok")
                except OSError:
                    res = Loaded(loc, rloc, None, "notfound")
            else:
                data, err = self._gh_api(self._endpoint(repo, path))
                text = None
                if not err:
                    try:
                        if isinstance(data, dict) and data.get("encoding") == "base64":
                            text = base64.b64decode(data.get("content", "")).decode("utf-8")
                        else:
                            err = "response had no base64 content"
                    except (ValueError, UnicodeDecodeError):
                        err = "content was not valid base64 UTF-8"
                if err:
                    res = Loaded(loc, rloc, None, "failed", self._fail_line(loc, err))
                else:
                    res = Loaded(loc, rloc, parse_seed(text), "ok")
        self._loaded[loc] = res
        return res

    @staticmethod
    def _fail_line(loc, err):
        return f"[seed-relations FAILED] {key(loc)} — gh api: {err}"

    def failure_lines(self, loaded):
        """The FAILED line for a load, the first time only (so it is never repeated)."""
        if loaded.status == "failed" and loaded.orig not in self._reported:
            self._reported.add(loaded.orig)
            return [loaded.failed_line]
        return []


# ---------------------------------------------------------------------------
# Repo context
# ---------------------------------------------------------------------------

def _run_git(directory, *args):
    try:
        p = subprocess.run(["git", "-C", directory, *args], capture_output=True,
                           encoding="utf-8", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None


def find_root(seed_file):
    d = os.path.dirname(os.path.realpath(seed_file))
    top = _run_git(d, "rev-parse", "--show-toplevel")
    if top:
        return os.path.realpath(top)
    cur = d
    while True:
        if os.path.isdir(os.path.join(cur, "docs")):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            return d
        cur = nxt


def _gh_repo_view(root):
    """`gh repo view` in the repo root -> `owner/repo`, or None when gh is missing or fails."""
    gh = os.environ.get("GH_BIN", "gh")
    try:
        p = subprocess.run([gh, "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                           cwd=root, capture_output=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = p.stdout.strip()
    return out if p.returncode == 0 and NAME_WITH_OWNER.match(out) else None


def origin_coordinate(root):
    """This repo's `owner/repo`: parsed from the origin URL, else asked of `gh`, else None."""
    url = _run_git(root, "remote", "get-url", "origin")
    m = REMOTE_URL.match(url) if url else None
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return _gh_repo_view(root)


def _short(desc):
    return desc if len(desc) <= TRUNC else desc[:TRUNC] + "..."


def _row(label, text):
    return (label.ljust(10) if len(label) < 10 else label + " ") + text


def _newer_note(rel, self_res):
    """A NOTE line when the named file has a newer -vN; the named file stays the Seed described."""
    if self_res == (None, rel):
        return []
    return [_row("NOTE", f"newer generation exists: {key(self_res)}")]


# ---------------------------------------------------------------------------
# tree
# ---------------------------------------------------------------------------

def cmd_tree(rd, rel, seed):
    out = [_row("SEED", f"{rel}  (target: {seed.target or '(none)'})")]
    self_res = rd.resolve_quiet((None, rel))
    out += _newer_note(rel, self_res)

    parent = None
    if seed.parent:
        ploc = rd.norm(seed.parent, None)
        parent = rd.load(ploc)
        line = _row("PARENT", disp(parent.orig, parent.loc))
        if parent.status == "notfound":
            line += "  [file not found]"
        if parent.loc[0] is not None:
            line += LINK_ONLY
        out.append(line)
        out += rd.failure_lines(parent)
    else:
        out.append(_row("PARENT", "(none)"))

    for rid in seed.refines:
        if parent is None:
            note = "[no parent]"
        elif parent.seed is None:
            note = "[parent unreadable]"
        elif rid in parent.seed.item_map:
            note = _short(parent.seed.item_map[rid])
        else:
            note = "[missing in parent]"
        out.append(_row("REFINES", f"{rid} — {note}"))

    # Family = the parent's children (resolved) — used for siblings and for who refines what.
    family = []  # [(resolved loc, display, Loaded)]
    seen = set()
    if parent is not None and parent.seed is not None:
        for c in parent.seed.children:
            ld = rd.load(rd.norm(c, parent.loc[0]))
            if ld.loc in seen:
                continue
            seen.add(ld.loc)
            family.append(ld)
    siblings = [ld for ld in family if ld.loc != self_res]
    listed = {ld.loc for ld in siblings} | {self_res}
    for d in seed.depends_on:
        ld = rd.load(rd.norm(d, None))
        if ld.loc not in listed:
            listed.add(ld.loc)
            siblings.append(ld)

    for ld in siblings:
        line = _row("SIBLING", disp(ld.orig, ld.loc))
        if ld.seed is not None:
            line += f"  (target: {ld.seed.target or '(none)'})"
        elif ld.status == "notfound":
            line += "  [file not found]"
        if ld.loc[0] is not None:
            line += LINK_ONLY
        out.append(line)
        out += rd.failure_lines(ld)
        if ld.seed is None:
            continue
        for dep in ld.seed.depends_on:
            dloc = rd.norm(dep, ld.loc[0])
            dres = rd.resolve_quiet(dloc) if dloc[0] is None else dloc
            note = ("same repo — next-goal judges whether it is finished" if dres[0] is None
                    else "다른 레포 — 확인 못 함")
            out.append(_row("SIBLING", f"{disp(ld.orig, ld.loc)}  requires {disp(dloc, dres)} ({note})"))

    for c in seed.children:
        ld = rd.load(rd.norm(c, None))
        line = _row("CHILD", disp(ld.orig, ld.loc))
        if ld.status == "notfound":
            line += "  [file not found]"
        out.append(line)
        out += rd.failure_lines(ld)

    if parent is not None and parent.seed is not None:
        refiners = []  # [(display, refines list)]
        for ld in family:
            if ld.loc == self_res:
                continue
            if ld.seed is not None:
                refiners.append((key(ld.loc), ld.seed.refines))
        refiners.append((rel, seed.refines))
        mark = LINK_ONLY if parent.loc[0] is not None else ""
        for iid, desc in parent.seed.items:
            who = [name for name, refs in refiners if iid in refs]
            out.append(_row("PARENT-ITEM", f"{iid} — {_short(desc)}  refined by: "
                            f"{', '.join(who) if who else '(none)'}{mark}"))
    return out, 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def cmd_check(rd, rel, seed):
    mismatches = 0
    failed = 0
    edges = 0
    self_res = rd.resolve_quiet((None, rel))
    out = _newer_note(rel, self_res)

    def mismatch(text):
        nonlocal mismatches
        mismatches += 1
        out.append(_row("MISMATCH", text))

    def fail(ld):
        nonlocal failed
        failed += 1
        out.extend(rd.failure_lines(ld))

    if seed.parent:
        parent = rd.load(rd.norm(seed.parent, None))
        pname = key(parent.loc)
        if parent.status == "failed":
            fail(parent)
        elif parent.status == "notfound":
            edges += 1
            mismatch(f"{rel} parent {key(parent.orig)} does not exist")
        else:
            edges += 1
            kids = {rd.resolve_quiet(rd.norm(c, parent.loc[0])) for c in parent.seed.children}
            if self_res not in kids:
                if parent.loc[0] is None:
                    mismatch(f"{pname} children is missing {rel}")
                else:
                    self_name = f"{rd.self_repo}:{rel}" if rd.self_repo else rel
                    mismatch(f"{pname} children is missing {self_name} — 부모 레포에서 추가 필요")
            for rid in seed.refines:
                edges += 1
                if rid not in parent.seed.item_map:
                    mismatch(f"{rel} refines {rid}, which {pname} does not define")

    for c in seed.children:
        child = rd.load(rd.norm(c, None))
        if child.status == "failed":
            fail(child)
            continue
        edges += 1
        if child.status == "notfound":
            mismatch(f"{rel} children names {key(child.orig)}, which does not exist")
            continue
        back = child.seed.parent
        back_res = rd.resolve_quiet(rd.norm(back, child.loc[0])) if back else None
        if back_res != self_res:
            mismatch(f"{key(child.loc)} parent does not point back to {rel}")

    if mismatches:
        out.append(f"FOUND: {mismatches} mismatch(es)")
        return out, 1
    out.append(f"OK: {edges} edge(s) consistent")
    return out, 2 if failed else 0


# ---------------------------------------------------------------------------

def main(argv):
    if len(argv) != 3 or argv[1] not in ("tree", "check"):
        print("usage: seed-relations.py tree|check <seed-path>   (a named Seed is required)",
              file=sys.stderr)
        return 2
    cmd, seed_file = argv[1], argv[2]
    if not os.path.isfile(seed_file):
        print(f"seed-relations: not a file: {seed_file}", file=sys.stderr)
        return 2
    root = find_root(seed_file)
    rel = posixpath.normpath(
        os.path.relpath(os.path.realpath(seed_file), root).replace(os.sep, "/"))
    with open(seed_file, encoding="utf-8") as f:
        seed = parse_seed(f.read())
    rd = Reader(root)
    lines, code = (cmd_tree if cmd == "tree" else cmd_check)(rd, rel, seed)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
