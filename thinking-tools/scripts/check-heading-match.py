#!/usr/bin/env python3
"""check-heading-match.py — issue-raise template-heading conformance guard (#563, #774).

RULE: an issue body assembled from a repo's issue template must carry the template's `## `
headings with the same text and in the same order, including an optional marker such as
`(선택)` / `(optional)` — because issue-raise's Phase 2 only INSTRUCTS an LLM to copy them
verbatim; nothing mechanically confirms it did. #562 is the observed failure: the template's
`## 제안 (선택)` heading was assembled as `## 제안`, silently dropping the marker, with no
guard between body assembly and the approval prompt to catch it.

The one allowed deviation (#774): issue-raise Phase 2 tells the LLM to leave out an optional
section that has nothing to say, so a template heading that is **optional** may be absent from
the draft. Everything else still fails — a required heading missing, headings reordered, an
extra heading, or reworded heading text (a dropped/added `(선택)` marker is reworded text, so
#562 keeps failing even though the template heading it hit was optional).

Optional-ness is decided exactly as issue-template.py decides it: `is_optional()` over the
heading's trailing parenthetical (`OPTIONAL_WORDS`), reused by loading that sibling script.
A `.yml` issue form states optional-ness out of band (`validations.required: false`), so its
`--headings` output carries no marker; pass `--optional-from <the chosen template path>` and the
sections issue-template.py flags `optional` are skippable too. Without that flag only the
trailing-parenthetical rule applies (backward compatible).

Comparison is an order-preserving alignment (minimum edit, so one omission is reported as one
problem instead of shifting every later heading): a template heading may be skipped only when
optional; every other difference is reported by kind (missing / changed / extra / reordered /
duplicate).

`--template` takes a **section list in `## ` form**, which is what `issue-template.py
--headings` emits for every template shape the repo might ship. Point it at a raw Markdown
template and it still works (that file already is `## ` lines); point it at a raw `.yml` issue
form and it would find zero headings and pass anything — hence the normalization step, which
keeps form parsing out of the comparison itself.

Zero LLM cost, same philosophy as backlog-prefilter.py.

Usage:
    check-heading-match.py --template <path> --draft <path> [--optional-from <path>] [--json]
    check-heading-match.py --self-test

Exit codes:
    0 = headings conform (or --self-test passed)
    1 = mismatch found
    2 = usage error / a path is unreadable / issue-template.py cannot be loaded
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n?", re.DOTALL)
# Exactly `## ` (two hashes + space) — a `### ` sub-heading does not match this prefix.
HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)

_ISSUE_TEMPLATE = None


def load_issue_template():
    """Load the sibling issue-template.py (hyphenated filename, so not a plain import).
    Single source of truth for OPTIONAL_WORDS / is_optional() / form parsing."""
    global _ISSUE_TEMPLATE
    if _ISSUE_TEMPLATE is None:
        path = Path(__file__).resolve().with_name("issue-template.py")
        spec = importlib.util.spec_from_file_location("issue_template", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _ISSUE_TEMPLATE = mod
    return _ISSUE_TEMPLATE


def extract_headings(text):
    """Return the ordered list of `## ` heading texts, frontmatter stripped."""
    body = FRONTMATTER_RE.sub("", text, count=1)
    return HEADING_RE.findall(body)


def make_optional_fn(optional_names=()):
    """Optional = trailing-parenthetical marker (issue-template.is_optional) or a name the
    caller got from issue-template's own parse (a `.yml` form's `required: false`)."""
    is_opt = load_issue_template().is_optional
    names = set(optional_names)
    return lambda heading: heading in names or is_opt(heading)


_MARKER_TAIL_RE = re.compile(r"\s*[(（][^()（）]*[)）]\s*$")


def _strip_marker(heading):
    return _MARKER_TAIL_RE.sub("", heading)


def diff_headings(template_headings, draft_headings, is_optional):
    """Order-preserving alignment; only optional template headings may be skipped.

    Returns a list of mismatch dicts (empty = conforming). Each has `kind`:
      missing    required template heading absent from the draft
      changed    draft heading sits where a template heading is expected but its text differs
      extra      draft heading that matches nothing in the template
      reordered  heading present but in a different position than the template puts it
      duplicate  draft heading repeated (already matched elsewhere)
    plus `template`/`draft` text, `template_position`/`draft_position` (1-based or None),
    and `position` (the draft position when the draft is involved, else the template one).
    """
    t, d = template_headings, draft_headings
    n, m = len(t), len(d)
    inf = float("inf")
    extra = 10  # an unmatched draft heading

    def skip_cost(h):  # dropping a template heading: free only when it is optional
        return 0 if is_optional(h) else 10

    def sub_cost(th, dh):  # pairing two headings; a marker-only difference is the closer pair
        if th == dh:
            return 0
        return 9 if _strip_marker(th) == _strip_marker(dh) else 10

    # cost[i][j] = cheapest alignment of t[i:] with d[j:]. The weights only steer which of
    # several equally-failing alignments is reported (so `## 범위` is paired with
    # `## 범위 (선택)` rather than with an unrelated skipped optional heading); pass/fail
    # is cost == 0, i.e. nothing but optional skips.
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    cost[n][m] = 0
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n and j == m:
                continue
            best = inf
            if i < n and j < m:
                best = cost[i + 1][j + 1] + sub_cost(t[i], d[j])
            if i < n:
                best = min(best, cost[i + 1][j] + skip_cost(t[i]))
            if j < m:
                best = min(best, cost[i][j + 1] + extra)
            cost[i][j] = best

    ops = []  # (op, i, j) with op in match|skip|missing|changed|extra
    i = j = 0
    while i < n or j < m:
        here = cost[i][j]
        can_sub = i < n and j < m and cost[i + 1][j + 1] + sub_cost(t[i], d[j]) == here
        can_skip = i < n and cost[i + 1][j] + skip_cost(t[i]) == here
        can_extra = j < m and cost[i][j + 1] + extra == here
        if can_sub and t[i] == d[j]:
            ops.append(("match", i, j))
            i += 1
            j += 1
        elif can_sub and not ((can_skip or can_extra) and t[i] in d and d[j] in t):
            # Prefer "changed" over skip+extra on a tie: the #562 marker-drop reads as a
            # reworded heading, not as an unrelated extra one. But when both headings exist
            # elsewhere on the other side it is a move, so fall through and report reordering.
            ops.append(("changed", i, j))
            i += 1
            j += 1
        elif can_skip:
            ops.append(("skip" if is_optional(t[i]) else "missing", i, None))
            i += 1
        else:
            ops.append(("extra", None, j))
            j += 1

    skipped = {t[i] for op, i, _ in ops if op == "skip"}
    missing_texts = {t[i] for op, i, _ in ops if op == "missing"}
    matched = {t[i] for op, i, _ in ops if op == "match"}
    consumed_missing = set()
    mismatches = []
    for op, i, j in ops:
        if op in ("match", "skip"):
            continue
        entry = {
            "kind": op,
            "template": t[i] if i is not None else None,
            "draft": d[j] if j is not None else None,
            "template_position": i + 1 if i is not None else None,
            "draft_position": j + 1 if j is not None else None,
        }
        if op == "extra":
            text = d[j]
            if text in missing_texts or text in skipped:
                entry["kind"] = "reordered"
                entry["template"] = text
                consumed_missing.add(text)
            elif text in matched:
                entry["kind"] = "duplicate"
        mismatches.append(entry)
    # A "missing X" paired with a reordered "X" is one problem, reported once.
    mismatches = [e for e in mismatches
                  if not (e["kind"] == "missing" and e["template"] in consumed_missing)]
    for e in mismatches:
        e["position"] = e["draft_position"] or e["template_position"]
    return mismatches


def render_mismatches(mismatches):
    lines = ["FAIL: 템플릿 헤딩과 초안 헤딩이 일치하지 않아요:"]
    for m in mismatches:
        k = m["kind"]
        if k == "missing":
            lines.append(
                f"  필수 헤딩 누락: 템플릿 {m['template_position']}번째 `## {m['template']}`이(가) 초안에 없어요")
        elif k == "changed":
            lines.append(
                f"  헤딩 텍스트 변경: 템플릿 `## {m['template']}` -> 초안 {m['draft_position']}번째 `## {m['draft']}`")
        elif k == "reordered":
            lines.append(
                f"  헤딩 순서 어긋남: 초안 {m['draft_position']}번째 `## {m['draft']}`이(가) 템플릿 순서와 달라요")
        elif k == "duplicate":
            lines.append(f"  헤딩 중복: 초안 {m['draft_position']}번째 `## {m['draft']}`")
        else:
            lines.append(f"  템플릿에 없는 헤딩: 초안 {m['draft_position']}번째 `## {m['draft']}`")
    return "\n".join(lines)


def run_self_test():
    # Each case: (name, template text, draft text, expected [(kind, template, draft), ...],
    # optional_names for the out-of-band `.yml` form path).
    cases = [
        ("match", "## A\n## B (선택)", "## A\n## B (선택)", [], ()),
        # #562's actual defect: the `(선택)` marker silently dropped during assembly. The
        # template heading is optional, yet the reworded draft heading must still FAIL.
        ("562-marker-dropped", "## 무엇을 / 왜\n## 제안 (선택)", "## 무엇을 / 왜\n## 제안",
         [("changed", "제안 (선택)", "제안")], ()),
        # Marker dropped on a heading that sits among other (skipped) optionals: reported
        # against its own template heading, not against the first optional one.
        ("562-marker-dropped-among-optionals", "## A\n## P (선택)\n## S (선택)\n## C\n## R",
         "## A\n## S\n## C\n## R", [("changed", "S (선택)", "S")], ()),
        # #774: an optional section left out (Phase 2: nothing answers it) passes, and the
        # headings after it are not reported as shifted.
        ("optional-omitted", "## A\n## B (선택)\n## C", "## A\n## C", [], ()),
        ("optional-omitted-last", "## A\n## B (선택)", "## A", [], ()),
        ("all-optional-omitted", "## A (optional)\n## B (선택)", "", [], ()),
        ("optional-omitted-mid-run", "## A\n## B (선택)\n## C (선택)\n## D\n## E",
         "## A\n## D\n## E", [], ()),
        ("optional-omitted-english", "## A\n## B (optional)\n## C", "## A\n## C", [], ()),
        # `.yml` form: no inline marker, optional-ness arrives out of band.
        ("form-optional-omitted", "## A\n## B\n## C", "## A\n## C", [], ("B",)),
        ("form-without-optional-names", "## A\n## B\n## C", "## A\n## C",
         [("missing", "B", None)], ()),
        # Only a trailing optional-word parenthetical marks optional; other parentheticals don't.
        ("paren-not-optional", "## A\n## B (Claude Code 버전)\n## C", "## A\n## C",
         [("missing", "B (Claude Code 버전)", None)], ()),
        # Was `missing-heading`, which asserted two positional mismatches (B->C, C->None).
        # A required omission still fails; it is now reported as the one actual problem.
        ("required-omitted", "## A\n## B\n## C", "## A\n## C", [("missing", "B", None)], ()),
        ("required-omitted-beside-optional", "## A\n## B (선택)\n## C\n## D", "## A\n## D",
         [("missing", "C", None)], ()),
        ("extra-heading", "## A\n## B", "## A\n## B\n## C", [("extra", None, "C")], ()),
        ("reordered", "## A\n## B", "## B\n## A", [("reordered", "A", "A")], ()),
        ("reordered-optional", "## A\n## B (선택)\n## C", "## A\n## C\n## B (선택)",
         [("reordered", "B (선택)", "B (선택)")], ()),
        ("duplicate", "## A\n## B", "## A\n## B\n## B", [("duplicate", None, "B")], ()),
        ("required-reworded", "## A\n## B\n## C", "## A\n## X\n## C",
         [("changed", "B", "X")], ()),
        ("frontmatter-stripped", "---\nname: X\nlabels: bug\n---\n\n## A", "## A", [], ()),
        ("sub-heading-ignored", "## A\n### not a top heading\n## B", "## A\n## B", [], ()),
    ]
    failures = []
    for name, tmpl_text, draft_text, expected, opt_names in cases:
        got = diff_headings(extract_headings(tmpl_text), extract_headings(draft_text),
                            make_optional_fn(opt_names))
        got = [(e["kind"], e["template"], e["draft"]) for e in got]
        if got != expected:
            failures.append((name, got, expected))
    if failures:
        print("FAIL: check-heading-match self-test")
        for name, got, want in failures:
            print(f"  {name}: got {got}, want {want}")
        return 1
    print("OK: all check-heading-match self-test cases passed")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--template", default=None)
    parser.add_argument("--draft", default=None)
    parser.add_argument(
        "--optional-from", default=None, metavar="TEMPLATE",
        help="the chosen raw template path (.md or .yml form); sections issue-template.py "
        "flags optional become skippable. Needed for .yml forms, whose --headings output "
        "has no inline marker.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if not args.template or not args.draft:
        print("ERROR: --template and --draft are both required (or use --self-test)", file=sys.stderr)
        return 2

    try:
        with open(args.template, encoding="utf-8") as fh:
            template_text = fh.read()
        with open(args.draft, encoding="utf-8") as fh:
            draft_text = fh.read()
        optional_names = ()
        if args.optional_from:
            _, sections = load_issue_template().parse(args.optional_from)
            optional_names = [s["name"] for s in sections if s["optional"]]
        is_optional = make_optional_fn(optional_names)
    except (OSError, UnicodeDecodeError, ImportError, AttributeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    template_headings = extract_headings(template_text)
    draft_headings = extract_headings(draft_text)
    mismatches = diff_headings(template_headings, draft_headings, is_optional)

    if args.json:
        print(json.dumps({"match": not mismatches, "mismatches": mismatches}, ensure_ascii=False, indent=2))
    elif mismatches:
        print(render_mismatches(mismatches))
    else:
        omitted = len(template_headings) - len(draft_headings)
        note = f" (선택 헤딩 {omitted}개 생략)" if omitted else ""
        print(f"OK: heading match clean — 템플릿 {len(template_headings)}개 헤딩 중 "
              f"초안 {len(draft_headings)}개 텍스트·순서 일치{note}")

    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
