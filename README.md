# A Semantic Model of Genetic Evidence

A conceptual framework for representing scientific and genetic evidence from
the biomedical literature in a form suitable for variant interpretation,
automated reasoning, and AI-ready clinical infrastructure.

This repository accompanies a paper submitted to the 17th International
Conference on Biological and Biomedical Ontology (ICBO 2026, Washington
D.C., July 15–17 2026).

## What this repository contains

```
.
├── paper/          LaTeX source for the manuscript (main.tex, references.bib)
├── schema/         SHACL shapes + supporting definitions
├── annotations/    One YAML file per annotated publication + raw PDF extractions
├── extraction/     Scripts that extract highlights and callouts from annotated PDFs
├── figures/        Source files for figures used in the paper
└── .github/        CI configuration validating annotations against the schema
```

## The annotation corpus

Six publications, chosen to span the major epistemic shapes of genetic
evidence encountered in literature-based variant interpretation:

| Annotation                      | Role in the paper                    | Source                       |
| ------------------------------- | ------------------------------------ | ---------------------------- |
| `jossin2017.yaml`    (Llgl1)    | molecular mechanism                  | manual (ground truth)        |
| `davis2011.yaml`     (TTC21B)   | breadth exemplar                     | manual (ground truth)        |
| `nelson1992.yaml`    (CD18)     | classical molecular genetics         | manual (ground truth)        |
| `gupta2015.yaml`     (ATP6AP2)  | low-credibility edge case            | manual (ground truth)        |
| `duerr2006.yaml`     (IL23R)    | clean GWAS exemplar                  | AI-drafted, expert-reviewed  |
| `inouye2018.yaml`    (metaGRS)  | polygenic-score model-extension case | AI-drafted, expert-reviewed  |

For manually annotated papers, PDF highlights and sticky-note callouts are the
authoritative ground truth. The YAML is a structured transformation of those
artefacts, with every assertion carrying a `source_span` pointing back to the
specific page and quoted passage. Disagreements between the annotator and the
AI reviewer are not silently resolved — they are captured as `reviewer_query`,
`reviewer_suggestion`, or `reviewer_disagreement` fields so they remain
auditable.

For AI-drafted annotations, the same `source_span` anchoring is used, and
curator review is the evaluation signal.

## Extraction pipeline

The scripts in `extraction/` read a PDF with highlights and callouts and emit
a structured JSON record of every annotation, including the text covered by
each highlight (extracted via coordinate lookup) and the free-text notes
attached to callouts.

```bash
python3 extraction/extract_annotations.py paper.pdf out.json
```

Two extractors are provided. `extract_annotations.py` uses PyMuPDF and is the
recommended one — it reliably recovers the text under each highlight.
`extract_annotations_pypdf.py` uses pypdf and is provided as a fallback.

Dependencies:

```
pip install pymupdf pypdf pyyaml
```

## Schema

Two complementary representations:

- `schema/genetic_evidence.shacl.ttl` — SHACL shapes encoding the class
  hierarchy, dimension types, cardinalities, and conditional activation
  rules. This is the machine-checkable validation layer.
- `schema/dimensions.md` — the human-readable enumeration reference for all
  categorical value types (knowledge domain, method, target type, etc.).

Annotations in `annotations/` are validated against the SHACL shapes by the
CI workflow in `.github/workflows/validate.yml`. A failing validation blocks
merges and indicates either a schema bug or an annotation error.

## Citing this work

See `CITATION.cff`. Once the paper is accepted, a DOI will be registered via
Zenodo and the CITATION file updated.

## License

See `LICENSE` (content) and `LICENSE-CODE` (scripts and schema). Both are
permissive and compatible with CEUR-WS publication terms.

## Contact

See the corresponding-author block on the paper's title page.
