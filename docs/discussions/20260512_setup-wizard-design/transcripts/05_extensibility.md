# Topic 5 — 확장성

**날짜**: 2026-05-12
**참가자**: Moderator, Optimistic Practitioner, Critical Practitioner, DX Expert, Plugin Architecture Expert, State Management Expert, i18n/Voice Expert, Operations/KPI Expert

## Briefing

미래에 4번째(혹은 그 이상) 플러그인이 claude-kit 마켓플레이스에 추가될 때 wizard가 어떻게 대응할 것인가.

## Q&A

**[Plugin Architecture Expert]**: TOPIC 4에서 결정된 `pages/{plugin}.md` 패턴이 이미 확장성 해결해요. 새 플러그인 추가 시 페이지 파일 하나 떨어뜨리고 frontmatter에 `appliesTo: <new-plugin-id>` 명시하면 자동으로 wizard에 포함돼요.

**[State Management Expert]**: 단, 자동 인식의 한계는 — wizard 페이지를 누가 작성할 것인가예요. 플러그인 제작자가 직접 `pages/`에 PR 보내야 한다는 약속이 필요해요. 안 그러면 새 플러그인은 wizard에서 영영 안 보임.

**[Optimistic Practitioner]**: 그건 CONTRIBUTING.md에 명시하면 돼요. "마켓플레이스에 플러그인 추가 시 `claude-kit-welcome/skills/welcome/pages/{name}.md` 동봉 필수"라고.

**[Critical Practitioner]**: 페이지 누락된 플러그인은 wizard에서 어떻게 처리하나요? 침묵? 디폴트 안내?

**[DX Expert]**: 페이지 없는 플러그인은 wizard 입구의 multi-select 옵션에서 "기본 안내만"으로 묶거나, "(이 플러그인의 상세 안내가 아직 없어요. README 참조)" 1줄 페이지로 fallback. graceful degradation이 원칙.

**[Operations/KPI Expert]**: 분석 관점에서는 — 새 플러그인이 wizard에 등록되는 시점을 setupVersion 차이로 감지하면 좋아요. `setupVersion = '1.0.0'`에서 '1.1.0'으로 변경됐고 `pagesViewed`에 새 페이지 ID가 없으면 "새 콘텐츠 있음" 배지 표시 가능.

**[i18n/Voice Expert]**: 좋아요. 그 배지는 SessionStart 안내에서 "claude-kit에 새 플러그인 추가됐어요. /welcome --new로 확인하세요" 같은 짧은 멘트로.

**[Plugin Architecture Expert]**: 합의 — 자동 인식은 `pages/` 디렉토리 스캔으로 처리, 매뉴얼 작업은 contributor가 페이지 파일 작성 (PR에 포함). 페이지 없는 플러그인은 fallback page로 graceful degradation.

## Dialectic

| 단계 | 내용 |
|------|------|
| **Thesis** | wizard가 새 플러그인을 완전 자동 인식 (zero contributor work) |
| **Antithesis** | 본문 작성은 contributor만 할 수 있음 (LLM 자동 생성은 품질 보장 불가) |
| **Synthesis** | 구조 자동 인식 + 본문 contributor 책임 + 누락 시 fallback |

## 결론

**자동 인식 + Contributor 의무 + Fallback의 3-레이어 확장 전략**

1. **자동 인식 (구조)**: `pages/*.md` 스캔으로 새 페이지 자동 등록. 별도 매뉴얼 등록 불필요.

2. **Contributor 의무 (본문)**: 새 플러그인 마켓플레이스 추가 시 `claude-kit-welcome/skills/welcome/pages/{plugin-id}.md` 동봉. CONTRIBUTING.md에 명시.

3. **Fallback (누락 시)**: 페이지 없는 플러그인은 wizard 입구에서 노출되지 않거나, 노출 시 "(이 플러그인의 상세 안내가 아직 없어요. README를 참조하세요)" 1줄 페이지로 표시.

4. **신규 콘텐츠 알림**: `setupVersion` bump 시 새 페이지 발견하면 SessionStart에서 짧은 안내. `/welcome --new`로 신규 페이지만 표시 가능.

## Action Items

- [ ] CONTRIBUTING.md에 wizard 페이지 동봉 의무 섹션 추가
- [ ] Fallback 페이지 템플릿 (1줄 안내 + README 링크)
- [ ] `setupVersion` 비교 로직 (state.json vs `claude-kit-welcome/plugin.json` version)
- [ ] `/welcome --new` 옵션 명세 (pagesViewed에 없는 페이지만 표시)
- [ ] 페이지 ID 컨벤션 정의 (`{plugin-id}` = plugin.json의 name 필드 그대로)
