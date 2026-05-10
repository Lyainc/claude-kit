# TOPIC 2: 각 카테고리의 유지비용 — 자기 모순 risk

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing

**[Plugin Maintenance Expert]**: 셋 다 비용 있어요. 각각 *고유한 실패 모드*가 있어서 합쳐서 보면 안 돼요.

| 카테고리 | 주요 실패 모드 | mitigation |
|---|---|---|
| P1a (cheatsheet) | drift — 명령어 갱신과 cheatsheet 갱신 분리 | 명령어 frontmatter에서 자동 추출 |
| P1b (hook) | silent failure — hook이 잘못 발화하면 사용자 작업 중단 | exit 0 (log-only) 기본 + opt-in strict |
| P1c (alias) | env-bound — 본인 dotfile/설정에 박혀서 다른 머신에서 깨짐 | repo 안 commit + setup script |

## Q&A

**[Critical Practitioner]**: P1b silent failure가 가장 무서워요. cheatsheet drift는 사용자가 한 번 시도해보면 즉시 알아챌 수 있어요. 하지만 hook이 *조용히 잘못된 동작*을 하면 사용자가 모르는 사이에 잘못된 가정으로 작업 진행해요. vault-bridge의 SessionEnd hook이 silent 안전망인 게 의도지만, 잘못된 안전망은 *없는 것보다 나빠요*.

**[Claude Code Platform Expert]**: 동의. Claude Code hook은 systemMessage로 사용자에게 알릴 수 있지만, 매 hook이 메시지 띄우면 노이즈. 노이즈 억제 vs 가시성 trade-off. P1b는 가시성 강하게 디폴트 권장 — 처음엔 systemMessage로 fired 사실 명시, 익숙해지면 사용자가 직접 silent로 전환.

**[Cognitive Ergonomics Expert]**: 또 다른 비용 — 추가가 거꾸로 새 까먹음 지점을 만든다. P1b에 hook 5개 추가하면, 사용자가 "어떤 hook이 어떤 명령어 앞에 fired되는지" 또 까먹어요. P1a가 hook도 cover해야 해요 — *cheatsheet에 hook 카탈로그 포함*.

**[Optimistic Practitioner]**: P1c는 비용 작아 보이지만 — 사용자 confirm. alias를 *어디에* 박을지 (zsh? Claude Code settings? plugin 안?) 결정 안 했죠? Claude Code settings에 박으면 plugin 차원 alias가 아니라 사용자 settings 차원이라 plugin 입장에선 *제어 불가*. plugin 안에 박으려면 새 메커니즘 설계 필요.

## Dialectic

**Thesis**: P1c가 가장 가벼운 비용
**Antithesis**: P1b가 가장 무거운 비용 (silent failure)
**Synthesis**: 비용 순서 고정 — P1c < P1a < P1b. 단 *cumulative*. P1b 가면 P1a (cheatsheet)가 hook 카탈로그까지 포함해야 함 → P1a 비용 증가.

## 결론

비용 순서 P1c < P1a < P1b 합의. P1b silent failure는 가장 큰 risk, 가시성 디폴트 강제. P1a는 hook 추가 시 카탈로그 자동 확장 필요. 만장일치.
