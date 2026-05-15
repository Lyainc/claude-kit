# Topic 2 — SessionStart 훅 경합

**날짜**: 2026-05-12
**참가자**: Moderator, Optimistic Practitioner, Critical Practitioner, DX Expert, Plugin Architecture Expert, State Management Expert, i18n/Voice Expert, Operations/KPI Expert

## Briefing

vault-bridge가 이미 SessionStart 훅(`hooks/session-start-manifest.sh`)을 보유하고 있음. wizard의 1회 안내를 어느 hook handler에 둘 것인가.

- 옵션 A: 새 hook handler 추가 (`session-start-wizard.sh`) — 독립
- 옵션 B: vault-bridge의 manifest 훅에 wizard 로직 weld
- 옵션 C: 마켓플레이스(`claude-kit`) 레벨의 별도 hook

## Q&A

**[Plugin Architecture Expert]**: 옵션 B는 절대 안 돼요. vault-bridge는 자기 도메인(vault)만 책임져야 하고, 마켓플레이스 wizard 안내는 OVM/vault-bridge에 의존성 없는 별도 관심사거든요. 단일 책임 원칙 위반이에요.

**[Optimistic Practitioner]**: 그럼 옵션 C 같은데, 마켓플레이스 레벨에 hook 정의가 가능한가요?

**[Critical Practitioner]**: 마켓플레이스 자체는 hook을 가질 수 없어요. `.claude-plugin/marketplace.json`은 plugins 목록(`source` 경로)만 갖고, hook은 각 plugin의 `plugin.json`/`hooks/` 안에서만 정의되거든요. → 옵션 A 강제.

**[Plugin Architecture Expert]**: 그러면 새로운 4번째 플러그인 `claude-kit-welcome`을 만드는 게 깔끔해요. 이 플러그인이 1) SessionStart 훅, 2) `/welcome` 슬래시 커맨드, 3) wizard skill을 보유. 다른 세 플러그인은 그대로 두고, 사용자가 wizard만 원치 않으면 이 플러그인만 disable 가능.

**[DX Expert]**: 사용자 입장에선 "또 플러그인 하나 더?" 거부감 있을 수 있어요. 차라리 `thinking-tools` 같은 의존성 적은 플러그인에 wizard skill+hook을 얹는 게 어떨까요?

**[Plugin Architecture Expert]**: 안 좋아요. thinking-tools가 wizard 책임지면 thinking-tools 미설치 시 wizard 사용 불가. 마켓플레이스의 입구는 마켓플레이스 자체 권한이지 특정 플러그인 권한이 아니에요.

**[State Management Expert]**: 동의. 그리고 이 플러그인이 다른 플러그인 감지를 위해서는 `~/.claude/plugins/cache/` 스캔보다 `~/.claude/plugins/marketplaces/Lyainc-claude-kit/.claude-plugin/marketplace.json` 직접 파싱이 더 안정적이에요. 캐시 디렉토리 구조가 바뀔 수 있으니까.

**[Operations/KPI Expert]**: 새 플러그인 만들면 install funnel이 추가돼요. 사용자가 marketplace에서 세 플러그인 + welcome까지 4개를 install해야 하는데, welcome이 install 안 되면 wizard 자체가 안 떠요. → marketplace에 welcome을 default-recommended로 두고 "marketplace 추천 첫 위치" 배치.

**[i18n/Voice Expert]**: 이름은 `claude-kit-welcome`보다 짧고 의미 명확한 게 좋아요 — `claude-kit-tour` 혹은 `claude-kit-onboarding`. 사용자에게 "이게 뭐 하는 플러그인인지"가 즉시 보여야 해요.

## Dialectic

| 단계 | 내용 |
|------|------|
| **Thesis** | 기존 플러그인(thinking-tools 등)에 wizard 얹기 |
| **Antithesis** | 마켓플레이스 레벨 hook은 불가능, 별도 책임이 필요 |
| **Synthesis** | 새 4번째 플러그인 `claude-kit-welcome` 신설 |

## 결론

**새 플러그인 `claude-kit-welcome` 추가 (이름은 향후 brand voice 단계에서 재검토)**

- 구성: `hooks/session-start-welcome.sh` + `commands/welcome.md` + `skills/welcome/SKILL.md`
- `marketplace.json`에서 첫 위치 또는 "recommended" 태그
- 플러그인 감지: `~/.claude/plugins/marketplaces/Lyainc-claude-kit/.claude-plugin/marketplace.json` 직접 파싱
- vault-bridge의 manifest 훅과 독립

## Action Items

- [ ] 플러그인 이름 brand voice 단계에서 확정 (`claude-kit-welcome` vs `claude-kit-tour` vs `claude-kit-onboarding`)
- [ ] 4번째 플러그인 디렉토리 구조 설계
- [ ] `marketplace.json` 항목 추가 + 첫 위치 정렬
- [ ] `session-start-welcome.sh` 동작 명세 작성 (state.json 읽기 → grace 판정 → systemMessage)
- [ ] CONTRIBUTING.md에 "wizard 페이지 동봉 의무" 명시
