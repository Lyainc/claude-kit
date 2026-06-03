# Adversarial Review — ⑤ 실행 하네스 소유권

**Date**: 2026-06-03
**Method**: adversarial-review (자동 방어 + 격리 실행). Attacker = main, Defender = 독립 에이전트(opus), Judge = 격리 에이전트(opus).
**Claims tested**: 1

---

## Claim: claude-kit이 ⑤ 실행 하네스를 자체 소유해야 한다

**Steelman (Attack Target)**: "⑤ 실행 루프는 claude-kit이라는 '에이전틱 개발 워크플로우 제품'의 심장이지 외주 가능한 주변부가 아니다. OMC 의존은 제품 정체성·버전 안정성·UX 일관성을 영구히 저당잡는다. 자체 소유는 비용이 아니라 필수 투자이며, 단방향 통합(harness→leaf)이 오히려 통합 표면을 단순화한다." (= SUMMARY C-1이 만장일치로 기각한 옵션 B 채택 + OMC 자체 대체 + 유지보수 표면 증가 수용)

### Attack History

| Round | Vector | 공격 요지 | 방어 결과 | Judge | Δ |
|-------|--------|---------|---------|-------|---|
| 1 | Logical Integrity | "심장⇒소유"는 non-sequitur(엔진 외주). "단방향=표면감소"는 순환회계(하네스 빌드비용 누락). 만장일치 뒤집기엔 비유 하나 | PARTIAL — "섀시/헌법 invariant" 재구성은 생존, 순환회계는 인정 | 21/30 | +8% |
| 2 | Evidence | lock-in 증거 0건. `7a94a34`가 ⑤ 소유 없이 vendor-neutral 이미 달성 = 전제 반증. 작동 시스템 심장이식 리스크 | **CONCEDED** — "reframe 가능하나 rebut 불가" | 14/30 | 0% |
| 3 | Counter-scenario | native supersession(Anthropic이 /goal·Workflow 네이티브 강화 → 자체 하네스 매몰비용). 플랫폼 추격 속도 | PARTIAL — fault-isolation 대칭은 생존, supersession은 방어 불가 | 18/30 | +8% |
| 4 | Scope Boundary | claude-kit=마켓플레이스(배포처≠오케스트레이터). plural-marketplace 카탈로그 분열. 게이트=프로젝트 자율성 | PARTIAL — "마켓플레이스는 불변천장 아님" 생존, 카탈로그 분열·자율성 침해는 인정 | 18/30 | +8% |

### Final Scores

- Logical Integrity: 58% (×0.30)
- Evidence: 50% (×0.25)
- Counter-resilience: 58% (×0.25)
- Scope Robustness: 58% (×0.20)
- **Weighted Score: 56%**

### Verdict: `pending` (보통, 56%)

정량은 경계선 pending이나, **정량 메커니즘이 둔감**(1라운드 + 50% 시작 + Evidence 완전붕괴에도 0% delta)하다. 독립 Defender와 격리 Judge 둘 다 독립적으로 **"strong form은 살아남지 못한다"**고 결론 — 정성 판정이 더 신뢰할 만하며, 그것은 **strong form(전면 옵션 B 전환) 기각**에 가깝다.

**Key vulnerabilities (landed)**:
- Evidence 완전 붕괴: lock-in 증거 0, `7a94a34`가 ⑤ 소유 없이 vendor-neutral 달성(전제 반증), #122 자체가 "OMC에서 동작 + D1 장기목표"로 긴급성 부정.
- Native supersession 방어 불가: Anthropic이 `/goal`·Workflow를 네이티브로 강화 중 → from-scratch 자체 하네스는 매몰비용 리스크.
- 순환 회계: "단방향=표면 감소"는 하네스 빌드·유지 비용 누락.
- Scope: plural-marketplace 카탈로그 분열(CC-lock tier) + 게이트의 프로젝트 자율성 침해.

**Surviving strengths (narrow)**:
- ⑤가 OMC/native가 강제 못 하는 product-defining invariant(헌법: new-file-only·self-approval 금지·단방향·goal-doc 스키마)를 가진다면, *그 enforcement만큼은* 자체 소유 정당("엔진"이 아니라 "섀시").
- fault-isolation은 대칭(OMC 버그도 ⑤ 마비) → 소유 = "벤더 대기↔자가 수정" 트레이드.
- "마켓플레이스"는 불변 정체성 천장이 아님(재설계가 이미 ⑤를 레이어 모델에 포함).

---

## 결론 — strong form 기각, narrow form 채택 (2026-06-03 사용자 결정)

전면 옵션 B(긴급 OMC 자체 대체)는 기각. 단 **OMC 탈피 니즈는 유효**하므로, adversarial을 통과하는 형태로 재정의:

> **Claude Code 네이티브(dynamic Workflow, /goal, agents, hooks)를 substrate로 한 경량 하네스로, OMC를 strangler 점진 대체한다.**

이 재정의가 각 반박을 흡수하는 방식:
- **Native supersession → 자산화**: native 위에 thin하게 올리므로 native가 강해질수록 수혜(매몰비용 회피).
- **유지보수 표면 → 최소화**: native 재사용으로 자체 빌드 표면을 invariant enforcement gap에 한정.
- **Evidence(lock-in 증거 없음) → 점진 정당화**: 전면 교체는 못 받쳐도 strangler 점진은 막지 못함. leaf vendor-neutrality는 이미 `7a94a34`로 달성.
- **Scope(마켓플레이스) → 완화**: thin·점진·opt-in이라 정체성 충돌·자율성 침해 최소.

### Recommendations (이슈 액션)

- #99: 경계를 정적("⑤=OMC")에서 진화형("현재 OMC / 목표 native 기반 경량 하네스 / strangler 점진")으로 수정.
- #122: "OMC 자체 대체 엔진"을 "native substrate 위 경량 레이어 + strangler 점진"으로 재정의.
- 신설: native substrate 매핑 + strangler 경로 / ⑤ 스킬 인벤토리(native 우선) / 검증 게이트 체인.
