#!/usr/bin/env python3
"""invariant_guard.py — D5 constitutional invariant enforcement (#183 S2, Gap-INV §4.2).

The harness only owns the *semantic judgment* native cannot make. Native already
does the mechanical part — PreToolUse hooks block Write (vault-bridge
`pre-write-guard`), a Workflow `verify` stage summons a reviewer, `/goal` runs the
loop. What native does NOT do is decide "is this Write a critique artifact?", "is
this reviewer the same context that authored?", "does this goal-doc match the
schema?", "is this leaf reaching up into the harness?". Those four judgments are the
thin gap this module enforces (boundary §5 / `omc-to-native-substrate.md` §4.2):

    INV-4 (CON-4) goal-doc schema      validate_goal_doc()        — #100 §4.3 deterministic check
    INV-1 (CON-1) new-file-only        check_new_file_only()      — vault write must not clobber
    INV-2/3 (CON-3) isolated critique  check_isolated_critique()  — reviewer ≠ author (no self-approval)
    INV-5 (CON-5) one-way dependency   check_one_way_dependency() — leaf must not import/call the harness

Native-delegation boundary: this is a *decision library*, not a runtime blocker. The
active agent / a PreToolUse handler calls these to get a verdict; the actual block is
native's. Single source of truth for the rules: `docs/design/claude-kit-boundary.md`
§5 (CON-1…CON-5) — this module enforces, it does not redefine.

Stdlib only (no PyYAML — parity with vault-bridge/scripts/generate-manifest.py).

CLI:
    python3 invariant_guard.py validate <goal-doc.md>   # INV-4 — exit 0 clean, 1 violations
    python3 invariant_guard.py --self-test              # in-memory cases
"""
from __future__ import annotations

import argparse
import re
import sys

# ── frontmatter parsing (mirrors generate-manifest.py _parse_frontmatter) ─────
_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FLOW_ARRAY_RE = re.compile(r"^\[([^\]]*)\]$")

# INV-4 enum domains (goal-doc-spec §4.3.2)
_MODEL_ENUM = {"haiku", "sonnet", "opus"}
_STATUS_ENUM = {"gated", "ready"}
_WORK_TYPE_ENUM = {"feature-full", "decision-only", "doc-only"}
# applies_tiers is a cumulative list (§1.3): each prefix of this order is legal.
_TIER_ORDER = ["default", "user", "project"]

# required frontmatter = core 8 (§1.1) + work_type (§1.2)
_REQUIRED_FM = [
    "goal_id", "title", "issues", "wave", "depends_on",
    "recommended_model", "status", "created", "work_type",
]

# body 5 sections (§2) — identified by order + keyword, NOT exact title match (§2 note).
# Each entry: (canonical-name, [keyword substrings, lowercased]).
_REQUIRED_SECTIONS = [
    ("background", ["배경", "목적", "background", "purpose"]),
    ("dod", ["완료", "dod", "definition of done", "acceptance"]),
    ("tradeoff", ["쟁점", "트레이드오프", "trade-off", "tradeoff"]),
    ("slices", ["슬라이스", "slice"]),
    ("e2e", ["자가검증", "e2e", "self-verif", "자가 검증"]),
]

_GOAL_ID_RE = re.compile(r"^G\d+$")
# a slice line: "N. **<name>** → 바인딩: ..." — we only require the binding marker.
_SLICE_LINE_RE = re.compile(r"^\s*\d+\.\s+\*\*.+?\*\*")
_BINDING_MARKER_RE = re.compile(r"바인딩\s*:|binding\s*:", re.IGNORECASE)


def _parse_scalar(value: str):
    """Parse a YAML scalar into a Python value (subset, stdlib only)."""
    v = value.strip()
    if not v:
        return None
    # Strip an unquoted trailing YAML comment (` # ...`) before any coercion — inline
    # comments are legal YAML, so `status: ready  # gate done` must reduce to "ready",
    # not be rejected as a bad enum. Quoted scalars keep a literal '#'. Done before the
    # flow-array check so `[183]  # note` also reduces cleanly.
    if v[0] not in "\"'":
        v = re.sub(r"\s+#.*$", "", v).strip()
        if not v:
            return None
    m = _FLOW_ARRAY_RE.match(v)
    if m:
        inner = m.group(1)
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        v = v[1:-1]
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    try:
        return int(v)
    except ValueError:
        return v


def _parse_frontmatter(text: str) -> dict:
    """Top-level scalar / flow-array / block-sequence frontmatter values."""
    m = _FM_BLOCK_RE.match(text)
    if not m:
        return {}
    result: dict = {}
    current_key = None
    current_list = None
    for raw_line in m.group(1).splitlines():
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            item = raw_line.lstrip("- ").strip().strip("\"'")
            if current_key is not None:
                if current_list is None:
                    existing = result.get(current_key)
                    if isinstance(existing, list):
                        current_list = existing
                    else:
                        current_list = []
                        if existing not in (None, ""):
                            current_list.append(existing)
                        result[current_key] = current_list
                current_list.append(item)
            continue
        if ":" in raw_line:
            idx = raw_line.index(":")
            key = raw_line[:idx].strip()
            value = raw_line[idx + 1:].strip()
            current_key = key
            current_list = None
            parsed = _parse_scalar(value)
            if isinstance(parsed, list):
                result[key] = parsed
                current_list = parsed
            elif parsed is None or parsed == "":
                result[key] = None
            else:
                result[key] = parsed
    return result


def _iter_sections(body: str):
    """Yield (header_text, lowercased_header) for each `## ` / `### ` heading, in order.

    Both H2 and H3 count — §2 identifies the 5 sections by order + keyword, not by a
    fixed heading level, so a goal-doc nesting a required section at `### ` is still
    recognized. H1 (`# `, the title) is excluded.
    """
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            head = stripped.lstrip("#").strip()
            yield head, head.lower()


def _extract_slice_lines(text: str) -> list[str]:
    """Return slice lines from the body (numbered + bold + a binding marker).

    Scoped: a line counts only if it both looks like a slice entry (`N. **…**`) and
    carries a binding marker — so prose numbered lists elsewhere don't leak in.
    """
    m = _FM_BLOCK_RE.match(text)
    body = text[m.end():] if m else text
    out = []
    for raw in body.splitlines():
        if _SLICE_LINE_RE.match(raw) and _BINDING_MARKER_RE.search(raw):
            out.append(raw.strip())
    return out


def parse_goal_doc(text: str) -> dict:
    """Parse a goal-doc into {frontmatter, section_headers, slice_lines}.

    Shared by the router (slice_router.route) and the INV-4 validator. Pure parse —
    no validation here; validate_goal_doc() is the judgment layer.
    """
    m = _FM_BLOCK_RE.match(text)
    body = text[m.end():] if m else text
    return {
        "frontmatter": _parse_frontmatter(text),
        "section_headers": [head for head, _ in _iter_sections(body)],
        "slice_lines": _extract_slice_lines(text),
    }


# ── INV-4 (CON-4): goal-doc schema validation (goal-doc-spec §4.3) ───────────

def _validate_applies_tiers(value) -> list[str]:
    """applies_tiers must be a cumulative prefix of [default, user, project] (§1.3)."""
    if value is None:
        return []  # unspecified → defaults to [default] (§1.3), legal
    if not isinstance(value, list):
        return [f"applies_tiers must be a list, got {type(value).__name__}"]
    expected_prefixes = {tuple(_TIER_ORDER[:i]) for i in range(1, len(_TIER_ORDER) + 1)}
    if tuple(value) not in expected_prefixes:
        return [
            "applies_tiers must be a cumulative prefix of "
            f"{_TIER_ORDER} (e.g. [default], [default, user]); got {value}"
        ]
    return []


def validate_goal_doc(text: str) -> list[str]:
    """INV-4 — deterministic schema check (goal-doc-spec §4.3). Returns [] when clean.

    Checks: (1) required frontmatter present, (2) enum legality, (3) body 5 sections
    present in order, (4) namespace resolution (depends_on=goal_id, issues=int),
    (5) slice binding structure present. `wave` value space is NOT checked (§1.5).
    """
    violations: list[str] = []
    parsed = parse_goal_doc(text)
    fm = parsed["frontmatter"]

    if not fm:
        return ["no frontmatter block found (goal-doc must open with a --- YAML block)"]

    # (1) required frontmatter present
    for key in _REQUIRED_FM:
        if key not in fm or fm[key] in (None, ""):
            violations.append(f"missing required frontmatter field: {key}")

    # `issues: []` is present-but-empty → still effectively missing: a goal must close ≥1
    # issue (#190 N1). Scoped to `issues` ONLY — depends_on:[] is legitimately empty for
    # foundation goals (G1 has no predecessors), so this is NOT a blanket
    # empty-list-is-missing rule applied across the required fields.
    if isinstance(fm.get("issues"), list) and not fm["issues"]:
        violations.append(
            "issues must list at least one GitHub issue number (empty list is not allowed)"
        )

    # (2) enum legality (only when the field is present — absence already flagged above)
    if fm.get("recommended_model") not in (None, "") and fm.get("recommended_model") not in _MODEL_ENUM:
        violations.append(
            f"recommended_model must be one of {sorted(_MODEL_ENUM)}, got {fm['recommended_model']!r}"
        )
    if fm.get("status") not in (None, "") and fm.get("status") not in _STATUS_ENUM:
        violations.append(f"status must be one of {sorted(_STATUS_ENUM)}, got {fm['status']!r}")
    if fm.get("work_type") not in (None, "") and fm.get("work_type") not in _WORK_TYPE_ENUM:
        violations.append(
            f"work_type must be one of {sorted(_WORK_TYPE_ENUM)}, got {fm['work_type']!r} "
            "(bug-light is signalled by goal-doc ABSENCE, never this field — §4.4)"
        )
    violations.extend(_validate_applies_tiers(fm.get("applies_tiers")))

    # (3) body 5 sections present in order (keyword match, not exact title — §2 note)
    headers = [h.lower() for h in parsed["section_headers"]]
    search_from = 0
    for canon, keywords in _REQUIRED_SECTIONS:
        found_at = None
        for i in range(search_from, len(headers)):
            if any(kw in headers[i] for kw in keywords):
                found_at = i
                break
        if found_at is None:
            # maybe present but out of order → distinguish the two failure modes
            if any(any(kw in h for kw in keywords) for h in headers):
                violations.append(f"body section out of order: '{canon}' appears before a prior required section")
            else:
                violations.append(f"missing required body section: '{canon}' (§2)")
        else:
            search_from = found_at + 1

    # (4) namespace resolution (§1.4): depends_on=goal_id space, issues=GitHub-int space
    deps = fm.get("depends_on")
    if isinstance(deps, list):
        for d in deps:
            if not _GOAL_ID_RE.match(str(d).strip()):
                violations.append(f"depends_on entry '{d}' is not a goal_id (G\\d+) — issues use a separate namespace (§1.4)")
    elif deps not in (None, ""):
        # a non-empty scalar depends_on is allowed only if it's a single goal_id
        if not _GOAL_ID_RE.match(str(deps).strip()):
            violations.append(f"depends_on '{deps}' is not a goal_id (G\\d+) (§1.4)")
    issues = fm.get("issues")
    issue_items = issues if isinstance(issues, list) else ([issues] if issues not in (None, "") else [])
    for it in issue_items:
        try:
            int(str(it).strip())
        except (ValueError, TypeError):
            violations.append(f"issues entry '{it}' is not a GitHub issue number (int) (§1.4)")

    # (5) slice binding structure present (§3) — at least one slice with a binding expr
    if not parsed["slice_lines"]:
        violations.append("no slice with a binding expression found in the slice section (§3.1)")

    return violations


# ── INV-1 (CON-1): new-file-only vault write ─────────────────────────────────

def check_new_file_only(write_path, existing_paths, *, frontmatter_only_status_patch=False) -> str | None:
    """INV-1 — a vault write must create a NEW file, never clobber an existing one.

    Carve-out (boundary §5 CON-1 status-machine note, ratified 2026-06-08): a
    frontmatter-only `status:` transition (raw→draft→evergreen→archived) is *within*
    CON-1, so an in-place write that is a frontmatter-only status patch is allowed even
    on an existing path. Any other write to an existing path is a clobber → violation.
    """
    existing = {str(p) for p in existing_paths}
    if str(write_path) in existing and not frontmatter_only_status_patch:
        return (
            f"new-file-only violation (CON-1): write to existing path '{write_path}' "
            "would clobber it; vault writes must create a new file (or be a "
            "frontmatter-only status-machine transition)"
        )
    return None


# ── INV-2/3 (CON-3): isolated critique / no self-approval ────────────────────

def _binding_candidates(binding: str) -> set[str]:
    """Reduce a binding expression to its candidate skill ids.

    "adversarial-review|code-reviewer(#133)" → {"adversarial-review", "code-reviewer"}
    "직접(메인 컨텍스트)"                       → {"직접"}
    Strips (#issue) confirmations, (qualifier) text, and <#placeholder> tokens.
    """
    b = re.sub(r"<#?\d+>", "", binding)        # drop <#133> placeholder
    b = re.sub(r"\(#?\d+\)", "", b)            # drop (#133) confirmation
    b = re.sub(r"\([^)]*\)", "", b)            # drop (qualifier) prose
    return {p.strip() for p in b.split("|") if p.strip()}


def check_isolated_critique(route_plan: dict) -> str | None:
    """INV-2/3 — the critique slice must bind to a skill DISJOINT from the authoring slices.

    A reviewer that is also an author is self-approval (CON-3). Only feature-full has a
    critique slice; for other work_types there is nothing to check. The verdict is over
    candidate *sets*: if any critique candidate also appears among the authoring (spec /
    impl) candidates, the same context could approve its own output → violation.
    """
    slices = route_plan.get("slices") or []
    critique = [s for s in slices if s.get("name") == "critique"]
    if not critique:
        return None  # no critique slice (decision-only / doc-only / bug-light) — nothing to isolate
    authors: set[str] = set()
    for s in slices:
        if s.get("name") in ("spec", "impl"):
            authors |= _binding_candidates(s.get("binding", ""))
    for c in critique:
        raw = c.get("binding", "")
        cands = _binding_candidates(raw)
        overlap = cands & authors
        if overlap:
            return (
                "isolated-critique violation (CON-3): critique binding "
                f"{sorted(cands)} overlaps authoring binding(s) {sorted(overlap)} — "
                "reviewer must differ from author (no self-approval)"
            )
        if not cands:
            return "isolated-critique violation (CON-3): critique slice has no reviewer binding"
        # Defense: an authoring skill-id smuggled INSIDE a qualifier. §3.3's 직접(<context>)
        # form legitimately holds a context descriptor in parens, but naming the author
        # there (e.g. 직접(executor가 self-review)) would slip past candidate extraction —
        # that is self-approval. Scan the raw binding (qualifier included) for any author id.
        for a in sorted(authors):
            # ASCII skill-id boundary — NOT \w, because a Korean qualifier like
            # `직접(executor가 …)` puts a Hangul char (which IS \w) right after the id,
            # so a \w boundary would miss it. Skill-ids are ascii [A-Za-z0-9_-].
            if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(a) + r"(?![A-Za-z0-9_-])", raw):
                return (
                    "isolated-critique violation (CON-3): critique binding "
                    f"{raw!r} names authoring skill '{a}' inside a qualifier — "
                    "reviewer must differ from author (no self-approval hidden in context)"
                )
    return None


# ── INV-5 (CON-5): one-way dependency (harness → leaf, no reverse) ───────────

# A leaf reaching UP into the harness: a code import / call of the harness module or
# plugin. Prose that merely *names* the harness (boundary citations, the CON-5 rule
# itself) is allowed — only import/call syntax counts, to avoid false positives.
_HARNESS_REVERSE_RE = [
    re.compile(r"\bimport\s+(?:\w+\.)*invariant_guard\b"),
    re.compile(r"\bimport\s+(?:\w+\.)*slice_router\b"),
    re.compile(r"\bfrom\s+(?:\w+\.)*(?:invariant_guard|slice_router)\s+import\b"),
    re.compile(r"\bfrom\s+workflow[_-]harness\b"),
    re.compile(r"\bimport\s+workflow[_-]harness\b"),
    # dynamic import evasions — __import__ / importlib.import_module
    re.compile(r"__import__\(\s*['\"](?:invariant_guard|slice_router|workflow[_-]harness)"),
    re.compile(r"importlib\.import_module\(\s*['\"](?:invariant_guard|slice_router|workflow[_-]harness)"),
    # a leaf script shelling out to a harness script — match the script name anywhere on
    # the line (the path may be assembled from a variable), not only the full repo path.
    re.compile(r"(?:invariant_guard|slice_router)\.py\b"),
]

# Leaf plugins (①②③④) — the directories that must never depend back on ⑤ harness.
_LEAF_DIRS = ("thinking-tools/", "obsidian-vault-manager/", "vault-bridge/")


def check_one_way_dependency(leaf_path: str, text: str) -> str | None:
    """INV-5 — a leaf file must not import/call the harness (boundary §3 / CON-5).

    `leaf_path` is the file's repo-relative path; `text` is its content. Returns a
    violation string if the leaf reaches up into the harness, else None. Mechanical
    git-diff guards (leaf diff 0-lines on a harness change) complement this at CI/
    integration level — this is the per-file code-level judgment for unit testing.
    """
    if not any(leaf_path.startswith(d) or f"/{d}" in leaf_path for d in _LEAF_DIRS):
        return None  # not a leaf file — INV-5 only constrains leaves
    for line in text.splitlines():
        # Skip commented-out lines: a `# import invariant_guard` example or a
        # "never do this" note in a leaf must not trip a false INV-5 verdict. (The
        # regexes already require real import/call syntax, so prose without a comment
        # marker still won't match — this closes the commented-out-code path. #189 nit 2.)
        if line.lstrip().startswith("#"):
            continue
        for rx in _HARNESS_REVERSE_RE:
            if rx.search(line):
                return (
                    f"one-way-dependency violation (CON-5): leaf '{leaf_path}' imports/"
                    f"calls the harness — '{line.strip()}'. Leaves are harness-neutral "
                    "by construction; fix the direction, never add a back-edge."
                )
    return None


# ── self-test ────────────────────────────────────────────────────────────────

_VALID_GOAL_DOC = """---
goal_id: G99
title: Sample feature goal
issues: [200, 201]
wave: 3
depends_on: [G1]
recommended_model: opus
status: ready
work_type: feature-full
created: 2026-06-08
---

## 배경 / 목적
why.

## 완료 조건 (Definition of Done)
- [ ] thing

## 쟁점과 트레이드오프
| a | b |

## 슬라이스 순서
1. **spec** → 바인딩: spec-first | 대상 파일: x | 산출: y | 검증: z
2. **impl** → 바인딩: executor|native(#133) | 대상 파일: x | 산출: y | 검증: z

## E2E 자가검증
```bash
echo ok
```
"""


def run_self_test() -> int:
    failures = []

    # INV-4: valid doc passes clean
    v = validate_goal_doc(_VALID_GOAL_DOC)
    if v:
        failures.append(f"  valid goal-doc flagged: {v}")

    # INV-4: missing work_type
    bad = _VALID_GOAL_DOC.replace("work_type: feature-full\n", "")
    if not any("work_type" in x for x in validate_goal_doc(bad)):
        failures.append("  missing work_type not caught")

    # INV-4: bad enum
    bad = _VALID_GOAL_DOC.replace("work_type: feature-full", "work_type: bug-light")
    if not any("work_type must be one of" in x for x in validate_goal_doc(bad)):
        failures.append("  invalid work_type enum (bug-light) not caught")

    # INV-4: depends_on namespace (issue number where a goal_id belongs)
    bad = _VALID_GOAL_DOC.replace("depends_on: [G1]", "depends_on: [183]")
    if not any("not a goal_id" in x for x in validate_goal_doc(bad)):
        failures.append("  depends_on namespace violation not caught")

    # INV-4: missing a body section
    bad = _VALID_GOAL_DOC.replace("## E2E 자가검증\n", "## Something else\n")
    if not any("e2e" in x.lower() for x in validate_goal_doc(bad)):
        failures.append("  missing E2E section not caught")

    # INV-1: clobber existing path
    if check_new_file_only("notes/a.md", ["notes/a.md"]) is None:
        failures.append("  new-file-only clobber not caught")
    if check_new_file_only("notes/b.md", ["notes/a.md"]) is not None:
        failures.append("  new path wrongly flagged as clobber")
    if check_new_file_only("notes/a.md", ["notes/a.md"], frontmatter_only_status_patch=True) is not None:
        failures.append("  frontmatter-only status carve-out wrongly blocked")

    # INV-2/3: self-approval (critique == author)
    bad_plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor"},
        {"name": "critique", "binding": "executor"},
    ]}
    if check_isolated_critique(bad_plan) is None:
        failures.append("  self-approval (critique==author) not caught")
    good_plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor|native(#133)"},
        {"name": "critique", "binding": "adversarial-review|code-reviewer(#133)"},
    ]}
    if check_isolated_critique(good_plan) is not None:
        failures.append("  isolated critique wrongly flagged")

    # INV-5: leaf importing harness
    if check_one_way_dependency("vault-bridge/scripts/x.py", "from invariant_guard import validate_goal_doc") is None:
        failures.append("  leaf→harness import not caught")
    if check_one_way_dependency("workflow-harness/scripts/slice_router.py", "import invariant_guard") is not None:
        failures.append("  harness self-import wrongly flagged as INV-5")
    if check_one_way_dependency("vault-bridge/README.md", "see workflow-harness boundary §5 CON-5") is not None:
        failures.append("  leaf prose citing harness wrongly flagged")

    if failures:
        print("FAIL: invariant_guard self-test")
        print("\n".join(failures))
        return 1
    print("OK: all invariant_guard self-test cases passed")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="D5 constitutional invariant enforcement (#183)")
    parser.add_argument("command", nargs="?", choices=["validate"], help="validate a goal-doc (INV-4)")
    parser.add_argument("path", nargs="?", help="goal-doc path for `validate`")
    parser.add_argument("--self-test", action="store_true", help="run in-memory cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if args.command == "validate":
        if not args.path:
            print("ERROR: validate requires a goal-doc path", file=sys.stderr)
            return 2
        try:
            with open(args.path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            print(f"ERROR: cannot read {args.path}: {e}", file=sys.stderr)
            return 2
        violations = validate_goal_doc(text)
        if violations:
            print(f"INV-4 FAIL: {args.path} has {len(violations)} schema violation(s):")
            for v in violations:
                print(f"  - {v}")
            return 1
        print(f"INV-4 OK: {args.path} conforms to the goal-doc schema")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
