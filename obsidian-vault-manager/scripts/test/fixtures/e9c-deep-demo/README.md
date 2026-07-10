# E9c `--deep` demo fixtures (#167)

Twelve `notes/` files, used to demonstrate that `audit/SKILL.md` Phase 2.5's
E9c sub-check catches a real semantic-synonym tag pair and does not flag
non-synonymous pairs — including the *hub-tag* shape (a broad category tag
that directly co-occurs with a specific tag it is not synonymous with), which
is the more common real-world false-positive case for E9c. This is **not** a
`--dod`-gated fixture — E9c has no `audit-validate.py` function to
seed/measure (see `vault-audit-rules.md`'s E9c section for why) — it is a
manual walkthrough of the skill-only `--deep` LLM path, mirroring
`fixtures/e12b-deep-demo/`.

## Tags

- `llm` (3 files) / `large-language-model` (3 files), both tagged alongside `ai` (6 files total) — the **target synonym pair**: the two tags name the exact same concept under two different spellings.
- `python` (3 files) / `docker` (3 files), both tagged alongside `backend` (6 files total) — the **target non-synonym pair**: a language and a containerization tool that are related in practice but not the same concept.
- `ai` and `backend` are hub tags: each independently crosses `E9_MIN_FILES` (3) and co-occurs directly with every file of its two specific tags — a realistic shape (a broad category tag applied alongside multiple specific ones), not an artifact of this fixture.

## Walkthrough performed (2026-07-10, against SKILL.md Phase 2.5 E9c as written in this PR)

1. **Candidate-pair prefilter** (deterministic, `E9_MIN_FILES` floor + source-overlap/common-neighbor check). `frequent_tags` = `{llm, large-language-model, python, docker, ai, backend}` (all 6 meet the floor). Walking every pair of `frequent_tags` through the prefilter — **not** just the two target pairs — actually yields 6 candidates, not 2:
   - `llm` ↔ `ai` → **source overlap** (every `llm` file also carries `ai`) → candidate.
   - `large-language-model` ↔ `ai` → **source overlap** → candidate.
   - `llm` ↔ `large-language-model` → no source overlap, but **common neighbor** `ai` → candidate.
   - `python` ↔ `backend` → **source overlap** → candidate.
   - `docker` ↔ `backend` → **source overlap** → candidate.
   - `python` ↔ `docker` → no source overlap, but **common neighbor** `backend` → candidate.
   - All remaining pairs (e.g. `llm`↔`python`, `ai`↔`backend`, `llm`↔`docker`) → no source overlap, no shared neighbor → not candidates.
   - Result: **6 candidate pairs** reach the LLM judgment step — 2 "headline" pairs plus 4 hub-tag pairs.

2. **LLM judgment** (same concept under different spelling/phrasing, vs. merely related-but-distinct concepts that co-occur):
   - `llm` ↔ `large-language-model` → same concept, two spellings of the same term → **SYNONYM**.
   - `llm` ↔ `ai` → `ai` is a broad category, `llm` one specific technology within it → **not a synonym**, despite always co-occurring.
   - `large-language-model` ↔ `ai` → same reasoning → **not a synonym**.
   - `python` ↔ `docker` → a programming language and a containerization tool; related in practice but not the same concept → **not a synonym**.
   - `python` ↔ `backend` → `backend` is a broad category, `python` one specific language within it → **not a synonym**, despite always co-occurring.
   - `docker` ↔ `backend` → same reasoning → **not a synonym**.
   - This is the acceptance-relevant part of the demo: 5 of 6 candidates are hub-tag or unrelated-but-adjacent pairs, and the LLM judgment step must decline all 5 — a naive "shares a neighbor or co-occurs → synonym" heuristic would wrongly flag every one of them.

3. **FP-mitigation confirm gate**: only the `llm`/`large-language-model` pair is staged as a DEEP candidate and offered to the user via `AskUserQuestion`. The other 5 pairs never reach the gate at all (Step 2 correctly declined to flag them) — confirmed "동의어 맞음" by the user for the llm pair.

4. **Finding emitted** (folded into the same `tag_vocabulary_inconsistency` bucket E9a/E9b already populate):
   ```json
   {"error_type": "tag_vocabulary_inconsistency", "severity": "Warning", "priority": "P2",
    "path": "", "detail": "태그 의미 동의어(LLM 판단, --deep): 'llm' (3개 파일) ↔ 'large-language-model' (3개 파일) — 같은 개념(대형 언어 모델)을 가리키는 두 표기",
    "auto_fix_eligible": false}
   ```
   No finding for any of the other 5 candidate pairs.

**Outcome**: `--deep` catches the intentional semantic synonym and does not flag
any of the 5 non-synonymous candidates — including the hub-tag shape, the more
common real-world E9c false-positive case — the acceptance criterion for #167.

## Reproducing live

Point a vault root at this directory (e.g. `VAULT_BRIDGE_VAULT_ROOT` set to this
fixture dir) and run `/audit --deep` in a session with the
`obsidian-vault-manager` plugin installed. Phase 2.5's E9c sub-check re-derives
the same 6 candidate pairs from `frontmatter_records` and performs the same
judgment live.
