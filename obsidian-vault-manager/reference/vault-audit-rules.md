# vault-audit — Error Type Detection Rules

Detection rules for the `audit` skill's CLASSIFY phase. The skill body (`skills/audit/SKILL.md`) summarizes these as a table; this file is the canonical pseudocode reference.

Nine error types cover v4's three-folder vault layout (`sources/`, `notes/`, `assets/`) plus v5's `wiki/`. Severity buckets: **Critical** (data integrity risk), **Warning** (quality / navigation risk), **Info** (style / convention). A tenth item, `unreadable`, is not a rule-driven error type — it is `scan-summary.py`'s report of a file it could not read at all (see the Priority Mapping table and `## SCAN output budget` below).

> **Reading `**Source**` below (#614)**: each type's `**Source**` names what `scan-summary.py` reads OFF DISK to apply that predicate (`frontmatter_records`/`filename_records`/`inbound_links` — the untruncated raw scans). It is NOT what CLASSIFY itself receives — CLASSIFY only ever sees the reduced `scan_summary.errors.<code>` bundle these predicates compute into (`skills/audit/SKILL.md`'s CLASSIFY table `Source` column), same as `## SCAN output budget` below describes. Use this file for the RULE definitions; use the CLASSIFY table for what is actually in context.

> **v4 history**: Legacy E6–E9 (project-binding checks) were removed in v4 because `20_Projects/` is no longer part of the layout. The codes were later reused — PR 5 (`/audit` Phase 2) introduced a new **E6 `stale_inbox`** and **E7 `stale_draft`** covering v4 §6.1 Step 2 "정체" (stagnation). PR 4 had added P0–P2 priority mapping and display-only manifest summary; PR 5 extended with P1 stagnation. PR 4d added **E8 `promotion_candidate`** (P2/Info), read from the vault-bridge manifest.
>
> **v5 removal (#480, 2026-08-02)**: E7 `stale_draft` and E8 `promotion_candidate` were removed. Both existed only to serve the B-layer promotion gate (raw/draft → evergreen), and that gate itself was abolished (v5 §5/§6, #477 범주 오류 — a gate that only acts after intake cannot defend intake). E7 never fired in practice (`/vault-save` writes no `status:` field, so no new file could ever reach `status: draft`); E8 kept firing on `status: archived` notes because it read `type`+refs/access without consulting `status` at all (#435) — noise for a gate that no longer existed. The codes E7/E8 are retired, not reused; a future check takes a new number.
>
> **v5 removal (#482, #477 하위 C)**: E4 `broken_wikilink` was removed as a native-Obsidian duplicate — Obsidian's own unresolved-link highlighting already surfaces the same signal inside the app, and E4's own extractor had a measured 33% false-positive rate on backticked syntax examples before the #434 masking fix. The masking logic (`mask_code`, `CODE_FENCE`/`UNCLOSED_FENCE`/`INLINE_CODE`) is preserved — E5 orphan detection reads the same masked inbound-link index, so over-masking still silently manufactures a false orphan even with E4 gone. The code E4 is retired, not reused; a future check takes a new number.

## Priority Mapping

Every finding carries a `priority` field independent of severity. Priority drives REPORT grouping; severity drives semantic labeling.

| Code | Priority | Rationale |
|------|----------|-----------|
| E1   | P0       | Frontmatter absent → file is invisible to type opt-in (v4 §2.2); blocks all downstream tooling. |
| E2   | P0       | Required fields missing → status machine and type routing break. |
| E3   | P0       | v3-style filename → convention violation that blocks future automated routing. |
| E5   | P2       | Orphan note → quality signal, not integrity risk. |
| E6   | P1       | Stale sources → raw input never processed; loses freshness, signals review needed. |
| E9   | P2       | Tag/property vocabulary inconsistency → a vault-wide style signal (kepano "consistent style"), never an integrity defect. Canonical-form choice is always the user's call → no auto-fix. E9a/E9b are deterministic; E9c semantic synonym ships as the skill-only `--deep` LLM opt-in (#167, see the `## E9` section below). |
| E10  | P1       | Misplaced file → `type` lives in the wrong canonical folder; moving affects inbound links (display-only warning). |
| E11  | P1       | Unstructured path → file outside `sources/notes/assets`; structural drift, moving affects inbound links (display-only warning). |
| E12  | P1       | Wiki self-audit (v5 §7 U3) → a `wiki/` page whose `verified:` age exceeds `STALE_WIKI_DAYS`; staleness is the abandonment risk for the LLM wiki. E12a (staleness) is display-only; its companion `E12_wiki_unverified` (#494) flags a `wiki/` page whose `verified:` is missing or unparseable — staleness is uncomputable, so it is reported for a different reason instead of being skipped forever; E12b cross-page semantic contradiction ships as the skill-only `--deep` LLM opt-in (#336, see the `## E12 — wiki_self_audit` section below); E12c (#698, #645 F1) flags a deterministic near-duplicate — two wiki pages sharing the exact same `tags` set plus an overlapping title token. |
| `unreadable` (#614) | P0 | Not an error type — no rule fired, the file's frontmatter was never examined (permission denied, encoding error, etc). Ranked ahead of E1: "we could not look" is a worse integrity signal than any judgment made ON content that WAS read. Kept OUT of every content-based type (E1/E3/E5/E6/E10/E11/E12) so a file that could not be read is never laundered into a finding about content nobody saw. See `## SCAN output budget` below. |

> **P0 = 무결성 (integrity)**: All three E1–E3 types are in v4 §6.1 Step 1 "무결성", which outputs P0 items first and gates OPTIONAL-FIX on user confirmation.
> **P1 = 정체/구조 (stagnation / structure)**: E6 surfaces unprocessed inputs; E10 and E11 surface folder-structure drift; E12 surfaces stale wiki pages. All are visible signal only, never auto-fixed (each requires a semantic decision: process / archive / move / recompile).
> **P2 = quality**: E5 orphan notes and E9 vocabulary inconsistencies are quality signals, not integrity defects.

> **Code numbering**: E9 (#119, #167) is the tag/property vocabulary check below. Its deterministic sub-checks (E9a singular/plural, E9b camel/snake property naming) ship in `audit-validate.py`; E9c (semantic synonyms) ships as a skill-only `--deep` LLM opt-in in `audit/SKILL.md` Phase 2.5 stub, full procedure in `reference/audit-deep.md` (see the E9 section). E10/E11 are the structural checks per #128/#129. E12 (#330, #336, #698) is the wiki self-audit: E12a staleness and E12c near-dup both ship deterministically in `audit-validate.py`; E12b cross-page contradiction ships as a skill-only `--deep` LLM opt-in in `audit/SKILL.md` Phase 2.5 stub, full procedure in `reference/audit-deep.md` — the same deterministic/semantic split E9 draws around E9c, and both now ship behind the same `--deep` flag.

The priority mapping is canonical in `scripts/test/audit-validate.py` (constant `PRIORITY_BY_TYPE`). Keep this table and that constant in sync. `audit-validate.py` is a **mechanical reference oracle** for DoD measurement — not the production classifier (production path = `ovm-primitives.sh` + SKILL.md). Drift between the two is detected by `--dod`'s `priority_mismatches` field.

## E1 — `missing_frontmatter` [Critical]

**Rule**: `has_frontmatter == false`
**Source**: `frontmatter_records`
**Guard**: Skip `.ovm/` and `.obsidian/` paths.

## E2 — `missing_required_fields` [Critical]

**Rule**: `has_frontmatter == true` AND `missing_required` is non-empty
**Source**: `frontmatter_records`
**Reports**: which fields are missing.

**Required fields**:

| Scope | Fields |
|-------|--------|
| All types (universal) | `created`, `tags`, `type`, `provenance` |

`status` is **not** a required field for any type. It used to be required for `type: note` and
`type: decision` (v4 §3.3 status machine); that machine was abolished when B became a reference
warehouse (v5 §5/§6, #480), and `/vault-save` writes no `status` at all — requiring it would flag
every newly saved file as Critical. A `status:` still present on an older file is not an error.

`provenance:` joined E2 (#477 item 4) — it was required by the v5 §4.1/§5 spec at the
`/vault-save` and `/wiki` write points from the start, but E2 itself couldn't enforce it until the
pre-v5 inventory was backfilled: the 135 sources/notes/wiki files that predated the requirement now
carry a `provenance:` derived from each file's git add-commit (date + subject) as the origin record.

**Tag inference** (#127, display-only proposal): when `tags:` is among the
missing fields, the OPTIONAL-FIX step does **not** insert an empty `tags: []`.
It derives a deterministic tag proposal (no LLM) via
`ovm-primitives.sh infer-tags <relpath>` using three tiers, in order. Tokens are
lowercased, deduplicated (original order preserved), and pure-numeric / stopword
tokens (`the a an of and or to for`) are dropped — so the proposal plausibly
passes a future E9 vocabulary check (#119, still open): lowercase, kebab-friendly
atoms, no duplicates. Inference here is intentionally conservative (no
singular/plural normalization) to avoid hard-depending on the not-yet-finalized
E9 standard.

| Tier | Source | Rule |
|------|--------|------|
| 1 | `type:` field | always the first tag (`type: note` → `note`) |
| 2 | filename slug | strip the date prefix (`YYYY-MM-DD-` / `YYYY-MM-`) and a leading `{type}-`, then split the remainder on `-`/`_` into one tag per word |
| 3 | first segment under `notes/` | only inside `notes/{segment}/...` (path depth ≥ 3) → add `segment`. This is `rel.parts[1]`, **not** the file's literal parent folder — at depth 4+ (`notes/diary/2026/x.md`) it tags `diary`, never `2026`. The vault-root folder name itself (`notes`) is structural, not a domain. |

```
infer_tags(rel, fm):
  tags = []
  push(fm.type)                         # tier 1 (skipped if type absent)
  slug = strip_date_and_type_prefix(rel.name)
  for word in split(slug, /[-_]+/): push(word)   # tier 2
  if rel.parts[0] == "notes" and len(rel.parts) >= 3:
    push(rel.parts[1])                  # tier 3: first segment under notes/, always index 1 —
                                         # a pure-digit segment (a year folder) is dropped by
                                         # push()'s digit filter, so no separate year exception
                                         # is needed here.
  return tags                           # push() lowercases, dedups, drops stopwords/digits
```

**Examples**:
- `notes/llm/decision-2026-04-12-context-window.md`, `type: decision` → `[decision, context, window, llm]`
- `sources/capture-2026-05-01-obsidian-api.md`, `type: capture` → `[capture, obsidian, api]`

**Graceful empty slug**: a date-only filename (e.g. `session-2026-04-12.md`)
leaves an empty slug after prefix stripping → the proposal falls back to the
**type tag only** (never crashes, never an empty list when `type:` is present).
The proposal is a suggestion — Phase 4 keeps the `수정 실행` confirmation gate and
previews `추론된 태그: [X, Y, Z]`; nothing is auto-committed.

## E3 — `filename_convention_violation` [Warning]

**Rule**: file does not conform to v4 naming convention (v4 §3.6)
**Source**: `filename_records`

v4 filename rules per folder:

| Folder | Convention | Example violation |
|--------|-----------|-------------------|
| `notes/` | `{slug}.md` (no date prefix) — or `{type}-YYYY-MM-DD-{slug}.md` for dated types (`decision`, `plan`) | `2026-04-bad-name.md` (`\d{4}-\d{2}-` date-first, v3 style) |
| `sources/` | Exempt — raw input zone; any filename accepted | — |
| `assets/` | Exempt — attachments; any filename accepted | — |

**Guard**: `_index.md` is always valid (skip). Files in `sources/` and `assets/` are exempt.

**Detection pseudocode** for files in `notes/`:

```
for each file in notes/ (recursive):
  if file.name == "_index.md": skip
  if file.name matches /^\d{4}-\d{2}-/: → filename_convention_violation
  # date-first prefix is a v3 artifact; v4 requires type-first or no-date slugs
```

**Suggested filename** (#126, display-only): when a violation is found, compute a
v4-conforming rename suggestion and append `권장 파일명: {name}` to the finding
`detail`. The filename is the source of truth for the slug (`created:` carries
only the date), so the slug is extracted from the current filename.

```
slug = stem
  minus leading /^\d{4}-\d{2}(-\d{2})?-/    # strip date-first prefix
  minus leading /^(note|decision|plan|capture|session)-/   # strip a type prefix

suggested_filename(rel, fm):
  type = fm.type ; created = parse(fm.created)
  if type missing:                  → None   (keep base message; cannot suggest)
  if type == "note":                → "{slug}.md"          (date prefix removed)
  if created is None (non-note):     → None
  if type in {decision, plan}:       → "{type}-{YYYY-MM-DD}-{slug}.md"
  if type in {capture, session}:     → "{type}-{YYYY-MM-DD}.md"
  else:                             → None
```

Rename is **never auto-applied** — it affects inbound wikilinks, so the audit
only suggests; the user decides.

## E5 — `orphan_note` [Warning]

**Rule**: A `.md` file in `notes/` (any depth) has zero entries in `inbound_links[stem]`.
**Source**: `inbound_links` (built from full vault scan).
**Guard**: `_index.md` files are never orphans. Files in `sources/` are exempt (unprocessed captures). Files in `assets/` are exempt.

**Connection candidates** (#130, display-only; rarity-weighted scoring #495): for
each orphan, compute the top-3 `notes/` files by a **rarity-weighted** shared-tag
score — not raw shared-tag COUNT — so a tag common across the vault (e.g. every
note tagged `note`) doesn't manufacture a "connection" on its own; a tag seen on
only a couple of files outweighs it. Exact-match intersection only, no semantic
synonyms. Build a `notes/` tag index once before the orphan loop to avoid O(N²).

**Production primitive** (#619): the pseudocode below ships as `ovm-primitives.sh
e5-candidates <dir>` — CLASSIFY looks up an orphan's `{candidates, floor_gated}` by
path from that primitive's output (audit/SKILL.md Phase 1 Step 10) instead of
hand-computing the score. `audit-validate.py`'s copy of this same algorithm stays
the mechanical `--dod` reference oracle, unaffected by this primitive's addition
(same production/oracle split as E9, see `## E9`).

```
notes_tag_index = [(rel, frozenset(tags)) for rel in notes/ if rel != _index.md]

df(t) = count of notes_tag_index entries whose tagset contains t   # E9a-style
        vault-wide aggregation, built once from notes_tag_index (no 2nd scan)

score(P, Q) = Σ_{t ∈ P.tags ∩ Q.tags} 1 / log(1 + df(t))

for each orphan P:
  orphan_tags = frozenset(P.tags)            # [] when tags empty
  scored = [(score(P, Q), Q.rel, sorted(shared))
            for Q in notes_tag_index if Q != P and (shared := orphan_tags & Q.tags)]
  scored.sort by (score desc, path asc)
  if not scored:
    candidates, floor_gated = [], False       # no note shares ANY tag with P
  elif scored[0].score < E5_MIN_CANDIDATE_SCORE:
    candidates, floor_gated = [], True         # shared tags exist, but the best
                                                # match is still noise — don't
                                                # force-fill top-3 with weak matches
  else:
    candidates, floor_gated = scored[:3], False  # [{path, shared_tags}]
```

`floor_gated` is NOT the same condition as `candidates == []` on its own — it
distinguishes *why* candidates is empty, so the rendered `detail` (below) can
say which. Conflating the two (e.g. testing only `orphan_tags` truthiness) had
misreported an orphan whose tag is shared by NO ONE as "공유 태그가 너무 흔해" —
backwards, since there was no shared tag, common or otherwise.

`E5_MIN_CANDIDATE_SCORE` (= 0.5) is the floor the BEST-scoring candidate must
clear. A single shared tag scores `1/log(1+df)`: a tag exclusive to this
orphan+candidate pair (df=2) scores ~0.91, down to shared with 4 other notes
too (df=6) at ~0.51 — both clear the floor. A tag common enough to sit on 7+
notes/ files (df>=7) scores <=0.48 alone, so it takes >=2 such tags, or one
genuinely rarer one, to count as a real connection signal.

The finding carries a **structured** `candidates: [{path, shared_tags}]` field
(REPORT renders the `연결 후보` line from it) AND a rendered `detail`:

- with candidates: `연결 후보: [[X]] (공유 태그: a, b); [[Y]] (공유 태그: a)`
- empty tags, or tags present but no other note shares any of them (`floor_gated`
  is False): `연결 후보 없음 (공유 태그 없음)`, `candidates: []`
- shared tags exist but the best score misses the floor (`floor_gated` is True):
  `연결 후보 없음 (공유 태그가 너무 흔해 신호가 되지 못함)`, `candidates: []`

Empty-tags orphans are handled gracefully (no candidate computation, no error).
Linking position is the user's decision — the audit only suggests candidates.

## E6 — `stale_inbox` [Warning]

**Rule**: A file in `sources/` is still "raw" and its `created:` date is more than `STALE_INBOX_DAYS` (= 14) days before today.
**Source**: `frontmatter_records` (uses `fm.created` + `fm.status`).
**Guard**: Files with explicit non-raw status (e.g., `type: session` + `status: active`, or any other processed marker) are exempt. Files without a parseable `created:` field are skipped (no false positive on malformed frontmatter — E1/E2 catch those separately).

**Detection pseudocode**:

```
for each record in frontmatter_records where path startswith "sources/":
  status = normalize(fm.status)            # non-string or missing → ""
  if status not in {"", "raw"}: skip       # explicit non-raw → exempt
  if parse(fm.created) is None: skip       # malformed → E1/E2 territory
  age_days = today - parse(fm.created)
  if age_days > STALE_INBOX_DAYS: → stale_inbox
```

**Rationale**: Captures (and any unprocessed sources file) accumulate freshness debt — review and either promote to `notes/` or delete. `type: session` notes carry `status: active`/`closed` and are skipped, so historical session records don't pollute the stagnation report.

## E9 — `tag_vocabulary_inconsistency` [Warning]

**Rule**: The vault mixes two spellings of the same vocabulary atom. kepano's vault discipline ("Property names and values should aim to be reusable across categories"; "Having a consistent style collapses hundreds of future decisions into one") wants one canonical form per concept. E9 surfaces the two deterministic, non-semantic cases:

| Sub-check | Detects | Example pair |
|-----------|---------|--------------|
| **E9a** singular/plural | a lowercase tag `t` and its regular `+s` plural `t+"s"` both used | `api` ↔ `apis`, `tag` ↔ `tags` |
| **E9b** property naming | a frontmatter key in camelCase and its snake_case equivalent both used | `sourceUrl` ↔ `source_url` |

**E9c** (semantic synonyms — `llm` ↔ `large-language-model`, `react` ↔ `reactjs`) was **out of scope** for #119: a fixed synonym dictionary over-fires and is costly to maintain. It ships instead as a skill-only `--deep` LLM opt-in (#167, see the **E9c** subsection below), following the source-overlap + common-neighbor approach from #119's D10 design note.

**Source**: `frontmatter_records` — but aggregated **vault-wide**, not per file. E9 is a single vault-level pass over every record's `tags` (E9a) and frontmatter keys (E9b); each detected pair is one finding.

**Finding shape**: vault-level. `path: ""` (empty — the inconsistency is a property of the vault, not of any one file). REPORT must group the empty path gracefully (render under a "볼트 전역" / vault-wide heading rather than a per-file bullet).

### FP guard — frequency threshold (N ≥ 3)

A pair is reported **only when BOTH forms appear in `E9_MIN_FILES` (= 3) or more files** (file count per form, deduped per file). This is the Risk-section mitigation: a one-off typo (`apis` written once) does not drag an established `api` tag into a finding, and intentional distinct singulars (`status` vs `statuses` — note `statuses` is an *irregular* `+es` plural, so E9a never pairs them anyway) stay quiet. The threshold plus P2/visibility-only (never auto-fixed, never blocks) keeps E9 conservative.

> **Irregular plurals excluded by construction**: E9a pairs only `t` with the literal `t+"s"`. `leaf`/`leaves`, `status`/`statuses`, `index`/`indices` differ by more than a trailing `s`, so the naive rule cannot pair them — no irregular-plural FPs, no English-morphology table needed.

### Detection pseudocode

```
E9_MIN_FILES = 3

# E9a — singular/plural tags (vault-wide)
tag_files = {}                                  # lowercase tag → set(file paths)
for rec in frontmatter_records:
  for t in (rec.fm.tags or []):                 # only string items
    tag_files[lower(t)].add(rec.path)
seen = set()
for t in sorted(tag_files):                     # deterministic order
  plural = t + "s"
  if plural in tag_files and t not in seen and plural not in seen:
    if len(tag_files[t]) >= E9_MIN_FILES and len(tag_files[plural]) >= E9_MIN_FILES:
      report pair (t, plural)                    # path:"" — singular/plural
      seen.add(t); seen.add(plural)

# E9b — camelCase vs snake_case property keys (vault-wide)
key_files = {}                                  # frontmatter key → set(file paths)
for rec in frontmatter_records:
  for k in rec.fm.keys():
    key_files[k].add(rec.path)
for camel in sorted(key_files):
  if not re.search(r"[a-z][A-Z]", camel): continue          # camelCase marker
  snake = re.sub(r"([a-z])([A-Z])", r"\1_\2", camel).lower() # inferred equivalent
  if snake == camel: continue
  if snake in key_files:
    if len(key_files[camel]) >= E9_MIN_FILES and len(key_files[snake]) >= E9_MIN_FILES:
      report pair (camel, snake)                 # path:"" — property naming
```

**`detail` rendering** (Korean, user-facing): name both forms and their file counts, e.g. `태그 단복수 혼용: 'api' (N개 파일) ↔ 'apis' (M개 파일) — 정준 형태를 하나로 통일하세요` (E9a) / `프로퍼티 이름 혼용(camel/snake): 'sourceUrl' (N개 파일) ↔ 'source_url' (M개 파일)` (E9b). The canonical-form choice is **never** suggested or auto-applied — the user picks.

**Guard**: non-string tag items are ignored (a malformed `tags:` is E2 territory). Files without `tags`/frontmatter contribute nothing. Each unordered pair is reported once (E9a dedup via `seen`).

**Auto-fix**: none. Picking the canonical form (and rewriting every affected file) is a semantic decision with inbound-link and habit implications — E9 is display-only.

### E9c — tag semantic synonym (`--deep`, skill-only, #167)

**Where it lives**: `audit/SKILL.md` Phase 2.5 stub, full procedure in `reference/audit-deep.md`, not `audit-validate.py`. There is no reference-impl function for E9c and none is planned — the judgment step needs LLM semantic reasoning over tag strings, which the deterministic reference impl structurally cannot do (same reasoning as E12b).

**Candidate-pair prefilter** (deterministic, cheap — bounds the expensive judgment step to plausibly-related tags instead of every O(n²) pair of vault-wide tags). Reuses E9a/E9b's existing `E9_MIN_FILES` (3) floor, then applies the source-overlap + common-neighbor signals from #119's D10 design note:

```
tag_files = {}                                        # lowercase tag → set(file paths)
for rec in frontmatter_records:
  for t in (rec.fm.tags or []):
    tag_files[lower(t)].add(rec.path)

frequent_tags = {t for t in tag_files if len(tag_files[t]) >= E9_MIN_FILES}

tag_neighbors = {}                                    # tag → set(co-occurring tags), precomputed once outside the pair loop
for rec in frontmatter_records:
  for t in (rec.fm.tags or []):
    tag_neighbors.setdefault(t, set()).update(rec.fm.tags)
for t in tag_neighbors:
  tag_neighbors[t].discard(t)

for (A, B) in unordered_pairs(frequent_tags):
  if already_reported_as_E9a(A, B):                   # lookup against vocabulary_pairs[] (SCAN's detect-vocabulary, E9a sub)
    continue                                          # regular plural — deterministic, no LLM needed
  co_occurs = any(A in rec.fm.tags and B in rec.fm.tags for rec in frontmatter_records)
  common_neighbor = bool(tag_neighbors.get(A, set()) & tag_neighbors.get(B, set()))
  if co_occurs or common_neighbor:
    candidate_pairs.append((A, B))
```

**LLM judgment**: for each candidate pair, judge from the tag strings and file counts alone (no file body reads) whether they name the **same concept** under two different spellings/phrasings — a true synonym — as opposed to two related-but-distinct concepts that merely tend to co-occur (e.g. a language and a tool commonly used with it).

**FP guard — mandatory user-confirm gate**: every pair the judgment step flags is a *candidate*, never reported directly. `AskUserQuestion` confirms each candidate pair individually (one question per pair, batched ≤4 per call — mirrors E12b's confirm gate exactly); only confirmed pairs become findings. There is no `fp_on_clean == 0` contract for E9c (it is explicitly out of `--dod` scope, see below), so this confirm gate is the FP-mitigation mechanism, same as E12b.

**Finding shape**: folded into the SAME `tag_vocabulary_inconsistency` bucket E9a/E9b already populate — no new error type, renders under the existing E9 vault-wide heading in REPORT:

```
{"error_type": "tag_vocabulary_inconsistency", "severity": "Warning", "priority": "P2",
 "path": "", "detail": "<reason>", "auto_fix_eligible": false}
```

**Out of `--dod` scope**: `--dod` (`obsidian-vault-manager/scripts/test/assert-dod.py`) measures `audit-validate.py`'s deterministic detection against seeded fixtures (`seeded_detected`, `fp_on_clean`). E9c has no reference-impl function to measure and cannot be seeded/detected deterministically (its output depends on live LLM judgment), so it is not a `--dod` target and never will be — `dod.seeded_detected.E9` stays scoped to E9a/E9b pairs exactly as it was before #167. Acceptance for E9c instead is a fixture demonstration: see `obsidian-vault-manager/scripts/test/fixtures/e9c-deep-demo/`.

**Never auto-fixed**: like E9a/E9b, picking the canonical form is the user's decision — display-only, same as every other E9 finding.

## E10 — `misplaced_file` [Warning]

**Rule**: A file's `type` does not match the canonical folder it lives in (v4 §3.1). Each managed type belongs in exactly one top-level folder:

```python
EXPECTED_FOLDER = {
    "session": "sources", "capture": "sources",
    "note": "notes", "decision": "notes", "plan": "notes",
    "wiki": "wiki",   # v5 §3 — A-layer LLM wiki; a type:wiki file outside wiki/ is misplaced
}
```

**Source**: `frontmatter_records` (uses `fm.type` + top-level folder of the path).
**Guard**:
- Files already flagged E1/E2 are **skipped** — no reliable `type` to check until integrity is fixed.
- `assets/` files are exempt (attachments carry no managed type).
- Hidden top folders (`.obsidian/`, `.vault-bridge/`, `.ovm/`) are exempt.
- Root-direct files and files in non-canonical folders are **out of scope** — those are E11's domain (type↔folder is only meaningful inside canonical folders).
- `type` not in `EXPECTED_FOLDER` (e.g., unknown type) → skip (no expectation to compare against).

**Detection pseudocode**:

```
for each record in frontmatter_records:
  if record in E1/E2 findings: skip
  top = path.parts[0]
  if top startswith "." or top == "assets": skip
  if path is root-direct or top not in {sources,notes,assets,wiki}: skip   # E11 owns these
  type = fm.type ; if type not str: skip
  expected = EXPECTED_FOLDER.get(type) ; if expected is None: skip
  if top != expected: → misplaced_file
```

**Rationale**: A `type: session` note in `notes/` (or a `type: note` in `sources/`) breaks the folder-as-routing contract. Moving the file affects inbound wikilinks, so this is a **display-only** P1 warning — never auto-moved.

## E11 — `unstructured_path` [Warning]

**Rule**: A `.md` file lives outside the canonical top-level folders (v4 §3.1; v5 §3 adds `wiki/`). Only `sources/`, `notes/`, `assets/`, `wiki/` are canonical; anything else (arbitrary folders, root-direct files) is structural drift.

```python
CANONICAL_FOLDERS = {"sources", "notes", "assets", "wiki"}  # v5 §3 adds wiki/ (A layer)
EXEMPT_FILES = {"_index.md"}
```

**Source**: `frontmatter_records` (uses the path only; `collect()` already excludes hidden directories).
**Guard**:
- `_index.md` (any location) is exempt — vault/folder index files legitimately live at the root or any folder root.
- Hidden top folders (`.obsidian/`, `.vault-bridge/`, `.ovm/`) are exempt (already excluded by `collect()`; the classifier re-checks `top.startswith(".")` defensively).
- Root-direct files (`"/" not in path`) are **included** — a stray `.md` at the vault root is unstructured.

**Detection pseudocode**:

```
for each record in frontmatter_records:
  if path.name in EXEMPT_FILES: skip               # _index.md
  if path is root-direct ("/" not in path): → unstructured_path
  top = path.parts[0]
  if top startswith ".": skip                       # hidden dir
  if top in CANONICAL_FOLDERS: skip                 # sources/notes/assets OK
  → unstructured_path
```

**Rationale**: Files outside the three-folder layout are invisible to folder-based routing and accumulate untracked. Moving them affects inbound wikilinks, so this is a **display-only** P1 warning — the user decides where they belong. The `_index.md` exempt guard is regression-covered: the test fixture seeds a root-level `_index.md` into the clean area and asserts `fp_on_clean.E11 == 0`.

## E12 — `wiki_self_audit` [Warning]

**Rule**: The `wiki/` A-layer (LLM-compiled domain knowledge, v5 §7 U3) needs its own freshness/consistency defense — Karpathy's LLM-wiki research names *staleness* as the primary cause of wiki abandonment, so without a mechanical lint the "review delegated to AI" delegation has nothing guarding it. The rule splits into a **deterministic half** (E12a staleness + companion + E12c near-dup, all shipping in `audit-validate.py`) and a **non-deterministic half** (E12b contradiction, deferred `--deep`) — the exact split E9 already makes between its shipping sub-checks and the deferred E9c:

| Sub-check | What it catches | Determinism | Status |
|-----------|-----------------|-------------|--------|
| **E12a** wiki staleness | a wiki page whose `verified:` age exceeds `STALE_WIKI_DAYS` (90) | deterministic — date arithmetic only | **SHIPS** (`E12_wiki_stale`, `audit-validate.py`) |
| **E12a companion** wiki unverified (#494) | a wiki page whose `verified:` is missing or unparseable — staleness is uncomputable, not confirmed fresh | deterministic — presence/parse check only | **SHIPS** (`E12_wiki_unverified`, `audit-validate.py`) |
| **E12b** cross-page contradiction | two wiki pages asserting conflicting claims | **non-deterministic** — needs semantic LLM judgment | **SHIPS** (#336) as a skill-only `--deep` LLM opt-in (`wiki_contradiction`, mirrors E9c) |
| **E12c** near-duplicate (#698, #645 F1) | two wiki pages with the exact same `tags` set and an overlapping title token — e.g. `defuddle.md` vs `defuddle-cli.md` | deterministic — set/string ops only | **SHIPS** (`E12_wiki_near_dup`, `audit-validate.py`) |

**Why the split, not one rule**: the audit is a deterministic reference impl (`audit-validate.py` runs with LLM cost 0). Cross-page *semantic* contradiction cannot be decided by a mechanical rule — a keyword/regex proxy would only manufacture false positives against the audit's `fp_on_clean == 0` contract. Rather than fake determinism, E12b follows the E9c precedent: it never touches `audit-validate.py` or the `--dod` gate (both stay deterministic-only, unmodified by #336). Instead the LLM judgment lives entirely in `audit/SKILL.md` Phase 2.5 stub, full procedure in `reference/audit-deep.md`, gated behind explicit `--deep` opt-in and a mandatory `AskUserQuestion` confirm step for false-positive mitigation. E12a — staleness — remains the honest deterministic slice `audit-validate.py` ships and is DoD-measured. This resolves the G23-S1 design fork ("deterministic audit vs. semantic contradiction detection") the same way #167 intends to resolve it for E9 (E9c itself remains unimplemented/open). E12c near-dup (below) is a LATER addition to the same deterministic half — unlike E12b, matching on `tags`/filename needs no LLM judgment at all, so it never had a reason to defer to `--deep`.

### E12b — cross-page contradiction (`--deep`, skill-only, #336)

**Where it lives**: `audit/SKILL.md` Phase 2.5 stub, full procedure in `reference/audit-deep.md` DEEP, not `audit-validate.py`. There is no reference-impl function for E12b and none is planned — the judgment step needs an LLM reading page bodies, which the deterministic reference impl structurally cannot do.

**Candidate-pair prefilter** (deterministic, cheap — bounds the expensive judgment step instead of comparing every wiki page against every other):

```
wiki_pages = [r for r in frontmatter_records if r.path.parts[0] == "wiki" and r.fm.type == "wiki"]
for (A, B) in unordered_pairs(wiki_pages):
  shared_tags = set(lower(t) for t in A.fm.tags) & set(lower(t) for t in B.fm.tags)
  # inbound_links: target_stem -> [source_paths] (same index E5 uses, #482 removed
  # the per-file wikilinks_by_file that used to serve this — E4 was its only consumer).
  links = B.path in inbound_links.get(stem(A.path), []) or A.path in inbound_links.get(stem(B.path), [])
  if shared_tags or links:
    candidate_pairs.append((A, B))
```

**LLM judgment**: for each candidate pair, Read both bodies and judge whether they assert conflicting claims about the same subject (a fact/number/decision/status that cannot both be true). Complementary information, different scopes, or stylistic differences are not a contradiction.

**FP guard — mandatory user-confirm gate**: every pair the judgment step flags is a *candidate*, never reported directly. A single `AskUserQuestion` lists all candidates from the run and asks the user to confirm each as a real contradiction or dismiss it; only confirmed pairs become findings. This is the FP-mitigation mechanism for a check that is inherently non-deterministic — there is no `fp_on_clean == 0` contract for E12b (it is explicitly out of `--dod` scope, see below), so the confirm gate is what keeps it from spamming false positives instead of a fixed threshold.

**Finding shape**: pair-level, like E9. `path` is a synthetic `"wiki/a.md ↔ wiki/b.md"` string (not empty — REPORT's generic path+detail bullet rendering already handles any non-empty path, no REPORT-phase code change needed):

```
{"error_type": "wiki_contradiction", "severity": "Warning", "priority": "P1",
 "path": "wiki/a.md ↔ wiki/b.md", "detail": "<reason>", "auto_fix_eligible": false}
```

**Out of `--dod` scope**: `--dod` (`obsidian-vault-manager/scripts/test/assert-dod.py`) measures `audit-validate.py`'s deterministic detection against seeded fixtures (`seeded_detected`, `fp_on_clean`). E12b has no reference-impl function to measure and cannot be seeded/detected deterministically (its output depends on live LLM judgment), so it is not a `--dod` target and never will be — that gate stays scoped to E1–E11 + E12a exactly as it was before #336. Acceptance for E12b instead is a fixture demonstration: see `obsidian-vault-manager/scripts/test/fixtures/e12b-deep-demo/`.

**Never auto-fixed**: like E12a, recompiling/reconciling a genuine contradiction is a semantic decision — display-only, same as every other E12 finding.

```python
STALE_WIKI_DAYS = 90   # `verified:` is auto-stamped on every wiki write (v5 §4.1) —
                       # a last-touched signal, NOT active verification.
```

**Source**: `frontmatter_records` (uses path + `type` + `verified` only).
**Scope guard** (`detect_stale_wiki` / `detect_unverifiable_wiki` share the same `_wiki_pages` filter): flags a page **only** when its top folder is `wiki/` AND `type: wiki` — a stray old/missing `verified:` on a non-wiki file is never an E12. A page with a missing or unparseable `verified:` is **skipped by `detect_stale_wiki`** (staleness is uncomputable without it) but **not dropped** — it is reported by the E12a companion `E12_wiki_unverified` instead (#494), so a page the write-time auto-stamp (v5 §4.1) never touched — every `wiki/` page compiled before that landed — does not go permanently invisible to the audit.

**Detection pseudocode**:

```
for each record in frontmatter_records:
  if path.parts[0] != "wiki": skip          # wiki/-scoped
  if fm.type != "wiki": skip                # type:wiki only
  verified = parse_date(fm.verified)
  if verified is None:                      # missing/unparseable → uncomputable
    → wiki_unverified                       # E12a companion (#494), NOT skipped
    continue
  if (today - verified).days > STALE_WIKI_DAYS: → wiki_stale
```

**Why not fall back to `created:`**: the issue this shipped against (#494) considered defaulting staleness age to `fm.created` when `verified` is absent. Rejected — `created` is the page's authoring date, not its last-touched date; treating it as a staleness proxy conflates the two and can UNDERSTATE the age of a page that was genuinely re-verified since creation but never re-stamped (pre-v5-§4.1 cohort). Reporting "verified 판정 불가" instead of a guessed age keeps the finding honest about what is actually known.

**Rationale**: A stale wiki page is a **display-only** P1 warning (staleness = 정체, same tier as E6) — the next action (recompile / re-verify) is a semantic decision, never auto-fixed. `E12_wiki_unverified` carries the same P1/display-only treatment, for a different reason: the page's freshness is simply unknown. Regression-covered by the DoD fixture (5 seeded `wiki/` pages with `verified: 2020-01-01` → `seeded_detected.E12_wiki_stale == 5`; 2 seeded `wiki/` pages with missing/unparseable `verified:` → `seeded_detected.E12_wiki_unverified == 2`; 2 fresh pages stamped with the run date → `fp_on_clean == 0` for both types, date-independent) plus a scoping unit test (`test-wiki-self-audit.py`).

### E12c — near-duplicate wiki pages (#698, #645 F1 follow-up)

**Rule**: two `wiki/` pages with the exact same `tags` set and overlapping title tokens (filename slug, split on `-`/`_`, numeric-only segments dropped) are flagged as a candidate near-duplicate — e.g. `defuddle.md` vs `defuddle-cli.md` under the same domain tag, the exact multi-slug miss `wiki/SKILL.md`'s DEDUP step cites (a manifest exit-3 — absent/unparseable/malformed — degrades DEDUP to slug-only matching, which cannot catch a different-slug duplicate). Deterministic — SHIPS in `audit-validate.py` (`detect_wiki_near_dup`, `E12_wiki_near_dup`) and `scan-summary.py` (`E12_near_dup`), same LLM-0 tier as E12a. **No `--deep` component** — there is no non-deterministic half to defer, unlike E12b's semantic contradiction judgment.

**Manifest-free by design (#645 §4 F1)**: this check reads only `frontmatter_records` (`ovm-primitives.sh scan-frontmatter`'s direct corpus scan — path + full frontmatter per file), the same source E12a already uses. It does **not** call `manifest-wiki-match.py` (vault-bridge, moved there by #645) — doing so would create a new OVM→vault-bridge script dependency, which E12 has never had and does not need one to add now. E12 stays self-contained inside OVM, same as every other audit rule.

**Why exact tag match, not "any shared tag"**: every wiki page's `tags` always include the literal `wiki` type tag (v5 §4.1 `tags: [{type}, {domain}]`), so "any overlap" would trivially match every wiki page against every other one. Exact tag-set equality also gives the check most of its precision for free — two pages on genuinely different domains rarely carry identical tag sets, whereas two pages about the SAME domain compiled under different slugs usually do.

**Source**: `frontmatter_records` (uses path + `type` + `tags` only), same `_wiki_pages` wiki/+type:wiki scope guard as E12a/companion.

**Detection pseudocode**:

```
wiki_pages = [(rel, fm) for rel, fm in _wiki_pages(frontmatter_records)]
for (A, B) in unordered_pairs(wiki_pages):
  tags_a, tags_b = tag_set(A.fm), tag_set(B.fm)          # lowercased, deduped
  if not tags_a or tags_a != tags_b: skip
  shared_tokens = title_tokens(A.rel) & title_tokens(B.rel)   # numeric-only dropped
  if not shared_tokens: skip
  → wiki_near_dup(min(A.rel, B.rel), max(A.rel, B.rel), shared_tags=tags_a, shared_tokens=shared_tokens)
```

**Finding shape**: pair-level, like E9/E12b, but — unlike E9's path-less `""` — carries a real `path` (the lexicographically-first of the pair) plus `other_path` for the second, so REPORT's generic per-file bullet rendering needs no special case:

```
{"error_type": "wiki_near_dup", "severity": "Warning", "priority": "P1",
 "path": "wiki/defuddle-cli.md", "other_path": "wiki/defuddle.md",
 "detail": "<shared tags + tokens>", "auto_fix_eligible": false}
```

**Never auto-fixed**: merging two near-duplicate pages is a semantic decision (which one is canonical, what to keep from each) — display-only, same as every other E12 finding.

**Rationale**: wiki duplicates accumulate when `/wiki` DEDUP degrades to slug-only matching on a manifest exit-3 — #645 §4 F1 follow-up, independent of the `/wiki` deployment-unit migration itself (that migration *lowers* the exit-3 rate by co-locating `/wiki` with the manifest-generating hook, but does not eliminate the existing debt; F1 is deliberately NOT bundled with the migration PR so a one-line rollback of the migration stays possible — #645 §4). Regression-covered by the DoD fixture (1 seeded near-dup pair under a `dup-fixture` tag distinct from every other wiki seed group above, so it never exact-tag-matches them → `seeded_detected.E12_wiki_near_dup == 1`; `fp_on_clean.E12_wiki_near_dup == 0`, guarded by giving every other wiki seed group its own per-file tag suffix so this fixture's shared `audit-e12-*` filename convention never manufactures an accidental cross-group match) plus a scoping/matching unit test (`test-wiki-near-dup.py`).

## Auto-fix eligibility

Only the following are mutated by Phase 4 OPTIONAL-FIX (frontmatter-only edits):

| Type | Auto-fix action |
|------|-----------------|
| `missing_required_fields` (E2) | Add missing `tags`, `type`, `created` fields. For `tags:`, propose a deterministic 3-tier inference (type → filename slug → first segment under `notes/`; see the E2 **Tag inference** section above) — never an empty `tags: []` — and preview it in the confirmation gate before applying. `provenance` (#477 item 4) is required but NOT auto-fillable — unlike `tags`, there is no safe deterministic inference for "where did this come from." When it's among the missing fields, surface it in the confirmation gate per-file and ask the user for the actual origin instead of writing a placeholder. |

Never auto-fixed: E1 (body structure unknown), E3 (rename affects inbound links — suggestion only), E5 (content value judgment — connection candidates are suggestions only), E6 (stagnation requires semantic decision: process / archive), E9 (canonical-form choice + multi-file rewrite is the user's decision — display-only), E10/E11 (moving a file affects inbound links — display-only warning, user decides the destination), E12 (recompiling/re-verifying a stale wiki page, reconciling a confirmed E12b contradiction, or merging a confirmed E12c near-duplicate pair, is a semantic decision — display-only warning).

## Manifest Summary (display-only)

The audit REPORT header shows manifest metadata when `.vault-bridge/manifest.json` exists at the vault root:

- `file_count` — number of files indexed by vault-bridge
- `generated_at` — ISO timestamp of last manifest refresh

Absence is non-fatal: the header shows `매니페스트: 없음 (vault-bridge 미설치)`. No finding is emitted for missing or stale manifest.

### Reading the manifest — never `cat` it (#468, #460)

**Canonical text (#663).** `audit/SKILL.md` Phase 1 Step 8 points here; this section is the
binding contract, not background, and must be applied as written (the body keeps the call plus a
locator). Its whole text — heading to the next heading, so nothing unpinned may be parked at the
bottom — is pinned VERBATIM by `_READING_MANIFEST_SECTION` in
`obsidian-vault-manager/scripts/test/test-manifest-reads.py`, and the headings on either side are
pinned by identity so an inserted sibling cannot park contradicting text just outside it. Editing
anything below is a deliberate contract change and updates that constant in the same commit; a
reflow is free (the comparison is whitespace-normalised).

**Never `cat` the manifest directly.** It can run past 100 KB, and the harness truncates large
Bash output to a 2 KB preview, so a raw `cat` silently degrades to whichever entries survive the
cut — indistinguishable from a legitimately small manifest. Use the filter script instead, which
reads the full file on disk and returns only the two fields the REPORT header needs:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/.vault-bridge/manifest.json"
```

- **Exit 0** → parse stdout as `{file_count, generated_at}` and use it as `manifest_summary`.
- **Exit 3** (manifest absent, unparseable, or missing a required field) → set `manifest_summary`
  to null, and **never re-attempt with a raw `cat` as a fallback**. A truncated read is worse than
  no read: the header would print a confident wrong count instead of `없음`.

---

## REPORT output example

The `audit` skill's Phase 3 layout, moved here (#447) to keep SKILL.md inside the 5,000-token
window auto-compaction re-attaches. Illustration only — actual content varies by vault state.

**Example** (representative — actual content varies by vault state):

```
볼트 감사 완료
──────────────────────────────────────────
볼트 상태: 42 노트 / clean 38 · dirty 3 · untracked 1
발견된 이슈: 3건 (P0 2건 · P1 1건)
──────────────────────────────────────────

[P0 / Critical] missing_frontmatter — 1건
  • notes/scratch.md
      상세: frontmatter 없음

[P0 / Warning] filename_convention_violation — 1건
  • notes/2026-04-old-topic.md
      상세: v3 날짜 우선 파일명 — {type}-YYYY-MM-DD-{slug}.md 또는 {slug}.md로 변경 필요

[P1 / Warning] stale_inbox — 1건
  • sources/capture-2026-03-15-old-topic.md
      상세: age 73d > 14d (status:raw, created 2026-03-15)

──────────────────────────────────────────
자동 수정 가능: 0건
수동 처리 필요: 3건
```

> **git 활동 줄**: `commits == 0`이거나 vault가 git 저장소가 아닌 경우 해당 줄을 출력하지 않습니다.
- The 7-day window can be overridden via `VAULT_AUDIT_ACTIVITY_DAYS` env var.

---

## E2 tag inference

The tier rules behind `ovm-primitives.sh infer-tags`, moved out of `audit/SKILL.md` (#447) to
keep it inside the 5,000-token compaction window. The skill keeps the rule and the batched
call; this is the derivation.

**Tag inference** (#127, deterministic — no LLM; batched #152): when `tags:` is
missing, do NOT insert an empty `tags: []`. Instead derive a tag PROPOSAL from
three tiers via a SINGLE batched call
`ovm-primitives.sh infer-tags <relpath1> <relpath2> ...` (one Python process for
all E2 findings, not one per finding). The call emits a JSON array — one element
per path — with order preserved, duplicates dropped, all lowercased so the result
plausibly passes a future E9 vocabulary check:

| Tier | Source | Rule |
|------|--------|------|
| 1 | `type:` field | always the first tag (`type: note` → `note`) |
| 2 | filename slug | words after stripping the date + `{type}-` prefix, split on `-`/`_` |
| 3 | first segment under `notes/` | `notes/{segment}/...` → add `segment` (`rel.parts[1]`, not the literal parent folder — see the E2 Tag inference section above) |

Examples: `notes/llm/decision-2026-04-12-context-window.md` (`type: decision`)
→ `[decision, context, window, llm]`; `sources/capture-2026-05-01-obsidian-api.md`
(`type: capture`) → `[capture, obsidian, api]`. Empty slug (date-only filename,
e.g. `session-2026-04-12.md`) gracefully falls back to the type tag only.
The proposal is never auto-committed — `audit/SKILL.md` Phase 4 previews it in the
OPTIONAL-FIX confirmation gate.

---

## SCAN output budget and the reduced bundle (#614)

Why Phase 1 writes its scans to files and reads back a summary instead of printing
them: the harness truncates Bash output to a ~2 KB preview before the model sees
anything. `scan-frontmatter` + `scan-filename` measured 148,669 B + 50,077 B on a
real 193-file vault, and 174,973 B + 115,692 B on the 528-file fixture — so roughly
0.7% of the source data for E1/E2/E3/E5/E6/E10/E11/E12 survived, with nothing marking
the cut. A vault whose defects fell past the line read as a nearly-clean one. This is
the same failure #468/#460 fixed for `manifest.json`'s raw `cat`, at a worse scale.

`scan-summary.py` reads the scans off disk untruncated and keeps only defect-bearing
records with only the fields each judgment consumes; clean files carry no information
for the REPORT and were the 480-of-528 majority that blew the budget. 290,665 B
becomes ~1.5 KB.

`--max-per-type` defaults to 2 because nine error types share the one preview:
1,536 B at a cap of 2, 2,046 B at 3 (two bytes under the limit, which is not a
margin), 2,935 B at 4. A capped list always carries `omitted: N`, and `count` is
always the full number found, so the cut is legible twice over. The tail is not
lost — re-run with a larger cap into a file and open it with `Read`, which paginates
where Bash stdout truncates.

`extract-wikilinks-batch` exists for the same reason plus speed: the old per-file
`extract-wikilinks` loop cost 528 Bash round trips and one Python start each,
measured at ~110 s on the 528-file fixture against 0.14 s for the single dir-shaped
call. It is #152's `infer-tags` batching applied to the last per-file loop, and it
returns the finished `{target_stem → [source_paths]}` index rather than per-file
records so the model never assembles the index by hand.

A file `scan-frontmatter` cannot read at all (permission denied, decode error) goes into
`scan_summary.errors.unreadable` — `{path, error}` — instead of any content-based type.
CLASSIFY renders it Critical/P0, sorted ahead of E1 (see the Priority Mapping table above):
"we could not look" outranks any judgment made on content that was actually read. It is
excluded from E1/E3/E5/E6/E10/E11/E12's own record lists so the same file is never
double-reported as both `unreadable` and a finding about content nobody examined.
