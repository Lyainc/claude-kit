# expert-panel 2토픽 벤치마크 입력과 측정 절차

issue #864에서 보존을 요청한 expert-panel 2토픽 벤치마크의 입력 원문, 측정 절차, 기록된 측정값을 모아 둔 문서예요. #771(resume 비용)과 #770(effort 관측)이 같은 벤치마크로 실측을 다시 할 때 세션 transcript를 뒤지지 않도록 하는 것이 목적이에요.

## 출처

- 원문: #864 (`feat(thinking-tools): expert-panel 라벨 한정어 실행 확인과 보류 enum 정적 검사를 더하고 2토픽 벤치마크를 보존한다`)
- 이슈 본문에 나오는 벤치마크 사용처: #768 3×3 실측, #793 전후 비교, #793 위임 실행
- 이슈 본문의 날짜 표기: 원문에 없음 (이슈 생성일과 본문 작성일은 확인되지 않아요)
- 코멘트 2026-10-16 (Lyainc): #835 코멘트에 `0319346`(add-policy SKILL.md를 Codex 8,000바이트 상한 아래로 복구)이 기록됐다는 관계 정리
- 코멘트 2026-10-17 (Lyainc): `docs/specs/expert-panel-delegated-mode.yaml`의 `issues.tracking`에 이 이슈를 기록했다는 내용(브랜치 `docs/seed-tracking-cleanup`, `1508a76`). 코멘트 본문에는 "2026-10-16"으로 적혀 있어요.
- 관련 참조: PR #851(c0dc27b, 24e8fe7), #771, #770, #835, #793

## 벤치마크 입력

이슈 본문의 `<details>` 블록에 있던 프롬프트 원문이에요. 토픽 1과 토픽 2를 한 프롬프트 안에 담고 있어요.

```text
/thinking-tools:expert-panel 전문가 토론으로 두 가지 결정을 검토해줘.

토픽 1: claude-kit에서 SKILL.md가 Codex의 8,000바이트 invoked-skill 상한에 거의 닿았을 때(예: expert-panel SKILL.md가 상한까지 20~30바이트만 남은 상태) 앞으로 어떤 방식으로 대응할지 정한다. 후보는 (A) 지금처럼 산문을 reference.md로 옮기고 SKILL.md에는 locator만 남기는 관례를 계속 쓴다, (B) 상한 근처 스킬을 하위 스킬 둘 이상으로 나눈다, (C) Codex 전용으로 축약 SKILL 본문을 따로 생성해 Claude 본문과 분리한다.

토픽 2: claude-kit CI의 가드 검사를 앞으로 어떻게 구성할지 정한다. 후보는 (A) 지금처럼 .github/workflows/validate.yml에 가드 명령을 단계별로 계속 나열한다, (B) 가드 목록을 한 파일로 모으고 단일 러너 스크립트가 실행하게 한다, (C) 플러그인별 워크플로로 나눈다.

초기 자료(이 파일들만 근거로 쓰고, 필요하면 Read/Grep으로 읽어줘):
- thinking-tools/skills/expert-panel/SKILL.md
- scripts/check-skill-token-budget.py
- docs/skill-boundaries.md
- thinking-tools/reference/codex-portability.md
- .github/workflows/validate.yml

완료 조건: 토픽 두 개를 각각 결론까지 진행하고, 스킬의 Phase 2 규칙대로 기록 파일을 만든 뒤, 대화 안에 SUMMARY를 결론, 근거, 권고(실행안), 소수 의견, 적용 조건(실행안·실패/중단 조건), 불확실성, 미해결 순서로 내고 끝낸다. 사용자에게 추가 질문은 하지 말고, 사용자만 답할 수 있는 사실은 미해결로 남긴다.
```

위임 변형은 위 프롬프트 끝에 빈 줄과 `위임해서 진행해줘.`를 붙여요.

## 측정 절차

### 실행 조건

- 실행 위치: 커밋별 새 detached worktree에서 실행해요. (이슈 제안 1번은 main의 새 worktree에서 실행하도록 적고 있어요.)
- 모델과 effort: Sonnet, effort high, 같은 도구 권한으로 실행해요.
- 실행 명령:

```bash
claude -p "$P" --plugin-dir ./thinking-tools --model sonnet --effort high --output-format json --allowedTools "Read Grep Glob Skill Agent Write Bash(python3:*)" --session-id $sid
```

### 세어야 할 항목

- 전체 사용량은 CLI JSON `modelUsage`, 메인 사용량은 `usage`예요. worker는 `modelUsage`에서 `usage`를 뺀 값이에요.
- TTL은 `~/.claude/projects/<worktree>/<sid>.jsonl`과 `<sid>/subagents/*.jsonl`의 `cache_creation.ephemeral_{5m,1h}_input_tokens`로 확인해요. effort는 같은 파일의 `effort` 필드로 확인해요.
- Codex에서는 `~/.codex/sessions/<날짜>/rollout-*.jsonl`의 `session_meta.source.subagent.thread_spawn.parent_thread_id`로 자식 thread를 찾아요. fork 여부는 `forked_from_id`로 보고, 사용량은 마지막 `token_count.total_token_usage`로 봐요. 메인 turn 사용량에 자식이 포함되는지는 미확정이에요.
- 비용은 CLI `total_cost_usd`(list 기준 추정)이고, 구독 usage로 환산하지 않아요.
- 이슈 제안 1번이 적은 기록 항목: 비용, 시간, cache(메인/worker, TTL), 그리고 transcript Moderator 줄에 라벨 뒤 한정어가 없는지 여부예요. 결과는 표본 수와 함께 적어요.

## 기록된 측정값

이슈에 적힌 수치만 옮겼어요. 이 문서에서 새로 계산한 값은 없어요.

- 본문, #793 마무리 실측 규모: Claude 위임 1회, Codex 격리 1회.
- 본문, 패널 바이트 관찰(#835, n=1): 언어 지시로 권고된 문장이 약 232바이트, 지금 문장은 69~141바이트. 파일마다 90~160바이트가 늘어요. `obsidian-vault-manager/skills/audit/SKILL.md`는 7,992바이트로 8,000바이트 한도를 넘게 된다고 적혀 있어요.
- 본문, SKILL.md 현재 크기: expert-panel SKILL.md 7,987바이트(영향 범위 절).
- 본문, #771 참고값(Codex 격리 자식 사용량): E2/E3 재spawn 12개, input 839,827, 자식 전체의 42%, 대부분 cache.
- 본문, #768 원 실측: 3×3.
- 비용·시간·cache 수치(이번 위임 실행 1회): 원문에 없음. 이슈 본문은 이 실행의 결과를 완료 조건으로만 적고 있어요.

## 한계

- 이슈 본문은 #793 마무리 실측을 Claude 위임 1회와 Codex 격리 1회로 적고 있어요.
- 이슈 본문은 패널 관찰 두 가지가 n=1이라고 명시하고 있어요.
