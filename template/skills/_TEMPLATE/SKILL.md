---
name: [skill-name]
# 소문자/숫자/하이픈만, 64자 이하

description: |
  [What] 이 스킬이 무엇을 하는지 구체적으로 설명.
  [When] Use when [사용 시나리오], or when the user mentions [트리거 키워드].
# Claude가 description을 보고 자동 호출 여부를 결정
# 1024자 이하 필수, "Use when..." 패턴 권장
---

# [Skill Display Name]

[한 줄 요약]

## When to Use

- [사용 시나리오 1]
- [사용 시나리오 2]

## Prerequisites

- [필요한 입력/파일/정보]

## Core Workflow

### Phase 1: [단계명]

[핵심 지침]

### Phase 2: [단계명]

[핵심 지침]

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)

## Quick Start

```
User: "[예시 요청]"
→ Phase 1: [수행 내용]
→ Output: [산출물]
```
