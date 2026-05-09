# vault-bridge 쓰기 문제점 개선 — 전문가 패널 요약

**날짜**: 2026-04-13
**패널**: Moderator, Optimistic/Critical Practitioner, Claude Code Platform Expert, Plugin Architecture Expert, UX/DX Expert, Knowledge Management Expert
**토픽 수**: 4 (모두 합의)

## 배경

이번 세션에서 vault-bridge 사용 중 드러난 3가지 pain point:
1. **P1 쓰기 실패**: session-note 저장 시 vault-searcher가 권한 거부, 메인 에이전트가 대신 씀 → 라우팅 무너짐
2. **P2 UX 일관성 부재**: Mode 선택/저장 확인이 AskUserQuestion 아닌 plain text 대화로 진행
3. **P3 artifact 자동 정리 부재**: 메인이 생성한 discussion docs 등이 vault로 자동 편입되지 않음

## 합의 결론

### 1. 쓰기 role 공식화 (P1)
- **4-tier 쓰기 범위 명시**:
  - 허용: `00_Inbox/**` 신규, `20_Projects/{linked}/**` 신규 (`.vault-link` 바인딩 시)
  - 금지: `30_Notes/` 수정 (OVM 책임), 모든 덮어쓰기, append
- **권한 선언 이중화**: agent frontmatter `tools:` + plugin manifest 양쪽에 Write 명시
- **샌드박스 검증**: 이번 실패 재현 후 vault 경로 허용 정책 확인
- **동일 날짜 충돌**: `-v2`, `-v3` 컨벤션으로 신규 파일 (덮어쓰기 절대 금지)

### 2. AskUserQuestion 기반 UX (P2)
- **이산 선택**: Mode 선택(record/handoff/quick), 저장 확인(save/edit/cancel) → AskUserQuestion 강제
- **자유 지시**: 수정 내용, 커스텀 태그 등 → plain text 유지
- **하이브리드 패턴**: 수정 요청도 "어느 섹션?"(옵션) → 섹션 수정 지시(자유) 2단계
- **skill body에 anti-pattern 명시**: "`record/handoff/quick 중 골라주세요` 같은 plain text 질문 금지"
- **Hook 검증은 포기**: 비용 대비 효과 낮음, 문서 강제 + 리뷰 의존

### 3. Mode 4 일반화: vault write (P3)
Mode 4 역할 확장: "session note" → "vault write (session + artifact)"

**입력**: 본문 + (선택) 힌트(프로젝트명, 타입)
**처리**:
1. skim → type 분류 (session / capture / note / project)
2. frontmatter 자동 생성 (rule-based 우선, LLM skim 보조)
3. 파일명 컨벤션 (`{type}-YYYY-MM-DD[-topic][-vN].md`)
4. 경로 결정: `.vault-link` 있으면 `20_Projects/{linked}/` 후보, 없으면 `00_Inbox/`
5. AskUserQuestion으로 경로/파일명/frontmatter 확인 (dry-run diff)
6. 쓰기

**원칙**:
- **자동 감지 금지, 명시 요청만** (hook 기반 hot-pickup은 inbox 범람 위험)
- **새 Mode 번호 금지** — 기존 4-mode 유지, Mode 4 내부 서브플로우로 분기
- **bridge/OVM 경계**: bridge = frontmatter+경로+쓰기 / OVM = 내용 재구성·MOC·wikilink

### 4. 쓰기 위임 인터페이스 원칙
- vault 쓰기의 **단일 진입점 = vault-bridge** (메인 직접 Write는 anti-pattern)
- bridge 실패 시 **구조화 에러** 반환: `{kind: "permission" | "path_invalid" | "convention_violation", detail: "..."}`
- 메인은 사용자에게 투명 보고 + 3-옵션 fallback (재시도 / 메인 직접 쓰기 / 취소)
- fallback은 **예외 경로**, 패턴화 금지

## 실행 순서

1. **[blocker]** vault-bridge 쓰기 권한 샌드박스 정책 재현·fix — 이게 안 되면 나머지 전부 무효
2. `vault-bridge/agents/vault-searcher.md` description 업데이트 (4-tier 쓰기 범위 + 결정 로직)
3. `vault-bridge/.claude-plugin/plugin.json` allowed-tools에 Write 명시 확인
4. `vault-bridge/skills/save-session/SKILL.md` 리팩터 (AskUserQuestion 강제 + anti-pattern 예시)
5. Mode 4 일반화: vault-searcher description에 artifact filing 서브플로우 추가
6. 구조화 에러 반환 포맷 명세 (vault-searcher description에 포함)
7. 경계 테스트 시나리오 문서화 (inbox 신규 / project 신규 / notes 거부 / 덮어쓰기 거부 / bridge 실패→메인 fallback)

## 액션 아이템

- [ ] `vault-bridge/agents/vault-searcher.md`: 쓰기 범위·Mode 4 일반화·구조화 에러 포맷 업데이트
- [ ] `vault-bridge/.claude-plugin/plugin.json`: Write tool 명시 + vault 경로 허용 검증
- [ ] `vault-bridge/skills/save-session/SKILL.md`: AskUserQuestion 강제 + anti-pattern 예시
- [ ] 경계 테스트 케이스 문서화 (새 파일 또는 vault-searcher reference)
- [ ] README에 bridge/OVM 쓰기 책임 경계 표 추가

## 합의 상태
- TOPIC 1 (쓰기 role 공식화): 만장일치
- TOPIC 2 (AskUserQuestion UX): 만장일치
- TOPIC 3 (Mode 4 일반화): 만장일치
- TOPIC 4 (쓰기 위임 인터페이스): 만장일치

---
*4개 토픽 논의 완료 · 4개 합의, 0개 보류 · 미해결 3건 UNRESOLVED.md 참조*
