from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from check_release_version import ReleaseVersionError, validate_release


class ReleaseVersionCheckTests(unittest.TestCase):
    def make_repo(self, tauri: str = "0.1.18", cargo: str = "0.1.18") -> Path:
        root = Path(tempfile.mkdtemp())
        manifest = root / "ui" / "src-tauri"
        manifest.mkdir(parents=True)
        (manifest / "tauri.conf.json").write_text(json.dumps({"version": tauri}))
        (manifest / "Cargo.toml").write_text(
            f'[package]\nname = "filingforge"\nversion = "{cargo}"\n'
        )
        return root

    def test_accepts_stable_and_beta_tags_for_manifest_version(self):
        root = self.make_repo()

        self.assertEqual(validate_release(root, "v0.1.18"), "0.1.18")
        self.assertEqual(validate_release(root, "v0.1.18-beta1"), "0.1.18")

    def test_rejects_tag_for_an_old_internal_version(self):
        with self.assertRaisesRegex(ReleaseVersionError, "tag version 0.1.17"):
            validate_release(self.make_repo(), "v0.1.17-beta1")

    def test_rejects_malformed_release_tag(self):
        with self.assertRaisesRegex(ReleaseVersionError, "valid release tag"):
            validate_release(self.make_repo(), "release-0.1.18")

    def test_rejects_tauri_and_cargo_manifest_drift(self):
        with self.assertRaisesRegex(ReleaseVersionError, "manifest versions differ"):
            validate_release(self.make_repo(cargo="0.1.13"), "v0.1.18-beta1")

    def test_can_check_manifest_consistency_without_a_tag(self):
        self.assertEqual(validate_release(self.make_repo(), None), "0.1.18")


if __name__ == "__main__":
    unittest.main()
