#!/usr/bin/env python3
"""
vault-commit-message.py — status-transition-aware commit message generator for /vault-commit.

Interface:
  First CLI arg: vault_root (path to vault)
  Stdin: lines of `git diff --cached --name-status` (tab-separated)
  Stdout: a single suggested commit message string

Exit codes:
  0 — success (always, even on fallback)
"""

import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FIELD_RE = re.compile(r"^([a-z_]+):\s*(.+)$", re.MULTILINE)


def _extract_frontmatter_field(content: str, field: str) -> str | None:
    """Return the value of a frontmatter field, or None if absent."""
    m = _FM_RE.match(content)
    if not m:
        return None
    fm_block = m.group(1)
    for line in fm_block.splitlines():
        kv = re.match(r"^" + re.escape(field) + r":\s*(.+)$", line.strip())
        if kv:
            return kv.group(1).strip().strip('"').strip("'")
    return None


def _read_file_safe(path: Path) -> str | None:
    """Read a file, returning None on any error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _git_show(vault_root: str, rel_path: str) -> str | None:
    """Return HEAD content of a file in the vault git repo, or None on error."""
    try:
        result = subprocess.run(
            ["git", "-C", vault_root, "show", f"HEAD:{rel_path}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return None


# ---------------------------------------------------------------------------
# Per-file message generation
# ---------------------------------------------------------------------------

_IMPORTANCE = {
    "decision": 0,
    "plan": 1,
    "note": 2,
    "wiki": 3,
    "session": 4,
    "capture": 5,
    "vault": 6,
}


def _importance(msg: str) -> int:
    # Status transitions (archive) are highest priority within their type
    # — surface them as the title in multi-file commits.
    #
    # This literal is the same set as `_TRANSITION_SUBOPS`, which
    # `_synthesize` groups and ranks by. They stay separate because each needs a
    # distinct score here, not a membership test — so adding another transition
    # means editing both places. (`promote` was removed with the B-layer
    # promotion gate, v5 §5/§6, #480 — no path writes `status:` anymore.)
    if "(archive)" in msg:
        return -1
    for key, rank in _IMPORTANCE.items():
        if msg.startswith(f"{key}(") or msg.startswith(f"{key}:"):
            return rank
    return 99


def _stem(filename: str) -> str:
    """Return filename without extension."""
    p = Path(filename)
    return p.stem


def _msg_for_added(vault_root: str, rel_path: str) -> str:
    """Generate message for an added (A) file."""
    full_path = Path(vault_root) / rel_path
    content = _read_file_safe(full_path)
    if content is None:
        return f"vault: add {Path(rel_path).name}"

    ftype = _extract_frontmatter_field(content, "type")
    status = _extract_frontmatter_field(content, "status")
    stem = _stem(rel_path)

    if ftype == "decision":
        return f"decision(create): {stem}"
    elif ftype == "plan":
        return f"plan(create): {stem}"
    elif ftype == "note":
        if status in ("raw", "draft", None):
            return f"note(draft): {stem} (new)"
        elif status == "evergreen":
            return f"note(evergreen): {stem} (new)"
        else:
            return f"note(draft): {stem} (new)"
    elif ftype == "wiki":
        # v5 A layer — no status machine, so a wiki page has only create/update.
        return f"wiki(create): {stem}"
    elif ftype == "session":
        return f"session: {stem} (new)"
    elif ftype == "capture":
        return f"capture: {stem} (new)"
    return f"vault: add {Path(rel_path).name}"


def _type_prefix(new_type: str | None) -> str | None:
    """Map frontmatter type to commit message prefix.

    Returns None for types without a meaningful archive semantic
    (session/capture/unknown) — caller should fall back to a generic vault label.
    """
    if new_type in ("decision", "plan", "note"):
        return new_type
    return None


def _msg_for_modified(vault_root: str, rel_path: str) -> str:
    """Generate message for a modified (M) file."""
    full_path = Path(vault_root) / rel_path
    new_content = _read_file_safe(full_path)
    old_content = _git_show(vault_root, rel_path)

    stem = _stem(rel_path)

    # If new content is unreadable, fall back
    if new_content is None:
        return f"vault: update {Path(rel_path).name}"

    new_type = _extract_frontmatter_field(new_content, "type")
    if new_type is None:
        return f"vault: update {Path(rel_path).name}"

    new_status = _extract_frontmatter_field(new_content, "status")
    old_status = _extract_frontmatter_field(old_content, "status") if old_content else None

    prefix = _type_prefix(new_type)

    # Status transitions only apply to types with archive semantics. Promotion
    # (raw→draft, draft→evergreen) was removed with the B-layer promotion gate
    # (v5 §5/§6, #480) — no path writes `status:` anymore, so a non-archival
    # status change (a manual hand-edit) falls through to a plain content update.
    if prefix is not None and new_status == "archived" and old_status != "archived":
        return f"{prefix}(archive): {stem}"

    # Content change without status change. `wiki` never reaches the transition
    # block above (`_type_prefix` returns None) because the A layer carries no
    # `status:` — it only ever lands here.
    if new_type in ("note", "decision", "plan", "wiki"):
        return f"{new_type}(update): {stem}"
    else:
        return f"vault: update {Path(rel_path).name}"


def _msg_for_deleted(rel_path: str) -> str:
    return f"vault: delete {Path(rel_path).name}"


def _msg_for_renamed(old_path: str, new_path: str) -> str:
    old_stem = _stem(old_path)
    new_stem = _stem(new_path)
    return f"vault: rename {old_stem} → {new_stem}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_diff_lines(lines: list[str], vault_root: str) -> list[tuple[str, str]]:
    """Parse `git diff --cached --name-status` lines into (op, message) records.

    `op` is carried alongside the message so `_synthesize` can group by what
    happened, not just by the message text it would otherwise have to re-parse.
    """
    records: list[tuple[str, str]] = []

    for line in lines:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0].strip()

        if status == "A":
            records.append(("add", _msg_for_added(vault_root, parts[1])))
        elif status == "M":
            records.append(("update", _msg_for_modified(vault_root, parts[1])))
        elif status == "D":
            records.append(("delete", _msg_for_deleted(parts[1])))
        elif (status.startswith("R") or status.startswith("C")) and len(parts) >= 3:
            records.append(("rename", _msg_for_renamed(parts[1], parts[2])))

    return records


def _kind(msg: str) -> str:
    """Leading type token of a per-file message ('wiki(create): x' -> 'wiki')."""
    return re.split(r"[(:]", msg, maxsplit=1)[0].strip()


# Status transitions, the sub-op `_importance` scores below every type.
# Cannot collide with a git-status op (add/update/delete/rename). (`promote`
# was removed with the B-layer promotion gate, v5 §5/§6, #480.)
_TRANSITION_SUBOPS = ("archive",)


def _subop(msg: str, op: str) -> str:
    """The sub-op a message groups under.

    An archive and an ordinary content edit are both git status `M`, so keying
    the group on the status letter alone put `note(archive): x` and
    `note(update): y` in one bucket — the transition then disappeared into a
    generic "note: update 2 files".

    Only archive is split out. `note(draft)` vs `note(evergreen)` on a
    new note is a status *value*, not a different operation, so both stay under
    the status letter; splitting them would fragment ordinary groups and undo
    the count-based titling this grouping exists for.

    Detected the same way `_importance` detects them — one convention for what
    marks a transition, so the two cannot drift apart.
    """
    for subop in _TRANSITION_SUBOPS:
        if f"({subop})" in msg:
            return subop
    return op


def _synthesize(records: list[tuple[str, str]]) -> str:
    """Synthesize per-file messages into a final commit message."""
    if not records:
        return "vault: update notes"

    sorted_msgs = sorted((msg for _, msg in records), key=_importance)

    if len(sorted_msgs) == 1:
        return sorted_msgs[0]

    # The title names the largest (kind, sub-op) group rather than the single
    # highest-importance file. Ranking by importance alone let one
    # `note(update)` title a commit of twenty wiki pages, because the title was
    # picked from a sort that never looked at how many files shared a kind.
    #
    # Four ranking levels, in order — all four are load-bearing, so a change
    # here needs the tie cases in test-vault-commit-message.py to stay green:
    #   1. a status transition present at all, since `_importance` scores
    #      archive below every type precisely to say "this outranks
    #      everything". Count-based titling was introduced to stop one
    #      *ordinary* file outranking twenty, not to demote a transition.
    #   2. file count, descending
    #   3. best _importance within the group — keeps a 1-decision + 1-note
    #      commit titled by the decision
    #   4. first appearance in `records`, since dicts preserve insertion order.
    #      `git diff --cached --name-status` emits paths sorted, so this is
    #      stable for a given staged set rather than arbitrary.
    #
    # Each group carries [count, best _importance, the message scoring it]. The
    # representative is tracked rather than re-derived from `sorted_msgs`: a
    # one-file winner must be titled by *its own* member. Today the global sort
    # happens to agree, but only because `_importance` puts archive
    # below every type — reorder that map and a global sort would title a
    # single-file winner with a losing group's message.
    groups: dict[tuple[str, str], list] = {}
    for op, msg in records:
        importance = _importance(msg)
        g = groups.setdefault((_kind(msg), _subop(msg, op)), [0, 99, msg])
        g[0] += 1
        if importance < g[1]:
            g[1], g[2] = importance, msg

    def _rank(item: tuple[tuple[str, str], list]) -> tuple[bool, int, int]:
        (_, subop_), (count_, best_, _rep) = item
        return (subop_ in _TRANSITION_SUBOPS, count_, -best_)

    (kind, subop), (count, _best, representative) = max(groups.items(), key=_rank)

    if count > 1:
        # Name the remainder too — a bare "wiki: add 20 files" on a 34-file
        # commit reads, in `git log --oneline`, as if the other 14 do not exist.
        rest = len(records) - count
        title = f"{kind}: {subop} {count} files" + (f" (+{rest} more)" if rest else "")
        body = sorted_msgs
    else:
        title = representative
        body = list(sorted_msgs)
        body.remove(representative)

    bullets = "\n".join(f"- {m}" for m in body)
    return f"{title}\n\n{bullets}"


def main() -> int:
    vault_root = sys.argv[1] if len(sys.argv) > 1 else "."
    stdin_lines = sys.stdin.readlines()
    records = _parse_diff_lines(stdin_lines, vault_root)
    print(_synthesize(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
