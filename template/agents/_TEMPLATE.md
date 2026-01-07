---
name: [agent-name]
# 고유 식별자 (예: researcher, code-reviewer)

description: |
  [1-2문장: 이 에이전트를 언제 호출해야 하는지]
  Use keywords for auto-invocation. Include "proactively" for eager activation.

tools: [Read, Write, Edit, Grep, Glob, Bash, WebSearch, WebFetch, Task]
# Read, Write, Edit: 파일 작업
# Grep, Glob: 검색
# Bash: 명령어 실행
# WebSearch, WebFetch: 웹 검색
# Task: 하위 작업 생성

model: opus
# opus | sonnet | haiku | inherit

permissionMode: default
# default | acceptEdits | bypassPermissions | plan | ignore
---

# [Agent Display Name]

[에이전트 역할 요약]

## When to Use

- [호출 상황 1]
- [호출 상황 2]

## Approach

1. [단계 1]
2. [단계 2]
3. [검증]

## Output

- [출력 형식]
- [품질 기준]

## Boundaries

**DO**: [해야 할 것]

**DO NOT**: [하지 말아야 할 것]
