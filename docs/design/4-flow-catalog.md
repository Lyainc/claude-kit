# 4-흐름 카탈로그 (4-Flow Catalog)

**Status**: design · **Created**: 2026-06-05 · **Issue**: #170

> **Note**: 이 4-흐름 카탈로그는 사용자의 작업을 돕는 **논리적 뷰(Logical View)**이며, 플러그인이나 폴더의 **물리적 재구조화(Physical Restructure)가 아닙니다**. `claude-kit-boundary.md`에 정의된 5-레이어 구조와 단방향(harness -> leaf) 의존성 제약(CON-5)을 엄격히 준수하기 위한 근거 기록입니다.

이 문서는 사용자가 `claude-kit`의 기능을 직관적으로 사용할 수 있도록 4가지 주요 흐름(Flow)과 기존 5-레이어 간의 직교 매핑(Orthogonal Mapping)을 정의합니다. 

> **갱신 (2026-07-07)**: 아래 문장이 가리키던 #117의 multi-page 온보딩 마법사(setup-wizard, `claude-kit-welcome` 4번째 플러그인)는 실제로 만들어지지 않고 backlog로 닫혔어요(`docs/design/setup-wizard.md` SUPERSEDED 배너 참조). 실제 shipped된 건 훨씬 작은 `thinking-tools/hooks/session-start-welcome.sh`(1회성 discoverability 힌트, 위저드 규모 아님)뿐이라, 아래 "연결 지점" 서술은 실현 안 된 계획이에요 — 이 카탈로그 자체(4-흐름 매핑)는 여전히 유효하니 그 부분만 무시하세요.

이 매핑 모델은 ~~**#117 setup-wizard**(신규 사용자 온보딩 마법사)에서 각 사용자의 작업 유형에 맞는 도구 세트를 제안하는 연결 지점(Connection Point)으로 사용됩니다.~~ (위 갱신 참조 — 실현 안 됨)

## 4-흐름 <-> 5-레이어 직교 매핑표

| 4-흐름 (Logical Flow) | 목적 | 사용되는 5-레이어 (Physical Boundary) |
| --- | --- | --- |
| **사고/기획** (Thinking & Planning) | 모호한 아이디어를 구체화하고 스펙으로 확정 | ①인지, ②결정화·출력, ⑤실행 |
| **작업/폴리싱** (Work & Polishing) | 결과물을 생성하고 품질(QA)을 검증 및 리뷰 | ①인지, ②결정화·출력, ⑤실행 |
| **시각화** (Visualization) | 다이어그램, 차트 등을 통해 복잡도 해소 | ②결정화·출력 |
| **지식관리** (Knowledge Management) | 작업 이력을 세션/볼트로 보존 및 검색 | ③딜리버리, ④지식베이스 |

### 흐름별 대표 기능
- **사고/기획**: `build-spec`, `diverse-sampling`, `unknown-discovery` 등 (①인지, ②결정화)
- **작업/폴리싱**: `doc-polish`, `expert-panel`, `adversarial-review` 등 (①인지, ②결정화)
- **시각화**: `graphify(html)` (계획 — *claude-kit 플러그인에 미수록*; 현재는 사용자 글로벌 스킬로만 존재) 등 (②결정화)
- **지식관리**: `vault-bridge`, `obsidian-vault-manager` 플러그인의 전체 기능 (③딜리버리, ④지식베이스)

이 카탈로그는 구조의 종속성(CON-5)을 위반하지 않으면서 목적별 스킬 묶음을 뷰 형태로만 제공합니다.
