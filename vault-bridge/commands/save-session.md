---
description: Create a session note recording the current session's work via vault-searcher Mode 4
allowed-tools: Task
---

Delegate to the `vault-searcher` agent in Mode 4 (Session Note Creation).

Use the Task tool with `subagent_type: "vault-bridge:vault-searcher"` and request:

> 현재 세션을 정리해서 세션 노트를 작성해줘. Mode 4 (Session Note Creation)로 진입하고, AskUserQuestion으로 다음 두 단계를 사용자에게 확인해줘:
> 1. **Mode 선택**: record (요약만) / handoff (다음 세션 인계) / quick (최소 캡처)
> 2. **저장 확인**: 작성된 본문을 보여주고 저장 여부 확인
>
> 파일은 `~/vault/00_Inbox/session-YYYY-MM-DD.md` 컨벤션을 따르고, 같은 날짜 충돌 시 `-v2`, `-v3` 자동 증가.

I/O: All user-facing output in Korean.
