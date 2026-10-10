#!/usr/bin/env python3
"""Deterministic manifest JSON/mtime race and incremental regressions (#844)."""

import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "generate-manifest.py"
SPEC = importlib.util.spec_from_file_location("generate_manifest", SCRIPT)
manifest_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest_module)


class ManifestFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = Path(self.temp.name)
        self.out = self.vault / ".vault-bridge" / "manifest.json"
        self.out.parent.mkdir()
        self.stamp = int(time.time()) - 100
        self.source = self.vault / "source.md"
        self.write_note(self.source, "Old", "Original body", self.stamp)
        self.write_note(self.vault / "target.md", "Target", "Target body", self.stamp)
        self.refresh(force=True)
        os.utime(self.out, (self.stamp + 1, self.stamp + 1))

    def write_note(self, path, title, body, mtime):
        path.write_text(f"---\ntype: note\ntags: [test]\n---\n# {title}\n\n{body}\n",
                        encoding="utf-8")
        os.utime(path, (mtime, mtime))

    def refresh(self, force=False):
        manifest, stats = manifest_module.generate(self.vault, self.out, force)
        manifest_module._atomic_write_text(self.out, json.dumps(manifest))
        return manifest, stats

    def assert_matches_full_scan(self, actual):
        expected, _ = manifest_module.generate(self.vault, self.out, True)
        self.assertEqual({k: v for k, v in actual.items() if k != "generated_at"},
                         {k: v for k, v in expected.items() if k != "generated_at"})

    def test_replacement_after_json_load_does_not_reuse_old_entry(self):
        # The edit precedes both requests. Inject B's entire write after A loads JSON.
        self.write_note(self.source, "Changed", "Changed body [[target]]", self.stamp + 2)
        real_load = manifest_module._load_existing_manifest
        b_titles = []

        def load_then_replace(path):
            cached = real_load(path)
            self.assertEqual(cached["files"][0]["title"], "Old")
            latest, _ = self.refresh(force=True)
            b_titles.append(latest["files"][0]["title"])
            self.assertGreater(self.out.stat().st_mtime, self.source.stat().st_mtime)
            return cached

        with mock.patch.object(manifest_module, "_load_existing_manifest",
                               side_effect=load_then_replace):
            actual, stats = self.refresh()

        self.assertEqual(b_titles, ["Changed"])
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(json.loads(self.out.read_text())["files"][0]["title"], "Changed")
        self.assert_matches_full_scan(actual)

    def test_replacement_before_json_load_is_conservative(self):
        self.write_note(self.source, "Changed", "Changed body [[target]]", self.stamp + 2)
        real_load = manifest_module._load_existing_manifest

        def replace_then_load(path):
            self.refresh(force=True)
            return real_load(path)

        with mock.patch.object(manifest_module, "_load_existing_manifest",
                               side_effect=replace_then_load):
            actual, _ = self.refresh()
        self.assert_matches_full_scan(actual)

    def test_unchanged_entries_still_use_cache(self):
        with mock.patch.object(manifest_module, "_build_entry",
                               wraps=manifest_module._build_entry) as build:
            actual, stats = self.refresh()
        self.assertEqual(build.call_count, 0)
        self.assertEqual(stats["updated"], 0)
        self.assert_matches_full_scan(actual)

    def test_add_change_delete_matches_full_scan(self):
        self.write_note(self.source, "Changed", "Changed body", self.stamp + 2)
        self.write_note(self.vault / "added.md", "Added", "[[source]]", self.stamp + 2)
        (self.vault / "target.md").unlink()
        actual, stats = self.refresh()
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["removed"], 1)
        self.assert_matches_full_scan(actual)

    def test_subsecond_edit_is_not_rounded_away(self):
        os.utime(self.out, (self.stamp + .25, self.stamp + .25))
        self.write_note(self.source, "Changed", "Changed body", self.stamp + .5)
        self.assertGreater(self.source.stat().st_mtime, self.out.stat().st_mtime)
        self.assertEqual(int(self.source.stat().st_mtime), int(self.out.stat().st_mtime))
        actual, stats = self.refresh()
        self.assertEqual(stats["updated"], 1)
        self.assert_matches_full_scan(actual)

    def test_force_does_not_consult_cache_or_cutoff(self):
        self.write_note(self.source, "Changed", "Changed body", self.stamp + 2)
        with mock.patch.object(manifest_module, "_load_existing_manifest",
                               side_effect=AssertionError("force loaded cache")), \
             mock.patch.object(manifest_module, "_manifest_mtime",
                               side_effect=AssertionError("force read cutoff")):
            actual, _ = self.refresh(force=True)
        self.assert_matches_full_scan(actual)

    def test_absent_or_corrupt_cache_recovers(self):
        for content in (None, "{broken", '{"not_files": []}'):
            with self.subTest(content=content):
                if content is None:
                    self.out.unlink()
                else:
                    self.out.write_text(content, encoding="utf-8")
                actual, _ = self.refresh()
                self.assert_matches_full_scan(actual)

    def test_cache_deleted_before_json_read_recovers(self):
        real_read = Path.read_text

        def delete_then_read(path, *args, **kwargs):
            if path == self.out:
                path.unlink()
            return real_read(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", delete_then_read):
            actual, _ = self.refresh()
        self.assert_matches_full_scan(actual)

    def test_cache_deleted_after_json_read_remains_fresh(self):
        self.write_note(self.source, "Changed", "Changed body", self.stamp + 2)
        real_load = manifest_module._load_existing_manifest

        def load_then_delete(path):
            cached = real_load(path)
            path.unlink()
            return cached

        with mock.patch.object(manifest_module, "_load_existing_manifest",
                               side_effect=load_then_delete):
            actual, _ = self.refresh()
        self.assert_matches_full_scan(actual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
