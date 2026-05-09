# Transcript 01 — 정체성·SoC·runtime 적합도 (C/D/E)

**[Moderator]**: 세 옵션의 도메인 정체성 적합도부터 평가.

**[Knowledge Management Expert]**: 정체성 분석:
- OVM = "Obsidian vault 지식 관리". 지식 단위 관리에 특화. 멀티 plan orchestration은 "프로젝트 관리" 도메인 → 스코프 크리프.
- thinking-tools = "사고 도구". 분석·토론 산출. 파일 쓰기 부재. PM write-heavy와 근본 불일치.
- 신규 플러그인 = 정체성 충돌 없음.

**[Plugin Architecture Expert]**: SoC 관점. D는 OVM 단일 책임 원칙 위반. E는 thinking-tools의 "순수 사고" 경계 파괴. C는 경계 명확, 다만 marketplace 혼잡·의존 복잡도 증가.

**[Project Manager]**: PM 도메인 6대 활동(감사·통합·의존성·아카이브·team dispatch·verifier)이 어떤 기존 플러그인에도 없음. 공백 지대. D/E는 "억지 배치".

**[Optimistic Practitioner]**: 사용자 비용 관점. 플러그인 3→4 증가는 체감 비용. D가 "이미 설치된 OVM에 추가"라 마찰 최소. 정체성 확장은 README로 해소 가능.

**[Critical Practitioner]**: "확장 정의"가 스코프 크리프 시작점. 1년 후 OVM이 "vault 관련 뭐든 하는 플러그인"이 되면 유지 불가.

**[LLM Orchestration Expert]**: runtime 라우팅 관점. 에이전트 description 키워드 경쟁이 핵심. D는 vault-knowledge-manager와 "프로젝트"·"플랜" 키워드 중복 가능성. E는 thinking-tools에 plan 키워드 없어 도입 부담 적으나 사고 도구 멘털 모델 붕괴. C가 가장 깨끗.

**[KM]**: E는 파일 I/O 부재로 실질 불가능.

**[PA]**: 동의. E 탈락.

**[Moderator]**: E 탈락 합의. C vs D는 TOPIC 3에서 runtime 성능 깊이 비교.

**결론**: E 탈락. C/D 속행.
