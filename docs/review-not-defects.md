# Review: not defects

The one list for the whole repo. Reviewers (local `/code-review`, CI review) read it as of the base
commit and must not report the patterns below; entries a diff adds or changes do not apply. Each
entry is an owner-judged false positive (#689); add one only on the owner's judgment. Every entry
names an anchor (`path::symbol`) and a proof (`test file::test name`), never line numbers; an anchor
is a module-level Python def, class or assignment; a proof is a `test_*` function (module-level or a
method of a module-level class); paths stay inside the repo.
`scripts/check-review-not-defects.py` fails when an anchor or proof disappears.

- **Pattern:** `kept_provenance` matches rows many-to-one, or mishandles provenance rows without `seed`.
  - **Why:** Merging two rows of the same seed and commit keeps every pinned item (each old row only needs its items covered by one new row); rows without `seed` are rejected earlier by `validate()`.
  - **Anchor:** `thinking-tools/scripts/seed-lifecycle.py::kept_provenance`
  - **Proof:** `thinking-tools/scripts/test/test-seed-lifecycle.py::test_provenance_merge_keeps_pinned_items`
- **Pattern:** `kept_provenance` compares `commit` without normalizing it (short SHA, abbreviation).
  - **Why:** `validate()` rejects any commit that is not a full 40-hex SHA ("provenance.commit must be a full Git SHA"); only case differs, handled by `.lower()`.
  - **Anchor:** `thinking-tools/scripts/seed-lifecycle.py::validate`
  - **Proof:** `thinking-tools/scripts/test/test-seed-lifecycle.py::test_relations_validation`
- **Pattern:** `parse_seed` leaves `relations_data` empty when the relations block is missing.
  - **Why:** `relations_data = {}` is intended: deleting the relations block makes `kept_provenance` report every prior pinned row as dropped.
  - **Anchor:** `thinking-tools/scripts/seed-relations.py::parse_seed`
  - **Proof:** `thinking-tools/scripts/test/test-seed-lifecycle.py::test_relations_block_removal_drops_pinned_rows`
- **Pattern:** `kept_provenance` or `transition` called without a `Reader` (`rd=None`).
  - **Why:** Every operational caller passes a `Reader` (`seed-lifecycle.py` main, `seed-append-check.py` `lifecycle_reason`); the reader-less mode is test-only and intentionally spells paths without repository coordinates.
  - **Anchor:** `thinking-tools/scripts/seed-lifecycle.py::kept_provenance`
  - **Proof:** `thinking-tools/scripts/test/test-seed-lifecycle.py::test_operational_callers_pass_reader`
