#!/usr/bin/env python3
"""Exercise the owned-output boundary used by both APK asset generators."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from generated_asset_directory import BUILD, prune


class GeneratedAssetDirectoryTest(unittest.TestCase):
    def test_incremental_run_removes_only_omitted_assets(self):
        parent = BUILD / "tmp"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="dsha-assets-", dir=parent) as temp:
            output = Path(temp) / "standardAssets"
            (output / "nested").mkdir(parents=True)
            (output / "current.js").write_text("current", encoding="utf-8")
            (output / "nested/obsolete.js").write_text("obsolete", encoding="utf-8")
            prune(output, {"current.js"})
            self.assertEqual((output / "current.js").read_text(encoding="utf-8"), "current")
            self.assertFalse((output / "nested/obsolete.js").exists())
            self.assertFalse((output / "nested").exists())

    def test_output_outside_build_is_not_pruned(self):
        with tempfile.TemporaryDirectory(prefix="dsha-not-generated-") as temp:
            output = Path(temp) / "user-files"
            output.mkdir()
            protected = output / "keep.txt"
            protected.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                prune(output, set())
            self.assertEqual(protected.read_text(encoding="utf-8"), "keep")

    def test_standard_generator_removes_an_asset_deleted_from_its_source(self):
        parent = BUILD / "tmp"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="dsha-standard-incremental-", dir=parent) as temp:
            source = Path(temp) / "source"
            output = Path(temp) / "standardAssets"
            original = BUILD.parent / "src/main/assets"
            for name in ("web-integration/es-compat.inputs.json", "web-integration/es-compat.js",
                         "web-integration/compat.js", "web-integration/startup.js",
                         "glibc-python.tar.gz", "adb-wheels.tar.gz"):
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original / name, target)
            marker = source / "removed-on-next-build.js"
            marker.write_text("old asset", encoding="utf-8")

            def generate() -> None:
                run = subprocess.run([sys.executable, "-B", str(BUILD.parent.parent / "tools/prepare-standard-assets.py"),
                                      "--source", str(source), "--output", str(output)],
                                     cwd=BUILD.parent.parent, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

            generate()
            self.assertTrue((output / marker.name).is_file())
            marker.unlink()
            generate()
            self.assertFalse((output / marker.name).exists())


if __name__ == "__main__":
    unittest.main()
