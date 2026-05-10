---
created: 2026-05-10
tags: [vault-bridge, ux, plan, save-plan-doc]
type: plan
status: active
---

# save-plan-doc UX 개선 계획

## 배경

`vault-bridge`의 plan-doc 캡처 흐름이 사용자 경험 측면에서 다섯 가지 마찰을 만든다 (마지막 하나는 UX보다 *모델 정의* 차원의 문제).

### 1. `auto_capture` 명명 모호성

`.vault-link`와 `{vault_path}/_index.md` 양쪽이 동일한 키 이름(`auto_capture: true`)을 사용한다. 두 권한은 방향과 주체가 다른데 이름이 같아 사용자가 구분하지 못한다.

| 위치 | 실제 의미 | 권한 주체 | 관리 도구 |
|---|---|---|---|
| `.vault-link` | 이 프로젝트의 plan을 vault로 *내보내기* 허용 (outbound) | 프로젝트 오너 | vault-bridge |
| `{vault_path}/_index.md` | 이 vault project가 외부 스냅샷 *받기* 허용 (inbound) | vault 오너 | OVM |

`obsidian-vault-manager/skills/project/SKILL.md`의 `/project --enrich auto_capture=true`만 L2를 변경할 수 있고, vault-bridge는 read-only다 (`vault-bridge/agents/vault-searcher.md` Forbidden writes). 같은 이름이면 사용자는 *어느 도구가 무엇을 책임지는지*도 구분 못 한다.

또한 이름이 `auto_capture`인데 실제 동작은 "캡처 자동화"가 아니라 "게이트 자동 통과"다 (`commands/save-plan-doc.md:36-87`, `plan-doc-syncer.py:411-427`). "켰는데 왜 자동으로 안 되지?" 헷갈릴 여지가 있다.

### 2. AskUserQuestion 임팩트 불투명

게이트 미활성 시 표시되는 현재 메시지는 결정의 임팩트를 옵션 라벨 한 줄에 압축한다. 사용자가 모르는 네 가지:

1. 무엇을 결정하는 건지 ("L1 게이트", "auto_capture"가 뭔지)
2. 어떤 데이터가 영향받는지 (어느 파일이 vault로 갈지)
3. 결정의 지속 범위 (이번 한 번? 영구?)
4. 되돌리는 방법

L2 메시지의 추가 갭: "obsidian-vault-manager로 `_index.md`를 수정"만 안내하고 *어느 명령*으로 어떻게 수정하는지가 없다.

### 3. discover 노이즈 (89개 폭격)

기본 include 패턴(`docs/discussions/**/*.md`, `docs/design/**/*.md`, ...)이 광범위해서 `docs/` 하위 토론 transcript까지 모두 후보로 잡힌다. 실제 dogfooding 결과 89개 후보가 발견됐다. "전체 저장" 옵션이 사실상 vault 폭격 트리거가 된다.

### 4. plan mode ↔ save-plan-doc 의도 단절

dogfooding 시나리오: 사용자가 plan mode에서 plan 작성 → `/save-plan-doc`로 vault 박제 (의도: 다음 세션에서 작업) → plan mode 종료 시 native UX가 "지금 진행할까?"를 묻는다. 사용자 의도(save = defer)와 시스템 질문이 정반대라 같은 의도를 두 번 표현해야 한다. save-plan-doc 호출 자체가 "지금 작업 안 함" 시그널인데 시스템이 그걸 못 읽는다.

### 5. snapshot 누적과 vault git의 책임 중복

현재 모델은 같은 plan의 시점별 박제를 vault 내에 `-v{N}` 파일로 누적한다(`plan-doc-syncer.py:702-723`). 동시에 vault 자체가 git으로 관리되어 *vault 전체 파일의 commit 히스토리*가 따로 쌓인다. 두 메커니즘이 plan-doc 도메인 한정으로는 부분 중복이다:

| 측면 | vault 내 `-v{N}` 누적 | vault git |
|---|---|---|
| 대상 | 같은 plan의 시점별 박제 | vault 전체 파일 시스템 |
| 추상 레벨 | 파일 일등 객체 (Obsidian 직접 탐색) | 메타 레이어 (git tooling 필요) |
| 시점 추적 | filename에 v1/v2 | git log/blame |
| 누적 비용 | vault 디렉토리 비대 | git 객체 (압축됨) |

`20_Projects/claude-kit/`에 이미 session 노트 8개가 누적된 패턴이 plan에도 일어나면, N달 후 같은 plan의 v1~vN이 한 디렉토리에 쌓여 "현재 정사가 무엇인지" 한눈에 안 보인다. snapshot이 박제(immutable)인지 정사 미러(mutable)인지 spec이 명확히 선언하지 않은 상태다.

## 결정

### D1. frontmatter 키 분리 (snapshot_export / snapshot_import)

```yaml
# .vault-link (프로젝트 측 — outbound, vault-bridge 관리)
snapshot_export: true

# {vault_path}/_index.md (vault 측 — inbound, OVM 관리)
snapshot_import: true
```

- `snapshot`이라는 어휘가 frontmatter에 이미 들어있어 일관성이 있다.
- `export` / `import`는 방향이 즉시 보인다.
- 책임 주체 분리도 frontmatter 차원에서 시각화된다.
- `auto_capture`는 deprecated alias로 한 동안 인정 + syncer가 사용 시 stderr 경고.

### D2. AskUserQuestion 메시지 임팩트 명시화

본문에 다음을 포함한다:

- **무엇이 일어나는지**: "plan/design 파일을 vault에 스냅샷으로 저장하려고 합니다."
- **영향받는 데이터**: discover 결과를 본문에 직접 표시 ("발견된 후보 (N개): ...")
- **무해성 보장**: "원본은 수정되지 않습니다"
- **결정 주체 (L2 한정)**: "vault 오너만 변경할 수 있습니다"
- **L2 actionable 명령**: "권한을 켜려면 `/project {name} --enrich auto_capture=true` 실행 (vault 오너만)"

각 옵션 description에 다음을 포함한다:

- **지속 범위**: "이후 모든 호출이 통과" vs "이번 1회만"
- **부수 효과**: "SessionEnd 안내 활성화"
- **되돌리는 방법**: "`.vault-link`에서 해당 줄 제거"

L2는 "권한 켜고 계속" 옵션을 두지 않는다 — vault 오너만 변경할 수 있기 때문. 본문에 그 이유를 명시한다.

### D3. trigger 자동화는 별도 플래그 (옵션, 후순위)

`auto_sync_on_session_end: true`를 별도 키로 추가한다. `snapshot_export`는 게이트 통과만 담당하고, SessionEnd 자동 syncer 실행은 이 플래그로 분리한다. 권한 레벨이 다르기 때문이다.

- `snapshot_export` = 호출 시 마찰 제거 (수동 트리거)
- `auto_sync_on_session_end` = 트리거 자체 자동화

### D4. plan mode ↔ save-plan-doc 의도 연결

#### D4-A. `/save-plan-doc` 첫 단계에 의사 명시 옵션 추가 (즉시 적용)

명령 호출 직후 (Step 1 직후, 게이트 체크 직전) AskUserQuestion 한 단계 추가:

> 이 plan을 어떻게 진행할까요?

옵션:

| label | description |
|---|---|
| **지금 이번 세션에서 작업** | 저장 + 진행. 결과 안내에 "ExitPlanMode → 진행 선택" 표시. |
| **다음 세션으로 미룸** (저장만) | 저장 + 결과 안내에 "ExitPlanMode → 진행 안 함 선택" 표시. |
| **취소** | 저장 안 함. |

이 단계는 사용자 의도를 시스템에 들여보내는 핵심 — 결과 메시지 마지막 안내 문구가 의도에 맞춰 분기된다. plan mode 비활성 시에도 작동(안내 문구만 무해하게 무시됨).

#### D4-B. ExitPlanMode PostToolUse 훅 통합 (검토 후 진행)

PostToolUse 훅으로 ExitPlanMode 결과를 가로채서 한 번에 의도 받기:

> plan mode가 종료되었습니다. 이 plan을 어떻게 처리할까요?
> - 지금 작업 — 코드 변경 진행
> - 저장하고 다음 세션 — `docs/plans/{auto-slug}.md`에 저장 + vault에 박제
> - 폐기 — 아무것도 저장 안 함

"저장하고 다음 세션" 선택 시 자동으로:
1. plan 텍스트를 `docs/plans/plan-YYYY-MM-DD-{slug}.md`에 저장
2. `/save-plan-doc` 흐름 trigger
3. 세션은 그냥 종료

**전제 조건 (PoC 필요)**:
- PostToolUse 훅이 ExitPlanMode 결과를 가로챌 수 있는가
- plan mode 활성 상태를 환경변수/transcript로 감지 가능한가
- 훅에서 AskUserQuestion 발화 가능한가 (plan mode 종료 시점)

**Fallback 트리거**: PoC에서 위 전제 중 하나라도 미충족 시 D4-B 폐기, D4-A로 만족.

**우선순위**: D4-A 먼저 구현 → 정착 후 D4-B PoC → 가능 시 점진 전환.

### D5. discover 노이즈 완화

세 가지 조합:

#### D5-a. 임계치 경고 (즉시 적용)

discover 결과 N개 (기본 10개) 초과 시 AskUserQuestion 본문에 경고 표시:

> 발견된 후보가 많아요 ({count}개). 의도하지 않은 파일이 포함됐을 수 있습니다.
> 카테고리별 분포:
>   - docs/design/: 1개
>   - docs/discussions/.../SUMMARY.md: 14개
>   - docs/discussions/.../UNRESOLVED.md: 14개
>   - docs/discussions/.../transcripts/: 60개
>   - 기타: ...

#### D5-b. 최근 수정 필터 옵션 (즉시 적용)

`/save-plan-doc --recent {hours}` 인자로 mtime 필터. 기본은 비활성 (전체). 사용자가 의도적으로 좁히고 싶을 때 사용.

#### D5-c. transcripts 기본 제외 (검토 후)

`docs/discussions/**/transcripts/**`는 default exclude에 추가. transcripts는 의사결정 raw 자료라 *결과 plan과 분리*되는 게 자연스러움. backwards compat 우려가 있어 v2.0 메이저 단계에서 적용.

**우선순위**: D5-a + D5-b 먼저 (즉시). D5-c는 사용 패턴 관찰 후.

### D6. snapshot 모델 재정의 (결정 보류, 옵션 검토)

이건 UX 마찰이 아니라 spec 정의 결정이다. "vault snapshot은 박제(immutable)인가, 정사 미러(mutable)인가?"를 먼저 답해야 다른 결정이 정합적이 된다.

#### 검토 옵션

**D6-A. 현재 (누적) 유지**
- `-v1, -v2, -v3` 파일 누적, vault git은 별개 백업.
- 장점: vault 안에서 wikilink·검색으로 시점 비교 가능.
- 단점: 디렉토리 비대 + vault git과 부분 중복.

**D6-B. 덮어쓰기 (정사 미러)**
- vault에 plan 한 파일만. 같은 source path → 같은 vault filename → 덮어쓰기.
- vault git이 plan 변천 추적 (git을 본래 목적대로 사용).
- 장점: 단순. vault 디렉토리 깔끔. "현재 정사" 명확.
- 단점: snapshot immutability 약화. vault-searcher Forbidden writes 룰과 시맨틱 충돌(plan-doc-syncer는 vault-searcher 안 거치므로 기술적으로는 가능).
- `captured_at` / `source_commit` / `source_stale_risk` 메타는 frontmatter에 그대로 유지 — vault git commit과 함께 보면 "이 vault 시점에 외부 정사는 어땠는지" 추적 가능.

**D6-C. 하이브리드 (기본 덮어쓰기 + 명시적 fork)**
- 기본 덮어쓰기, `--keep-history` 플래그 시에만 누적.
- 장점: 일반 use case 단순, 필요 시 누적 가능.
- 단점: 모드 두 개라 사용자가 매번 결정해야 함.

**D6-D. 메타 압축**
- vault에 한 파일 (덮어쓰기).
- 이전 버전들은 frontmatter에 `previous_captures: [{commit, captured_at, ...}]` 메타로 누적.
- 장점: 단일 파일 + 박제 메타 보존.
- 단점: frontmatter 비대. Obsidian이 메타에서 시점 비교 UX 미지원.

#### 권장 (저자 의견)

**D6-B (덮어쓰기)** — vault git이 이미 시점 추적 정사 인프라이고, vault는 *현재 정사*만 명확히 보여주는 게 사용자(Obsidian)에게 친절하다. "예전 plan은 git log"가 git을 본래 목적대로 쓰는 방식이다.

#### 결정 절차

이 결정은 다른 phase와 직교라 병행 가능하지만, 채택 시 영향이 spec 차원이라 별도 합의 단계 필요:

1. snapshot 모델 정의(immutable/mutable) 선언을 vault-bridge spec(`vault-bridge/README.md` §3.4 또는 별도 §)에 명문화.
2. 채택 안에 따라 `plan-doc-syncer.py`의 `_resolve_collision_free_path` 동작 변경 또는 유지.
3. `vault-searcher.md` Forbidden writes 룰과의 정합성 재검토 (plan-doc는 예외인지, 아니면 룰을 시맨틱 분리할지).

**우선순위**: 다른 phase(D1~D5)와 독립. 별도 RFC 또는 discussion으로 분리해 결정한 뒤 phase 추가.

## 실행 계획

### Phase 1 — 키 분리 + alias 호환성 (D1)

**대상 파일**:
- `vault-bridge/scripts/plan-doc-syncer.py`
- `vault-bridge/commands/save-plan-doc.md`
- `vault-bridge/hooks/session-end-pre.sh`

**변경**:
1. `_check_gate_l1` / `_check_gate_l2`가 신규 키(`snapshot_export` / `snapshot_import`) 우선 인식, 없으면 `auto_capture` alias.
2. alias 사용 시 stderr deprecation 경고.
3. `session-end-pre.sh` grep 패턴을 신규 키 + alias 둘 다 매치.
4. `save-plan-doc.md` Step 2 본문에서 신규 키 사용.

### Phase 2 — AskUserQuestion 메시지 재작성 (D2)

**대상 파일**: `vault-bridge/commands/save-plan-doc.md`

**Layer 1 본문 (개선안)**:

```
이 프로젝트의 plan/design 파일을 vault에 스냅샷으로 저장하려고 합니다.

발견된 후보 ({N}개){경고 — D5-a 적용 시}:
{list 또는 카테고리별 요약}

각 파일은 ~/vault/{vault_path}/ 아래에 frontmatter가 추가된 새 파일로
박제됩니다. 원본은 수정되지 않습니다.

이 프로젝트에 vault 내보내기 권한(.vault-link의 snapshot_export)이
아직 켜져 있지 않습니다. 어떻게 진행할까요?
```

옵션 description은 D2 결정대로 (지속 범위 + 부수 효과 + 되돌리기).

**Layer 2 본문 (개선안)**:

```
캡처 대상 vault 프로젝트({vault_path}/_index.md)가 외부 스냅샷 수신
권한(snapshot_import)을 켜지 않았습니다.

이 권한은 vault 오너만 변경할 수 있습니다. 본인이 vault 오너라면:

  /project {name} --enrich auto_capture=true

(vault 오너가 아닌 경우 우회 저장 시 vault 오너 정책에 따라 나중에
삭제될 수 있습니다.)
```

**Discover 시점**: 메시지 본문에 후보 수 표시를 위해 게이트 미활성 케이스에서도 `--discover` 1회 선실행.

### Phase 3 — D4-A 의사 명시 단계 추가

**대상 파일**: `vault-bridge/commands/save-plan-doc.md`

**변경**:
- Step 1과 Step 2 사이에 새 단계 (Step 1.5) 추가: "이 plan을 지금/다음 세션/취소"
- Step 6 결과 메시지를 의사 결정에 따라 분기:
  - 지금: "ExitPlanMode → 진행 선택"
  - 다음 세션: "ExitPlanMode → 진행 안 함 선택"
  - (취소는 Step 1.5에서 즉시 종료)

### Phase 4 — D5-a + D5-b discover 노이즈 완화

**대상 파일**:
- `vault-bridge/scripts/plan-doc-syncer.py` (`--recent` 인자 추가, `_discover_candidates`에 mtime 필터)
- `vault-bridge/commands/save-plan-doc.md` (Step 4 본문에 임계치 경고 + 카테고리 분포)

**임계치 기본값**: 10개. 환경변수 `VAULT_BRIDGE_DISCOVER_WARN_THRESHOLD`로 override 가능.

### Phase 5 (검토 후) — D4-B PoC

**선행 검증** (PoC):
- ExitPlanMode 발화 시 PostToolUse 훅이 fire되는지 (matcher: `ExitPlanMode`)
- 훅에서 prompt 타입으로 AskUserQuestion 발화 가능한지
- plan mode 활성 감지 신호 존재 여부

**검증 결과 분기**:
- 모두 가능 → D4-B 구현, D4-A는 fallback 보존
- 일부 불가 → D4-B 폐기, D4-A로 만족

### Phase 6 (옵션, 후순위) — D3 trigger 자동화 플래그

**대상 파일**:
- `vault-bridge/hooks/session-end-pre.sh` (state JSON에 `auto_sync_on_session_end` 추가)
- `vault-bridge/.claude-plugin/plugin.json` (SessionEnd prompt 훅 분기 로직)

**전제**: 양쪽 게이트 + `auto_sync_on_session_end` 셋 다 활성일 때만 자동 실행.

### Phase 7 (별도 RFC) — D6 snapshot 모델 결정

다른 phase와 독립. spec 차원 결정이라 RFC 또는 discussion으로 분리해 합의 후 진행.

**선행 작업**:
1. snapshot 모델(박제 vs 정사 미러) 정의 — vault-bridge spec에 명문화.
2. vault-searcher Forbidden writes 룰과의 정합성 결정 (plan-doc 예외 vs 룰 시맨틱 분리).
3. 영향 분석: 기존 누적 snapshot의 마이그레이션 정책 (그대로 둠 / archive 폴더로 이전).

**채택 시 코드 변경**:
- D6-B 또는 D6-C/D 채택 시: `plan-doc-syncer.py`의 `_resolve_collision_free_path` 로직 변경 또는 모드 분기.
- D6-A 유지 시: 변경 없음. 다만 spec에 "박제 모델"임을 명문화하여 vault git과의 책임 분리 명시.

## 영향 범위

| 파일 | Phase | 변경 종류 |
|---|---|---|
| `vault-bridge/scripts/plan-doc-syncer.py` | 1, 4 | 키 인식 확장, deprecation 경고, `--recent` 인자, mtime 필터 |
| `vault-bridge/commands/save-plan-doc.md` | 1, 2, 3, 4 | Step 본문/옵션 재작성, Step 1.5 추가, 카테고리 표시 |
| `vault-bridge/hooks/session-end-pre.sh` | 1, 6 | grep 확장, state JSON 필드 |
| `vault-bridge/.claude-plugin/plugin.json` | 5, 6 | (Phase 5) PostToolUse hook 추가, (Phase 6) SessionEnd 분기 |
| `vault-bridge/README.md` | 7 | (D6 채택 시) snapshot 모델 정의 명문화 |
| `vault-bridge/agents/vault-searcher.md` | 7 | (D6 채택 시) Forbidden writes 룰과 plan-doc 예외 정합성 명시 |
| `vault-bridge/CHANGELOG.md` | all | 변경 기록 |
| 버전 동기화 | all | `plugin.json` + `marketplace.json` minor 범프 (D6 채택 시 major) |

**호환성**:
- `auto_capture: true` 기존 사용자는 그대로 동작 (alias).
- alias 사용 시 stderr 경고 한 줄 (warning-only, fail 아님).
- D3 / D4-B는 기본 비활성, opt-in 시에만 동작.

## Out of Scope

- **plan mode → 파일 자동 저장 (PostToolUse 훅)**: D4-B의 일부로 흡수. 단독 작업 아님.
- **2-layer gate 합치기**: 보안 모델 약화 우려로 보류 (다인 vault 보호 기능).
- **`/save-plan-doc`과 Mode 4 plan 단일 명령 통합**: 정사 모델이 다른 별개 작업 — 통합 시 시맨틱 손실.
- **frontmatter 커스텀 필드 보존 옵션**: 별도 이슈로 추적.
- **OVM `/project` skill 충돌 처리 보강** (broken state, Mode A 거부 시 Mode C 안내): OVM 측 직교 작업, 별도 이슈로 분리.
- **vault snapshot 사후 deprecated 마킹**: snapshot immutability 위반(현재 모델 가정). D6에서 모델 자체가 재정의되면 이 정책도 재검토 — D6-B 채택 시 deprecated 마킹은 무의미(덮어쓰기), D6-A 유지 시 그대로 거부.

## 검증 절차

### Phase 1
- [ ] `snapshot_export: true`만 있는 `.vault-link`로 `/save-plan-doc` → L1 통과
- [ ] `auto_capture: true`만 있는 `.vault-link` → L1 통과 + stderr 경고
- [ ] 둘 다 없으면 → L1 차단 + AskUserQuestion 발화
- [ ] L2 동일 시나리오
- [ ] `session-end-pre.sh`가 신규 키 + alias 모두 인식

### Phase 2
- [ ] AskUserQuestion 본문에 후보 파일 목록 표시
- [ ] 옵션 description에 지속 범위 + 되돌리기 표시
- [ ] L2 메시지에 actionable 명령 (`/project --enrich`) 표시
- [ ] visual check (transcript 첨부)

### Phase 3 (D4-A)
- [ ] Step 1.5 의사 명시 옵션 발화
- [ ] "지금" 선택 → 결과에 "진행 선택" 안내
- [ ] "다음 세션" 선택 → 결과에 "진행 안 함 선택" 안내
- [ ] "취소" 선택 → 즉시 종료, vault 변경 X

### Phase 4 (D5-a, D5-b)
- [ ] 후보 수 < 임계치: 경고 미표시
- [ ] 후보 수 ≥ 임계치: 경고 + 카테고리별 분포 표시
- [ ] `--recent 60` 시 60분 내 수정 파일만 후보
- [ ] `--recent` 미지정 시 기존 동작

### Phase 5 PoC (D4-B)
- [ ] ExitPlanMode PostToolUse 훅 발화 확인
- [ ] 훅 내 AskUserQuestion 발화 가능 여부
- [ ] plan mode 활성 감지 신호 확인
- [ ] 결과에 따라 D4-B 진행/폐기 결정

### Phase 6 (D3, 실행 시)
- [ ] `auto_sync_on_session_end: false` (기본) → 안내만, 자동 실행 X
- [ ] 셋 다 활성 → SessionEnd 종료 시 syncer 자동, session-note에 기록
- [ ] dedup 동작 (같은 plan 두 번 자동 sync → 두 번째 skip)

### Phase 7 (D6, RFC 합의 후)
- [ ] snapshot 모델 정의(박제/미러) spec 명문화 확인
- [ ] vault-searcher Forbidden writes 룰과의 정합성 결정 명문화
- [ ] D6-B 채택 시: 같은 source path → 같은 vault filename 덮어쓰기, frontmatter만 갱신
- [ ] D6-A 유지 시: 코드 변경 없이 spec 명문화만
- [ ] 마이그레이션: 기존 `-v{N}` 누적 snapshot 처리 정책 적용 확인

## 다음 단계

1. 이 plan v3를 `/save-plan-doc`로 vault에 박제 (자동 `-v2` 박제, vault snapshot v1은 immutable로 보존). 외부 파일 차원 v3, vault snapshot 차원 v2.
2. Phase 1 PR (D1 — 키 분리 + alias).
3. Phase 2 PR (D2 — 메시지 재작성 + L2 actionable).
4. Phase 3 PR (D4-A — 의사 명시).
5. Phase 4 PR (D5-a + D5-b — discover 노이즈).
6. Phase 5 PoC 결과 보고 후 D4-B 진행/폐기 결정.
7. Phase 6은 사용 패턴 관찰 후 결정.
8. Phase 7 (D6) 별도 RFC로 분리 — 합의 후 진행. 다른 phase와 병행 가능.

## 변경 이력

> 차수 표기: 외부 `docs/.../plan.md` 갱신 차수 (살아있는 정사). vault snapshot 차수는 `/save-plan-doc` 호출 시점에만 증가하므로 외부 차수와 어긋날 수 있다.

### v1 → v2 (2026-05-10, 같은 날 갱신)

**v1에서 추가된 결정**:
- D4 신규: plan mode ↔ save-plan-doc 의도 단절 해소 (A 즉시 + B 검토 후)
- D5 신규: discover 노이즈 완화 (89개 폭격 dogfooding 발견)

**v1에서 보강된 결정**:
- D1: SoC 근거 추가 (vault-bridge = export 관리, OVM = import 관리)
- D2: L2 메시지에 actionable 명령 추가 (`/project --enrich auto_capture=true`)

**v1에서 추가된 Out of Scope**:
- vault snapshot 사후 deprecated 마킹 거부 (immutability 위반)
- OVM `/project` 충돌 처리 보강 (직교 작업)

**Phase 재정렬**:
- v1의 D3 trigger 자동화 → Phase 6으로 후순위 이동
- D4-A를 Phase 3, D5-a/b를 Phase 4, D4-B PoC를 Phase 5로 재정렬

**v1 처리**: vault snapshot은 immutable로 보존. 외부 파일만 갱신.
**vault snapshot 차수**: v2는 `/save-plan-doc` 미호출이라 vault에 박제되지 않음.

### v2 → v3 (2026-05-11)

**v2에서 추가된 결정**:
- D6 신규: snapshot 모델 재정의 (박제 vs 정사 미러) — UX가 아닌 spec 정의 결정. 결정 보류 + 옵션 검토. 다른 phase와 직교.
  - dogfooding 발견: vault snapshot `-v{N}` 누적과 vault git의 책임 부분 중복
  - 권장: D6-B (덮어쓰기) — vault git이 시점 추적 정사 인프라

**v2에서 보강된 항목**:
- 배경 §5 신규: snapshot 누적 ↔ vault git 중복 분석
- Out of Scope의 deprecated 마킹 정책: D6 결정에 따라 재검토 명시
- 영향 범위 표: `vault-bridge/README.md`, `vault-searcher.md` 추가 (D6 채택 시 spec 명문화 대상)
- Phase 7 신규: D6 RFC 합의 후 진행

**v3 처리**: 외부 파일 갱신 후 `/save-plan-doc` 재호출 예정 → vault snapshot은 v1 → **v2로 박제** (외부 차수 v3과 vault 차수 v2가 어긋나는 첫 사례). 이 박제 결과 자체가 D6의 dogfooding 사례 — vault에 plan v1, v2가 같은 디렉토리에 누적되어 D6에서 짚는 노이즈 패턴 즉시 발현.
