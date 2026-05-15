# Topic 4 — wizard 본문 분리 전략

**날짜**: 2026-05-12
**참가자**: Moderator, Optimistic Practitioner, Critical Practitioner, DX Expert, Plugin Architecture Expert, State Management Expert, i18n/Voice Expert, Operations/KPI Expert

## Briefing

wizard 본문을 어떻게 파일로 분리할 것인가.

- 옵션 A: 단일 `SKILL.md`에 모든 페이지 본문 인라인
- 옵션 B: 페이지 단위 별도 MD (`pages/01-intro.md`, `pages/02-thinking-tools.md`, ...) — OMC `phases/` 패턴
- 옵션 C: 플러그인 단위 분리 (`pages/thinking-tools.md`, `pages/obsidian-vault-manager.md`, `pages/vault-bridge.md`) — claude-kit 구조와 동일

## Q&A

**[Plugin Architecture Expert]**: 옵션 C가 명백히 좋아요. 새 플러그인이 추가되면 이 디렉토리에 파일 하나 더 떨어뜨리면 되니까 확장성이 자연스러워요. OMC의 phases 패턴은 phase가 워크플로 단계라서 그런 거고, 우리는 페이지가 플러그인-단위로 정렬돼요.

**[State Management Expert]**: 동의. 그리고 본문이 자주 바뀌는 도메인은 분리가 maintenance 측면에서도 유리해요. SKILL.md 한 파일에 다 넣으면 versioning 시 conflict 나기 쉬워요.

**[Optimistic Practitioner]**: 옵션 C에서 한 가지 명시할 게 있어요 — `pages/{name}.md` 파일의 자동 발견 메커니즘 정의 필요. 파일명 컨벤션 + frontmatter metadata.

**[i18n/Voice Expert]**: frontmatter에 `title`, `description`, `enabled: true`, `order: 1`, `appliesTo: <plugin-id>` 같은 필드 넣고, wizard skill이 디렉토리 스캔해서 정렬. 다국어 향후 확장 시 `pages/thinking-tools.ko.md`, `pages/thinking-tools.en.md` 구조로도 갈 수 있게.

**[Critical Practitioner]**: 옵션 A의 장점도 짚어볼게요 — 단일 파일이면 LLM이 한 번에 다 읽고 일관된 톤으로 응답 가능. 분리하면 페이지마다 컨텍스트 로드해야 해서 약간 느릴 수 있어요.

**[DX Expert]**: 그건 비합리적 우려예요. 한 페이지 분량이 8-12줄이면 LLM 컨텍스트 비용 무시 가능 수준이고, 분리의 maintenance 이득이 훨씬 커요.

**[Plugin Architecture Expert]**: 그리고 옵션 C 하면 i18n 확장이 쉬워요. 같은 디렉토리에 `.ko.md`/`.en.md` 공존 가능.

## Dialectic

| 단계 | 내용 |
|------|------|
| **Thesis** | 단일 SKILL.md (옵션 A) — 일관성·간결성 |
| **Antithesis** | OMC phases식 페이지 단위 (옵션 B) — 워크플로 추적 |
| **Synthesis** | 플러그인 단위 분리 (옵션 C) — 확장성·i18n·responsibility 일치 |

## 결론

**옵션 C 채택 — 플러그인 단위 분리**

- 디렉토리 구조:
  ```
  claude-kit-welcome/
    skills/
      welcome/
        SKILL.md           # wizard orchestration
        pages/
          00-hub.md         # 입구 페이지 (고정, order: 0)
          thinking-tools.md
          obsidian-vault-manager.md
          vault-bridge.md
          99-closing.md     # 종료 페이지 (고정, order: 99)
  ```

- 페이지 파일 frontmatter:
  ```yaml
  ---
  title: "thinking-tools — 사고 도구 7종"
  order: 10
  appliesTo: thinking-tools   # null이면 항상 표시 (hub/closing)
  enabled: true
  ---
  ```

- wizard skill 동작:
  1. `pages/*.md` 스캔
  2. frontmatter `appliesTo`에 해당하는 플러그인이 marketplace.json에 있고 설치된 경우만 노출
  3. `enabled: false`는 제외
  4. `order` 순으로 정렬

## Action Items

- [ ] `pages/` 디렉토리 스캔 로직 작성
- [ ] frontmatter 파서 (또는 간단한 grep 기반 추출)
- [ ] `00-hub.md`, `99-closing.md` 템플릿 작성
- [ ] 세 플러그인별 페이지 초안 작성 (각 8-12줄)
- [ ] i18n 확장 명세 (현재 ko 단일, 향후 `.ko.md`/`.en.md` 분리 명세)
