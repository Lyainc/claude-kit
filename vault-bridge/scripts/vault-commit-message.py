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
    "session": 3,
    "capture": 4,
    "vault": 5,
}


def _importance(msg: str) -> int:
    # Status transitions (promote/archive) are highest priority within their type
    # — surface them as the title in multi-file commits.
    if "(promote)" in msg:
        return -2  # higher than any type
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
    elif ftype == "session":
        return f"session: {stem} (new)"
    elif ftype == "capture":
        return f"capture: {stem} (new)"
    return f"vault: add {Path(rel_path).name}"


def _type_prefix(new_type: str | None) -> str:
    """Map frontmatter type to commit message prefix."""
    if new_type in ("decision", "plan", "note"):
        return new_type
    return "note"  # fallback for unknown types


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

    # Status transition detection
    if old_status is not None and new_status is not None and old_status != new_status:
        if new_status == "archived":
            return f"{prefix}(archive): {stem}"
        elif old_status == "raw" and new_status == "draft":
            return f"{prefix}(promote): {stem} {{raw→draft}}"
        elif old_status == "draft" and new_status == "evergreen":
            return f"{prefix}(promote): {stem} {{draft→evergreen}}"
        else:
            return f"{prefix}(promote): {stem} {{{old_status}→{new_status}}}"
    elif new_status == "archived" and old_status != "archived":
        return f"{prefix}(archive): {stem}"

    # Content change without status change
    if new_type in ("note", "decision", "plan"):
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

def _parse_diff_lines(lines: list[str], vault_root: str) -> list[str]:
    """Parse git diff --cached --name-status lines into per-file messages."""
    messages: list[str] = []

    for line in lines:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0].strip()

        if status == "A":
            messages.append(_msg_for_added(vault_root, parts[1]))
        elif status == "M":
            messages.append(_msg_for_modified(vault_root, parts[1]))
        elif status == "D":
            messages.append(_msg_for_deleted(parts[1]))
        elif (status.startswith("R") or status.startswith("C")) and len(parts) >= 3:
            messages.append(_msg_for_renamed(parts[1], parts[2]))

    return messages


def _synthesize(messages: list[str]) -> str:
    """Synthesize per-file messages into a final commit message."""
    if not messages:
        return "vault: update notes"

    # Sort by importance
    sorted_msgs = sorted(messages, key=_importance)

    if len(sorted_msgs) == 1:
        return sorted_msgs[0]

    title = sorted_msgs[0]
    bullets = "\n".join(f"- {m}" for m in sorted_msgs[1:])
    return f"{title}\n\n{bullets}"


def main() -> int:
    vault_root = sys.argv[1] if len(sys.argv) > 1 else "."
    stdin_lines = sys.stdin.readlines()
    messages = _parse_diff_lines(stdin_lines, vault_root)
    print(_synthesize(messages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
