#!/usr/bin/env bash
# ovm-primitives.sh — reusable bash primitives for OVM vault scanning and audit state management

set -euo pipefail

# Kill switch
if [[ "${VAULT_BRIDGE_DISABLE:-}" == "1" ]]; then
  exit 0
fi

# Priority: VAULT_ROOT (direct override, used by tests/callers) > VAULT_BRIDGE_VAULT_ROOT
# (env override) > VAULT_BRIDGE_VAULT_PATH (userConfig) > $HOME/vault (default). Mirrors
# vault-bridge/hooks/pre-write-guard.sh's chain so both plugins agree on one vault.
VAULT_ROOT="${VAULT_ROOT:-${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-$HOME/vault}}}"
VAULT_ROOT="${VAULT_ROOT/#\~/$HOME}"
AUDIT_STATE_PATH="${AUDIT_STATE_PATH:-$VAULT_ROOT/.ovm/audit-state.json}"
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

  python3 - "$abs_dir" "$VAULT_ROOT" <<'PYEOF'
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
# realpath, matching validate_vault_path's resolution of target_dir — otherwise a
# symlinked tmpdir (e.g. macOS /tmp -> /private/tmp) makes the two bases disagree and
# os.path.relpath produces a bogus ../../.. traversal instead of "notes/x.md" (#619
# e5-candidates precedent, extended here to scan-frontmatter's own --path scoping).
vault_root = os.path.realpath(os.path.expanduser(sys.argv[2]))
records = []
required_fields = {'created', 'tags', 'type', 'provenance'}
# `status` dropped from the required set — the v4 §3.3 status machine is abolished
# (v5 §5/§6, #480); /vault-save writes no status field.
# `provenance` added (v5 §4.1/§5, #477) — the existing inventory was backfilled
# from git add-commit history first, so this adds no new false positives.

for root, dirs, files in os.walk(target_dir):
    # Skip hidden dirs
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(root, fname)
        # $VAULT_ROOT-relative, not target_dir-relative (#619/#631): a --path-scoped
        # call (target_dir == "$VAULT_ROOT/notes") must still emit "notes/x.md" so
        # CLASSIFY's E5 lookup can join this array against e5-candidates' output by
        # the same key — a target_dir-relative "x.md" here silently missed every match.
        relpath = os.path.relpath(fpath, vault_root)
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

  python3 - "$abs_dir" "$VAULT_ROOT" <<'PYEOF'
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
# $VAULT_ROOT-relative basis, matching scan-frontmatter's fix (#619/#631) — see that
# function's comment for why target_dir-relative broke the CLASSIFY E5 join.
vault_root = os.path.realpath(os.path.expanduser(sys.argv[2]))
records = []

for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(root, fname)
        relpath = os.path.relpath(fpath, vault_root)
        rec = parse_filename(fname)
        rec['path'] = relpath
        records.append(rec)

print(json.dumps(records, indent=2, ensure_ascii=False))
PYEOF
}

# ── wikilink extraction: shared Python core ───────────────────────────────────
# ONE definition of the masking + parsing logic, emitted on stdin ahead of whichever
# driver needs it (#614). `extract-wikilinks` (single file) and
# `extract-wikilinks-batch` (N files, one process) both read it from here — a second
# copy of the #434 masking regexes is exactly the drift this avoids.

_wikilink_py_core() {
  cat <<'PYEOF'
import sys, os, re, json

WIKILINK_PATTERN = re.compile(r'!?\[\[([^\[\]]+)\]\]')

# #434: [[...]] inside a code fence or inline code is a syntax EXAMPLE, not a link.
# Left unmasked it produced 33% of E4's broken-link findings (27/82 on a 158-note vault),
# and users had no workaround — the examples were already backticked. Fences first
# (leading indent allowed; an unterminated one runs to EOF), then inline spans of any
# backtick run-length.
#
# Every bound below exists because over-masking is SILENT: a swallowed region stops E4
# reporting genuinely broken links (and turns their targets into fresh E5 orphans), which
# is strictly worse than the 33% FP rate being fixed — nothing surfaces to disbelieve.
#   - a closed fence may open AND close at any indent, independently (CommonMark allows
#     the closing marker its own indent; demanding column 0 made one mis-indented closer
#     swallow the rest of the file)
#   - only a column-0 fence may run to EOF unclosed; an indented one ends with its
#     containing list item or quote, so EOF would be a link-eater
#   - an inline span may cross a single newline but never a blank line, or a lone stray
#     backtick in prose pairs with the next span far below and deletes everything between
#   - a closing fence is a bare marker line (CommonMark forbids an info string there), so
#     an unclosed opener cannot pair with a LATER fence's opening line
# ponytail: four shapes still over-mask, all measured at 0 occurrences across this repo's
# 174 .md files, and all one root cause — a ``` run that CommonMark does NOT classify as a
# fence opener still reaches these patterns. Each wants a different structural fix:
#   - an INDENTED unclosed fence pairs with a later bare closer (needs a block-boundary
#     pattern per indent class)
#   - a tab-indented ``` is an indented code block to CommonMark, not a fence, but `[ \t]*`
#     reads it as one (needs column accounting, where a tab is 4 columns)
#   - a bare ``` inside a TABLE CELL (`| ``` |`) leaves an odd run for the inline pass to
#     pair with a later span, eating a link between them
#   - an UNQUOTED line carrying a link, sitting between two `>`-prefixed fence markers with
#     no blank line between them: the quoted runs leak to INLINE_CODE and pair across it.
#     NOT blockquoted fences in general — the normal layout (`> ```…> ``` `, blank line,
#     then prose) is safe, because the blank line stops the inline pass. Needs quote-prefix
#     stripping before any of this runs.
# Left as known ceilings deliberately: five of the six defects fixed on the way here were
# NEW silent false negatives introduced by tightening these patterns, so further churn for
# shapes with no
# observed occurrences is the losing side of that trade. Note the shape of the fix each
# one wants — remove a shape from the INPUT (as splitting UNCLOSED_FENCE out did), don't
# narrow a pattern further; narrowing is what kept reintroducing false negatives.
CODE_FENCE = re.compile(
    r'^[ \t]*(?P<f>```+|~~~+)[^\n]*\n.*?^[ \t]*(?P=f)(?:(?<=`)`*|(?<=~)~*)[ \t\r]*$', re.S | re.M)
UNCLOSED_FENCE = re.compile(r'^(?P<f>```+|~~~+)[^\n]*\n.*\Z', re.S | re.M)
INLINE_CODE = re.compile(r'(?P<t>`+)(?:(?!(?P=t))(?:[^\n]|\n(?!\s*\n)))+(?P=t)')

def mask_code(text):
    return INLINE_CODE.sub('', UNCLOSED_FENCE.sub('', CODE_FENCE.sub('', text)))

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

def extract_links(fpath):
    """Masked wikilink records for one file. Raises OSError on an unreadable file."""
    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return [parse_wikilink(m.group(0))
            for m in WIKILINK_PATTERN.finditer(mask_code(content))]
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

  { _wikilink_py_core; cat <<'PYEOF'
print(json.dumps(extract_links(sys.argv[1]), indent=2, ensure_ascii=False))
PYEOF
  } | python3 - "$abs_file"
}

# ── subcommand: extract-wikilinks-batch ───────────────────────────────────────
# Usage: extract-wikilinks-batch <dir>
# BATCH (#614): the audit's link index used to call `extract-wikilinks` once per .md
# file — 528 Bash round trips / ~110s on the 528-file fixture, one Python interpreter
# start each. This walks <dir> in ONE python3 process and returns the FINISHED inbound
# index, so the model neither drives the loop nor assembles the index by hand:
#   {"<target_stem>": ["<source relpath>", ...], ...}
# Vault-wide dir argument, same shape as `detect-vocabulary`/`e5-candidates`.
#
# Keys are the link target's basename, lowercased, with a trailing `.md` stripped, so
# [[Note]] / [[note.md]] / [[folder/Note|alias]] / [[note#heading]] all land on `note` —
# the same key `scan-summary.py` looks a file's own stem up by for E5 orphan detection.
# Sources are $VAULT_ROOT-relative and deduped; a file linking itself still appears (E5
# excludes self-links at lookup time, where it knows which file it is asking about).
#
# A SEPARATE subcommand, not an overload: `extract-wikilinks <file>` keeps returning its
# flat per-file array (test-wikilink-code-masking.py drives that contract by subprocess).
# Both share ONE copy of the #434 masking logic via `_wikilink_py_core`.
#
# An unreadable file is skipped, never silently: each one prints a WARN line to stderr and
# the count is repeated at the end, so a partial index announces itself. stdout stays pure
# JSON (same convention as the other dir-shaped subcommands).

cmd_extract_wikilinks_batch() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && die "extract-wikilinks-batch requires <dir>"
  local abs_dir
  abs_dir="$(validate_vault_path "$dir")"
  [[ -d "$abs_dir" ]] || die "Not a directory: $abs_dir"

  { _wikilink_py_core; cat <<'PYEOF'
target_dir = sys.argv[1]
vault_root = os.path.realpath(os.path.expanduser(sys.argv[2]))

index, unreadable = {}, []
for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(fpath, vault_root)
        try:
            links = extract_links(fpath)
        except OSError as e:
            unreadable.append('%s: %s' % (rel, e))
            continue
        for link in links:
            stem = link['target'].rsplit('/', 1)[-1].strip().lower()
            if stem.endswith('.md'):
                stem = stem[:-3]
            if not stem:
                continue
            sources = index.setdefault(stem, [])
            if rel not in sources:
                sources.append(rel)

for msg in unreadable:
    print('WARN: unreadable, not in index: %s' % msg, file=sys.stderr)
if unreadable:
    print('WARN: %d file(s) skipped — the index below is PARTIAL' % len(unreadable),
          file=sys.stderr)

print(json.dumps({k: index[k] for k in sorted(index)}, ensure_ascii=False))
PYEOF
  } | python3 - "$abs_dir" "$VAULT_ROOT"
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
#   3) first segment under notes/ → notes/{domain}/... → add `domain`
# Empty slug (date-only filename) → type tag only (graceful, never crashes).
# The proposal is NOT auto-committed — the audit skill keeps the "수정 실행" gate.
#
# PARTIAL-FAILURE / EXIT-CODE POLICY (#152): graceful degradation is intended —
# one unreadable file must NOT abort the whole audit batch. Per-file OSErrors are
# captured in that element's `error` field (with inferred_tags: []) and the batch
# continues. Exit code is non-zero (1) ONLY when EVERY item failed (caller can
# treat that as a hard failure); a mix of ok+failed items still exits 0 so the
# successful proposals are consumed. An empty input (no paths) also exits 1.

# Resolve a batch subcommand's N paths through the vault-boundary guard up front so a
# traversal / out-of-vault path fails loudly (security), while per-file *read* errors
# degrade gracefully inside Python (see the policy above). A bare relative path is
# resolved against VAULT_ROOT (NOT cwd) so callers can pass vault-relative finding paths
# from any directory; absolute paths are used as-is. The guard result is captured in a
# plain variable BEFORE the array append so `set -e` propagates a validate_vault_path
# `die` — a command substitution failure inside `arr+=(...)` is easy to overlook.
# Result lands in the global RESOLVED_BATCH_PATHS (a function cannot return an array).
# Shared by infer-tags (#152) and extract-wikilinks-batch (#614).
resolve_batch_paths() {
  RESOLVED_BATCH_PATHS=()
  local line file candidate validated
  if [[ "$1" == "-" && $# -eq 1 ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" ]] && continue
      case "$line" in /*) candidate="$line" ;; *) candidate="$VAULT_ROOT/$line" ;; esac
      validated="$(validate_vault_path "$candidate")"
      RESOLVED_BATCH_PATHS+=("$validated")
    done
  else
    for file in "$@"; do
      [[ -z "$file" ]] && continue
      case "$file" in /*) candidate="$file" ;; *) candidate="$VAULT_ROOT/$file" ;; esac
      validated="$(validate_vault_path "$candidate")"
      RESOLVED_BATCH_PATHS+=("$validated")
    done
  fi
}

cmd_infer_tags() {
  [[ $# -eq 0 ]] && die "infer-tags requires <file> [<file> ...] or '-' for stdin"
  resolve_batch_paths "$@"

  python3 - "$VAULT_ROOT" "${RESOLVED_BATCH_PATHS[@]}" <<'PYEOF'
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

    # Tier 3: first segment under notes/ — only inside notes/{domain}/...
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

# ── subcommand: e5-candidates ──────────────────────────────────────────────────
# Usage: e5-candidates <dir>
# E5 (#495, #619): orphan connection-candidate ranking, production counterpart of
# audit-validate.py's rarity-weighted scorer (the CLASSIFY-time pseudocode in
# reference/vault-audit-rules.md's `## E5` section). Deterministic, no LLM — same
# shape as detect-vocabulary: takes a dir, emits one JSON record per `.md` file.
#
# Builds a tag index over every `.md` file directly under <dir> (recursive,
# `_index.md` excluded per the E5 guard — it is never a candidate or a target),
# computes df(t) = vault-wide document frequency per tag, then for each file P
# scores every other file Q by Sum 1/log(1+df(t)) over shared tags and keeps the
# top 3. Orphan DETERMINATION (zero inbound links) stays the audit runtime's job —
# this primitive only ranks connection candidates; CLASSIFY looks up an orphan's
# entry here by path instead of hand-computing the score.
#
# Output: JSON array of {"path", "candidates": [{"path","shared_tags"}], "floor_gated"}
#   candidates == [] and floor_gated == false → no other file shares any tag with P.
#   candidates == [] and floor_gated == true  → shared tags exist, but even the best
#     match scores below E5_MIN_CANDIDATE_SCORE (too common to be a real signal).

cmd_e5_candidates() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && die "e5-candidates requires <dir>"
  local abs_dir
  abs_dir="$(validate_vault_path "$dir")"
  # A vault with no notes/ yet (sources/-only so far) is not an error — SKILL.md's Step 10
  # calls this unconditionally on every unscoped /audit, so a missing dir must degrade to
  # "no candidates" instead of dying (unlike scan-frontmatter/scan-filename, whose --path
  # argument comes from the user and a missing dir there IS worth failing loudly on).
  [[ -d "$abs_dir" ]] || { echo '[]'; return 0; }

  python3 - "$abs_dir" "$VAULT_ROOT" <<'PYEOF'
import sys, os, re, math, json

E5_MIN_CANDIDATE_SCORE = 0.5

def parse_tags(content):
    """Read only the `tags:` list from the frontmatter block."""
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return []
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == '---':
            break
        fm_lines.append(line)
    else:
        return []

    tags = []
    in_tags = False
    for line in fm_lines:
        stripped = line.lstrip()
        if stripped.startswith('- ') and in_tags:
            tags.append(stripped[2:].strip().strip('"\''))
            continue
        in_tags = False
        m = re.match(r'^tags\s*:\s*(.*)', line)
        if not m:
            continue
        val = m.group(1).strip()
        if val == '' or val == '[]':
            in_tags = True
        elif val.startswith('[') and val.endswith(']'):
            inner = val[1:-1]
            tags = [x.strip().strip('"\'') for x in inner.split(',') if x.strip()]
    return [t for t in tags if isinstance(t, str) and t.strip()]

target_dir = sys.argv[1]
# realpath, matching validate_vault_path's resolution of target_dir — otherwise a
# symlinked tmpdir (e.g. macOS /tmp -> /private/tmp) makes the two bases disagree and
# os.path.relpath produces a bogus ../../.. traversal instead of "notes/x.md".
vault_root = os.path.realpath(os.path.expanduser(sys.argv[2]))
index = []   # [(relpath, frozenset(lowercase tags))]

for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in sorted(files):
        if not fname.endswith('.md') or fname == '_index.md':
            continue
        fpath = os.path.join(root, fname)
        # Relative to VAULT_ROOT, not target_dir (#619): frontmatter_records (from
        # scan-frontmatter) keys its findings the same way, and CLASSIFY joins E5
        # orphans against this array by that key. target_dir is always
        # "$VAULT_ROOT/notes" (SKILL.md Step 10), so this yields "notes/..." paths.
        relpath = os.path.relpath(fpath, vault_root)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except OSError:
            continue
        # NOT lowercased — matches audit-validate.py's rank_e5_candidates/notes_tag_index
        # exactly (E5 does case-sensitive tag matching, unlike E9's lowercase vocabulary
        # aggregation; #619 production/oracle parity).
        tags = frozenset(t for t in parse_tags(content) if t)
        index.append((relpath, tags))

df = {}
for _, tags in index:
    for t in tags:
        df[t] = df.get(t, 0) + 1

def score(a_tags, b_tags):
    shared = a_tags & b_tags
    if not shared:
        return 0.0, shared
    return sum(1.0 / math.log(1 + df[t]) for t in shared), shared

results = []
for p_path, p_tags in index:
    scored = []
    for q_path, q_tags in index:
        if q_path == p_path:
            continue
        s, shared = score(p_tags, q_tags)
        if shared:
            scored.append((s, q_path, sorted(shared)))
    scored.sort(key=lambda x: (-x[0], x[1]))

    if not scored:
        candidates, floor_gated = [], False
    elif scored[0][0] < E5_MIN_CANDIDATE_SCORE:
        candidates, floor_gated = [], True
    else:
        candidates = [{"path": q, "shared_tags": tags} for _, q, tags in scored[:3]]
        floor_gated = False

    results.append({"path": p_path, "candidates": candidates, "floor_gated": floor_gated})

print(json.dumps(results, indent=2, ensure_ascii=False))
PYEOF
}

# ── subcommand: audit-state ────────────────────────────────────────────────────
# Usage: audit-state <is-clean|mark-clean|invalidate|list-dirty-since|stats> [args]
#   is-clean <relpath>               → {"clean": true|false}
#   mark-clean <relpath> [<mtime>]   → {"ok": true}
#   invalidate <relpath>             → {"ok": true}
#   list-dirty-since <ISO8601>       → JSON array of dirty records (walks the vault; a file
#                                       with no sidecar record gets `reason: "untracked"`)
#   stats (alias: status)            → {"total","clean","dirty","untracked","tracked_missing",
#                                       "last_full_scan"} — no scan, sidecar vs live vault only.
#                                       `status` is accepted verbatim (#619 skill flag name).
# Exit 3 = the state file exists but is unusable (unparseable, or not an object with a
#   `paths` object). The original is copied to <path>.corrupt-<ISO8601> and left in place;
#   nothing is written back. Never falls back to an empty state (#443).

cmd_audit_state() {
  local op="${1:-}"
  [[ -z "$op" ]] && die "audit-state requires an operation: is-clean|mark-clean|invalidate|list-dirty-since|stats"

  python3 - "$op" "${2:-}" "${3:-}" "$AUDIT_STATE_PATH" "$VAULT_ROOT" <<'PYEOF'
import sys, os, json, time, hashlib, shutil, glob
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

    load_state runs before op dispatch, so a per-file loop (`--reset-state` calls
    `invalidate` once per vault file) reaches this on every iteration. Identical
    bytes therefore reuse the existing sidecar instead of leaving one copy per
    call; genuinely different content still gets its own, so no evidence is lost.

    Preserving is best-effort: a read-only directory or an unreadable file must still
    end in the documented exit 3 with an honest message, never a traceback that gets
    read as "corrupt" when the real problem is permissions.
    """
    def read_bytes(p):
        with open(p, 'rb') as f:
            return f.read()

    try:
        original = read_bytes(path)
        # glob.escape: VAULT_ROOT is a user env var and a folder named `vault [backup]`
        # is legal — unescaped, `[u]` reads as a character class, no existing sidecar is
        # ever found, and the per-file storm comes straight back.
        sidecar = next(
            (p for p in sorted(glob.glob(glob.escape(path) + '.corrupt-*'))
             if os.path.isfile(p) and read_bytes(p) == original),
            None)
        if sidecar is None:
            # Colon-free (unlike now_iso(), which stays real ISO8601 for the JSON
            # last_audited field parsed elsewhere via fromisoformat): a `:`-bearing
            # filename breaks on FAT32/exFAT/NTFS-mounted vault dirs and some
            # cloud-sync tools.
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            sidecar = f"{path}.corrupt-{stamp}"
            shutil.copy2(path, sidecar)
        where = f"Original preserved at {sidecar}"
    except OSError as e:
        where = f"COULD NOT preserve a copy ({e}) — back up {path} by hand before touching it"
    print(f"ERROR: audit-state unusable ({reason}). {where}; "
          f"{path} left as-is. Recover the last good state from {path}.bak if it exists "
          f"(deleting {path} instead discards all audit state and forces a full re-scan), "
          f"then re-run.", file=sys.stderr)
    sys.exit(3)

def load_state(path):
    if not os.path.exists(path):
        return {"version": 1, "paths": {}, "last_full_scan": None}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except OSError as e:
        # Unreadable is not corrupt — say which one it is.
        die_corrupt(path, f"cannot be read: {e}")
    except Exception as e:
        die_corrupt(path, f"parse failed: {e}")
    if not isinstance(state, dict) or not isinstance(state.get('paths'), dict):
        die_corrupt(path, "shape mismatch: expected an object with a 'paths' object")
    # Per-record shape too: every op indexes into these, so one bad record would
    # otherwise still be an uncaught traceback rather than the documented exit 3.
    bad = sorted(k for k, v in state['paths'].items() if not isinstance(v, dict))
    if bad:
        die_corrupt(path, f"shape mismatch: {len(bad)} record(s) are not objects, e.g. {bad[0]!r}")
    return state

def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Rotate backup
    if os.path.exists(path):
        shutil.copy2(path, path + '.bak')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def audited_mtime(rec):
    """`mtime_at_audit` as a number, or 0 when it is missing or the wrong type.

    A record whose stamp is unusable cannot honestly claim the file is clean, so 0
    (= never audited) re-audits it. The alternative is a TypeError on the comparison,
    which is the traceback-instead-of-exit-3 failure this subcommand is done with.
    """
    v = rec.get('mtime_at_audit', 0)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0

def list_md_files(root):
    """Every `.md` relpath under root, hidden dirs skipped (mirrors scan-frontmatter)."""
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if fname.endswith('.md'):
                out.append(os.path.relpath(os.path.join(dirpath, fname), root))
    return out

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
        elif mtime > audited_mtime(rec):
            print(json.dumps({"clean": False, "reason": "mtime_changed",
                              "mtime": mtime, "mtime_at_audit": audited_mtime(rec)}))
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

    # Walk the live vault so a file with NO sidecar record (#619 "untracked") can be
    # reported at all — the old code only iterated `paths.items()`, which by definition
    # cannot see a file the sidecar has never heard of.
    live_files = list_md_files(vault_root)
    dirty = []
    for relpath in sorted(live_files):
        rec = paths.get(relpath)
        if rec is None:
            dirty.append({'path': relpath, 'reason': 'untracked'})
            continue
        mtime = file_mtime(relpath)
        if rec.get('status') == 'dirty':
            dirty.append({**rec, 'path': relpath, 'reason': 'explicitly_invalidated', 'mtime': mtime})
            continue
        audit_ts = audited_mtime(rec)
        if mtime is not None and mtime > audit_ts:
            if since_ts is None or mtime > since_ts:
                dirty.append({**rec, 'path': relpath, 'reason': 'mtime_changed',
                              'mtime': mtime, 'mtime_at_audit': audit_ts})

    # A tracked file whose bytes vanished from disk is not in live_files at all —
    # still worth reporting (`file_missing`), so check the sidecar records the walk
    # could not have surfaced.
    live_set = set(live_files)
    for relpath, rec in paths.items():
        if relpath in live_set:
            continue
        if file_mtime(relpath) is None:
            dirty.append({**rec, 'path': relpath, 'reason': 'file_missing'})

    print(json.dumps(dirty, indent=2, ensure_ascii=False))

elif op in ('stats', 'status'):
    # No scan — sidecar-vs-live-vault bookkeeping only (#619). `status` is accepted
    # verbatim as an alias since that's the name the audit skill's flag surfaces.
    live_files = list_md_files(vault_root)
    live_set = set(live_files)
    clean = dirty_n = untracked = 0
    for relpath in live_files:
        rec = paths.get(relpath)
        if rec is None:
            untracked += 1
        elif rec.get('status') == 'dirty':
            dirty_n += 1
        else:
            mtime = file_mtime(relpath)
            audit_ts = audited_mtime(rec)
            if mtime is not None and mtime > audit_ts:
                dirty_n += 1
            else:
                clean += 1
    tracked_missing = sum(
        1 for relpath in paths if relpath not in live_set and file_mtime(relpath) is None)
    print(json.dumps({
        "total": len(live_files),
        "clean": clean,
        "dirty": dirty_n,
        "untracked": untracked,
        "tracked_missing": tracked_missing,
        "last_full_scan": state.get('last_full_scan'),
    }, ensure_ascii=False))

else:
    print(f'ERROR: unknown audit-state op: {op}', file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── subcommand: metrics ────────────────────────────────────────────────────────
# Usage: metrics <start|stop|report>
# Manages timing/size metrics. State stored in /tmp/ovm-metrics-$$.json during a run.
# For pipeline use: call start before work, stop after, report to emit JSON.

# The metrics path is derived from an md5 of $VAULT_ROOT. That used to be computed at
# TOP-LEVEL scope, so EVERY subcommand invocation spawned a python3 just for the digest
# even when it never touched metrics — and the old per-file `extract-wikilinks` loop
# multiplied it by the vault's file count (#614). It is now derived inside the metrics
# python process itself, so no subcommand pays for it and `metrics` pays nothing extra.

cmd_metrics() {
  local op="${1:-}"
  [[ -z "$op" ]] && die "metrics requires an operation: start|stop|report"

  python3 - "$op" "$VAULT_ROOT" "${2:-}" <<'PYEOF'
import sys, os, json, time, hashlib

op = sys.argv[1]
vault_root = os.path.expanduser(sys.argv[2])
extra = sys.argv[3] if len(sys.argv) > 3 else ''
# Same path as before: md5(raw $VAULT_ROOT)[:8], so an in-flight metrics file from an
# older run is still found. Hash the RAW value (pre-expanduser), matching the old shell.
mfile = os.path.join(
    os.environ.get('TMPDIR') or '/tmp',
    'ovm-metrics-%s.json' % hashlib.md5(sys.argv[2].encode()).hexdigest()[:8])

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
  extract-wikilinks-batch) cmd_extract_wikilinks_batch "$@" ;;
  infer-tags)         cmd_infer_tags "$@" ;;
  detect-vocabulary)  cmd_detect_vocabulary "$@" ;;
  e5-candidates)      cmd_e5_candidates "$@" ;;
  audit-state)        cmd_audit_state "$@" ;;
  metrics)            cmd_metrics "$@" ;;
  "")
    echo "Usage: ovm-primitives.sh <subcommand> [args]" >&2
    echo "" >&2
    echo "Subcommands:" >&2
    echo "  scan-frontmatter <dir>                      Emit JSON array of frontmatter records" >&2
    echo "  scan-filename <dir>                         Emit JSON array of filename parse results" >&2
    echo "  extract-wikilinks <file>                    Emit JSON array of wikilink targets" >&2
    echo "  extract-wikilinks-batch <file> [<file> ...] Emit [{path, links}] for N files in ONE python process (#614)" >&2
    echo "  extract-wikilinks-batch -                   ... same, reading newline-delimited paths from stdin" >&2
    echo "  infer-tags <file> [<file> ...]              Emit E2 auto-fix tag proposals as a JSON array (batched)" >&2
    echo "  infer-tags -                                ... same, reading newline-delimited paths from stdin" >&2
    echo "  detect-vocabulary <dir>                     Emit E9 tag/property vocabulary inconsistency pairs (vault-wide)" >&2
    echo "  e5-candidates <dir>                          Emit E5 orphan connection-candidate ranking (rarity-weighted)" >&2
    echo "  audit-state <op> [args]                     Manage sidecar audit state" >&2
    echo "    ops: is-clean <relpath>                   Check if file is clean" >&2
    echo "         mark-clean <relpath> [mtime]         Mark file as audited clean" >&2
    echo "         invalidate <relpath>                 Mark file as dirty" >&2
    echo "         list-dirty-since <ISO8601>           List files changed since timestamp (untracked files included)" >&2
    echo "         stats (alias: status)                Sidecar-vs-vault counts, no scan" >&2
    echo "  metrics <op>                                Emit timing/size metrics as JSON" >&2
    echo "    ops: start [label]  stop  report" >&2
    exit 1
    ;;
  *)
    die "Unknown subcommand: $SUBCOMMAND. Run without args for usage."
    ;;
esac
