#!/usr/bin/env python3
"""
Regression test — feedback-loop/scripts/plugin-map.json vs each plugin's real
skills/agents dirs (#664 root cause).

The bug this pins: plugin-map.json is a hand-maintained bare-name -> plugin
lookup used by event-logger.sh's resolve_plugin() (event-logger.sh:108, called
at :199 skill_invoke, :218 agent_spawn, :243 command_run). #664 traced a
plugin=unknown telemetry mystery to four claude-kit-owned skills
(issue-raise, next-goal, add-policy, distill) missing from this map — nothing
enforced the map staying in sync with the skills/agents dirs it describes, so
a new skill silently telemetry-attributes as "unknown" forever.

Scope: only checks the catalog-subset-of-map direction (every real skill/agent
name must have a map entry) — that's the direction that actually breaks
attribution. A map entry with no matching skill/agent (a retired one, left
stale) still resolves fine and is out of scope here.

Run: python3 feedback-loop/scripts/test/test-plugin-map-drift.py
Exit 0 on pass, 1 on fail.
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]  # feedback-loop/scripts
REPO_ROOT = SCRIPT_DIR.parent.parent               # repo root
PLUGIN_MAP = SCRIPT_DIR / "plugin-map.json"


def scan_names(repo_root: Path) -> dict[str, str]:
    """bare skill/agent name -> plugin, from every top-level plugin dir's
    skills/*/SKILL.md and agents/*.md."""
    names: dict[str, str] = {}
    for skill_md in repo_root.glob("*/skills/*/SKILL.md"):
        plugin, _, skill_name, _ = skill_md.relative_to(repo_root).parts
        if plugin.startswith("."):
            continue
        names[skill_name] = plugin
    for agent_md in repo_root.glob("*/agents/*.md"):
        plugin, _, _ = agent_md.relative_to(repo_root).parts
        if plugin.startswith("."):
            continue
        names[agent_md.stem] = plugin
    return names


def main() -> int:
    catalog = scan_names(REPO_ROOT)
    plugin_map = json.loads(PLUGIN_MAP.read_text(encoding="utf-8"))

    missing = sorted(
        f"{name} ({plugin})"
        for name, plugin in catalog.items()
        if name not in plugin_map
    )
    if missing:
        print("FAIL: plugin-map.json is missing entries for:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    print(f"OK: plugin-map.json covers all {len(catalog)} skill/agent names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
