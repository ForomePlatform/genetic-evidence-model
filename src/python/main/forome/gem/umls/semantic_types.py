#!/usr/bin/env python3
"""Load the UMLS Semantic Network reference (semantic_types.yaml, produced by
fetch_semantic_network.py) and provide subtree + lookup helpers used by the
crosswalk harness to constrain value searches by a dimension's axis type.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from forome.gem.umls._paths import DATA_DIR, REFERENCE_DIR

_BY_TUI: dict | None = None


def _types_yaml() -> Path:
    """The Semantic Network reference: prefer the workspace's copy, else fall
    back to the repo's canonical one so type exploration works with an empty
    workspace."""
    local = DATA_DIR / "semantic_types.yaml"
    return local if local.is_file() else REFERENCE_DIR / "semantic_types.yaml"


def _load() -> dict:
    global _BY_TUI
    if _BY_TUI is None:
        yml = _types_yaml()
        if yml.is_file():
            doc = yaml.safe_load(yml.read_text()) or {}
            _BY_TUI = {t["tui"]: t for t in (doc.get("types") or [])}
        else:
            _BY_TUI = {}
    return _BY_TUI


def get(tui: str) -> dict | None:
    return _load().get(tui)


def subtree_tuis(tui: str) -> set[str]:
    """The TUI plus all its descendants, by semantic-network tree-number prefix.

    So a dimension whose axis is T082 (Spatial Concept, tree A2.1.5) constrains
    its value search to A2.1.5 and everything under it (Molecular Sequence,
    Nucleotide Sequence, ...), which is exactly the set a value of that axis may
    faithfully map to.
    """
    types = _load()
    root = types.get(tui)
    if not root or not root.get("tree_number"):
        return {tui} if tui else set()
    prefix = root["tree_number"]

    def under(tree: str) -> bool:
        # descendant iff equal, or extends the prefix at a level boundary.
        # Levels below a single-letter root (A -> A1 -> A1.1) have no dot,
        # so "A1" is a child of "A" even though "A." is not its prefix.
        if not tree:
            return False
        if tree == prefix:
            return True
        return tree.startswith(prefix) and (len(prefix) == 1
                                            or tree[len(prefix)] == ".")

    return {t["tui"] for t in types.values() if under(t.get("tree_number") or "")}


def filter_param(tui: str | None) -> str | None:
    """Comma-joined TUI list for the UTS `semanticTypes` search parameter."""
    if not tui:
        return None
    tuis = subtree_tuis(tui)
    return ",".join(sorted(tuis)) if tuis else None


def _by_tree() -> dict:
    return {t["tree_number"]: t for t in _load().values() if t.get("tree_number")}


def _row(t: dict) -> dict:
    return {"tui": t["tui"], "name": t["name"], "tree": t.get("tree_number")}


def most_specific(tuis: list[str]) -> str | None:
    """The deepest (most specific) of several semantic types, by tree depth."""
    cand = [_load().get(t) for t in tuis if _load().get(t)]
    if not cand:
        return None
    return max(cand, key=lambda x: len((x.get("tree_number") or "").split(".")))["tui"]


def path_to(tui: str, axis_tui: str | None) -> list[dict]:
    """Path (deepest-first) from a semantic type up to ``axis_tui`` if it is a
    descendant, ending at the axis type; otherwise the walk continues to the
    branch root. Each element is {tui, name, tree}. Empty if tui is unknown."""
    types = _load()
    t = types.get(tui)
    if not t or not t.get("tree_number"):
        return [_row(t)] if t else []
    by_tree = _by_tree()
    axis = types.get(axis_tui) if axis_tui else None
    axis_tree = axis.get("tree_number") if axis else None
    path, cur = [], t["tree_number"]
    while True:
        node = by_tree.get(cur)
        if node:
            path.append(_row(node))
        if axis_tree and cur == axis_tree:
            break
        if "." in cur:
            cur = cur.rsplit(".", 1)[0]
        elif len(cur) > 1:
            cur = cur[0]          # A1 -> A, B2 -> B: the single-letter root
        else:
            break
    return path


def all_types() -> list:
    """All semantic TYPES (A/B branches), tree-ordered, for the UI picker."""
    def key(t):
        import re
        out = []
        for p in (t.get("tree_number") or "").split("."):
            m = re.match(r"([A-Za-z]*)(\d+)", p)
            out.append((m.group(1), int(m.group(2))) if m else ("", 0))
        return out
    return sorted((t for t in _load().values()
                   if (t.get("tree_number") or "").startswith(("A", "B"))), key=key)
