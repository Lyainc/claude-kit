# vault-audit — Error Type Detection Rules

Detection rules for the `audit` skill's CLASSIFY phase. The skill body (`skills/audit/SKILL.md`) summarizes these as a table; this file is the canonical pseudocode reference.

Eleven error types cover v4's three-folder vault layout (`inbox/`, `notes/`, `assets/`). Severity buckets: **Critical** (data integrity risk), **Warning** (quality / navigation risk), **Info** (style / convention).

> **v4 history**: Legacy E6–E9 (project-binding checks) were removed in v4 because `20_Projects/` is no longer part of the layout. The codes were later reused — PR 5 (`/audit` Phase 2) introduces a new **E6 `stale_inbox`** and **E7 `stale_draft`** covering v4 §6.1 Step 2 "정체" (stagnation). PR 4 had added P0–P2 priority mapping and display-only manifest summary; PR 5 extends with P1 stagnation. PR 4d adds **E8 `promotion_candidate`** (P2/Info), read from the vault-bridge manifest. Manifest-level *stale-manifest* checks (e.g., stale manifest as an Info finding) remain deferred to PR 6+.

## Priority Mapping

Every finding carries a `priority` field independent of severity. Priority drives REPORT grouping; severity drives semantic labeling.

| Code | Priority | Rationale |
|------|----------|-----------|
| E1   | P0       | Frontmatter absent → file is invisible to type opt-in (v4 §2.2); blocks all downstream tooling. |
| E2   | P0       | Required fields missing → status machine and type routing break. |
| E3   | P0       | v3-style filename → convention violation that blocks future automated routing. |
| E4   | P0       | Broken wikilink → navigation hazard with Critical severity (data graph integrity). |
| E5   | P2       | Orphan note → quality signal, not integrity risk. |
| E6   | P1       | Stale inbox → raw input never processed; loses freshness, signals review needed. |
| E7   | P1       | Stale draft → notes/ `status: draft` sitting too long; either promote to evergreen or archive. |
| E8   | P2       | Promotion candidate → high inbound refs or access count; suggests manual `status: evergreen`. Manifest-sourced, never auto-fixed. |
| E9   | P2       | Tag/property vocabulary inconsistency → a vault-wide style signal (kepano "consistent style"), never an integrity defect. Canonical-form choice is always the user's call → no auto-fix. E9a/E9b are deterministic; E9c semantic synonym ships as the skill-only `--deep` LLM opt-in (#167, see the `## E9` section below). |
| E10  | P1       | Misplaced file → `type` lives in the wrong canonical folder; moving affects inbound links (display-only warning). |
| E11  | P1       | Unstructured path → file outside `inbox/notes/assets`; structural drift, moving affects inbound links (display-only warning). |
| E12  | P1       | Wiki self-audit (v5 §7 U3) → a `wiki/` page whose `verified:` age exceeds `STALE_WIKI_DAYS`; staleness is the abandonment risk for the LLM wiki. E12a (staleness) is display-only; E12b cross-page semantic contradiction ships as the skill-only `--deep` LLM opt-in (#336, see the `## E12 — wiki_self_audit` section below). |

> **P0 = 무결성 (integrity)**: All four E1–E4 types are in v4 §6.1 Step 1 "무결성", which outputs P0 items first and gates OPTIONAL-FIX on user confirmation.
> **P1 = 정체/구조 (stagnation / structure)**: E6 and E7 surface unprocessed inputs and stalled drafts; E10 and E11 surface folder-structure drift; E12 surfaces stale wiki pages. All are visible signal only, never auto-fixed (each requires a semantic decision: process / promote / archive / move / recompile).
> **P2 = quality**: E5 orphan notes, E8 promotion candidates, and E9 vocabulary inconsistencies are quality signals, not integrity defects.

> **Code numbering**: E9 (#119, #167) is the tag/property vocabulary check below. Its deterministic sub-checks (E9a singular/plural, E9b camel/snake property naming) ship in `audit-validate.py`; E9c (semantic synonyms) ships as a skill-only `--deep` LLM opt-in in `audit/SKILL.md` Phase 2.5 (see the E9 section). E10/E11 are the structural checks per #128/#129. E12 (#330, #336) is the wiki self-audit: E12a staleness ships deterministically in `audit-validate.py`; E12b cross-page contradiction ships as a skill-only `--deep` LLM opt-in in `audit/SKILL.md` Phase 2.5 — the same deterministic/semantic split E9 draws around E9c, and both now ship behind the same `--deep` flag.

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
| All types (universal) | `created`, `tags`, `type` |
| `type: note` and `type: decision` only | `status` (v4 §3.3 status machine) |

`status` is optional for `capture`, `session`, and `plan` — omitting it for those types is not an E2 violation.

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
| 3 | parent folder | only inside `notes/{domain}/...` (path depth ≥ 3) → add `domain`. The vault-root folder name itself (`notes`) is structural, not a domain. |

```
infer_tags(rel, fm):
  tags = []
  push(fm.type)                         # tier 1 (skipped if type absent)
  slug = strip_date_and_type_prefix(rel.name)
  for word in split(slug, /[-_]+/): push(word)   # tier 2
  if rel.parts[0] == "notes" and len(rel.parts) >= 3:
    push(rel.parts[1])                  # tier 3 domain
  return tags                           # push() lowercases, dedups, drops stopwords/digits
```

**Examples**:
- `notes/llm/decision-2026-04-12-context-window.md`, `type: decision` → `[decision, context, window, llm]`
- `inbox/capture-2026-05-01-obsidian-api.md`, `type: capture` → `[capture, obsidian, api]`

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
| `inbox/` | Exempt — raw input zone; any filename accepted | — |
| `assets/` | Exempt — attachments; any filename accepted | — |

**Guard**: `_index.md` is always valid (skip). Files in `inbox/` and `assets/` are exempt.

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

## E4 — `broken_wikilink` [Critical]

**Rule**: For each `[[target]]` in a file — look up `target` stem in the vault file set. If no file exists with that stem (case-insensitive match), it is broken.
**Source**: `wikilinks_by_file`, global file index.
**Guard**: Ignore embed links `![[image.png]]` where target has a non-`.md` extension or no extension at all and a matching file exists in assets. Ignore links to headings / blocks within a found note.

## E5 — `orphan_note` [Warning]

**Rule**: A `.md` file in `notes/` (any depth) has zero entries in `inbound_links[stem]`.
**Source**: `inbound_links` (built from full vault scan).
**Guard**: `_index.md` files are never orphans. Files in `inbox/` are exempt (unprocessed captures). Files in `assets/` are exempt.

**Connection candidates** (#130, display-only): for each orphan, compute the top-3
`notes/` files sharing the most tags (exact-match intersection only — no semantic
synonyms). Build a `notes/` tag index once before the orphan loop to avoid O(N²).

```
notes_tag_index = [(rel, frozenset(tags)) for rel in notes/ if rel != _index.md]

for each orphan P:
  orphan_tags = frozenset(P.tags)            # [] when tags empty
  scored = [(len(orphan_tags & Q.tags), Q.rel, sorted(shared))
            for Q in notes_tag_index if Q != P and (orphan_tags & Q.tags)]
  scored.sort by (shared desc, path asc)
  candidates = scored[:3]                     # [{path, shared_tags}]
```

The finding carries a **structured** `candidates: [{path, shared_tags}]` field
(REPORT renders the `연결 후보` line from it) AND a rendered `detail`:

- with candidates: `연결 후보: [[X]] (공유 태그: a, b); [[Y]] (공유 태그: a)`
- no shared tags / empty tags: `연결 후보 없음 (공유 태그 없음)`, `candidates: []`

Empty-tags orphans are handled gracefully (no candidate computation, no error).
Linking position is the user's decision — the audit only suggests candidates.

## E6 — `stale_inbox` [Warning]

**Rule**: A file in `inbox/` is still "raw" and its `created:` date is more than `STALE_INBOX_DAYS` (= 14) days before today.
**Source**: `frontmatter_records` (uses `fm.created` + `fm.status`).
**Guard**: Files with explicit non-raw status (e.g., `type: session` + `status: active`, or any other processed marker) are exempt. Files without a parseable `created:` field are skipped (no false positive on malformed frontmatter — E1/E2 catch those separately).

**Detection pseudocode**:

```
for each record in frontmatter_records where path startswith "inbox/":
  status = normalize(fm.status)            # non-string or missing → ""
  if status not in {"", "raw"}: skip       # explicit non-raw → exempt
  if parse(fm.created) is None: skip       # malformed → E1/E2 territory
  age_days = today - parse(fm.created)
  if age_days > STALE_INBOX_DAYS: → stale_inbox
```

**Rationale**: Captures (and any unprocessed inbox file) accumulate freshness debt — review and either promote to `notes/` or delete. `type: session` notes carry `status: active`/`closed` and are skipped, so historical session records don't pollute the stagnation report.

## E7 — `stale_draft` [Warning]

**Rule**: A file in `notes/` has `status: draft` and its `created:` date is more than `STALE_DRAFT_DAYS` (= 30) days before today.
**Source**: `frontmatter_records` (uses `fm.created` + `fm.status`).
**Guard**: Only `status: draft` triggers — `evergreen`, `archived`, `raw` (with the `note` type) are out of scope.

**Detection pseudocode**:

```
for each record in frontmatter_records where path startswith "notes/":
  if fm.status != "draft": skip
  if parse(fm.created) is None: skip
  age_days = today - parse(fm.created)
  if age_days > STALE_DRAFT_DAYS: → stale_draft
```

**Rationale**: A draft sitting beyond a month signals a decision is needed — promote to `evergreen`, move to `archived`, or delete. The audit surfaces them; the user decides.

## E8 — `promotion_candidate` [Info]

**Rule**: A note flagged `promotion_candidate: true` in the vault-bridge manifest (`schema_version ≥ 3`). The flag is computed by `vault-bridge/scripts/generate-manifest.py` (PR 4c), **not** by the audit CLASSIFY phase — audit consumes it as a read-side signal (no detection pseudocode here).
**Source**: `manifest.json` `files[]` entries where `promotion_candidate == true` — `type: note`/`decision` via `references_in ≥ VAULT_AUDIT_PROMOTION_REFS` (3) OR `access_count ≥ VAULT_AUDIT_PROMOTION_ACCESS` (5); `type: capture` via `access_count` alone (Model X — inbox ore rarely gets wikilinked in, so `references_in` isn't a fair signal there).
**Guard**: Absent or `schema_version < 3` manifest → no E8 findings (graceful skip). Manifest entries whose underlying files were deleted are skipped (phantom guard).

**Rationale**: A note with high inbound references or frequent access is a candidate for manual promotion to `status: evergreen`. A recalled `capture` has no `status` field to flip (v4 §3.3 — capture can never become evergreen directly); its finding instead points at `/note` or `/wiki` to promote. Surfaced as Info/P2 — the user decides; never auto-fixed.

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

**Where it lives**: `audit/SKILL.md` Phase 2.5, not `audit-validate.py`. There is no reference-impl function for E9c and none is planned — the judgment step needs LLM semantic reasoning over tag strings, which the deterministic reference impl structurally cannot do (same reasoning as E12b).

**Candidate-pair prefilter** (deterministic, cheap — bounds the expensive judgment step to plausibly-related tags instead of every O(n²) pair of vault-wide tags). Reuses E9a/E9b's existing `E9_MIN_FILES` (3) floor, then applies the source-overlap + common-neighbor signals from #119's D10 design note:

```
tag_files = {}                                        # lowercase tag → set(file paths)
for rec in frontmatter_records:
  for t in (rec.fm.tags or []):
    tag_files[lower(t)].add(rec.path)

frequent_tags = {t for t in tag_files if len(tag_files[t]) >= E9_MIN_FILES}

for (A, B) in unordered_pairs(frequent_tags):
  if already_reported_as_E9a(A, B):
    continue                                          # regular plural — deterministic, no LLM needed
  co_occurs = any(A in rec.fm.tags and B in rec.fm.tags for rec in frontmatter_records)
  neighbors_A = {t for rec in frontmatter_records if A in rec.fm.tags for t in rec.fm.tags} - {A}
  neighbors_B = {t for rec in frontmatter_records if B in rec.fm.tags for t in rec.fm.tags} - {B}
  common_neighbor = bool(neighbors_A & neighbors_B)
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
    "session": "inbox", "capture": "inbox",
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
  if path is root-direct or top not in {inbox,notes,assets,wiki}: skip   # E11 owns these
  type = fm.type ; if type not str: skip
  expected = EXPECTED_FOLDER.get(type) ; if expected is None: skip
  if top != expected: → misplaced_file
```

**Rationale**: A `type: session` note in `notes/` (or a `type: note` in `inbox/`) breaks the folder-as-routing contract. Moving the file affects inbound wikilinks, so this is a **display-only** P1 warning — never auto-moved.

## E11 — `unstructured_path` [Warning]

**Rule**: A `.md` file lives outside the canonical top-level folders (v4 §3.1; v5 §3 adds `wiki/`). Only `inbox/`, `notes/`, `assets/`, `wiki/` are canonical; anything else (arbitrary folders, root-direct files) is structural drift.

```python
CANONICAL_FOLDERS = {"inbox", "notes", "assets", "wiki"}  # v5 §3 adds wiki/ (A layer)
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
  if top in CANONICAL_FOLDERS: skip                 # inbox/notes/assets OK
  → unstructured_path
```

**Rationale**: Files outside the three-folder layout are invisible to folder-based routing and accumulate untracked. Moving them affects inbound wikilinks, so this is a **display-only** P1 warning — the user decides where they belong. The `_index.md` exempt guard is regression-covered: the test fixture seeds a root-level `_index.md` into the clean area and asserts `fp_on_clean.E11 == 0`.

## E12 — `wiki_self_audit` [Warning]

**Rule**: The `wiki/` A-layer (LLM-compiled domain knowledge, v5 §7 U3) needs its own freshness/consistency defense — Karpathy's LLM-wiki research names *staleness* as the primary cause of wiki abandonment, so without a mechanical lint the "review delegated to AI" delegation has nothing guarding it. The rule has **two halves, split on the audit's deterministic (LLM-0) boundary** — the exact split E9 already makes between its shipping sub-checks and the deferred E9c:

| Sub-check | What it catches | Determinism | Status |
|-----------|-----------------|-------------|--------|
| **E12a** wiki staleness | a wiki page whose `verified:` age exceeds `STALE_WIKI_DAYS` (90) | deterministic — date arithmetic only | **SHIPS** (`E12_wiki_stale`, `audit-validate.py`) |
| **E12b** cross-page contradiction | two wiki pages asserting conflicting claims | **non-deterministic** — needs semantic LLM judgment | **SHIPS** (#336) as a skill-only `--deep` LLM opt-in (`wiki_contradiction`, mirrors E9c) |

**Why the split, not one rule**: the audit is a deterministic reference impl (`audit-validate.py` runs with LLM cost 0). Cross-page *semantic* contradiction cannot be decided by a mechanical rule — a keyword/regex proxy would only manufacture false positives against the audit's `fp_on_clean == 0` contract. Rather than fake determinism, E12b follows the E9c precedent: it never touches `audit-validate.py` or the `--dod` gate (both stay deterministic-only, unmodified by #336). Instead the LLM judgment lives entirely in `audit/SKILL.md` Phase 2.5, gated behind explicit `--deep` opt-in and a mandatory `AskUserQuestion` confirm step for false-positive mitigation. E12a — staleness — remains the honest deterministic slice `audit-validate.py` ships and is DoD-measured. This resolves the G23-S1 design fork ("deterministic audit vs. semantic contradiction detection") the same way #167 intends to resolve it for E9 (E9c itself remains unimplemented/open).

### E12b — cross-page contradiction (`--deep`, skill-only, #336)

**Where it lives**: `audit/SKILL.md` Phase 2.5 DEEP, not `audit-validate.py`. There is no reference-impl function for E12b and none is planned — the judgment step needs an LLM reading page bodies, which the deterministic reference impl structurally cannot do.

**Candidate-pair prefilter** (deterministic, cheap — bounds the expensive judgment step instead of comparing every wiki page against every other):

```
wiki_pages = [r for r in frontmatter_records if r.path.parts[0] == "wiki" and r.fm.type == "wiki"]
for (A, B) in unordered_pairs(wiki_pages):
  shared_tags = set(lower(t) for t in A.fm.tags) & set(lower(t) for t in B.fm.tags)
  links = A in wikilinks_by_file[B] or B in wikilinks_by_file[A]
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
**Scope guard** (`detect_stale_wiki`): flags a page **only** when its top folder is `wiki/` AND `type: wiki` — a stray old `verified:` on a non-wiki file is never an E12. A page with a missing or unparseable `verified:` is **skipped** (staleness is uncomputable without it; the field is write-time auto-stamped, so absence is a write-path bug rather than a staleness signal — flagging it would be a false E12).

**Detection pseudocode**:

```
for each record in frontmatter_records:
  if path.parts[0] != "wiki": skip          # wiki/-scoped
  if fm.type != "wiki": skip                # type:wiki only
  verified = parse_date(fm.verified)
  if verified is None: skip                 # missing/unparseable → uncomputable
  if (today - verified).days > STALE_WIKI_DAYS: → wiki_stale
```

**Rationale**: A stale wiki page is a **display-only** P1 warning (staleness = 정체, same tier as E6/E7) — the next action (recompile / re-verify) is a semantic decision, never auto-fixed. Regression-covered by the DoD fixture (5 seeded `wiki/` pages with `verified: 2020-01-01` → `seeded_detected.E12 == 5`; 2 fresh pages stamped with the run date → `fp_on_clean.E12 == 0`, date-independent) plus a scoping unit test (`test-wiki-self-audit.py`).

## Auto-fix eligibility

Only the following are mutated by Phase 4 OPTIONAL-FIX (frontmatter-only edits):

| Type | Auto-fix action |
|------|-----------------|
| `missing_required_fields` (E2) | Add missing `tags`, `type`, `created` fields. For `tags:`, propose a deterministic 3-tier inference (type → filename slug → parent folder; see the E2 **Tag inference** section above) — never an empty `tags: []` — and preview it in the confirmation gate before applying. |

Never auto-fixed: E1 (body structure unknown), E3 (rename affects inbound links — suggestion only), E4 (requires human decision on rename/delete), E5 (content value judgment — connection candidates are suggestions only), E6/E7 (stagnation requires semantic decision: process / promote / archive), E8 (manifest-sourced promotion signal — manual `status` decision), E9 (canonical-form choice + multi-file rewrite is the user's decision — display-only), E10/E11 (moving a file affects inbound links — display-only warning, user decides the destination), E12 (recompiling/re-verifying a stale wiki page, or reconciling a confirmed E12b contradiction, is a semantic decision — display-only warning).

## Manifest Summary (display-only)

The audit REPORT header shows manifest metadata when `.vault-bridge/manifest.json` exists at the vault root:

- `file_count` — number of files indexed by vault-bridge
- `generated_at` — ISO timestamp of last manifest refresh

Absence is non-fatal: the header shows `매니페스트: 없음 (vault-bridge 미설치)`. No finding is emitted for missing or stale manifest in PR 4.

> **Not Step 0**: v4 §6.1 Step 0 describes manifest compute (`references_in/out`, `access_count`, `promotion_candidate`). That write-side Step 0 is deferred to PR 5+. PR 4 only reads `file_count` and `generated_at` from the vault-bridge-generated manifest for display purposes.
