# OVM Scripts — Primitives CLI

Reusable bash primitives for OVM vault scanning and audit state management.
All output is valid JSON on stdout; human-readable progress goes to stderr.

## Requirements

- bash 3.2+
- python3 (stdlib only — `json`, `re`, `os`, `hashlib`, `shutil`)
- No external dependencies (no jq, no PyYAML, no node)

## Kill Switch

Set `VAULT_BRIDGE_DISABLE=1` to make all scripts exit 0 silently.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VAULT_ROOT` | `~/vault` | Root of the Obsidian vault |
| `AUDIT_STATE_PATH` | `~/vault/.ovm/audit-state.json` | Sidecar audit state file |

---

## `ovm-primitives.sh`

Single entry point with five subcommands.

```
bash ovm-primitives.sh <subcommand> [args]
```

### `scan-frontmatter <dir>`

Walk `<dir>` recursively, parse YAML frontmatter from every `.md` file, emit a JSON array.

```bash
bash ovm-primitives.sh scan-frontmatter ~/vault/30_Notes
```

**Output schema** (one element per file):

```json
[
  {
    "path": "relative/path.md",
    "frontmatter": { "created": "2026-04-01", "tags": ["note"], "type": "note", "provenance": "..." },
    "missing_required": [],
    "has_frontmatter": true,
    "mtime": 1713571200,
    "size_bytes": 420
  }
]
```

`missing_required` lists any of `{created, tags, type, provenance}` absent from the frontmatter.

### `scan-filename <dir>`

Walk `<dir>` recursively, parse each `.md` filename against the vault naming convention, emit a JSON array.

**Naming convention** (from vault spec):

| Type | Pattern |
|---|---|
| `session`, `capture`, `plan` | `{type}-YYYY-MM-DD[-{topic}][-vN].md` |
| `note` | `{topic-kebab}.md` (flat, no date prefix) |
| `project` | `_index.md` (fixed) |

```bash
bash ovm-primitives.sh scan-filename ~/vault
```

**Output schema** (one element per file):

```json
[
  {
    "path": "30_Notes/api-design.md",
    "filename": "api-design.md",
    "type": "note",
    "date": null,
    "topic": "api-design",
    "version": null,
    "conforms": true,
    "violation": null
  }
]
```

`conforms: false` + `violation: "<reason>"` when the filename does not match any pattern.

### `extract-wikilinks <file>`

Parse all `[[...]]` and `![[...]]` links from a single file, emit a JSON array.

Handles: `[[note]]`, `[[note|alias]]`, `[[note#heading]]`, `[[note#^block]]`, `![[embed]]`.

```bash
bash ovm-primitives.sh extract-wikilinks ~/vault/30_Notes/my-note.md
```

**Output schema**:

```json
[
  {
    "raw": "[[api-design|API Design]]",
    "target": "api-design",
    "alias": "API Design",
    "heading": null,
    "block_ref": null,
    "embed": false
  }
]
```

### `audit-state <op> [args]`

Manage the sidecar index at `~/vault/.ovm/audit-state.json`.
"Dirty" means the file's current mtime > `mtime_at_audit`.

**Sidecar schema**:

```json
{
  "version": 1,
  "paths": {
    "<relpath>": {
      "last_audited": "2026-04-18T00:00:00+00:00",
      "mtime_at_audit": 1713571200,
      "content_hash": "abcd1234abcd1234",
      "status": "clean|dirty"
    }
  },
  "last_full_scan": null
}
```

A `.bak` file is written before every save (one-rotation backup).

**Exit 3 — unusable state file** (#443). Every op loads the state file before dispatch, so
any of them can hit this. If `audit-state.json` exists but cannot be used (unparseable, or
not an object with a `paths` object), the original is copied to
`audit-state.json.corrupt-<ISO8601>`, `audit-state.json` itself is left untouched, nothing
is written back, and the command exits 3. Identical content reuses one sidecar rather than
adding a copy per call, so a per-file loop does not litter; different content still gets its
own. It never falls back to an empty state. Recover from `.bak` (the last good state) —
deleting `audit-state.json` also works but discards all audit state and forces a full re-scan.

#### `is-clean <relpath>`

```bash
bash ovm-primitives.sh audit-state is-clean 30_Notes/api-design.md
# {"clean": true, "last_audited": "2026-04-18T00:00:00+00:00", "status": "clean"}
# {"clean": false, "reason": "mtime_changed", "mtime": 1713571300, "mtime_at_audit": 1713571200}
# {"clean": false, "reason": "untracked"}
```

#### `mark-clean <relpath> [mtime]`

Record a file as audited-clean. If `mtime` is omitted, reads the file's current mtime.

```bash
bash ovm-primitives.sh audit-state mark-clean 30_Notes/api-design.md
# {"ok": true, "path": "30_Notes/api-design.md", "mtime_at_audit": 1713571200}
```

#### `invalidate <relpath>`

Force a file to dirty status (e.g., after a failed audit).

```bash
bash ovm-primitives.sh audit-state invalidate 30_Notes/api-design.md
# {"ok": true, "path": "30_Notes/api-design.md"}
```

#### `list-dirty-since <ISO8601>`

List all records where `mtime > mtime_at_audit` and `mtime > <timestamp>`.
Omit the timestamp to list all dirty records.

```bash
bash ovm-primitives.sh audit-state list-dirty-since 2026-04-18T00:00:00+00:00
# JSON array of dirty records
```

### `metrics <op>`

Emit timing and vault-size metrics as JSON. Designed for wrapping a pipeline run.

```bash
bash ovm-primitives.sh metrics start "inbox-review-run"
# ... do work ...
bash ovm-primitives.sh metrics stop
bash ovm-primitives.sh metrics report
```

**Report output schema**:

```json
{
  "start_time": 1713571200.123,
  "stop_time": 1713571205.456,
  "elapsed_ms": 5333,
  "note_count": 300,
  "vault_size_bytes": 1048576,
  "label": "inbox-review-run"
}
```

---

## `manifest-summary.py` / `manifest-wiki-match.py`

Filter `~/vault/.vault-bridge/manifest.json` server-side before it ever reaches the model
(#468, mirrors feedback-loop's retired `e8-candidates.py` pattern from #460). The harness
truncates large Bash output to a 2 KB preview — a raw `cat` of a real manifest (100+ KB) would
silently degrade to whichever few entries survive the cut. Both scripts read the full file on
disk and print only the fields their caller needs.

```bash
python3 manifest-summary.py [MANIFEST_PATH]      # audit/SKILL.md REPORT header
# {"file_count": N, "generated_at": "..."}

python3 manifest-wiki-match.py [MANIFEST_PATH]   # wiki/SKILL.md Phase 3 DEDUP
# {"scanned": N, "wiki_entries": [{path, title, tags}, ...]}
```

Both default `MANIFEST_PATH` to `<vault root>/.vault-bridge/manifest.json` (`VAULT_BRIDGE_VAULT_ROOT` → `VAULT_BRIDGE_VAULT_PATH` → `~/vault`) and exit 3 — with nothing on stdout — when the manifest is absent, unparseable, or malformed; callers must not fall back to a raw `cat`.

---

## `test/gen-fixture.sh`

Synthesize a test vault fixture under `/tmp/ovm-fixture-$$/`.

```bash
bash test/gen-fixture.sh
# prints fixture path to stdout
# /tmp/ovm-fixture-12345

# Use a fixed path for repeatable tests:
OVM_FIXTURE_DIR=/tmp/ovm-test bash test/gen-fixture.sh
```

**Fixture contents** (~300 notes, 30 intentional issues):

| Directory | Contents |
|---|---|
| `00_Inbox/` | 30 captures + 10 sessions |
| `20_Projects/alpha/` | `_index.md` + 5 plans |
| `20_Projects/beta/` | `_index.md` + 3 sessions (with broken links) |
| `30_Notes/` | 200 clean notes + 30 issues |

**Injected issues**:

| Issue type | Count |
|---|---|
| Missing frontmatter entirely | 5 |
| Non-conforming filename | 5 |
| Broken wikilinks (target does not exist) | 5 |
| Missing required fields (tags, type) | 5 |
| Orphan notes (no inbound links) | 10 |

The fixture also seeds `/.ovm/audit-state.json` with 100 pre-audited records
to enable incremental-scan benchmarks.

---

## `test/baseline-measure.sh`

Benchmark all primitives against the fixture and emit a JSON timing report to stdout.

```bash
bash test/baseline-measure.sh
# emits JSON report with timing data

# Use existing fixture:
OVM_FIXTURE_DIR=/tmp/ovm-test bash test/baseline-measure.sh
```

**Report schema**:

```json
{
  "measured_at": "2026-04-19T...",
  "fixture": "/tmp/ovm-fixture-12345",
  "vault_stats": {
    "note_count": 293,
    "vault_size_bytes": 491520,
    "ms_per_note_scan_frontmatter": 0.12,
    "ms_per_note_scan_filename": 0.08
  },
  "timings_ms": {
    "scan_frontmatter_full_vault": 35,
    "scan_filename_full_vault": 25,
    "extract_wikilinks_single_file": 20,
    "audit_state_mark_clean_avg_per_file": 4,
    "audit_state_list_dirty_since": 15,
    "metrics_start": 30,
    "metrics_stop": 5,
    "metrics_report": 5
  }
}
```

---

## Input Validation Rules

- All `<dir>` and `<file>` paths must be under `VAULT_ROOT`
- Paths containing `..` are rejected immediately
- Non-existent paths produce an error on stderr and exit 1
- Sidecar JSON corruption is detected and falls back to an empty state (with a warning on stderr)
