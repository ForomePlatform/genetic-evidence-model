# Roadmap

This document tracks the active and planned work on the
Genetic Evidence Model (GEM) project beyond the snapshot
documented in the companion paper. It is a living record of
what is in progress, what is planned, what is deferred, and
what has already shipped.

Items are tagged with a status:

- **complete:** the work has shipped; remains here as record.
- **in-progress:** active work, partially complete.
- **planned:** scoped and committed but not yet started.
- **deferred:** considered and explicitly postponed, with reason.

Each item names a concrete next step where one exists.

---

## 1. Method-dimension hierarchical structure

**Status: in-progress.**

The `method` dimension was a flat enumeration in the original
schema. In response to a reviewer comment on the flat structure
of the dimensional vocabulary, the dimension has been
restructured as a hierarchy with parent-child relationships
between values (see `schema/dimensions.md`).

Two activities flow from this:

### 1.a Schema and protocol changes

**Status: complete.**

The hierarchical `method` enumeration is in `schema/dimensions.md`.
The annotation protocol's rule for hierarchical dimensions is in
`protocols/PROTOCOL.md` §3.4. The hierarchy is documented as `is_a`
relations between terms (subject `is_a` object), structured to lift
directly to OWL `rdfs:subClassOf` when the schema is rendered as an
ontology (item 2 below). The SHACL schema
(`schema/genetic_evidence.shacl.ttl`) already encodes these `is_a`
relations as `rdfs:subClassOf` axioms.

### 1.b Migration of existing corpus annotations

**Status: in-progress.**

The six existing corpus annotations were authored under the
pre-hierarchical schema and use flat method values such as
`STATISTICAL_GENETICS` or `IN_VIVO_EXPERIMENT`. These remain
valid as intermediate-value annotations under the new hierarchy;
no annotation is "wrong." Where the underlying paper supports a
more specific value, the annotation can be migrated to a leaf
value (`GWAS`, `IN_VIVO`, etc.).

Expected per-paper migrations:

| Paper          | Notable migrations                                                                                       |
| -------------- | -------------------------------------------------------------------------------------------------------- |
| Jossin 2017    | `IN_VIVO_EXPERIMENT` → `IN_VIVO` and `IN_VITRO_EXPERIMENT` → `IN_VITRO` (renames).                       |
| Davis 2011     | GE-1 `STATISTICAL_GENETICS` → `CANDIDATE_GENE_STUDY` (resequencing, not genome-wide); experimental renames. |
| Nelson 1992    | `IN_VITRO_EXPERIMENT` → `IN_VITRO`; segregation evidence may refine to `SEGREGATION_ANALYSIS`.            |
| Gupta 2015     | No migration expected (existing flat values remain appropriate).                                         |
| Duerr 2006     | GE-1 → `GWAS`; GE-2 → `ASSOCIATION_STUDY`; GE-3 → `TRANSMISSION_DISEQUILIBRIUM_TEST`; GE-4 → `FINE_MAPPING`; GE-5 → `GWAS`; GE-6 → `IN_VIVO`/`IN_VITRO` (renames). Reconciled with the applied review (`annotations/reviews/duerr2006-review-2026-06-04.yaml`); the corpus has no GE-8. |
| Inouye 2018    | GE-1 → `META_ANALYSIS` (polygenic-score construction).                                                   |

Migration is best-effort and non-blocking. Annotations using
intermediate values remain valid; the migration improves
specificity rather than correctness.

**Next step:** curator review of each annotation to apply
leaf-value migrations where supported. Migrations are recorded
in the annotation's `provenance` block.

---

## 2. OWL / LinkML rendering of the schema

**Status: planned.**

The current schema is distributed as SHACL shapes
(`schema/genetic_evidence.shacl.ttl`) plus a human-readable
dimension reference (`schema/dimensions.md`). For broader
interoperability with the OBO Foundry and Bridge2AI ecosystems,
the schema should be available in OWL and LinkML renderings
as well.

The recently-introduced hierarchical `method` dimension was
designed to be directly liftable: each `is_a` relation maps onto
`rdfs:subClassOf` in OWL or the corresponding LinkML constructor
(and is already carried as `rdfs:subClassOf` in the SHACL schema).
Other dimensions are currently flat and would render as plain
enumerations in OWL.

**Next step:** identify a single source-of-truth representation
from which all four renderings (SHACL, OWL, LinkML, JSON Schema)
can be generated. LinkML is the strongest candidate because
its tooling already targets these output formats.

---

## 3. Second corpus annotation

**Status: planned.**

The current corpus is six papers. The reviewer-acknowledged
evaluation limitation in §6.2 of the paper points to this:
six papers and a single human annotator do not support claims
about inter-annotator agreement or generalisability.

A second corpus pass would target the strongest unpromoted
candidate extensions in `schema/EXTENSIONS.md` (those that
have surfaced once and need a second independent occurrence
to be promoted) and would extend the corpus to a domain
adjacent to but distinct from variant interpretation in
clinical genomics.

**Next step:** scope the second corpus (size, paper selection
criteria, target candidate extensions). A working candidate
size is 10 to 15 papers.

---

## 4. Interactive annotation workflow

**Status: planned.**

The current annotation protocol exists in a single mode
(`protocols/PROTOCOL_AUTONOMOUS.md`): the AI produces a
complete YAML in one pass and the curator reviews the result.
An interactive annotation workflow would invert this: the
curator collaborates with the AI through decomposition, then
through dimension assignment, with the AI emitting
intermediate state for curator confirmation at each stage.

This is the analogue of the review skill (which is
interactive) for the annotation skill (which is currently
autonomous-only).

**Next step:** specify `protocols/PROTOCOL_INTERACTIVE.md`,
modelled on `protocols/REVIEW_PROTOCOL_INTERACTIVE.md`.

---

## 5. Batch review workflow

**Status: planned.**

The current review protocol exists in a single mode
(`protocols/REVIEW_PROTOCOL_INTERACTIVE.md`): a curator
participates in dialogue with the AI through every item. A
batch review workflow would produce a review log for an
annotation autonomously, suitable for screening many
annotations quickly without curator interaction.

This is the analogue of the autonomous-annotation skill for
the review skill.

**Next step:** specify `protocols/REVIEW_PROTOCOL_BATCH.md`.

---

## 6. Hierarchical structure for other dimensions

**Status: deferred.**

The method-dimension hierarchy (item 1) is the first
hierarchical dimension in the schema. Other dimensions have
natural hierarchical structures that were considered for
the current revision but deferred:

- **`knowledge_domain`** has `MODEL_ORGANISM` as a parent with
  natural children (mouse, zebrafish, rat, drosophila, etc.).
  The deferral reason is interaction with the existing
  conditional `organism` dimension: introducing hierarchy
  under `knowledge_domain` would create redundancy that
  requires a careful design choice between deprecating
  `organism`, restricting it to strain-level information, or
  living with the redundancy.

- **`phenotype_scale`** has a natural ordering (molecular ⟶
  cellular ⟶ histological ⟶ organismal ⟶ clinical) but the
  ordering is by scale, not by subsumption. A scale-ordering
  encoding requires choosing between SKOS-style ordered lists,
  partial-order axioms in OWL, or a numeric-scale annotation
  on each value. None is obviously right.

- **`BIOINFORMATICS_INFERENCE`** and **`CLINICAL_EVIDENCE`**
  branches under `method` are kept flat in the current
  revision. Natural decompositions exist (conservation
  analysis, splice prediction, impact prediction;
  pedigree segregation, case report, case series) but the
  corpus does not yet exercise enough leaves to motivate
  promotion.

**Next step:** these will be revisited when either (a) the
corpus exercises the hierarchy concretely, or (b) the OWL
rendering work (item 2) requires consistent treatment
across dimensions.

---

## 7. Coverage computation tooling

**Status: planned.**

`annotations/coverage.md` is currently maintained manually.
A `scripts/compute_coverage.py` would auto-regenerate the
file from the current YAML annotations, eliminating drift
between the annotations and their derived summary.

**Next step:** specify the script's expected output format
(should match the current `coverage.md` exactly) and a
deterministic algorithm for the per-cell rationale text.

---

## 8. Clinical-deployment study

**Status: deferred.**

The paper's §6.2 names this as a future-work direction: the
model is motivated by variant interpretation in
clinical-genomics programs, but the current pilot stops short
of applying the model to a live workflow.

A clinical-deployment study would integrate the schema with
an existing variant-interpretation pipeline (a candidate is
the AnFiSA platform documented in the companion preprint),
producing live annotations that downstream classifiers can
consume.

**Next step:** none in the near term. This item depends on
items 1 (method-hierarchy migration complete) and 3 (a second
corpus annotated and validated) before it would be productive.

---

## How to use this roadmap

- A reader of the paper or repository can consult this file
  to understand what is in scope for active development and
  what is named as future work.
- A contributor can pick up any **planned** item with a clear
  next step.
- Items move from **planned** to **in-progress** when work
  begins; from **in-progress** to **complete** when shipped.
- Deferred items can be re-promoted when the conditions
  named in their "Next step" change.

This file is updated as items move. Significant changes are
recorded in the repository's commit history.
