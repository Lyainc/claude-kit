#!/usr/bin/env bash
# vault-bridge SessionStart hook — Vault Manifest Staleness Check & Regeneration
#
# Runs at the start of every Claude Code session. Checks whether the vault
# manifest needs regeneration and triggers generate-manifest.py if so.
# Failures are always silent — this hook must never block session startup.
#
# Environment variables:
#   VAULT_BRIDGE_DISABLE=1        — skip entirely (kill switch)
#   VAULT_BRIDGE_VAULT_ROOT=PATH  — explicit env override (highest priority)
#   VAULT_BRIDGE_VAULT_PATH=PATH  — userConfig vault path (set by Claude Code plugin settings)

set -uo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-}" = "1" ]; then
  exit 0
fi

# Resume handoff injection: surface a prior session's resume.md to the *model*
# via additionalContext — systemMessage would reach only the user. The python3
# guard leaves the file intact when no interpreter is available, rather than
# consuming an undelivered handoff note.
_PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
_RESUME_FILE="$_PROJECT_ROOT/.claude-kit/vault-bridge/resume.md"
_resume_consumed=false
if [ -f "$_RESUME_FILE" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$_RESUME_FILE" <<'PYEOF'
import sys, json, os
try:
    resume_path = sys.argv[1]
    raw = open(resume_path).read().strip()
    if not raw:
        sys.exit(0)  # empty resume.md — leave intact so a future write can replace it
    lines = raw.split('\n')

    # Strip YAML frontmatter; collect project_name from it
    project_name = None
    body_start = 0
    if lines and lines[0].strip() == '---':
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                body_start = i + 1
                break
            if line.startswith('project:'):
                project_name = line.split(':', 1)[1].strip()
    body_lines = lines[body_start:]
    body = '\n'.join(body_lines).strip()

    if not body:
        sys.exit(0)  # frontmatter only, no body — leave file intact, retry next session

    # Extract one-liner from "## 한 줄 재개 프롬프트" section (standard /handoff format),
    # or fall back to "## 한 줄 목표" section (manual handoff format).
    # Supports both plain-text and fenced-code-block forms.
    one_liner = None
    for section_marker in ('한 줄 재개 프롬프트', '한 줄 목표'):
        in_section = False
        for line in body_lines:
            if section_marker in line and line.strip().startswith('#'):
                in_section = True
                continue
            if in_section:
                s = line.strip()
                if s.startswith('#'):
                    break
                if s.startswith('```') or s.startswith('~~~'):
                    continue
                if s:
                    one_liner = s
                    break
        if one_liner:
            break

    # Extract brief topic from "**작업 주제**:" line
    topic = None
    for line in body_lines:
        if '작업 주제' in line and ':' in line:
            topic = line.split(':', 1)[1].strip().strip('*').strip()
            if len(topic) > 80:
                topic = topic[:77] + '...'
            break

    # Header: one-liner if parsed, else generic marker. Verbose line carries
    # project/topic context separately to avoid duplicating either.
    if one_liner:
        header = '[세션 복원] ' + one_liner
    else:
        header = '[세션 복원] 이전 세션 인수인계 (상세: "handoff 보여줘")'

    verbose_parts = []
    if project_name:
        verbose_parts.append('프로젝트: ' + project_name)
    if topic:
        verbose_parts.append('작업: ' + topic)

    user_msg = header
    if verbose_parts:
        user_msg += '\n' + '  |  '.join(verbose_parts)

    model_ctx = '이전 세션의 인수인계 메모입니다:\n\n' + body
    print(json.dumps({
        'systemMessage': user_msg,
        'additionalContext': model_ctx,
    }))
    prev_path = resume_path[:-3] + '.prev.md'
    os.replace(resume_path, prev_path)  # atomic rename; .prev kept as one-level backup
except Exception:
    pass  # leave resume_path intact so next session can retry
PYEOF
  # Flag reflects actual file state: True iff Python's os.replace() ran successfully
  # (resume.md renamed away). Early-bail paths inside Python keep the file present,
  # so this check stays accurate without depending on the script's exit code.
  [ ! -f "$_RESUME_FILE" ] && _resume_consumed=true
fi

# Recovery hint: resume.md consumed in a short/accidental session → .prev.md survives as backup.
# Guard with _resume_consumed: after a successful rename resume.md→.prev.md above, both
# conditions (no resume.md + prev.md exists) would be true — causing a spurious backup warning.
_PREV_FILE="${_RESUME_FILE%.md}.prev.md"
if [ "$_resume_consumed" = false ] && [ ! -f "$_RESUME_FILE" ] && [ -f "$_PREV_FILE" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$_PREV_FILE" <<'PYEOF'
import sys, json
try:
    prev = sys.argv[1]
    restored = prev[:-8] + '.md'  # .prev.md → .md
    msg = '[resume 백업 감지] 직전 세션 resume가 짧은 세션으로 소비됐을 수 있어요.\n복구하려면: mv ' + prev + ' ' + restored

    raw = open(prev).read().strip()
    lines = raw.split('\n')
    body_start = 0
    if lines and lines[0].strip() == '---':
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                body_start = i + 1
                break
    body = '\n'.join(lines[body_start:]).strip()

    out = {'systemMessage': msg}
    if body:
        out['additionalContext'] = '이전 세션의 인수인계 메모입니다 (백업):\n\n' + body
    print(json.dumps(out))
except Exception:
    pass
PYEOF
fi

# Resolve vault root: VAULT_BRIDGE_VAULT_ROOT (env override) >
# VAULT_BRIDGE_VAULT_PATH (userConfig, set by Claude Code) > $HOME/vault (default).
_raw_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_raw_vr" ] && _raw_vr="${HOME}/vault"
VAULT_ROOT="${_raw_vr/#\~/$HOME}"
unset _raw_vr

# Vault must exist; if not, silently exit (external projects may not have a vault)
if [ ! -d "$VAULT_ROOT" ]; then
  exit 0
fi

# Locate this script's directory to find the generator relative to plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
GENERATOR="${PLUGIN_ROOT}/scripts/generate-manifest.py"

if [ ! -f "$GENERATOR" ]; then
  exit 0
fi

# Run generator in background with a 10s wall-time cap to handle large vaults
# or slow filesystems. The generator itself is fast (incremental mtime checks).
# Discard stdout/stderr — stats are not needed here.
(
  timeout 10 python3 "$GENERATOR" --vault-root "$VAULT_ROOT" >/dev/null 2>&1
) &

exit 0
