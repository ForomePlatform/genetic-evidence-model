# Project Handover — ICBO 2026 Paper on Genetic Evidence Model

*A comprehensive context document for resuming this project in a fresh
Claude conversation.*

## 1. What this project is

Preparing a **full paper (8–12 pages, CEUR single-column)** for submission
to the 17th International Conference on Biological and Biomedical Ontology
(**ICBO 2026**, Washington D.C., **July 15–17, 2026**).

- **Submission deadline:** **May 1, 2026**
- **Current date as of handover:** April 19, 2026 (roughly 12 days remain)
- **Submission portal:** https://cmt3.research.microsoft.com/ICBBO2026/Submission/index
- **Conference theme:** *"Semantic Awareness in the Age of Generative AI"* —
  strongly oriented toward trustworthy-AI, AI-readiness, provenance, and
  ontology-driven validation
- **Call page:** https://icbo-conference.github.io/icbo2026/call-for-submissions/
- **LaTeX template:** not yet released by ICBO as of April 2026; only .docx
  available. Using standard `ceurart` class pending an ICBO-specific version
- **Author Agreement:** CC-BY only, NTP (no third-party material) variant is
  right for this paper. Printed-and-signed form required; PDF digital signature
  not accepted. https://ceur-ws.org/ceur-author-agreement-ccby-ntp.pdf

### 1.1 Paper topic

A **semantic model for genetic evidence from the biomedical literature**,
designed to support variant interpretation and AI-ready clinical
infrastructure. Extends a prior preprint by the user. Key contributions:

1. Semantic model with **core classes** (ScientificEvidence,
   EvidenceVariable, EvidenceAssertion) and their **genetic specialisations**
2. Compact **dimensional vocabulary** with a **conditional-activation**
   mechanism (some dimensions are required only when other dimensions
   take certain values)
3. **Annotation corpus of six papers** demonstrating coverage
4. **Human–AI collaborative annotation workflow** with evaluation against
   manually curated ground truth
5. **Alignment sketch** to existing standards: FHIR Evidence, ECO, SEPIO,
   GA4GH GKS, IAO/OBI, PROV-O

### 1.2 What makes this paper fit ICBO 2026 specifically

- **Topic 4 (AI-Readiness and Semantic Infrastructure):** the schema is
  explicitly designed as AI-ready infrastructure; conditional-activation
  rules are the kind of "semantic metadata's role in model training"
  that the call foregrounds
- **Topic 2 (Semantic Modeling and Bounding of GenAI):** the AI-assisted
  annotation workflow with curator review is a concrete example of
  ontology-driven validation of generative outputs
- **Topic 5 (FAIR Principles):** source-span anchoring of every
  annotation makes provenance and traceability explicit

## 2. Where the work lives

### 2.1 Repository — `genetic-evidence-model/`

All work product is in a single repository structure packaged as
`genetic-evidence-model.zip` in the chat outputs. The user intends to
push this to GitHub (they'll add LICENSE files themselves).

```
genetic-evidence-model/
├── README.md                              project overview
├── CITATION.cff                           machine-readable citation metadata (CC-BY-4.0)
├── .gitignore                             LaTeX + Python ignore rules
│
├── paper/
│   ├── main.tex                           LaTeX skeleton (ceurart class)
│   ├── references.bib                     seed bibliography
│   └── sections/                          drafted sections, included via \input{}
│       ├── 03_model.tex                   §3 Model (drafted 2026-04-20)
│       └── 04_examples.tex                §4 Worked Examples (drafted 2026-04-20)
│
├── schema/
│   ├── genetic_evidence.shacl.ttl         SHACL shapes, 82 triples as of Gupta
│   └── dimensions.md                      human-readable enumeration reference
│
├── annotations/                           all 6 annotations complete
│   ├── jossin2017.yaml                    manual (ground truth)
│   ├── jossin2017.raw.json                raw PDF extraction
│   ├── davis2011.yaml                     manual (ground truth)
│   ├── davis2011.raw.json
│   ├── nelson1992.yaml                    manual (ground truth)
│   ├── nelson1992.raw.json
│   ├── gupta2015.yaml                     manual (ground truth)
│   ├── gupta2015.raw.json
│   ├── duerr2006.yaml                     AI-drafted, awaiting review
│   └── inouye2018.yaml                    AI-drafted, awaiting review
│
├── extraction/
│   ├── extract_annotations.py             PyMuPDF-based (recommended)
│   └── extract_annotations_pypdf.py       pypdf-based (fallback)
│
├── figures/                               empty, will hold TikZ/SVG for class diagram
│
└── .github/workflows/
    └── validate.yml                       CI: YAML parse + placeholder for SHACL
```

### 2.2 Licensing

- **User adds LICENSE files themselves.** I should not create or commit
  these.
- **CITATION.cff says CC-BY-4.0** for content (matches CEUR publication
  terms).
- **No publisher PDFs committed to the repo.** Raw PDF annotations
  (highlighted_text fields) contain short excerpts only, within fair
  use norms. Source spans in the YAML annotations have been trimmed to
  "key phrases" (typically under 15 words) per user protocol decision.

## 3. The annotation corpus — current state

| Paper | Source | Role | GE items | Candidate exts | Q/S/D flags | Credibility |
|---|---|---|---|---|---|---|
| **Jossin 2017** (Llgl1) | manual | molecular mechanism | 6 | 3 | 3/1/0 | VERY HIGH |
| **Davis 2011** (TTC21B) | manual | breadth exemplar | 6 | 2 | 2/1/1 | HIGH |
| **Nelson 1992** (CD18) | manual | classical molecular genetics | 3 | 1 | 0/3/0 | MEDIUM |
| **Gupta 2015** (ATP6AP2) | manual | low-credibility edge case | 2 | 0 | 0/1/0 | LOW |
| **Duerr 2006** (IL23R) | AI-drafted | clean GWAS exemplar | 6 | 1 | 3 AI-uncert / 2 AI-assum | HIGH |
| **Inouye 2018** (metaGRS) | AI-drafted | polygenic-score stress test | 5 | 6 | 0 AI-uncert / 2 AI-assum | HIGH+MEDIUM |

Manual annotations are **locked as ground truth**. Disagreements between
the annotator's summary table and AI-reviewer interpretation are
preserved as `reviewer_query`, `reviewer_suggestion`, or
`reviewer_disagreement` fields in the YAML, not silently resolved.

AI-drafted annotations use a different flag vocabulary:
- `ai_uncertainty` — AI unsure about a mapping; reviewer input wanted
- `ai_assumption` — AI made a judgment call the reviewer should verify
- (No disagreement category, because there's nothing to disagree with yet.)

**Total candidate extensions surfaced across the corpus: 13** (not 14 —
CE-DU2 was retracted, see §4.2.1). None have been auto-promoted
because no extension has recurred in a second paper under the 2-papers
rule.

### 3.1 Cross-paper observations

- **Credibility range is good:** VERY HIGH, HIGH, MEDIUM, LOW span all
  four manual papers. This gives the Evaluation section real variation
  to analyse.
- **Promoted dimensions applied in all four papers:** `phenotype_scale`
  and `variant_ascertainment` both fire on multiple papers. This confirms
  the promotion rule (see §4.2) was correct for these two.
- **Candidate extensions are NOT being auto-promoted yet** — none of the
  six single-paper gaps recurred. Gupta in particular surfaced ZERO
  candidate extensions, which is a useful signal: the model correctly
  accommodates schema-fitting papers.

## 4. Decisions made and locked — DO NOT REVISIT without user consent

### 4.1 Protocol for manual annotations

For the four manually-annotated papers (Jossin, Davis, Nelson, Gupta):

- **Blank cells in the annotator's summary = "considered and chose not to
  populate"**, not `null`. YAML marks these as
  `annotated_as: not_applicable_or_omitted`. Significant for coverage
  statistics in the Evaluation section.
- **Annotator's informal values normalised to schema enumerations where
  feasible** (e.g., "Binding activity" → `BINDING`); preserved verbatim
  via `normalization_note` with `type: ai_normalization`. Ground truth
  not overwritten.
- **Arbitrary key-value pairs allowed in `special_considerations`**. Not
  every novel key justifies updating the model itself. Promotion to a
  named dimension requires curator review.
- **Ground truth is NOT silently overwritten.** Disagreements flagged
  inline as `reviewer_query` / `reviewer_suggestion` / `reviewer_disagreement`.

### 4.2 Extension-promotion rule (decided 2026-04-19)

- **Single-paper gap** → recorded in `candidate_extensions` block at the
  top of the YAML; marked candidate in `schema/dimensions.md`
- **Second independent paper exercising same gap** → promoted to
  first-class dimension in the schema

Two promotions so far (both user-approved):
- **`phenotype_scale`** with enum `MOLECULAR | CELLULAR | HISTOLOGICAL |
  ORGANISMAL | CLINICAL` (surfaced by Jossin's three "phenotype"
  callouts at distinct scales)
- **`variant_ascertainment`** with enum `OBSERVED_IN_CASES |
  OBSERVED_IN_CONTROLS | FROM_DATABASE | SYNTHETIC` (surfaced by Davis's
  explicit distinction between patient-observed and functionally-tested
  variants)

Six candidate extensions currently awaiting confirmation. Listed in
`schema/dimensions.md` under "Candidate dimensions and enumeration values".

### 4.2.1 Withdrawn candidate extension: CE-DU2 (negated assertion handling)

Initially proposed from the Duerr annotation (GE-5 asserts "no
significant association at IL12RB1/IL23A/IL12B"). User correctly
pointed out that an `EvidenceAssertion` is defined as a *predicate*,
and a predicate can state the absence of something just as readily as
its presence. No new dimension required — the assertion's `statement`
field already carries the polarity as part of the predicate. CE-DU2
has been removed from `annotations/duerr2006.yaml`; `schema/dimensions.md`
was never updated with it, so no schema change is needed.

**Methodological note for the paper:** this is a useful example of the
review process catching a premature candidate extension. It also
illustrates why the 2-papers promotion rule is valuable — CE-DU2 would
likely have never recurred, and without human review it might have
been carried forward unnecessarily. Worth mentioning in the Workflow &
Evaluation section.

### 4.3 Decomposition granularity

- **Natural-claim granularity per paper.** Short papers like Gupta may
  have 1–2 GE items; dimension-rich papers like Davis have 6.
- Follow the annotator's Knowledge Domain scoping even when the paper
  contains information that could populate other domains (e.g., Nelson
  is Gene Function per annotator, so pedigree info is `context_not_extracted`).

### 4.4 Source span quoting policy

- **Option (c): key phrases** in the public YAML (typically under 15
  words per quote)
- Raw full extraction kept in `annotations/*.raw.json` with provenance
  note as derivative work
- Avoids copyright concerns while preserving audit trail

### 4.5 Curator style

- **Treated as noise, not a finding.** User confirmed the multiple
  annotator names in PDFs (alico, Vladimir Seplyarskiy) are actually
  the same person in different moods / project contexts. Drop any
  curator-style-variation framing from the Discussion.

### 4.6 LaTeX choices

- **`ceurart` document class** (CEUR Workshop Proceedings, single column)
- **`listings`, not `minted`**, for YAML code blocks (no `-shell-escape`
  dependency, works on Overleaf without extra setup)
- User added to preamble: `\begin{document}`, `\usepackage{lipsum}`,
  `\usepackage{morefloats}`, `\usepackage[section]{placeins}`. Strip
  `lipsum` and `\lipsum[1-2]` before submission.

### 4.6.1 LaTeX gotchas the user had to fix (DO NOT reintroduce these)

- **`\todo{}` is illegal inside floats** (`table*`, `figure`). The
  `todonotes` package uses `\marginpar`, which LaTeX does not allow
  inside floats — this produces `LaTeX Error: Not in outer par mode`.
  The main.tex defines a `\tbd{}` macro that renders as an orange
  `[?]` inside floats and falls back to `\todo{}` elsewhere. Use
  `\tbd{}` in table cells, not `\todo{}` or `---`.
- **Unicode em-dash and en-dash in listings** need the `literate={—}{{---}}1
  {–}{{--}}1` clause in `\lstset`. Without it, `\ttfamily` fonts used
  by `listings` lack glyphs for these characters. The YAML annotations
  contain such characters in assertion text (e.g., "LLGL1–N-cadherin");
  do not strip the `literate=` clause.
- **Do not add `\bibliographystyle{}`** — `ceurart` sets its own when
  loaded with `natbib=true`. Adding another causes a redefinition warning
  or wrong style.

### 4.7 Avro rejected as primary schema language

User asked about Avro for other projects. Decision:
- **Primary schema in the paper: SHACL** (validation) + **OWL Manchester
  fragment** (class hierarchy)
- **LinkML** suggested as possible source-of-truth for generating
  Avro/OWL/SHACL/JSON-Schema from one definition (future work; not this
  paper)
- **Annotations stay in YAML** (human-readable, validatable via SHACL)

## 5. Current state of key artefacts

### 5.1 `paper/main.tex` and `paper/sections/`

User-provided skeleton with:
- `ceurart` class, `sigconf,natbib=true`
- Author block placeholders (needs real ORCIDs/emails)
- Abstract placeholder (write last)
- Section structure with `\todo[inline]{}` notes
- Tables: standards-mapping (still empty), corpus table (filled for all six papers)
- Two YAML listings as placeholders (Duerr, Inouye)
- Bibliography stub with 17 entries in `references.bib`
- `\tbd{}` macro for placeholders inside floats (`\todo{}` illegal there)
- Unicode dash `literate=` clause in `\lstset`

**Drafted sections so far (included via \input):**
- **§3 Model** — `paper/sections/03_model.tex` (drafted 2026-04-20).
  Contains dimensions table (now including the two promoted dimensions)
  and two SHACL conditional-activation examples.
- **§4 Worked Examples** — `paper/sections/04_examples.tex` (drafted
  2026-04-20). Corpus table + Duerr and Inouye featured examples
  with 20-22 line YAML excerpts each.

All other sections remain `\todo` placeholders in `main.tex` pending
drafting. The paper still does not compile to a complete document — it
compiles, but with extensive placeholders marked by `\todo` margin
notes and `\lipsum[1-2]` filler in §1.

### 5.2 `schema/genetic_evidence.shacl.ttl`

88 RDF triples. Declares:
- Top-level classes (ScientificEvidence, EvidenceVariable, EvidenceAssertion
  + genetic specialisations)
- Enumerations for KnowledgeDomain, Method, TargetType, PhenotypeScale,
  VariantAscertainment
- Base NodeShape for GeneticEvidence with required property constraints
- Conditional-activation SPARQL rules for:
  - `variant_ascertainment` required when `target_type = VARIANT`
  - `mode_of_inheritance` required when `knowledge_domain contains
    HUMAN_GENETICS` AND `target_type = GENE`
  - `organism` required when `method contains IN_VIVO_EXPERIMENT` OR
    `knowledge_domain contains MODEL_ORGANISM` (added 2026-04-20 to
    match the second SHACL example in §3 of the paper)

**Not yet shaped:** measurement_target enumeration, organism enumeration,
shape for `source_span`, shape for reviewer flag fields.

### 5.3 `schema/dimensions.md`

Complete human-readable reference. Sections:
- Core dimensions (always required): KnowledgeDomain, Method, TargetType,
  Resolution, Credibility, **plus the two PROMOTED dimensions**
- Conditional dimensions grouped by activation condition
- **Candidate dimensions and enumeration values** (6 entries, tracking
  single-paper gaps awaiting second-paper confirmation)

### 5.4 The four manual YAMLs

Each follows the same structure:
```
publication: {id, doi, citation, title}
provenance: {curation_context, annotator, ...}
candidate_extensions: [list, may be empty]
evidence: [list of GeneticEvidence items]
annotator_omitted_dimensions: [list with rationale_inferred]
summary_table_crosswalk: {original_row, transformation_notes, reviewer_queries}
reviewer_flag_summary: {queries, suggestions, disagreements, candidate_extensions, promoted_dimensions_applied}
```

Each `evidence` item has:
- `id, label, source: manual_annotation`
- Dimension values
- `credibility`, `credibility_comment`, `special_considerations`
- `assertions`: list with `id, statement, source_span {page, key_phrase},
  callout` (which links to the annotator's PDF sticky note if any)

## 6. Work remaining (ordered by dependency)

### 6.0 Collaboration workflow (decided 2026-04-20)

User asked to switch to **incremental file patches** rather than full
ZIP drops, to save tokens. From this point forward:

- When a single file changes, produce just that file (or a `str_replace`
  patch against it) — not the whole repo
- `HANDOVER.md` should be **updated in-place whenever the project state
  changes** (new decision, candidate extension, protocol tweak, LaTeX
  fix, etc.), not maintained separately
- No PDF rendering of `HANDOVER.md` needed; raw markdown is fine
- Full ZIP only when (a) explicitly requested, or (b) transferring the
  complete state to a fresh conversation

### 6.1 Status of annotations

**All six annotations complete:**

- Jossin, Davis, Nelson, Gupta — manual ground truth, locked
- Duerr, Inouye — AI-drafted, pending user review

User is reviewing Duerr and Inouye in parallel with paper writing
(2026-04-20). Any `ai_uncertainty` resolutions or corrections will
patch the respective YAMLs.

### 6.2 Next immediate step: paper writing

Order of composition (decided 2026-04-20; Abstract last):

1. **§3 Model** — **DRAFTED 2026-04-20.** See
   `paper/sections/03_model.tex`. Contains core-class definitions,
   consolidated dimension table (14 rows including the two promoted
   dimensions), and the conditional-activation mechanism with two
   SHACL examples (mode_of_inheritance with AND-conjunction;
   organism with OR-disjunction and cross-axis activation). The
   EvidenceAssertion description explicitly notes that assertions
   are predicates of any polarity, per user's CE-DU2 correction.
2. **§4 Worked Examples** — **DRAFTED 2026-04-20.** See
   `paper/sections/04_examples.tex`. Contains the six-paper corpus
   table and two featured examples: Duerr (clean GWAS) with a 20-line
   YAML excerpt showing GE-1 (the primary discovery), and Inouye
   (model-extension stress test) with a 22-line YAML excerpt showing
   GE-2 (UK Biobank validation) including inline candidate-extension
   tags. Pointer to GitHub for the other four annotations.
   Featured-pair decision: Duerr + Inouye (positive + stress-test)
   rather than Duerr + Davis (positive + breadth). Duerr+Inouye gives
   a stronger ICBO-theme narrative because Inouye's six candidate
   extensions concentrate the methodology findings.
3. **§5 Workflow & Evaluation** — ICBO-theme hook. Protocol,
   coverage/agreement metrics, disagreement taxonomy. Note the CE-DU2
   retraction as an example of the review process working.
4. **§6 Discussion** — "Model extensions surfaced by annotation"
   subsection listing 2 promoted dimensions + 13 candidates,
   limitations, future work.
5. **§2 Background and Related Work** — existing draft to adapt, fill
   standards-mapping table.
6. **§1 Introduction** — existing draft to adapt, finalize contributions
   list.
7. **§7 Conclusion** — 3-4 sentences.
8. **Abstract** — ~200 words, written last.

**File structure for paper writing:** sections split into
`paper/sections/NN_name.tex` files, included via `\input{}` from
`main.tex`. Keeps sections independently reviewable and easy to reorder.

### 6.3 Final polish

- Strip `\lipsum` from main.tex
- Pass `\usepackage[disable]{todonotes}` or remove `todonotes` entirely
- Fill in author ORCIDs/emails
- Resolve `TODO` entries in `references.bib`
- Prepare signed CEUR Author Agreement NTP form (print, sign by hand,
  scan, upload to CMT and email to ontology.world@gmail.com with subject
  line "Author Agreement for submission PAPER [PAPER-ID]")

## 7. Open questions for user

These were raised in the conversation but not yet decided. New chat
should re-ask:

1. **Mode-of-inheritance / Knowledge-Domain scoping tension in Nelson.**
   Paper explicitly says "This autosomally recessive disease" and
   annotator highlighted it, but Knowledge Domain = Gene Function only
   by annotator's scoping. The conditional rule does not activate.
   Should it? User to decide for final paper.
2. **Test-set vs training-set scoping.** Nelson was annotated in the
   user's "test set" document (separate from the training set document
   covering Jossin, Davis, Gupta). If the AI-assisted workflow
   evaluation wants a held-out test set, Nelson may need to be
   partitioned separately. Or it may not matter for this paper and can
   be left as a single corpus.
3. **Extension promotion re-evaluation.** The six candidate extensions
   have all been single-paper so far. After Duerr and Inouye are
   annotated, some may hit the 2-papers threshold and auto-promote.
4. **Class diagram format.** Paper skeleton has a `\fbox` placeholder.
   TikZ vs external SVG?
5. **Featured-example YAML lengths.** Paper allows ~15-25 line listings
   per featured example. Need to select the right excerpts from Duerr
   and Davis.

## 8. Key URLs and paths

- **Conference:** https://icbo-conference.github.io/icbo2026/
- **Submission:** https://cmt3.research.microsoft.com/ICBBO2026/Submission/index
- **Author agreement (NTP):** https://ceur-ws.org/ceur-author-agreement-ccby-ntp.pdf
- **Contact:** ontology.world@gmail.com
- **User uploaded PDFs in /mnt/user-data/uploads/:**
  - `Dev_Cell_Reading_for_Shamil.pdf` (Jossin)
  - `TTC21B_ng_756.pdf` (Davis)
  - `J__Biol__Chem_-1992-Nelson-3351-7.pdf` (Nelson)
  - `1-s2_0-S135380201530002X-main.pdf` (Gupta)
  - `inouye-et-al-2018-genomic-risk-prediction-of-coronary-artery-disease-in-480-000-adults.pdf` (Inouye)
  - `science_1135245.pdf` (Duerr)
- **User uploaded annotator summary documents:**
  - "Genetic literature - training set" (covers ATP6AP2/Gupta,
    Llgl1/Jossin, TTC21B/Davis)
  - "Genetic literature - test set" (covers CD18/Nelson)

## 9. Tone/style notes for continuation

- User prefers **direct, substantive responses**; values surface
  methodological issues over glossing them
- User is an experienced scientist, LaTeX user (rusty, last active
  ~30 years ago), familiar with OBO/ICBO landscape
- User explicitly asked that ground truth NOT be silently overwritten.
  Flag all AI-reviewer changes inline.
- User explicitly asked to NOT include forward-looking statements in
  README about publication status (paper is unpublished)
- User handles LICENSE files themselves — do not create them
- User does not want the manuscript PDF committed to the repo initially
  (`.gitignore` excludes it by default)

## 10. How to restart

When resuming in a fresh conversation, the user should:

1. Attach this handover document
2. Attach the `genetic-evidence-model.zip` (or the individual updated
   files if small)
3. Mention which step from §6 they want to tackle first

A good first message to the new Claude would be something like:

> *"I'm resuming work on an ICBO 2026 paper. Attached is the project
> handover document and the current repo state. We're at the point of
> producing AI-drafted annotations for Duerr 2006 and Inouye 2018, then
> writing the paper. Please read the handover and confirm your
> understanding before we proceed."*

The new Claude should respond by summarising the state in its own words
(to verify comprehension) and then asking about any of the §7 open
questions before making assumptions.
