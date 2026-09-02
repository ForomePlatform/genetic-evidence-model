"""Packaged copies of the repository's reference data, so a pip-installed
`forome-gem` works outside a repo checkout (the walk-up discovery in
`forome.gem.umls._paths` prefers the repo copies when present).

These files are SYNCED COPIES, not sources of truth. The sources are
`data/umls/semantic_types.yaml`, `schema/genetic_evidence.shacl.ttl` and
`schema/dimensions.md` at the repo root; `scripts/release-pypi.sh` re-syncs
them before building, and the test suite asserts they match.
"""
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent
