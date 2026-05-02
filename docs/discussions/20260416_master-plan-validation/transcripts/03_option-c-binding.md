# Transcript 03 — Note-Project Binding 옵션 C(유지+강한 링크) 건전성

**[Moderator]**: note → project 승격 시 **이동 vs 복사 vs 유지+링크** 중 옵션 C 선택이 타당한가.

**[Knowledge Management Expert]**: **강한 찬성**. Zettelkasten·Roam·Logseq 전통에서 atomic note 불변성은 핵심 원칙. 옵션 A(이동)는 PARA 방법론과 충돌 — PARA는 프로젝트 종료 시 Area/Resource 복귀를 전제하는데 이동은 복귀 경로 파괴.

**[Project Manager]**: 실무도 같은 결론. 한 note가 여러 프로젝트에 쓰이는 경우가 빈번. 이동은 N:N을 1:1로 강제.

**[Critical Practitioner]**: "두 곳을 볼 필요" 단점이 과소 평가. Obsidian graph에서 노드가 다중 폴더에 속한 것처럼 보이면 인지 부하. 또 `absorbs` vs `related_notes` 의미 차이가 미묘 — 1년 후 본인도 구별 못 할 수 있다.

**[Optimistic Practitioner]**: Dataview 쿼리로 "project X 관련 모든 note" 집계 가능. 두 곳 보는 부담은 툴링으로 흡수.

**[LLM Orchestration Expert]**: `promoted_to_project` 단일/다중 미해결. 권고: **단일값(primary origin) + `also_related_projects` 배열(보조)**. LLM audit 일관 처리를 위해 의미 명확화.

**[DX/Tooling Expert]**: `absorbs` vs `related_notes` 구분 근거를 현재 plan이 주석 1줄로만 제시. 부족. **Field dictionary 섹션**으로 필드별 정의·예시·사용 시점을 명문화해야.

**[KM]**: 동의. Dataview 쿼리 예시도 binding plan에 포함하면 실사용 패턴 입증 가능.

**[Moderator]**: 정리: (a) 옵션 C 유지, (b) `promoted_to_project` 단일 + `also_related_projects` 배열, (c) `absorbs` = 탄생 기반 note(1–2개 통상), `related_notes` = 작업 참조(N개), (d) Binding plan에 field dictionary + Dataview 예시.

**전원 합의.**

**결론**: 합의. 옵션 C 채택 확정 + 필드 명문화 보강.
