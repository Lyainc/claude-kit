#!/usr/bin/env python3
"""
E4 false-positive regression: wikilinks inside code are not links (#434).

Measured 2026-07-29 on a 158-note vault: 27 of 82 E4 `broken_wikilink` findings (33%)
were syntax examples that were ALREADY backticked, so no user-side workaround existed —
the extractors simply did not distinguish code from prose. E4 is Critical/P0 and heads
the report, so a third of the top block was noise.

The two extractors carry duplicate `mask_code` copies, so this file drives BOTH over the
same fixture (the #165 parity pattern):
  PART A — ovm-primitives.sh `extract-wikilinks` via subprocess
  PART B — audit-validate.py `collect()` in-process, plus a `mask_code` unit battery

What is gated is masking parity, not extractor parity: the two `WIKILINK_PATTERN`s differ
(the shell one takes an embed prefix and splits `|`/`#` afterwards), which predates #434
and is out of scope here.

Real links outside code must survive untouched — masking that eats real links trades a
33% FP rate for a silent FN rate, which is worse: a swallowed region also strips the
inbound-link map, so the eaten target turns into a fresh E5 orphan on top of the missed E4.

Run: python3 obsidian-vault-manager/scripts/test/test-wikilink-code-masking.py
  → "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_PY = _HERE / "audit-validate.py"
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"

_spec = importlib.util.spec_from_file_location("audit_validate", _AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

collect = _mod.collect
# Resolved leniently: if the fix is reverted this reports a named assertion failure
# instead of an AttributeError at import time, which says nothing about what regressed.
mask_code = getattr(_mod, "mask_code", None)

# A note shaped like the real offenders: design docs whose backticked examples were the
# 27 FPs. `real-note` is the only genuine link and must survive both extractors.
FIXTURE = """---
created: 2026-07-29
type: note
tags: [test]
---

# Wikilink syntax

Inline examples are already backticked: `[[Note]]`, `[[link|alias]]`, `![[embed]]`,
and `[[path/to/file1]]`. A double-backtick span with a literal tick: ``[[weird`]]``.

A genuine link to [[real-note]] sits in prose and must survive.

To mark code you wrap it in a ` character — a lone tick in prose must not pair with
the next span far below and swallow everything between, including [[third-real-note]].

An inline span may cross one newline, so `[[wrapped-
example]]` is still code.

```markdown
[[fenced-example]]
![[fenced-embed]]
```

~~~bash
if [[ "$VAR" == "x" ]]; then echo [[tilde-fenced]]; fi
~~~

````
[[four-backtick-fence]]
```
[[still-inside]]
````

Trailing prose links to [[second-real-note]].

```python
# an unterminated fence runs to EOF
print("[[unterminated]]")
"""

# Every target that must NOT be extracted.
FP_TARGETS = {
    "Note", "link", "embed", "path/to/file1", "weird`",
    "fenced-example", "fenced-embed", "tilde-fenced",
    "four-backtick-fence", "still-inside", "unterminated",
    '"$VAR" == "x"', "wrapped-\nexample",
}
REAL_TARGETS = {"real-note", "second-real-note", "third-real-note"}


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def check_targets(targets: set, label: str, errors: list) -> None:
    leaked = sorted(t for t in targets if any(fp.lower() == t.lower() for fp in FP_TARGETS))
    _assert(not leaked, f"{label}: no code-fenced/inline example extracted (leaked: {leaked})",
            errors)
    missing = sorted(r for r in REAL_TARGETS if r not in {t.lower() for t in targets})
    _assert(not missing, f"{label}: real prose links survive (missing: {missing})", errors)
    _assert(
        {t.lower() for t in targets} == REAL_TARGETS,
        f"{label}: extracted set is exactly the real links (got {sorted(targets)})",
        errors,
    )


def seed_vault(tmp: Path) -> Path:
    vault = tmp / "vault"
    (vault / "notes").mkdir(parents=True)
    (vault / "notes" / "doc.md").write_text(FIXTURE, encoding="utf-8")
    for stem in REAL_TARGETS:
        (vault / "notes" / f"{stem}.md").write_text(
            f"---\ncreated: 2026-07-29\ntype: note\ntags: [test]\n---\n\n# {stem}\n",
            encoding="utf-8",
        )
    return vault


def case_primitives_extract(errors: list) -> None:
    """PART A — the shipped shell primitive."""
    with tempfile.TemporaryDirectory() as td:
        vault = seed_vault(Path(td))
        env = {**os.environ, "VAULT_ROOT": str(vault)}
        proc = subprocess.run(
            ["bash", str(_PRIM_SH), "extract-wikilinks", str(vault / "notes" / "doc.md")],
            capture_output=True, text=True, env=env,
        )
        _assert(proc.returncode == 0,
                f"ovm-primitives: exits 0 (got {proc.returncode}: {proc.stderr})", errors)
        if proc.returncode != 0:
            return
        targets = {link["target"] for link in json.loads(proc.stdout)}
        check_targets(targets, "ovm-primitives", errors)


def case_audit_validate_collect(errors: list) -> None:
    """PART B — the reference impl over the same fixture."""
    with tempfile.TemporaryDirectory() as td:
        vault = seed_vault(Path(td))
        bundle = collect(vault)
        targets = set(bundle["wikilinks_by_file"].get("notes/doc.md", []))
        check_targets(targets, "audit-validate", errors)


def case_mask_code_unit(errors: list) -> None:
    """Unit battery — the masker's own edge cases, independent of the fixture.

    A masked block leaves its closing newline behind (the fence regex stops at the
    closing marker). Harmless for extraction, so the expectations keep it rather than
    growing the regex to trim whitespace nothing reads.
    """
    if mask_code is None:
        _assert(False, "audit-validate.py exports mask_code (#434 fix is present)", errors)
        return
    for label, text, expected in [
        ("inline span dropped", "a `[[x]]` b", "a  b"),
        ("bare prose untouched", "see [[x]] here", "see [[x]] here"),
        ("fence dropped", "a\n```\n[[x]]\n```\nb\n", "a\n\nb\n"),
        ("unterminated fence runs to EOF", "a\n```\n[[x]]\n", "a\n"),
        ("tilde fence dropped", "a\n~~~\n[[x]]\n~~~\nb\n", "a\n\nb\n"),
        ("shorter fence inside longer one", "````\n```\n[[x]]\n````\nb\n", "\nb\n"),
        ("empty span is not a code span", "``", "``"),
        ("unclosed inline tick untouched", "a `[[x]] b", "a `[[x]] b"),
        # The false-negative guard: a span must not reach across a blank line to find
        # its partner, or a stray tick eats every real link in between.
        ("stray tick does not pair across a blank line",
         "a ` tick\n\nkeep [[x]]\n\nthen `code` end", "a ` tick\n\nkeep [[x]]\n\nthen  end"),
        ("span may cross one newline", "a `co\nde` b", "a  b"),
        ("indented fence is masked", "a\n\n   ```\n   [[x]]\n\n   more\n   ```\n\nb\n",
         "a\n\n\n\nb\n"),
        # Over-masking is the silent failure: a region wrongly swallowed stops E4 from
        # reporting real broken links AND makes their targets look like fresh E5 orphans.
        ("closing fence may carry its own indent",
         "```bash\necho hi\n  ```\n\nkeep [[x]]\n", "\n\nkeep [[x]]\n"),
        ("indented unclosed fence stops at its block, not EOF",
         "- step:\n\n  ```bash\n  echo hi\n\nkeep [[x]] and `lit`.\n",
         "- step:\n\n  ```bash\n  echo hi\n\nkeep [[x]] and .\n"),
        ("column-0 unclosed fence still runs to EOF",
         "a\n```\n[[x]]\nkeep nothing\n", "a\n"),
        ("a backtick in frontmatter does not kill the note",
         "---\ntype: note\nd: uses ` for code\n---\n\nkeep [[x]]\n\nand `code`.\n",
         "---\ntype: note\nd: uses ` for code\n---\n\nkeep [[x]]\n\nand .\n"),
    ]:
        _assert(mask_code(text) == expected,
                f"mask_code [{label}]: {mask_code(text)!r} == {expected!r}", errors)


def main() -> int:
    errors: list = []
    for case in (case_primitives_extract, case_audit_validate_collect, case_mask_code_unit):
        print(f"\n{case.__name__}:")
        case(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed")
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
