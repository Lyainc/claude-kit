# Document Polish - Reference

Detailed procedures and guidelines for the 4-layer verification system.

## Table of Contents

- [Layer 1: Mechanical Details](#layer-1-mechanical-details)
- [Layer 2: Consistency & Readability Details](#layer-2-consistency--readability-details)
- [Layer 3: Semantic Details](#layer-3-semantic-details)
- [Layer 4: Fact Cross-Check Details](#layer-4-fact-cross-check-details)
- [Fix Mode Behavior](#fix-mode-behavior)
- [Edge Cases](#edge-cases)

---

## Layer 1: Mechanical Details

### Markdown Lint Rules

Using standard markdownlint configuration with these priorities:

| Rule | Description | Auto-fix |
|------|-------------|----------|
| MD001 | Heading levels increment by one | ✅ |
| MD003 | Heading style consistency | ✅ |
| MD009 | Trailing spaces | ✅ |
| MD010 | Hard tabs | ✅ |
| MD012 | Multiple consecutive blank lines | ✅ |
| MD022 | Headings should be surrounded by blank lines | ✅ |
| MD023 | Headings must start at beginning of line | ✅ |
| MD031 | Fenced code blocks surrounded by blank lines | ✅ |
| MD032 | Lists surrounded by blank lines | ✅ |
| MD047 | Files should end with single newline | ✅ |

### Link Validation

**Internal Links**:
```
1. Extract all [text](path) links
2. Check if path exists relative to document
3. For anchor links (#section), verify heading exists
4. Report: broken links with suggested fixes
```

**External Links**:
```
1. Extract all [text](https://...) links
2. HEAD request to check accessibility
3. Timeout: 5 seconds
4. Report: unreachable URLs (don't auto-fix)
```

### Code Block Validation

```
1. Find all fenced code blocks (```)
2. Check for language tag
3. If missing:
   - Analyze content for language hints
   - Suggest most likely language
4. Report: blocks without tags + suggestions
```

**Language Detection Hints**:
| Content Pattern | Suggested Language |
|-----------------|-------------------|
| `function`, `const`, `=>` | javascript |
| `def`, `import`, `class` (Python style) | python |
| `func`, `package` | go |
| `public class`, `void` | java |
| `#!/bin/bash`, `echo` | bash |
| `SELECT`, `FROM`, `WHERE` | sql |
| `<html>`, `<div>` | html |
| `{`, `}`, `"key":` | json |

---

## Layer 2: Consistency & Readability Details

### Term Consistency Check

**Process**:
```
1. Build term frequency map
2. Identify potential synonyms:
   - 사용자/유저/User
   - 설정/구성/Configuration
   - 파일/파일/File
3. Flag documents using multiple terms for same concept
4. Suggest most frequent term for unification
```

**Common Term Pairs**:
| Concept | Variants |
|---------|----------|
| User | 사용자, 유저, user, User |
| Setting | 설정, 구성, 세팅, config |
| File | 파일, 파일, file |
| Function | 함수, 기능, function |
| Error | 에러, 오류, error |

### Sentence Quality Analysis

**Korean**:
```
1. Split by sentence endings (다, 요, 니다, etc.)
2. Count characters (excluding spaces)
3. Flag if > 50 characters
4. Suggest split points:
   - At commas
   - At conjunctions (그리고, 하지만)
   - At relative clauses
```

**English**:
```
1. Split by sentence endings (. ! ?)
2. Count words
3. Flag if > 35 words
4. Suggest split points:
   - At conjunctions (and, but, or)
   - At semicolons
   - Before "which", "that" clauses
```

### Tone Uniformity Check

**Korean**:
```
Pattern detection:
- 합니다/습니다 체 (formal polite)
- 해요/에요 체 (casual polite)
- 한다/이다 체 (plain)
- 하시오/십시오 체 (formal command)

Flag: mixed endings within same section
```

**English**:
```
Pattern detection:
- Active vs Passive voice ratio
- First person (I/We) vs Third person
- Contractions vs Full forms

Flag: inconsistent patterns within same section
```

---

## Layer 3: Semantic Details

### Vague Claim Detection

**Patterns to Flag**:

| Language | Pattern | Example |
|----------|---------|---------|
| Korean | 약, 대략, 정도 + number | "약 80%" |
| Korean | 많은, 적은, 수많은 | "많은 사용자가" |
| Korean | 일부, 대부분, 거의 | "대부분의 경우" |
| English | about, approximately | "about 50%" |
| English | many, few, several | "many users" |
| English | some, most, often | "most cases" |

**Output Format**:
```
Line 45: Vague claim detected
  "약 80%의 성능 향상"
  → Recommendation: Specify exact percentage or range (e.g., "78-82%")
```

### Outdated Information Detection

**Patterns to Flag**:

| Type | Pattern | Check |
|------|---------|-------|
| Version | v1.x, 2.0, version X | Compare with latest |
| Year | 2023, 2022, etc. | Flag if > 1 year old |
| Date | YYYY-MM-DD | Flag if > 6 months |
| URL | Specific version URLs | Check if current |

**Output Format**:
```
Line 23: Potentially outdated information
  "React 18.2 기준"
  → Recommendation: Verify this is still current (latest: check npm)
```

### Unexplained Term Detection

**Process**:
```
1. Build glossary of defined terms:
   - Terms followed by "is", "란", "는"
   - Terms in parenthetical explanations
2. Scan for:
   - ALL CAPS acronyms (API, SDK, CLI)
   - CamelCase terms
   - Terms in backticks
3. Flag first occurrence without explanation
```

**Output Format**:
```
Line 12: Unexplained term
  "API" first appears without definition
  → Recommendation: Add explanation on first use
     e.g., "API (Application Programming Interface)"
```

---

## Layer 4: Fact Cross-Check Details

### Gate

Scan the document once before doing any lookup. Run the layer only when at least one of these is
present; otherwise skip it and omit its line from the report entirely.

| Pattern | Example |
|---------|---------|
| Issue/PR reference | `#123`, `PR #693` |
| Repo-relative path | `scripts/check-test-exitcode.py`, `thinking-tools/skills/` — only counts with a file extension (e.g. `.py`, `.md`) or when the first segment names an existing top-level directory in this repo (e.g. `scripts/`, `skills/`, `docs/`, `thinking-tools/`); an ordinary slash-separated phrase ("read/write 권한") does not qualify |
| Script, function, or flag name | `check-version-sync.py`, `--fix`, `create_inline_comment` |
| Commit SHA (7-40 hex) | `3b82292` |
| Status assertion | "미구현", "없음", "아직", "지원 안 함", "not implemented" — only when the same sentence/line also carries an `#N`, a path, or a name; "알려진 버그는 없음" alone does not qualify |

The gate is what keeps `gh`/`git` off an ordinary polish call. A README with no issue numbers and
no paths costs exactly what it did before this layer existed.

### Checks

| Claim | Command | Mismatch looks like |
|-------|---------|---------------------|
| `#N` and what the prose says about it | `gh issue view N --json state,title` | prose says "열려 있다", state is `CLOSED` |
| path exists | test the path | referenced file was moved or deleted |
| name exists as described | `grep -rn "<name>"` | renamed, or never existed |
| SHA resolves | `git log -1 --format=%s <sha>` | rebased away, or wrong subject |
| asserted absence still holds | `grep`/`gh` for the thing | "아직 없다" but it landed since |

**A command that errors is not a mismatch.** `git log`'s `fatal: bad revision`, a `gh` auth/network
failure, or any other case where the check itself couldn't run is 저장소로 확인 불가 — 어긋남 is
reserved for a command that ran fine and returned something that contradicts the prose.

**Deterministic only.** If settling the claim needs weighing rather than one lookup, it is out of
scope — that is `adversarial-review`'s question, not this one.

### Reporting

Three verdicts, one reported:

| Verdict | Reported |
|---------|----------|
| 확인됨 | no |
| **어긋남** | **yes** — line number, what the doc asserts, what the check returned |
| 저장소로 확인 불가 | no |

Reporting the two silent verdicts would bury the one that matters under a list of things that were
fine. When the whole layer finds nothing, its report line is omitted rather than printed as zero.

### Why this layer never writes

A wrong fact means the document's *content* must change, and "Editor, not Writer" forbids exactly
that. So Layer 4 is excluded from `--fix` by design, not by omission: it hands the mismatch to a
human and stops. Auto-correcting here would quietly make this skill a writer.

---

## Fix Mode Behavior

### Auto-fix Scope

| Layer | What Gets Fixed | What Gets Reported |
|-------|-----------------|-------------------|
| Layer 1 | Formatting, whitespace, blank lines | Broken links, missing lang tags |
| Layer 2 | Nothing (suggestions only) | Consistency issues, readability suggestions |
| Layer 3 | Nothing (warnings only) | Vague claims, outdated info |
| Layer 4 | Nothing, ever (see below) | 어긋남 only — 확인됨/확인 불가 stay silent |

### Fix Process

```
1. Create backup: file.md.bak
2. Apply Layer 1 fixes in order:
   a. Run markdownlint --fix
   b. Fix heading hierarchy
   c. Add missing blank lines
3. Report applied changes with line numbers
4. List remaining issues requiring manual review
```

### Rollback

If user requests undo:
```
1. Check for .bak file
2. Restore original
3. Delete .bak file
```

---

## Edge Cases

### Empty or Minimal Documents

```
If document < 100 characters:
  - Skip Layer 2 and 3
  - Only run Layer 1
  - Report: "Document too short for full analysis"
```

### Non-Markdown Content

```
If significant non-MD content detected:
  - Flag code blocks > 50% of document
  - Suggest: "Consider if this should be a code file"
```

### Multiple Languages

```
If mixed Korean/English:
  - Apply rules for both languages
  - Flag inconsistent mixing patterns
  - Don't flag intentional code-switching
```

### Large Documents

```
If document > 10,000 words:
  - Process in chunks
  - Aggregate results
  - Report: "Large document - partial analysis possible"
```

---

## Security Considerations

### URL Validation for WebFetch

When validating external links, apply these security measures:

**SSRF Prevention**:
```
1. Only allow http:// and https:// schemes
2. Block private IP ranges:
   - IPv4: 10.x.x.x, 192.168.x.x, 172.16-31.x.x, 127.x.x.x
   - IPv6: ::1, fe80::/10, fc00::/7
3. Block localhost and internal hostnames
4. Block cloud metadata endpoints:
   - 169.254.169.254 (AWS/GCP/Azure)
   - metadata.google.internal
   - 169.254.170.2 (ECS)
5. Limit redirect depth (max 3 redirects)
6. Validate final URL after redirects
```

**Timeout Configuration**:
```
- Connection timeout: 5 seconds
- Read timeout: 10 seconds
- Total timeout: 15 seconds
```

**Rate Limiting**:
```
- Max 10 external URLs per document
- 1 second delay between requests
- If exceeded: sample URLs instead of checking all
```

---

## Error Handling

### External Link Validation Failures

| Error Type | Handling | Report Output |
|------------|----------|---------------|
| Connection timeout | Skip URL | "⚠️ URL unreachable (timeout)" |
| DNS resolution failure | Skip URL | "⚠️ URL unreachable (DNS)" |
| SSL/TLS error | Report warning | "⚠️ SSL certificate issue" |
| HTTP 4xx | Report as broken | "❌ Broken link (404/403)" |
| HTTP 5xx | Report as uncertain | "⚠️ Server error (may be temporary)" |
| Too many redirects | Report warning | "⚠️ Redirect loop detected" |
| Rate limited | Partial check | "ℹ️ Rate limited - partial check only" |

### Graceful Degradation

```
If external link validation fails entirely:
  1. Log the failure reason
  2. Continue with internal link validation
  3. Report: "External link validation skipped due to [reason]"
  4. Document remains usable without external checks
```

### Network Unavailable

```
If no network connectivity:
  - Skip all external URL checks
  - Complete Layer 1 internal checks only
  - Report: "Offline mode - external links not verified"
```
