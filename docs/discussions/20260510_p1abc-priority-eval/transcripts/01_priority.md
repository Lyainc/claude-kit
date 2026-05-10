# TOPIC 1: P1a/b/c 우선순위 — 어느 카테고리부터?

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing

**[Optimistic Practitioner]**: P1c (인자/옵션 디폴트·프리셋)부터 가야 해요. 가장 작은 변경이고, ROI 즉시 확인 가능. `save-session --hours 3` 같은 alias는 본인 dotfile에 한 줄 추가만으로 끝나요. P1a/P1b는 설계 비용 있어요.

**[Critical Practitioner]**: P1c부터는 안 돼요. P1a 없이 P1c 들어가면 자기 모순이거든요. 본인이 명령어 *이름조차* 까먹는다는데 — 까먹은 명령어에 alias를 어떻게 박아요? "내가 alias를 만들어둔 게 있다"는 사실 자체를 까먹어요. P1a (cheatsheet)가 전제예요.

## Q&A

**[Claude Code Platform Expert]**: Critical 의견에 가중치 줘요. Claude Code 환경에서 자연어 트리거가 1차 진입로인데, alias는 명시적 호출 경로거든요. 자연어로 "세션 정리"라고 하면 vault-searcher Mode 4가 알아서 진행돼요 — alias가 끼어들 자리가 없어요. P1c는 명령어 직접 호출 빈도가 정량적으로 높을 때만 의미 있어요. 그게 검증됐어요?

**[Optimistic Practitioner]**: 검증 안 됐어요. 본인 직감이에요.

**[Cognitive Ergonomics Expert]**: 잠깐 — "까먹음"의 종류부터 분류할게요.
1. 존재 망각 — 명령어가 있는지 자체를 모름
2. 이름 망각 — 있는 건 아는데 정확한 이름 모름
3. 인자 망각 — 이름은 아는데 플래그/옵션 까먹음
4. 순서 망각 — 워크플로 단계가 헷갈림

사용자 답변(unknown-discovery Round 7에서 1, 2, 3 다 선택)은 *모든 종류 망각이 다 있다*는 신호예요. P1a가 (1)(2)(3) 다 잡고, P1c는 (3)만 잡아요. 포괄성이 P1a 압도적이에요.

**[Plugin Maintenance Expert]**: 다른 각도. P1a는 *문서*고, P1c는 *동작*이에요. 문서는 drift 위험이 코드보다 큰데, P1a는 cheatsheet drift가 곧바로 거짓말로 이어져요. 명령어 추가될 때마다 cheatsheet 갱신 안 하면 미래 본인이 "예전엔 됐는데?" 헤매요. 유지비용 순서는 P1c < P1a < P1b.

## Dialectic

**Thesis**: P1c부터 (작은 변경, 빠른 ROI)
**Antithesis**: P1a부터 (까먹음 종류 포괄성, 자기 모순 회피)
**Synthesis**: P1a 먼저 — 단, drift mitigation을 같이 설계 (cheatsheet 자동 생성 메커니즘 — 명령어 description에서 추출)

**[Moderator]**: P1c 옹호 측 의견 변경?

**[Optimistic Practitioner]**: 받아들여요. P1a 없이 P1c는 "본인이 만든 alias도 까먹는" 자기참조 함정이에요. P1a가 1차.

## 결론

**P1a → P1b → P1c 순.** P1a는 자동 생성 메커니즘 필수 (drift 방지). 만장일치.
