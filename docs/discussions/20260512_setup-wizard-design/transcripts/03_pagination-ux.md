# Topic 3 — 페이지네이션 UX 무게감

**날짜**: 2026-05-12
**참가자**: Moderator, Optimistic Practitioner, Critical Practitioner, DX Expert, Plugin Architecture Expert, State Management Expert, i18n/Voice Expert, Operations/KPI Expert

## Briefing

페이지네이션 구조에서 매 페이지마다 AskUserQuestion("다음?/건너뛰기") 4-5회 호출이면 관조형 walkthrough의 '읽는 맛'이 손상될 수 있음.

## Q&A

**[DX Expert]**: 사실 AskUserQuestion이 '다음/건너뛰기'만 묻는 거면 인터랙션이 거추장스럽지 않아요. 1초만에 누를 수 있는 거니까. 문제는 '읽는 시간 vs 클릭 시간' 비율이에요. 페이지 본문이 3-4줄로 짧으면 클릭이 부담되고, 본문이 10줄 이상이면 자연스럽게 "다음으로 가야지" 흐름이 됨.

**[Optimistic Practitioner]**: 그럼 페이지를 보장된 길이(8-12줄)로 두면 페이지네이션이 부담되지 않을 것 같아요. 페이지 안에 정보 밀도가 충분하면 클릭이 합리적.

**[Critical Practitioner]**: 사용자가 '나는 vault-bridge만 궁금하다'면 OVM, thinking-tools 페이지 둘을 매번 '건너뛰기' 눌러야 해요. 4페이지짜리에서 2번 건너뛰기는 짜증나거든요.

**[i18n/Voice Expert]**: 페이지 선택을 페이지네이션 시작 시 한 번에 처리하는 게 어때요? 첫 화면에서 "어떤 플러그인부터 볼까요? (multi-select)" — 그 다음엔 선택한 것만 순차 표시.

**[DX Expert]**: 좋아요. 이거 두 가지 장점이 있어요. (1) 사용자가 처음에 선택하면 그 뒤로는 AskUserQuestion 없이 paginated read-only flow, (2) '관심 있는 것만 본다' 권한을 명시적으로 줌.

**[State Management Expert]**: 그러면 페이지네이션 끝에 '읽은 페이지 기록'을 state.json에 저장해야 해요. `pagesViewed: ["hub", "thinking-tools", "vault-bridge"]` 같은 식으로. /welcome 재실행 시 "이미 본 페이지 건너뛸까요?" 옵션 제공.

**[Operations/KPI Expert]**: 측정 관점에서도 좋아요. 어느 플러그인 페이지가 많이 읽히는지, 어디서 사용자가 이탈하는지 분석 가능.

**[Plugin Architecture Expert]**: 한 가지 확인 — AskUserQuestion이 multi-select 가능한지. 확인 결과 가능 (`multiSelect: true`).

## Dialectic

| 단계 | 내용 |
|------|------|
| **Thesis** | 매 페이지마다 "다음?" AskUserQuestion으로 사용자 의사 확인 |
| **Antithesis** | 4-5회 클릭이 '관조형' 흐름을 깸. 관심 없는 페이지에 거부감 |
| **Synthesis** | 입구 1회 multi-select으로 페이지 묶음 선택, 그 후엔 자동 순차 표시, 종료 시 1회 액션 선택 |

## 결론

**AskUserQuestion 총 2회로 압축**

1. **입구 페이지** (multi-select): "어떤 플러그인부터 볼까요?"
   - 옵션: thinking-tools / obsidian-vault-manager / vault-bridge / 모두 / 건너뛰기
   - 다중 선택 허용
2. **선택된 페이지들 순차 표시** (AskUserQuestion 없음, 페이지 끝마다 "── 다음: {next page title}" 표지만)
3. **종료 페이지** (single-select): "마침 / 추가 페이지 보기 / 이 wizard 다시 안 보기"

**페이지 본문 가이드**: 8-12줄 권장 (정보 밀도 + 읽는 흐름 양립)

**상태 기록**: `state.json.pagesViewed` 배열에 본 페이지 ID 누적

## Action Items

- [ ] 입구 페이지 UI 스펙 작성 (multi-select 텍스트 + 옵션 라벨)
- [ ] 종료 페이지 UI 스펙 작성 (3지 액션)
- [ ] 페이지 본문 길이 가이드(8-12줄) 페이지 템플릿에 명시
- [ ] `pagesViewed` 기록 로직 (페이지 표시 시점에 append)
- [ ] `/welcome --new` 재실행 시 "이미 본 페이지 건너뛸까요?" 옵션 처리
