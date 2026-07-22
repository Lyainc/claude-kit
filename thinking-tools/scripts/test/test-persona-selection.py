#!/usr/bin/env python3
"""Regression test: the persona-pool Selection Rule picks what it claims to (#418).

The rule in `thinking-tools/reference/personas.md` is prose an LLM follows, not code —
so this executes the same rule against the live tag table and asserts the outcome.
It exists because raw substring matching silently mis-selected: `ui` hit "build",
`db` hit "feedback", `doc` hit "docker", `test` hit "latest". Selection is deterministic
AND silent, so a false hit outranks a real one with nobody looking.

Checks:
1. Every Latin tag is word-start-safe against a corpus of common unrelated words.
2. No single-character Hangul tags (`글` matches "구글", `톤` matches "버튼").
3. Fixture topics select the expected personas (positive + negative).
4. The cut rule honours the 5-entry ceiling / 3-entry floor.
5. Both skills feed the rule the SAME input (the user's original topic text), and the
   2026-07-22 measurement showing why that matters is pinned as a fixture (#423). The
   previous form of this check ("rank 1 is inside the cut") was a tautology — every cut
   starts at rank 1, so it could not fail on any pool or topic.

Usage:
    python3 thinking-tools/scripts/test/test-persona-selection.py
    python3 thinking-tools/scripts/test/test-persona-selection.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_POOL_PATH = _REPO_ROOT / "thinking-tools" / "reference" / "personas.md"

_HANGUL = re.compile(r"[가-힣]")


# ---------------------------------------------------------------------------
# The Selection Rule (personas.md §Selection Rule), executed
# ---------------------------------------------------------------------------

def parse_pool(text: str) -> list[tuple[str, list[str]]]:
    """Return [(id, tags)] from the Pool table rows, in file order."""
    pool: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*`(P\d+)`\s*\|(.*)\|\s*$", line)
        if not m:
            continue
        tags = [t.strip().lower() for t in m.group(2).split("|")[-1].split(",")]
        pool.append((m.group(1), [t for t in tags if t]))
    return pool


def tag_matches(tag: str, haystack: str) -> bool:
    """Step 2: Hangul tags match as substrings, Latin tags only at a word start."""
    if _HANGUL.search(tag):
        return tag in haystack
    return re.search(r"(?<![a-z0-9])" + re.escape(tag), haystack) is not None


def select(pool, topic: str) -> tuple[list[str], int]:
    """Steps 1-5. Returns (selected ids in rank order, adhoc count)."""
    hay = topic.lower()
    scored = [
        (sum(1 for t in tags if tag_matches(t, hay)), i, pid)
        for i, (pid, tags) in enumerate(pool)
    ]
    ranked = sorted([s for s in scored if s[0] > 0], key=lambda s: (-s[0], s[1]))
    ids = [pid for _, _, pid in ranked]
    if len(ids) >= 3:
        return ids[: min(5, len(ids))], 0
    return ids, 3 - len(ids)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

# Words that must never score a hit — the exact collisions raw substring matching caused,
# plus their neighbours. Every entry has to be a word that plausibly appears in a real review
# topic; padding the list with words nobody writes ("costume" for `cost`) only forces tag
# contortions for collisions that never happen. Extend when a real false positive shows up.
_DECOY_WORDS = [
    "build", "quick", "guide", "requirement", "fluid", "suit",
    "feedback", "shops", "drops", "workshops",
    "latest", "fastest", "greatest", "contest", "protest",
    "docker", "download", "illegal", "author", "authoring",
]

_FIXTURES = [
    # (topic, must-include, must-exclude)
    ("로그인 토큰 만료를 어떻게 처리할까", ["P1"], ["P3", "P6"]),
    ("quick build pipeline 개선", [], ["P3"]),          # `ui` must not hit "build"
    ("user feedback loop 설계", [], ["P5"]),            # `db` must not hit "feedback"
    ("docker 배포 롤백 절차", ["P4"], ["P10"]),          # `doc` must not hit "docker"
    ("latest release 자동화", [], ["P6"]),              # `test` must not hit "latest"
    ("캐시 도입으로 p99 latency 개선", ["P2"], []),
    ("이 문서의 네이밍이 헷갈려요", ["P10"], []),
]


# The 2026-07-22 divergence measurement (#418 run log → #423). One claim, two texts: as the
# user submitted it, and after Steelman construction. The selected sets differ — which is the
# whole reason both skills must run the rule on the submitted text and never on the Steelman.
# `topic` is verbatim from the run log; the Steelman text was not captured there, so `steelman`
# is reconstructed to reproduce the recorded set (P6 out, P3/P7 in).
_DIVERGENCE = {
    "topic": (
        "사내 API 게이트웨이에 OAuth 토큰 캐시를 도입해 인증 지연을 줄일지 결정한다. "
        "로그인 요청마다 인증 서버를 호출하는 현재 구조는 p99 지연이 크고, 캐시를 두면 "
        "성능은 좋아지지만 토큰 무효화가 늦어져 보안 위험이 생긴다."
    ),
    "topic_expected": ["P1", "P2", "P6"],
    "steelman": (
        "토큰 캐시 도입은 정당하다. 인증 서버 왕복을 없애 로그인 응답의 p99 지연을 줄이면 "
        "사용자가 체감하는 대기가 짧아지고, 인증 서버 호출 비용도 함께 내려간다. 캐시 TTL을 "
        "짧게 잡으면 토큰 무효화 지연은 그 TTL 안으로 갇히므로 보안 노출은 제한적이고, "
        "남는 이득은 성능과 비용 양쪽에서 크다."
    ),
    "steelman_expected": ["P1", "P2", "P3", "P7"],
}

# Files that define or invoke the rule. Each must name the shared input and must not aim the
# rule at the Steelman. `section` limits the scan to one `## ` section; None scans the
# rule-mentioning paragraphs. Prose, so both checks are literal: a phrase that must appear and
# a phrasing that must not. Discussing the Steelman is fine — "run it ON the Steelman" is not.
_CONSUMERS = [
    ("thinking-tools/reference/personas.md", "Selection Rule"),
    ("thinking-tools/skills/expert-panel/SKILL.md", None),
    ("thinking-tools/skills/adversarial-review/SKILL.md", None),
]

_INPUT_PHRASE = "original topic text"
_AIMED_AT_STEELMAN = re.compile(r"(?:on|from|against) the [\w ]*Steelman")


def _section(text: str, heading: str) -> str:
    """The `## {heading}` section body, up to the next `## `."""
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def _fail(msgs: list[str], msg: str) -> None:
    msgs.append(msg)


def run_checks(pool) -> list[str]:
    failures: list[str] = []

    # 1 + 2: tag hygiene
    for pid, tags in pool:
        for tag in tags:
            if _HANGUL.search(tag):
                if len(tag) < 2:
                    _fail(failures, f"{pid}: single-character Hangul tag {tag!r} — too collision-prone")
                continue
            for decoy in _DECOY_WORDS:
                if tag_matches(tag, decoy):
                    _fail(failures, f"{pid}: tag {tag!r} falsely matches unrelated word {decoy!r}")

    # 3: fixture selection
    for topic, must_include, must_exclude in _FIXTURES:
        ids, adhoc = select(pool, topic)
        for pid in must_include:
            if pid not in ids:
                _fail(failures, f"topic {topic!r}: expected {pid} in selection, got {ids}")
        for pid in must_exclude:
            if pid in ids:
                _fail(failures, f"topic {topic!r}: {pid} should not match, got {ids}")

        # 4: cut rule
        if len(ids) > 5:
            _fail(failures, f"topic {topic!r}: {len(ids)} entries exceeds the 5-entry ceiling")
        if len(ids) + adhoc < 3:
            _fail(failures, f"topic {topic!r}: {len(ids)}+{adhoc} below the 3-expert floor")

    return failures


def check_shared_input(pool) -> list[str]:
    """5: the two skills run the rule on one shared input, and the case proving it matters."""
    failures: list[str] = []

    # 5a: the pinned measurement still reproduces — derived text really does select differently
    got = {k: select(pool, _DIVERGENCE[k])[0] for k in ("topic", "steelman")}
    for k, ids in got.items():
        if ids != _DIVERGENCE[f"{k}_expected"]:
            _fail(failures, f"#423 divergence fixture ({k}): expected "
                            f"{_DIVERGENCE[f'{k}_expected']}, got {ids}")
    if got["topic"] == got["steelman"]:
        _fail(failures, "#423 divergence fixture no longer diverges — re-measure it or drop it; "
                        "as-is it no longer demonstrates why the input must be fixed")

    # 5b: no consumer aims the rule at the Steelman, and each names the shared input
    for rel, section in _CONSUMERS:
        path = _REPO_ROOT / rel
        if not path.is_file():
            _fail(failures, f"{rel}: not found — the Selection Rule's consumer set moved")
            continue
        text = path.read_text(encoding="utf-8")
        if section:
            scope = _section(text, section)
            if not scope:
                _fail(failures, f"{rel}: '## {section}' section not found")
        else:
            scope = "\n\n".join(b for b in text.split("\n\n") if "Selection Rule" in b)

        scope = re.sub(r"[\s*_`]+", " ", scope)  # these files hard-wrap and bold mid-phrase
        if _INPUT_PHRASE not in scope:
            _fail(failures, f"{rel}: the Selection Rule is invoked without naming its input "
                            f"{_INPUT_PHRASE!r} — the two skills' inputs stop being provably the same")
        aimed = _AIMED_AT_STEELMAN.search(scope)
        if aimed:
            _fail(failures, f"{rel}: Selection Rule aimed at model-authored text "
                            f"({aimed.group(0)!r}) — a Steelman varies run to run, so the "
                            f"selection would too (#423)")

    return failures


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run_self_test() -> int:
    """In-memory: a planted-violation pool must fail, a clean one must pass."""
    dirty = "| `P1` | X | s | c | v | ui, db, doc, 글 |\n"
    clean = "| `P1` | X | s | c | v | security, 보안 |\n"

    cases = [
        ("planted collisions are caught", dirty, False),
        ("clean pool passes tag hygiene", clean, True),
    ]
    failures = []
    for name, table, should_pass in cases:
        pool = parse_pool(table)
        if not pool:
            failures.append(f"{name}: pool table failed to parse")
            continue
        # tag hygiene only — fixtures assume the real 10-entry pool
        hygiene = [f for f in run_checks(pool) if "falsely matches" in f or "Hangul tag" in f]
        if should_pass and hygiene:
            failures.append(f"{name}: expected clean, got {hygiene}")
        if not should_pass and not hygiene:
            failures.append(f"{name}: expected violations, got none")

    # matcher semantics
    for tag, hay, expected in [
        ("test", "latest release", False),
        ("test", "testing plan", True),
        ("db", "feedback loop", False),
        ("db", "db 마이그레이션", True),
        ("보안", "보안성 검토", True),
    ]:
        if tag_matches(tag, hay) is not expected:
            failures.append(f"tag_matches({tag!r}, {hay!r}) != {expected}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: all {len(cases) + 5} test-persona-selection self-test cases passed")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        return run_self_test()

    if not _POOL_PATH.is_file():
        print(f"FAIL: pool not found at {_POOL_PATH}")
        return 1
    pool = parse_pool(_POOL_PATH.read_text(encoding="utf-8"))
    if len(pool) < 3:
        print(f"FAIL: parsed only {len(pool)} pool entries from {_POOL_PATH}")
        return 1

    failures = run_checks(pool) + check_shared_input(pool)
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: all persona-selection checks passed "
        f"({len(pool)} pool entries, {len(_FIXTURES)} topic fixtures, "
        f"{len(_DECOY_WORDS)} decoy words, {len(_CONSUMERS)} shared-input consumers)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
