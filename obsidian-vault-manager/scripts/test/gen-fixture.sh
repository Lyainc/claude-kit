#!/usr/bin/env bash
# gen-fixture.sh — synthesize a test vault fixture under /tmp/ovm-fixture-*/
#
# Flags:
#   --with-audit-errors   Inject 5 seeded errors of each of the 8 vault-audit
#                         error types (40 total) for measurement.md DoD verification.
#                         Also adds 200 extra clean notes for FP measurement.

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

# ── create directory structure ─────────────────────────────────────────────────

mkdir -p \
  "$FIXTURE_DIR/00_Inbox" \
  "$FIXTURE_DIR/20_Projects/alpha" \
  "$FIXTURE_DIR/20_Projects/beta" \
  "$FIXTURE_DIR/30_Notes" \
  "$FIXTURE_DIR/.ovm"

# ── helper: write a file ───────────────────────────────────────────────────────

write_file() {
  local path="$1"
  cat > "$path"
}

# ── 00_Inbox: 30 captures + 10 sessions ───────────────────────────────────────

for i in $(seq 1 30); do
  date="2026-04-$(printf '%02d' $((i % 28 + 1)))"
  topic="topic-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/00_Inbox/capture-${date}-${topic}.md" <<EOF
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
  write_file "$FIXTURE_DIR/00_Inbox/session-${date}.md" <<EOF
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

# ── 20_Projects/alpha: _index + 5 plans ───────────────────────────────────────

write_file "$FIXTURE_DIR/20_Projects/alpha/_index.md" <<'EOF'
---
created: 2026-04-01
tags: [project, alpha]
type: project
status: active
linked_notes: [alpha-architecture, alpha-decisions]
related_plans: [plan-2026-04-01-init, plan-2026-04-10-phase2]
---

# Project Alpha

Main project index.

[[alpha-architecture]]
[[alpha-decisions]]
EOF

for i in $(seq 1 5); do
  date="2026-04-$(printf '%02d' $i)"
  write_file "$FIXTURE_DIR/20_Projects/alpha/plan-${date}-task-${i}.md" <<EOF
---
created: ${date}
tags: [plan, alpha]
type: plan
workstream: W${i}
---

# Plan Task ${i}

Spec for task ${i}.

[[alpha-architecture]]
EOF
done

# ── 20_Projects/beta: _index + 3 sessions ────────────────────────────────────

write_file "$FIXTURE_DIR/20_Projects/beta/_index.md" <<'EOF'
---
created: 2026-04-05
tags: [project, beta]
type: project
status: active
---

# Project Beta

Beta project. Missing linked_notes field (intentional gap).
EOF

for i in $(seq 1 3); do
  date="2026-04-$(printf '%02d' $((i + 10)))"
  write_file "$FIXTURE_DIR/20_Projects/beta/session-${date}.md" <<EOF
---
created: ${date}
tags: [session, beta]
type: session
status: active
---

# Beta Session ${i}

[[nonexistent-note-${i}]]
EOF
done

# ── 30_Notes: 200 clean notes ─────────────────────────────────────────────────

for i in $(seq 1 200); do
  name="note-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/30_Notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Note ${i}

Content of note ${i}.
EOF
done

# ── 30_Notes: intentional issues (30 total) ───────────────────────────────────

# Issue batch 1: missing frontmatter (5 files)
for i in $(seq 1 5); do
  write_file "$FIXTURE_DIR/30_Notes/no-frontmatter-$(printf '%03d' $i).md" <<EOF
# Note Without Frontmatter ${i}

This note has no frontmatter at all.
EOF
done

# Issue batch 2: wrong filename convention (5 files) — dated prefix on notes
for i in $(seq 1 5); do
  write_file "$FIXTURE_DIR/30_Notes/2026-04-bad-name-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Bad Filename Note ${i}

Note with non-conforming filename.
EOF
done

# Issue batch 3: broken wikilinks (5 files) — link to nonexistent notes
for i in $(seq 1 5); do
  name="broken-links-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/30_Notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Broken Links Note ${i}

Points to [[totally-nonexistent-note-${i}]] and [[also-missing-${i}]].
EOF
done

# Issue batch 4: missing required frontmatter fields (5 files)
for i in $(seq 1 5); do
  name="missing-fields-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/30_Notes/${name}.md" <<EOF
---
created: 2026-04-01
---

# Missing Fields Note ${i}

Has created but missing tags and type.
EOF
done

# Issue batch 5: orphan notes — clean notes with no inbound links (10 files)
for i in $(seq 1 10); do
  name="orphan-$(printf '%03d' $i)"
  write_file "$FIXTURE_DIR/30_Notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
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
for root, dirs, files in os.walk(os.path.join(fixture, '30_Notes')):
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
log "  Structure:"
log "    00_Inbox/       : 30 captures + 10 sessions"
log "    20_Projects/    : alpha (1 _index + 5 plans) + beta (1 _index + 3 sessions)"
log "    30_Notes/       : 200 clean + 30 intentional issues"
log "      Issues: 5 missing frontmatter, 5 bad filenames, 5 broken links,"
log "              5 missing fields, 10 orphans"
log "    .ovm/           : audit-state.json with 100 pre-audited records"
log ""

# ── --with-audit-errors: inject 5×8=40 seeded errors for DoD measurement ──────

if [[ "$WITH_AUDIT_ERRORS" == "1" ]]; then
  log "Injecting audit-error fixtures (--with-audit-errors) ..."

  mkdir -p \
    "$FIXTURE_DIR/20_Projects/gamma" \
    "$FIXTURE_DIR/20_Projects/delta"

  # ── E1: missing_frontmatter (5 files) ────────────────────────────────────────
  # Files with NO frontmatter at all.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/audit-e1-missing-fm-$(printf '%03d' $i).md" <<EOF
# Audit E1 Note ${i}

This note has no frontmatter block whatsoever.
EOF
  done

  # ── E2: missing_required_fields (5 files) ────────────────────────────────────
  # Files with frontmatter but missing tags and/or type.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/audit-e2-missing-fields-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
---

# Audit E2 Note ${i}

Has created but missing tags and type.
EOF
  done

  # ── E3: filename_convention_violation (5 files) ───────────────────────────────
  # Notes with dated prefixes (violates note naming rule).
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/2026-04-audit-e3-bad-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Audit E3 Note ${i}

Non-conforming filename with date prefix.
EOF
  done

  # ── E4: broken_wikilink (5 files) ────────────────────────────────────────────
  # Files referencing stems that don't exist anywhere in the vault.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/audit-e4-broken-links-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Audit E4 Note ${i}

Links to [[audit-ghost-target-${i}]] which does not exist.
EOF
  done

  # ── E5: orphan_note (5 files) ────────────────────────────────────────────────
  # Clean notes that no other file links to (and not in project linked_notes).
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/audit-e5-orphan-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Audit E5 Orphan Note ${i}

This note exists but nothing links to it.
EOF
  done

  # ── E6: broken_project_to_note (5 entries via 1 project) ─────────────────────
  # gamma/_index.md lists 5 note stems that don't exist in 30_Notes/.
  write_file "$FIXTURE_DIR/20_Projects/gamma/_index.md" <<'EOF'
---
created: 2026-04-01
tags: [project, gamma]
type: project
status: active
linked_notes: [audit-e6-ghost-note-001, audit-e6-ghost-note-002, audit-e6-ghost-note-003, audit-e6-ghost-note-004, audit-e6-ghost-note-005]
---

# Project Gamma

Project with linked_notes pointing to nonexistent notes (E6 errors).
EOF

  # ── E7: missing_back_reference (5 files) ─────────────────────────────────────
  # delta/_index.md lists 5 notes that exist but lack project: delta back-ref.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/audit-e7-no-backref-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Audit E7 Note ${i}

Exists but has no project: delta back-reference.
EOF
  done

  write_file "$FIXTURE_DIR/20_Projects/delta/_index.md" <<'EOF'
---
created: 2026-04-01
tags: [project, delta]
type: project
status: active
linked_notes: [audit-e7-no-backref-001, audit-e7-no-backref-002, audit-e7-no-backref-003, audit-e7-no-backref-004, audit-e7-no-backref-005]
---

# Project Delta

Project where all linked notes exist but lack back-references.
EOF

  # ── E8: broken_note_to_project (5 files) ─────────────────────────────────────
  # Notes with project: field pointing to a project that has no _index.md.
  for i in $(seq 1 5); do
    write_file "$FIXTURE_DIR/30_Notes/audit-e8-bad-project-ref-$(printf '%03d' $i).md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
project: audit-nonexistent-project
---

# Audit E8 Note ${i}

Points to project 'audit-nonexistent-project' which has no _index.md.
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
    write_file "$FIXTURE_DIR/30_Notes/${name}.md" <<EOF
---
created: 2026-04-01
tags: [note]
type: note
---

# Audit Clean Note ${i}

Clean note for FP measurement. Links to [[${link_target}]].
EOF
  done

  log "  Audit error fixtures:"
  log "    E1 missing_frontmatter         : 5 files"
  log "    E2 missing_required_fields     : 5 files"
  log "    E3 filename_convention_violation: 5 files"
  log "    E4 broken_wikilink             : 5 files"
  log "    E5 orphan_note                 : 5 files"
  log "    E6 broken_project_to_note      : 5 entries (gamma/_index.md)"
  log "    E7 missing_back_reference      : 5 files (delta project)"
  log "    E8 broken_note_to_project      : 5 files"
  log "    Total seeded errors            : 40"
  log "    Extra clean notes (FP base)    : 200"
  log ""
fi

# Write mode marker so subsequent runs can detect mismatched reuse.
echo "$expected_mode" > "$MARKER_FILE"

# Print fixture path on stdout for programmatic consumption
echo "$FIXTURE_DIR"
