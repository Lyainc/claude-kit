# thinking-tools 고도화 방안 (2026-06-02)

> **상태 (2026-06-03 갱신)**: C1(expert-panel STATE) ✅ 완료(`79781d1`). C2(saturation 일반화 + STATE 헤더 dedup) → **#107**로 진행 중. §4 폐기·보류 항목은 backlog 이슈로 이관(payload=폐기, 관점다양성→#114, Ontologist→#113). spec-first 분리(§1)는 **#111** 소유. 의사결정 원칙·telemetry 근거는 압축 보존.
>
> **추가 갱신 (2026-07-07)**: #107·#111·#114 전부 CLOSED(#111은 spec-first→build-spec 리네임으로 해소, `spec-first-extraction-2026-06-02.md` 참조). **#113만 아직 OPEN**(backlog, 3번째 doc primitive 게이트) — 이 문서에서 유일하게 살아있는 실이에요.

## 배경 · 범위

ouroboros(`Q00/ouroboros`) 대조 분석에서 출발해, claude-kit thinking-tools의 정체성과 내부 품질을 재검토한 결과를 정리한다.

**확정된 선행 결정**:
- **spec-first 분리**: thinking-tools에서 제거해 별도 플러그인으로 (동일 마켓플레이스 내 존속). 결정·근거·정의·미해결은 별도 문서 `spec-first-extraction-2026-06-02.md` 참조 (본 문서 범위 밖).
- 분리 후 thinking-tools = **7개 사고 도우미**. 공통 정체성 = *출력의 최종 수신자가 사람*(개발 외 문서작업도 전제).

**이 문서의 범위**: 남는 7개 스킬의 내부 품질 강화. **비용 기준 분류** — 명백히 싼 개선은 진행, 비싸거나 효과 불확실하면 보류.

**명시적 제외(별개 트랙)**:
- trigger 정확도 / 스킬 간 라우팅 명확성 → description 작업, slimming의 다른 트랙 (이번 세션의 "spec-first 모호함"이 이 트랙의 증거지만, 본 문서 대상 아님)
- spec-first 분리 실행(플러그인 구조·이름·marketplace 등록) → 별도 작업
- 기계 연계(payload) → §4에서 **폐기 확정**

---

## 의사결정 원칙

초안은 "검증 통과 후 채택"을 깔았으나, 검증 자체가 무겁고(§6) telemetry로도 메울 수 없음이 드러나 **비용 기준**으로 전환했다.

| 원칙 | 내용 |
|---|---|
| **비용 우선** | 우선순위를 *검증 가능성*이 아니라 **비용**에 묶는다. 비용이 명백히 낮은(기존 패턴 이식 등) 개선은 무검증 진행 — 사용 빈도가 높든 낮든 손해가 없기 때문. 비싸거나 불확실하면 보류 |
| **slimming 우선** | 사용자 대면 복잡도 증가 금지. 내부 메커니즘 추가도 *복잡도 비용*(파일 길이) 계산 대상. 32cefcf가 줄인 줄을 무근거로 되늘리지 않는다 → §5 reference로 상쇄 |
| **telemetry 비맹신** | dogfooding 1인 로그라 사용량을 "안 쓰인다"로 over-read 금지(§6). "핫패스 아님" 정도의 약한 참고만 |
| **새 스킬 남발 금지** | 신규 스킬은 slimming 역행. 빈 칸 진단은 기록하되 추가는 별도 정당화 |
| **정체성 보존** | 사람이 최종 수신자. payload·기계연계는 정체성 이탈 |

---

## §1. 전제: spec-first 분리 (별도 트랙)

thinking-tools에서 spec-first를 별도 플러그인으로 분리하기로 결정 → 분리 후 thinking-tools = **7개 사고 도우미**(이 문서의 전제). 분리 결정·근거(정체성 이질 / 방법 중복 / 도메인 편향 / 기능 중복)·정의·미해결(명명·유사도구 웹검증·인터뷰 엔진 중복)은 **별도 문서 `spec-first-extraction-2026-06-02.md`** 로 정리. 본 문서 범위 밖.

---

## §2. 진단 — 유형론은 *보조 렌즈*

> **주의**: 7개 스킬 = 7개 유형의 1:1 매핑은 *분류 체계*가 아니라 *이름표*에 가깝다(unknown-discovery 검증). 아래 유형은 품질 속성을 매핑하기 위한 **보조 렌즈**로만 쓰고, 문서의 중심 주장으로 삼지 않는다. 실제 진단 단위는 *품질 속성*이다.

**다축 품질 속성** (스킬을 가로지르는 cross-cutting 특성):

| 스킬 | 지속성(여러 턴) | 반복성(루프) | 수신자 | resumability | termination | 관점 다양성 |
|---|---|---|---|---|---|---|
| diverse-sampling | 단발 | 무 | 사람 | N/A | N/A | 내장(VS) |
| unknown-discovery | 지속 | 반복 | 사람 | 보유 | Depth Gate 의존 | — |
| expert-panel | 지속 | 반복 | 사람 | **없음** | **없음** | 페르소나(동형위험) |
| adversarial-review | 지속 | 반복 | 사람 | 보유 | cap만 | attacker/judge(동형위험) |
| doc-concretize | 중간 | 무 | 사람 | 부분 | N/A | N/A |
| doc-polish | 중간 | 무 | 사람 | 부분 | N/A | N/A |
| thought-chain | (위임) | (위임) | 사람 | (위임) | (위임) | (위임) |

**관찰**:
- expert-panel이 resumability·termination 둘 다 공란 — *구조적으로* 가장 노출됨.
- 32cefcf가 숫자 점수 표면을 제거 → 사용자의 비공식 종료 신호(예: "Depth 안 올라가네")가 사라짐 → termination 공란이 *상대적으로* 더 노출됨.
- 단 "노출됨 = 시급"이 아님. 진행 여부는 §3 비용 기준으로 판단.

---

## §3. 진행 후보 — 비용 기준 분류

비용이 명백히 낮은 개선만 무검증 진행한다. **핵심 논리**: expert-panel을 2번 쓰든 200번 쓰든, *이미 다른 스킬에 있는 STATE 블록을 복사해 넣는 비용*은 동일하게 0에 가깝다. 빈도가 높으면 이득이 크고 낮아도 손해가 없으므로, "할 가치 있나"를 검증할 필요가 없다. 사용 빈도 논쟁 자체를 우회한다.

### C1. expert-panel에 STATE 블록 (resumability)

- **현상**: 다토픽·다라운드 토론으로 가장 길게 지속되나 STATE 없음 → compaction 시 토론 상태 손실 가능.
- **비용**: **거의 0** — unknown-discovery·adversarial-review가 이미 가진 `STATE:CHECKPOINT` 패턴을 복사·적응.
- **명분**: 일관성. 지속형 스킬 중 expert-panel만 빠짐. 빈도와 무관하게 손해 없음.
- **전파**: thought-chain이 expert-panel을 파이프라인 단계(`unknown-discovery→expert-panel→doc-concretize→doc-polish`)로 호출하므로 변경이 thought-chain 경유 실행에도 전파(무해). 분리되는 spec-first는 thought-chain 미호출이라 무영향.
- **판정**: ✅ **완료** (`79781d1` — STATE 블록 추가, "never rendered to user" 내부 복원 스캐폴딩으로 구현).

### C2. saturation 종료조건 일반화 (expert-panel + unknown-discovery)

- **현상**: 명시적 saturation이 spec-first(분리 예정)에만 존재. unknown-discovery는 Depth Gate 의존, expert-panel은 종료조건 자체가 없음.
- **비용**: **낮음** — spec-first/unknown-discovery의 saturation 패턴 이식.
- **명분**: 32cefcf가 숫자 종료신호를 제거 → 명시적 종료조건이 그 대체재. 반복형 스킬 일관성.
- **타이밍 주의**: spec-first 분리 전에 saturation 패턴을 공통 reference로 추출해두면 이식원이 보존됨(§5). 분리와 순서 조율 필요.
- **판정**: → **#107**로 진행 중 (saturation 일반화 + 공유 STATE 헤더 dedup, 비용 낮음).

---

## §4. 폐기 · 보류

| 항목 | 판정 | 사유 |
|---|---|---|
| **payload (measurement→actionable)** | **폐기 확정** | spec-first 분리로 thinking-tools는 전부 사람-수신자. 기계 연계는 정체성 이탈 |
| **관점 다양성 (single-model 동형성 해소)** | **보류** | 비용 높음(격리 서브에이전트 실험 필요) + 효과 불확실(희망사항 위험). 비용 기준에서 진행 안 함. 동형성은 *수용된 single-model 한계*로 문서화, multi-model(MCP)은 미래 옵션으로만 |
| **본질/구조 발견 신규 스킬(Ontologist)** | **보류** | 발견형이 unknown-discovery(맹점)만이라는 빈 칸은 *기록*. 신규 스킬은 slimming 역행 — 별도 정당화 전까지 추가 안 함 |

**이슈 이관 (2026-06-03)**: payload = 폐기 확정(이슈 없음). 관점 다양성 multi-model → **#114**(backlog). 단 저비용 single-model 버전(역할 프롬프트 차별화)은 **#106**(D4a)에서 별도 진행. Ontologist 빈 칸 = **#113**(3rd doc primitive 게이트)와 별개 기록.

---

## §5. 구현 방식 — reference 추출 (비용을 0으로 유지하는 레버)

C1·C2가 SKILL.md를 늘리면 slimming과 충돌. 이를 막는 핵심:

- **공통 reference 추출**: STATE·saturation 패턴을 각 SKILL.md에 복붙하지 않고 공통 reference 1곳 + 포인터. 중복 없이 일관화.
- **선례 존재**: audit이 이미 `vault-audit-rules.md` canonical 포인터 방식을 씀(slimming plan E1). 새로 검증할 필요 없이 선례를 따른다.
- **분기**: 포인터 방식에서 LLM이 STATE/saturation을 inline만큼 정확히 따르지 못하면 inline 불가피 → 그 경우에만 slimming 비용 재계산. 이건 *구현 형태* 선택이지 채택 여부가 아니므로, C1/C2 진행 자체를 막지 않는다.

---

## §6. telemetry 실측 — 왜 정량 검증에 의존하지 않는가 (압축)

초안은 정량 검증(빈도·고통·다양성)을 전제했으나 실측이 비현실적이라 **비용 기준(§3)으로 전환**.

- **인프라**: 정상 작동(`CLAUDE_KIT_TELEMETRY=1` opt-in, hook 기반). 19일·telemetry-on 65세션.
- **실측**: expert-panel 2 / unknown-discovery·thought-chain·adversarial-review 각 1 / 나머지 0. 대비 OMC ai-slop-cleaner 14.
- **over-read 금지**: 분모 작음 + 의도적 사고작업이라 본질적으로 드묾 + dogfooding 1인 + telemetry-on 한정 → "안 쓰인다"로 읽으면 안 됨.
- **결론**: 정량 검증 연료로 부적합 → 비용 기준 채택. 살아남는 신호 = "thinking-tools는 핫패스 아님"(과잉 튜닝 불필요)의 약한 참고만.

---

## 비목표 (재론 방지)

- 사용자 대면 복잡도 증가 (32cefcf 역행)
- telemetry 사용량으로 우선순위 단정 (over-read)
- 비싸거나 효과 불확실한 항목의 무리한 채택 (관점 다양성 등)
- 새 스킬 추가 (별도 정당화 없이)
- 기계 연계 / payload (정체성 이탈)
- trigger·라우팅 개선 (별개 트랙)
