---
name: vault-manifest-refresh
description: "Force-regenerate the vault manifest cache (~/vault/.vault-bridge/manifest.json), bypassing the staleness check. Invoke via /vault-manifest-refresh."
allowed-tools: Bash
disable-model-invocation: true
---

Force-regenerate the vault manifest by running the manifest generator with `--force`.

**User language: Korean.** All user-facing output MUST be in Korean.

## Procedure

### Step 1 — Determine vault root

Resolve in priority order — `VAULT_BRIDGE_VAULT_ROOT` (env override) > `VAULT_BRIDGE_VAULT_PATH`
(userConfig) > `~/vault` (default), same chain as `hooks/pre-write-guard.sh`:

```bash
_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_vr" ] && _vr="$HOME/vault"
echo "${_vr/#\~/$HOME}"
```

If the resolved vault root does not exist as a directory, output the following and stop:

> vault 디렉토리를 찾을 수 없습니다: `{vault_root}`
> `VAULT_BRIDGE_VAULT_ROOT` 환경변수를 설정하거나 `~/vault/`에 vault를 배치해 주세요.

### Step 2 — Run generator

Locate the plugin root via the script directory and use Bash to run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/generate-manifest.py" \
  --vault-root "{vault_root}" \
  --force
```

Capture stdout (JSON stats line) and exit code.

### Step 3 — Report result

**On success (exit 0)**: parse the JSON stats line and output:

> vault manifest를 재생성했습니다.
>
> | 항목 | 수치 |
> |------|------|
> | 총 파일 수 | `{generated}` |
> | 소요 시간 | `{elapsed_ms}ms` |
>
> 저장 위치: `{vault_root}/.vault-bridge/manifest.json`

**On exit code 1** (vault_root missing):

> vault 디렉토리가 없습니다: `{vault_root}`

**On exit code 2** (write failure):

> manifest 파일 쓰기에 실패했습니다. 디스크 공간 또는 권한을 확인해 주세요.

**On any other error**:

> manifest 재생성 중 오류가 발생했습니다. `stderr` 내용을 확인해 주세요.

## Rules

- Always run with `--force` to bypass staleness check.
- Never modify vault files — only reads vault and writes to `{vault_root}/.vault-bridge/manifest.json`.
- If `VAULT_BRIDGE_DISABLE=1` is set, inform the user that vault-bridge is disabled and skip execution.
