# Transcript — Topic 2: improvement-matrix.md 경로·거버넌스·업데이트

**Date**: 2026-04-19
**Topic**: 신규 living 문서의 경로 선택, 오너십, 업데이트 메커니즘 설계
**Round**: 1 (합의 도달)

---

## Briefing

**[Optimistic Practitioner]**: 경로는 `thinking-tools/docs/improvement-matrix.md`가 정답이에요. 스코프 근접성(Doc Expert 원칙)과 청자 분리(Plugin Expert)가 모두 이 위치를 가리켜요. 거버넌스는 Doc Expert의 frontmatter 스키마 + OSS의 3계층 + CODEOWNERS로 충분히 명시할 수 있어요.

**[Critical Practitioner]**: 경로보다 거버넌스 부재가 더 큰 위험이에요. PR 단위 업데이트는 인센티브가 없어요 — 작성자가 코드만 고치고 매트릭스는 그냥 안 건드림. Phase 완료 단위는 추적 주체가 누군지 불명확. 오너 1명 지정 + 분기별 리뷰 + PR 템플릿 체크박스 셋 다 없으면 경로·이름 논의는 의미 없어요. 매트릭스가 stale 마커 없이 썩는 게 OSS 실패 패턴 1순위예요.

## Q&A

**[Moderator]**: Doc Expert, frontmatter 스키마 구체안 말씀해주세요.

**[Technical Documentation Expert]**: 다음 필드가 필수예요.

```yaml
---
title: Thinking-Tools Improvement Matrix
type: living-reference
status: active          # active | superseded | archived
version: 0.3.0          # semver, 엔트리 구조 변경 시 major
schema_version: 1
last_reviewed: 2026-04-19
owners: [thinking-tools]
source_discussions:
  - docs/discussions/20260419_ouroboros-integration/
---
```

엔트리 구조에서 가장 중요한 건 **ID 재활용 금지**예요. W1·D1 같은 ID는 외부 링크 안정성을 위해 삭제해도 번호 비워야 해요. PR이나 commit message에서 "W3 해결"이라고 쓰는데 나중에 W3가 다른 항목으로 재할당되면 history가 거짓말하게 돼요. 엔트리는 `id`, `status: open|in-progress|resolved|wontfix`, `priority`, `resolved_in: v1.2.0`, `supersedes: <old_id>` 필드 보유.

**[OSS Maintainer Expert]**: 거버넌스에서 핵심은 **3계층 분리 명문화**예요. Issues는 원자 작업, matrix는 테마·우선순위·분기, CHANGELOG는 릴리스 기록(과거). matrix가 Issues를 중복 추적하면 동기화 실패로 둘 다 거짓말쟁이 돼요. matrix 엔트리는 "이 테마에 대해 우리는 이런 우선순위로 갈 것"이고, 실제 작업 추적은 Issue 링크로 위임해야 해요. CODEOWNERS에 `thinking-tools/docs/ @maintainer` 명시해서 PR 리뷰 자동 할당. 그리고 README에 한 줄: "matrix는 미래 계획, CHANGELOG는 과거 릴리스 — 시간축이 다름."

**[Plugin Ecosystem Expert]**: 보충해요. 매트릭스가 user-facing이라면 plugin install된 사용자도 봐요. 사용자는 "이 플러그인이 어디로 가는지" 보고 싶어할 수 있지만, 동시에 W(약점)를 노출하는 건 상품 신뢰도 측면에서 부담이에요. 매트릭스 항목 진척 시 thinking-tools `plugin.json` minor 범프 + CHANGELOG 갱신 룰을 thinking-tools 내부 CONTRIBUTING이나 README에 명시 안 하면 매트릭스가 진척돼도 SemVer 누락 위험이 있어요.

**[Critical Practitioner]**: 그 user-facing 이슈가 진짜 문제 같아요. 매트릭스가 약점 8개를 노출하면, 처음 install하는 사람은 "이 플러그인 문제 많네"라고 받아들일 수 있어요. 이건 어떻게 해결하나요?

**[Plugin Ecosystem Expert]**: **W 섹션과 D 섹션 청자 분리**가 답이에요. 같은 파일 내에서 헤더로 명시:
```markdown
# Improvement Matrix

## Strategic Directions (M1-M5) — for users and contributors
[방향성 표 — 미래 계획, 긍정적 톤]

## Internal Weaknesses (W1-W8) — for contributors
[약점 매트릭스 — 진단, 솔직한 톤]
```

또는 더 보수적으로 가려면 W 섹션을 별도 파일(`thinking-tools/docs/internal/weaknesses.md`)로 분리. 단 분리 시 동기화 비용 증가. 같은 파일 + 섹션 구분이 1차 권고예요.

**[Critical Practitioner]**: 그 정도면 우려 해소돼요. 단 PR 트리거를 확실히 못 박아주세요 — "matrix 항목 status 변경 시 PR 체크리스트 필수 항목"으로요.

## Dialectic

**[Thesis — Optimistic]**: `thinking-tools/docs/improvement-matrix.md` + Doc Expert frontmatter + OSS 3계층 거버넌스.

**[Antithesis — Critical]**: PR 인센티브 부재 + user-facing W 섹션 우려.

**[Synthesis]**: 위 패키지에 다음 추가:
- W vs D 섹션 분리 (같은 파일, 헤더 명시)
- PR 템플릿 체크박스: "matrix 항목 변경 동반 갱신했는가"
- CHANGELOG 트리거 룰 thinking-tools README에 명시
- CODEOWNERS 등록

## 결론

**합의 (조건부)**: 경로 + 거버넌스 패키지 채택. 5개 조건 (frontmatter 스키마, ID 재활용 금지, CODEOWNERS, CHANGELOG 트리거, W/D 섹션 분리) 동시 도입.

**Confidence**: High (5명 전원)
