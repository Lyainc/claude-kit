# audit `--deep` — Phase 2.5 reference

The `--deep` opt-in phase of the `audit` skill, split out of `SKILL.md` (#447) so the skill body
fits inside the 5,000-token window auto-compaction re-attaches. Nothing here runs without
`--deep`; without the flag `audit` makes zero LLM judgment calls end to end, so this file is only
read when the flag is present.

Both sub-checks below end in a mandatory per-candidate `AskUserQuestion` confirm gate. That gate is
not optional and not summarisable — a semantic judgment never becomes a finding unsupervised.

## Phase 2.5 — DEEP (opt-in, `--deep`)

**Purpose**: Run every LLM-judgment check gated behind `--deep`. This is the **only** phase in this skill that reads file bodies or uses LLM judgment — SCAN, CLASSIFY, and REPORT stay LLM-cost-0 without `--deep`. Two independent sub-checks run here, each with its own candidate-pair prefilter and its own confirm gate: E12b (cross-page wiki contradiction, #336, below) and E9c (tag semantic synonym, #167, further down).

### E12b — cross-page wiki contradiction

**Purpose**: Detect `wiki/` pages that assert conflicting claims about the same subject (#336).

**Inputs**: `frontmatter_records` and `wikilinks_by_file` from the scan bundle (already collected, no re-scan).

**Tools used**: Read, AskUserQuestion.

**Skip conditions** (exit phase immediately, no findings added):
- `--deep` flag not passed.
- Fewer than 2 records with top folder `wiki/` AND `fm.type == "wiki"`.

**Procedure**:

1. Collect `wiki_pages` = every `frontmatter_records` entry with top folder `wiki/` and `fm.type == "wiki"`.

2. Build **candidate pairs** deterministically (no LLM, cheap prefilter — bounds the expensive judgment step to topically-related pages instead of every O(n²) pair): two wiki pages `(A, B)` are a candidate when EITHER holds:
   - they share at least one tag (case-insensitive intersection of `fm.tags`), or
   - one wikilinks to the other (via `wikilinks_by_file`).

   If zero candidate pairs, exit phase (no findings).

3. Read each **unique** page in `wiki_pages` that appears in at least one candidate pair exactly once, and cache its body by path — a hub page in several candidate pairs is not re-read per pair.

4. Judge each candidate pair using the cached bodies: do the two pages assert **conflicting claims about the same subject** (a fact, a number, a decision, a status that cannot both be true)? Complementary information, different scopes, or purely stylistic differences are NOT a contradiction — do not flag those.

5. Stage every pair judged contradictory as a DEEP candidate. Do **not** add it to the findings list yet — Step 6 is the mandatory FP-mitigation gate.

6. If any DEEP candidates exist, confirm each **individually** — a single generic accept/decline does not let the user keep one pair and drop another. `AskUserQuestion` takes up to 4 questions per call, so ask one question per candidate pair, batching in groups of ≤4 (sequential calls if there are more than 4):
   ```
   AskUserQuestion:
     questions:
       - question: "wiki/a.md ↔ wiki/b.md — 이 쌍, 실제 상충으로 볼까요?"
         header: "상충 확인"
         options:
           - label: "실제 상충 — 보고에 포함"
             description: "<one-line reason the pages conflict>"
           - label: "상충 아님 — 무시"
             description: "판단 오류로 보고 이 쌍은 건너뜀"
       - question: "wiki/c.md ↔ wiki/d.md — 이 쌍, 실제 상충으로 볼까요?"
         header: "상충 확인"
         options: [...]   # same two-option shape, one row per additional candidate pair
   ```
   Each pair's answer is independent. A candidate the user declines is dropped silently — no finding, no residual state.

7. Every confirmed pair becomes one finding:
   ```
   {
     "error_type": "wiki_contradiction",
     "severity": "Warning",
     "priority": "P1",
     "path": "wiki/a.md ↔ wiki/b.md",
     "detail": "human-readable reason",
     "auto_fix_eligible": false
   }
   ```
   Append it to the findings list produced by CLASSIFY (sorts under E12 in REPORT, alongside E12a staleness findings).

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to the E9c sub-check below.

### E9c — tag semantic synonym

**Purpose**: Detect two vault-wide tags that name the same concept under different spellings (e.g. `llm` ↔ `large-language-model`, `react` ↔ `reactjs`, #167). A fixed synonym dictionary was rejected in #119 as over-firing and costly to maintain, so this judgment is LLM-only, gated and confirmed the same way as E12b above.

**Inputs**: `frontmatter_records` from the scan bundle (already collected, no re-scan) — the same vault-wide tag aggregation E9a already builds in `audit-validate.py`, re-derived here in-skill. E9c never touches that reference impl or the `--dod` gate.

**Tools used**: AskUserQuestion (no Read needed — tag strings and file counts are enough context for the judgment; unlike E12b there are no file bodies to read).

**Skip conditions** (exit sub-check immediately, no findings added):
- `--deep` flag not passed.
- Fewer than 2 distinct tags meet the `E9_MIN_FILES` (= 3) floor below.

**Procedure**:

1. Build `tag_files` = lowercase tag → set(file paths), from every `frontmatter_records[].fm.tags` (same aggregation as E9a). Drop any tag used in fewer than `E9_MIN_FILES` (3) files — reuses E9a/E9b's existing FP floor so a one-off tag never reaches LLM judgment.

2. Build **candidate pairs** deterministically (no LLM, cheap prefilter — mirrors E12b's shared-tag/wikilink prefilter, adapted to compare tags instead of pages; #167's D10 design note names these signals source-overlap + common-neighbor). First precompute a tag → co-occurring-tags map once, in a single pass over `frontmatter_records` (not per pair — that map is what Step 1's `tag_files` pass already walks, so build both together). Then, for every distinct pair `(A, B)` that both survived Step 1, it's a candidate when EITHER holds:
   - **source overlap**: at least one file's `tags` list contains BOTH `A` and `B`, or
   - **common neighbor**: `A`'s entry in the precomputed map shares at least one tag with `B`'s entry.

   Skip any pair already reported by E9a — a lookup against `vocabulary_pairs[]` (produced by SCAN Phase's `detect-vocabulary` step), not a re-derivation. Regular singular/plural is already deterministically handled there, no LLM opinion needed. If zero candidate pairs, exit sub-check (no findings).

3. Judge each candidate pair: do `A` and `B` name the **same concept** under two different spellings/phrasings (a true synonym), as opposed to two related-but-distinct concepts that merely tend to co-occur (e.g. a language and a tool commonly used with it)? Judge from the tag strings and their file counts alone.

4. Stage every pair judged synonymous as a DEEP candidate. Do **not** add it to the findings list yet — Step 5 is the mandatory FP-mitigation gate (same contract as E12b Step 6).

5. If any DEEP candidates exist, confirm each **individually**, exactly like E12b Step 6 — one `AskUserQuestion` per candidate pair, batched in groups of ≤4 (sequential calls if more than 4):
   ```
   AskUserQuestion:
     questions:
       - question: "'llm' (N개 파일) ↔ 'large-language-model' (M개 파일) — 같은 개념의 동의어로 볼까요?"
         header: "동의어 확인"
         options:
           - label: "동의어 — 보고에 포함"
             description: "<one-line reason the tags are synonymous>"
           - label: "동의어 아님 — 무시"
             description: "판단 오류로 보고 이 쌍은 건너뜀"
       - question: "'X' (N개 파일) ↔ 'Y' (M개 파일) — 같은 개념의 동의어로 볼까요?"
         header: "동의어 확인"
         options: [...]   # same two-option shape, one row per additional candidate pair
   ```
   Each pair's answer is independent. A candidate the user declines is dropped silently — no finding, no residual state.

6. Every confirmed pair becomes one finding, folded into the SAME `tag_vocabulary_inconsistency` bucket E9a/E9b already populate (renders under the existing E9 vault-wide heading in REPORT — no new error type):
   ```
   {
     "error_type": "tag_vocabulary_inconsistency",
     "severity": "Warning",
     "priority": "P2",
     "path": "",
     "detail": "태그 의미 동의어(LLM 판단, --deep): 'llm' (N개 파일) ↔ 'large-language-model' (M개 파일) — <reason>",
     "auto_fix_eligible": false
   }
   ```
   Append it to the findings list produced by CLASSIFY.

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to REPORT with the (possibly unchanged) findings list.
