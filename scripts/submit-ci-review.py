#!/usr/bin/env python3
"""Turn the CI review's structured findings into ONE pull-request review.

`.github/workflows/claude-code-review.yml` runs the reviewer with `--json-schema`, so its
only output is `{summary, findings[], deferred_issue}`. This script is the deterministic
half: it never asks a model anything. It submits a single `POST /pulls/{N}/reviews` —
REQUEST_CHANGES with inline comments when any P0/P1 is present, APPROVE otherwise — then
dismisses this bot's earlier rounds and exits 1 while P0/P1 remain, so the `claude-review`
check and `reviewDecision` both carry the verdict instead of a plain comment.

Inline comments only land on lines inside the PR diff (the API rejects the whole review
otherwise), so a finding outside the diff stays in the body only. The body restates EVERY
finding in full and ends with `Reviewed head: <sha>`: it is the record the next round
reads, and inline comments are not returned by the read the reviewer is allowed to make.

Empty or unparseable output exits 1 before anything is posted: a reviewer that produced
nothing must not become an APPROVE.

Usage (CI): REVIEW_JSON=... PR=N HEAD_SHA=... GITHUB_REPOSITORY=o/r python3 scripts/submit-ci-review.py
            python3 scripts/submit-ci-review.py --self-test
"""
import json
import os
import re
import subprocess
import sys

BOT = "github-actions[bot]"
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def commentable_lines(diff):
    """{path: set(RIGHT-side line numbers)} a review comment may anchor to."""
    lines, path, n, prev = {}, None, 0, ""
    for raw in diff.splitlines():
        # A header `+++` always follows `---`; an added line reading `++ x` does not.
        if raw.startswith("+++ ") and prev.startswith("--- "):
            prev = raw
            path = raw[6:] if raw.startswith("+++ b/") else None
            continue
        prev = raw
        m = _HUNK.match(raw)
        if m:
            n = int(m.group(1))
            continue
        if path is None or raw.startswith(("--- ", "diff ", "index ", "\\")):
            continue
        if raw.startswith("-"):
            continue
        if raw.startswith(("+", " ")):
            lines.setdefault(path, set()).add(n)
            n += 1
    return lines


def build_review(out, commentable, head_sha):
    """Return (payload, blocking_count). Raises ValueError on malformed output."""
    if not isinstance(out, dict) or not isinstance(out.get("summary"), str) or not out["summary"].strip():
        raise ValueError("review output has no summary")
    findings = out.get("findings")
    if not isinstance(findings, list):
        raise ValueError("review output has no findings list")
    blocking = [f for f in findings if f.get("severity") in ("P0", "P1")]

    parts, comments = [], []
    if blocking:
        for sev in ("P0", "P1"):
            group = [f for f in blocking if f["severity"] == sev]
            if group:
                parts.append(f"### {sev}")
            for f in group:
                where = f"`{f.get('path')}:{f.get('line')}`" if f.get("path") else "(no file)"
                parts.append(f"- **[{sev}] {f['title']}** {where}\n\n  {f['body']}")
                if f.get("line") in commentable.get(f.get("path"), ()):
                    comments.append({"path": f["path"], "line": f["line"], "side": "RIGHT",
                                     "body": f"**[{sev}] {f['title']}**\n\n{f['body']}"})
    else:
        parts.append("P0/P1 없음 — LGTM")
    if out.get("deferred_issue"):
        parts.append(f"### Deferred nits (P2)\n{out['deferred_issue']}")
    parts.append(out["summary"].strip())
    parts.append(f"Reviewed head: {head_sha}")

    payload = {"commit_id": head_sha, "body": "\n\n".join(parts),
               "event": "REQUEST_CHANGES" if blocking else "APPROVE"}
    if comments:
        payload["comments"] = comments
    return payload, len(blocking)


def _gh(*args, data=None):
    res = subprocess.run(["gh", "api", *args], input=data, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"gh api {args[0]} failed: {res.stderr.strip()}")
    return res.stdout


def main():
    repo, pr, head = os.environ["GITHUB_REPOSITORY"], os.environ["PR"], os.environ["HEAD_SHA"]
    try:
        out = json.loads(os.environ.get("REVIEW_JSON") or "null")
        diff = subprocess.run(["gh", "pr", "diff", pr], capture_output=True, text=True)
        # ponytail: no diff (too large for the API) means body-only findings, not a red job.
        commentable = commentable_lines(diff.stdout) if diff.returncode == 0 else {}
        payload, blocking = build_review(out, commentable, head)
    except ValueError as exc:
        print(f"::error::the review produced no usable output ({exc}) — nothing reviewed this PR.")
        return 1

    base = f"repos/{repo}/pulls/{pr}/reviews"
    try:
        review = json.loads(_gh(base, "--method", "POST", "--input", "-", data=json.dumps(payload)))
    except RuntimeError:
        if "comments" not in payload:
            raise
        # A rejected anchor fails the whole review; the body already holds every finding.
        payload.pop("comments")
        review = json.loads(_gh(base, "--method", "POST", "--input", "-", data=json.dumps(payload)))
    print(f"Submitted review {review['id']}: {review['state']} ({blocking} P0/P1, "
          f"{len(payload.get('comments', []))} inline)")

    prior = json.loads(_gh(base, "--paginate", "--slurp"))
    for r in (r for page in prior for r in page):
        if (r["user"]["login"] == BOT
                and r["state"] in ("APPROVED", "CHANGES_REQUESTED")):
            _gh(f"{base}/{r['id']}/dismissals", "--method", "PUT",
                "-f", f"message=Superseded by the review of {head}.", "-f", "event=DISMISS")

    if blocking:
        print(f"::error::{blocking} P0/P1 finding(s) remain — see the review on PR #{pr}.")
        return 1
    return 0


_DIFF = """diff --git a/a.py b/a.py
index 1..2 100644
--- a/a.py
+++ b/a.py
@@ -1,3 +1,4 @@
 keep
-gone
+new1
+++ added line that looks like a header
 tail
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1 +0,0 @@
-x
"""


def _self_test():
    lines = commentable_lines(_DIFF)
    f = lambda sev, line: {"severity": sev, "path": "a.py", "line": line, "title": "t", "body": "b"}
    cases = [
        ("diff: context and added lines are commentable, deleted file is not",
         lines == {"a.py": {1, 2, 3, 4}}),
    ]
    p, n = build_review({"summary": "ran x", "findings": []}, lines, "abc")
    cases.append(("no findings -> APPROVE with LGTM and the head line",
                  p["event"] == "APPROVE" and n == 0 and "LGTM" in p["body"]
                  and p["body"].endswith("Reviewed head: abc") and "comments" not in p))
    p, n = build_review({"summary": "s", "findings": [f("P0", 2), f("P1", 99)]}, lines, "abc")
    cases.append(("P0/P1 -> REQUEST_CHANGES, both in the body",
                  p["event"] == "REQUEST_CHANGES" and n == 2 and p["body"].count("**[P") == 2))
    cases.append(("only the in-diff finding goes inline",
                  [c["line"] for c in p["comments"]] == [2]))
    for bad in (None, {}, {"summary": "", "findings": []}, {"summary": "s"}):
        try:
            build_review(bad, lines, "abc")
            ok = False
        except ValueError:
            ok = True
        cases.append((f"malformed output {bad!r} is refused, never approved", ok))

    for label, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    failed = sum(1 for _, ok in cases if not ok)
    if failed:
        print(f"\nSELF-TEST FAILED: {failed} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} submit-ci-review self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test() if sys.argv[1:] == ["--self-test"] else main())
