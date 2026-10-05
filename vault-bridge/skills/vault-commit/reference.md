# vault-commit — reference detail

Rationale and edge-case detail moved out of `SKILL.md` (Codex truncates an invoked SKILL.md at 8,000 bytes, #750).
Approval gates and prohibitions stay in `SKILL.md`; this file only refines them.

## Step 1 — vault-absent message rationale (#763)

`VAULT_ABSENT` stops here because Step 2's "not a git repository" would misname the cause.

## Step 5 — large change sets

**When `{N}` ≥ 10, list the counts per path group above the file list** — a 30-line file list is scrolled past, not read, and the approval stops being a real one:

```
wiki/ 23 · notes/ 2 · sources/ 4 · .obsidian/ 2 · 기타 1
```

## Step 6 Option B — grouping detail

Grouping is **deterministic — the first path segment, nothing else** (`wiki/`, `notes/`, `sources/`, `assets/`, `.obsidian/`, …). Never group by reading file *content*: the same staged set must produce the same commits on every run.

**A top-level file (no `/` in its path) has no directory prefix**, so it cannot be staged by one. Those files form a final group named `기타` whose pathspec is the **explicit list of its members**, never the label itself — `add -- 기타` fails with `fatal: pathspec '기타' did not match any files` and, by the stop-on-failure rule, aborts the whole split.

Why the order matters: read the groups off the still-staged set (`diff --cached --name-only`) **before** `reset HEAD` un-stages anything. Running the listing after the reset returns nothing, and the `기타` group then vanishes from the plan with no error — top-level files would be silently left out of every commit.

Per-group staging: `{group_pathspec}` is the directory prefix for a normal group; for `기타` it is the recorded member paths, **each passed as its own quoted argument** — vault filenames contain spaces and Hangul, and an unquoted list splits one name into two bad pathspecs:

```bash
# the add line takes ONE of these two forms, depending on the group:
git -C "{vault_root}" add -A -- "wiki/"                      # normal group: the prefix
git -C "{vault_root}" add -A -- "README.md" "2026 계획.md"    # 기타: each member, quoted

git -C "{vault_root}" -c core.quotepath=false diff --cached --name-status \
  | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit-message.py" "{vault_root}"
git -C "{vault_root}" reset HEAD
```

The approval must name each message — an approval of "커밋해줘" that never displayed the messages does not authorize them.

## Rules — rationale

- Step 4a runs `git add -A` for preview only; the commit itself requires approval.
- **This skill does not filter derived or generated files.** Regenerable indexes (`.ovm/`, `.vault-bridge/manifest.json`) are excluded by the vault's `.gitignore`, so they never reach the staged set. Do not add an exclusion list here — a second list drifts from the first.
- If the command is interrupted after Step 4a (timeout, crash, context limit) before Step 6 cleanup runs, the vault git index is left staged. Restore with `git -C {vault_root} reset HEAD`.
- Grouping by path prefix only: content-based classification would make two runs of the same staged set produce different commits.
- This command is fully independent of `.vault-link` and the vault manifest subsystem.
