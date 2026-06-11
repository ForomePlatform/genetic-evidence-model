#!/usr/bin/env python3
"""Convert a Genetic Evidence Model annotation YAML to RDF (Turtle).

The emitted RDF is what the SHACL shapes in ``schema/genetic_evidence.shacl.ttl``
validate. Every ``GeneticEvidence`` item becomes a ``gem:GeneticEvidence``
node carrying its dimension values (as ``gem:`` IRIs for categorical
dimensions, literals for free-text ones) and its assertions, each with a
``gem:sourceSpan`` blank node.

Design notes
------------
* Field-name aliases are normalised: ``resolution``/``target_resolution`` and
  source-span ``key_phrase``/``phrase`` (the v0 -> v1 protocol rename).
* Legacy method synonyms are mapped to canonical values
  (``IN_VIVO_EXPERIMENT`` -> ``IN_VIVO`` etc.) so the shapes need only the
  canonical enumeration.
* The explicit escape value ``not_applicable_or_omitted`` (used when a
  curator considered a dimension and chose not to fill it) is emitted as
  ``gem:NOT_APPLICABLE_OR_OMITTED``; the shapes accept it as "addressed".

Usage:
    python3 extraction/yaml_to_rdf.py annotations/jossin2017.yaml [out.ttl]
    python3 extraction/yaml_to_rdf.py annotations/*.yaml --stdout
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

GEM = "https://w3id.org/genetic-evidence-model/"
NA = "NOT_APPLICABLE_OR_OMITTED"

# Categorical dimensions: YAML key -> gem: property local name. Values become
# gem:<VALUE> IRIs (drawn from the enumerations declared in the SHACL file).
CATEGORICAL = {
    "knowledge_domain": "knowledgeDomain",
    "method": "method",
    "target_type": "targetType",
    "resolution": "resolution",
    "target_resolution": "resolution",   # v1 alias
    "credibility": "credibility",
    "phenotype_scale": "phenotypeScale",
    "variant_ascertainment": "variantAscertainment",
    "measurement_target": "measurementTarget",
    "gene_relation": "geneRelation",
    "knockout_type": "knockoutType",
    "mode_of_inheritance": "modeOfInheritance",
    "penetrance": "penetrance",
}

# Free-text dimensions emitted as plain literals.
LITERAL_DIMS = {
    "organism": "organism",
    "target": "target",
    "specificity_of_phenotype": "specificityOfPhenotype",
    "subdomain": "subdomain",   # enum values contain spaces ("Candidate Gene Study")
}

# A value safe to use as a Turtle IRI local name (no spaces/punctuation).
import re as _re
_TOKEN = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Boolean dimensions.
BOOLEAN_DIMS = {
    "mendelian_segregation": "mendelianSegregation",
    "exact_variant": "exactVariant",
    "genetic_background_considered": "geneticBackgroundConsidered",
}

# Legacy method synonyms -> canonical value (dimensions.md "Backward compatibility").
METHOD_SYNONYMS = {
    "IN_VIVO_EXPERIMENT": "IN_VIVO",
    "IN_VITRO_EXPERIMENT": "IN_VITRO",
    "BIOINFORMATICS_PREDICTION": "BIOINFORMATICS_INFERENCE",
}


def esc(text: str) -> str:
    """Escape a string for a Turtle long-literal (triple-quoted)."""
    return str(text).replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def _values(raw):
    """Normalise a YAML dimension value into a list of scalar strings."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [v for v in raw if v is not None]
    if isinstance(raw, dict):
        # e.g. hpo_terms: {annotated_as: not_applicable_or_omitted, ...}
        if raw.get("annotated_as"):
            return [raw["annotated_as"]]
        return []
    return [raw]


def _iri_value(prop: str, val) -> str:
    """Map a scalar dimension value to a gem: IRI local name."""
    s = str(val).strip()
    if s.lower() == "not_applicable_or_omitted":
        return NA
    if prop == "method":
        s = METHOD_SYNONYMS.get(s, s)
    return s


def item_triples(item: dict, idx: int) -> list[str]:
    """Return a list of Turtle blocks for one GeneticEvidence item."""
    raw_id = str(item.get("id", f"item{idx}"))
    node = f"gem:item_{raw_id.replace('.', '_').replace('-', '_')}"
    item_props = [f'gem:itemId "{esc(raw_id)}"']
    extra_blocks = []  # assertion + source-span nodes, declared separately

    for key, prop in CATEGORICAL.items():
        for v in _values(item.get(key)):
            tok = _iri_value(prop, v)
            if _TOKEN.match(tok):
                item_props.append(f"gem:{prop} gem:{tok}")
            else:  # value is not a clean enum token; keep it as a literal
                item_props.append(f'gem:{prop} """{esc(v)}"""')

    for key, prop in LITERAL_DIMS.items():
        if item.get(key) not in (None, ""):
            item_props.append(f'gem:{prop} """{esc(item[key])}"""')

    for key, prop in BOOLEAN_DIMS.items():
        if item.get(key) is not None:
            b = "true" if item[key] in (True, "true", "True") else "false"
            item_props.append(f"gem:{prop} {b}")

    for a_i, a in enumerate(item.get("assertions", []) or []):
        an = f"{node}_a{a_i}"
        span = a.get("source_span") or {}
        phrase = span.get("phrase", span.get("key_phrase"))
        page = span.get("page")
        a_props = [f'gem:assertionId "{esc(a.get("id", f"{raw_id}.A{a_i}"))}"']
        if a.get("statement"):
            a_props.append(f'gem:statement """{esc(a["statement"])}"""')
        if phrase is not None or page is not None:
            sp_props = []
            if page is not None:
                sp_props.append(f"gem:page {int(page)}")
            if phrase is not None:
                sp_props.append(f'gem:phrase """{esc(phrase)}"""')
            extra_blocks.append(
                f"{an}_span a gem:SourceSpan ;\n    "
                + " ;\n    ".join(sp_props) + " .")
            a_props.append(f"gem:sourceSpan {an}_span")
        extra_blocks.append(
            f"{an} a gem:GeneticEvidenceAssertion ;\n    "
            + " ;\n    ".join(a_props) + " .")
        item_props.append(f"gem:assertion {an}")

    item_block = (f"{node} a gem:GeneticEvidence ;\n    "
                  + " ;\n    ".join(item_props) + " .")
    return [item_block] + extra_blocks


def convert(path: Path) -> str:
    data = yaml.safe_load(path.read_text())
    triples = [f"@prefix gem: <{GEM}> .",
               f"@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
               f"# Generated from {path.name} by extraction/yaml_to_rdf.py", ""]
    for idx, item in enumerate(data.get("evidence", []) or []):
        triples.extend(item_triples(item, idx))
        triples.append("")
    return "\n".join(triples) + "\n"


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    to_stdout = "--stdout" in argv
    if not args:
        print(__doc__)
        return 2
    for src in args:
        p = Path(src)
        ttl = convert(p)
        if to_stdout or len(args) == 1 and len(argv) == 1:
            sys.stdout.write(ttl)
        else:
            out = p.with_suffix(".ttl")
            out.write_text(ttl)
            print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
