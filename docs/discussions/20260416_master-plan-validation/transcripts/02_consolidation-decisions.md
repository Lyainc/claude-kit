# Transcript 02 — 중복/통폐합 결정의 합리성

**[Moderator]**: 5개 문서 아카이브 + 10개 문서 `consolidates` 필드 지칭 결정이 합리적인지.

**[Knowledge Management Expert]**: 아카이브 5개는 모두 완료 작업의 계획서. `superseded_by` + `archive_reason` 보존이 best practice. 삭제 아닌 아카이브는 지식 관리상 정답.

**[Project Manager]**: 그러나 `consolidates` 필드가 의미 이중성. 10개 중 6개는 여전히 "살아있는 참조 문서"로 active. 흡수(dead)와 참조(living)를 한 필드가 섞어 표현. 필드 분리 권고: `references_active` + `supersedes_archived`.

**[Critical Practitioner]**: "실제 코드 중복은 거의 없다"는 판정이 낙관적. stop-hook-rewrite의 Phase F/G와 cleanup-v3의 PR-B는 **동일 작업을 다른 번호체계**로 기술. 문서 간 합의 없이 병렬 작성된 흔적. 재발 위험.

**[Optimistic Practitioner]**: 과거 이슈. 앞으로는 Master Plan의 W0–W8 통일 번호 쓰니 재발 없음.

**[DX/Tooling Expert]**: 통일을 실제로 보장하려면 **신규 plan 생성 시 `parent` + `workstream` 필수 필드**가 규약으로 필요. 현재 두 신규 plan은 parent만 있고 workstream ID 없음.

**[KM Expert]**: DX 제안 동의. 지식 관리에서 ID 체계는 규약으로 강제해야 유지됨.

**[PM]**: 모두 동의.

**[Moderator]**: 정리: (a) `consolidates` → `references_active` + `supersedes_archived` 분리, (b) 신규 plan에 `workstream` 필수 필드, (c) Master Plan에 "이 ID 체계 준수" 규약 명시.

**전원 합의.**

**결론**: 합의. 프런트매터 필드 분리 및 workstream ID 규약 도입.
