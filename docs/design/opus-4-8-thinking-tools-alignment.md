# Opus 4.8 정렬 검토 — thinking-tools

> 상태: **검토용 제안서** (변경 전). 작성일 2026-05-29.
> 범위: `thinking-tools` 플러그인의 skill/agent 텍스트가 Claude Opus 4.8 행동 특성과 정렬되는지 검토하고, 실질 변경 후보를 추린다.
> 출처: [Anthropic 공식 prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), [migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide), [Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md), Simon Willison (2026-05-28).

## 1. 핵심 결론

thinking-tools는 **이미 4.8-friendly하게 설계돼 있다.** 공식 가이드도 *"performs well out of the box on existing Claude Opus 4.7 prompts"*라고 명시한다. 전수 grep + 핵심 skill 정독 결과, 4.8이 경고하는 안티패턴(과격 tool 강제 트리거, 주관적 필터링 지시, progress scaffolding 강제)이 거의 없다.

따라서 **대규모 프롬프트 재작성은 근거 없는 과잉수정이다.** 실질 변경은 1건, 나머지는 "유지 권장"의 근거 명문화에 해당한다.

## 2. 4.8 행동 변화 요약 (4.7 대비)

| 특성 | 내용 |
|------|------|
| More literal instruction following | 명시 안 한 요청 추론 안 함, 한 항목→다른 항목 일반화 안 함. scope 명시 필요 |
| Spawns fewer subagents | 기본적으로 subagent 덜 생성. steerable |
| Favors reasoning over tool calls | tool 사용 줄임. effort↑ 또는 명시로 보정 |
| Response length self-calibration | 고정 verbosity 안 함. 단순작업 짧게, open-ended 길게 |
| Honesty / abstention ↑ | 근거 없는 주장 회피. code-review류에서 "conservative" 지시를 과충실히 따라 finding drop 가능 |
| Overtriggering 주의 | "CRITICAL: You MUST use [tool]" 과격 트리거는 dial back 권장 |
| effort 기본 high, strict | coding/agentic은 xhigh 권장. low/medium에서 scope를 요청된 것만 |
| thinking off by default | `adaptive` 명시 필요. extended thinking(`budget_tokens`)은 deprecated |
| Tone | direct, opinionated, minimal validation, sparing emoji |

## 3. skill별 판정

| Skill | 4.8 접점 | 판정 |
|-------|---------|------|
| `thinking-facilitator` (agent) | 명시적 decision tree + signal keyword 테이블 라우팅 | ✅ literal following과 본질 정렬 — 4.8에서 더 정확 |
| `adversarial-review` | 정량 rubric(Relevance/Substance/Completeness 0–10), STATE block | ✅ 주관 필터 아님 → abstention 위험 없음. STATE는 정형 산출물 |
| `expert-panel` | MANDATORY recording, anti-conformity directive, `--deep` subagent | ✅ literal following·honesty와 정렬. `--deep`는 명시 플래그 |
| `unknown-discovery` | blind-spot 인터뷰 | ✅ 4.8 honesty와 시너지 |
| `doc-polish` | LLM trope blacklist 기반 *입력 문서* 검사 | ✅ 검사 기준은 모델 무관 → 영향 없음 |
| `doc-concretize` | step-by-step 재귀 작성 | ✅ self-contained |
| `thought-chain` | 4-stage 파이프라인 | ✅ 명시적 stage 정의 |
| `spec-first` | STATE block after every round | ✅ 정형 checkpoint, progress scaffolding 아님 |
| `diverse-sampling` | **"Model Capabilities" 섹션의 Opus/Sonnet 이분법** | ⚠️ **유일한 실질 변경 후보** (§4) |

## 4. 실질 변경 후보 (Tier 1, 1건)

### diverse-sampling: `Model Capabilities` 섹션 (SKILL.md L164–174)

현재 본문:

```
### Extended Thinking (Opus)
- 구조화 데이터 처리를 thinking 단계에서 수행
- 출력에는 변환된 자연어만 포함
- 확률 calibration 더 정확

### Standard Mode (Sonnet)
- 명시적 지시로 구조화 데이터 은닉
- "NEVER output XML/JSON to user" 강조
- 파싱 실패 시 즉시 fallback
```

**문제**:
1. `Extended Thinking (Opus)` 분류가 4.6+ 시대에 부정확하다. 4.8은 **adaptive thinking**(`thinking: {type: "adaptive"}`)을 쓰고, 구식 extended thinking(`budget_tokens`)은 deprecated다. 게다가 4.8은 thinking이 기본 off다.
2. 이 skill은 frontmatter가 `model: sonnet`으로 고정돼 있어, "Extended Thinking (Opus)" 분기는 **실행되지 않는 dead path**다 — 문서로서만 부정확.
3. `reference.md`에는 모델 분기가 없어(확인 완료), 변경 범위는 SKILL.md 이 섹션 한 곳으로 한정된다.

**제안 방향** (택1, 변경 시 결정):
- **(a) 단순화**: model이 sonnet 고정이므로 모델 분기를 없애고, "구조화 데이터(XML/JSON)는 thinking/내부에서만 처리하고 사용자 출력에는 변환된 자연어만 노출"이라는 모델-중립 원칙 1개로 합친다. (권장 — 가장 정직)
- **(b) 갱신**: 분기를 유지하되 "Extended Thinking (Opus)" → "Adaptive thinking 지원 모델(Opus/Sonnet 4.6+)"로 정정하고 `budget_tokens` 언급 제거.

> 주의: 이 변경은 정확성 교정이지 4.8 성능 최적화가 아니다. 기능 동작은 동일하다.

## 5. 유지 권장 (근거 명문화)

4.8 특성에 비춰 **바꾸지 않는 것이 맞는** 항목 — 과잉수정 방지용으로 근거를 남긴다.

- **STATE block "after every round"** (adversarial-review, spec-first): 가이드가 제거를 권한 *"after every 3 tool calls, summarize"* 류 progress scaffolding이 아니다. Survival Score·인터뷰 게이트를 추적하는 **정형 산출물**이며 제거 시 기능이 손실된다.
- **NEVER/MUST 제약**: 전수 확인 결과 전부 안전·경계 제약(`NEVER commit without approval`, `NEVER call vault-searcher`, `NEVER changes content meaning`)이다. 4.8이 충실히 따르는 것이 바람직하다. tool 강제 트리거 안티패턴이 아니다.
- **`--deep` subagent spawn** (expert-panel, adversarial-review): 명시적 플래그로 제어되어 4.8의 "덜 spawn" 경향과 무관하다. default 모드는 단일 컨텍스트 내 페르소나 분리라 subagent를 쓰지 않는다.
- **doc-polish trope blacklist**: 입력 문서 기준 검사라 생성 모델과 무관하다. 4.8 prose(sparing emoji, direct)와 충돌하지 않는다.

## 6. 4.8에서 가치 상승 (변경 불요, 활용 강조)

- **diverse-sampling**: 4.8은 강한 default house style 등 **mode collapse 경향**이 있다고 가이드가 명시한다(*"converge toward generic outputs"*). VS 기법의 가치가 오히려 커진다.
- **unknown-discovery / adversarial-review**: 4.8 honesty·calibration 향상과 시너지. 더 날카로운 blind-spot·공격 벡터를 기대할 수 있다.

## 7. 권하지 않는 것

- skill body에 일괄 verbosity/thoroughness 지시 추가 — 4.8 self-calibrate라 역효과.
- NEVER/MUST 일괄 완화 — 안전 제약이라 유지가 맞음.
- `model:` frontmatter를 opus로 일괄 승격 — 비용 증가, routing 재측정 근거 없음.
- description trigger 문구 재작성 — 명시적 keyword 기반이라 4.8에 이미 최적.

## 8. 실행 체크리스트 (승인 시)

- [ ] diverse-sampling SKILL.md `Model Capabilities` 섹션 정정 (§4, 방향 a 또는 b)
- [ ] 변경 후 `reference.md`와의 일관성 재확인 (현재 모델 분기 없음 — 신규 모순 없는지)
- [ ] thinking-tools 회귀 영향 없음 확인 (이 변경은 문서 정확성 교정이라 테스트 변화 없음)
- [ ] 별도 트랙: 글로벌 `~/.claude/CLAUDE.md`의 "4.7" 명시 문구 갱신 (repo 밖, 승인 필요)
- [ ] 보류: Dynamic Workflows 매핑 (research preview, 2주 안정화 후 재평가)
