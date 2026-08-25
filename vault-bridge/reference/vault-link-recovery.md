# vault-searcher — `.vault-link` recovery

`vault-searcher.md` § .vault-link Discovery Protocol points here for the rare-case fallback
when `{vault_root}/{vault_path}` doesn't resolve. This is procedure, not a live decision: the
happy path (discovery walks upward, parses the pointer, resolves `{vault_root}`/`{vault_path}`)
is unaffected by whether this recovery runs, and its absence from the always-loaded agent body
never changes what the agent decides to do on that path.

**Recovery (path resolution failure)**:
- Construct full path: `{vault_root}/{vault_path}`.
- Check if that directory exists via Bash: `[ -d "{full_path}" ]`.
- If directory does NOT exist:
  1. Scan `{vault_root}/notes/` for subdirectory names.
  2. Compute edit distance between `vault_path`'s leaf segment and each candidate.
  3. Collect candidates with edit distance ≤ 2.
  4. If 1+ candidates found: use AskUserQuestion to present them and ask user to confirm correct path or proceed with full-vault scope.
  5. If no candidates: log a warning in Korean ("`.vault-link`의 경로를 찾을 수 없어 vault 전체를 검색합니다.") and fall back to full-vault scope.
- **Graceful fallback**: pointer resolution failure must never halt operation. Always fall back to pre-pointer behavior.
