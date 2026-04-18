#!/usr/bin/env bash
# gen-fixture.sh — synthesize a test vault fixture under /tmp/ovm-fixture-*/

set -euo pipefail

if [[ "${VAULT_BRIDGE_DISABLE:-}" == "1" ]]; then
  exit 0
fi

FIXTURE_DIR="${OVM_FIXTURE_DIR:-/tmp/ovm-fixture-$$}"

# Allow reuse of an existing fixture dir (for testing stability)
if [[ -d "$FIXTURE_DIR" ]]; then
  echo "Fixture already exists at $FIXTURE_DIR" >&2
  echo "$FIXTURE_DIR"
  exit 0
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

# Print fixture path on stdout for programmatic consumption
echo "$FIXTURE_DIR"
