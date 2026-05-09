# Transcript — Topic 1: 문서 수명 기준 분리 원칙의 정당성

**Date**: 2026-04-19
**Topic**: 동결(frozen) 문서와 살아있는(living) 문서 분리 원칙이 본 케이스(Position C)에 정당한가
**Round**: 1 (합의 도달)

---

## Briefing

**[Optimistic Practitioner]**: Position C는 정보 아키텍처와 OSS 양쪽에서 표준 패턴이에요. Rust RFC는 병합 후 동결, `rust-lang/reference`는 living. VS Code wiki Roadmap, Babel/Turborepo 같은 monorepo도 동일 분리. claude-kit의 `docs/discussions/20260416_pm-agent-design/`는 이미 동결 사례로 superseded 마커까지 찍혔어요. 여기에 living roadmap까지 얹으면 한 폴더가 두 수명을 섞어버려서 관례 위반이에요. Position C는 이 문제를 lifecycle 축으로 자연스럽게 해결해요.

**[Critical Practitioner]**: 원칙 자체는 건전하지만 비용을 먼저 봐야 해요. claude-kit에 "living document" 선례가 없어요. 한 건을 위해 규약을 신설하는 모양새예요. 더 큰 우려는 W1-W8 매트릭스가 6개월 뒤에도 살아있을지 불확실하다는 것이에요. D1-D5가 다 구현되면 매트릭스는 그냥 아카이브되어야 해요. 그러면 living이라는 분류가 무의미해져요. **YAGNI**예요. 단일 파일에 `status: living | last-updated: YYYY-MM-DD` frontmatter만 박는 가벼운 대안도 있어요. 분리는 두 번째 매트릭스가 실제로 생길 때 해도 늦지 않아요.

## Q&A

**[Moderator]**: Critical의 YAGNI 우려에 대해 Doc Expert 의견은요?

**[Technical Documentation Expert]**: YAGNI는 보통 "지금 없는 기능"에 적용되는데, 여기서 분리는 **이미 발생한 두 종류 문서**에 대한 분류예요. 회고적이지 예측적이지 않아요. "Documents of Record" vs "Documents of Practice" 분리는 DITA의 topic type 분리와 동형이고, 둘은 권한·갱신·감사 모델이 다르니 한 폴더에 두면 정책 충돌이 생겨요. 토론 기록을 고쳐쓰면 "왜 그 결정을 했나" 추적성이 무너지고, 살아있는 매트릭스를 동결하면 진척 반영이 안 돼요. 둘 중 하나를 양보하는 비용이 분리 비용보다 커요.

**[Critical Practitioner]**: 그러면 6개월 뒤 W1-W8이 다 resolved되면 매트릭스는 어떻게 되나요? 분리 신설했는데 archive로 넘어가면 결국 living 분류가 일시적이라는 증거 아닌가요?

**[OSS Maintainer Expert]**: 좋은 질문이에요. 답은 — **매트릭스 자체가 아카이브되는 게 아니라, 그 안의 항목이 resolved 상태로 전환되고 새 항목이 추가**돼요. React `ROADMAP.md`도 2018년 항목들은 다 resolved지만 파일은 살아있어요. matrix는 컨테이너고, 항목이 갱신되는 거예요. living 분류는 컨테이너 자체에 적용돼요. 만약 thinking-tools 자체가 deprecated되면 그때 matrix도 frozen으로 전환하면 돼요 — 이게 정상 lifecycle이에요.

**[Plugin Ecosystem Expert]**: 추가로, 청자가 다른 게 핵심이에요. `docs/discussions/`는 GitHub 방문자(contributor)만 도달하고, plugin install된 사용자에겐 안 보여요. `thinking-tools/docs/`는 install 시 동기화돼서 사용자도 봐요. 두 청자, 두 위치 — Position C는 청자 분리를 자연스럽게 반영해요. Position B(통합)는 두 청자에게 같은 문서를 보여주게 되어 메시지가 흐려져요.

## Dialectic

**[Thesis — Optimistic]**: Position C 채택. IA·OSS 표준, 청자 분리 정합.

**[Antithesis — Critical]**: 거버넌스 부재 시 living document가 stale로 부패. 분리 자체보다 운영 메커니즘이 먼저.

**[Synthesis]**: Position C 채택하되 거버넌스 명시를 전제 조건으로 흡수. 구체:
1. frozen 문서에 명시적 마커 (`status: frozen` + `frozen_at` + `tracking_continued_in`)
2. living 문서에 owner + 리뷰 주기 frontmatter 필수
3. CONTRIBUTING.md에 1단락 운영 룰 추가

이 셋이 충족되면 Critical 우려는 절차적으로 봉합됨. 충족 안 되면 Position C도 무의미.

## 결론

**합의 (조건부)**: Position C 채택. 거버넌스 마커 3종 (frozen marker / living frontmatter / CONTRIBUTING 룰)을 동시 도입 전제.

**Confidence**: High (4명), Medium (Critical Practitioner — 거버넌스 실행 의지에 대한 유보)
