#!/usr/bin/env python3
"""Regression test for `scripts/subagent-git-guard.sh` (#209).

Policy (rules/RULES.md §1, #209): a subagent leaves changes in the working tree — it
does NOT commit, push, or create/merge PRs. The main context owns git. This guard is a
PreToolUse Bash hook that denies subagent git side effects; a subagent is detected via
agent-identifier fields in the PreToolUse payload (same fields as vault-bridge
pre-write-guard).

In-memory cases: planted VIOLATIONS (must deny in enforce / warn in warn mode) plus
CLEAN fixtures (must pass with empty stdout, FP=0 — git reads, main-context git, quoted
mentions, non-git commands). Hermetic: each case sets its own env, runs the hook via
subprocess with a crafted JSON payload. No real git is invoked.

Run: python3 scripts/test/test-subagent-git-guard.py
Exit 0 on pass, 1 on fail.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts" / "subagent-git-guard.sh"

_ENV_KEYS = ("CLAUDE_KIT_SUBAGENT_GIT_DISABLE", "CLAUDE_KIT_SUBAGENT_GIT_CONTRACT")


def _assert(cond: bool, desc: str, errors: list) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _run(payload: dict, env_overrides=None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    for key in _ENV_KEYS:  # hermetic: never inherit the vars under test
        env.pop(key, None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def _payload(command: str, *, tool_name: str = "Bash",
             agent_field: str = "subagent_type", agent_value=None) -> dict:
    p = {"tool_name": tool_name, "tool_input": {"command": command}}
    if agent_value is not None:
        p[agent_field] = agent_value
    return p


def _denied(proc) -> bool:
    return '"permissionDecision":"deny"' in proc.stdout.replace(" ", "")


def _clean(proc) -> bool:
    return proc.returncode == 0 and proc.stdout.strip() == ""


# ---------------------------------------------------------------------------
# VIOLATION cases — a subagent attempting a git side effect → deny (enforce default).
# ---------------------------------------------------------------------------

VIOLATIONS = [
    ("git_commit", 'git commit -m "feat: x"'),
    ("git_push", "git push origin main"),
    ("git_push_force", "git push --force-with-lease"),
    ("gh_pr_create", 'gh pr create --title "x" --body "y"'),
    ("gh_pr_merge", "gh pr merge 205 --rebase"),
    ("chained_add_commit_push", 'git add -A && git commit -m "x" && git push'),
    ("git_global_opts_commit", "git -C /repo -c user.name=x commit -m y"),
    ("subshell_push", "(git push)"),
    ("full_path_git_commit", "/usr/bin/git commit -m z"),
    ("sudo_git_push", "sudo git push"),
    ("env_assign_git_commit", "GIT_AUTHOR_NAME=x git commit -m y"),  # env-assignment prefix
    ("time_git_push", "time git push"),                              # wrapper-command prefix
    ("commit_after_semicolon", 'echo hi ; git commit -m x'),
    # Evasion forms surfaced by adversarial review (#209 hardening) — must all DENY:
    ("git_push_bg_glued", "git push&"),                 # trailing & glued to the verb
    ("git_push_bg_spaced", "git push origin main &"),   # backgrounded push (spaced &)
    ("git_continuation_commit", "git \\\ncommit -m x"), # backslash-newline between git+verb
    ("gh_repo_flag_before_create", "gh -R owner/repo pr create --fill"),  # global flag first
    ("gh_repo_flag_before_merge", "gh --repo owner/repo pr merge 1"),
    # $(...) command substitution: the () split boundary exposes the inner verb, so a real
    # commit/push hidden in a substitution is still caught (a read like $(git log) is not).
    ("command_subst_commit", "echo $(git commit -m x)"),
]


def case_violations_enforce(errors: list) -> None:
    print("\ncase group: violations (enforce default → deny)")
    for name, cmd in VIOLATIONS:
        proc = _run(_payload(cmd, agent_value="executor"))
        _assert(proc.returncode == 0, f"{name}: exit 0", errors)
        _assert(_denied(proc), f"{name}: permissionDecision:deny (cmd={cmd!r})", errors)


def case_violation_alt_agent_fields(errors: list) -> None:
    """Each accepted agent-identifier field triggers the guard."""
    print("\ncase group: alternate agent-identifier fields")
    for field in ("agent_name", "subagent_type", "attributionAgent"):
        proc = _run(_payload("git push", agent_field=field, agent_value="some-agent"))
        _assert(_denied(proc), f"{field}: deny", errors)
    # nested .agent.name / .agent.type
    for nested in ("name", "type"):
        p = {"tool_name": "Bash", "tool_input": {"command": "git push"},
             "agent": {nested: "nested-agent"}}
        proc = _run(p)
        _assert(_denied(proc), f"agent.{nested}: deny", errors)


# ---------------------------------------------------------------------------
# CLEAN cases — must pass with empty stdout (FP=0).
# ---------------------------------------------------------------------------

CLEAN_SUBAGENT = [
    ("git_status", "git status --short"),
    ("git_diff", "git diff HEAD"),
    ("git_log_grep_commit", "git log --grep=commit --oneline"),  # 'commit' in args, not subcmd
    ("git_show", "git show HEAD"),
    ("git_rev_parse", "git rev-parse --verify HEAD"),
    ("git_add_only", "git add -A"),
    ("git_stash", "git stash list"),
    ("gh_pr_list", "gh pr list"),
    ("gh_pr_view", "gh pr view 205"),
    ("gh_issue_view", "gh issue view 209"),
    ("quoted_git_commit", 'echo "git commit"'),  # quoted mention, not an invocation
    ("non_git_command", "ls -la && npm run build"),
    ("substring_only_gh", "echo tonight"),  # 'gh' substring → python parser → no hit
    ("substring_only_git", "echo legitimate"),  # 'git' substring → python parser → no hit
    ("bg_non_git", "sleep 1 & echo done"),  # FP guard: '&' split must not block non-git
    ("git_continuation_read", "git \\\nstatus --short"),  # continuation join, still a read
    ("gh_pr_list_search", 'gh pr list --search "is:open"'),  # 'pr' but not create/merge
    # Command-position guard (#239 nit 1): git/gh as an ARGUMENT, not the command → allowed.
    ("echo_git_push", "echo git push"),          # unquoted mention as echo args
    ("man_git_commit", "man git commit"),        # reading git help
    ("grep_git_push", 'grep "git push" file'),   # searching for the string
    # gh pr non-publishing subcommands (#239 nit 2): commonly issued, must stay unblocked.
    ("gh_pr_comment", 'gh pr comment 238 --body "x"'),
    ("gh_pr_close", "gh pr close 238"),
    ("gh_pr_edit", "gh pr edit 238 --add-label x"),
]


def case_clean_subagent(errors: list) -> None:
    print("\ncase group: clean subagent commands (FP=0, empty stdout)")
    for name, cmd in CLEAN_SUBAGENT:
        proc = _run(_payload(cmd, agent_value="executor"))
        _assert(_clean(proc), f"{name}: clean pass (cmd={cmd!r}, got stdout={proc.stdout!r})", errors)


def case_main_context_allowed(errors: list) -> None:
    """No agent identifier → main context owns git → never blocked, even for push."""
    print("\ncase group: main-context git (no agent id → allowed)")
    for cmd in ("git commit -m x", "git push origin main", "gh pr create"):
        proc = _run(_payload(cmd, agent_value=None))
        _assert(_clean(proc), f"main-context {cmd!r}: clean pass", errors)


# Accepted residual scope (NOT defects): arbitrary indirection cannot be caught
# statically without false positives, and the guard's threat model is an honest LLM
# subagent ignoring a prose contract (#209), not a deliberate adversary. These forms are
# ALLOWED BY DESIGN. The assertions below pin that boundary in the test (no silent cap),
# so any future tightening updates this list deliberately rather than by accident.
KNOWN_EVASIONS = [
    ("eval", 'eval "git push"'),
    ("sh_dash_c", 'sh -c "git push"'),
    ("backtick", "echo `git push`"),  # backticks are not a split boundary → not parsed
    ("alias_then_use", "alias g=git; g push"),
]


def case_known_evasions(errors: list) -> None:
    """Documented accepted limits: these indirection forms are ALLOWED by design."""
    print("\ncase group: KNOWN_EVASIONS (accepted residual scope → allowed by design)")
    for name, cmd in KNOWN_EVASIONS:
        proc = _run(_payload(cmd, agent_value="executor"))
        _assert(_clean(proc),
                f"{name}: allowed by design (cmd={cmd!r}, got stdout={proc.stdout!r})", errors)


# ---------------------------------------------------------------------------
# Mode + kill-switch + tool-filter behavior.
# ---------------------------------------------------------------------------

def case_warn_mode(errors: list) -> None:
    print("\ncase: warn mode (allow + warn, not deny)")
    proc = _run(_payload("git push", agent_value="executor"),
                env_overrides={"CLAUDE_KIT_SUBAGENT_GIT_CONTRACT": "warn"})
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(not _denied(proc), "NOT a deny", errors)
    _assert("CONTRACT WARNING" in proc.stderr, "stderr has CONTRACT WARNING", errors)
    _assert("subagent-git-guard" in proc.stdout, "stdout has systemMessage", errors)


def case_off_mode(errors: list) -> None:
    print("\ncase: off mode (skip entirely)")
    proc = _run(_payload("git push", agent_value="executor"),
                env_overrides={"CLAUDE_KIT_SUBAGENT_GIT_CONTRACT": "off"})
    _assert(_clean(proc), f"clean pass (got stdout={proc.stdout!r})", errors)


def case_kill_switch(errors: list) -> None:
    print("\ncase: kill switch (DISABLE=1)")
    proc = _run(_payload("git push", agent_value="executor"),
                env_overrides={"CLAUDE_KIT_SUBAGENT_GIT_DISABLE": "1",
                               "CLAUDE_KIT_SUBAGENT_GIT_CONTRACT": "enforce"})
    _assert(_clean(proc), f"clean pass (got stdout={proc.stdout!r})", errors)


def case_non_bash_tool(errors: list) -> None:
    """Only Bash is guarded; a Write carrying git-ish content is untouched."""
    print("\ncase: non-Bash tool (Write) → not guarded")
    proc = _run(_payload("git push", tool_name="Write", agent_value="executor"))
    _assert(_clean(proc), f"clean pass (got stdout={proc.stdout!r})", errors)


def main() -> int:
    print(f"Running subagent-git-guard regression tests against: {HOOK}")
    if not HOOK.exists():
        print(f"ERROR: hook not found at {HOOK}", file=sys.stderr)
        return 1

    errors: list = []
    case_violations_enforce(errors)
    case_violation_alt_agent_fields(errors)
    case_clean_subagent(errors)
    case_main_context_allowed(errors)
    case_known_evasions(errors)
    case_warn_mode(errors)
    case_off_mode(errors)
    case_kill_switch(errors)
    case_non_bash_tool(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
