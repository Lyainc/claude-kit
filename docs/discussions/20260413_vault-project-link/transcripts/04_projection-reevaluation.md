# TOPIC 4: On-demand projection (옵션 B) 재평가

**상태**: 합의 (만장일치, 스코프 아웃)
**라운드**: 1

## Briefing

**[LLM Orchestration Expert]**: projection이 정말 필요한가? vault-searcher Mode 1/2/3이 이미 read 제공. projection은 "IDE에서 파일로 열고 싶다"는 UX 욕구만 커버.

## Q&A

**[Optimistic Practitioner]**: Obsidian 창 띄우면 해결됩니다. 코드·문서 side-by-side는 WM 영역이지 파일시스템 영역이 아닙니다.

**[DX/Tooling Expert]**: 동의. 오버엔지니어링. 캐시 무효화, writeback 정책, 머지 충돌 — 복잡성 폭발합니다.

**[Critical Practitioner]**: writeback 없는 read-only로 제한해도 캐시 stale 문제 남습니다. 필요해지면 나중에.

**[Knowledge Management Expert]**: projection은 "vault를 repo 안으로 끌어오려는" 심볼릭 발상의 재현입니다. 문화 가이드(C)와 충돌합니다.

## Dialectic

**Thesis**: MVP에 B 포함.
**Antithesis**: B 스코프 아웃.
**Synthesis**: B 제거. MVP = A(pointer) + C(문화 가이드)만.

## 결론

Projection 기능 스코프 아웃. 향후 실사용 시 "IDE에서 직접 열고 싶다"는 구체 요구가 반복 제기될 때 재검토.
