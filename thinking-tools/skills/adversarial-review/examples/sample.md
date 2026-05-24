# Adversarial Review — Session Example

Full example showing the complete Phase 0 → Phase 1 → Phase 2 flow for a single claim.
See the main [SKILL.md](../SKILL.md) for the core workflow and [reference/patterns.md](../reference/patterns.md) for attack templates.

---

## Example: "마이크로서비스가 모놀리식보다 항상 낫다"

```
User: "마이크로서비스가 모놀리식보다 항상 낫다는 주장을 검증해줘"

→ Phase 0: Steelman 3개 후보 생성 → 사용자가 최강판 선택
   후보 A (실용 프레이밍): "팀 규모가 일정 이상인 조직에서 마이크로서비스는 배포 독립성과 장애 격리 면에서 모놀리식보다 우월하다"
   후보 B (원칙 프레이밍): "소프트웨어 복잡성 증가에 따라 관심사 분리를 물리적 경계로 강제하는 마이크로서비스가 장기적으로 유지보수성이 높다"
   후보 C (실증 프레이밍): "Netflix/Amazon 사례에서 검증된 것처럼, 고부하 분산 서비스에서 마이크로서비스는 확장성 병목을 제거한다"
   → 사용자가 후보 A 선택 (Attack Target 확정)

→ Phase 1 Round 1 [Logical Integrity]:
   [Attacker]: "후보 A는 '팀 규모가 일정 이상인 조직에서'라는 조건을 붙였습니다.
   그런데 원래 주장 '항상 낫다'는 이 조건을 포함하지 않습니다.
   Steelman이 이미 주장의 보편성을 포기한 것 아닌가요?"
   [User defense]: "원래 주장이 과장이라는 걸 인정해요. 실제로는 조건부로 더 낫다는 거예요."
   [Judge — Logical Integrity]: Relevance 9/10 · Substance 7/10 · Completeness 6/10 → Score delta: +8%
   Weighted Score: 52.4% (Logical Integrity: 58%)

→ Phase 1 Round 2 [Evidence Attack]:
   [Attacker]: "마이크로서비스 전환 실패 사례(예: Majestic Monolith 논문, Segment의 마이크로서비스→모놀리식 회귀)가 존재합니다.
   제시된 Netflix/Amazon 사례는 수백 명 이상의 전담 인프라팀이 있는 조직으로, 대부분의 팀에 적용하기엔 선택 편향이 있어요."
   [User defense]: "맞아요. 그래서 팀 규모 조건이 필요한 거예요. 소규모 팀엔 맞지 않죠."
   [Judge — Evidence Attack]: Relevance 8/10 · Substance 6/10 · Completeness 5/10 → Score delta: +8%
   Weighted Score: 54.4% (Evidence: 58%)

→ Soft Round Checkpoint (3 rounds 완료 아직 아님, Round 2 종료 — 계속 진행)

→ Phase 1 Round 3 [Counter-scenario]:
   [Attacker]: "소규모 스타트업(5인 팀, MVP 단계) 상황에서 마이크로서비스를 도입하면:
   인프라 오버헤드(K8s, 서비스 메시, 분산 트레이싱), 디버깅 복잡도, 배포 파이프라인 비용이
   비즈니스 속도를 심각하게 저하시킵니다. 이 시나리오에서 주장이 어떻게 성립하나요?"
   [User defense]: "5인 팀에서는 모놀리식이 낫죠. 그래서 '팀 규모 조건'을 달았어요."
   [Judge — Counter-scenario]: Relevance 7/10 · Substance 5/10 · Completeness 4/10 → Score delta: 0%
   Weighted Score: 54.4% (Counter-resilience: 50%, delta 0 — defense did not move the dimension)

→ Soft Round Checkpoint: "계속할까요?" → 계속

→ Phase 1 Round 4 [Scope Boundary]:
   [Attacker]: "주장은 '마이크로서비스 vs 모놀리식' 이분법을 전제하지만,
   모듈식 모놀리스(Modular Monolith), 서비스 지향 아키텍처(SOA) 등
   중간 아키텍처가 존재합니다. 경계 조건이 단순 이분법으로 설정되어 있어
   주장의 범위가 실제 선택지를 포괄하지 못합니다."
   [User defense]: "그 부분은 제가 단순화했네요. 중간 아키텍처까지 포함하면 주장이 더 복잡해져요."
   [Judge — Scope Boundary]: Relevance 8/10 · Substance 4/10 · Completeness 3/10 → Score delta: 0%
   Weighted Score: 54.4% (Scope Robustness: 50%, delta 0 — defense did not move the dimension)

→ Phase 2: Verdict
   Final Scores: Logical Integrity 58% · Evidence 58% · Counter-resilience 50% · Scope Robustness 50%
   Weighted Score: 54.4% → Verdict: pending (26–59%)

   Key vulnerabilities:
   - "항상"이라는 보편성 주장은 Steelman 단계에서 이미 조건부로 후퇴
   - 소규모 팀/초기 단계 시나리오에서 명백한 반례 존재
   - 이분법적 프레이밍이 실제 아키텍처 선택지를 단순화

   Surviving strengths:
   - 팀 규모 조건을 명시하면 중·대규모 조직에서 경험적 타당성 확보
   - Netflix/Amazon 사례의 선택 편향 인정 → 조건 특정성 향상

   Recommendation: "마이크로서비스가 모놀리식보다 항상 낫다"를
   "50명 이상의 엔지니어링 조직에서, 독립 배포와 장애 격리가 핵심 요구사항일 때,
   마이크로서비스는 모놀리식 대비 유지보수성과 확장성 면에서 우위를 보인다"로 범위 수정 권고
```

---

## Notes on This Example

- **Steelman phase**: Claim was immediately narrowed from "always better" to conditional, which correctly reduces the attack surface but also reveals the original claim's overreach.
- **Round 1 observation**: The Steelman already conceded universality — Logical Integrity attack was essentially pre-answered. This is expected; note it in the vulnerability list.
- **Termination**: 4 rounds completed, score 54% (pending zone) → Phase 2 forced naturally without hitting Round Limit cap.
- **Practical outcome**: "pending" verdict with clear scope recommendation is more useful than a binary survived/collapsed result for architectural decisions.
