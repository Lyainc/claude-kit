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
  p="${p/#\~/$HOME}"
  if [[ "$p" == *".."* ]]; then
    die "Path traversal detected: $p"
  fi
  local real vault_real
  real="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$p" 2>/dev/null)" || die "Cannot resolve path: $p"
  vault_real="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$VAULT_ROOT" 2>/dev/null)" || die "Cannot resolve VAULT_ROOT"
  # Require exact match or trailing-slash boundary so /vault2/ doesn't match VAULT_ROOT=/vault.
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
        if not line.strip():
            continue
        stripped = line.lstrip()
        # List item continuation (any indent level)
        if stripped.startswith('- '):
            item = stripped[2:].strip().strip('"\'')
            if current_key and current_list is not None:
                current_list.append(item)
                result[current_key] = current_list
            continue
        m = re.match(r'^(\w[\w\-_]*)\s*:\s*(.*)', line)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip()
            if val == '' or val == '[]':
                current_list = []
                result[current_key] = current_list
            elif val.startswith('[') and val.endswith(']'):
                inner = val[1:-1]
                items = [x.strip().strip('"\'') for x in inner.split(',') if x.strip()]
                result[current_key] = items
                current_list = None
            else:
                result[current_key] = val.strip('"\'')
                current_list = None
        else:
            current_list = None

    return result

target_dir = sys.argv[1]
records = []
required_fields = {'created', 'tags', 'type'}
# status required for note/decision types only (v4 §3.3 status machine)
STATUS_REQUIRED_TYPES = frozenset({'note', 'decision'})

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
        note_type = fm.get('type', '')
        all_required = required_fields | ({'status'} if note_type in STATUS_REQUIRED_TYPES else set())
        missing = sorted(all_required - set(fm.keys()))
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

# #434: [[...]] inside a code fence or inline code is a syntax EXAMPLE, not a link.
# Left unmasked it produced 33% of E4's broken-link findings (27/82 on a 158-note vault),
# and users had no workaround — the examples were already backticked. Fences first
# (an unterminated one runs to EOF), then inline spans of any backtick run-length.
CODE_FENCE = re.compile(r'^(?P<f>```+|~~~+)[^\n]*\n.*?(?:^(?P=f)[^\n]*$|\Z)', re.S | re.M)
INLINE_CODE = re.compile(r'(?P<t>`+)(?:(?!(?P=t)).)+(?P=t)', re.S)

def mask_code(text):
    return INLINE_CODE.sub('', CODE_FENCE.sub('', text))

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
for m in WIKILINK_PATTERN.finditer(mask_code(content)):
    raw = m.group(0)
    links.append(parse_wikilink(raw))

print(json.dumps(links, indent=2, ensure_ascii=False))
PYEOF
}

# ── subcommand: infer-tags ─────────────────────────────────────────────────────
# Usage: infer-tags <file> [<file> ...]   |   infer-tags -   (paths via stdin, one per line)
#   Paths may be absolute or VAULT_ROOT-relative — a bare relative path is resolved
#   against VAULT_ROOT (NOT the current directory), so the audit runtime can pass
#   vault-relative finding paths regardless of its cwd.
# Deterministic E2 auto-fix tag proposal (#127, batched #152). No LLM. Reads each
# file's frontmatter `type:` and its path, and emits a tag PROPOSAL as JSON.
# BATCH (#152): accepts N paths in one invocation (args or stdin) and emits a
# JSON ARRAY — one object per input path — so the audit runtime spawns a single
# Python process for all E2 findings instead of one per finding. Each element:
#   {"path": "<rel>", "type": "<type|null>", "inferred_tags": [...]}
# or, on a per-file read error (same keys as success, with `error` added and
# `type: null` so callers can read `element["type"]` uniformly):
#   {"path": "<rel>", "type": null, "error": "<msg>", "inferred_tags": []}
# Three tiers (order preserved, duplicates dropped, all lowercased):
#   1) type: field        → always the first tag
#   2) filename slug       → words after stripping the date + {type}- prefix,
#                            split on `-`/`_`
#   3) parent folder       → notes/{domain}/... → add `domain`
# Empty slug (date-only filename) → type tag only (graceful, never crashes).
# The proposal is NOT auto-committed — the audit skill keeps the "수정 실행" gate.
#
# PARTIAL-FAILURE / EXIT-CODE POLICY (#152): graceful degradation is intended —
# one unreadable file must NOT abort the whole audit batch. Per-file OSErrors are
# captured in that element's `error` field (with inferred_tags: []) and the batch
# continues. Exit code is non-zero (1) ONLY when EVERY item failed (caller can
# treat that as a hard failure); a mix of ok+failed items still exits 0 so the
# successful proposals are consumed. An empty input (no paths) also exits 1.

cmd_infer_tags() {
  [[ $# -eq 0 ]] && die "infer-tags requires <file> [<file> ...] or '-' for stdin"

  # Resolve each requested path through the vault-boundary guard up front so a
  # traversal / out-of-vault path fails loudly (security), while per-file *read*
  # errors degrade gracefully inside Python (see policy above). A bare relative
  # path is resolved against VAULT_ROOT (NOT cwd) so callers can pass vault-relative
  # finding paths from any directory; absolute paths are used as-is. The guard
  # result is captured in a plain variable BEFORE the array append so `set -e`
  # propagates a validate_vault_path `die` — a command substitution failure inside
  # `arr+=(...)` is easy to overlook.
  local -a abs_files=()
  local line file candidate validated
  if [[ "$1" == "-" && $# -eq 1 ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" ]] && continue
      case "$line" in /*) candidate="$line" ;; *) candidate="$VAULT_ROOT/$line" ;; esac
      validated="$(validate_vault_path "$candidate")"
      abs_files+=("$validated")
    done
  else
    for file in "$@"; do
      [[ -z "$file" ]] && continue
      case "$file" in /*) candidate="$file" ;; *) candidate="$VAULT_ROOT/$file" ;; esac
      validated="$(validate_vault_path "$candidate")"
      abs_files+=("$validated")
    done
  fi

  python3 - "$VAULT_ROOT" "${abs_files[@]}" <<'PYEOF'
import sys, os, re, json

vault_root = os.path.realpath(os.path.expanduser(sys.argv[1]))
abs_files = sys.argv[2:]

STOPWORDS = frozenset({"the", "a", "an", "of", "and", "or", "to", "for"})
TYPE_PREFIXES = ("note", "decision", "plan", "capture", "session")

def parse_type(content):
    """Read only the `type:` scalar from the frontmatter block."""
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return None
    for line in lines[1:]:
        if line.strip() == '---':
            break
        m = re.match(r'^type\s*:\s*(.+)$', line)
        if m:
            return m.group(1).strip().strip('"\'') or None
    return None

def slug_from_filename(name):
    stem = name[:-3] if name.endswith('.md') else name
    stem = re.sub(r'^\d{4}-\d{2}(?:-\d{2})?-', '', stem)
    stem = re.sub(r'^(?:' + '|'.join(TYPE_PREFIXES) + r')-', '', stem)
    return stem

def infer_one(abs_file):
    rel = os.path.relpath(os.path.realpath(abs_file), vault_root)
    try:
        with open(abs_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except OSError as e:
        # Graceful degradation: record the failure, keep going (#152). Carry a
        # null `type` so error and success elements share one schema and callers
        # can index element["type"] without a KeyError.
        return {"path": rel, "type": None, "error": str(e), "inferred_tags": []}, False

    ftype = parse_type(content)
    tags = []

    def push(tok):
        tok = (tok or '').strip().lower()
        if not tok or tok in STOPWORDS or tok.isdigit():
            return
        if tok not in tags:
            tags.append(tok)

    # Tier 1: type.
    if ftype:
        push(ftype)

    # Tier 2: filename slug words (split on -/_).
    slug = slug_from_filename(os.path.basename(rel))
    if slug:
        for word in re.split(r'[-_]+', slug):
            push(word)

    # Tier 3: parent folder domain — only inside notes/{domain}/...
    parts = rel.split(os.sep)
    if len(parts) >= 3 and parts[0] == 'notes':
        push(parts[1])

    return {"path": rel, "type": ftype, "inferred_tags": tags}, True

results = []
ok_count = 0
for abs_file in abs_files:
    rec, ok = infer_one(abs_file)
    results.append(rec)
    if ok:
        ok_count += 1

print(json.dumps(results, ensure_ascii=False))

# Exit non-zero only when ALL items failed (or there were none): a single bad
# file must not abort the batch, so a mix of ok+failed still exits 0.
sys.exit(0 if (results and ok_count > 0) else 1)
PYEOF
}

# ── subcommand: detect-vocabulary ──────────────────────────────────────────────
# Usage: detect-vocabulary <dir>
# E9 (#119): vault-WIDE tag/property vocabulary inconsistency detection.
# Aggregates tags + frontmatter keys across the whole directory (NOT per file —
# E9 is a vault-level check) and emits one JSON object per detected pair. This is
# the RUNTIME counterpart of audit-validate.py's detect_vocabulary_pairs(); the
# two must agree (reference oracle vs production scan path). Deterministic, no LLM.
#
# Two sub-checks:
#   E9a singular/plural — a lowercase tag `t` and its regular `+s` plural `t+"s"`
#     both used. Only the literal `t+"s"` is paired → irregular plurals
#     (leaf/leaves, status/statuses) are excluded by construction.
#   E9b property naming — a frontmatter key in camelCase (`[a-z][A-Z]`) and its
#     inferred snake_case equivalent both used (`sourceUrl` ↔ `source_url`).
# FP guard (E9_MIN_FILES = 3): a pair is reported only when BOTH forms appear in
# >= 3 files (per-form file count, deduped per file). Output: JSON array of
#   {"sub": "E9a|E9b", "a": "<form>", "b": "<form>", "a_files": N, "b_files": M}
# Empty array when the vault is vocabulary-consistent.

cmd_detect_vocabulary() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && die "detect-vocabulary requires <dir>"
  local abs_dir
  abs_dir="$(validate_vault_path "$dir")"
  [[ -d "$abs_dir" ]] || die "Not a directory: $abs_dir"

  python3 - "$abs_dir" <<'PYEOF'
import sys, os, re, json

# Must match audit-validate.py: E9_MIN_FILES and the camelCase marker.
E9_MIN_FILES = 3
CAMEL_RE = re.compile(r'[a-z][A-Z]')

def parse_frontmatter(content):
    """Parse YAML frontmatter — tags list + scalar keys. Mirrors scan-frontmatter."""
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
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith('- '):
            item = stripped[2:].strip().strip('"\'')
            if current_key and current_list is not None:
                current_list.append(item)
                result[current_key] = current_list
            continue
        m = re.match(r'^(\w[\w\-_]*)\s*:\s*(.*)', line)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip()
            if val == '' or val == '[]':
                current_list = []
                result[current_key] = current_list
            elif val.startswith('[') and val.endswith(']'):
                inner = val[1:-1]
                items = [x.strip().strip('"\'') for x in inner.split(',') if x.strip()]
                result[current_key] = items
                current_list = None
            else:
                result[current_key] = val.strip('"\'')
                current_list = None
        else:
            current_list = None
    return result

def camel_to_snake(key):
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', key).lower()

target_dir = sys.argv[1]
tag_files = {}   # lowercase tag -> set(relpath)
key_files = {}   # frontmatter key -> set(relpath)

for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(root, fname)
        relpath = os.path.relpath(fpath, target_dir)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except OSError:
            continue
        fm = parse_frontmatter(content)
        raw_tags = fm.get('tags')
        if isinstance(raw_tags, list):
            for t in raw_tags:
                if isinstance(t, str) and t.strip():
                    tag_files.setdefault(t.strip().lower(), set()).add(relpath)
        for k in fm.keys():
            key_files.setdefault(k, set()).add(relpath)

pairs = []

# E9a — singular/plural tags.
seen = set()
for t in sorted(tag_files):
    plural = t + 's'
    if plural not in tag_files:
        continue
    if t in seen or plural in seen:
        continue
    if len(tag_files[t]) >= E9_MIN_FILES and len(tag_files[plural]) >= E9_MIN_FILES:
        pairs.append({'sub': 'E9a', 'a': t, 'b': plural,
                      'a_files': len(tag_files[t]), 'b_files': len(tag_files[plural])})
        seen.add(t); seen.add(plural)

# E9b — camelCase vs snake_case property keys.
# E9b: no `seen` set needed — each camelCase key has exactly one snake_case form.
for camel in sorted(key_files):
    if not CAMEL_RE.search(camel):
        continue
    snake = camel_to_snake(camel)
    if snake == camel or snake not in key_files:
        continue
    if len(key_files[camel]) >= E9_MIN_FILES and len(key_files[snake]) >= E9_MIN_FILES:
        pairs.append({'sub': 'E9b', 'a': camel, 'b': snake,
                      'a_files': len(key_files[camel]), 'b_files': len(key_files[snake])})

print(json.dumps(pairs, indent=2, ensure_ascii=False))
PYEOF
}

# ── subcommand: audit-state ────────────────────────────────────────────────────
# Usage: audit-state <is-clean|mark-clean|invalidate|list-dirty-since> [args]
#   is-clean <relpath>               → {"clean": true|false}
#   mark-clean <relpath> [<mtime>]   → {"ok": true}
#   invalidate <relpath>             → {"ok": true}
#   list-dirty-since <ISO8601>       → JSON array of dirty records
# Exit 3 = the state file exists but is unusable (unparseable, or not an object with a
#   `paths` object). The original is copied to <path>.corrupt-<ISO8601> and left in place;
#   nothing is written back. Never falls back to an empty state (#443).

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

def die_corrupt(path, reason):
    """Preserve the unusable state file and fail loudly (#443).

    The sidecar name carries a microsecond ISO8601 stamp so it never rotates —
    save_state's single `.bak` slot is overwritten by the very next write, which
    is how the original used to vanish. `path` itself is left untouched: the
    audit stays blocked until a human decides to repair or delete it.
    """
    sidecar = f"{path}.corrupt-{now_iso()}"
    shutil.copy2(path, sidecar)
    print(f"ERROR: audit-state unusable ({reason}). Original preserved at {sidecar}; "
          f"{path} left as-is. Repair or delete it, then re-run.", file=sys.stderr)
    sys.exit(3)

def load_state(path):
    if not os.path.exists(path):
        return {"version": 1, "paths": {}, "last_full_scan": None}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        die_corrupt(path, f"parse failed: {e}")
    if not isinstance(state, dict) or not isinstance(state.get('paths'), dict):
        die_corrupt(path, "shape mismatch: expected an object with a 'paths' object")
    return state

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
paths = state['paths']   # load_state guarantees a dict — no direct re-indexing below

if op == 'is-clean':
    if not arg1:
        print('ERROR: is-clean requires <relpath>', file=sys.stderr); sys.exit(1)
    rec = paths.get(arg1)
    if rec is None:
        # Unknown file — treat as dirty (untracked)
        print(json.dumps({"clean": False, "reason": "untracked"}))
    else:
        mtime = file_mtime(arg1)
        if mtime is None:
            print(json.dumps({"clean": False, "reason": "file_missing"}))
        elif mtime > rec.get('mtime_at_audit', 0):
            print(json.dumps({"clean": False, "reason": "mtime_changed",
                              "mtime": mtime, "mtime_at_audit": rec.get('mtime_at_audit', 0)}))
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
    paths[arg1] = {
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
    if arg1 in paths:
        paths[arg1]['status'] = 'dirty'
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
    for relpath, rec in paths.items():
        mtime = file_mtime(relpath)
        if mtime is None:
            dirty.append({**rec, 'path': relpath, 'reason': 'file_missing'})
            continue
        if rec.get('status') == 'dirty':
            dirty.append({**rec, 'path': relpath, 'reason': 'explicitly_invalidated', 'mtime': mtime})
            continue
        audit_ts = rec.get('mtime_at_audit', 0)
        if mtime > audit_ts:
            if since_ts is None or mtime > since_ts:
                dirty.append({**rec, 'path': relpath, 'reason': 'mtime_changed',
                              'mtime': mtime, 'mtime_at_audit': audit_ts})
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
  infer-tags)         cmd_infer_tags "$@" ;;
  detect-vocabulary)  cmd_detect_vocabulary "$@" ;;
  audit-state)        cmd_audit_state "$@" ;;
  metrics)            cmd_metrics "$@" ;;
  "")
    echo "Usage: ovm-primitives.sh <subcommand> [args]" >&2
    echo "" >&2
    echo "Subcommands:" >&2
    echo "  scan-frontmatter <dir>                      Emit JSON array of frontmatter records" >&2
    echo "  scan-filename <dir>                         Emit JSON array of filename parse results" >&2
    echo "  extract-wikilinks <file>                    Emit JSON array of wikilink targets" >&2
    echo "  infer-tags <file> [<file> ...]              Emit E2 auto-fix tag proposals as a JSON array (batched)" >&2
    echo "  infer-tags -                                ... same, reading newline-delimited paths from stdin" >&2
    echo "  detect-vocabulary <dir>                     Emit E9 tag/property vocabulary inconsistency pairs (vault-wide)" >&2
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
