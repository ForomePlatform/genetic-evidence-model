"""The packaged reference copies (forome.gem._reference) must stay in sync
with their repo sources of truth, and the standalone fallback must be able to
serve them. Guards the PyPI release story (scripts/release-pypi.sh re-syncs;
this test catches drift in between)."""
import unittest
from pathlib import Path

from forome.gem._reference import REFERENCE_DIR as PACKAGED
from forome.gem.umls._paths import REPO_ROOT

SYNCED = {
    "semantic_types.yaml": Path("data/umls/semantic_types.yaml"),
    "genetic_evidence.shacl.ttl": Path("schema/genetic_evidence.shacl.ttl"),
    "dimensions.md": Path("schema/dimensions.md"),
}


class TestPackagedReference(unittest.TestCase):
    def test_packaged_files_present(self):
        for name in SYNCED:
            self.assertTrue((PACKAGED / name).is_file(), name)

    def test_packaged_files_match_sources(self):
        for name, rel in SYNCED.items():
            src = REPO_ROOT / rel
            if not src.is_file():          # standalone install: nothing to compare
                self.skipTest("no repo checkout")
            self.assertEqual(
                (PACKAGED / name).read_bytes(), src.read_bytes(),
                f"{name} drifted from {rel} — run scripts/release-pypi.sh "
                f"(or cp {rel} src/python/main/forome/gem/_reference/)")


if __name__ == "__main__":
    unittest.main()
