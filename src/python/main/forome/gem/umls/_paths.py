"""Locate the repository's data and schema directories.

The UMLS crosswalk tooling is a repo-run data project: its inputs/outputs live
in ``data/umls/`` and the schema in ``schema/`` at the repo root, discovered by
walking up from this module. ``GEM_DATA_DIR`` overrides the data directory
(used by tests / alternate checkouts).

Standalone installs (``pip install forome-gem``, no repo checkout) fall back
to the synced reference copies packaged in ``forome.gem._reference`` for the
Semantic Network and the SHACL schema, and to the current working directory
as the default workspace (the Studio treats an empty directory as a fresh
workspace).
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve()


def _repo_root() -> Path | None:
    """The repo checkout this module runs from, or None (standalone install)."""
    for cand in _HERE.parents:
        if (cand / "data" / "umls").is_dir() and (cand / "schema").is_dir():
            return cand
    for cand in _HERE.parents:
        if (cand / "pyproject.toml").is_file():
            return cand
    return None


_REPO = _repo_root()
_PACKAGED = _HERE.parent.parent / "_reference"   # forome/gem/_reference

# Kept for repo-mode consumers; in standalone mode it points at the package's
# parent purely so derived paths stay well-defined (they will not exist).
REPO_ROOT = _REPO if _REPO is not None else _HERE.parents[6] if len(_HERE.parents) > 6 else _HERE.parent

# The workspace: inventory / crosswalk / adjudications live here. ``GEM_DATA_DIR``
# points the tooling at any mapping directory (which may be empty, e.g. when
# building axes from scratch). Standalone default: the current directory.
if "GEM_DATA_DIR" in os.environ:
    DATA_DIR = Path(os.environ["GEM_DATA_DIR"])
elif _REPO is not None:
    DATA_DIR = _REPO / "data" / "umls"
else:
    DATA_DIR = Path.cwd()

# Canonical reference data (the UMLS Semantic Network) resolves to the repo's
# copy when in a checkout — independent of the workspace, so type exploration
# works even when GEM_DATA_DIR is an empty directory — and to the packaged
# synced copy otherwise.
REFERENCE_DIR = (_REPO / "data" / "umls") if _REPO is not None else _PACKAGED
# The SHACL schema and dimensions.md: repo ``schema/`` or the packaged copies
# (the packaged layout is flat: the same filenames, no ``schema/`` prefix).
SCHEMA_DIR = (_REPO / "schema") if _REPO is not None else _PACKAGED
PAPER_SECTIONS = REPO_ROOT / "paper" / "sections"
