# TOPIC 3: vault-bridge 책임 경계

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing

**[Critical Practitioner]**: 초안은 vault-bridge가 심볼릭 생성까지 담당. 포인터 파일로 바뀐 지금, 생성·관리·validation 중 어디까지가 vault-bridge인가?

**[Optimistic Practitioner]**: 소비는 명백히 내부, 생성은 경계 이슈.

## Q&A

**[LLM Orchestration Expert]**: vault-bridge 현재 role = I/O serving (read + session-note write). 포인터 **소비**는 role 내부 (vault-searcher 스코프 결정). **생성**은 role 바깥.

**[DX/Tooling Expert]**: 생성은 `/vault-link` slash command로 분리. 에이전트 아님 — 1회성 세팅이라 오버엔지니어링. 하위 명령: `init`, `status`, `fix`.

**[Knowledge Management Expert]**: `init`이 vault에 대응 폴더가 없을 때 obsidian-vault-manager의 `project` 스킬을 호출해 자동 생성? 크로스 플러그인 암묵 호출은 기존 패턴에 없습니다.

**[Critical Practitioner]**: 암묵 호출 금지. "`/ovm project create` 먼저 실행해주세요" 사용자 안내만. scope creep의 입구를 열지 않습니다.

**[Security Expert]**: `.gitignore` 수정은 제안만, 강제 금지. 사용자 repo에 쓰기를 암묵적으로 감행하면 신뢰 파괴.

## Dialectic

**Thesis**: vault-bridge가 생성까지 소유.
**Antithesis**: 생성은 OVM 위임 또는 사용자 수동.
**Synthesis**: vault-bridge는 포인터 소비 + `/vault-link` command까지 소유. vault 폴더 생성은 OVM 안내. repo 파일 수정은 제안만.

## 결론

| 항목 | 소유 |
|------|------|
| 포인터 소비 (자동 스코프) | vault-bridge |
| `/vault-link` slash command | vault-bridge |
| vault 프로젝트 폴더 생성 | OVM 위임 (사용자 안내) |
| 심볼릭 생성 | (기각) |
| repo `.gitignore` 수정 | 제안만 |
