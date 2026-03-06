# Development Starter - Examples

Workflow examples demonstrating different modes and tool combinations.

---

## Example 1: Solo Mode + serena

### User Request

```
User: "개발 시작해줘"
```

### Step 1: Tool Selection

```
> AskUserQuestion:
> Question: "이번 작업에서 사용할 도구를 선택하세요."
> Header: "Tools"
> Options:
>   - serena (LSP 코드 분석) ✓
>   - /team (팀 협업)
>   - /ralph (자기참조 루프)
>   - /chrome-devtools (라이브 검증)
>
> User selects: serena
```

### Step 2: Mode Detection

```
/team, /ralph 미선택 → Solo Mode
```

### Step 3-5: Setup

```
[Core Rules 적용]
- Atomic Commits: 하나의 논리적 변경 = 하나의 커밋
- Test on Every Commit: 커밋 전 테스트 실행
- serena: LSP 기반 코드 분석 활성화

[Context Recording]
notepad_write_working: "[2026-03-06] devstarter: Solo Mode | serena"
```

### Step 6: Confirmation

```
| Item | Value |
|------|-------|
| Mode | Solo |
| Tools | serena (LSP) |
| Rules | Atomic commits, Test-on-commit |
| Branch | feature/current-task |

설정이 완료되었습니다. 첫 번째 작업을 알려주세요.
```

---

## Example 2: Team Mode + /team + serena + chrome-devtools

### User Request

```
User: "팀 작업 시작해줘"
```

### Step 1: Tool Selection

```
> AskUserQuestion:
> Question: "이번 작업에서 사용할 도구를 선택하세요."
> Header: "Tools"
> Options:
>   - serena (LSP 코드 분석) ✓
>   - /team (팀 협업) ✓
>   - /ralph (자기참조 루프)
>   - /chrome-devtools (라이브 검증) ✓
>
> User selects: serena, /team, /chrome-devtools
```

### Step 2: Mode Detection

```
/team 선택됨 → Team Mode
→ references/team-workflow.md 로드 및 적용
```

### Step 3: Core Rules + Team Rules

```
[Core Rules]
- Atomic Commits: Conventional Commits 스타일
- Test on Every Commit: 테스트 통과 후 커밋
- Live Verification: UI 변경 시 chrome-devtools로 확인

[Team Mode Rules]
- 각 에이전트는 별도 git branch + worktree에서 작업
- 에이전트 완료 시점마다 team-lead가 conflict 체크
- 머지 전 전체 테스트 실행
```

### Step 4: Skill Chaining

```
→ Skill("oh-my-claudecode:team") 호출
→ serena LSP 도구 활성화
→ chrome-devtools 라이브 검증 절차 적용
```

### Step 5-6: Context Recording + Confirmation

```
[Context Recording]
notepad_write_working: "[2026-03-06] devstarter: Team Mode | serena, /team, /chrome-devtools"

| Item | Value |
|------|-------|
| Mode | Team |
| Tools | serena (LSP), /team, /chrome-devtools |
| Rules | Atomic commits, Test-on-commit, Live verification |
| Branch | worktree per agent |

팀 모드로 설정되었습니다. /team 워크플로우를 시작합니다.
```

---

## Example 3: /ralph Mode

### User Request

```
User: "/devstarter"
```

### Step 1: Tool Selection

```
> User selects: serena, /ralph
```

### Step 2: Mode Detection

```
/ralph 선택됨 → Team Mode
→ references/team-workflow.md 로드 및 적용
```

### Step 3-4: Setup + Chaining

```
[Core Rules 적용]
- Atomic Commits + Test on Every Commit

→ Skill("oh-my-claudecode:ralph") 호출
→ architect 검증 루프 시작:
  1. 구현 에이전트가 코드 작성
  2. architect 에이전트가 검증
  3. 피드백 반영 → 재검증
  4. 승인 시 커밋
```

### Step 5: Context Recording

```
notepad_write_working: "[2026-03-06] devstarter: Team Mode (/ralph) | serena, /ralph"
```

### Step 6: Confirmation

```
| Item | Value |
|------|-------|
| Mode | Team (/ralph) |
| Tools | serena (LSP), /ralph |
| Rules | Atomic commits, Test-on-commit |
| Branch | feature/current-task |

/ralph 자기참조 루프를 시작합니다.
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|---|---|---|
| /team + /ralph 동시 선택 | 두 협업 모드는 동시 사용 불가 | Step 4에서 하나만 선택하도록 AskUserQuestion 재호출 |
| OMC 미설치 + /team 선택 | oh-my-claudecode 플러그인 필요 | Solo Mode 도구만 표시 (serena, /chrome-devtools) |
| 테스트 없이 커밋 | Step 3 규칙 위반 | 커밋 전 반드시 테스트 실행, 실패 시 커밋 차단 |
| 대규모 번들 커밋 | 여러 변경사항을 하나의 커밋에 포함 | 하나의 논리적 변경 = 하나의 커밋 (atomic commit) |
| Setup confirmation 생략 | 사용자가 설정 상태를 모름 | 반드시 확인 테이블 출력 (Output Format) |
