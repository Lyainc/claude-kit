#!/usr/bin/env bash
# ovm-primitives.sh — reusable bash primitives for OVM vault scanning and audit state management

set -euo pipefail

# Kill switch
if [[ "${VAULT_BRIDGE_DISABLE:-}" == "1" ]]; then
  exit 0
fi

VAULT_ROOT="${VAULT_ROOT:-$HOME/vault}"
AUDIT_STATE_PATH="${AUDIT_STATE_PATH:-$HOME/vault/.ovm/audit-state.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── helpers ────────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "$*" >&2; }

# Validate that a path is under VAULT_ROOT and contains no traversal
validate_vault_path() {
  local p="$1"
  # Expand ~ if present
  p="${p/#\~/$HOME}"
  # Resolve to absolute
  local real
  real="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$p" 2>/dev/null)" || die "Cannot resolve path: $p"
  local vault_real
  vault_real="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$VAULT_ROOT" 2>/dev/null)" || die "Cannot resolve VAULT_ROOT"
  # Check no .. traversal in original
  if [[ "$p" == *".."* ]]; then
    die "Path traversal detected: $p"
  fi
  # Check prefix — require exact match or trailing-slash boundary
  # to avoid matching sibling dirs like /vault2/ when VAULT_ROOT=/vault.
  if [[ "$real" != "$vault_real" && "$real" != "$vault_real"/* ]]; then
    die "Path '$real' is not under VAULT_ROOT '$vault_real'"
  fi
  echo "$real"
}

# ── subcommand: scan-frontmatter ───────────────────────────────────────────────
# Usage: scan-frontmatter <dir>
# Emits one JSON object per .md file with parsed YAML frontmatter fields.
# Output: JSON array on stdout

cmd_scan_frontmatter() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && die "scan-frontmatter requires <dir>"
  local abs_dir
  abs_dir="$(validate_vault_path "$dir")"
  [[ -d "$abs_dir" ]] || die "Not a directory: $abs_dir"

  python3 - "$abs_dir" <<'PYEOF'
import sys, os, re, json

def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown content. Returns dict of key:value."""
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == '---':
            break
        fm_lines.append(line)
    else:
        return {}  # no closing ---

    result = {}
    current_key = None
    current_list = None

    for line in fm_lines:
        # Skip blank lines
        if not line.strip():
            continue
        # List item continuation
        if line.startswith('  - ') or line.startswith('- '):
            item = line.strip().lstrip('- ').strip()
            # strip quotes
            item = item.strip('"\'')
            if current_key and current_list is not None:
                current_list.append(item)
                result[current_key] = current_list
            continue
        # Key: value line
        m = re.match(r'^(\w[\w\-_]*)\s*:\s*(.*)', line)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip()
            if val == '' or val == '[]':
                current_list = []
                result[current_key] = current_list
            elif val.startswith('[') and val.endswith(']'):
                # inline list
                inner = val[1:-1]
                items = [x.strip().strip('"\'') for x in inner.split(',') if x.strip()]
                result[current_key] = items
                current_list = None
            else:
                # scalar — strip quotes
                result[current_key] = val.strip('"\'')
                current_list = None
        else:
            current_list = None

    return result

target_dir = sys.argv[1]
records = []
required_fields = {'created', 'tags', 'type'}

for root, dirs, files in os.walk(target_dir):
    # Skip hidden dirs
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(root, fname)
        relpath = os.path.relpath(fpath, target_dir)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            records.append({'path': relpath, 'error': str(e), 'frontmatter': {}})
            continue

        fm = parse_frontmatter(content)
        missing = sorted(required_fields - set(fm.keys()))
        stat = os.stat(fpath)

        records.append({
            'path': relpath,
            'frontmatter': fm,
            'missing_required': missing,
            'has_frontmatter': bool(fm),
            'mtime': int(stat.st_mtime),
            'size_bytes': stat.st_size
        })

print(json.dumps(records, indent=2, ensure_ascii=False))
PYEOF
}

# ── subcommand: scan-filename ──────────────────────────────────────────────────
# Usage: scan-filename <dir>
# Emits JSON array with filename parse results: type/date/topic/version, conformance flag.

cmd_scan_filename() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && die "scan-filename requires <dir>"
  local abs_dir
  abs_dir="$(validate_vault_path "$dir")"
  [[ -d "$abs_dir" ]] || die "Not a directory: $abs_dir"

  python3 - "$abs_dir" <<'PYEOF'
import sys, os, re, json

# Valid types per vault spec
VALID_TYPES = {'session', 'capture', 'note', 'project', 'plan'}

# Patterns:
#   {type}-YYYY-MM-DD[-{topic}][-vN].md  (session, capture, plan)
#   {topic}.md                            (note — flat, no date prefix)
#   _index.md                             (project container)
DATED_PATTERN = re.compile(
    r'^(?P<type>[a-z]+)-(?P<date>\d{4}-\d{2}-\d{2})(?:-(?P<topic>[^.]+?))?(?:-(?P<version>v\d+))?\.md$'
)
NOTE_PATTERN = re.compile(r'^(?P<topic>[a-z][a-z0-9\-]*)\.md$')

def parse_filename(fname):
    if fname == '_index.md':
        return {
            'filename': fname,
            'type': 'project',
            'date': None,
            'topic': None,
            'version': None,
            'conforms': True,
            'violation': None
        }

    m = DATED_PATTERN.match(fname)
    if m:
        ftype = m.group('type')
        valid = ftype in VALID_TYPES
        violation = None if valid else f"unknown type '{ftype}'"
        return {
            'filename': fname,
            'type': ftype,
            'date': m.group('date'),
            'topic': m.group('topic'),
            'version': m.group('version'),
            'conforms': valid,
            'violation': violation
        }

    m = NOTE_PATTERN.match(fname)
    if m:
        return {
            'filename': fname,
            'type': 'note',
            'date': None,
            'topic': m.group('topic'),
            'version': None,
            'conforms': True,
            'violation': None
        }

    return {
        'filename': fname,
        'type': None,
        'date': None,
        'topic': None,
        'version': None,
        'conforms': False,
        'violation': 'does not match any known filename convention'
    }

target_dir = sys.argv[1]
records = []

for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(root, fname)
        relpath = os.path.relpath(fpath, target_dir)
        rec = parse_filename(fname)
        rec['path'] = relpath
        records.append(rec)

print(json.dumps(records, indent=2, ensure_ascii=False))
PYEOF
}

# ── subcommand: extract-wikilinks ─────────────────────────────────────────────
# Usage: extract-wikilinks <file>
# Emits JSON array of link target strings from [[...]] / ![[...]] syntax.

cmd_extract_wikilinks() {
  local file="${1:-}"
  [[ -z "$file" ]] && die "extract-wikilinks requires <file>"
  local abs_file
  abs_file="$(validate_vault_path "$file")"
  [[ -f "$abs_file" ]] || die "Not a file: $abs_file"

  python3 - "$abs_file" <<'PYEOF'
import sys, re, json

WIKILINK_PATTERN = re.compile(r'!?\[\[([^\[\]]+)\]\]')

def parse_wikilink(raw):
    """Parse [[target]], [[target|alias]], [[target#heading]], [[note#^block]]."""
    # Strip embed prefix
    embed = raw.startswith('!')
    inner = raw.lstrip('!')
    # Remove [[ ]]
    inner = inner[2:-2]
    # Split alias
    if '|' in inner:
        target, alias = inner.split('|', 1)
    else:
        target, alias = inner, None
    # Split heading/block
    heading = None
    block_ref = None
    if '#^' in target:
        target, block_ref = target.split('#^', 1)
    elif '#' in target:
        target, heading = target.split('#', 1)
    return {
        'raw': raw,
        'target': target.strip(),
        'alias': alias,
        'heading': heading,
        'block_ref': block_ref,
        'embed': embed
    }

fpath = sys.argv[1]
with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

links = []
for m in WIKILINK_PATTERN.finditer(content):
    raw = m.group(0)
    links.append(parse_wikilink(raw))

print(json.dumps(links, indent=2, ensure_ascii=False))
PYEOF
}

# ── subcommand: audit-state ────────────────────────────────────────────────────
# Usage: audit-state <is-clean|mark-clean|invalidate|list-dirty-since> [args]
#   is-clean <relpath>               → {"clean": true|false}
#   mark-clean <relpath> [<mtime>]   → {"ok": true}
#   invalidate <relpath>             → {"ok": true}
#   list-dirty-since <ISO8601>       → JSON array of dirty records

cmd_audit_state() {
  local op="${1:-}"
  [[ -z "$op" ]] && die "audit-state requires an operation: is-clean|mark-clean|invalidate|list-dirty-since"

  python3 - "$op" "${2:-}" "${3:-}" "$AUDIT_STATE_PATH" "$VAULT_ROOT" <<'PYEOF'
import sys, os, json, time, hashlib, shutil
from datetime import datetime, timezone

op = sys.argv[1]
arg1 = sys.argv[2]
arg2 = sys.argv[3]
state_path = sys.argv[4]
vault_root = os.path.expanduser(sys.argv[5])

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_state(path):
    if not os.path.exists(path):
        return {"version": 1, "paths": {}, "last_full_scan": None}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: audit-state corrupted ({e}), returning empty state", file=sys.stderr)
        return {"version": 1, "paths": {}, "last_full_scan": None}

def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Rotate backup
    if os.path.exists(path):
        shutil.copy2(path, path + '.bak')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def file_mtime(relpath):
    fpath = os.path.join(vault_root, relpath)
    if not os.path.exists(fpath):
        return None
    return int(os.stat(fpath).st_mtime)

def content_hash(relpath):
    fpath = os.path.join(vault_root, relpath)
    if not os.path.exists(fpath):
        return None
    h = hashlib.sha256()
    with open(fpath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()[:16]

state = load_state(state_path)

if op == 'is-clean':
    if not arg1:
        print('ERROR: is-clean requires <relpath>', file=sys.stderr); sys.exit(1)
    rec = state['paths'].get(arg1)
    if rec is None:
        # Unknown file — treat as dirty (untracked)
        print(json.dumps({"clean": False, "reason": "untracked"}))
    else:
        mtime = file_mtime(arg1)
        if mtime is None:
            print(json.dumps({"clean": False, "reason": "file_missing"}))
        elif mtime > rec.get('mtime_at_audit', 0):
            print(json.dumps({"clean": False, "reason": "mtime_changed",
                              "mtime": mtime, "mtime_at_audit": rec['mtime_at_audit']}))
        else:
            print(json.dumps({"clean": True, "last_audited": rec.get('last_audited'),
                              "status": rec.get('status', 'clean')}))

elif op == 'mark-clean':
    if not arg1:
        print('ERROR: mark-clean requires <relpath>', file=sys.stderr); sys.exit(1)
    mtime = int(arg2) if arg2 else file_mtime(arg1)
    if mtime is None:
        print('ERROR: file not found and no mtime provided', file=sys.stderr); sys.exit(1)
    chash = content_hash(arg1)
    state['paths'][arg1] = {
        'last_audited': now_iso(),
        'mtime_at_audit': mtime,
        'content_hash': chash,
        'status': 'clean'
    }
    save_state(state_path, state)
    print(json.dumps({"ok": True, "path": arg1, "mtime_at_audit": mtime}))

elif op == 'invalidate':
    if not arg1:
        print('ERROR: invalidate requires <relpath>', file=sys.stderr); sys.exit(1)
    if arg1 in state['paths']:
        state['paths'][arg1]['status'] = 'dirty'
        save_state(state_path, state)
    print(json.dumps({"ok": True, "path": arg1}))

elif op == 'list-dirty-since':
    # arg1 is ISO8601 timestamp (optional; if absent list all dirty/untracked)
    since_ts = None
    if arg1:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(arg1.replace('Z', '+00:00'))
            since_ts = dt.timestamp()
        except ValueError:
            print(f'ERROR: invalid ISO8601 timestamp: {arg1}', file=sys.stderr); sys.exit(1)

    dirty = []
    for relpath, rec in state['paths'].items():
        mtime = file_mtime(relpath)
        if mtime is None:
            dirty.append({'path': relpath, 'reason': 'file_missing', **rec})
            continue
        if rec.get('status') == 'dirty':
            dirty.append({'path': relpath, 'reason': 'explicitly_invalidated', 'mtime': mtime, **rec})
            continue
        audit_ts = rec.get('mtime_at_audit', 0)
        if mtime > audit_ts:
            if since_ts is None or mtime > since_ts:
                dirty.append({'path': relpath, 'reason': 'mtime_changed',
                              'mtime': mtime, 'mtime_at_audit': audit_ts, **rec})
    print(json.dumps(dirty, indent=2, ensure_ascii=False))

else:
    print(f'ERROR: unknown audit-state op: {op}', file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── subcommand: metrics ────────────────────────────────────────────────────────
# Usage: metrics <start|stop|report>
# Manages timing/size metrics. State stored in /tmp/ovm-metrics-$$.json during a run.
# For pipeline use: call start before work, stop after, report to emit JSON.

METRICS_FILE="${TMPDIR:-/tmp}/ovm-metrics-$(python3 -c "import hashlib,sys; print(hashlib.md5(sys.argv[1].encode()).hexdigest()[:8])" "${VAULT_ROOT:-$HOME/vault}").json"

cmd_metrics() {
  local op="${1:-}"
  [[ -z "$op" ]] && die "metrics requires an operation: start|stop|report"

  python3 - "$op" "$METRICS_FILE" "$VAULT_ROOT" "${2:-}" <<'PYEOF'
import sys, os, json, time

op = sys.argv[1]
mfile = sys.argv[2]
vault_root = os.path.expanduser(sys.argv[3])
extra = sys.argv[4] if len(sys.argv) > 4 else ''

def load_metrics(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def save_metrics(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

if op == 'start':
    data = {
        'start_time': time.time(),
        'stop_time': None,
        'elapsed_ms': None,
        'vault_root': vault_root,
        'note_count': None,
        'vault_size_bytes': None,
        'label': extra or 'unnamed'
    }
    # Count notes and total size
    note_count = 0
    total_bytes = 0
    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.endswith('.md'):
                note_count += 1
                try:
                    total_bytes += os.stat(os.path.join(root, f)).st_size
                except Exception:
                    pass
    data['note_count'] = note_count
    data['vault_size_bytes'] = total_bytes
    save_metrics(mfile, data)
    print(json.dumps({"ok": True, "start_time": data['start_time'],
                      "note_count": note_count, "vault_size_bytes": total_bytes}))

elif op == 'stop':
    data = load_metrics(mfile)
    if not data:
        print('ERROR: no metrics session started', file=sys.stderr); sys.exit(1)
    data['stop_time'] = time.time()
    data['elapsed_ms'] = int((data['stop_time'] - data['start_time']) * 1000)
    save_metrics(mfile, data)
    print(json.dumps({"ok": True, "elapsed_ms": data['elapsed_ms']}))

elif op == 'report':
    data = load_metrics(mfile)
    if not data:
        print(json.dumps({"error": "no metrics data"})); sys.exit(0)
    print(json.dumps(data, indent=2))

else:
    print(f'ERROR: unknown metrics op: {op}', file=sys.stderr); sys.exit(1)
PYEOF
}

# ── dispatch ───────────────────────────────────────────────────────────────────

SUBCOMMAND="${1:-}"
shift || true

case "$SUBCOMMAND" in
  scan-frontmatter)   cmd_scan_frontmatter "$@" ;;
  scan-filename)      cmd_scan_filename "$@" ;;
  extract-wikilinks)  cmd_extract_wikilinks "$@" ;;
  audit-state)        cmd_audit_state "$@" ;;
  metrics)            cmd_metrics "$@" ;;
  "")
    echo "Usage: ovm-primitives.sh <subcommand> [args]" >&2
    echo "" >&2
    echo "Subcommands:" >&2
    echo "  scan-frontmatter <dir>                      Emit JSON array of frontmatter records" >&2
    echo "  scan-filename <dir>                         Emit JSON array of filename parse results" >&2
    echo "  extract-wikilinks <file>                    Emit JSON array of wikilink targets" >&2
    echo "  audit-state <op> [args]                     Manage sidecar audit state" >&2
    echo "    ops: is-clean <relpath>                   Check if file is clean" >&2
    echo "         mark-clean <relpath> [mtime]         Mark file as audited clean" >&2
    echo "         invalidate <relpath>                 Mark file as dirty" >&2
    echo "         list-dirty-since <ISO8601>           List files changed since timestamp" >&2
    echo "  metrics <op>                                Emit timing/size metrics as JSON" >&2
    echo "    ops: start [label]  stop  report" >&2
    exit 1
    ;;
  *)
    die "Unknown subcommand: $SUBCOMMAND. Run without args for usage."
    ;;
esac
