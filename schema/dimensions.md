# Dimensions of the Genetic Evidence Model — Reference

This document is the human-readable enumeration reference for every dimension
in the model. The machine-checkable version lives in
`genetic_evidence.shacl.ttl`. The paper describes the dimensions
conceptually; this file lists their current enumerations.

Dimensions marked **PROMOTED** have been adopted into the model as first-class
dimensions after surfacing during annotation and being accepted by the curator.
Dimensions marked **CANDIDATE** have been surfaced once during annotation but
have not yet been encountered in a second independent paper (per the
promotion rule: a second, independent occurrence promotes the candidate to
first-class).

---

## Core dimensions (always required)

### Knowledge Domain

Cardinality: multiple. Objectivity: objective.

| Value | Meaning |
| --- | --- |
| `HUMAN_GENETICS`      | Evidence from human family- or inheritance-based genetic studies (pedigrees, segregation, transmission) |
| `ANIMAL_GENETICS`     | Non-human animal genetics outside a model-organism context |
| `POPULATION_GENETICS` | Population-level variation, allele frequencies, case-control association, GWAS, PGS |
| `COMPARATIVE_GENOMICS`| Cross-species sequence/synteny analysis |
| `EPIGENETICS`         | Methylation, chromatin, non-sequence inheritance |
| `GENE_FUNCTION`       | Molecular function of gene products |
| `MODEL_ORGANISM`      | Experimental work in a non-human organism used as a model |

### Method

Cardinality: multiple. Objectivity: objective.

The `method` dimension records *how* the evidence was generated. It is the
first dimension of the model to receive an explicit **hierarchical structure**
rather than a flat enumeration. To stay consistent with OBO conventions, the
hierarchy is expressed as `is_a` relations between terms (subject `is_a`
object), which lift directly to OWL `rdfs:subClassOf` when the schema is
rendered as an ontology (future work; see §6.2 of the companion paper).
Subsumption is transitive: `GWAS is_a ASSOCIATION_STUDY` and
`ASSOCIATION_STUDY is_a STATISTICAL_GENETICS`, so a `GWAS` is also (by
transitivity) a `STATISTICAL_GENETICS`.

**Method terms.**

| Term | Meaning |
| --- | --- |
| `STATISTICAL_GENETICS`             | Population-level statistical inference from genetic data |
| `ASSOCIATION_STUDY`                | Statistical test of association between genetic variation and phenotype |
| `GWAS`                             | Genome-wide, hypothesis-free association scan |
| `CANDIDATE_GENE_STUDY`             | Hypothesis-driven association study at one or a small set of genes |
| `FINE_MAPPING`                     | Within-locus association analysis, often with conditional or LD-aware modelling |
| `FAMILY_BASED`                     | Statistical inference from family or pedigree data |
| `LINKAGE_ANALYSIS`                 | LOD-score-based identification of disease-linked chromosomal regions |
| `TRANSMISSION_DISEQUILIBRIUM_TEST` | Tests for non-random allele transmission to affected offspring (TDT, FBAT) |
| `SEGREGATION_ANALYSIS`             | Tests of Mendelian segregation patterns in pedigrees |
| `META_ANALYSIS`                    | Combining results across studies; includes polygenic-score construction from multiple GWASes |
| `EXPERIMENT`                       | Empirical procedure (laboratory or computational simulation) producing new data points |
| `IN_VIVO`                          | Experiment in a living organism |
| `IN_VITRO`                         | Experiment in isolated cells, tissues, or biochemical systems outside a living organism |
| `IN_SILICO`                        | Computational simulation of a biological process (molecular dynamics, docking, simulation models) |
| `BIOINFORMATICS_INFERENCE`         | Computational analysis of existing biological data to characterise or predict features |
| `CLINICAL_EVIDENCE`                | Observation of variants or phenotypes in clinical contexts |

The four top-level families, `STATISTICAL_GENETICS`, `EXPERIMENT`,
`BIOINFORMATICS_INFERENCE`, and `CLINICAL_EVIDENCE`, have no parent and so do
not appear as a subject in the relations table below.

**Method hierarchy (`is_a` relations).**

| Term | Relation | Parent term |
| --- | --- | --- |
| `ASSOCIATION_STUDY`                | `is_a` | `STATISTICAL_GENETICS` |
| `GWAS`                             | `is_a` | `ASSOCIATION_STUDY`    |
| `CANDIDATE_GENE_STUDY`             | `is_a` | `ASSOCIATION_STUDY`    |
| `FINE_MAPPING`                     | `is_a` | `ASSOCIATION_STUDY`    |
| `FAMILY_BASED`                     | `is_a` | `STATISTICAL_GENETICS` |
| `LINKAGE_ANALYSIS`                 | `is_a` | `FAMILY_BASED`         |
| `TRANSMISSION_DISEQUILIBRIUM_TEST` | `is_a` | `FAMILY_BASED`         |
| `SEGREGATION_ANALYSIS`             | `is_a` | `FAMILY_BASED`         |
| `META_ANALYSIS`                    | `is_a` | `STATISTICAL_GENETICS` |
| `IN_VIVO`                          | `is_a` | `EXPERIMENT`           |
| `IN_VITRO`                         | `is_a` | `EXPERIMENT`           |
| `IN_SILICO`                        | `is_a` | `EXPERIMENT`           |

Convention: when multiple methods apply, the optional `primary_method` field
records the curator's hierarchy preference. Multiple values from this
dimension are interpreted as **additive, not hierarchical** (e.g.,
`method: [GWAS, META_ANALYSIS]` means both apply); do not list a leaf and its
own ancestor together unless both genuinely apply.

#### Notes on the structure

**Why `EXPERIMENT` is a parent.** The pre-hierarchical schema had
`IN_VIVO_EXPERIMENT` and `IN_VITRO_EXPERIMENT` as flat sibling values, with no
explicit acknowledgement that they share an epistemic structure (a controlled
procedure producing new data points). Introducing `EXPERIMENT` as a parent
makes the shared structure explicit and creates a natural home for `IN_SILICO`
as a third sibling.

**`IN_SILICO` is distinct from `BIOINFORMATICS_INFERENCE`.** The two are easy
to conflate but capture different epistemic operations. `IN_SILICO` is
computational *simulation*: a model is constructed, parameterised, executed,
and analysed, producing new data points by execution (molecular dynamics,
docking, forward population-genetics simulation). `BIOINFORMATICS_INFERENCE` is
computational *analysis* of existing data (sequences, structures, database
records) to characterise or predict features of those data, with no process
simulated (conservation analysis, splice-site prediction, variant-impact
prediction). A study running molecular dynamics to predict the effect of a
substitution is `IN_SILICO`; a study running SIFT or PolyPhen on a list of
substitutions is `BIOINFORMATICS_INFERENCE`.

**Branches kept flat in this revision.** `BIOINFORMATICS_INFERENCE` and
`CLINICAL_EVIDENCE` are top-level families without children in this version.
Natural decompositions exist (`CONSERVATION_ANALYSIS`, `SPLICE_PREDICTION`,
`IMPACT_PREDICTION` for the former; `PEDIGREE_SEGREGATION`, `CASE_REPORT`,
`CASE_SERIES` for the latter) and are candidates for elaboration as the corpus
exercises more leaves. Until then they remain flat to avoid introducing
structure not exercised by available evidence.

#### How to use the hierarchy in annotations

See `protocols/PROTOCOL.md` §3.4. The short version: pick the most specific
applicable value; parent relationships are recoverable from the `is_a`
hierarchy table above.
If you are confident only at an intermediate level (e.g., the paper says
"statistical genetics" without specifying the design), record the intermediate
value and emit `ai_uncertainty` on the dimension.

#### Backward compatibility

Existing annotations in the corpus use the pre-hierarchical flat values
(`STATISTICAL_GENETICS`, `IN_VIVO_EXPERIMENT`, `IN_VITRO_EXPERIMENT`,
`BIOINFORMATICS_PREDICTION`). These remain valid: `STATISTICAL_GENETICS` is a
legitimate value (the top of its family); `IN_VIVO_EXPERIMENT` and
`IN_VITRO_EXPERIMENT` are legacy synonyms for `IN_VIVO` and `IN_VITRO`; and
`BIOINFORMATICS_PREDICTION` is a legacy synonym for `BIOINFORMATICS_INFERENCE`.
A future curator-review pass will migrate these to leaf values where the
underlying paper supports a more specific assignment (see
`notes/ROADMAP.md` §1.b); until then, annotations using flat values are
interpreted as having committed to the intermediate level only.

Note: the earlier POPULATION_DATA and EPIGENETICS_DATA method values
(never exercised by any annotation in the corpus) no longer appear as
standalone method values in this revision. Their content is recovered in
two places:

* Population-scale statistical work is recorded under
STATISTICAL_GENETICS (or its leaves such as GWAS or
META_ANALYSIS); the relevant phenomenon is captured by the
POPULATION_GENETICS value in knowledge_domain.
* Epigenetic work is recorded with the appropriate experimental
method (IN_VIVO, IN_VITRO, or BIOINFORMATICS_INFERENCE,
depending on the workflow); the relevant phenomenon is captured
by the EPIGENETICS value in knowledge_domain.

The general principle: the previous *_DATA method values conflated
what the evidence concerns (knowledge domain) with how it was
generated (method). The revision separates these into the appropriate
dimensions.

### Target type

Cardinality: single. Objectivity: objective.

| Value | Meaning |
| --- | --- |
| `GENE`         | A single gene |
| `RELATED_GENE` | Another gene related to the primary target |
| `VARIANT`      | A specific sequence variant |
| `SEGMENT`      | A defined genomic segment |
| `INTERVAL`     | A coordinate interval (bp or cM) |
| `TRANSCRIPT`   | A transcript isoform |

### Resolution

Cardinality: single. Objectivity: objective.

| Value | Meaning |
| --- | --- |
| `WINDOW`            | Coarse genomic window |
| `GENE`              | Gene-level resolution |
| `FUNCTIONAL_ELEMENT`| Regulatory or functional element |
| `POSITION`          | Single-base position |
| `VARIANT`           | Specific variant |

### Credibility

Cardinality: one overall rating, plus optional facets. Objectivity: subjective.

The overall credibility is an ordinal rating from the enumeration
`{VERY_HIGH, HIGH, MEDIUM, LOW}` (anchored on SEPIO confidence), optionally
accompanied by a free-text `credibility_comment` and by separately rated
facets — statistical power / sample size, independent replication,
multiple-testing control, ancestry or population-stratification control,
and ascertainment. The facet keys are not a closed set and grow with the
corpus; facets observed so far include `cohort_size`, `replication_cohort`,
`ancestry_composition`, `followup_duration`, `source_GWAS`,
`n_variants_tested`, `multiple_testing_correction`. The SHACL shape enforces
the overall ordinal rating; the facets remain open.

### **PROMOTED**: phenotype_scale

Cardinality: single per evidence item. Objectivity: objective.

Promoted based on Jossin 2017 annotation where three separate "phenotype"
callouts tagged passages at distinct scales of phenotypic description. The
existing `Resolution` dimension captures *genetic* scale; this dimension
captures *phenotypic* scale, which is independent of genetic scale.

| Value | Meaning |
| --- | --- |
| `MOLECULAR`    | Molecular-level phenotype (binding, activity) |
| `CELLULAR`     | Cell-level phenotype (morphology, polarity) |
| `HISTOLOGICAL` | Tissue-level phenotype (cell composition, architecture) |
| `ORGANISMAL`   | Whole-organism phenotype (gross anatomy, behavior) |
| `CLINICAL`     | Human clinical phenotype |

Relation to existing vocabularies: ECO and HPO both carry partial
information here under different modeling assumptions. Unification with
those vocabularies is flagged as future work.

### **PROMOTED**: variant_ascertainment

Cardinality: multiple. Objectivity: objective. **Conditional**: required
only when `target_type = VARIANT` (a variant-level ascertainment route
applies only to variant targets); the SHACL shape enforces it under that
condition, and an explicit `not_applicable_or_omitted` is accepted where a
variant target has no single ascertainment mode (e.g. a polygenic score).

Promoted based on Davis 2011 annotation, where the paper explicitly studies
two populations of variants with different epistemic status: variants
observed in patients (~14 in pedigrees / 38 heterozygous cases) versus
variants tested functionally regardless of patient observation (40 total in
zebrafish). The dimension records the ascertainment route by which each
variant entered the study.

| Value | Meaning |
| --- | --- |
| `OBSERVED_IN_CASES`    | Variant observed in one or more affected individuals |
| `OBSERVED_IN_CONTROLS` | Variant observed only in unaffected individuals |
| `FROM_DATABASE`        | Variant sourced from a database (HapMap, dbSNP, gnomAD) |
| `SYNTHETIC`            | Variant constructed in silico / in the laboratory |

---

## Conditional dimensions

### When Knowledge Domain contains `HUMAN_GENETICS` and Target type = `GENE`

| Dimension               | Value type  | Cardinality |
| ----------------------- | ----------- | ----------- |
| `mode_of_inheritance`   | categorical | single      |
| `mendelian_segregation` | boolean     | single      |
| `exact_variant`         | boolean     | single      |
| `subdomain`             | categorical | single      |

Subdomain enumeration: `GWAS`, `Linkage Study`, `WGS-WES Study`,
`Candidate Gene Study`.

### When Knowledge Domain contains `HUMAN_GENETICS` and Target type = `VARIANT`

| Dimension                       | Value type              | Cardinality |
| ------------------------------- | ----------------------- | ----------- |
| `environmental_factors`         | quasi-categorical       | multiple    |
| `penetrance`                    | categorical             | single      |
| `genetic_background_considered` | boolean                 | single      |

Penetrance enumeration: `complete`, `incomplete`, `unknown`.

### When Knowledge Domain contains `GENE_FUNCTION`

| Dimension            | Value type  | Cardinality |
| -------------------- | ----------- | ----------- |
| `measurement_target` | categorical | multiple    |
| `gene_relation`      | categorical | single      |

Measurement target enumeration: `EXISTENCE`, `EXPRESSION`, `STABILITY`,
`BINDING`, `LOCALIZATION`, `ACTIVITY`, `CATALYSIS`.

Gene relation enumeration: `X_has_same_function_as_Y`, `X_regulates_Y`,
`X_inhibits_Y`.

### When Method contains `IN_VIVO` (or legacy `IN_VIVO_EXPERIMENT`) or Knowledge Domain contains `MODEL_ORGANISM`

| Dimension                  | Value type   | Cardinality |
| -------------------------- | ------------ | ----------- |
| `organism`                 | categorical  | multiple    |
| `specificity_of_phenotype` | free text    | single      |

### When Knowledge Domain contains `MODEL_ORGANISM`

| Dimension                  | Value type   | Cardinality |
| -------------------------- | ------------ | ----------- |
| `knockout_type`            | categorical  | single      |

Knockout type enumeration: `CONDITIONAL`, `UNCONDITIONAL`. (Activation
is narrower than `organism`: a knockout type is only meaningful for
model-organism evidence, not for every in-vivo experiment.)

---

## Candidate dimensions and enumeration values

The following have been surfaced once during annotation but have not yet been
independently confirmed by a second paper. They are recorded here for
traceability; each promotion requires a second paper exercising the same gap.

### Candidate: `PROTEIN_SUBDOMAIN` value for Resolution

Source: Jossin 2017, WD14/WD10 domain mapping for LLGL1–N-cadherin
interaction.

### Candidate: `INTERACTION` and `COMPLEX` values for Target type

Source: Jossin 2017 in vivo dominant-negative experiment, which targets the
LLGL1–N-cadherin interaction rather than a gene. The LLGL1–N-cadherin–β-catenin
tripartite complex also motivates a `COMPLEX` target value.

### Candidate: additional Gene relation values

Source: Jossin 2017 — `X_physically_binds_Y` and
`X_regulates_trafficking_of_Y`. The existing enumeration covers functional
equivalence, regulation, and inhibition; it does not cover physical binding
or trafficking regulation.

### Candidate: `knowledge_domain_priority`

Source: Davis 2011 annotator used "Model Organism (primary) Human Genetics
Functional (somewhat)" — an explicitly ordered compound value. Would either
attach an ordinal priority to each knowledge_domain value or introduce a
scalar `primary_knowledge_domain` field (analogous to `primary_method`).

### Candidate: `curator_critique` sub-block on Assertion

Source: Davis 2011 annotator's callout "Looks unrealistic, they have twice
as many cases..." — a methodological critique attached to a specific
assertion in the paper. Would attach raised_by / concern / status fields
to `GeneticEvidenceAssertion`.

---

## Free-form extension

Per the model's design, `special_considerations` accepts arbitrary key-value
pairs. Keys observed in the corpus include: `cell_type`,
`developmental_timing`, `cre_driver`, `techniques`, `cohort_composition`,
`variant_yield`, `ancestry_stratification`. Promotion of any such key to a
named dimension requires a second paper to exercise the same slot and
curator review.
