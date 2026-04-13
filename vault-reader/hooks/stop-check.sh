#!/usr/bin/env bash
# vault-reader Stop hook — deterministic session-closing signal detector.
#
# Why this is a shell script (not a prompt hook):
#   The previous prompt-based Stop hook caused an infinite loop because every
#   LLM invocation produces an assistant turn (even "(silent pass-through)"),
#   which re-fires the Stop hook. A deterministic script produces output ONLY
#   when a closing signal is detected — no LLM call, no loop.

set -euo pipefail

# Ensure a UTF-8 locale so Korean keywords match under grep -E even when the
# parent shell uses a bare C/POSIX locale (otherwise multi-byte chars silently fail).
# Probe for an installed UTF-8 locale; leave LC_ALL untouched if none found
# (setting a non-existent locale would cause setlocale warnings on every fire).
if ! printf '%s' "${LC_ALL:-${LANG:-}}" | grep -qiE 'utf-?8'; then
  for cand in C.UTF-8 en_US.UTF-8 en_US.utf8 C.utf8; do
    if locale -a 2>/dev/null | grep -qx "$cand"; then
      export LC_ALL="$cand"
      break
    fi
  done
fi

payload=$(cat)

transcript_path=$(printf '%s' "$payload" | jq -r '.transcript_path // empty')

if [[ -z "$transcript_path" || ! -f "$transcript_path" ]]; then
  exit 0
fi

# Extract the most recent USER text PROMPT (string content OR array with text blocks).
# We deliberately scan all user entries and take the last non-empty TEXT — not the
# transcript's last entry — because tool_result entries are also user-role and would
# mask the actual user prompt that triggered the closing-signal check.
last_user_text=$(jq -rs '
  map(select(.type == "user"))
  | map(
      .message.content as $c
      | if ($c | type) == "string" then $c
        elif ($c | type) == "array" then
          ($c | map(select(.type == "text") | .text) | join("\n"))
        else "" end
    )
  | map(select(. != null and . != ""))
  | last // ""
' "$transcript_path" 2>/dev/null || true)

if [[ -z "$last_user_text" ]]; then
  exit 0
fi

# Closing-signal regex (Korean + English). Case-insensitive for English.
# Keep this list in sync with vault-reader README documentation.
if printf '%s' "$last_user_text" | grep -qiE \
  -e '세션 끝|세션 마무리|세션 종료|오늘은 여기까지|마무리하자|그만하자|끝내자|오늘 끝|세션 정리해줘|작업 기록 남겨줘' \
  -e "wrap up|let's end|we're done for today|end session|session done|finish up|call it a day|that's all"; then
  jq -nc '{
    systemMessage: "세션 종료 신호 감지. 세션 노트를 남기려면 `/save-session` 실행 또는 vault-searcher에 \"세션 기록해줘\" 요청."
  }'
fi

exit 0
