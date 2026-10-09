#!/usr/bin/env python3
"""Read-only Seed relationship and lifecycle discovery (#780, #814).

Usage: tree|check <seed>; walk <seed> [--max-depth N] [--max-nodes N] [--json];
       metadata|read <seed> [--json]. A named file is always required.

metadata returns title, short goal, lifecycle/reason and eligibility without requirement
bodies. read explicitly returns requirement bodies. walk preserves bounded BFS and all
visited nodes, including closed/unknown Seeds; inactive nodes omit item_desc. Every node
has lifecycle {state,outcome,reason} and eligibility {eligible,reason,excluded_items,
review_required}. These are represented decision gates, never a judgment of fulfillment.

relations.version 2 and lifecycle-bearing edges pin exact files. Only unversioned legacy
edges to legacy targets retain latest -vN resolution. Provenance reads the exact recorded
file at its full Git commit, or reports historical source unavailable. Other-repo reads
use gh api, GH_BIN may override the executable; external walk nodes are not expanded.

check validates lifecycle and relationships; failed reads are visible. Exit codes: check
0 consistent, 1 mismatch, 2 read failure; metadata/read 1 malformed input; tree/walk are
read-only data (0), bad usage is 2. Stdlib only; unsupported YAML fails visibly.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
from pathlib import Path
import json
import os
import posixpath
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote

_lc_spec = importlib.util.spec_from_file_location("seed_lifecycle", Path(__file__).with_name("seed-lifecycle.py"))
lifecycle = importlib.util.module_from_spec(_lc_spec)
_lc_spec.loader.exec_module(lifecycle)

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
UNRECORDED = "(기록 없음 — 미확인)"
USAGE = ("usage: seed-relations.py tree|check <seed-path>\n"
         "       seed-relations.py metadata|read <seed-path> [--json]\n"
         "       seed-relations.py walk <seed-path> [--max-depth N] [--max-nodes N] [--json]\n"
         "(a named Seed is required)")
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
    def __init__(self, target, parent, refines, depends_on, children, items,
                 link_reason=None, source=None, tracking=None):
        self.target = target
        self.parent = parent
        self.refines = refines
        self.depends_on = depends_on
        self.children = children
        self.items = items  # [(id, description)] constraints first, then success_criteria
        self.item_map = dict(items)  # a repeated id collapses here; duplicate_ids reports it
        seen, dups = set(), []
        for iid, _ in items:
            if iid in seen and iid not in dups:
                dups.append(iid)
            seen.add(iid)
        self.duplicate_ids = dups
        self.link_reason = link_reason  # None = not recorded (or an old Seed)
        self.source = source            # issues.source, None = not recorded
        self.tracking = tracking or []  # issues.tracking


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

    link_reason = _scalar(*rel["link_reason"]) if "link_reason" in rel else None
    if _null(link_reason):
        link_reason = None

    iss = {}
    if "issues" in top:
        iss = {k: (inline, body) for k, inline, body in _mapping_blocks(top["issues"][1])}
    source = _scalar(*iss["source"]) if "source" in iss else None
    if _null(source):
        source = None
    tracking = _list(*iss["tracking"]) if "tracking" in iss else []

    items = []
    for key in ("constraints", "success_criteria"):
        if key in top:
            items += _items(top[key][1])
    seed = Seed(target, parent, lst("refines"), lst("depends_on"), lst("children"), items,
                link_reason=link_reason, source=source, tracking=tracking)
    seed.format_errors = []
    seed.lifecycle = None
    seed.relations_version = None
    seed.relations_data = {}
    seed.requirements = {}
    seed.semantic = {}
    seed.title = _short(target)
    goal = {k: (v,b) for k,v,b in _mapping_blocks(top.get("goal", ("",[]))[1])}
    seed.short_goal = _short(_scalar(*goal["statement"])) if "statement" in goal else ""
    strict = "lifecycle" in top or any(k in rel for k in ("version","refines_map","provenance","replaces","transfers"))
    for name in ("relations", "lifecycle"):
        if name in top:
            try:
                value = lifecycle.parse_block(*top[name])
                if not isinstance(value, dict):
                    raise lifecycle.FormatError(name + " must be a mapping")
                if name == "relations":
                    seed.relations_data = value
                    seed.relations_version = value.get("version")
                    if strict:
                        for field in ("parent", "refines", "children", "depends_on"):
                            if field in value:
                                setattr(seed, field, value[field])
                else:
                    seed.lifecycle = value
            except lifecycle.FormatError as exc:
                if strict:
                    seed.format_errors.append(str(exc))
    if strict:
        blocks = _mapping_blocks(text.splitlines())
        if len(blocks) != len(top):
            seed.format_errors.append("duplicate top-level key")
        for name, inline, body in blocks:
            try:
                value = lifecycle.parse_block(inline, body)
                seed.semantic[name] = value
                if name in ("constraints", "success_criteria"):
                    if value is not None and not isinstance(value, list):
                        raise lifecycle.FormatError(name + " must be a sequence")
                    for item in value or []:
                        if not isinstance(item,dict) or not lifecycle.text(item.get("id")):
                            raise lifecycle.FormatError(name + " items must have an id")
                        seed.requirements[item["id"]] = item
            except lifecycle.FormatError as exc:
                seed.format_errors.append(name + ": " + str(exc))
    else:
        # A legacy baseline can be compared during its first lifecycle adoption.
        for name in ("constraints", "success_criteria"):
            if name in top:
                try:
                    for item in lifecycle.parse_block(*top[name]) or []:
                        if isinstance(item,dict) and "id" in item:
                            seed.requirements[item["id"]] = item
                except lifecycle.FormatError:
                    seed.format_errors.append("requirements cannot be parsed for transition")
    # Invalid shapes remain visible to validation; prevent traversal from crashing.
    for field in ("refines", "children", "depends_on"):
        value = getattr(seed,field)
        if not isinstance(value,list) or any(not isinstance(v,str) for v in value):
            seed.format_errors.append("relations." + field + " must be a string list")
            setattr(seed,field,[])
    if seed.parent is not None and not isinstance(seed.parent,str):
        seed.format_errors.append("relations.parent must be a path or null")
        seed.parent = None
    return seed


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


# Item ids follow thinking-tools/reference/identifiers.md: `constraint-N` / `acceptance-N` in the
# file, `<slug>/<id>` (or `owner/repo:<slug>/<id>`) whenever shown outside it. `c<N>`/`ac<N>` is
# the pre-convention form: still read as a plain string, reported by `check`, renamed only by
# seed-id-migrate.py. The number is kept, so the rename needs no mapping table.
LEGACY_ID = re.compile(r"^(c|ac)(\d+)$")
LEGACY_KIND = {"c": "constraint", "ac": "acceptance"}


def canonical_id(item_id):
    """`c3` -> `constraint-3`, `ac2` -> `acceptance-2`; any other id is returned unchanged."""
    m = LEGACY_ID.match(item_id)
    return f"{LEGACY_KIND[m.group(1)]}-{m.group(2)}" if m else item_id


def seed_slug(path):
    """`docs/specs/foo-v3.yaml` -> `foo`: the affiliation of a Seed's items."""
    stem = posixpath.splitext(posixpath.basename(path))[0]
    return VERSION_SUFFIX.sub("", stem)


def qualified_id(seed_key, item_id):
    """Full identifier of a Seed item: `foo/constraint-1`, or `owner/repo:foo/constraint-1`.

    `seed_key` is a walk/tree key — a repo-relative path or an `owner/repo:path` coordinate.
    """
    m = COORD.match(seed_key)
    if m:
        return f"{m.group(1)}:{seed_slug(m.group(2))}/{item_id}"
    return f"{seed_slug(seed_key)}/{item_id}"


CANONICAL_ID = re.compile(r"^(constraint|acceptance)-(\d+)$")


def legacy_form(item_id):
    """`constraint-3` -> `c3`, `acceptance-2` -> `ac2`; any other id is returned unchanged."""
    m = CANONICAL_ID.match(item_id)
    return ("c" if m.group(1) == "constraint" else "ac") + m.group(2) if m else item_id


def other_id_form(item_id, defined):
    """The same item under the other id form, when `defined` (an id container) has it."""
    for cand in (canonical_id(item_id), legacy_form(item_id)):
        if cand != item_id and cand in defined:
            return cand
    return None


def legacy_ids(seed):
    return [iid for iid, _ in seed.items if LEGACY_ID.match(iid)]


def disp(orig, resolved):
    return key(orig) if orig == resolved else f"{key(orig)} -> {key(resolved)}"


class Loaded:
    def __init__(self, orig, loc, seed, status, failed_line=None, error=None):
        self.orig = orig        # location as written (normalized)
        self.loc = loc          # after -vN resolution
        self.seed = seed        # Seed or None
        self.status = status    # "ok" | "failed" | "notfound"
        self.failed_line = failed_line
        self.error = error      # the gh error text of a failed load


class Reader:
    def __init__(self, root):
        self.root = root
        self._self_repo = _UNSET
        self._lists = {}
        self._loaded = {}
        self._reported = set()
        self._raw_cache = {}
        self.invalid_incoming = set()

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

    def raw(self, loc, commit=None):
        """Read an exact file, optionally at a historical commit; never list or redirect."""
        cache_key = (loc,commit)
        if cache_key in self._raw_cache:
            return self._raw_cache[cache_key]
        repo,path = loc
        if repo is None:
            if commit:
                if _run_git(self.root,"cat-file","-t",commit) != "commit":
                    result = (None,"historical commit unavailable or not a commit object")
                else:
                    value = _run_git(self.root,"show",f"{commit}:{path}")
                    result = (value,None) if value is not None else (None,"historical source unavailable")
            else:
                try:
                    result = (Path(self.root,path).read_text(encoding="utf-8"),None)
                except (OSError,UnicodeError):
                    result = (None,"file not found or unreadable")
        else:
            endpoint = self._endpoint(repo,path)
            if commit:
                obj,err = self._gh_api(f"repos/{repo}/git/commits/{commit}")
                if err or not isinstance(obj,dict) or obj.get("sha") != commit.lower():
                    result = (None,err or "historical commit unavailable or not a commit object")
                    self._raw_cache[cache_key] = result
                    return result
                endpoint += "?ref=" + quote(commit,safe="")
            data,err = self._gh_api(endpoint)
            try:
                if not err and isinstance(data,dict) and data.get("encoding") == "base64":
                    result = (base64.b64decode(data.get("content","")).decode("utf-8"),None)
                else:
                    result = (None,err or "response had no base64 content")
            except (ValueError,UnicodeError):
                result = (None,"content was not valid base64 UTF-8")
        self._raw_cache[cache_key] = result
        return result

    def resolve(self, loc, exact=False):
        """v2/lifecycle targets pin exact files; only legacy targets resolve latest."""
        if exact:
            return loc,None
        raw,_ = self.raw(loc)
        if raw is not None:
            sd = parse_seed(raw)
            if sd.lifecycle is not None or sd.relations_version is not None or sd.format_errors:
                return loc,None
        repo,path = loc
        names,err = self._list_dir(repo,posixpath.dirname(path))
        return (loc,err) if err else ((repo,pick_latest(names,path)),None)

    def resolve_quiet(self, loc, exact=False):
        return self.resolve(loc,exact)[0]

    def load(self, loc, exact=False):
        cache_key = (loc,exact)
        if cache_key in self._loaded:
            return self._loaded[cache_key]
        rloc,err = self.resolve(loc,exact)
        raw = None
        if not err:
            raw,err = self.raw(rloc)
        if raw is None:
            status = "failed" if rloc[0] is not None or err != "file not found or unreadable" else "notfound"
            res = Loaded(loc,rloc,None,status,self._fail_line(loc,err),err)
        else:
            res = Loaded(loc,rloc,parse_seed(raw),"ok")
        if res.seed is not None:
            res.seed.location = rloc
        self._loaded[cache_key] = res
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


def exact_edges(seed):
    return seed.relations_version == 2 or seed.lifecycle is not None


def lifecycle_summary(seed):
    lc = seed.lifecycle if seed and isinstance(seed.lifecycle,dict) else {}
    return {"state":lc.get("state","unknown"), "outcome":lc.get("outcome"),
            "reason":lc.get("reason")}


def validate_provenance(rd, seed, ctx_repo):
    errors = []
    rows = seed.relations_data.get("provenance",[])
    if not isinstance(rows,list):
        return errors  # structural validator names the malformed shape
    for row in rows:
        if not isinstance(row,dict) or not lifecycle.path(row.get("seed")) or not isinstance(row.get("commit"),str) or not lifecycle.SHA.fullmatch(row["commit"]):
            continue
        loc = rd.norm(row["seed"],ctx_repo)
        raw,err = rd.raw(loc,row["commit"])
        if raw is None:
            errors.append(f"provenance historical source unavailable: {key(loc)}@{row['commit']} ({err})")
            continue
        source = parse_seed(raw)
        ids = row.get("items",[])
        if isinstance(ids,list) and all(isinstance(i,str) for i in ids):
            missing = set(ids)-set(source.item_map)
            if missing:
                errors.append("provenance historical source lacks items: " + ", ".join(sorted(missing)))
        if source.format_errors or source.duplicate_ids:
            errors.append("provenance historical source malformed: " + key(loc))
    return errors


def wholly_withdrawn(seed):
    lc = lifecycle_summary(seed)
    return (lc["state"] == "closed" and lc["outcome"] == "discontinued" and
            bool(seed.item_map) and
            {r["id"] for r in seed.lifecycle.get("withdrawn",[])} == set(seed.item_map))


def eligibility(rd, seed, ctx_repo=None, trail=None):
    """Deterministic candidate gate; excluded items are never evidence of fulfillment."""
    def result(eligible,reason,excluded=(),review=False):
        return {"eligible":eligible,"reason":reason,"excluded_items":sorted(set(excluded)),
                "review_required":review}
    if seed is None:
        return result(False,"Seed unavailable",review=True)
    if getattr(seed,"location",None) in rd.invalid_incoming:
        return result(False,"incoming child relation invalid",seed.item_map,True)
    errors = lifecycle.validate(seed,rd.root if ctx_repo is None else None)
    errors += validate_provenance(rd,seed,ctx_repo)
    if errors:
        return result(False,"invalid lifecycle",review=True)
    lc = lifecycle_summary(seed)
    inactive = lc["state"] != "active"
    if inactive:
        reason = "closed: " + str(lc["outcome"]) if lc["state"] == "closed" else "unknown lifecycle" if lc["state"] == "unknown" else lc["state"]
        # Finished Seeds stay history; paused/unknown ones get the same parent checks before any resume.
        if lc["state"] == "closed" or not seed.parent:
            return result(False,reason)
    own = set(seed.item_map)
    excluded = {r["id"] for r in (seed.lifecycle or {}).get("withdrawn",[])}
    if seed.parent:
        loc = rd.norm(seed.parent,ctx_repo)
        trail = set(trail or ())
        if loc in trail:
            return result(False,"parent cycle",own,True)
        trail.add(loc)
        parent = rd.load(loc,exact_edges(seed))
        if parent.seed is None:
            return result(False,"parent unavailable",own,True)
        ps = parent.seed
        # Backlink resolution expands the parent's children; an inactive child is not a candidate to vouch for.
        if hasattr(seed,"location") and not inactive:
            back = {rd.resolve_quiet(rd.norm(c,parent.loc[0]),exact_edges(ps)) for c in ps.children}
            if seed.location not in back:
                return result(False,"parent backlink missing",own,True)
        pe = lifecycle.validate(ps,rd.root if parent.loc[0] is None else None)
        if pe or validate_provenance(rd,ps,parent.loc[0]):
            return result(False,"parent lifecycle invalid",own,True)
        pl = lifecycle_summary(ps)
        if wholly_withdrawn(ps):
            return result(False,"parent discontinued; child review required",own,True)
        withdrawn = {r["id"] for r in (ps.lifecycle or {}).get("withdrawn",[])}
        # A legacy/unknown parent cannot substantiate a child's automatic candidacy.
        if pl["state"] == "unknown" and not inactive:
            return result(False,"parent lifecycle unknown",own,True)
        if not seed.refines and withdrawn:
            return result(False,"withdrawn parent items need mapping",own,True)
        if set(seed.refines)-set(ps.item_map):
            return result(False,"parent mapping invalid",own,True)
        impacted = withdrawn & set(seed.refines)
        if impacted:
            maps = {r["parent_item"]:r["child_items"] for r in seed.relations_data.get("refines_map",[])}
            if impacted-set(maps):
                return result(False,"withdrawn parent items need mapping",own,True)
            excluded.update(i for rid in impacted for i in maps[rid])
        # Ancestor withdrawal holds propagate through item mappings without pruning traversal.
        if pl["state"] == "active":
            gate = eligibility(rd,ps,parent.loc[0],trail)
            if gate["review_required"]:
                return result(False,"ancestor review required",own,True)
            if gate["excluded_items"]:
                impacted = set(gate["excluded_items"]) & set(seed.refines)
                if not gate["excluded_items"] or not seed.refines:
                    return result(False,"ancestor review required",own,True)
                maps = {r["parent_item"]:r["child_items"] for r in seed.relations_data.get("refines_map",[])}
                if impacted-set(maps):
                    return result(False,"withdrawn parent items need mapping",own,True)
                excluded.update(i for rid in impacted for i in maps[rid])
    mapped_hold = bool(excluded - {r["id"] for r in (seed.lifecycle or {}).get("withdrawn",[])})
    if inactive:
        return result(False,reason,excluded,mapped_hold)
    return result(bool(own-excluded),"mapped parent items withdrawn" if mapped_hold else "withdrawn items" if excluded else "active",excluded,False)


# ---------------------------------------------------------------------------
# tree
# ---------------------------------------------------------------------------

def cmd_tree(rd, rel, seed):
    out = [_row("SEED", f"{rel}  (target: {seed.target or '(none)'})")]
    self_res = rd.resolve_quiet((None, rel), seed.relations_version == 2 or seed.lifecycle is not None)
    out += _newer_note(rel, self_res)
    out.append(_row("SOURCE", seed.source or UNRECORDED))
    out.append(_row("TRACKING", ", ".join(seed.tracking) or "(없음)"))

    parent = None
    if seed.parent:
        ploc = rd.norm(seed.parent, None)
        parent = rd.load(ploc, exact_edges(seed))
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
            out.append(_row("REFINES", f"{rid} · [no parent]"))
            continue
        if parent.seed is None:
            note = "[parent unreadable]"
        elif rid in parent.seed.item_map:
            note = _short(parent.seed.item_map[rid])
        else:
            note = "[missing in parent]"
        out.append(_row("REFINES", f"{qualified_id(key(parent.loc), rid)} · {note}"))

    if seed.parent:
        if seed.link_reason:
            out.append(_row("LINK", _short(seed.link_reason)))
        elif not seed.refines:
            out.append(_row("LINK", "(기록 없음 — 미확인; 대응 부모 항목도 비어 있음)"))
        else:
            out.append(_row("LINK", UNRECORDED))

    # Family = the parent's children (resolved) — used for siblings and for who refines what.
    family = []  # [(resolved loc, display, Loaded)]
    seen = set()
    if parent is not None and parent.seed is not None:
        for c in parent.seed.children:
            ld = rd.load(rd.norm(c, parent.loc[0]), exact_edges(parent.seed))
            if ld.loc in seen:
                continue
            seen.add(ld.loc)
            family.append(ld)
    siblings = [ld for ld in family if ld.loc != self_res]
    listed = {ld.loc for ld in siblings} | {self_res}
    for d in seed.depends_on:
        ld = rd.load(rd.norm(d, None), exact_edges(seed))
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
            dres = rd.resolve_quiet(dloc, exact_edges(ld.seed)) if dloc[0] is None else dloc
            note = ("same repo — next-goal judges whether it is finished" if dres[0] is None
                    else "다른 레포 — 확인 못 함")
            out.append(_row("SIBLING", f"{disp(ld.orig, ld.loc)}  requires {disp(dloc, dres)} ({note})"))

    kids, kid_seen = [], set()  # the named Seed's children, deduplicated by resolved location
    for c in seed.children:
        ld = rd.load(rd.norm(c, None), exact_edges(seed))
        line = _row("CHILD", disp(ld.orig, ld.loc))
        if ld.status == "notfound":
            line += "  [file not found]"
        elif ld.seed is not None:
            line += ("  refines: " + (", ".join(qualified_id(rel, r) for r in ld.seed.refines)
                                          or "(none)"))
        out.append(line)
        out += rd.failure_lines(ld)
        if ld.loc not in kid_seen:
            kid_seen.add(ld.loc)
            kids.append(ld)

    if kids:  # the parent-side view: each of this Seed's items -> the child Seeds that refine it
        readable = [ld for ld in kids if ld.seed is not None]
        for iid, desc in seed.items:
            who = [ld for ld in readable if iid in ld.seed.refines]
            mark = LINK_ONLY if any(ld.loc[0] is not None for ld in who) else ""
            out.append(_row("ITEM", f"{qualified_id(rel, iid)} · {_short(desc)}  refined by: "
                            f"{', '.join(key(ld.loc) for ld in who) if who else '(none)'}{mark}"))
        for ld in kids:
            if ld.seed is None:
                out.append(_row("ITEM", f"(unreadable child {key(ld.loc)} — 대응 미확인)"))

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
            out.append(_row("PARENT-ITEM", f"{qualified_id(key(parent.loc), iid)} · {_short(desc)}  refined by: "
                            f"{', '.join(who) if who else '(none)'}{mark}"))
    return out, 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def cmd_check(rd, rel, seed):
    mismatches = 0
    failed = 0
    edges = 0
    self_res = rd.resolve_quiet((None, rel), seed.relations_version == 2 or seed.lifecycle is not None)
    out = _newer_note(rel, self_res)
    legacy_lines, legacy_seen = [], set()

    def mismatch(text):
        nonlocal mismatches
        mismatches += 1
        out.append(_row("MISMATCH", text))

    def note_legacy(loc, sd):
        """Informational only: a Seed that still carries c<N>/ac<N> ids (never a mismatch)."""
        ids = legacy_ids(sd)
        if not ids or loc in legacy_seen:
            return
        legacy_seen.add(loc)
        if loc[0] is None:
            how = f"run: seed-id-migrate.py {loc[1]}"
        else:
            how = f"migrate it in that repo (seed-id-migrate.py {loc[1]})"
        legacy_lines.append(_row("LEGACY", f"{key(loc)} still uses legacy item ids "
                                           f"{', '.join(ids)} — {how}"))

    def dup_mismatch(name, sd):
        for iid in sd.duplicate_ids:
            mismatch(f"{name} defines item id {iid} more than once")

    # Unrecorded values are reported, never guessed, and are not mismatches (exit code unchanged).
    if seed.parent and seed.link_reason is None:
        out.append(_row("UNRECORDED", f"{rel} link_reason is not recorded (미확인 — 추측해 채우지 않음)"))
    if seed.source is None:
        out.append(_row("UNRECORDED", f"{rel} issues.source is not recorded"))
    note_legacy((None, rel), seed)
    dup_mismatch(rel, seed)
    out.append(_row("LIFECYCLE", json.dumps(lifecycle_summary(seed),ensure_ascii=False)))
    out.append(_row("ELIGIBILITY", json.dumps(eligibility(rd,seed),ensure_ascii=False)))
    for error in lifecycle.validate(seed,rd.root) + validate_provenance(rd,seed,None):
        if error != "item IDs must be unique":
            mismatch(error)

    def fail(ld):
        nonlocal failed
        failed += 1
        out.extend(rd.failure_lines(ld))

    if seed.parent:
        parent = rd.load(rd.norm(seed.parent, None), exact_edges(seed))
        pname = key(parent.loc)
        if parent.status == "failed":
            fail(parent)
        elif parent.status == "notfound":
            edges += 1
            mismatch(f"{rel} parent {key(parent.orig)} does not exist")
        else:
            edges += 1
            note_legacy(parent.loc, parent.seed)
            dup_mismatch(pname, parent.seed)
            for error in lifecycle.validate(parent.seed,rd.root if parent.loc[0] is None else None):
                mismatch(pname + ": " + error)
            kids = {rd.resolve_quiet(rd.norm(c, parent.loc[0]), exact_edges(parent.seed)) for c in parent.seed.children}
            if self_res not in kids:
                if parent.loc[0] is None:
                    mismatch(f"{pname} children is missing {rel}")
                else:
                    self_name = f"{rd.self_repo}:{rel}" if rd.self_repo else rel
                    mismatch(f"{pname} children is missing {self_name} — 부모 레포에서 추가 필요")
            for rid in seed.refines:
                edges += 1
                if rid not in parent.seed.item_map:
                    text = f"{rel} refines {rid}, which {pname} does not define"
                    alt = other_id_form(rid, parent.seed.item_map)
                    if alt:
                        where = parent.loc[1] + (f" (in {parent.loc[0]})" if parent.loc[0] else "")
                        text += (f" — {pname} has {alt}: the id form differs, "
                                 f"run seed-id-migrate.py {where}")
                    mismatch(text)

    for c in seed.children:
        child = rd.load(rd.norm(c, None), exact_edges(seed))
        if child.status == "failed":
            fail(child)
            continue
        edges += 1
        if child.status == "notfound":
            mismatch(f"{rel} children names {key(child.orig)}, which does not exist")
            continue
        note_legacy(child.loc, child.seed)
        dup_mismatch(key(child.loc), child.seed)
        for error in lifecycle.validate(child.seed,rd.root if child.loc[0] is None else None):
            mismatch(key(child.loc) + ": " + error)
        back = child.seed.parent
        back_res = rd.resolve_quiet(rd.norm(back, child.loc[0]), exact_edges(child.seed)) if back else None
        if back_res != self_res:
            mismatch(f"{key(child.loc)} parent does not point back to {rel}")
        else:
            for rid in child.seed.refines:
                if rid not in seed.item_map:
                    mismatch(f"{key(child.loc)} refines {rid}, which {rel} does not define")

    # New relationship kinds are read exactly; provenance has its own historical loader.
    for edge in (("depends_on","replaces","transfers") if exact_edges(seed) else ()):
        entries = seed.relations_data.get(edge,[])
        if not isinstance(entries,list):
            continue
        for entry in entries:
            target = entry.get("seed") if isinstance(entry,dict) else entry
            if not lifecycle.path(target):
                continue
            ld = rd.load(rd.norm(target,None),exact_edges(seed) or edge != "depends_on")
            edges += 1
            if ld.status == "failed":
                fail(ld)
            elif ld.seed is None:
                mismatch(f"{rel} {edge} names {key(ld.orig)}, which does not exist")
            else:
                for error in lifecycle.validate(ld.seed,rd.root if ld.loc[0] is None else None):
                    mismatch(key(ld.loc) + ": " + error)
                if edge == "transfers":
                    for error in validate_provenance(rd,ld.seed,ld.loc[0]):
                        mismatch(key(ld.loc) + ": " + error)
                    provenance = ld.seed.relations_data.get("provenance",[])
                    covered = set()
                    for row in provenance if isinstance(provenance,list) else []:
                        if isinstance(row,dict) and lifecycle.path(row.get("seed")) and isinstance(row.get("items"),list) and all(isinstance(i,str) for i in row["items"]):
                            if rd.norm(row["seed"],ld.loc[0]) == (None,rel) and isinstance(row.get("commit"),str) and lifecycle.SHA.fullmatch(row["commit"]):
                                covered.update(row["items"])
                    transferred = entry.get("items",[]) if isinstance(entry,dict) else []
                    if isinstance(transferred,list) and all(isinstance(i,str) for i in transferred) and set(transferred)-covered:
                        mismatch(f"{key(ld.loc)} transfer destination lacks pinned provenance for {rel} selected items")
                elif edge == "replaces":
                    provenance = seed.relations_data.get("provenance",[])
                    matches = [row for row in provenance if isinstance(row,dict) and lifecycle.path(row.get("seed")) and rd.norm(row["seed"],None) == ld.loc] if isinstance(provenance,list) else []
                    if not matches:
                        mismatch(f"{rel} replaces {key(ld.loc)} without pinned provenance")

    out.extend(legacy_lines)
    if mismatches:
        out.append(f"FOUND: {mismatches} mismatch(es)")
        return out, 1
    out.append(f"OK: {edges} edge(s) consistent")
    return out, 2 if failed else 0


# ---------------------------------------------------------------------------
# walk
# ---------------------------------------------------------------------------

# Which edges a node of each relation kind follows, and the kind a followed target gets.
WALK_EDGES = {
    "start": ("parent", "children", "depends_on"),
    # An ancestor's own predecessors too: its items are candidates, and an unfinished
    # predecessor is what holds them.
    "ancestor": ("parent", "children", "depends_on"),
    "descendant": ("children", "depends_on"),
    "ancestor-child": ("depends_on",),
    "predecessor": ("depends_on",),
}
WALK_NEXT = {
    ("start", "parent"): "ancestor", ("start", "children"): "descendant",
    ("start", "depends_on"): "predecessor",
    ("ancestor", "parent"): "ancestor", ("ancestor", "children"): "ancestor-child",
    ("ancestor", "depends_on"): "predecessor",
    ("descendant", "children"): "descendant", ("descendant", "depends_on"): "predecessor",
    ("ancestor-child", "depends_on"): "predecessor",
    ("predecessor", "depends_on"): "predecessor",
}


class _Node:
    def __init__(self, key_, loc, depth, relation, via, path, status, seed, came_from=None):
        self.key = key_
        self.loc = loc              # identity: the resolved location
        self.depth = depth
        self.relation = relation
        self.via = via              # [[edge, key], ...] from the start
        self.path = path            # identities from the start to this node, inclusive
        self.status = status        # ok | external | external-failed | notfound
        self.seed = seed
        self.came_from = came_from  # identity of the node this one was reached from
        self.error = None
        self.sha = None
        self.expanded = set(WALK_EDGES[relation])  # edges queued for expansion from this node
        self.todo = None            # a re-expansion shadow: only these edges are followed


def _sha8(raw):
    return hashlib.sha256(raw).hexdigest()[:8]


def _edge_texts(seed, edge):
    if edge == "parent":
        return [seed.parent] if seed.parent else []
    return list(getattr(seed, edge))


def walk(seed_file, max_depth=3, max_nodes=25):
    """Bounded breadth-first walk from the named Seed -> the data every output format renders."""
    root = find_root(seed_file)
    rel = posixpath.normpath(
        os.path.relpath(os.path.realpath(seed_file), root).replace(os.sep, "/"))
    with open(seed_file, "rb") as f:
        raw = f.read()
    rd = Reader(root)
    seed = parse_seed(raw.decode("utf-8"))
    self_res = rd.resolve_quiet((None, rel), exact_edges(seed))
    start = _Node(rel, self_res, 0, "start", [], [self_res], "ok", parse_seed(raw.decode("utf-8")))
    start.seed.location = (None,rel)
    start.sha = _sha8(raw)
    nodes = [start]
    by_loc = {self_res: start}
    by_orig = {(None, rel): start}
    dups, cycles, stops, seen = [], [], [], set()
    work = [start]  # expansion queue: nodes, plus re-expansions of a node found by another route

    def record(bucket, rec):
        ident = (id(bucket),) + tuple(rec.values())
        if ident not in seen:
            seen.add(ident)
            bucket.append(rec)

    def seen_target(src, edge, tgt):
        # A cycle is a loop of one edge kind: the target sits on the run of same-kind steps that
        # ended at this node (A depends_on B depends_on A; a parent chain that comes back). A
        # sibling depending on the start closes no such run — it is an ordinary edge to a Seed
        # already listed, so a duplicate.
        i = len(src.via)
        while i > 0 and src.via[i - 1][0] == edge:
            i -= 1
        bucket = cycles if tgt.loc in src.path[i:] else dups
        record(bucket, {"from": src.key, "edge": edge, "to": tgt.key})

    def stop(src, edge, nloc, reason):
        record(stops, {"from": src.key, "edge": edge, "target": key(nloc), "reason": reason})

    def reexpand(src, edge, tgt):
        # A Seed found again by a different route keeps its first relation/via/depth in the
        # output (the shortest, first-seen path), but the new route may allow edges the first
        # one did not (a `predecessor` only follows depends_on; as a `descendant` it also
        # follows children). Those edges are followed once, from a shadow of the node carrying
        # the new route's relation, depth and path, so depth/node caps and cycle checks hold
        # for that route. Each (node, edge) is expanded at most once, so this stays bounded.
        if tgt.status != "ok" or src.depth + 1 > max_depth:
            return
        rel_ = WALK_NEXT[(src.relation, edge)]
        extra = [e for e in WALK_EDGES[rel_] if e not in tgt.expanded]
        if not extra:
            return
        tgt.expanded.update(extra)
        shadow = _Node(tgt.key, tgt.loc, src.depth + 1, rel_, src.via + [[edge, tgt.key]],
                       src.path + [tgt.loc], tgt.status, tgt.seed, src.loc)
        shadow.todo = extra
        work.append(shadow)

    def follow(src, edge, text):
        nloc = rd.norm(text, src.loc[0])
        rloc = rd.resolve_quiet(nloc, exact_edges(src.seed)) if nloc[0] is None else None
        if rloc is not None and src.relation == "ancestor" and edge == "children" \
                and rloc == src.came_from:
            return  # the node we came up from is not its own sibling
        tgt = by_orig.get(nloc)
        if tgt is None and rloc is not None:
            tgt = by_loc.get(rloc)
        if tgt is not None:
            seen_target(src, edge, tgt)
            reexpand(src, edge, tgt)
            return
        if src.depth + 1 > max_depth:
            stop(src, edge, nloc, "depth")
            return
        if len(nodes) >= max_nodes:
            stop(src, edge, nloc, "nodes")
            return
        ld = rd.load(nloc, exact_edges(src.seed))
        tgt = by_loc.get(ld.loc)
        if tgt is not None:
            by_orig[nloc] = tgt
            seen_target(src, edge, tgt)
            reexpand(src, edge, tgt)
            return
        external = ld.loc[0] is not None
        if ld.status == "failed":
            status = "external-failed"
        elif ld.status == "notfound":
            status = "notfound"
        else:
            status = "external" if external else "ok"
        k = key(ld.loc)
        node = _Node(k, ld.loc, src.depth + 1, WALK_NEXT[(src.relation, edge)],
                     src.via + [[edge, k]], src.path + [ld.loc], status, ld.seed, src.loc)
        node.error = ld.error
        if status == "ok":
            try:
                with open(os.path.join(root, ld.loc[1]), "rb") as f:
                    node.sha = _sha8(f.read())
            except OSError:
                pass
        nodes.append(node)
        work.append(node)
        by_loc[ld.loc] = node
        by_orig[nloc] = node

    i = 0
    while i < len(work):
        src = work[i]
        i += 1
        if src.status != "ok":
            continue  # notfound / other-repo nodes are never expanded
        for edge in (src.todo or WALK_EDGES[src.relation]):
            for text in _edge_texts(src.seed, edge):
                follow(src, edge, text)

    def child_locs(n):
        out, got = [], set()
        for c in n.seed.children:
            nloc = rd.norm(c, n.loc[0])
            loc = rd.resolve_quiet(nloc, exact_edges(n.seed)) if nloc[0] is None else nloc
            if loc not in got:
                got.add(loc)
                out.append(loc)
        return out

    # Determine incoming-edge holds before evaluating any node, so recursive parent
    # eligibility sees them too. Traversal order must not let grandchildren escape a hold.
    for n in nodes:
        s = n.seed
        # Incoming children edges can be malformed even when the child's own parent is null
        # or points elsewhere. Check every visited source, including duplicate routes.
        if s is not None:
            for owner in nodes:
                if owner.seed is None:
                    continue
                linked = []
                for c in owner.seed.children:
                    loc = rd.norm(c,owner.loc[0])
                    if loc[0] is None:
                        loc = rd.resolve_quiet(loc,exact_edges(owner.seed))
                    elif loc in by_orig:
                        loc = by_orig[loc].loc
                    linked.append(loc)
                if n.loc in linked:
                    back = rd.resolve_quiet(rd.norm(s.parent,n.loc[0]),exact_edges(s)) if s.parent else None
                    if back != owner.loc:
                        rd.invalid_incoming.add(n.loc)
                        break
    node_dicts, items = [], []
    for n in nodes:
        s = n.seed
        kids = child_locs(n) if s is not None else []
        gate = eligibility(rd,s,n.loc[0])
        node_dicts.append({
            "key": n.key, "depth": n.depth, "relation": n.relation, "status": n.status,
            "via": n.via,
            "target": s.target if s else None,
            "parent": s.parent if s else None,
            "refines": list(s.refines) if s else [],
            "link_reason": s.link_reason if s else None,
            "source": s.source if s else None,
            "tracking": list(s.tracking) if s else [],
            "items": [iid for iid, _ in s.items] if s else [],
            # Descriptions ride along so a consumer can show `<slug>/<id> · <description>`
            # without re-reading the Seed (identifiers.md).
            "item_desc": {iid: desc for iid, desc in s.items} if s and lifecycle_summary(s)["state"] == "active" else {},
            "lifecycle": lifecycle_summary(s),
            "eligibility": gate,
            "refines_map": s.relations_data.get("refines_map",[]) if s else [],
            "provenance": s.relations_data.get("provenance",[]) if s else [],
            "replaces": s.relations_data.get("replaces",[]) if s else [],
            "transfers": s.relations_data.get("transfers",[]) if s else [],
            "children": [key(loc) for loc in kids],
        })
        visited = [by_loc[loc] for loc in kids if loc in by_loc and by_loc[loc].seed is not None]
        if visited:  # every item of a Seed with a visited child, so unmapped items stay visible
            for iid, _ in s.items:
                items.append({"owner": n.key, "id": iid,
                              "refined_by": [v.key for v in visited if iid in v.seed.refines]})

    failures = [{"key": n.key, "error": n.error or ""} for n in nodes
                if n.status == "external-failed"]
    summary = {
        "visited": len(nodes), "stopped": len(stops), "failed": len(failures),
        "cycles": len(cycles),
        "external": sum(1 for n in nodes if n.status in ("external", "external-failed")),
        "notfound": sum(1 for n in nodes if n.status == "notfound"),
    }
    prints = sorted(f"{n.key}:{n.sha}" for n in nodes if n.status == "ok" and n.sha)
    fingerprint = hashlib.sha256("\n".join(prints).encode("utf-8")).hexdigest()[:12]
    head = _run_git(root, "rev-parse", "HEAD")
    # The id moves with HEAD, the start file and every visited Seed (via the fingerprint), so a
    # judgment made on an earlier walk is recognisably stale whichever Seed changed.
    # The limits ride in the id too, so a consumer re-walking it uses the same bounds.
    walk_id = (f"{rd.self_repo or 'local'}@{head[:12] if head else 'nohead'}:{rel}"
               f"#{start.sha}.{fingerprint[:8]}~d{max_depth}n{max_nodes}")
    return {
        "walk": {"id": walk_id, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "start": rel, "max_depth": max_depth, "max_nodes": max_nodes,
                 "fingerprint": fingerprint},
        "nodes": node_dicts, "items": items, "dups": dups, "cycles": cycles, "stops": stops,
        "failures": failures, "summary": summary,
    }


def _clean(text):
    """One tab-free, single-line value."""
    return str(text).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def render_walk_text(data):
    w = data["walk"]
    out = ["\t".join(["WALK", f"id={_clean(w['id'])}", f"at={w['at']}", f"start={_clean(w['start'])}",
                      f"max_depth={w['max_depth']}", f"max_nodes={w['max_nodes']}",
                      f"fingerprint={w['fingerprint']}"])]

    def csv(vals):
        return _clean(",".join(vals)) if vals else "-"

    for n in data["nodes"]:
        loaded = n["status"] in ("ok", "external")
        via = ">".join(part for step in n["via"] for part in step) or "-"
        out.append("\t".join([
            "NODE", str(n["depth"]), n["relation"], _clean(n["key"]), n["status"],
            f"via={_clean(via)}",
            f"target={_short(_clean(n['target'])) if n['target'] else '-'}",
            f"refines={csv(n['refines'])}",
            # A root has nothing to link to, so only a node with a parent can lack a reason.
            "link_reason=" + (_short(_clean(n["link_reason"])) if n["link_reason"]
                              else ("미확인" if loaded and n["parent"] else "-")),
            "source=" + (_clean(n["source"]) if n["source"] else ("미확인" if loaded else "-")),
            f"tracking={csv(n['tracking'])}", f"items={csv(n['items'])}",
            f"children={csv(n['children'])}",
            "lifecycle_state="+_clean(n["lifecycle"]["state"]),
            "lifecycle_outcome="+_clean(n["lifecycle"]["outcome"] or "-"),
            "lifecycle_reason="+_clean(n["lifecycle"]["reason"] or "-"),
            "eligible="+str(n["eligibility"]["eligible"]).lower(),
            "eligibility_reason="+_clean(n["eligibility"]["reason"]),
            "excluded_items="+csv(n["eligibility"]["excluded_items"]),
            "review_required="+str(n["eligibility"]["review_required"]).lower()]))
    for it in data["items"]:
        refined = csv(it["refined_by"]) if it["refined_by"] else "(none)"
        out.append("\t".join(["ITEM", _clean(it["owner"]), _clean(it["id"]),
                              f"refined_by={refined}"]))
    for tag, rows in (("DUP", data["dups"]), ("CYCLE", data["cycles"])):
        for r in rows:
            out.append("\t".join([tag, _clean(r["from"]), r["edge"], _clean(r["to"])]))
    for r in data["stops"]:
        out.append("\t".join(["STOP", _clean(r["from"]), r["edge"], _clean(r["target"]),
                              f"reason={r['reason']}"]))
    for r in data["failures"]:
        out.append("\t".join(["FAILED", _clean(r["key"]), _clean(r["error"])]))
    sm = data["summary"]
    out.append("\t".join(["SUMMARY"] + [f"{k}={sm[k]}" for k in
                                        ("visited", "stopped", "failed", "cycles", "external",
                                         "notfound")]))
    return out


def _parse_walk_args(args):
    """`[--max-depth N] [--max-nodes N] [--json]` -> (depth, nodes, as_json), or None if invalid."""
    depth, nodes, as_json = 3, 25, False
    i = 0
    while i < len(args):
        a = args[i]
        i += 1
        if a == "--json":
            as_json = True
        elif a.split("=", 1)[0] in ("--max-depth", "--max-nodes"):
            name, eq, val = a.partition("=")
            if not eq:
                if i >= len(args):
                    return None
                val = args[i]
                i += 1
            try:
                n = int(val)
            except ValueError:
                return None
            if n < 1:
                return None
            if name == "--max-depth":
                depth = n
            else:
                nodes = n
        else:
            return None
    return depth, nodes, as_json


# ---------------------------------------------------------------------------

def main(argv):
    if len(argv) < 3 or argv[1] not in ("tree", "check", "walk", "metadata", "read") or argv[2].startswith("--"):
        print(USAGE, file=sys.stderr)
        return 2
    cmd, seed_file = argv[1], argv[2]
    opts = None
    if cmd == "walk":
        opts = _parse_walk_args(argv[3:])
        if opts is None:
            print(USAGE + "\n(--max-depth and --max-nodes take an integer >= 1)", file=sys.stderr)
            return 2
    elif len(argv) != 3 and not (cmd in ("metadata","read") and argv[3:] == ["--json"]):
        print(USAGE, file=sys.stderr)
        return 2
    if not os.path.isfile(seed_file):
        print(f"seed-relations: not a file: {seed_file}", file=sys.stderr)
        return 2
    if cmd == "walk":
        data = walk(seed_file, opts[0], opts[1])
        if opts[2]:
            print(json.dumps(data, ensure_ascii=False))
        else:
            print("\n".join(render_walk_text(data)))
        return 0
    root = find_root(seed_file)
    rel = posixpath.normpath(
        os.path.relpath(os.path.realpath(seed_file), root).replace(os.sep, "/"))
    with open(seed_file, encoding="utf-8") as f:
        seed = parse_seed(f.read())
    rd = Reader(root)
    seed.location = (None,rel)
    if cmd in ("metadata","read"):
        data = {"path":rel,"title":seed.title,"goal":seed.short_goal,
                "lifecycle":lifecycle_summary(seed),"reason":lifecycle_summary(seed)["reason"],
                "eligibility":eligibility(rd,seed)}
        if cmd == "read":
            data["requirements"] = seed.requirements or {i:{"id":i,"description":d} for i,d in seed.items}
        print(json.dumps(data,ensure_ascii=False))
        return 1 if seed.format_errors else 0
    lines, code = (cmd_tree if cmd == "tree" else cmd_check)(rd, rel, seed)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
