# Evaluation Protocol: Corpus-2 Annotation Study

## Status

**Draft for adoption.**

When this protocol is adopted, the repository will be tagged before data
collection begins. The tagged version of this protocol, the annotation
schema, the instruction bundles, the paper list, and the analysis code
will then be fixed. Any later change must be recorded in
`study/AMENDMENTS.md` before the affected study stage begins.

This study evaluates whether the GEM annotation protocol produces similar
annotations when it is carried out independently by a trained human
annotator and by an AI system.

---

## 1. Aim and limits of the study

### 1.1 Main aim

The study measures **protocol reproducibility**.

In this document, protocol reproducibility means the extent to which
independent executions of the same written annotation instructions produce
the same:

- evidence items;
- source-linked claims;
- values for GEM dimensions;
- candidate schema extensions; and
- review findings.

The study compares manual annotation, autonomous AI annotation, and
several review routes.

### 1.2 What the study will support

The study is designed to support the following conclusions:

1. How closely manual and autonomous AI annotations agree when both follow
   the same protocol.
2. How consistently the AI workflow reproduces its own annotations in
   separate fresh sessions.
3. Which parts of the annotation protocol and schema produce disagreement.
4. Whether human and AI routes independently identify the same candidate
   schema limitations.
5. How much time each annotation and review route requires.
6. Whether two pre-specified AI signals predict later disagreement or
   editing.

### 1.3 What the study will not support

The study will not claim:

- conventional inter-annotator agreement, because there is one human
  annotator;
- that the human annotation is a statistical gold standard;
- that AI is better or worse than a human annotator;
- that agreement proves scientific or clinical correctness;
- that results generalise to all genetic-evidence papers; or
- that AI-generated annotations can be accepted without expert review.

A future second trained annotator may independently annotate the sealed
paper set. That future work could support a conventional
inter-annotator-agreement analysis.

---

## 2. Definitions

This section defines terms used throughout the protocol.

- **Annotation**: a GEM YAML record describing evidence in one paper.
- **Evidence item**: one `GeneticEvidence` record in an annotation.
- **Assertion**: a source-linked claim recorded within an evidence item.
- **Source span**: the page and character range in the frozen canonical
  text of the paper that supports an assertion.
- **Manual annotation**: annotation completed by the human annotator
  without using an LLM for reading, summarising, drafting, checking, or
  editing.
- **Autonomous AI annotation**: annotation completed by the pinned AI
  system in a fresh session, using the frozen AI instruction bundle.
- **Fresh session**: a session that contains no output from any other
  study pass for the same paper.
- **Review**: a pass in which a draft annotation is checked against the
  source paper and the GEM schema.
- **Sealed output**: a completed output that is saved, hashed, and not
  changed except through an amendment recorded under Section 5, with the
  original file and its hash retained.
- **Typical paper**: a paper sampled from the predefined eligible
  literature frame.
- **Stress paper**: a deliberately selected paper that tests a known
  difficult area of the schema or protocol.
- **Candidate extension**: a possible addition or change to the GEM
  schema that has not yet been promoted into the schema.

---

## 3. Study roles

### 3.1 Study lead

The study lead is responsible for:

- maintaining the study design;
- preparing the frozen materials;
- conducting blinded alignment adjudication;
- judging semantic equivalence of labels;
- coding and reconciling disagreement categories; and
- approving final study decisions.

### 3.2 Human annotator

The human annotator is trained in genetics, completes all manual
annotation passes, and performs the intake screen for typical-stratum
candidates (Section 6.4). The annotator also takes the curator role in
the interactive AI-review sessions.

### 3.3 AI annotator and AI reviewer

The AI annotator and AI reviewer are the pinned model running the frozen
annotation and review bundles.

### 3.4 Known constraint

The human annotator operates the AI sessions. This creates a possible
risk of exposure to AI output. The study addresses that risk structurally:

- all manual drafts and manual self-reviews are completed and sealed before
  the annotator sees AI output;
- AI outputs are generated and stored without being read during Stage 3;
- analysis rules are fixed before any study data are examined; and
- alignment and semantic-equivalence judgments are performed with
  provenance hidden.

---

## 4. Materials fixed before the study begins

Before Stage 1 begins, the repository tag must freeze the following:

1. The GEM schema and all annotation and review protocols.
2. The annotation, review, and batch-review skill bundles, including their
   hashes.
3. The four AI exemplars:
    - Jossin 2017;
    - Davis 2011;
    - Nelson 1992; and
    - Gupta 2015.

   No study output may be used as an AI exemplar.
4. The AI provider, model name, model version or dated snapshot where
   available, and access route.
5. AI execution settings, including system prompt, temperature, maximum
   output length, tool access, retry policy, and whether web access,
   retrieval, code execution, or file search is enabled.
6. The PDF-to-text extraction tool and version.
7. A canonical text file and hash for each study paper.
8. This protocol, the analysis code, and the paper-selection file.
9. The annotation worksheet, worksheet converter, and validation tools.
10. The study rulings file, `study/RULINGS.md`.

`study/RULINGS.md` contains clarifications that arose during calibration.
The same file must be supplied to every review route: batch review,
interactive review, and human review.

---

## 5. Amendments

Any change after the study tag must be entered in `study/AMENDMENTS.md`.

Each amendment must include:

- amendment number;
- date;
- reason for the change;
- exact files or procedures affected;
- study stage affected; and
- confirmation that the amendment was recorded before that stage began.

No amendment may change a completed stage retrospectively.

---

## 6. Paper selection

### 6.1 Number and strata

The study will include 10 to 12 papers:

- at least 8 typical papers; and
- 2 to 4 stress papers.

Results for the two strata will be reported separately. The headline
agreement estimates will use the typical stratum only.

### 6.2 Typical papers

Typical papers will be sampled from a predefined literature frame recorded
in `study/PAPERS.md`.

Before selection, the file must record:

- the exact source or search query;
- the search date;
- eligibility criteria;
- exclusion criteria;
- the full list of eligible papers;
- the sampling method;
- any stratification variables; and
- the random seed used for selection.

### 6.3 Stress papers

Stress papers are selected deliberately to test areas that are underused or
currently difficult in GEM. For each stress paper, `study/PAPERS.md` must
state the expected challenge and the candidate extensions it is intended to
test.

Examples include:

- polygenic-score extensions CE-IN1 to CE-IN6;
- direction of effect, CE-DU1;
- family-based activation, CE-DU4; and
- interaction targets, CE-J2.

### 6.4 Intake screen

Before acceptance, every paper must pass a recorded intake screen.

The screen records whether the paper:

1. is a primary research article in English;
2. can be extracted into usable canonical text;
3. contains at least two separate claims linking a genetic entity to a
   phenotype;
4. is in scope, or is deliberately adjacent to GEM’s current scope;
5. has low, medium, or high expected candidate-extension load;
6. belongs in the typical or stress stratum;
7. was published before or after the documented model training cutoff; and
8. is likely to be unusually familiar to the model because it is prominent,
   highly cited, or heavily curated.

Items 1 to 4 are gating criteria: a paper is rejected only on these,
and a rejection must name the failed criterion or criteria and quote
or describe the evidence. Items 5 to 8 are recorded classifications and are never
grounds for rejection; in particular, the expected candidate-extension
load (item 5) must not influence acceptance. For typical-stratum
candidates, item 6 is fixed by the draw and item 7 is satisfied by the
construction of the literature frame; both are recorded mechanically.

For the typical stratum, the screen is performed by the human annotator
with no AI assistance (Section 8.1), on candidates presented strictly in
the recorded draw order (`study/PAPERS.md` Section 1.5): the annotator
never chooses among candidates, only screens the one presented. Every
outcome, pass or fail, with reasons and the screening time in minutes,
is recorded in the draw log. Screening time counts as intake effort,
never as H0 effort. The study lead may audit recorded outcomes at any
time; an audit cannot reverse an outcome, and audit findings are
recorded in `study/DEVIATIONS.md`. Stress-stratum candidates are
screened by the study lead.

No paper from the original six-paper corpus is eligible because those papers
were used in annotator training and, for four papers, as AI exemplars.

---

## 7. Training and calibration

Before Stage 1, the human annotator studies:

- the GEM manuscript;
- the GEM schema;
- all annotation and review protocols;
- the existing corpus annotations; and
- the annotation worksheet.

The annotator then completes open-book calibration annotations for Gupta
2015 and Nelson 1992. These are compared with the existing curator-led
annotations and discussed with the study lead.

Calibration outputs are not included in the study analysis.

After calibration, the study lead writes `study/RULINGS.md`. This file
records only general decisions that are likely to recur. It is frozen at
the study tag (Section 4); any later change is an amendment under
Section 5. New rulings may not be introduced during a review session. A
newly discovered issue is recorded in the review log and deferred until
after the study.

Effort logging begins during calibration.

---

## 8. Annotation and review passes

Every study paper receives the following passes.

| Code | Pass | Producer | Input | Sealed output |
|---|---|---|---|---|
| H0 | Manual draft | Human annotator, no AI | Paper | `h0.yaml` |
| SR | Manual self-review | Human annotator, no AI | H0 and paper | `h1.yaml` and change log |
| A0 | Autonomous AI draft | AI annotation bundle, fresh session | Paper | `a0.yaml` |
| A0x | Autonomous AI repeat | AI annotation bundle, second fresh session | Paper | `a0x.yaml` |
| A0y | Optional third AI repeat | AI annotation bundle, third fresh session | Paper | `a0y.yaml` |
| RB | AI batch review | AI batch-review bundle, fresh session | A0 and paper | `a1.yaml` and review log |
| RI | Interactive AI review | Human annotator and AI review bundle | H1 and paper | `h2.yaml` and review log |
| RH | Human review of AI draft | Human annotator, no AI | A0 or A1 and paper | Revised YAML and change log |
| WR | Washout re-annotation | Human annotator, no AI | Paper | `h0r.yaml` |

### 8.1 No-AI rule

For the intake screen (Section 6.4) and for H0, SR, WR, and RH, the human
annotator must not use any LLM-based tool for reading, summarising,
drafting, checking, searching, or editing.

Ordinary literature databases and reference resources are allowed. Their use
must be recorded in the effort log.

### 8.2 Manual worksheet

Manual passes are completed in the GEM annotation worksheet. The worksheet
contains:

- one row per evidence item;
- controlled vocabulary lists;
- assertion text and source locations;
- candidate extensions;
- omitted dimensions;
- notes; and
- an effort log.

The worksheet converter creates YAML deterministically and rejects invalid
values. It makes no annotation decisions. The human annotator does not edit
the YAML directly.

### 8.3 AI repeatability

A0, A0x, and, if used, A0y are independent executions of the same frozen AI
workflow. They are used to estimate AI repeatability.

AI repeatability is a comparison reference. It is not a measure of
correctness and is not a formal upper limit on human–AI agreement.

### 8.4 Human review split

The human annotator cannot independently review both A0 and A1 for the same
paper because the first review would affect the second.

Papers are therefore assigned to one of two groups before Stage 3:

- **RH(A0):** human review of the unreviewed AI draft; or
- **RH(A1):** human review after AI batch review.

Assignment is balanced across typical and stress papers and frozen before
Stage 3.

RH measures the ability of a trained annotator, already familiar with the
paper through a sealed manual pass, to detect and correct problems in an AI
draft. It does not measure naïve review by a person seeing the paper for the
first time.

### 8.5 Washout re-annotation

At least six weeks after H0, the annotator re-annotates one or two papers
from scratch. The annotator must not consult H0, H1, H2, A0, A0x, A1, or
review logs for that paper.

WR is reported as intra-annotator stability, not inter-annotator agreement.

---

## 9. Study order and sealing

### Stage 1: Manual drafting

The human annotator completes H0 for the first wave of papers. Outputs are
sealed.

### Stage 2: Manual self-review

The human annotator completes SR for the same papers. H1 outputs are sealed.

The study may use two drafting waves of five to six papers. The exposure
barrier applies across all waves: the annotator must not see AI output for
any study paper until all H1 files are sealed.

After each drafting wave, the study lead may confirm or reduce the number
of remaining papers. This decision may use recorded effort only, never
annotation content or agreement results, and is recorded as an amendment
under Section 5.

### Stage 3: AI-only drafting and batch review

The AI runs A0, A0x, optional A0y, and RB for all papers.

The annotator may operate the runs but must not read their outputs. AI outputs
are stored and sealed.

### Stage 4: Interactive and human review

The annotator completes RI and RH in a randomised, recorded order. The
frozen `RULINGS.md` file is used in every review route.

### Stage 5: Washout re-annotation

WR takes place at least six weeks after the relevant H0 pass.

### Stage 6: Analysis

Analysis follows Section 11 of this protocol.

### Sealing procedure

Study files are stored under `study/` or in a private repository and are kept
outside `annotations/` until the study closes. Each completed stage receives
a commit, tag, timestamp, and file hashes.

Study outputs must never be loaded as exemplars or reference material for an
autonomous AI run.

---

## 10. Effort recording

The effort log contains one row for each work session.

Each row records:

- paper identifier;
- pass code;
- annotator or AI route;
- date;
- start time;
- stop time;
- interruptions;
- external reference resources used;
- technical problems; and
- free-text notes.

Reported effort will include calibration time, annotation time, review time,
and correction time.

---

## 11. Comparison and analysis plan

### 11.1 Provenance-blind preparation

Before comparison, provenance fields are removed from the files and stored
separately. Each annotation is given an opaque identifier.

The study lead receives only the blinded files for alignment, semantic
equivalence judgments, and initial disagreement coding. The mapping between
opaque identifiers and annotation routes is revealed only after these steps
are frozen.

### 11.2 Item alignment

Evidence items from two annotations of the same paper are matched using
overlap between their source spans in the frozen canonical paper text.

Instruments record each source span as a page number and a verbatim key
phrase; character ranges are derived, not collected. The analysis code
locates each key phrase in the frozen canonical text after Unicode and
whitespace normalisation, which covers hyphenation and ligature
differences introduced by PDF extraction. When the phrase occurs more
than once, the occurrence on or nearest the recorded page is used. When
the phrase cannot be located after normalisation, the span is routed to
blinded adjudication and the case is counted under the source-extraction
category of the disagreement taxonomy.

The matching procedure is:

1. calculate character-level overlap for every possible pair of items;
2. give higher priority to pairs with greater overlap;
3. break remaining ties using the same target entity;
4. then use the same method family;
5. use deterministic maximum-weight matching so that one item cannot be
   matched to more than one item unless a pre-specified split/merge rule
   applies; and
6. record unresolved cases for blinded adjudication.

Items that cannot be matched are retained as decomposition disagreements.

### 11.3 Main measures

The study reports the following measures separately.

#### A. Evidence-item decomposition

For each annotation pair:

- number of evidence items;
- matched items;
- unmatched items;
- precision;
- recall; and
- F1 score.

#### B. Dimension agreement

For matched items, report agreement for each GEM dimension separately.

For hierarchical dimensions, including `method`, report:

- exact agreement; and
- hierarchy-weighted agreement based on the frozen subclass hierarchy.

#### C. Source-span agreement

For matched assertions, report intersection-over-union of source spans in
the canonical text.

#### D. Candidate extensions and flags

Record whether each route identifies:

- the same candidate extension;
- the same source of uncertainty;
- the same assumption; and
- the same review issue.

### 11.4 Labels and semantic equivalence

Assertion labels are assessed in two separate ways:

1. **Statement-rule conformance:** whether the label expresses a subject,
   verb, object or effect, and any necessary qualifier.
2. **Semantic equivalence:** whether two differently worded labels express
   the same meaning.

The study lead judges semantic equivalence while provenance remains hidden.
No LLM is used to judge label equivalence.

### 11.5 Disagreement taxonomy

Every unmatched item and every dimension disagreement is assigned one or
more categories:

- schema gap;
- protocol ambiguity;
- human annotation error;
- AI annotation error;
- source-extraction or source-location problem;
- different but defensible judgment; or
- other, with explanation.

Categories are assigned first with provenance hidden. After unblinding, the
study lead reconciles the category record and documents any changes.

### 11.6 Review outcomes

For each review pass, report:

- flags raised;
- flags accepted;
- flag acceptance rate;
- edited items;
- edited fields;
- edits made without a preceding flag;
- final edits anticipated by a reviewer flag;
- type of accepted flag; and
- time per accepted change.

Acceptance rate is defined as:

`accepted flags / flags raised`

Acceptance rate describes how often the curator accepted reviewer-raised
issues. It is not, by itself, a measure of reviewer completeness or quality.

### 11.7 Statistical summaries

Raw agreement measures are primary.

Confidence intervals will be estimated by resampling papers, not individual
items, because multiple items from the same paper are not independent.

Typical and stress strata will be reported separately. No formal hypothesis
test will be treated as decisive in this small study. Results will emphasise
effect sizes, uncertainty intervals, paper-level variation, and qualitative
disagreement analysis.

Krippendorff’s alpha may be reported as a secondary sensitivity analysis
only for dimensions with a pre-specified unit of analysis and explicit rules
for multi-label values, missing values, and not-applicable values. It will
not be combined into one overall score for the full annotation task.

### 11.8 Pre-specified secondary questions

1. Does the autonomous AI `confidence_summary` identify papers or items
   where humans later disagree with the AI draft?
2. Do `ai_uncertainty` and `ai_assumption` flags identify items that are
   later edited during review?
3. Does AI batch review reduce the number or severity of problems later
   found during human review?
4. How much does manual self-review change H0 into H1?
5. How stable is the human annotator after washout?

### 11.9 Candidate extensions

If human and AI routes identify the same candidate extension from the same
paper, this is recorded as convergent detection of a possible schema gap.

It does not satisfy the GEM two-paper rule for promoting an extension. That
rule requires evidence from two independent papers.

---

## 12. Endpoints

### Primary endpoints

- **E1:** Per-dimension agreement between H0 and A0 in the typical stratum,
  reported as exact agreement and hierarchy-weighted agreement where
  applicable.
- **E2:** Evidence-item decomposition precision, recall, and F1 between H0
  and A0 in the typical stratum.
- **E3:** Interactive-review flag acceptance rate for review of H1.
- **E4:** The blinded disagreement taxonomy.

H0-versus-A0 results will be interpreted alongside AI repeatability
(A0-versus-A0x, and A0y if used).

### Secondary endpoints

- source-span overlap;
- A0-versus-A0x AI repeatability;
- batch-review and human-review overlap in RH(A0);
- remaining human corrections after batch review in RH(A1);
- H0-to-H1 self-review changes;
- washout stability;
- candidate-extension convergence;
- confidence and flag calibration; and
- effort by route.

---

## 13. Reporting and release

The manuscript will present:

- one main-text table of primary endpoints;
- at most one main-text figure;
- detailed per-paper results, disagreement taxonomy, and review logs in the
  supplement; and
- a clear description of all AI use, including model identifiers and the
  role of AI in study design.

The human annotator is a co-author of the resulting manuscript.
Publication of effort figures is covered by the annotator's signed
agreement.

After study close:

1. study annotations will be merged into `annotations/` with full
   provenance;
2. the corpus release will receive a citable archive identifier; and
3. frozen materials, hashes, amendments, analysis code, and de-identified
   blinded comparison files will be released where licensing permits.

---

## 14. Optional future work

The following are outside the present study unless resources permit:

1. Annotation by a second AI model using the same frozen materials.
2. Independent annotation by a second trained human annotator.
3. A second review round if the pre-specified trigger conditions in the
   review protocol are met.