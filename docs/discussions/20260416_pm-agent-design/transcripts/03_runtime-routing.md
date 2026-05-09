# Transcript 03 — Runtime 라우팅 성능 (C vs D)

**[Moderator]**: runtime 소환 신뢰도 기준 비교.

**[LLM Orchestration Expert]**: 핵심 변수 3가지 —
1. Description 키워드 정확도
2. 경쟁 에이전트 수 (동일 키워드 공유)
3. Proactive 트리거 패턴 작동

| 옵션 | 키워드 경쟁 | 네임스페이스 | Proactive 적합 |
|------|-----------|------------|---------------|
| C | 낮음 | 독립 | 높음 |
| D | 중간(OVM 3 에이전트 혼잡) | OVM 공유 | 중간 |

**[Plugin Architecture Expert]**: D의 키워드 혼잡 완화 가능 — OVM 기존 두 에이전트 description 경계 재정의. 하지만 OVM README·CLAUDE.md 확장 서술 필요. 부채 발생.

**[Optimistic Practitioner]**: C가 이론 우수해도 사용자 "어느 플러그인 언제?" 고민이 UX 손실. D는 "vault 작업 = OVM 하나" 멘털 모델 유지.

**[Project Manager]**: PM 작업은 vault 국한 아님. 코드 리포 docs/, .omc/plans/ 등 vault 외부 파일도 다룸. D면 "OVM인데 vault 밖 건드림" 혼선.

**[KM Expert]**: PM 동의. OVM = vault-bound. PM = vault-adjacent. 도메인 범위 다름.

**[Critical Practitioner]**: C 단점은 신규 플러그인의 채널·문서·버전 관리 재구축. 첫 1.0.0 릴리스 위험.

**[LLM Orchestration]**: 완화책 — C 플러그인을 OVM·vault-bridge와 peer-dependency 선언. marketplace에서 세트 표시. "claude-kit 세트 설치 = 4 플러그인 한꺼번에".

**[Moderator]**: 정리 — runtime·정체성·도메인 범위 모두 C 우세. UX·설치 비용의 D 우위는 peer-dep + 세트 릴리스로 완화. C 잠정 채택.

**전원 동의.**

**결론**: C 잠정 우세. TOPIC 4 유지보수 전망에서 최종 확정.
