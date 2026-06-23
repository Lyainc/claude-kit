# Vault Second Brain 설계안 v4

> 작성일: 2026-05-26
> 도출 과정: critic 토론 7라운드 + 외부 PKM 레퍼런스 검증 + 외부 도구 4개 검토 + 자기 비판 리뷰
> 상태: **SUPERSEDED by [`vault-second-brain-v5.md`](vault-second-brain-v5.md)** (2026-06-23, #215 — LLM wiki A 主 + B probation).
> v5가 인간 저작 second-brain 전제를 "LLM 컴파일 + 인간 승급만"으로 전환. v4의 type opt-in·status machine·recall 중심·git
> 통합·거부목록은 v5가 **계승**. 이 문서는 역사 기록으로 보존(원 상태: 설계 확정, 구현 대기).
> 관련 문서: `docs/plans/vault-second-brain-v4-migration.md`

## 1. 정의

> "Claude와 협업할 때, 과거의 내 의사결정과 축적된 도메인 지식이 항상 옆에 있어서, 같은 실수를 반복하지 않고 이전 통찰 위에서 사고할 수 있게 해주는 시스템."

### 1.1 타깃 사용자

- 1인 개발자 + LLM 협업자
- Obsidian + Claude Code + git을 기본 도구로 사용
- 동시에 vault를 *일반 노트앱*으로도 사용 (일기, 책 메모 등)

### 1.2 배제하는 시나리오

- 팀 위키 / 멀티유저 협업
- 출판용 글쓰기
- PARA 분류 강박형 PKM

## 2. 핵심 원칙

### 2.1 Cabinet/Brain 이중 모드

기본은 *cabinet*. Obsidian + git만으로 동작하며 claude-kit은 침묵한다.
`/audit` 호출 시점이 *brain화 의식*. 정체·promotion·(Phase 2) 패턴 추출이 그 순간에 일어난다.

→ 항상-on push 없음. 사용자 능동성이 brain화 시점을 결정. 지속가능성 우선.

### 2.2 `type:` 필드 = 관리 대상 마커

vault는 *사용자의 것*. claude-kit은 *손님*이다.
`type:` 필드가 있는 노트만 claude-kit이 관리하고, 없으면 invisible.
사용자가 일기·책 메모·자유 폴더 구조를 그대로 유지할 수 있다.

### 2.3 Recall이 핵심 (Capture만 강화 X)

LLM Wiki 실패 교훈 — 데이터 흡수 자동화만으로는 brain이 안 된다.
우리의 recall 메커니즘은 `/audit` 단일 채널. Phase 2에서 패턴 추출까지 확장.

### 2.4 Reformulation은 *원칙*, *강제 X*

자기 언어로 재작성하는 것이 evergreen의 본질이지만 시스템이 이를 검증할 수 없다.
사용자가 status를 `raw → draft`로 *변경하는 액션 자체*가 "내가 검토했다"는 단일 진실 소스가 된다.

### 2.5 Stand-alone

Obsidian + Claude Code + git 외 의존성 0. omc, graphify, llm-wiki, ouroboros 등 외부 플러그인은 nice-to-have 영감으로만 차용.

## 3. 구조

### 3.1 폴더 (3개)

```
~/vault/
├── inbox/      ─ raw 입력 (clip, capture)
├── notes/      ─ 모든 작성된 콘텐츠 (사용자 자유 하위 폴더 가능)
└── assets/     ─ 첨부 (이미지, PDF 등)
```

숫자 prefix 제거. 폴더로 의미 분류하지 않는다. 사용자가 `notes/diary/`, `notes/work/` 등 자유롭게 하위 폴더를 만들 수 있다.

### 3.2 Type (5개)

```yaml
type: capture | note | decision | session | plan
```

| Type | 역할 | 특징 |
|------|------|------|
| `capture` | 외부 콘텐츠 흡수 | source 필드로 출처 구분 (web-clipper, manual 등) |
| `note` | 일반 지식 단위 | Matuschak의 concept-oriented 원칙 |
| `decision` | 의사결정 트레일 | **핵심 자산**. Phase 2 패턴 추출 대상 |
| `session` | 세션 기록 | vault-bridge `/save-session`이 생성 |
| `plan` | 작업 스펙 | vault-bridge `/save-session plan`이 생성 |

**제거된 type**:
- `clip` → `capture` + `source: web-clipper`로 흡수 (라이프사이클 동일)
- `moc` → 슬롯 미할당. Obsidian graph view + evergreen 노트가 entry point 역할

### 3.3 Status Machine

```
                       [사용자 액션]
inbox ─raw─►  draft  ────────────►  evergreen
                │                       │
                └─────► archived ◄──────┘   (어디서든 exit)
```

| status | 의미 | 전이 주체 |
|--------|------|----------|
| `raw` | 외부 입력 직후, 미검토 | 시스템 자동 |
| `draft` | 검토 완료, 사용 의도 | 사용자 (Obsidian frontmatter 직접 편집) |
| `evergreen` | 안정화된 knowledge | 사용자 |
| `archived` | 비활성화 (exit) | 사용자 |

**Evergreen 승격 자격**: `type: note` 또는 `type: decision`만 가능. session/capture/plan은 evergreen 영구 불가 (Matuschak의 concept-oriented 원칙).

### 3.4 Frontmatter 스키마

노트 파일에는 *사용자가 정한 값*만 기록:

```yaml
---
type: note
status: draft
created: 2026-05-26
tags: [...]
source: web-clipper        # capture만, 선택
url: ...                   # capture만, 선택
---
```

시스템 자동 메타는 `manifest.json` 전용:

```json
{
  "path": "notes/something.md",
  "references_in": 5,
  "references_out": 3,
  "access_count": 12,
  "promotion_candidate": true
}
```

→ 노트 파일이 시스템 메타로 오염되지 않는다. Obsidian에서 보이는 frontmatter는 깔끔하게 유지.

**갱신 트리거**: `manifest.json`의 시스템 메타(`references_in/out`, `access_count`, `promotion_candidate`)는 `/audit` 호출 시 일괄 재계산된다. SessionStart 훅은 manifest 파일 자체의 incremental 갱신(파일 추가/변경 반영)만 수행하며 시스템 메타는 갱신하지 않는다. 따라서 `promotion_candidate` 신호는 *마지막 `/audit` 시점 기준*이다. 자동 push 없음 원칙(§9.1)과 정렬.

### 3.5 Decision 노트 템플릿 (Phase 2 준비)

```yaml
---
type: decision
status: draft
created: 2026-05-26
tags: [decision, {domain}]
problem: ...      # 1줄
chosen: ...       # 1줄
rejected: [...]   # 선택지 1-2개
rationale: ...    # 1-3줄
revisit_when: ... # 1줄 (선택)
---
```

가볍지만 구조화. Phase 2에서 audit이 공통 패턴 추출 가능.

### 3.6 파일명 컨벤션

```
inbox/capture-YYYY-MM-DD-{slug}.md
inbox/session-YYYY-MM-DD.md       (vault-bridge 생성)
notes/{slug}.md                    (evergreen 후보, 날짜 없음)
notes/decision-YYYY-MM-DD-{slug}.md
notes/plan-YYYY-MM-DD-{slug}.md
```

slug은 kebab-case. 동일 날짜 중복 시 `-v2`, `-v3` 증분.

## 4. Git 통합

vault가 git 저장소라는 가정. git이 없으면 graceful degradation.

### 4.1 Git log = vault-log 무료 대체

LLM Wiki의 `vault-log` 자동 갱신 시도가 실패한 자리를 `git log`가 자연스럽게 채운다.

```bash
git -C ~/vault log --since="1 week ago" --name-only --pretty=format:"%ad %s" --date=short
```

→ `/audit`에 "이번 주 vault 활동" 한 섹션으로 통합.

### 4.2 Commit Message 컨벤션

`/vault-commit`이 자동 생성:

```
note(promote):     {file} {status_from} → {status_to}
note(archive):     {file} → archived
capture(intake):   {file} ({source})
decision(create):  {file} - {problem 1줄}
```

→ git log가 *지식 진화 이력*이 된다.

```bash
git log --grep="→ evergreen"     # 내가 evergreen으로 승격한 노트들
git log --follow notes/foo.md    # 한 노트의 진화 이력
```

### 4.3 `.gitattributes` 마크다운 diff

```
*.md diff=markdown
```

evergreen 노트의 *변화 가독성* 확보. 템플릿 위치: `vault-bridge/reference/gitattributes-template.txt`.

**수동 설치** (사용자가 vault에 한 번):

```bash
cp ~/.claude/plugins/cache/.../vault-bridge/reference/gitattributes-template.txt ~/vault/.gitattributes
cd ~/vault && git add .gitattributes && git commit -m "enable markdown diff for vault"
```

플러그인 캐시 경로는 환경마다 다르다 (`find ~/.claude -name "gitattributes-template.txt"`로 확인).

## 5. 입력 강화 (Capture Pipeline)

### 5.1 Obsidian Web Clipper 통합

`obsidian-vault-manager/reference/web-clipper-template.md`로 템플릿 제공. 사용자가 Web Clipper 설정에 한 번 import:

```yaml
---
created: {{date}}
type: capture
source: web-clipper
url: {{url}}
clipped_at: {{datetime}}
status: raw
tags: [capture, clip]
---
{{content}}
```

저장 위치: `inbox/capture-YYYY-MM-DD-{slug}.md`

### 5.2 `/capture` 스킬 강화

- `/capture url1 url2 url3` — 다중 URL 병렬 defuddle 처리
- `/capture` (인자 없음) — `inbox/`의 `status: raw` 파일 일괄 처리

정제 단계: defuddle 결과 + 사용자 한 줄 요약 → notes/로 승격 + `status: draft`. 한 줄 요약이 *암묵적 reformulation*.

**type 전이**: 정제 시 `type: capture`인 inbox 파일이 `notes/`로 이동하면서 `type: note`로 변경된다. 이는 *concept-oriented*로 reformulation됐다는 사용자 선언(§2.4)에 해당. 원본 `source`, `url`, `clipped_at` 필드는 보존되어 출처 추적 가능. 파일명도 `capture-YYYY-MM-DD-{slug}.md` → `{slug}.md`로 변경 (날짜 prefix 제거).

```
inbox/capture-2026-05-26-deepseek-v3.md   (type: capture, status: raw)
   ↓ [/capture 정제 + 사용자 요약]
notes/deepseek-v3.md                       (type: note, status: draft, source: web-clipper 유지)
```

## 6. OVM 스킬 (3개)

| 스킬 | 책임 |
|------|------|
| `capture` | inbox/에 raw 저장 (다중 URL, web clipper 호환) |
| `note` | notes/에 type 노트 작성 (`--type note\|decision\|plan`), inbox → notes 정제 |
| `audit` | Brain화 의식: 무결성 + 정체 + promotion candidate + Phase 2 패턴 추출 (§6.1 명세) |

### 제거된 스킬 (이전 7개에서)

| 제거 | 대체 |
|------|------|
| `project` | `note --type decision` 또는 `tags: [project]` |
| `inbox-review` | `note` 스킬의 일괄 처리 모드 |
| `context` | `vault-searcher` Mode 2로 일원화 |
| `archive` | frontmatter `status: archived` 한 줄 |
| `decide` | `note --type decision` 흡수 |

### 6.1 `/audit` Phase 1 동작 명세

`/audit` 호출 시 다음 항목을 *우선순위 순*으로 점검·출력한다. 시스템 메타 일괄 재계산은 첫 단계.

**Step 0 — 시스템 메타 재계산 (silent)**
모든 `type:` 있는 노트에 대해 `references_in/out`, `access_count`(git log 기반), `promotion_candidate` 재계산. `manifest.json` 갱신.

**Step 1 — 무결성 (우선순위 P0)**
- frontmatter 누락 / 필수 필드(`type`, `status`) 부재
- 깨진 wikilink
- 파일명 컨벤션 위반

P0 항목 존재 시 *먼저 출력*하고 사용자 확인 후 다음 단계 진행.

**Step 2 — 정체 (우선순위 P1)**
- inbox `status: raw` 파일 카운트 (임계: 5개 이상 또는 14일 이상 묵힘)
- notes `status: draft` 30일 이상 묵힘
- 임계 미만이면 *침묵* (노이즈 방지)

**Step 3 — Promotion Candidate (우선순위 P2)**
- `references_in >= 3` 또는 `access_count >= 5` 노트 목록
- `type: note` 또는 `type: decision`만 (§3.3 승격 자격)
- 출력 형식: 파일명 + 신호값. evergreen 승격은 *사용자 수동 frontmatter 편집*

**Step 4 — Git 활동 요약 (우선순위 P3)**
- 지난 7일간 vault 활동: commit 수, 추가·수정·archive된 파일 카운트
- `git log --since="1 week ago"` 기반

**Step 5 — Phase 2 패턴 추출 (조건부)**
- `type: decision` 노트가 *임계 N* 누적 시에만 활성 (Phase 1에선 N 미정, §8 참조)
- Phase 1에선 비활성

**기본 임계값** (사용자 환경변수로 오버라이드 가능):
- `VAULT_AUDIT_INBOX_RAW_THRESHOLD=5`
- `VAULT_AUDIT_INBOX_AGE_DAYS=14`
- `VAULT_AUDIT_DRAFT_AGE_DAYS=30`
- `VAULT_AUDIT_PROMOTION_REFS=3`
- `VAULT_AUDIT_PROMOTION_ACCESS=5`

각 카테고리 출력은 *접힘(collapsed) 기본*. 사용자가 `--verbose` 또는 카테고리 키워드로 펼침.

## 7. vault-bridge 영향

| 컴포넌트 | 변경 |
|---------|------|
| `pre-write-guard.sh` | `00_Inbox` → `inbox` 패턴 갱신. type 없는 노트는 패스 |
| `generate-manifest.py` | EXCLUDED_DIRS 갱신, type 필터링, 시스템 메타 추적 (`references_in/out`, `access_count`, `promotion_candidate`) |
| `vault-searcher.md` | 경로 갱신, type 기반 우선순위, Mode 1/2/3 출력 경계 명세 정비 |
| `/save-session` | 저장 경로 갱신 |
| `/vault-commit` | Commit message 컨벤션 자동 생성 |
| SessionStart 훅 | 새 push 추가 X (기존 handoff resume만 유지) |

## 8. Phase 분리

### Phase 1 (즉시): 데이터 축적

- 폴더 단순화 (7 → 3)
- 스킬 정리 (7 → 3)
- type 마커 도입 + 옵트인 정책
- Capture pipeline 강화 (Web Clipper 템플릿 + 다중 URL)
- Git commit 컨벤션
- `/audit` Phase 1 기능 (무결성 + 정체 알림 + promotion candidate + git 활동 요약)

**목표**: decision 노트가 쌓이는 환경 조성. Phase 2의 데이터 기반 마련.

### Phase 2 (3-6개월 후, 데이터 충분 시점): 패턴 추출

- `/audit`이 decision 노트 N개 누적 감지
- 공통 패턴 추출 (Claude 호출, 사용자 명시 요청 시)
- 사용자에게 제안: "이 패턴을 메타 노트로 합칠까요?" 또는 "스킬로 결정화할까요?"
- skillify-like 메커니즘 (OMC `/skillify` 영감, 의존 X)

→ Phase 1 데이터 없이 Phase 2 시도는 *상상의 탑*. 선제 도입 금지.

## 9. 거부한 선택과 근거

### 9.1 SessionStart 자동 push

사용자가 *프로젝트 개발 세션 노이즈*를 명시적으로 거부. brain화는 `/audit` 호출 시점에 집중.

### 9.2 Embedding / RAG 기반 검색

외부 검증 (Karpathy 패턴 + 2025-2026 PKM 커뮤니티): long context + flat markdown이 vector RAG보다 우위. 노트 간 관계를 잃지 않으며 외부 서비스 의존 0.

대안: `manifest.json` 결정론적 인덱싱 + Claude long context 주입.

### 9.3 Typed Relations (relation_type frontmatter)

graphify의 `EXTRACTED/INFERRED/AMBIGUOUS`, activegraph의 typed edges 모두 매력적이나:
- 모든 wikilink에 type 부여 = 마찰 폭증
- `[[]]` 본문 기반 + 별도 frontmatter 메타 = 이중 관리
- 수익은 `type: decision`에 한정

→ YAGNI. 필요해질 때 추가.

### 9.4 자동 캡처 + 외부 서비스 (claude-mem 패턴)

자동 캡처 + Chroma 벡터 DB + 포트 워커 = stand-alone 3중 위반. 우리는 사용자 명시 + git + 결정론적 manifest로 동일 효과를 달성.

### 9.5 MOC 별도 type 슬롯

Obsidian의 graph view + 태그 + 백링크가 이미 MOC 역할을 수행. 명시적 MOC 파일은 *중복 큐레이션*이며 evergreen 노트 자체가 자연스러운 entry point.

### 9.6 Pre-commit hook 강제

`/audit`이 명시적 실행이라는 의도와 충돌. 마찰 + 침투적. 사용자가 원하면 `reference/` 가이드를 통해 수동 설치 안내.

### 9.7 graphify/activegraph 직접 통합

stand-alone 위반. 영감만 받음.

## 10. 외부 검증 요약

| 출처 | 우리 안과의 정렬 |
|------|----------------|
| **Andy Matuschak — Evergreen notes** | concept-oriented 원칙 부합. 자동 승격은 *인기*이지 *성숙*이 아님 → `promotion_candidate` 신호와 evergreen 결정 분리 |
| **Sönke Ahrens — Smart Notes** | reformulation 원칙 차용 (강제는 X, 사용자 액션에 위임) |
| **Tiago Forte PARA 비판 (zettelkasten.de)** | PARA의 폴더 분류 회피 — type/status frontmatter로 대체 |
| **Karpathy LLM Wiki pattern** | flat markdown + long context + Obsidian = 우리 방향 정확히 일치 |
| **LLM Wiki vault-log 실패 (vault 내부 자료)** | capture만 강화로는 brain 불가 → recall이 핵심. git log로 vault-log 자연 대체 |
| **claude-mem (반면교사)** | 자동 캡처 + RAG + 외부 서비스 = 우리가 거부하는 패턴 |

## 11. 잔여 의심점 (구현 단계에서 해결)

| # | 영역 | 처리 시점 |
|---|------|----------|
| 1 | Audit 호출 빈도 자연 유도 (README 가이드) | 구현 시 |
| 2 | Audit 출력 우선순위 (6+ 카테고리 동시 출력 시 노이즈) | 구현 시 |
| 3 | 마이그레이션 wikilink 호환성 | 별도 가이드 문서 |
| 4 | 신규 사용자 onboarding | README 작성 시 |
| 5 | 다국어 (한국어) 처리 | 기존 코드에서 처리 중 |
| 6 | 신규 사용자 첫 사용 예시 (`/capture`, `/note` 워크플로우 데모) | README 작성 시 |
| 7 | 다중 vault / `VAULT_BRIDGE_VAULT_ROOT` 환경변수 처리 | 구현 시 (vault-bridge 기존 지원과 정렬) |
| 8 | 한국어 slug kebab-case 변환 (transliteration vs 한글 보존) | 구현 시 정책 결정 |
| 9 | git 없는 vault의 graceful degradation 롤백 경로 | 구현 시 (manifest mtime 기반 대안) |
| 10 | Phase 2 트리거 임계값 N (decision 노트 누적 수) | dogfood 데이터 보고 결정 (3-6개월 후) |

## 12. 다음 단계

1. 본 설계 문서 리뷰 + 확정
2. 마이그레이션 가이드 (`docs/plans/vault-second-brain-v4-migration.md`)
3. 구현 PR 시리즈:
   - vault-bridge: 폴더 패턴 갱신, manifest 스키마 확장
   - OVM: 7 → 3 스킬 정리
   - capture 강화 + Web Clipper 템플릿
   - `/audit` Phase 1 기능
4. dogfood 1개월: claude-kit 자체 vault에서 사용
5. Phase 2 평가 (3-6개월 후)
