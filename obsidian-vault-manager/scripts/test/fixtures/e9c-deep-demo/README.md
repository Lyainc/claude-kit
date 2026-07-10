# E9c `--deep` demo fixtures (#167)

Twelve `notes/` files, two tag pairs, used to demonstrate that `audit/SKILL.md`
Phase 2.5's E9c sub-check catches a real semantic-synonym tag pair and does not
flag a topically-related but non-synonymous pair. This is **not** a `--dod`-gated
fixture — E9c has no `audit-validate.py` function to seed/measure (see
`vault-audit-rules.md`'s E9c section for why) — it is a manual walkthrough of the
skill-only `--deep` LLM path, mirroring `fixtures/e12b-deep-demo/`.

## Pairs

- **Synonym pair**: `llm` (3 files) vs `large-language-model` (3 files).
  Both meet the `E9_MIN_FILES` (3) floor and both co-occur with the `ai` tag
  (common-neighbor prefilter hit) — the two tags name the exact same concept
  under two different spellings.
- **Non-synonym pair**: `python` (3 files) vs `docker` (3 files).
  Both meet the `E9_MIN_FILES` floor and both co-occur with the `backend` tag
  (common-neighbor prefilter also hits — this pair is deliberately
  topically-adjacent, not excluded by the prefilter) but the tags name two
  distinct, unrelated concepts (a language vs. a containerization tool) that
  merely tend to appear together. This pair is the false-positive check: a
  naive "shares a neighbor tag → synonym" heuristic would wrongly flag it; the
  LLM judgment step must not.

## Walkthrough performed (2026-07-10, against SKILL.md Phase 2.5 E9c as written in this PR)

1. **Candidate-pair prefilter** (deterministic, `E9_MIN_FILES` floor + source-overlap/common-neighbor check):
   - `llm` (3 files) / `large-language-model` (3 files) → no direct file co-occurrence, but both co-occur with `ai` → common-neighbor hit → candidate.
   - `python` (3 files) / `docker` (3 files) → no direct file co-occurrence, but both co-occur with `backend` → common-neighbor hit → candidate.
   - All other cross-pairs (e.g. `llm`/`docker`) → no shared neighbor, no file overlap → not candidates.
   - Result: 2 candidate pairs reach the LLM judgment step.

2. **LLM judgment** (same concept under different spelling, vs. merely related-but-distinct concepts):
   - `llm` vs `large-language-model` → same concept, two spellings of the same term → **SYNONYM**.
   - `python` vs `docker` → a programming language and a containerization tool; related in practice (Python apps often run in Docker) but not the same concept → **not a synonym**, despite sharing the `backend` neighbor tag.

3. **FP-mitigation confirm gate**: only the `llm`/`large-language-model` pair is staged as a DEEP candidate and offered to the user via `AskUserQuestion`. The `python`/`docker` pair never reaches the gate at all (Step 2 correctly declined to flag it) — confirmed "동의어 맞음" by the user for the llm pair.

4. **Finding emitted** (folded into the same `tag_vocabulary_inconsistency` bucket E9a/E9b already populate):
   ```json
   {"error_type": "tag_vocabulary_inconsistency", "severity": "Warning", "priority": "P2",
    "path": "", "detail": "태그 의미 동의어(LLM 판단, --deep): 'llm' (3개 파일) ↔ 'large-language-model' (3개 파일) — 같은 개념(대형 언어 모델)을 가리키는 두 표기",
    "auto_fix_eligible": false}
   ```
   No finding for the `python`/`docker` pair.

**Outcome**: `--deep` catches the intentional semantic synonym and does not flag
the non-synonymous (but topically overlapping) pair — the acceptance criterion
for #167.

## Reproducing live

Point a vault root at this directory (e.g. `VAULT_BRIDGE_VAULT_ROOT` set to this
fixture dir) and run `/audit --deep` in a session with the
`obsidian-vault-manager` plugin installed. Phase 2.5's E9c sub-check re-derives
the same two candidate pairs from `frontmatter_records` and performs the same
judgment live.
