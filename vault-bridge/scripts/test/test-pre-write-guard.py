#!/usr/bin/env python3
"""
Regression test for `vault-bridge/hooks/pre-write-guard.sh` —
Write Role Contract enforcement + filename validation.

Policy (2026-05-12): vault writes must be user-initiated (main context,
slash commands). Subagent vault writes are out of policy and are
detected via agent identifier fields in the PreToolUse payload.

Run: python3 vault-bridge/scripts/test/test-pre-write-guard.py
Exit 0 on pass, 1 on fail.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "vault-bridge" / "hooks" / "pre-write-guard.sh"


def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _run(payload: dict, env_overrides: dict | None = None, vault_root: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Always unset the env vars under test so each case is hermetic
    for key in ("VAULT_BRIDGE_DISABLE", "VAULT_BRIDGE_STRICT_NAMING",
                "VAULT_BRIDGE_WRITE_CONTRACT", "VAULT_BRIDGE_VAULT_ROOT",
                "VAULT_BRIDGE_VAULT_PATH"):
        env.pop(key, None)
    if vault_root is not None:
        env["VAULT_BRIDGE_VAULT_ROOT"] = vault_root
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def _make_payload(
    file_path: str,
    tool_name: str = "Write",
    agent_id_field: str | None = None,
    agent_id_value: str | None = None,
) -> dict:
    payload: dict = {
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
    }
    if agent_id_field and agent_id_value:
        payload[agent_id_field] = agent_id_value
    return payload


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def case_main_context_inbox_write(errors: list[str], vault_root: str) -> None:
    """No agent_id + valid path → clean pass (exit 0, stdout empty)."""
    print("\ncase: main_context_inbox_write")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_subagent_enforce_default(errors: list[str], vault_root: str) -> None:
    """subagent_type present + no VAULT_BRIDGE_WRITE_CONTRACT → enforce (actual default at line 91)."""
    print("\ncase: subagent_enforce_default")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="vault-searcher")
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)
    _assert("systemMessage" in proc.stdout and "vault-bridge contract" in proc.stdout,
            f"stdout contains systemMessage with vault-bridge contract (got: {proc.stdout!r})", errors)


def case_subagent_warn_explicit(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_WRITE_CONTRACT=warn → explicit warn mode (log + allow); default is enforce."""
    print("\ncase: subagent_warn_explicit")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="vault-searcher")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "warn"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert("CONTRACT WARNING" in proc.stderr,
            f"stderr contains CONTRACT WARNING (got: {proc.stderr!r})", errors)
    _assert("systemMessage" in proc.stdout and "vault-bridge contract" in proc.stdout,
            f"stdout contains systemMessage with vault-bridge contract (got: {proc.stdout!r})", errors)


def case_subagent_enforce(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_WRITE_CONTRACT=enforce → permissionDecision:deny."""
    print("\ncase: subagent_enforce")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)


def case_subagent_off(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_WRITE_CONTRACT=off → contract bypassed; stdout empty."""
    print("\ncase: subagent_off")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "off"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_assets_passthrough(errors: list[str], vault_root: str) -> None:
    """assets/ is passthrough (v4) — exits 0 cleanly; no contract check, no naming check."""
    print("\ncase: assets_passthrough")
    path = f"{vault_root}/assets/image.png"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "",
            f"stdout empty (assets/ passthrough — no contract or naming check; got: {proc.stdout!r})", errors)


def case_notes_valid_filename(errors: list[str], vault_root: str) -> None:
    """notes/ with valid kebab-case filename → clean pass (exit 0, stdout empty)."""
    print("\ncase: notes_valid_filename")
    path = f"{vault_root}/notes/my-thought.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_subfolder_valid(errors: list[str], vault_root: str) -> None:
    """notes/ sub-folder with valid kebab filename → clean pass (top_dir=notes; filename validated)."""
    print("\ncase: notes_subfolder_valid")
    path = f"{vault_root}/notes/diary/my-entry.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_violation(errors: list[str], vault_root: str) -> None:
    """notes/ with uppercase filename → naming violation (VAULT_BRIDGE_STRICT_NAMING=1 → exit 2)."""
    print("\ncase: notes_violation")
    path = f"{vault_root}/notes/MyNote.md"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_notes_base_view(errors: list[str], vault_root: str) -> None:
    """notes/{view-name}.base (Obsidian Bases view, #118) → clean pass (exit 0, stdout empty)."""
    print("\ncase: notes_base_view")
    path = f"{vault_root}/notes/inbox-raw.base"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_base_subfolder(errors: list[str], vault_root: str) -> None:
    """notes/{sub}/{view-name}.base → clean pass (top_dir=notes; .base allowed under sub-folder)."""
    print("\ncase: notes_base_subfolder")
    path = f"{vault_root}/notes/diary/evergreen.base"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_base_uppercase_violation(errors: list[str], vault_root: str) -> None:
    """notes/ .base with uppercase stem → naming violation (STRICT_NAMING=1 → exit 2).

    Confirms the .base extension widening did NOT loosen the kebab stem rule.
    """
    print("\ncase: notes_base_uppercase_violation")
    path = f"{vault_root}/notes/InboxRaw.base"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_inbox_base_violation(errors: list[str], vault_root: str) -> None:
    """inbox/{view-name}.base → naming violation (.base is a notes/ view file, not inbox/).

    The .base extension widening is scoped to notes/; inbox/ keeps {type}-DATE.md only.
    """
    print("\ncase: inbox_base_violation")
    path = f"{vault_root}/inbox/inbox-raw.base"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_notes_moc_named_passes(errors: list[str], vault_root: str) -> None:
    """notes/moc-overview.md → clean pass via the kebab notes/ pattern (NOT a whitelist).

    Proves the moc-*.md whitelist removal (#166) is safe for notes/: a MOC-named
    file still matches the loose kebab pattern, so removal changes nothing here.
    """
    print("\ncase: notes_moc_named_passes")
    path = f"{vault_root}/notes/moc-overview.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_inbox_moc_named_violation(errors: list[str], vault_root: str) -> None:
    """inbox/moc-overview.md + STRICT_NAMING=1 → exit 2.

    Proves the moc-*.md whitelist case was actually removed (#166): with no
    whitelist, the file now fails the inbox capture|session pattern.
    """
    print("\ncase: inbox_moc_named_violation")
    path = f"{vault_root}/inbox/moc-overview.md"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_notes_index_structural(errors: list[str], vault_root: str) -> None:
    """notes/_index.md → clean pass (structural index still valid; audit-aligned)."""
    print("\ncase: notes_index_structural")
    path = f"{vault_root}/notes/_index.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_subfolder_index(errors: list[str], vault_root: str) -> None:
    """notes/diary/_index.md → clean pass (folder-level index in a sub-folder still valid)."""
    print("\ncase: notes_subfolder_index")
    path = f"{vault_root}/notes/diary/_index.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_root_index(errors: list[str], vault_root: str) -> None:
    """{vault_root}/_index.md → clean pass (vault-level index)."""
    print("\ncase: root_index")
    path = f"{vault_root}/_index.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_decision_dated(errors: list[str], vault_root: str) -> None:
    """notes/decision-YYYY-MM-DD-{slug}.md (v4 §3.6) matches the loose kebab pattern."""
    print("\ncase: notes_decision_dated")
    path = f"{vault_root}/notes/decision-2026-05-26-architecture-choice.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_plan_dated(errors: list[str], vault_root: str) -> None:
    """notes/plan-YYYY-MM-DD-{slug}.md (v4 §3.6) matches the loose kebab pattern."""
    print("\ncase: notes_plan_dated")
    path = f"{vault_root}/notes/plan-2026-05-26-pr1-rollout.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_wiki_valid_filename(errors: list[str], vault_root: str) -> None:
    """wiki/{slug}.md (v5 §3 A-layer) → clean pass (exit 0, stdout empty)."""
    print("\ncase: wiki_valid_filename")
    path = f"{vault_root}/wiki/defuddle-cli.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_wiki_subfolder_valid(errors: list[str], vault_root: str) -> None:
    """wiki/{sub}/{slug}.md → clean pass (free sub-folders, like notes/; top_dir=wiki)."""
    print("\ncase: wiki_subfolder_valid")
    path = f"{vault_root}/wiki/tools/obsidian-bases.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_wiki_violation(errors: list[str], vault_root: str) -> None:
    """wiki/ with uppercase filename → naming violation (STRICT_NAMING=1 → exit 2)."""
    print("\ncase: wiki_violation")
    path = f"{vault_root}/wiki/DefuddleCLI.md"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_wiki_base_violation(errors: list[str], vault_root: str) -> None:
    """wiki/{name}.base → naming violation (.base is a notes/ view file only; STRICT → exit 2)."""
    print("\ncase: wiki_base_violation")
    path = f"{vault_root}/wiki/view.base"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_wiki_subagent_enforce(errors: list[str], vault_root: str) -> None:
    """Subagent wiki write → deny (Write Role Contract holds for wiki/ too — wiki skill is main-context)."""
    print("\ncase: wiki_subagent_enforce")
    path = f"{vault_root}/wiki/defuddle-cli.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)


def case_filename_violation_warn_mode(errors: list[str], vault_root: str) -> None:
    """Subagent + bad filename + warn → both CONTRACT WARNING and NAMING VIOLATION in stderr."""
    print("\ncase: filename_violation_warn_mode")
    path = f"{vault_root}/inbox/badname.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "warn"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert("CONTRACT WARNING" in proc.stderr,
            f"stderr contains CONTRACT WARNING (got: {proc.stderr!r})", errors)
    _assert("NAMING VIOLATION" in proc.stderr,
            f"stderr contains NAMING VIOLATION (got: {proc.stderr!r})", errors)


def case_filename_violation_strict_naming(errors: list[str], vault_root: str) -> None:
    """No agent_id + bad filename + VAULT_BRIDGE_STRICT_NAMING=1 → exit 2."""
    print("\ncase: filename_violation_strict_naming")
    path = f"{vault_root}/inbox/badname.md"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_subagent_filename_violation_enforce(errors: list[str], vault_root: str) -> None:
    """Subagent + bad filename + enforce → deny fires first; filename check never reached."""
    print("\ncase: subagent_filename_violation_enforce")
    path = f"{vault_root}/inbox/badname.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)
    # Must NOT also emit a naming violation (contract deny exits before that check)
    _assert("NAMING VIOLATION" not in proc.stderr,
            f"stderr must not contain NAMING VIOLATION (got: {proc.stderr!r})", errors)


def case_kill_switch(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_DISABLE=1 → exit 0, stdout empty regardless of contract mode."""
    print("\ncase: kill_switch")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="vault-searcher")
    proc = _run(
        payload,
        env_overrides={"VAULT_BRIDGE_DISABLE": "1", "VAULT_BRIDGE_WRITE_CONTRACT": "enforce"},
        vault_root=vault_root,
    )
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


# ---------------------------------------------------------------------------
# Bash bypass cases (#381)
#
# The Write|Edit matcher alone left the Write Role Contract bypassable: a subagent
# holding Bash could write the vault with `echo >`, `mv`, `tee`. The guard now also
# fires on Bash and denies writes whose TARGET resolves inside the vault.
#
# FP=0 is the load-bearing property — reads must keep working. Every allow case below
# is a read (or a write that lands outside the vault / in assets/), and a false deny
# there would make the vault unreadable to subagents, which is the whole point of the
# read/write asymmetry.
#
# KNOWN_EVASIONS (deliberately not caught — honest-subagent threat model, same as
# scripts/subagent-git-guard.sh #209): indirection that takes the command as data —
# `eval`, `sh -c "..."`, backticks, `xargs`, `python3 -c "open(...).write()"` — and
# $(...)-computed target paths. Catching those statically costs false positives on
# reads, which is the more expensive failure here.
# ---------------------------------------------------------------------------

def _make_bash_payload(command: str, agent_id_value: str | None = None, cwd: str | None = None) -> dict:
    payload: dict = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent_id_value:
        payload["subagent_type"] = agent_id_value
    if cwd:
        payload["cwd"] = cwd
    return payload


def case_bash_subagent_writes_denied(errors: list[str], vault_root: str) -> None:
    """Subagent Bash commands whose write target is inside the vault → deny."""
    print("\ncase: bash_subagent_writes_denied")
    v = vault_root
    commands = [
        f'echo "hello" > {v}/notes/x.md',                    # the #381 headline bypass
        f'cat > {v}/notes/x.md <<EOF\nhello\nEOF',           # heredoc
        f'printf "x" >> {v}/wiki/page.md',                   # append
        f'mv /tmp/a.md {v}/notes/x.md',                      # move in
        f'cp /tmp/a.md {v}/notes/x.md',                      # copy in
        f'echo x | tee {v}/notes/x.md',                      # tee after a pipe
        f'cd {v} && echo x > notes/y.md',                    # relative target after cd
        f'sed -i "" s/a/b/ {v}/notes/x.md',                  # in-place edit
        f'touch {v}/inbox/capture-2026-01-01.md',
        f'mkdir -p {v}/notes/newdir',
        f'rm {v}/notes/x.md',                                # deletion is a write too
        f'sudo cp /tmp/a.md {v}/notes/x.md',                 # wrapper prefix
        # Compound redirects (#387): shlex(punctuation_chars=True) glues these into ONE
        # token, so the first-cut `^\d*>>?$` regex missed them — and `&>` is exactly what an
        # honest agent reaches for to capture a script's output.
        f'script.sh &> {v}/notes/log.md',
        f'script.sh &>> {v}/notes/log.md',
        f'script.sh >& {v}/notes/log.md',
        f'echo x >| {v}/notes/x.md',
        f'script.sh 2> {v}/notes/err.md',                    # fd-prefixed
        # GNU coreutils target-directory flags (#387): the destination is NOT the last
        # positional arg here — every positional is a source.
        f'mv -t {v}/notes /tmp/a.md /tmp/b.md',
        f'cp --target-directory={v}/notes /tmp/a.md',
        f'cp --target-directory {v}/notes /tmp/a.md',         # long-form, space-separated (#390)
        f'mv -t{v}/notes /tmp/a.md',                          # short-form, no space (#390)
        f'rsync -tv /tmp/a.md {v}/notes/x.md',                # rsync -t is boolean (--times),
                                                               # not target-directory (fresh-eyes review)
        f'rsync -t /tmp/a.md {v}/notes/x.md',                 # bare -t, same rsync semantics
                                                               # (fresh-eyes review round 2)
        f'cp -rt {v}/notes /tmp/a.md',                        # #399: -t at cluster END (-r before -t),
                                                               # value is the next token, not inline
        f'cp -vt {v}/notes /tmp/a.md',                        # #399: same, different leading flag
    ]
    for cmd in commands:
        payload = _make_bash_payload(cmd, agent_id_value="vault-file-organizer", cwd="/tmp")
        proc = _run(payload, vault_root=vault_root)
        _assert(proc.returncode == 0, f"exit 0 (deny is a decision, not an error): {cmd!r}", errors)
        _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
                f"denied: {cmd!r} (got: {proc.stdout!r})", errors)


def case_bash_reads_pass(errors: list[str], vault_root: str) -> None:
    """FP=0: subagent Bash reads (and non-vault / assets writes) → clean pass."""
    print("\ncase: bash_reads_pass")
    v = vault_root
    commands = [
        f'grep -r foo {v}',                                  # search the vault
        f'cat {v}/notes/x.md',                               # read a file
        f'cd {v} && git status',                             # vault as cwd, read-only git
        f'ls {v}/notes',
        f'cp {v}/notes/x.md /tmp/',                          # vault is the SOURCE, not the target
        f'echo "write to {v}/notes/x.md"',                   # path only mentioned, not written
        f"grep '>' {v}/notes/x.md",                          # quoted > is not a redirection
        'echo x > /tmp/outside.md',                          # write outside the vault
        f'cp /tmp/a.png {v}/assets/a.png',                   # assets/ passthrough
        f'grep -r foo {v} 2>&1',                             # fd dup, not a file target (#387)
        f'script.sh &> /tmp/log.md < {v}/notes/x.md',        # compound redirect, but outside the vault
        f'mv -t /tmp {v}/notes/x.md',                        # -t target is outside; vault is the source
        f'cp -rt /tmp {v}/notes/x.md',                       # #399: cluster -rt, target outside vault
    ]
    for cmd in commands:
        payload = _make_bash_payload(cmd, agent_id_value="vault-searcher", cwd="/tmp")
        proc = _run(payload, vault_root=vault_root)
        _assert(proc.returncode == 0, f"exit 0: {cmd!r}", errors)
        _assert(proc.stdout.strip() == "", f"stdout empty (no deny): {cmd!r} (got: {proc.stdout!r})", errors)


def case_bash_main_context_allowed(errors: list[str], vault_root: str) -> None:
    """Main context (no agent identifier) owns vault writes → Bash write passes."""
    print("\ncase: bash_main_context_allowed")
    payload = _make_bash_payload(f'echo x > {vault_root}/notes/x.md', cwd="/tmp")
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_bash_warn_and_off_modes(errors: list[str], vault_root: str) -> None:
    """warn → allow + systemMessage; off → silent; kill switch → silent."""
    print("\ncase: bash_warn_and_off_modes")
    cmd = f'echo x > {vault_root}/notes/x.md'
    payload = _make_bash_payload(cmd, agent_id_value="vault-file-organizer", cwd="/tmp")

    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "warn"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "warn: exit 0", errors)
    _assert("permissionDecision" not in proc.stdout, f"warn: no deny (got: {proc.stdout!r})", errors)
    _assert("vault-bridge contract" in proc.stdout, f"warn: systemMessage present (got: {proc.stdout!r})", errors)

    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "off"}, vault_root=vault_root)
    _assert(proc.stdout.strip() == "", f"off: stdout empty (got: {proc.stdout!r})", errors)

    proc = _run(payload, env_overrides={"VAULT_BRIDGE_DISABLE": "1"}, vault_root=vault_root)
    _assert(proc.stdout.strip() == "", f"kill switch: stdout empty (got: {proc.stdout!r})", errors)


def case_non_vault_path(errors: list[str]) -> None:
    """Subagent writing outside vault → exit 0, stdout empty (unchanged behavior)."""
    print("\ncase: non_vault_path")
    path = "/tmp/some-file.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"})
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"Running pre-write-guard regression tests against: {HOOK}")

    if not HOOK.exists():
        print(f"ERROR: hook not found at {HOOK}", file=sys.stderr)
        return 1

    errors: list[str] = []

    # Provision a temporary fake vault root so tests are hermetic and the real
    # ~/vault is never touched. The hook only requires the directory to exist.
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = tmp
        # Create the top-level dirs the hook navigates (v4: inbox, notes, assets; v5 adds wiki)
        for d in ("inbox", "notes", "assets", "wiki"):
            Path(vault_root, d).mkdir(parents=True, exist_ok=True)
        # Sub-folders for the notes/ and wiki/ sub-folder tests
        Path(vault_root, "notes", "diary").mkdir(parents=True, exist_ok=True)
        Path(vault_root, "wiki", "tools").mkdir(parents=True, exist_ok=True)

        case_main_context_inbox_write(errors, vault_root)
        case_subagent_enforce_default(errors, vault_root)
        case_subagent_warn_explicit(errors, vault_root)
        case_subagent_enforce(errors, vault_root)
        case_subagent_off(errors, vault_root)
        case_assets_passthrough(errors, vault_root)
        case_notes_valid_filename(errors, vault_root)
        case_notes_subfolder_valid(errors, vault_root)
        case_notes_violation(errors, vault_root)
        case_notes_base_view(errors, vault_root)
        case_notes_base_subfolder(errors, vault_root)
        case_notes_base_uppercase_violation(errors, vault_root)
        case_inbox_base_violation(errors, vault_root)
        case_notes_moc_named_passes(errors, vault_root)
        case_inbox_moc_named_violation(errors, vault_root)
        case_notes_index_structural(errors, vault_root)
        case_notes_subfolder_index(errors, vault_root)
        case_root_index(errors, vault_root)
        case_notes_decision_dated(errors, vault_root)
        case_notes_plan_dated(errors, vault_root)
        case_wiki_valid_filename(errors, vault_root)
        case_wiki_subfolder_valid(errors, vault_root)
        case_wiki_violation(errors, vault_root)
        case_wiki_base_violation(errors, vault_root)
        case_wiki_subagent_enforce(errors, vault_root)
        case_filename_violation_warn_mode(errors, vault_root)
        case_filename_violation_strict_naming(errors, vault_root)
        case_subagent_filename_violation_enforce(errors, vault_root)
        case_kill_switch(errors, vault_root)
        case_bash_subagent_writes_denied(errors, vault_root)
        case_bash_reads_pass(errors, vault_root)
        case_bash_main_context_allowed(errors, vault_root)
        case_bash_warn_and_off_modes(errors, vault_root)

    # Non-vault path test needs no vault_root provisioning
    case_non_vault_path(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
