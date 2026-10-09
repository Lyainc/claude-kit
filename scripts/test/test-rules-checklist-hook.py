#!/usr/bin/env python3
"""Exercise the work-rules reminder with real Git status and hook JSON."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[1] / "rules-checklist-hook.sh"


@unittest.skipUnless(shutil.which("jq"), "the hook requires jq")
class RulesChecklistHookTest(unittest.TestCase):
    def call_hook(self, changed_path=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", folder], check=True)
            if changed_path:
                path = root / changed_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n", encoding="utf-8")
                subprocess.run(["git", "-C", folder, "add", "-f", "--", changed_path], check=True)
            result = subprocess.run(
                ["bash", str(HOOK)], input="{}", text=True, capture_output=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": folder, "CLAUDE_KIT_RULES_HOOK_DISABLE": "0"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            return result.stdout

    def assert_reminder(self, changed_path):
        payload = json.loads(self.call_hook(changed_path))
        self.assertEqual(set(payload), {"systemMessage"})
        self.assertIn("rules/RULES.md", payload["systemMessage"])

    def test_codex_marketplace_reminds(self):
        self.assert_reminder(".agents/plugins/marketplace.json")

    def test_claude_marketplace_reminds(self):
        self.assert_reminder(".claude-plugin/marketplace.json")

    def test_rule_script_reminds(self):
        self.assert_reminder("scripts/example.py")

    def test_unrelated_change_is_silent(self):
        self.assertEqual(self.call_hook("example.txt"), "")

    def test_clean_tree_is_silent(self):
        self.assertEqual(self.call_hook(), "")


if __name__ == "__main__":
    unittest.main()
