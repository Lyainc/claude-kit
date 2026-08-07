#!/usr/bin/env python3
"""check-heading-match.py — issue-raise template-heading conformance guard (#563).

RULE: an issue body assembled from a `.github/ISSUE_TEMPLATE/*.md` template must carry the
exact same `## ` headings as the template — same text, same order, same count, including a
`(선택)` marker — because issue-raise's Phase 2 only INSTRUCTS an LLM to copy them verbatim;
nothing mechanically confirms it did. #562 is the observed failure: the template's
`## 제안 (선택)` heading was assembled as `## 제안`, silently dropping the marker, with no
guard between body assembly and the approval prompt to catch it.

Zero LLM cost, same philosophy as backlog-prefilter.py: extract `## ` headings from the
template (frontmatter stripped) and from the assembled draft, and diff them 1:1 by position.
Any mismatch — missing heading, extra heading, reordered heading, or reworded heading text
(including a dropped/added `(선택)` marker) — is reported by position.

Usage:
    check-heading-match.py --template <path> --draft <path> [--json]
    check-heading-match.py --self-test

Exit codes:
    0 = headings match exactly (or --self-test passed)
    1 = mismatch found
    2 = usage error / a path is unreadable
"""
import argparse
import json
import re
import sys

FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n?", re.DOTALL)
# Exactly `## ` (two hashes + space) — a `### ` sub-heading does not match this prefix.
HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)


def extract_headings(text):
    """Return the ordered list of `## ` heading texts, frontmatter stripped."""
    body = FRONTMATTER_RE.sub("", text, count=1)
    return HEADING_RE.findall(body)


def diff_headings(template_headings, draft_headings):
    """Positional 1:1 diff. Empty list means the headings match exactly (same count,
    same text, same order)."""
    mismatches = []
    n = max(len(template_headings), len(draft_headings))
    for i in range(n):
        t = template_headings[i] if i < len(template_headings) else None
        d = draft_headings[i] if i < len(draft_headings) else None
        if t != d:
            mismatches.append({"position": i + 1, "template": t, "draft": d})
    return mismatches


def render_mismatches(mismatches):
    lines = ["FAIL: 템플릿 헤딩과 초안 헤딩이 일치하지 않아요:"]
    for m in mismatches:
        t = m["template"] if m["template"] is not None else "(없음 — 초안에만 있는 헤딩)"
        d = m["draft"] if m["draft"] is not None else "(없음 — 초안에서 빠짐)"
        lines.append(f"  {m['position']}번째: 템플릿 `## {t}` vs 초안 `## {d}`")
    return "\n".join(lines)


def run_self_test():
    cases = [
        ("match", "## A\n## B (선택)", "## A\n## B (선택)", []),
        # #562's actual defect: the `(선택)` marker silently dropped during assembly.
        ("562-marker-dropped", "## 무엇을 / 왜\n## 제안 (선택)", "## 무엇을 / 왜\n## 제안",
         [{"position": 2, "template": "제안 (선택)", "draft": "제안"}]),
        ("missing-heading", "## A\n## B\n## C", "## A\n## C",
         [{"position": 2, "template": "B", "draft": "C"},
          {"position": 3, "template": "C", "draft": None}]),
        ("extra-heading", "## A\n## B", "## A\n## B\n## C",
         [{"position": 3, "template": None, "draft": "C"}]),
        ("reordered", "## A\n## B", "## B\n## A",
         [{"position": 1, "template": "A", "draft": "B"},
          {"position": 2, "template": "B", "draft": "A"}]),
        ("frontmatter-stripped", "---\nname: X\nlabels: bug\n---\n\n## A", "## A", []),
        ("sub-heading-ignored", "## A\n### not a top heading\n## B", "## A\n## B", []),
    ]
    failures = []
    for name, tmpl_text, draft_text, expected in cases:
        got = diff_headings(extract_headings(tmpl_text), extract_headings(draft_text))
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
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    template_headings = extract_headings(template_text)
    draft_headings = extract_headings(draft_text)
    mismatches = diff_headings(template_headings, draft_headings)

    if args.json:
        print(json.dumps({"match": not mismatches, "mismatches": mismatches}, ensure_ascii=False, indent=2))
    elif mismatches:
        print(render_mismatches(mismatches))
    else:
        print(f"OK: heading match clean — {len(template_headings)}개 헤딩 텍스트·순서·개수 일치")

    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
