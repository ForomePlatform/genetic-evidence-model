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
| `HUMAN_GENETICS`      | Evidence from human genetic studies (family, cohort, case-control) |
| `ANIMAL_GENETICS`     | Non-human animal genetics outside a model-organism context |
| `POPULATION_GENETICS` | Population-level variation, allele frequencies, GWAS, PGS |
| `COMPARATIVE_GENOMICS`| Cross-species sequence/synteny analysis |
| `EPIGENETICS`         | Methylation, chromatin, non-sequence inheritance |
| `GENE_FUNCTION`       | Molecular function of gene products |
| `MODEL_ORGANISM`      | Experimental work in a non-human organism used as a model |

### Method

Cardinality: multiple. Objectivity: objective.

| Value | Meaning |
| --- | --- |
| `CLINICAL_EVIDENCE`        | Clinical observation, phenotype report, pedigree |
| `STATISTICAL_GENETICS`     | Association, linkage, segregation statistics |
| `BIOINFORMATICS_PREDICTION`| In silico prediction (splice, conservation, structure) |
| `IN_VIVO_EXPERIMENT`       | Experimental intervention in a whole organism |
| `IN_VITRO_EXPERIMENT`      | Experimental work in cell culture or cell-free systems |
| `POPULATION_DATA`          | Aggregated population data (gnomAD, 1000G, biobanks) |
| `EPIGENETICS_DATA`         | Measurement of epigenetic state |

Convention: when multiple methods apply, the optional `primary_method` field
records the curator's hierarchy preference.

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

Cardinality: multiple. Objectivity: subjective.

Expressed as fuzzy key-value pairs. Accompanying free-text
`credibility_comment` supported. No closed enumeration — the keys grow with
the corpus.

Common keys observed so far: `cohort_size`, `replication_cohort`,
`ancestry_composition`, `followup_duration`, `source_GWAS`,
`n_variants_tested`, `multiple_testing_correction`.

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

Cardinality: multiple. Objectivity: objective.

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

### When Method contains `IN_VIVO_EXPERIMENT` or Knowledge Domain contains `MODEL_ORGANISM`

| Dimension                  | Value type   | Cardinality |
| -------------------------- | ------------ | ----------- |
| `organism`                 | categorical  | multiple    |
| `knockout_type`            | categorical  | single      |
| `specificity_of_phenotype` | free text    | single      |

Knockout type enumeration: `CONDITIONAL`, `UNCONDITIONAL`.

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
