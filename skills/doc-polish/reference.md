# Document Polish - Reference

Detailed procedures and guidelines for the 3-layer verification system.

## Table of Contents

- [Layer 1: Mechanical Details](#layer-1-mechanical-details)
- [Layer 2: Linguistic Details](#layer-2-linguistic-details)
- [Layer 3: Semantic Details](#layer-3-semantic-details)
- [Fix Mode Behavior](#fix-mode-behavior)
- [Report Generation](#report-generation)
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

## Layer 2: Linguistic Details

### LLM Trope Detection (6-Category)

**Process**:

```
1. Load trope reference from reference/llm-expression-blacklist.md
2. Phase A - Word scan:
   - Magic adverbs: "quietly", "deeply", "fundamentally", etc.
   - Delve and friends: "delve", "utilize", "leverage", "robust", etc.
   - Grandiose nouns: "tapestry", "landscape", "paradigm", "synergy"
   - Serves-as dodge: "serves as", "stands as" → suggest "is"/"are"
   - Korean expressions: 기존 블랙리스트 매칭
   - English expressions: 기존 블랙리스트 매칭
3. Phase B - Sentence scan:
   - Negative parallelism: "not" + em-dash + contrast clause
   - Dramatic countdown: "Not X. Not Y. Just Z."
   - Rhetorical Q&A: "?" followed by short answer sentence
   - Anaphora: 3+ consecutive sentences with same starting token
   - Tricolon: semicolon/period-separated 3+ parallel structures
   - Worth noting: "It's worth noting", "Importantly", "Notably"
   - Superficial analyses: trailing "-ing" constructions
   - False ranges: "From X to Y" without spectrum data
   - Gerund fragment litany: 3+ verb-less gerund sentences
4. Phase C - Paragraph scan:
   - Fragment density: 3+ consecutive <10-word paragraphs → flag
   - Listicle-in-trench-coat: "The first/second/third" pattern
5. Phase D - Tone scan:
   - False suspense: "Here's the kicker/thing/catch"
   - Patronizing analogies: "Think of it as...", "Imagine you're..."
   - Imagine a world: "Imagine a world where..."
   - False vulnerability: "I'll be honest...", "Can I be real?"
   - Truth is simple: "The reality is simpler", "History is clear"
   - Stakes inflation: "fundamentally reshape", "game-changer"
   - Let's break down: "Let's unpack/explore/dive in"
   - Vague attributions: "Experts argue", "Studies show"
   - Invented concept labels: "the X paradox/trap/effect"
6. Phase E - Formatting scan:
   - Em-dash count: >10 per 2000 words → flag
   - Bold-first bullet ratio: >80% bold-start items → flag
   - Unicode decoration: →, smart quotes, • usage
7. Phase F - Composition scan:
   - Fractal summaries: intro/conclusion similarity per section
   - Dead metaphor: same metaphor keyword 5+ times
   - Historical analogy stacking: 3+ company names in sequence
   - One-point dilution: 3+ paragraphs with high semantic overlap
   - Content duplication: near-identical sentences/paragraphs
   - Signposted conclusion: "In conclusion", "To sum up"
   - Despite its challenges: problem → immediate optimism pivot
8. Output: sorted by category, then severity, then line number
```

**Severity Levels**:

| Level | Criteria | Example |
|-------|----------|---------|
| High | Strong AI signal even in isolation | B1 Negative Parallelism, E1 Em-Dash Addiction, D6 Stakes Inflation |
| Medium | AI signal when clustered | B5 Tricolon Abuse, D2 Patronizing Analogies, F2 Dead Metaphor |
| Low | AI signal only at high frequency | B7 Superficial Analyses, E3 Unicode Decoration, B8 False Ranges |

### Trope Density Score

**Calculation**:

```
raw_count = total tropes detected
word_count = total words in document
density = (raw_count / word_count) * 1000

Weighted density (severity weighting):
  weighted = sum(High × 3 + Medium × 2 + Low × 1) / word_count × 1000

Thresholds:
  Low:    < 3.0 weighted/1000 words — minimal AI signal
  Medium: 3.0 - 6.0 — noticeable AI patterns
  High:   > 6.0 — strong AI signal, major revision needed
```

### Clustering Detection

**Algorithm**:

```
1. Sort all detected tropes by line number
2. Sliding window: 10 lines
3. If window contains 3+ tropes → mark as hotspot
4. Report: line range, trope names, category mix
5. Cross-category clusters (e.g., Word + Structure + Tone)
   are stronger AI signals than same-category clusters
```

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

## Fix Mode Behavior

### Auto-fix Scope

| Layer | What Gets Fixed | What Gets Reported |
|-------|-----------------|-------------------|
| Layer 1 | Formatting, whitespace, blank lines | Broken links, missing lang tags |
| Layer 2 | Nothing (suggestions only) | LLM expressions, inconsistencies |
| Layer 3 | Nothing (warnings only) | Vague claims, outdated info |

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

## Report Generation

### Report Structure

```markdown
# Document Polish Report

**File**: {filename}
**Date**: {timestamp}
**Mode**: {default|fix|report}

## Executive Summary

- Total issues: {count}
- Auto-fixed: {count}
- Manual review needed: {count}
- Quality score: {score}/100

## Layer 1: Mechanical

### Fixed
{list of auto-fixed items}

### Remaining
{list of issues needing attention}

## Layer 2: Linguistic

### High Priority
{critical LLM expressions}

### Medium Priority
{consistency issues}

### Low Priority
{style suggestions}

## Layer 3: Semantic

### Warnings
{vague claims, outdated info, unexplained terms}

## Recommendations

{prioritized action items}

## Statistics

- Word count: {count}
- Sentence count: {count}
- Average sentence length: {avg}
- Heading count: {count}
- Link count: {internal}/{external}
- Code block count: {count}
```

### Quality Score Calculation

```
Base score: 100

Deductions:
- Layer 1 issue: -2 points each (max -20)
- Layer 2 High: -5 points each (max -25)
- Layer 2 Medium: -2 points each (max -15)
- Layer 2 Low: -1 point each (max -10)
- Layer 3 warning: -3 points each (max -30)

Minimum score: 0
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
