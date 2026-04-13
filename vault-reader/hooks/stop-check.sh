#!/usr/bin/env bash
# vault-reader Stop hook — deterministic session-closing signal detector.
#
# Why this is a shell script (not a prompt hook):
#   The previous prompt-based Stop hook caused an infinite loop because every
#   LLM invocation produces an assistant turn (even "(silent pass-through)"),
#   which re-fires the Stop hook. A deterministic script produces output ONLY
#   when a closing signal is detected — no LLM call, no loop.

set -euo pipefail

payload=$(cat)

transcript_path=$(printf '%s' "$payload" | jq -r '.transcript_path // empty')

if [[ -z "$transcript_path" || ! -f "$transcript_path" ]]; then
  exit 0
fi

# Extract the most recent USER text message (string content OR array with text blocks).
# Skip tool_result-only user entries — they are tool responses, not user prompts.
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
