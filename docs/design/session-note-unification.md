# Session-Note 통합 설계안

> 작성일: 2026-04-12
> 도출 과정: Unknown Discovery (7개 발견) → Expert Panel (6개 합의) → Doc Concretize
> **2026-04-13 업데이트**: `vault-daily` 스킬이 제거되어 `daily` 타입은 더 이상 생성되지 않습니다. 본 문서의 `daily` 관련 항목은 과거 설계 기록으로 보존.
> **2026-04-13 업데이트**: `vault-reader` 플러그인이 `vault-bridge` v1.0.0으로 리네이밍되었습니다. 본문의 `vault-reader` 참조는 과거 설계 기록으로 보존.

## 1. 문제 정의

### 1.1 현행 구조

세션 기록이 두 플러그인에 걸쳐 분산되어 있다.

| 컴포넌트 | 위치 | 방향 | 실행 환경 |
|---------|------|------|----------|
| wrapup (스킬) | OVM | 과거 (뭘 했나) | vault 내부 전용 |
| handoff (Mode 4) | vault-reader | 미래 (뭘 해야 하나) | 외부 프로젝트 |

### 1.2 발견된 문제

**구조적 문제**:
- wrapup은 명확한 시나리오 없이 설계되었고, 실사용률이 사실상 0
- "wrapup 먼저 → handoff 다음" 순서는 실행 환경이 달라 한 세션에서 실현 불가
- handoff 템플릿에 이미 "Done This Session" 섹션이 존재하여 과거 요약을 부분적으로 커버

**사용자 경험 문제**:
- vault 전용 설계로 개발 프로젝트에서 접근 불가
- wrapup/handoff 분리로 "어떤 걸 써야 하나" 판단 비용 발생, 결국 둘 다 안 쓰게 됨
- "handoff"라는 이름이 단순 기록 시나리오에 부자연스러움

**아키텍처 문제**:
- 동일한 "세션 기록 → vault 저장" 기능이 두 플러그인에 분산 (단일 책임 위배)
- vault-reader의 "vault만 접근" 제약과 프로젝트 파일 추적 간 긴장

## 2. 결정 사항

| # | 결정 | 합의 | 근거 |
|---|------|------|------|
| 1 | OVM wrapup 스킬 제거 | 4:1 | 실사용률 0, handoff와 기능 중복 |
| 2 | "handoff" → "session-note" 리네이밍 | 5:0 | 단순 기록 시나리오 배제하는 네이밍 한계 |
| 3 | session-note는 연속 작업 유무에 따라 모드 분기 | 5:0 | 과거/미래를 단일 컨셉으로 통합 |
| 4 | 실행 위치는 vault-reader | 5:0 | 외부 프로젝트 접근성 확보 |
| 5 | vault-reader의 vault 전용 제약 유지, 대화 컨텍스트 수집 | 5:0 | 보안 원칙 유지 |
| 6 | 습관 형성을 위한 Stop hook 자동 제안 | 5:0 | 기능만으로 습관 형성 불가 |
| 7 | vault 전체 파일명/frontmatter 통일 | 사용자 확인 | 타입 우선 네이밍 + created/tags/type 표준 |

## 3. Vault 파일 생성 규칙 (통일안)

### 3.1 파일명 컨벤션

**형식**: `{type}-YYYY-MM-DD[-{topic}][-vN].md`

| 타입 | 파일명 예시 | 저장 경로 |
|------|------------|----------|
| `session` | `session-2026-04-12.md` | `00_Inbox/` 또는 `20_Projects/{name}/` |
| `capture` | `capture-2026-04-12-api-changes.md` | `00_Inbox/` |
| `daily` | `daily-2026-04-12.md` | `00_Inbox/` |
| `note` | `{topic}.md` (날짜 없음) | `30_Notes/` |
| `project` | `_index.md` (고정) | `20_Projects/{name}/` |

- topic은 kebab-case, 2-3 단어
- 동일 날짜 중복: `-v2`, `-v3` 순으로 증분
- `30_Notes/`의 note와 `20_Projects/`의 _index.md는 기존 규칙 유지

### 3.2 Frontmatter 표준

```yaml
---
created: YYYY-MM-DD                       # 필수: 모든 파일
tags: [{type}, {domain/project}]          # 필수: 파일 유형 + 도메인/프로젝트
type: session | capture | daily | note | project  # 필수: 파일 유형 식별자
status: active | archived                # 조건부: session(handoff 모드), project에서만
---
```

### 3.3 변경 영향

| 컴포넌트 | 현행 | 변경 후 |
|---------|------|--------|
| capture | `YYYY-MM-DD-{topic}.md` | `capture-YYYY-MM-DD-{topic}.md` |
| ~~wrapup~~ | `YYYY-MM-DD-session-wrapup.md` | 삭제 → session-note로 통합 |
| vault-daily | `YYYY-MM-DD-daily.md` | `daily-YYYY-MM-DD.md` |
| handoff → session | `handoff-YYYY-MM-DD.md` / `YYYY-MM-DD-handoff.md` | `session-YYYY-MM-DD.md` |
| note | `{topic}.md` | 변경 없음 (type frontmatter만 추가) |
| project | `_index.md` | 변경 없음 (type frontmatter만 추가) |

## 4. session-note 설계

### 4.1 모드 분기

| 조건 | 모드 | 포함 섹션 |
|------|------|----------|
| 연속 작업 없음 | `record` | Summary, Done, Related Files, Reference Context |
| 연속 작업 있음 | `handoff` | Summary, Done, In Progress, Blockers, Next Steps, Related Files, Reference Context |
| 빠른 기록 | `quick` | Summary, Related Files (+ Next Steps if handoff) |

### 4.2 AskUserQuestion 사용 시점

```
[Step 1] 모드 선택 ─── AskUserQuestion
         "어떤 형식으로 기록할까요?"
         - [작업 기록] record 모드 (연속 작업 없음)
         - [인수인계] handoff 모드 (다음 세션에서 이어갈 작업 있음)
         - [간단히]   quick 모드
              ↓
[Step 2] 컨텍스트 수집 ─── 자동
              ↓
[Step 3] 초안 작성 ─── 자동
              ↓
[Step 4] 저장 확인 ─── AskUserQuestion
         "이 내용으로 저장할까요?"
         - [저장] / [수정 후 저장] / [취소]
```

### 4.3 템플릿

```markdown
---
created: YYYY-MM-DD
tags: [session, {project-or-domain}]
type: session
status: active                 # handoff 모드에서만
---
# Session Note — {title} (YYYY-MM-DD)

## Summary
{2-3줄 요약}

## Done This Session
- {완료 작업}

## In Progress                  # handoff 모드 전용
- [ ] {미완료 작업 — 진행 정도 명시}

## Blockers / Warnings          # handoff 모드 + 존재 시
- {제약, 이슈, 의존성}

## Next Steps                   # handoff 모드 전용
1. {구체적, 실행 가능한 항목}

## Related Files
- [[path/to/file]] — {역할/변경 내용}

## Reference Context
{배경 지식, 결정사항, 논의 내용}
```

### 4.4 트리거

```
기존 유지: "create handoff", "save handoff", "prepare for next session"
신규 추가: "세션 정리", "작업 기록", "오늘 작업 저장", "session note",
          "세션 노트", "기록 남겨줘", "세션 저장"
```

### 4.5 파일명 및 저장 경로

```
프로젝트 연결:  ~/vault/20_Projects/{name}/session-YYYY-MM-DD.md
Inbox 저장:    ~/vault/00_Inbox/session-YYYY-MM-DD.md
동일 날짜:     session-YYYY-MM-DD-v2.md
```

### 4.6 하위 호환성

Mode 1 (Restore)에서 검색 패턴 확장:
```
기존: handoff-*.md, *-handoff.md
추가: session-*.md
```

## 5. Stop Hook 설계

### 5.1 트리거 조건

- 대화 턴 5회 이상 (단순 질의응답 제외)
- 또는 파일 수정/생성이 있었을 때

### 5.2 UX (AskUserQuestion 기반)

```
세션을 종료하기 전에 — session note를 vault에 저장할까요?

[네, 기록]   전체 session-note 생성 (모드 선택 포함)
[간단히]     quick 모드로 요약만 저장
[건너뛰기]   기록 없이 종료
```

### 5.3 구현 위치

vault-reader 플러그인의 Stop hook으로 구현.

## 6. 변경 파일 목록

### 삭제
- `obsidian-vault-manager/skills/wrapup/SKILL.md`

### 수정
| # | 파일 | 작업 |
|---|------|------|
| 1 | `vault-reader/agents/vault-searcher.md` | Mode 4 전면 개편 + Mode 1 패턴 확장 |
| 2 | `ovm/skills/capture/SKILL.md` | 파일명 패턴 + frontmatter 변경 |
| 3 | `ovm/skills/vault-daily/SKILL.md` | 파일명 패턴 + wrapup 참조 제거 + frontmatter |
| 4 | `ovm/skills/note/SKILL.md` | frontmatter에 type 추가 |
| 5 | `ovm/skills/project/SKILL.md` | frontmatter에 type 추가 |
| 6 | `ovm/agents/vault-knowledge-manager.md` | wrapup 참조 제거 + 네이밍 규칙 반영 |
| 7 | `ovm/agents/vault-file-organizer.md` | 네이밍 규칙 반영 |
| 8 | `ovm/.claude-plugin/plugin.json` | keywords 갱신 |
| 9 | `vault-reader/.claude-plugin/plugin.json` | keywords 갱신 |
| 10 | `.claude-plugin/marketplace.json` | 버전 범프 |
| 11 | `CLAUDE.md` | MECE 경계 갱신 |

### 신규
- vault-reader Stop hook 설정

## 7. 후속 과제 (별도 이슈)

| # | 이슈 | 설명 |
|---|------|------|
| 1 | OVM 스킬 재정비 | vault-daily 제거 검토 + OVM 핵심 스킬 재정의 |
| 2 | OVM vault 내부 세션 기록 | vault 에이전트 환경에서의 세션 기록 경로 결정 |
| 3 | 기존 handoff 파일 호환 | 1개뿐이므로 검색 패턴 확장으로 대응 |
