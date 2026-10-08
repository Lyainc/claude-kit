# #811 vault 쓰기 가드 비용 측정

판정 보존 비교와 두 번의 교차 측정에 근거해 이 최적화를 **채택**한다. 일반적인 단일 JSON
입력의 jq 추출을 한 번으로 묶고, 정상 경로의 cut/basename을 Bash 내장 확장으로 바꿨다.
실경로 Python과 이름 검사 Python은 각각 유지한다. Bash 탐지 알고리즘, 경로 판정, 계약·이름
정책, 출력 문구와 JSON 생성은 그대로다. 새로운 의존성·상주 프로세스·경로 pre-filter는 없다.

## 기준과 변경 범위

- 실제 시작 기준과 fetch로 확인한 최신 main: `ac95e788018c9e1fc171bc432ac2505e2b41b4d7`.
- 브랜치: `codex/811-vault-guard-cost`.
- 전용 worktree: `/Users/gowid/.codex/worktrees/811-vault-guard-cost/claude-kit`.
- 시작 시 열린 PR #828 (#804), #829 (#825), #830 (#827·#750)의 변경 파일을 확인했다.
  이번 두 실행/회귀 파일 및 이 폴더와 중복은 없었다.
- 최종 변경 범위: `vault-bridge/hooks/pre-write-guard.sh`,
  `vault-bridge/scripts/test/test-pre-write-guard.py`, 이 작업 전용 측정 폴더만이다.
  원래 main checkout의 Seed 변경과 다른 작업 worktree는 건드리지 않았다.
- 기준 훅은 위 커밋에서 추출한 그대로이며 수정 훅의 측정 시점 해시는 아래와 같다.
  최종 독립 검토는 같은 기준의 diff 및 이 측정·회귀 자료를 대상으로 1회만 수행한다.

## 환경과 방법

- 2026-10-08 같은 macOS arm64 머신, Bash·jq는 시스템 실행 파일을 사용했다.
  측정의 훅 Python은 uv가 PATH에 넣은 관리 Python **3.12.14**였고, jq는
  `jq-1.7.1-apple`이다. 정확한 실행 경로와 버전은 JSON의 `binaries`/`versions`에 있다.
  아래 별도 호환성 실행에서는 테스트 드라이버 안에서 PATH를 `/usr/bin:/bin`으로 고정해
  훅의 `python3`가 시스템 Python **3.9.6**을 실행하도록 했다.
- 임시 vault에 `.obsidian`, `sources`, `notes`, `wiki`, `assets` 디렉토리만 만들었다.
  Write/Edit/Bash payload는 가드의 stdin으로만 전달했다. payload가 표현하는 실제 파일 쓰기와
  Bash 명령은 실행하지 않았다. 이는 Codex 셸에서 훅을 직접 호출한 증거이며 Codex 네이티브
  훅 등록이나 런타임 강제 차단을 검증한 결과가 아니다.
- 입력 14종, 세션 2회. 각 세션·입력·판별판마다 워밍업 6회 후 120회 측정했다.
  입력별 판별판당 측정 표본 240개, 총 측정 6,720회와 워밍업 336회다.
- 각 반복에서 baseline/candidate를 연이어 실행하고 선후 순서를 번갈아 바꿨다.
  두 번째 세션에서는 입력 순서도 뒤집었다. `perf_counter_ns()`로 Bash 프로세스 시작 전부터
  종료·stdout/stderr 캡처까지 재고, 표본별 종료 코드·stdout JSON·stderr 일치도 함께 확인했다.
- 상위 지연은 nearest-rank p95다. 최대값·모든 개별 표본·세션별 중앙값/p95·환경 버전·시스템
  load average는 `measurements.json`에 있다. 별도 병렬 에이전트는 측정 중 실행하지 않았다.
  다른 세션의 활동이나 OS 부하는 통제하지 못했으므로 지연의 일반화는 하지 않는다.
- 호출 수는 타이밍 종료 후 임시 PATH wrapper로 외부 실행 파일 호출을 판별판마다 3회 세어
  동일한 수임을 확인했다. outer Bash와 cat/jq/python3/cut/basename을 포함한다.
  Bash 내부 command substitution/process substitution의 fork·subshell 수를 포함한 총 OS
  프로세스 수는 아니다. 측정에 wrapper를 사용하지 않았다.

## 결과

단위는 ms이며, 아래는 두 세션을 합친 표본이다. 개선율이 음수면 느려진 것이다.

| 입력 | 중앙값 기준 → 수정 | p95 기준 → 수정 | 중앙값 개선율 | 표본 기준 / 수정 | 외부 실행 호출 기준 → 수정 |
| --- | ---: | ---: | ---: | ---: | ---: |
| write_valid | 48.00 → 36.70 | 69.80 → 48.55 | 23.5% | 240 / 240 | 10 → 5 |
| edit_valid | 49.00 → 37.13 | 81.34 → 68.43 | 24.2% | 240 / 240 | 10 → 5 |
| write_deny | 32.22 → 22.83 | 40.94 → 27.82 | 29.2% | 240 / 240 | 9 → 5 |
| warn_bad_name | 49.87 → 38.45 | 78.23 → 52.31 | 22.9% | 240 / 240 | 11 → 6 |
| strict_bad_name | 47.30 → 36.18 | 73.53 → 50.66 | 23.5% | 240 / 240 | 10 → 5 |
| assets | 32.07 → 21.14 | 56.22 → 31.75 | 34.1% | 240 / 240 | 9 → 4 |
| contract_off | 46.78 → 35.29 | 65.37 → 45.81 | 24.6% | 240 / 240 | 10 → 5 |
| bash_deny | 35.69 → 28.36 | 41.13 → 32.75 | 20.5% | 240 / 240 | 8 → 5 |
| bash_read | 33.47 → 26.03 | 41.30 → 32.53 | 22.2% | 240 / 240 | 7 → 4 |
| bash_main | 11.68 → 9.30 | 15.00 → 12.87 | 20.3% | 240 / 240 | 4 → 3 |
| irrelevant | 8.42 → 8.53 | 11.54 → 12.74 | -1.3% | 240 / 240 | 3 → 3 |
| disabled | 3.83 → 3.83 | 4.72 → 4.51 | 0.0% | 240 / 240 | 1 → 1 |
| missing_vault | 8.35 → 8.57 | 10.94 → 11.20 | -2.6% | 240 / 240 | 3 → 3 |
| malformed | 8.97 → 11.97 | 17.70 → 24.30 | -33.4% | 240 / 240 | 3 → 4 |

두 세션 각각에서도 정상 Write/Edit와 계약·이름 검사 및 Bash 탐지 경로의 중앙값 개선이
일관됐다. 정상 Write/Edit는 외부 실행 호출이 10회에서 5회로, Bash 탐지 경로는 7/8회에서
4/5회로 줄었다. 정상 Write/Edit 중앙값은 이 환경에서 50ms 미만이지만 모든 표본이나 모든
환경에서 50ms 미만이라고 주장하지 않는다.

kill switch는 동일한 경로다. 무관한 도구·없는 vault는 호출 수가 같고 중앙값의 작은 차이를
개선으로 보지 않는다. malformed JSON은 추가 batch 시도 후 기존 파싱으로 돌아가므로 jq
한 번이 더 들고 약 3ms 느려진다. 다중 JSON·비정상 필드 타입·NUL도 기존 동작을 보존하는
fallback을 사용한다. 이 보수적인 비용을 남겨 정상 실행 경로의 반복 비용을 낮추는 선택이다.
입력 분포를 가정한 전체 평균 개선율은 계산하지 않았다.

## 동작 보존과 검사

`parity.txt`는 같은 임시 vault·payload·환경에서 기준판과 수정판의 전후 비교를 기록한다.
기존 Bash 쓰기/읽기·리다이렉션·대상 디렉토리 옵션, symlink 실경로, assets 예외,
enforce/warn/off, whitelist·strict naming, warn 메시지 병합·단일 JSON, 조기 종료를 포함한다.
추가 사례는 Write/Edit의 symlink 양방향 경로, 식별 필드 우선순위, 특수문자·개행·NUL,
malformed/다중 JSON·필드 타입, unknown mode, warn+strict, jq/Python 실패를 고정한다.
stdout는 빈 출력 또는 JSON 전체 값으로 비교하고 stderr는 문구 그대로 비교한다.
셸 오류의 스크립트 경로와 소스 줄 번호만 정규화한다. validation Python 실패는 임시 상태를
매번 초기화해 따로 비교한다. 종료 코드 0의 deny JSON과 strict exit 2를 구별한다.

검사 명령과 원문 출력은 `regression.txt`, `parity.txt`, `python39.txt`에 있다.

```bash
uv run --no-project python vault-bridge/scripts/test/test-pre-write-guard.py
PRE_WRITE_GUARD_BASELINE=/private/tmp/811-pre-write-guard-baseline.sh \
  uv run --no-project python vault-bridge/scripts/test/test-pre-write-guard.py
PRE_WRITE_GUARD_BASELINE=/private/tmp/811-pre-write-guard-baseline.sh \
  uv run --no-project /usr/bin/python3 -c 'import os, runpy; os.environ["PATH"]="/usr/bin:/bin"; print("Forced hook PATH:", os.environ["PATH"], flush=True); runpy.run_path("vault-bridge/scripts/test/test-pre-write-guard.py", run_name="__main__")'
uv run --no-project /usr/bin/python3 -c 'import os, runpy; os.environ["PATH"]="/usr/bin:/bin"; runpy.run_path("docs/performance/vault-write-guard-811/benchmark.py", run_name="__main__")' --help
uv tool run ruff check vault-bridge/scripts/test/test-pre-write-guard.py \
  docs/performance/vault-write-guard-811/benchmark.py
bash -n vault-bridge/hooks/pre-write-guard.sh
git diff --check
```

PATH를 드라이버 내부에서 고정한 별도 실행으로 Python 3.9.6에서 전체 회귀 파일과 훅의
embedded Python을 실제로 실행했고, 기준판 비교 131회와 별도 validation 실패도 통과했다.
`uv run --no-project /usr/bin/python3`만으로는 훅의 PATH를 보장하지 않는다.
측정 스크립트는 3.9.6으로 import/CLI도 확인했다. 루트 검사 스크립트·VALIDATION·CI·manifest·
version·SKILL·portability 계약·사용자 정책·설치본은 수정하지 않았다.

## 재현

저장소의 변경된 전용 worktree에서 다음 명령을 실행한다. baseline은 저장소에 별도 복제본을
등록하지 않고 Git의 실제 시작 커밋에서 얻는다. 기존 기록을 보존하려면 output을 다른 임시
파일로 지정한다. 측정 중 추가 검사·에이전트는 실행하지 않는다.

```bash
baseline_file="$(mktemp /tmp/vb-811-baseline.XXXXXX)"
git show ac95e788018c9e1fc171bc432ac2505e2b41b4d7:vault-bridge/hooks/pre-write-guard.sh > "$baseline_file"
PRE_WRITE_GUARD_BASELINE="$baseline_file" \
  uv run --no-project python vault-bridge/scripts/test/test-pre-write-guard.py
uv run --no-project python docs/performance/vault-write-guard-811/benchmark.py \
  --baseline "$baseline_file" --candidate vault-bridge/hooks/pre-write-guard.sh \
  --output /tmp/vb-811-reproduction.json --warmup 6 --repetitions 120 --sessions 2
```

측정 입력과 환경 override는 JSON의 `inputs`에 임시 루트만 `<TEMP>`로 바꾸어 기록했다.

기준/수정 훅 SHA-256:

```text
baseline: 824fd57f697eaf23b98bf8f7709909fca42641f67d951b35a5c58ed085546afc
candidate: 0e0dde81828a2d1d84dde55425ca616505ee4575d82b68d2f05d0a86dacaabbf
```

세션 1 load average (1/5/15분): 시작 [4.08642578125, 5.8984375, 6.40185546875], 종료 [4.8359375, 5.60986328125, 6.2275390625].

세션 2 load average (1/5/15분): 시작 [4.8359375, 5.60986328125, 6.2275390625], 종료 [4.4755859375, 5.30029296875, 6.03466796875].


## 독립 검토 1회와 후속 직접 확인

기준 `ac95e788018c9e1fc171bc432ac2505e2b41b4d7`의 최종 실행 코드·테스트 diff와 측정 자료를
독립 검토자에게 1회 전달했다. 실행 코드·테스트 SHA-256은 아래 값과 같으며 검토 이후
변경하지 않았다. 스타일 지적은 제외했다.

```text
hook: 0e0dde81828a2d1d84dde55425ca616505ee4575d82b68d2f05d0a86dacaabbf
test: d7ff6fc5437c7eb4cd1f785597ac98b645388026c404146dd73c7abb12987d3e
```

검토자는 허용·차단 판정의 기능적 회귀를 찾지 못했고, P2로 측정 Python 환경 설명 및
3.9 증거 부족을 지적했다. 최초 보고서의 3.9 측정 주장은 잘못이었다. 측정 JSON 자체는
처음부터 실제 uv 관리 Python 3.12.14를 기록했다. 따라서 위 환경 설명을 바로잡고,
메인 작업자가 PATH를 고정한 3.9.6 전후 회귀를 추가 실행해 `python39.txt`를 갱신했다.
실행 코드·테스트 및 성능 표본은 변경하지 않았다. 이 후속 정정·증거는 메인 직접 확인이며
추가 독립 검토를 수행한 것으로 세지 않는다.

검토자의 표본 요약 재계산용 uv 실행은 uv 캐시 접근 제한으로 실패했다. 지시대로 재시도하지
않고 직접 코드·기록 검사로 마쳤다. 독립적인 자동 표본 재계산은 미검증으로 남는다.
검토 당시 전체 diff SHA-256은 `fa87b0fbf27f37f79988d20b5b78aaa3498d4cc89ac7fe4f848d57be7695c10b`였으며,
환경 설명 및 `python39.txt` 정정 후 최종 자료 diff는 별도로 저장한다.
