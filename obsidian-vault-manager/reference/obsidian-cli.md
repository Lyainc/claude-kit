# Obsidian CLI Reference

Use this reference when a workflow can benefit from a running Obsidian instance. The CLI is optional; every skill must gracefully fall back to raw file I/O or existing shell search when `obsidian` is unavailable or a command fails.

Sources: Obsidian — [CLI overview](https://obsidian.md/cli); kepano/obsidian-skills — [obsidian-cli skill](https://github.com/kepano/obsidian-skills/blob/main/skills/obsidian-cli/SKILL.md).

## Availability gate and timeout helper

macOS does not ship GNU `timeout` by default. Detect a usable timeout binary first; if none exists, run the CLI without a wrapper but keep the rest of the gate.

```bash
# Detect timeout helper (GNU timeout, or gtimeout from Homebrew coreutils)
if command -v timeout >/dev/null 2>&1; then
  OBSIDIAN_TO="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  OBSIDIAN_TO="gtimeout"
else
  OBSIDIAN_TO=""   # no timeout helper available; CLI runs unwrapped
fi

# Probe binary + responsiveness
if command -v obsidian >/dev/null 2>&1 \
   && ${OBSIDIAN_TO:+$OBSIDIAN_TO 3} obsidian help >/dev/null 2>&1; then
  echo "obsidian-cli-ready"
else
  echo "fallback"
fi
```

Use `$OBSIDIAN_TO` (with the appropriate seconds) as a prefix on every CLI call:

```bash
${OBSIDIAN_TO:+$OBSIDIAN_TO 10} obsidian search query="..." limit=20
${OBSIDIAN_TO:+$OBSIDIAN_TO 5}  obsidian property:set name="..." value="..." path="..."
```

The `${VAR:+...}` form expands to the value only when `$VAR` is non-empty, so the command runs unwrapped on macOS hosts without `timeout`/`gtimeout`. **Never hard-code `timeout` directly in skills** — that breaks on default macOS where `timeout` is `command not found`.

Suggested durations: 3s for `help` probes, 10s for `search`/`read`, 5s for `property:set`. Skip the wrapper entirely when neither helper is installed; Obsidian normally responds in milliseconds, and a hang only matters in the rare case the app is stuck.

Rules:

1. Never require the CLI for correctness.
2. Never install the CLI from a skill.
3. Use the CLI only when Obsidian is open and the command succeeds.
4. On any non-zero exit (including timeout-induced 124), retry with the existing filesystem fallback.
5. Keep paths vault-relative when using `path=...`.
6. Quote parameter values that contain spaces.
7. Detect the timeout helper as shown above; do not assume `timeout` is on PATH.

## Command syntax

Parameters use `key=value`:

```bash
obsidian search query="meeting notes" limit=10
obsidian read path="10_MOC/kubernetes.md"
obsidian property:set name="status" value="archived" path="20_Projects/foo/_index.md"
```

Boolean flags are passed without values when needed. Use `obsidian help` for the current command list.

## Common OVM patterns

| Workflow | CLI-first command | Fallback |
| --- | --- | --- |
| Read a known note | `obsidian read path="10_MOC/{domain}.md"` | Read tool / `cat` |
| Search vault text | `obsidian search query="{term}" limit={N}` (add `path="{folder}"` to scope) | `mdfind` on macOS, `grep -rl` elsewhere |
| Scoped search (e.g. `.vault-link`) | `obsidian search query="{term}" path="{vault_path}" limit={N}` | `mdfind -onlyin {scoped_path}` / `grep -rl ... {scoped_path}` |
| Archive project status | `obsidian property:set name="status" value="archived" path="20_Projects/{name}/_index.md"` | Edit YAML frontmatter directly |
| Add archive date | `obsidian property:set name="archived" value="YYYY-MM-DD" type=date path="20_Projects/{name}/_index.md"` | Edit YAML frontmatter directly |
| Daily append (future skill) | `obsidian daily:append content="..."` | Write/Edit daily note file |

`property:set` accepts `type=text|list|number|checkbox|date|datetime`. Always pass `type=date` (or `type=datetime`) when the value is an ISO date so Obsidian Properties and Dataview recognize the field correctly. Defaults to `text` when omitted, which silently breaks date queries.

`search` accepts `path=<folder>` to restrict results to a vault-relative subtree (e.g. `path="20_Projects/{name}"`). Use this whenever a workflow has narrowed the search root via `.vault-link` instead of falling back to filesystem search.

`search` also accepts `format=text|json`. Prefer `format=json` when the caller needs machine-parseable results (paths + line numbers) rather than human-readable previews.

## Scope and liveness notes

- The CLI targets the active vault. If the user runs multiple vaults, pass `vault=<name>` to disambiguate.
- The CLI is only useful while the Obsidian app is running; the availability gate above (with `timeout`) catches both "binary missing" and "app not responding" cases.
- Inside `.vault-link` scoped searches, prefer the `path=` parameter over manifest/filesystem fallback when CLI is available — manifest stays as the second tier and `mdfind`/`grep` as the third.

## User-facing behavior

Do not mention CLI availability unless it affects the outcome. If the CLI path fails and fallback succeeds, report the normal successful result only.
