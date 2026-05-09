# Topic 4: SKILL.md Slimming + Reference Lazy Loading

**Date**: 2026-04-16
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Cost/Infra Expert, Plugin Architect, UX Expert

---

**[Optimistic Practitioner]**: thinking-tools의 SKILL.md들이 180-270줄이고, reference.md가 12-16KB다. 스킬 호출 시 SKILL.md 전체가 context에 로드되므로, 핵심만 남기고 reference를 선택적으로 Read하면 초기 context를 30-40% 줄일 수 있다.

**[Critical Practitioner]**: Claude Code의 스킬 로딩 메커니즘을 정확히 이해해야 한다. SKILL.md만 자동 로드되고, reference.md는 SKILL.md에서 참조할 때만 별도로 Read된다. reference.md는 이미 선택적 로드 구조다. 실제로 줄여야 할 것은 SKILL.md 본문 자체의 길이다.

**[Plugin Architect]**: 현재 구조를 보면 SKILL.md에 `reference/`를 링크로 참조하고 있다. 문제는 SKILL.md 자체에 상세한 절차, 예시, 템플릿이 포함되어 있는 것이다. 예를 들어 expert-panel SKILL.md에 토론 구조, 합의 규칙, 출력 포맷이 모두 있다. 줄이면 스킬 실행 품질이 직접적으로 영향받는다.

**[Cost/Infra Expert]**: 정량화하면, SKILL.md 200줄은 약 3-4K 토큰이다. 세션 전체 context 150K 대비 2-3%에 불과하다. SKILL.md를 절반으로 줄여도 1.5-2K 토큰 절감이고, >150k context 문제에 거의 영향이 없다. 진짜 context를 잡아먹는 건 토론 transcript, 코드 파일 읽기 등 작업 중 생성되는 내용이다.

**[UX Expert]**: SKILL.md가 상세할수록 스킬의 실행 품질이 높아진다. 특히 expert-panel이나 unknown-discovery 같은 복잡한 스킬은 절차적 지시가 품질을 결정한다. 줄이면 출력 일관성이 떨어질 수 있다.

---

**결론**: 합의 -- 현행 유지 권장
- SKILL.md는 전체 context의 2-3%에 불과하여 슬림화 효과 미미
- reference.md는 이미 선택적 로드 구조
- SKILL.md 축소 시 스킬 실행 품질 저하 리스크
- **우선순위: 보류 (Low impact, Medium risk)**
