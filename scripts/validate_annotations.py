#!/usr/bin/env python3
"""Validate every released annotation YAML against the SHACL shapes.

Converts each annotation to RDF with ``extraction/yaml_to_rdf.py``, merges the
class/enumeration declarations from the SHACL file so ``sh:class`` resolves,
and runs ``pyshacl``. Exits non-zero if any annotation does not conform, so it
can gate CI.

Usage:
    python3 scripts/validate_annotations.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import rdflib
from pyshacl import validate

ROOT = Path(__file__).resolve().parent.parent
SHACL = str(ROOT / "schema" / "genetic_evidence.shacl.ttl")

# Load the converter as a module.
_spec = importlib.util.spec_from_file_location(
    "yaml_to_rdf", ROOT / "extraction" / "yaml_to_rdf.py")
y2r = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(y2r)


def annotation_files():
    return sorted(
        p for p in (ROOT / "annotations").rglob("*.yaml")
        if "reviews" not in p.parts)


def main():
    failed = []
    for p in annotation_files():
        ttl = y2r.convert(p)
        data = rdflib.Graph().parse(data=ttl, format="turtle")
        data.parse(SHACL)  # merge enum/class declarations for sh:class
        conforms, _, text = validate(data, shacl_graph=SHACL, advanced=True)
        rel = p.relative_to(ROOT)
        print(f"{'PASS' if conforms else 'FAIL'}  {rel}")
        if not conforms:
            failed.append(rel)
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
