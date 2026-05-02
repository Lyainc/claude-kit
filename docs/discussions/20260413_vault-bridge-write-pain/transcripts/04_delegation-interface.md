# TOPIC 4: 쓰기 위임 인터페이스 원칙

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing
**[Plugin Architecture Expert]**: vault 쓰기 단일 진입점 = vault-bridge. 메인이 직접 Write에 vault 경로 쓰는 건 anti-pattern.

## Q&A
**[Optimistic Practitioner]**: 이번 세션 fallback으로 메인이 직접 썼음. 이걸 패턴화하면 어떤가?

**[Critical Practitioner]**: fallback 패턴화 시 라우팅 무너짐. bridge 존재 이유 사라짐. fallback은 **예외 경로**로만.

**[Claude Code Platform Expert]**: bridge 실패 시 **구조화 에러**: `{kind: "permission" | "path_invalid" | "convention_violation", detail: "..."}`. 메인은 사용자에게 투명 보고.

**[UX/DX Expert]**: 에러 메시지 템플릿화. "vault-bridge가 {kind} 이유로 실패. (a) 재시도 (b) 메인이 직접 쓰기 (c) 취소."

**[Plugin Architecture Expert]**: fallback (b) 선택 시에도 경고 로그 남김 — 라우팅 우회 기록.

## Dialectic
**Thesis**: fallback 자유화.
**Antithesis**: fallback 금지.
**Synthesis**: fallback은 예외 경로, 사용자 명시 선택 + 로그.

## 결론
- vault 쓰기 단일 진입점 = vault-bridge
- 실패 시 구조화 에러 반환 (kind + detail)
- 메인은 투명 보고 + 3-옵션 사용자 선택 (재시도 / 직접 쓰기 / 취소)
- fallback 선택 시 경고 로그
- fallback 패턴화 금지
