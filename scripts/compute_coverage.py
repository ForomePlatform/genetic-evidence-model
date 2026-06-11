#!/usr/bin/env python3
"""Compute dimension-coverage counts for the documented corpus from the YAMLs.

For each dimension it reports ``populated`` (items carrying a substantive
value) and ``applicable`` (items whose activation condition holds). A value of
``not_applicable_or_omitted`` (or null/absent) counts as applicable-but-not-
populated. This is the machine-readable basis for Supplementary Note SN7 and
the table in ``annotations/coverage.md``.

Usage:
    python3 scripts/compute_coverage.py           # markdown table to stdout
    python3 scripts/compute_coverage.py --tsv     # tab-separated
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
# The documented corpus: 4 manual + Duerr v0 + Inouye v1.
CORPUS = [
    "annotations/jossin2017.yaml",
    "annotations/davis2011.yaml",
    "annotations/nelson1992.yaml",
    "annotations/gupta2015.yaml",
    "annotations/v0/duerr2006.yaml",
    "annotations/v1/inouye2018.yaml",
]

NA = "not_applicable_or_omitted"
IN_VIVO = {"IN_VIVO", "IN_VIVO_EXPERIMENT"}


def load_items():
    items = []
    for rel in CORPUS:
        data = yaml.safe_load((ROOT / rel).read_text())
        for it in data.get("evidence", []) or []:
            items.append(it)
    return items


def populated(item, *keys):
    """True if any alias key holds a substantive (non-NA, non-empty) value."""
    for k in keys:
        if k not in item:
            continue
        v = item[k]
        if v is None:
            continue
        if isinstance(v, str):
            if v.strip().lower() == NA:
                continue
            return True
        if isinstance(v, list):
            vals = [x for x in v if x is not None and str(x).strip().lower() != NA]
            if vals:
                return True
            continue
        if isinstance(v, dict):
            if str(v.get("annotated_as", "")).strip().lower() == NA:
                continue
            return True
        return True  # bool / number
    return False


def _strset(v):
    if isinstance(v, list):
        return {x for x in v if isinstance(x, str)}
    if isinstance(v, str):
        return {v}
    return set()  # dict (NA form), None, etc. -> no substantive values


def kd(item):
    return _strset(item.get("knowledge_domain"))


def methods(item):
    return _strset(item.get("method"))


def main(argv):
    items = load_items()
    n = len(items)

    # (label, populated-keys, applicable-predicate)
    always = lambda it: True
    rows = [
        ("Knowledge Domain", ["knowledge_domain"], always),
        ("Method", ["method"], always),
        ("Target Type", ["target_type"], always),
        ("Resolution", ["resolution", "target_resolution"], always),
        ("Credibility", ["credibility"], always),
        ("Phenotype Scale", ["phenotype_scale"], always),
        ("Variant Ascertainment", ["variant_ascertainment"],
         lambda it: it.get("target_type") == "VARIANT"),
        ("Mode of Inheritance", ["mode_of_inheritance"],
         lambda it: "HUMAN_GENETICS" in kd(it) and it.get("target_type") == "GENE"),
        ("Mendelian Segregation", ["mendelian_segregation"],
         lambda it: "HUMAN_GENETICS" in kd(it) and it.get("target_type") == "GENE"),
        ("Penetrance", ["penetrance"],
         lambda it: "HUMAN_GENETICS" in kd(it) and it.get("target_type") == "VARIANT"),
        ("Measurement Target", ["measurement_target"],
         lambda it: "GENE_FUNCTION" in kd(it)),
        ("Gene Relation", ["gene_relation"],
         lambda it: "GENE_FUNCTION" in kd(it)),
        ("Organism", ["organism"],
         lambda it: bool(methods(it) & IN_VIVO) or "MODEL_ORGANISM" in kd(it)),
        ("Knockout Type", ["knockout_type"],
         lambda it: "MODEL_ORGANISM" in kd(it)),
    ]

    results = []
    for label, keys, applies in rows:
        applicable = [it for it in items if applies(it)]
        pop = sum(1 for it in applicable if populated(it, *keys))
        results.append((label, pop, len(applicable)))

    sep = "\t" if "--tsv" in argv else None
    print(f"# Dimension coverage over {n} GeneticEvidence items "
          f"(Duerr v0, Inouye v1), computed by scripts/compute_coverage.py")
    if sep:
        print("Dimension\tPopulated\tApplicable")
        for label, pop, app in results:
            print(f"{label}\t{pop}\t{app}")
    else:
        w = max(len(r[0]) for r in results)
        print(f"| {'Dimension':<{w}} | Populated | Applicable |")
        print(f"| {'-'*w} | --------: | ---------: |")
        for label, pop, app in results:
            print(f"| {label:<{w}} | {pop:>9} | {app:>10} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
