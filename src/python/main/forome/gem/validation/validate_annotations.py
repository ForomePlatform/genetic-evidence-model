#!/usr/bin/env python3
"""Validate GEM annotation YAML(s) against the SHACL shapes.

With no arguments, validates every annotation under ``annotations/`` (repo
mode, used by CI). With path arguments, validates exactly those YAML files —
e.g. a single annotation handed to the review skill. Each file is converted to
RDF with ``yaml_to_rdf.py``, the schema's class/enumeration declarations are
merged so ``sh:class`` resolves, and ``pyshacl`` is run. Exits non-zero if any
annotation does not conform.

This is the canonical validator: it produces the same verdict the CI uses, so
a skill that ships it does not have to re-invent the YAML->RDF mapping. It
locates ``schema/genetic_evidence.shacl.ttl`` and ``yaml_to_rdf.py`` relative
to itself, so it works both in the repository and inside a flat skill bundle.

Requirements: ``pyshacl rdflib pyyaml``.

Usage:
    python3 scripts/validate_annotations.py                 # whole repo corpus
    python3 scripts/validate_annotations.py path/to/x.yaml  # one or more files
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import rdflib
from pyshacl import validate

SCRIPT_DIR = Path(__file__).resolve().parent


def _find_base() -> Path:
    """Directory that holds schema/genetic_evidence.shacl.ttl (repo root or bundle).

    Walks all ancestors so it works from the deep package location
    (src/python/main/forome/gem/validation/) in the repo AND from the flat
    skill bundle where schema/ sits one or two levels up.
    """
    for cand in (SCRIPT_DIR, *SCRIPT_DIR.parents):
        if (cand / "schema" / "genetic_evidence.shacl.ttl").is_file():
            return cand
    return SCRIPT_DIR.parent.parent  # fallback


BASE = _find_base()
_shacl = BASE / "schema" / "genetic_evidence.shacl.ttl"
if not _shacl.is_file():
    # Standalone install (no repo checkout, no flat bundle): fall back to the
    # synced copy packaged in forome.gem._reference. Guarded import so the
    # flat skill bundle (where forome.gem is not importable) is unaffected.
    try:
        from forome.gem._reference import REFERENCE_DIR as _ref_dir
        if (_ref_dir / "genetic_evidence.shacl.ttl").is_file():
            _shacl = _ref_dir / "genetic_evidence.shacl.ttl"
    except ImportError:
        pass
SHACL = str(_shacl)


def _load_converter():
    """Import yaml_to_rdf.py, standalone (no forome.gem import) so it also works
    inside the flat skill bundle. Tries the package sibling, the flat bundle
    location, then legacy repo layouts."""
    for cand in (SCRIPT_DIR.parent / "extraction" / "yaml_to_rdf.py",  # package
                 SCRIPT_DIR / "yaml_to_rdf.py",                         # flat bundle
                 BASE / "extraction" / "yaml_to_rdf.py",                # legacy repo
                 BASE / "yaml_to_rdf.py"):
        if cand.is_file():
            spec = importlib.util.spec_from_file_location("yaml_to_rdf", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("ERROR: cannot locate yaml_to_rdf.py next to this script "
                     "or under extraction/.")


y2r = _load_converter()


def _corpus():
    return sorted(p for p in (BASE / "annotations").rglob("*.yaml")
                  if "reviews" not in p.parts)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    files = [Path(a) for a in argv] if argv else _corpus()
    if not files:
        print("No annotation files found.")
        return 1
    failed = []
    for p in files:
        if not p.is_file():
            print(f"FAIL  {p} (file not found)")
            failed.append(p)
            continue
        data = rdflib.Graph().parse(data=y2r.convert(p), format="turtle")
        data.parse(SHACL)  # merge enum/class declarations so sh:class resolves
        conforms, _, text = validate(data, shacl_graph=SHACL, advanced=True)
        try:
            label = p.resolve().relative_to(BASE)
        except ValueError:
            label = p
        print(f"{'PASS' if conforms else 'FAIL'}  {label}")
        if not conforms:
            failed.append(label)
            for line in text.splitlines():
                s = line.strip()
                if s.startswith(("Message:", "Focus Node:")):
                    print("      " + s)
    if failed:
        print(f"\n{len(failed)} annotation(s) failed SHACL validation: "
              + ", ".join(str(f) for f in failed))
        return 1
    print("\nAll annotations conform to the SHACL shapes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
