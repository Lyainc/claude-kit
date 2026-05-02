# TOPIC 1: 쓰기 role 공식화 (P1)

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing
**[Optimistic Practitioner]**: vault-searcher description은 이미 session-note 쓰기를 선언. 문제는 샌드박스에서 권한 미활성. 선언+manifest 동기화만 하면 됨.

**[Critical Practitioner]**: "이미 쓴다"는 선언 자체가 혼란 유발. `Only create new files` 원칙과 실제 샌드박스 권한 불일치가 진짜 버그.

## Q&A
**[Claude Code Platform Expert]**: 원인 후보 — (a) agent frontmatter에 `Write` tool 누락, (b) 플러그인 샌드박스가 `~/vault/` 기본 차단. 재현 후 특정 필요. 해결: frontmatter `tools:` 명시 + plugin manifest에서 vault 경로 허용 선언.

**[Plugin Architecture Expert]**: 쓰기 범위를 description에 못 박아야. 현재 "create only"는 모호. 4-tier 제안:
- 허용: `00_Inbox/**` 신규, `20_Projects/{linked}/**` 신규 (`.vault-link` 바인딩만)
- 금지: `30_Notes/` 수정, 모든 덮어쓰기, append

**[Knowledge Management Expert]**: `30_Notes/` 금지 동의. 도메인 지식 영역은 OVM(vault-knowledge-manager) 책임. bridge는 원재료(capture, session, artifact)만.

**[Critical Practitioner]**: 덮어쓰기 엄격? 같은 날짜 재저장은?
**[Knowledge Management Expert]**: `-v2`, `-v3` 컨벤션으로 신규 파일. 덮어쓰기 절대 금지 — 실수 복구 불가.

## Dialectic
**Thesis**: 선언-권한 동기화만.
**Antithesis**: 범위 명세 없으면 scope creep 재발.
**Synthesis**: 4-tier 명세 + 권한 선언 이중화 + 샌드박스 검증.

## 결론
- 4-tier 쓰기 범위 description에 명시
- agent frontmatter `tools:` + plugin manifest 양쪽에 Write 명시
- 샌드박스 vault 경로 허용 검증 (이번 실패 재현 후)
- 동일 날짜는 `-v2`, `-v3` 신규 파일, 덮어쓰기 절대 금지
