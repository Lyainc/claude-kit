#!/usr/bin/env bash
# gen-fixture.sh — synthesize a test vault fixture under /tmp/ovm-fixture-*/
#
# Flags:
#   --with-audit-errors   Inject 5 seeded errors of each of the 5 vault audit
#                         error types (25 total) for DoD verification.
#                         Also adds 200 extra clean notes for FP measurement.
#
# v4 layout: inbox/ + notes/ + assets/ (no 00_Inbox, 20_Projects, 30_Notes)
#
# Fixture naming convention (IMPORTANT):
#   Seeded error files: "audit-eN-*.md" (e1–e5); clean files: "audit-clean-*.md".
#   The DoD validator uses substring containment ("audit-eN-" in path) —
#   a clean fixture with an "audit-eN-" prefix will count as a false detection.

set -euo pipefail

if [[ "${VAULT_BRIDGE_DISABLE:-}" == "1" ]]; then
  exit 0
fi

WITH_AUDIT_ERRORS=0
for arg in "$@"; do
  [[ "$arg" == "--with-audit-errors" ]] && WITH_AUDIT_ERRORS=1
done

if [[ -n "${OVM_FIXTURE_DIR:-}" ]]; then
  FIXTURE_DIR="$OVM_FIXTURE_DIR"
else
  # Default dir name varies by mode so that a clean fixture and an
  # audit-error fixture do not collide on $$ collision or repeated runs.
  if [[ "$WITH_AUDIT_ERRORS" -eq 1 ]]; then
    FIXTURE_DIR="/tmp/ovm-fixture-audit-errors-$$"
  else
    FIXTURE_DIR="/tmp/ovm-fixture-$$"
  fi
fi

# Allow reuse of an existing fixture dir (for testing stability),
# but only if the existing fixture matches the requested mode. The mode
# marker prevents returning a stale clean fixture when --with-audit-errors
# is requested (and vice versa).
MARKER_FILE="$FIXTURE_DIR/.ovm/fixture-mode"
expected_mode="clean"
[[ "$WITH_AUDIT_ERRORS" -eq 1 ]] && expected_mode="audit-errors"
if [[ -d "$FIXTURE_DIR" ]]; then
  existing_mode="$(cat "$MARKER_FILE" 2>/dev/null || echo "unknown")"
  if [[ "$existing_mode" == "$expected_mode" ]]; then
    echo "Fixture already exists at $FIXTURE_DIR (mode=$existing_mode)" >&2
    echo "$FIXTURE_DIR"
    exit 0
  fi
  echo "ERROR: $FIXTURE_DIR exists with mode=$existing_mode but mode=$expected_mode was requested." >&2
  echo "Remove the existing dir or set OVM_FIXTURE_DIR to a different path." >&2
  exit 1
fi

log() { echo "$*" >&2; }

log "Generating fixture vault at $FIXTURE_DIR ..."

# ── create directory structure (v4: inbox/ + notes/ + assets/) ────────────────

mkdir -p \
  "$FIXTURE_DIR/inbox" \
  "$FIXTURE_DIR/notes" \
  "$FIXTURE_DIR/assets" \
  "$FIXTURE_DIR/.ovm"

# ── helper: write a file ───────────────────────────────────────────────────────

write_file() {
  local path="$1"
  cat > "$path"
}

# ── inbox/: 30 captures + 10 sessions ────────────────────────────────────────

for i in $(seq 1 30); do
  date="2026-04-$(printf '%02d' $((i % 28 + 1)))"
  topic="topic-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/inbox/capture-${date}-${topic}.md" <<EOF
---
created: ${date}
tags: [capture, inbox]
type: capture
---

# Capture ${i}

Inbox capture item ${i}. Needs processing.

[[note-$(printf '%03d' $((i % 20 + 1)))]]
EOF
done

for i in $(seq 1 10); do
  date="2026-04-$(printf '%02d' $i)"
  write_file "$FIXTURE_DIR/inbox/session-${date}.md" <<EOF
---
created: ${date}
tags: [session]
type: session
status: active
---

# Session ${i}

Work done during session ${i}.
EOF
done

# ── notes/: 200 clean notes ────────────────────────────────────────────────────

for i in $(seq 1 200); do
  name="note-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Note ${i}

Content of note ${i}.
EOF
done

# ── notes/: intentional issues (30 total) ─────────────────────────────────────

# Issue batch 1: missing frontmatter (5 files)
for i in $(seq 1 5); do
  write_file "$FIXTURE_DIR/notes/no-frontmatter-$(printf '%03d' $i).md" <<EOF
# Note Without Frontmatter ${i}

This note has no frontmatter at all.
EOF
done

# Issue batch 2: wrong filename convention (5 files) — v3 date-first prefix
for i in $(seq 1 5); do
  write_file "$FIXTURE_DIR/notes/2026-04-bad-name-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Bad Filename Note ${i}

Note with non-conforming v3 date-first filename.
EOF
done

# Issue batch 3: broken wikilinks (5 files) — link to nonexistent notes
for i in $(seq 1 5); do
  name="broken-links-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Broken Links Note ${i}

Points to [[totally-nonexistent-note-${i}]] and [[also-missing-${i}]].
EOF
done

# Issue batch 4: missing required frontmatter fields (5 files)
for i in $(seq 1 5); do
  name="missing-fields-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/notes/${name}.md" <<EOF
---
created: 2026-04-01
---

# Missing Fields Note ${i}

Has created but missing tags and type.
EOF
done

# Issue batch 5: orphan notes — no inbound wikilinks (10 files)
for i in $(seq 1 10); do
  name="orphan-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Orphan Note ${i}

This note exists but nothing links to it.
EOF
done

# ── seed audit-state with half the notes pre-audited ─────────────────────────

python3 - "$FIXTURE_DIR" <<'PYEOF'
import os, sys, json, time

fixture = sys.argv[1]
state = {"version": 1, "paths": {}, "last_full_scan": None}

# Mark the first 100 notes as already-audited (simulate incremental scan)
count = 0
for root, dirs, files in os.walk(os.path.join(fixture, 'notes')):
    for f in sorted(files):
        if count >= 100:
            break
        if not f.endswith('.md'):
            continue
        fpath = os.path.join(root, f)
        relpath = os.path.relpath(fpath, fixture)
        mtime = int(os.stat(fpath).st_mtime)
        state['paths'][relpath] = {
            'last_audited': '2026-04-18T00:00:00+00:00',
            'mtime_at_audit': mtime,
            'content_hash': 'abcd1234abcd1234',
            'status': 'clean'
        }
        count += 1
    dirs.clear()

os.makedirs(os.path.join(fixture, '.ovm'), exist_ok=True)
with open(os.path.join(fixture, '.ovm', 'audit-state.json'), 'w') as f:
    json.dump(state, f, indent=2)

print(f"Seeded {count} pre-audited records into audit-state.json", file=sys.stderr)
PYEOF

log ""
log "Fixture vault created at: $FIXTURE_DIR"
log "  Structure (v4):"
log "    inbox/          : 30 captures + 10 sessions"
log "    notes/          : 200 clean + 30 intentional issues"
log "      Issues: 5 missing frontmatter, 5 bad filenames, 5 broken links,"
log "              5 missing fields, 10 orphans"
log "    assets/         : empty"
log "    .ovm/           : audit-state.json with 100 pre-audited records"
log ""

# ── --with-audit-errors: inject 5×5=25 seeded errors for DoD measurement ──────

if [[ "$WITH_AUDIT_ERRORS" == "1" ]]; then
  log "Injecting audit-error fixtures (--with-audit-errors) ..."

  # ── E1: missing_frontmatter (5 files) ────────────────────────────────────────
  # Files with NO frontmatter at all.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/notes/audit-e1-missing-fm-$(printf '%03d' $i).md" <<EOF
# Audit E1 Note ${i}

This note has no frontmatter block whatsoever.
EOF
  done

  # ── E2: missing_required_fields (5 files) ────────────────────────────────────
  # Files with frontmatter but missing tags and/or type.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/notes/audit-e2-missing-fields-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
---

# Audit E2 Note ${i}

Has created but missing tags and type.
EOF
  done

  # (The former E2-status seed block is gone: `status` left the required set when the
  # v4 §3.3 status machine was abolished — v5 §5/§6, #480. A note with created+tags+type
  # and no status is now a CONFORMING file, so seeding one would be a false positive.)

  # ── E3: filename_convention_violation (5 files) ───────────────────────────────
  # Notes with v3-style date-first prefix (violates v4 notes/ naming rule).
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/notes/2026-04-audit-e3-bad-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Audit E3 Note ${i}

Non-conforming v3 date-first filename.
EOF
  done

  # ── E4: broken_wikilink (5 files) ────────────────────────────────────────────
  # Files referencing stems that don't exist anywhere in the vault.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/notes/audit-e4-broken-links-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Audit E4 Note ${i}

Links to [[audit-ghost-target-${i}]] which does not exist.
EOF
  done

  # ── E5: orphan_note (5 files + 1 empty-tags graceful case) ────────────────────
  # Clean notes that no other file links to. tags:[note] ensures tag-intersection
  # candidates are non-empty (#130) — shares the [note] tag with the 200 clean
  # notes below, so each orphan gets top-3 connection candidates.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/notes/audit-e5-orphan-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Audit E5 Orphan Note ${i}

This note exists but nothing links to it.
EOF
  done

  # E5 empty-tags orphan: tags:[] → no shared tags → candidates:[] graceful path
  # (#130: "연결 후보 없음 (공유 태그 없음)"). tags:[] does NOT trip E2 (empty list
  # is present, just empty), so this is a pure E5 with no candidate computation.
  write_file "$FIXTURE_DIR/notes/audit-e5-orphan-empty-tags.md" <<EOF
---
created: 2026-04-01
tags: []
type: note
status: raw
---

# Audit E5 Orphan No Tags

Orphan with empty tags — exercises the no-candidate graceful branch (#130).
EOF

  # ── E6: stale_inbox (5 files) ─────────────────────────────────────────────────
  # Inbox captures still raw with very old `created:` dates.
  # `created: 2020-01-01` ensures age > STALE_INBOX_DAYS (14) regardless of when
  # the audit runs. type:session would be exempt via status:active — we use
  # type:capture + status:raw to deliberately trigger E6.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/inbox/audit-e6-stale-capture-$(printf '%03d' $i).md" <<EOF
---
created: 2020-01-01
tags: [capture, inbox]
type: capture
status: raw
---

# Audit E6 Stale Capture ${i}

Inbox capture left raw since 2020 — should trigger E6_stale_inbox.
EOF
  done

  # ── E10: misplaced_file (5 files) ─────────────────────────────────────────────
  # type:session belongs in inbox/ (EXPECTED_FOLDER) but seeded in notes/.
  # Ring-linked so they don't also trip E5 orphan detection.
  for i in $(seq 1 5); do
    next=$(( (i % 5) + 1 ))
    link_target="audit-e10-misplaced-session-$(printf '%03d' $next)"
    write_file "$FIXTURE_DIR/notes/audit-e10-misplaced-session-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [session]
type: session
status: active
---

# Audit E10 Misplaced Session ${i}

type:session placed in notes/ instead of inbox/ — should trigger E10. Links to [[${link_target}]].
EOF
  done

  # ── E11: unstructured_path (5 files: 2 root-direct + 3 arbitrary folder) ───────
  # Root-direct files (no canonical top folder) and an arbitrary "20_Projects/"
  # folder both fall outside {inbox,notes,assets}. Each carries valid frontmatter
  # (so E1/E2 don't fire) and a self-edge wikilink to avoid noise.
  for i in 1 2; do
    write_file "$FIXTURE_DIR/audit-e11-root-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Audit E11 Root File ${i}

Root-direct file outside canonical folders — should trigger E11_unstructured_path.
EOF
  done

  mkdir -p "$FIXTURE_DIR/20_Projects"
  for i in 1 2 3; do
    write_file "$FIXTURE_DIR/20_Projects/audit-e11-misplaced-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Audit E11 Arbitrary Folder ${i}

File in non-canonical "20_Projects/" folder — should trigger E11_unstructured_path.
EOF
  done

  # ── E11 exempt-guard coverage (#129 Acceptance) ───────────────────────────────
  # A root-level _index.md must NOT be flagged as E11 (EXEMPT_FILES guard).
  # Seeded into the clean (non-error) area so fp_on_clean.E11 actually exercises
  # the exempt path. Uses no audit-eN- prefix so it cannot count as a seed.
  write_file "$FIXTURE_DIR/_index.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: evergreen
---

# Vault Index

Root-level vault index — must be EXEMPT from E11 (regression guard for #129).
EOF

  # ── E12: wiki_self_audit — staleness (5 files) ────────────────────────────────
  # v5 §7 U3 wiki self-audit. Deterministic slice = staleness: a wiki page whose
  # `verified:` is older than STALE_WIKI_DAYS (90). `verified: 2020-01-01` keeps
  # these stale regardless of run date (same date-independence trick as E6).
  # Full valid wiki frontmatter (created/tags/type:wiki/verified/provenance, NO
  # status — v5 §4.1 puts wiki outside the status machine) so they trip ONLY E12:
  # wiki/ is canonical (no E11), type:wiki→wiki/ is correct placement (no E10),
  # filename is slug form (no E3), and E5 orphan is notes/-scoped (no E5).
  # Semantic cross-page CONTRADICTION (E12b) is the deferred --deep LLM path — not
  # seeded here (a deterministic fixture cannot exercise a non-deterministic check).
  mkdir -p "$FIXTURE_DIR/wiki"
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/wiki/audit-e12-stale-$(printf '%03d' $i).md" <<EOF
---
created: 2020-01-01
tags: [wiki, domain]
type: wiki
verified: 2020-01-01
provenance: fixture-seed-e12-stale-${i}
---

# Audit E12 Stale Wiki ${i}

Wiki page whose \`verified:\` is 2020 — age > STALE_WIKI_DAYS (90) → E12_wiki_stale.
EOF
  done

  # E12 FP clean: fresh wiki pages whose `verified:` is TODAY → never stale.
  # Uses `audit-clean-` prefix so it lands in fp_on_clean.E12 measurement, and a
  # run-date-relative `verified:` so fp stays 0 no matter when the fixture is built
  # (a hardcoded recent date would silently go stale once the run date drifts past
  # the 90-day window — the exact date-dependence the DoD forbids).
  _E12_TODAY="$(date +%Y-%m-%d)"
  for i in 1 2; do
    write_file "$FIXTURE_DIR/wiki/audit-clean-wiki-$(printf '%03d' $i).md" <<EOF
---
created: 2020-01-01
tags: [wiki, domain]
type: wiki
verified: ${_E12_TODAY}
provenance: fixture-seed-e12-clean-${i}
---

# Audit Clean Wiki ${i}

Fresh wiki page (verified today) — must NOT trip E12_wiki_stale (fp guard).
EOF
  done

  # ── E9: tag_vocabulary_inconsistency (2 pairs, vault-wide) ────────────────────
  # E9 is a VAULT-LEVEL check (findings carry path:"") — DoD counts PAIRS, not
  # files. We seed two pairs, each form in 3 files (== E9_MIN_FILES) so the
  # frequency FP guard fires exactly at the threshold:
  #   E9a singular/plural : tag `api` (3 files) ↔ `apis` (3 files)
  #   E9b property naming : key `sourceUrl` (3 files) ↔ `source_url` (3 files)
  # All 12 files carry full valid frontmatter + conforming names + a ring
  # wikilink within their group, so they trip ONLY E9 (no E1/E2/E3/E4/E5).
  # The "note"/"notes" tag can never pair here — no `notes` tag exists in the
  # fixture, so E9a only reports the api/apis pair.

  # E9a — singular form `api` (3 files, ring-linked within the singular group).
  for i in 1 2 3; do
    next=$(( (i % 3) + 1 ))
    write_file "$FIXTURE_DIR/notes/audit-e9-tag-api-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note, api]
type: note
status: raw
---

# Audit E9a API ${i}

Uses the singular tag \`api\`. Links to [[audit-e9-tag-api-$(printf '%03d' $next)]].
EOF
  done

  # E9a — plural form `apis` (3 files, ring-linked within the plural group).
  for i in 1 2 3; do
    next=$(( (i % 3) + 1 ))
    write_file "$FIXTURE_DIR/notes/audit-e9-tag-apis-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note, apis]
type: note
status: raw
---

# Audit E9a APIs ${i}

Uses the plural tag \`apis\` — inconsistent with \`api\`. Links to [[audit-e9-tag-apis-$(printf '%03d' $next)]].
EOF
  done

  # E9b — snake_case key `source_url` (3 files, ring-linked).
  for i in 1 2 3; do
    next=$(( (i % 3) + 1 ))
    write_file "$FIXTURE_DIR/notes/audit-e9-prop-snake-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
source_url: https://example.com/snake-${i}
---

# Audit E9b snake ${i}

Uses the snake_case key \`source_url\`. Links to [[audit-e9-prop-snake-$(printf '%03d' $next)]].
EOF
  done

  # E9b — camelCase key `sourceUrl` (3 files, ring-linked) — inconsistent with
  # the snake_case form above → E9b pair.
  for i in 1 2 3; do
    next=$(( (i % 3) + 1 ))
    write_file "$FIXTURE_DIR/notes/audit-e9-prop-camel-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
sourceUrl: https://example.com/camel-${i}
---

# Audit E9b camel ${i}

Uses the camelCase key \`sourceUrl\`. Links to [[audit-e9-prop-camel-$(printf '%03d' $next)]].
EOF
  done

  # ── 200 extra clean notes for FP measurement ─────────────────────────────────
  # These have fully valid frontmatter and filenames; none should be flagged.
  # Linking strategy: note i links to note i+1 (mod 200), forming a ring so
  # every note has exactly one inbound link and is never an orphan.
  for i in $(seq 1 200); do
    name="audit-clean-$(printf '%03d' $i)"
    next=$(( (i % 200) + 1 ))
    link_target="audit-clean-$(printf '%03d' $next)"
    write_file "$FIXTURE_DIR/notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
status: raw
---

# Audit Clean Note ${i}

Clean note for FP measurement. Links to [[${link_target}]].
EOF
  done

  log "  Audit error fixtures (v4, E1-E11):"
  log "    E1 missing_frontmatter              : 5 files"
  log "    E2 missing_required_fields          : 5 files (5 base)"
  log "    E3 filename_convention_violation     : 5 files (v3 date-first prefix; suggested_filename)"
  log "    E4 broken_wikilink                  : 5 files"
  log "    E5 orphan_note                      : 6 files (5 w/ tag candidates + 1 empty-tags graceful)"
  log "    E6 stale_inbox                      : 5 files (inbox raw, created 2020)"
  log "    E9 tag_vocabulary_inconsistency     : 2 pairs (api↔apis, sourceUrl↔source_url; 12 files, 3 per form)"
  log "    E10 misplaced_file                  : 5 files (type:session in notes/, ring-linked)"
  log "    E11 unstructured_path               : 5 files (2 root-direct + 3 in 20_Projects/)"
  log "    E12 wiki_stale                      : 5 files (wiki/ verified:2020 > STALE_WIKI_DAYS; contradiction=--deep, deferred)"
  log "    Total seeded errors                 : 46 files + 12 E9 files (2 pairs)"
  log "    Extra clean notes (FP base)         : 200 + root _index.md (E11 exempt guard) + 2 fresh wiki (E12 fp guard)"
  log ""
fi

# Write mode marker so subsequent runs can detect mismatched reuse.
echo "$expected_mode" > "$MARKER_FILE"

# Print fixture path on stdout for programmatic consumption
echo "$FIXTURE_DIR"
