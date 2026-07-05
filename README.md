# claude-kit

**Claude Code가 같이 생각해주는 도구 모음.**

브레인스토밍하고, 주장의 약점을 반증하고, 결정을 다관점으로 검토하고 — 그 사고 과정을 지식으로 남겨요. `thinking-tools`는 코드와 무관해서 **기획·글쓰기·리서치·의사결정에 바로** 쓸 수 있어요.

```bash
claude plugin marketplace add Lyainc/claude-kit
claude plugin install thinking-tools@Lyainc-claude-kit
```

> 플러그인은 전부 독립적이에요. 하나만 깔아도 되고, 전부 깔아 **사고 → 기록**으로 이어도 돼요.
> 최신 버전은 [Releases](https://github.com/Lyainc/claude-kit/releases) 참고 (lockstep — 모든 플러그인이 같은 버전으로 함께 배포).

## 왜 claude-kit인가

Claude Code와의 작업은 강력하지만 세 가지가 아쉬워요:

- 생각을 **체계적으로** 끌어내는 도구가 없어요 — 그냥 물어보는 것 이상이 안 돼요
- 좋은 결론도 세션이 끝나면 **흩어져요**
- 매번 같은 사고 과정을 **처음부터** 반복해요

claude-kit은 이걸 *도구*로 만들어요. **사고**(`thinking-tools`)로 끌어내고, **기록·지식관리**(`vault-bridge` · `obsidian-vault-manager`)로 남겨요. 하나로 이어지는 흐름이지만, 스킬 하나만 따로 써도 강력해요.

## 플러그인

### thinking-tools — 사고 도구 (비개발자도 OK)

"그냥 답해줘"가 아니라 **체계적으로 같이 생각해요.** 코드와 무관해서 기획·글쓰기·리서치·의사결정에 바로 써요.

| 이럴 때 | 스킬 |
|---|---|
| 아이디어를 여러 갈래로 펼치고 싶을 때 | `diverse-sampling` — 브레인스토밍 (Verbalized Sampling) |
| 내 주장·계획의 약점을 찾고 싶을 때 | `adversarial-review` — 반증 + Survival Score |
| 결정을 다관점으로 검토하고 싶을 때 | `expert-panel` — 전문가 패널 토론 |
| 놓친 맹점을 발견하고 싶을 때 | `unknown-discovery` — 블라인드 스팟 인터뷰 |
| 모호한 생각을 문서·스펙으로 정리할 때 | `doc-concretize` · `build-spec` |
| 다 쓴 문서를 다듬고 싶을 때 | `doc-polish` |

`thinking-facilitator` 에이전트가 요청을 분석해 알맞은 스킬로 자동 안내해요. (여러 스킬을 한 번에 잇고 싶으면 `thought-chain`.)

```bash
claude plugin install thinking-tools@Lyainc-claude-kit
```

### obsidian-vault-manager — 지식 관리

작업하며 알게 된 걸 Obsidian vault(plain Markdown)에 쌓고 관리해요. 앱이 아니라 **사용자 소유 파일**에 지식이 상주해요.

| 스킬 | 하는 일 |
|---|---|
| `capture` | 즉시 메모 저장 (+ URL 본문 자동 추출) |
| `note` | 노트 생성 + MOC·프로젝트 연결 |
| `audit` | vault 구조 무결성 감사 (E1–E11 오류 + 승격 후보 추적) |
| `wiki` | 도메인 지식을 LLM wiki 페이지로 컴파일 (AI recall, 게이트된 명시 액션) |
| `base` | 비파괴 Obsidian Bases(.base) 뷰 생성 |

```bash
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

### vault-bridge — 프로젝트 ↔ vault 브릿지

외부 코드 프로젝트에서 vault에 접근하고, 세션 작업을 기록으로 남겨요. haiku 기반 읽기 전용 검색 에이전트 + 기록 슬래시 커맨드 + 결정형 훅(턴당 LLM 비용 0).

| 커맨드 | 하는 일 |
|---|---|
| `/save-session` | 세션 노트 작성 (record / quick) |
| `/vault-link` | 프로젝트를 특정 vault 위치에 바인딩 |
| `/vault-commit` | vault 변경사항 커밋 |

이 외에 `/vault-manifest-refresh`, 그리고 결정형 훅 3종(SessionStart 매니페스트 갱신 + 접근·쓰기 가드, 턴당 LLM 비용 0)이 있어요. 자세한 동작·정책은 [vault-bridge/README.md](vault-bridge/README.md) 참조.

```bash
claude plugin install vault-bridge@Lyainc-claude-kit
```

---

> **feedback-loop** (실험적 · layer ⑤ 자기개선): measure→review→keep 루프예요 (실행/이터레이션 엔진 아님). `retro` 스킬(세션 회고 + vault 승격 후보 재확인)과 opt-in 로컬 telemetry로 이뤄져요. telemetry는 `CLAUDE_KIT_TELEMETRY=1` 아니면 아무것도 안 쓰고(silent), 턴당 LLM 비용 0, 외부 유출 0이에요.
> ```bash
> claude plugin install feedback-loop@Lyainc-claude-kit
> ```

### 무엇부터 써볼까 — 작업 흐름별 진입점

플러그인 말고 *하려는 일* 기준으로 고르고 싶으면 이 표부터 보세요. (새 세션을 열면 Claude가 처음 몇 번 이 진입점을 자연스럽게 안내해요. 끄려면 `CLAUDE_KIT_WELCOME_DISABLE=1`.)

| 하려는 일 | 진입점 |
|---|---|
| 아이디어 펼치고 스펙으로 굳히기 (사고·기획) | `diverse-sampling` · `build-spec` · `unknown-discovery` |
| 결과물 검토·반증·다듬기 (작업·폴리싱) | `expert-panel` · `adversarial-review` · `doc-polish` |
| 작업을 기록·검색으로 남기기 (지식관리) | `/save-session` · `capture` · `note` |

흐름과 내부 5-레이어의 직교 매핑 근거는 [4-흐름 카탈로그](docs/design/4-flow-catalog.md) 참조.

## 빠른 시작 — vault second brain

`thinking-tools`는 설치 후 자연어로 바로 써요 ("브레인스토밍 해줘", "이 주장 반증해줘"). 아래는 vault 기반 지식 관리를 5분 안에 시작하는 방법이에요.

### 1. vault 초기화

```bash
mkdir -p ~/vault/{inbox,notes,assets}
cd ~/vault
git init
git add -A
git commit -m "initial vault structure (v4)"
```

### 2. 플러그인 설치

```bash
# 최소 설치 (vault 브릿지 + 세션 노트)
claude plugin install vault-bridge@Lyainc-claude-kit

# vault 지식 관리 스킬까지 포함
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

Claude Code를 재시작하면 적용됩니다.

### 3. 프로젝트와 vault 연결

코드 프로젝트 루트에서:

```
/vault-link
```

`.vault-link` 파일이 생성되면 이후 `/save-session`이 이 프로젝트 경로로 자동 저장됩니다.

### 4. 첫 캡처

```
/capture 오늘 배운 것: Claude Code 플러그인 구조
```

`~/vault/inbox/capture-YYYY-MM-DD-{slug}.md`로 저장됩니다. URL을 전달하면 본문을 자동 추출해요 (`defuddle` 설치 시).

### 5. 세션 노트 저장

작업 마무리 시:

```
/save-session
```

record / handoff / quick 모드 중 선택 후 `~/vault/inbox/` 또는 연결된 프로젝트 폴더에 저장됩니다.

## 마이그레이션

### `vault-reader` → `vault-bridge` (v1.0.0, 2026-04-13)

**Breaking change**: `vault-reader` 플러그인이 `vault-bridge`로 리네이밍되었습니다. vault 데이터는 완전 호환되므로 파일 이관 불필요.

```bash
claude plugin uninstall vault-reader
claude plugin install vault-bridge@Lyainc-claude-kit
```

에이전트/훅/슬래시 커맨드 동작과 트리거 문구는 동일. 스크립트에서 에이전트를 정식 이름으로 참조한다면 `vault-reader:vault-searcher` → `vault-bridge:vault-searcher`로 갱신하세요.

### 기존 `claude-kit` → `thinking-tools`

기존 `claude-kit` 플러그인이 `thinking-tools`로 이름이 변경되었습니다.

```bash
# 1. 기존 플러그인 제거
claude plugin uninstall claude-kit

# 2. 새 이름으로 재설치
claude plugin install thinking-tools@Lyainc-claude-kit
```

스킬 이름과 트리거는 동일하므로 사용법 변경은 없습니다.

### `/wrapup` 스킬 제거 (obsidian-vault-manager v0.4.0)

**Breaking change**: obsidian-vault-manager의 `/wrapup` 스킬이 제거되고, 세션 기록은 `vault-bridge` 플러그인의 `/save-session` 슬래시 커맨드로 일원화되었습니다 (v1.0.0에서는 `vault-searcher` 에이전트 Mode 4에 위임했고, v1.9.0부터는 `/save-session`이 main context에서 inline 실행).

| 기존 `/wrapup` 사용 | 신규 사용 |
|---|---|
| `/wrapup` | `/save-session` 또는 "세션 정리해줘" / "세션 노트 만들어줘" — record/handoff/quick 3-mode 라우팅 후 inline 실행 |
| `/wrapup --hours 3` | `/save-session` 프로시저가 대화 컨텍스트 + 최근 변경 파일(`find -mmin`)을 수집. 범위는 세션 내용 기반으로 자동 판단 |
| `/wrapup --no-save` | `/save-session` Step 10의 AskUserQuestion에서 `[취소]` 선택 |
| 자동 저장 (세션 종료 시) | SessionEnd hook이 meaningful work 감지 시 자동 quick-save (`session-YYYY-MM-DD.md`, `tags: [session, auto-saved]`) |

**기존 파일 처리**:
- 과거 `session-wrapup` 태그/파일명의 노트는 그대로 유지 (migration script 제공하지 않음)
- 필요 시 수동으로 `type: session` frontmatter 추가 또는 그대로 아카이브

자세한 session-note 3-mode(`record` / `handoff` / `quick`) 설명은 [`vault-bridge/README.md`](vault-bridge/README.md) 참조.

## 문제 해결

**설치 후 적용 안됨**: Claude Code 재시작 필요

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

## 개발

- 개발자 가이드: [CLAUDE.md](CLAUDE.md)
- 기여 가이드 (커밋 컨벤션·리뷰 라운드 정책): [CONTRIBUTING.md](CONTRIBUTING.md)
- 릴리스 정책·절차 (lockstep): [RELEASING.md](RELEASING.md)

## 라이선스

MIT
