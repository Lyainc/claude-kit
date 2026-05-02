# Topic 2: vault-knowledge-manager Sonnet → Haiku Downgrade

**Date**: 2026-04-16
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Cost/Infra Expert, Plugin Architect, UX Expert

---

**[Optimistic Practitioner]**: vault-knowledge-manager의 핵심 로직은 스킬에 위임된다. note 스킬이 도메인 분류를, context 스킬이 컨텍스트 로드를 담당한다. 에이전트 자체는 "어떤 스킬을 호출할지"와 "사용자 확인"을 조율하는 역할이므로 Haiku로 충분할 수 있다.

**[Critical Practitioner]**: facilitator와 본질적으로 다르다. vault-knowledge-manager는 12개 도메인 분류법을 기반으로 노트를 적절한 위치에 배치하고, MOC 링크를 생성하며, 프로젝트 구조를 관리한다. "A or B 중 선택"이 아니라 "사용자의 의도를 해석해서 vault 구조에 맞게 매핑"하는 작업이다. 예를 들어 "API 설계 노트"가 `dev-backend`인지 `architecture`인지 판단하는 건 맥락 이해가 필요하다.

**[Plugin Architect]**: vault-knowledge-manager는 `memory: project` 설정이 있다. 프로젝트 컨텍스트를 누적 기억하면서 일관된 판단을 해야 한다는 뜻이다. Haiku의 프로젝트 메모리 활용 능력이 Sonnet과 동등한지 확인 필요. 또한 "파일 작업 전 사용자 확인"이 필수인데, 확인 프롬프트의 품질도 모델 능력에 영향받는다.

**[Cost/Infra Expert]**: vault-knowledge-manager는 facilitator보다 호출 빈도가 낮다. vault 작업 세션에서만 사용되고, 전체 세션의 20-30% 정도로 추정된다. 절대적 절감액이 facilitator보다 작다.

**[UX Expert]**: vault 관리는 사용자의 지식 자산을 다루는 작업이다. 노트가 잘못된 도메인에 분류되거나 MOC 링크가 부정확하면 나중에 정보를 찾지 못하는 결과로 이어진다. 라우팅 실패(재시도 가능)와 달리 발견이 어렵고 누적되는 오류다. 품질 저하 리스크가 높다.

**[Critical Practitioner]**: 대안으로 단순 작업(capture, inbox-review)에서만 Haiku를 사용하고 복잡한 작업에서는 Sonnet을 유지하는 조건부 라우팅을 제안한다.

**[Plugin Architect]**: Claude Code 에이전트는 호출 시점에 모델이 고정된다. 작업 유형별로 모델을 바꾸려면 에이전트를 두 개로 분리해야 하는데, 복잡도를 높이고 MECE 경계를 흐린다. 현실적이지 않다.

---

**결론**: 합의 -- Sonnet 유지 권장
- 비용 절감 효과가 제한적 (vault 세션만 해당)
- 도메인 분류/MOC 품질 저하 리스크가 높음
- 에이전트 분리는 구조적 복잡도 증가
- **우선순위: 보류 (High risk, Low impact)**
