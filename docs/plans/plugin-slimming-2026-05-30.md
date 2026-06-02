# 플러그인 슬림화 개발계획 (2026-05-30) — ✅ 완료

> **상태 (2026-06-03 갱신)**: Track A~E 전부 완료, thinking-tools 2.0.0(BREAKING) 범프로 마감. 잔여는 보조파일 정리 **#110** 하나. 완료된 처방 상세(트랙별 변경 표·검증 절차)는 제거하고 트랙→커밋 매핑과 잔여만 남김.

## 목표 (달성)

claude-kit 3개 배포 플러그인(thinking-tools, obsidian-vault-manager, vault-bridge)의 **사용자 대면 복잡도**(플래그·점수·모드)를 낮추고 Claude Code 네이티브 UX로 전환. 줄 수 절감이 아니라 사용자가 들고 있어야 하는 개념 수 축소가 본질.

## 트랙별 완료 현황

| 트랙 | 내용 | 상태 | 커밋 |
|---|---|---|---|
| A | doc-polish 재포지셔닝 — Layer 2 trope 양도 → "구조/품질 에디터", `llm-expression-blacklist.md`·`POLISH_REPORT.md` 제거, Humanize KR 핸드오프 명시 | ✅ | `20e0fb1` |
| B | 플래그 제거 — thought-chain·spec-first·adversarial-review·diverse-sampling·expert-panel CLI 플래그 → 자연어 감지 | ✅ | `faf3595`·`a1562a1`·`32cefcf`·PR #109(`117c83d`) |
| C | 점수 표면 노출 제거 — Ambiguity/Weighted Score/Depth % → 정성 라벨(탄탄·보통·취약 등), 내부 STATE는 gate/compaction용으로 유지 | ✅ | `32cefcf` |
| D | 네이티브 UX 전환 — ASCII 진행 표시 최소화 | ✅ | B/C에 흡수 |
| E1·E2 | audit 단일출처화 — SKILL.md 규칙 본문 → `vault-audit-rules.md` canonical 포인터, REPORT 템플릿 압축 | ✅ | `32cefcf` |
| E2b | `7 types`→`8 types` 모순 수정 + E8 backfill + 식별자 통일 | ✅ | `faf3d6a`·`78f21c6`·`d7d318e` |
| E3 | 레거시 제거 — `auto_capture` deprecation alias | ✅ | `69bcf1c` |
| B5 | 메이저 범프 + breaking 마이그레이션 노트 | ✅ | thinking-tools 2.0.0 |

## 잔여 (1건)

- **#110** (open, chore) — SKILL.md *본문*은 자연어 전환됐으나 보조파일(examples/reference/templates) 17줄에 제거된 플래그 참조 잔존. 사용자가 그걸 읽으면 죽은 플래그를 배우게 됨 → slimming 목표 위반이라 정리 필요.

## 제외(철회) 항목 — 재론 방지

| 항목 | 제외 사유 |
|---|---|
| cross-plugin vault "통합" | OVM은 vault 상주, vault-bridge는 외부 접촉 — 다른 plane이라 중복 아님 |
| thinking-tools 8개 스킬 통합 | 목적/과정/결과 상이하면 유지 |
| docs/archive 삭제 · telemetry 정리 | 프로젝트 인프라, 런타임 surface 아님 |
| plan-doc-syncer 대수술 · audit 대폭 리라이트 | 기능적으로 정당, 부분 슬림화만(완료) |

---
*완료 마감 2026-06-03. audit는 277줄(목표 ~210-230은 근사치, 포인터화 본질은 달성). 후속 작업은 레이어 재설계 Epic #108(별도 트랙).*
