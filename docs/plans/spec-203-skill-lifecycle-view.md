# spec — telemetry per-skill lifecycle 파생 뷰 (#203 / G17)

spec 슬라이스 산출물 (메인 컨텍스트 작성, 2026-06-10). 구현 계약이에요 —
impl 슬라이스는 이 스펙과 G17 goal-doc DoD를 그대로 따라요.

## 1. 무엇을

`telemetry/scripts/report.py`에 **lifecycle 파생 뷰** 섹션을 추가해요. 기존 top-N
집계는 count 0인 스킬을 구조적으로 못 보여주니(Counter에 키 없음), 카탈로그를
별도로 스캔해 이벤트와 대조해요.

## 2. 카탈로그 스캔 (source of truth)

- 레포 루트 기준 `*/skills/*/SKILL.md` glob 스캔 → `{plugin}/{skill}` 식별자 목록.
- plugin 이름은 디렉토리명(예: `thinking-tools`), skill 이름은 스킬 디렉토리명.
- `plugin-map.json`은 카탈로그가 아니라 bare-name lookup 보조 — 카탈로그 출처로
  쓰지 않아요.
- distilled-skill(~/.claude/skills) 스캔은 **범위 외** (U4, P3 재상정).

## 3. 파생 뷰 출력 (3개 서브섹션)

이벤트의 `qualified_name`(또는 `plugin`+`name`)을 카탈로그 식별자와 매칭해요:

1. **never-fired**: 카탈로그에 있으나 (조회 윈도 내) 이벤트 0건인 스킬 전부.
2. **last-used > Nd**: 마지막 이벤트가 N일 이전인 스킬 (기본 N=14, 기존 --since와
   별개 파라미터 `--stale=Nd` 또는 상수 — 구현 단순성 우선, CLI 추가는 선택).
3. **bottom-N**: 이벤트 있는 스킬 중 최저빈도 N개 (기본 5).

## 4. 필수 출력 문구 (DoD 하드 조건)

- 캐비앗(하드코딩): `측정범위: claude-kit 레포 내 세션 기준 (telemetry Option A)`
- 해석 가이드(하드코딩, 뷰 하단):
  - thinking-tools류(in-repo 사용 본질)는 never-fired를 죽은 표면 신호로 우선 해석
  - vault-bridge/OVM류(타 프로젝트 사용 주류)는 측정범위 밖 사용 가능성을 먼저 의심

## 5. 불변 조건

- events jsonl **읽기 전용** — 쓰기 경로·스키마·파일 추가 0.
- 기존 출력 섹션(top-N, outcome, latency)은 동작 불변 — 파생 뷰는 추가만.
- `--format=json`이 이미 있으면 lifecycle 뷰도 json에 포함(키: `lifecycle`),
  table이면 사람이 읽는 섹션으로.
- stdlib only (기존 report.py와 동일).

## 6. 테스트 계약 (test-report.py 확장)

- zero-count 가시화: 카탈로그에만 있는 가짜 스킬 fixture → never-fired에 등장.
- 캐비앗 검증: 출력에 측정범위 문구 포함.
- 기존 케이스 전부 green 유지.
