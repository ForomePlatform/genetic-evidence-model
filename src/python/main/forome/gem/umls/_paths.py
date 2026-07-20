"""Locate the repository's data and schema directories.

The UMLS crosswalk tooling is a repo-run data project: its inputs/outputs live
in ``data/umls/`` and the schema in ``schema/`` at the repo root, discovered by
walking up from this module. ``GEM_DATA_DIR`` overrides the data directory
(used by tests / alternate checkouts).
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve()


def _repo_root() -> Path:
    for cand in _HERE.parents:
        if (cand / "data" / "umls").is_dir() and (cand / "schema").is_dir():
            return cand
    for cand in _HERE.parents:
        if (cand / "pyproject.toml").is_file():
            return cand
    return _HERE.parents[6]  # src/python/main/forome/gem/umls/_paths.py -> repo


REPO_ROOT = _repo_root()
# The workspace: inventory / crosswalk / adjudications live here. ``GEM_DATA_DIR``
# points the tooling at any mapping directory (which may be empty, e.g. when
# building axes from scratch).
DATA_DIR = Path(os.environ.get("GEM_DATA_DIR", REPO_ROOT / "data" / "umls"))
# Canonical reference data (the UMLS Semantic Network) always resolves to the
# repo's copy, independent of the workspace, so type exploration works even when
# GEM_DATA_DIR is an empty directory.
REFERENCE_DIR = REPO_ROOT / "data" / "umls"
SCHEMA_DIR = REPO_ROOT / "schema"
PAPER_SECTIONS = REPO_ROOT / "paper" / "sections"
