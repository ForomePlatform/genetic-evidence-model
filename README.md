# A Semantic Model of Genetic Evidence

A conceptual framework for representing scientific and genetic evidence from
the biomedical literature in a form suitable for variant interpretation,
automated reasoning, and AI-ready clinical infrastructure.

This repository accompanies a paper submitted to the 17th International
Conference on Biological and Biomedical Ontology (ICBO 2026, Washington
D.C., July 15–17 2026). The paper is currently under revision.

## What this repository contains

```
.
├── paper/          LaTeX source for the manuscript (main.tex, references.bib)
├── schema/         SHACL shapes + supporting definitions
├── annotations/    One YAML file per annotated publication + raw PDF extractions
├── case-reports/   Per-paper case reports (one for each of the six annotations)
├── protocols/      Annotation protocol documents (canonical rules + per-mode workflows)
├── skills/         Claude skill(s) that operationalise the protocols
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
AI reviewer are not silently resolved: they are captured as `reviewer_query`,
`reviewer_suggestion`, or `reviewer_disagreement` fields so they remain
auditable.

For AI-drafted annotations, the same `source_span` anchoring is used, and
curator review is the evaluation signal.

Per-paper case reports are in `case-reports/`. Each report summarises the
paper's role in the corpus, the decomposition into `GeneticEvidence` items,
the candidate extensions surfaced, the reviewer flags, and notes for
downstream consumers.

## Annotation protocols

The `protocols/` directory documents how annotations are produced, separately
from what they describe (the schema) and what they contain (the corpus). The
intent is that an annotation under this schema is reproducible and citable
under a versioned protocol, not an artefact of a particular annotator's
unwritten conventions.

- `protocols/PROTOCOL.md`: the canonical, mode-agnostic rules. Covers
  decomposition principles (the lumper default), dimension assignment,
  source-anchoring requirements, flag taxonomy, candidate-extension
  promotion, normalisation handling. Current version: 1.0.
- `protocols/PROTOCOL_AUTONOMOUS.md`: the operational workflow for autonomous
  AI annotation (single pass, no curator in the loop). Specifies input
  quality gating, self-consistency checks, mandatory confidence-summary
  emission, and failure handling.
- `protocols/PROTOCOL_INTERACTIVE.md`: planned but not yet specified.
  Staged AI annotation with curator review of the decomposition before
  dimension filling.

The two AI-drafted annotations in the corpus (Duerr 2006, Inouye 2018) were
produced under what became `PROTOCOL_AUTONOMOUS.md` v1.0; their `provenance`
blocks record the protocol version retroactively.

## Annotation skill

A Claude skill in `skills/genetic-evidence-annotation/` operationalises the
autonomous protocol. It triggers on requests like "annotate this paper under
the genetic-evidence model" or "produce a GEM YAML annotation for paper X".

The skill is portable across all major AI coding agents that have adopted
the Agent Skills open standard (Claude Code, Cursor, Copilot, and others),
not Claude-specific.

### Installing the skill

**Claude Code:** copy or symlink `skills/genetic-evidence-annotation/` into
your project's `.claude/skills/` directory (project-local) or
`~/.claude/skills/` (user-global). Claude Code auto-discovers skills in
either location.

**Claude.ai (web/mobile/desktop):** zip the `skills/genetic-evidence-annotation/`
folder and upload via Customize > Skills > + Create skill. The folder must
be the root of the zip, not just its contents.

**Other agents:** check your agent's skill-installation documentation. The
SKILL.md file is the entry point; supporting files in the same directory
are loaded as referenced.

### Using the skill

Once installed, ask in natural language:

> Annotate `papers/smith2024.pdf` under the genetic-evidence model.

The skill will confirm the input paper, the target output path, and the
schema location before proceeding. It produces a single YAML file matching
the format of the existing annotations.

## Extraction pipeline

The scripts in `extraction/` read a PDF with highlights and callouts and emit
a structured JSON record of every annotation, including the text covered by
each highlight (extracted via coordinate lookup) and the free-text notes
attached to callouts.

```bash
python3 extraction/extract_annotations.py paper.pdf out.json
```

Two extractors are provided. `extract_annotations.py` uses PyMuPDF and is the
recommended one: it reliably recovers the text under each highlight.
`extract_annotations_pypdf.py` uses pypdf and is provided as a fallback.

Dependencies:

```
pip install pymupdf pypdf pyyaml
```

## Schema

Two complementary representations:

- `schema/genetic_evidence.shacl.ttl`: SHACL shapes encoding the class
  hierarchy, dimension types, cardinalities, and conditional activation
  rules. This is the machine-checkable validation layer.
- `schema/dimensions.md`: the human-readable enumeration reference for all
  categorical value types (knowledge domain, method, target type, etc.).
- `schema/EXTENSIONS.md`: the authoritative log of all candidate extensions
  surfaced during corpus annotation, including their promotion or
  retraction status.

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