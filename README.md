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
├── skills/         Two Claude skills (annotation, review) that operationalise the protocols
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
| `v0/duerr2006.yaml`  (IL23R)    | clean GWAS exemplar                  | AI-drafted, expert-reviewed  |
| `v1/inouye2018.yaml` (metaGRS)  | polygenic-score model-extension case | AI-drafted, expert-reviewed  |

The four manual annotations live at the top of `annotations/`. The two
AI-drafted annotations are versioned: `annotations/v0/` holds the
original protocol-v0 drafts (curator-reviewed), and `annotations/v1/`
holds their re-annotation under the current protocol. The paper
documents **Duerr `v0`** and **Inouye `v1`** (the protocol matured on
the Duerr review and was then applied to Inouye); the other version of
each is retained for comparison.

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
- `protocols/REVIEW_PROTOCOL.md` and
  `protocols/REVIEW_PROTOCOL_INTERACTIVE.md`: the assertion-by-assertion
  review protocol and its interactive, curator-in-the-loop variant, used
  to adjudicate the AI-drafted annotations. Current version: 1.0.
- `protocols/LABELING_EXAMPLES.md`: worked cases for the recurring
  judgement calls referenced by the protocols above.

A staged interactive *annotation* protocol (curator review of the
decomposition before dimension filling) is planned but not yet
specified.

The two AI-drafted annotations in the corpus (Duerr 2006, Inouye 2018) were
produced under what became `PROTOCOL_AUTONOMOUS.md` v1.0; their `provenance`
blocks record the protocol version retroactively.

## Skills

Two Claude skills in `skills/` operationalise the protocols:

- **`genetic-evidence-annotation/`** — autonomous drafting of a YAML annotation
  for a paper (the autonomous protocol). Triggers on requests like "annotate
  this paper under the genetic-evidence model" or "produce a GEM YAML annotation
  for paper X".
- **`genetic-evidence-review/`** — interactive, curator-in-the-loop review of an
  existing annotation (the review protocol). Triggers on "review this GEM
  annotation", "audit this annotation against the paper", and similar; it emits
  a review log, a review report, and the updated annotation.

Both follow the Agent Skills open standard and are portable across agents that
support it (Claude Code, Cursor, Copilot, and others), not Claude-specific.
Each skill references shared material **outside** its own folder, the protocols
in `protocols/`, the schema in `schema/`, and exemplar annotations in
`annotations/`, so it has to be installed together with that material.

### Installing in Claude Code (or another in-repo agent)

Run the agent inside a checkout of this repository and copy or symlink the
skill folder into your skills directory (project-local `.claude/skills/` or
user-global `~/.claude/skills/`), for example:

```bash
ln -s "$PWD/skills/genetic-evidence-annotation" .claude/skills/
ln -s "$PWD/skills/genetic-evidence-review"     .claude/skills/
```

The skills' repo-relative references (`protocols/...`, `schema/...`,
`annotations/...`) resolve because the agent runs at the repository root.

### Installing on Claude.ai (web / mobile / desktop)

Do **not** zip the `skills/<name>/` folder directly: the skill depends on files
outside that folder (protocols, schema, exemplars) that a bare zip would miss.
Instead build a self-contained bundle with the provided script:

```bash
./build_skill_bundle.sh --skill annotation   # -> genetic-evidence-annotation-skill.zip
./build_skill_bundle.sh --skill review        # -> genetic-evidence-review-skill.zip
# add --check for an input-validation dry run
```

The script gathers `SKILL.md`, the relevant protocols, the schema, and (for the
annotation skill) the four curator-led exemplar annotations into one zip,
rewriting the paths for the flat bundle layout. Upload the resulting zip via
Customize > Skills > + Create skill (the bundle's top-level folder must be the
root of the zip, which the script ensures).

### Using the skills

Once installed, ask in natural language, for example:

> Annotate `papers/smith2024.pdf` under the genetic-evidence model.

> Review the GEM annotation in `annotations/smith2024.yaml` against the paper.

The annotation skill confirms the input paper, output path, and schema location,
then produces a single YAML file matching the existing annotations. The review
skill walks the annotation item by item with the curator and emits its three
artefacts (review log, review report, and the updated annotation).

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

Annotations in `annotations/` are checked by the CI workflow in
`.github/workflows/validate.yml`. The `parse-yaml` job verifies that every
annotation YAML parses cleanly and blocks merges on failure. Full SHACL
validation against the shapes is wired in as an advisory
(`continue-on-error`) job that activates once the `extraction/yaml_to_rdf.py`
converter lands; until then it is skipped. Flip the job to blocking once the
schema stabilises.

## Citing this work

See `CITATION.cff`. Once the paper is accepted, a DOI will be registered via
Zenodo and the CITATION file updated.

## License

See `LICENSE.txt` (content) and `LICENSE-code.txt` (scripts and schema). Both are
permissive and compatible with CEUR-WS publication terms.

## Contact

See the corresponding-author block on the paper's title page.