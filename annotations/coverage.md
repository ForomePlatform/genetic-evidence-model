# Dimension coverage of the six-paper pilot

This file reports per-dimension population counts for the six
annotated papers that form the corpus pilot of the Genetic Evidence
Model. The aggregate counts are reported in §5.2 of the ICBO 2026
paper (`tab:coverage`); this file gives the per-paper breakdown, the
definition of "applicable" for each dimension, and the rationale for
every zero-populated or under-populated cell.

## Corpus summary

- **6 papers, 28 `GeneticEvidence` items** in total.
- **4 manual annotations** (Jossin, Davis, Nelson, Gupta) treated as
  ground truth.
- **2 AI-drafted annotations** (Duerr, Inouye) pending full curator
  review.

| Paper | GE items | Source | Credibility | Role |
| ----- | -------: | ------ | ----------- | ---- |
| Jossin 2017 | 6 | manual | Very high | molecular mechanism |
| Davis 2011  | 6 | manual | High      | breadth exemplar |
| Nelson 1992 | 3 | manual | Medium    | classical molecular genetics |
| Gupta 2015  | 2 | manual | Low       | low-credibility edge case |
| Duerr 2006  | 6 | AI-drafted | High | clean GWAS exemplar |
| Inouye 2018 | 5 | AI-drafted | High/Medium | model-extension stress test |
| **Total**   | **28** | | | |

## Always-required dimensions

For every dimension in this group, "applicable" = all 28 items. The
schema validator rejects annotations that leave any of these empty,
so population is 28/28 by construction.

| Dimension              | Populated | Applicable |
| ---------------------- | --------: | ---------: |
| Knowledge Domain       | 28 | 28 |
| Method                 | 28 | 28 |
| Target Type            | 28 | 28 |
| Resolution             | 28 | 28 |
| Credibility            | 28 | 28 |
| Phenotype Scale        | 28 | 28 |
| Variant Ascertainment  | 21 | 21 |

**Variant Ascertainment** is the one exception: it is always required
*when applicable*, and "applicable" is restricted to items whose
`target_type` is `VARIANT`. Of the 28 items, 21 target a variant;
for the remaining 7 (target_type GENE, INTERVAL, etc.) the dimension
is not activated and is correctly empty.

## Conditional dimensions

For this group, "applicable" is item-specific: it depends on whether
the dimension's activation condition holds for each item.

| Dimension              | Populated | Applicable | Per-paper breakdown |
| ---------------------- | --------: | ---------: | --- |
| Mode of Inheritance    |  0 |  1 | Duerr GE-3 only (see below) |
| Mendelian Segregation  |  0 |  1 | Duerr GE-3 only (see below) |
| Penetrance             |  2 |  4 | Jossin (1/2), Davis (1/2) |
| Measurement Target     | 10 | 11 | Jossin (6/6), Davis (2/2), Nelson (2/3) |
| Gene Relation          |  1 | 11 | Jossin only (see below) |
| Organism               |  7 |  8 | Jossin (1/1), Davis (3/3), Nelson (2/2), Duerr GE-6 (0/1), other (1/1) |
| Knockout Type          |  1 |  6 | Jossin GE-3 only |

## Commentary on the under-populated cells

### Mode of Inheritance (0/1) and Mendelian Segregation (0/1)

Both activation conditions (`HUMAN_GENETICS` AND `target_type = GENE`)
are satisfied by exactly one item across the corpus: Duerr GE-3, the
family-based transmission disequilibrium analysis in 883 nuclear
families. That item is a complex-trait study where the AI reviewer
flagged `ai_uncertainty` against both dimensions because the paper
does not claim a Mendelian mode and the current enumeration does not
include a `COMPLEX` value. The items are therefore correctly empty
with an explicit flag.

Cross-paper note: the other gene-level items in the corpus
(Jossin's *Llgl1* knockout, Davis's TTC21B pedigree, Nelson's CD18
splice variant, Gupta's ATP6AP2 intellectual-disability family) all
belong to `MODEL_ORGANISM` or mixed `HUMAN_GENETICS` +
`IN_VIVO_EXPERIMENT` scopings that do not activate the HG+GENE rule.

### Penetrance (2/4)

Activation condition: `HUMAN_GENETICS` AND `target_type = VARIANT`.
Four items across Jossin, Davis satisfy the condition; two are
populated (the two with explicit penetrance discussion in the
paper's text) and two are left empty with `reviewer_suggestion`
flags noting that the paper is silent on penetrance.

### Measurement Target (10/11)

Activation condition: `knowledge_domain` contains `GENE_FUNCTION`.
Ten of eleven applicable items are populated; the single empty case
is Nelson GE-3 (the alloantibody-binding assay) where the value
`BINDING` was proposed by the AI reviewer as a `reviewer_suggestion`
but not adopted in the ground-truth annotation pending curator
confirmation.

### Gene Relation (1/11)

Activation condition: `knowledge_domain` contains `GENE_FUNCTION`.
Only Jossin GE-4 populates the dimension with a current enumeration
value (`X_inhibits_Y`). The other ten applicable items all involve
physical binding or trafficking regulation, neither of which is in
the current enumeration `{X_has_same_function_as_Y, X_regulates_Y,
X_inhibits_Y}`. The gap motivates candidate extension CE-J3 (see
`schema/EXTENSIONS.md`), which proposes adding
`X_physically_binds_Y` and `X_regulates_trafficking_of_Y`. Under
the two-papers rule, CE-J3 would promote if a second paper
exercises the same gap.

### Organism (7/8)

Activation condition: `method` contains `IN_VIVO_EXPERIMENT` OR
`knowledge_domain` contains `MODEL_ORGANISM`. Seven of eight
applicable items are populated. The one empty item is Duerr GE-6,
which collects mouse-model work *cited* by the paper rather than
work the paper itself performed, and the AI reviewer flagged an
`ai_assumption` asking whether cited-work items should carry organism
values from the cited studies or leave the dimension empty pending a
curator policy decision.

### Knockout Type (1/6)

Activation condition: `knowledge_domain` contains `MODEL_ORGANISM`.
Only Jossin GE-3 (the conditional Llgl1 knockout) populates the
dimension. The other five applicable items are in vivo experiments
that are not knockouts (dominant-negative injections, retinal
electroporation, and so on). The low population is not a schema
shortcoming but an artefact of the activation condition firing on
items where the dimension is not literally meaningful; a future
refinement could narrow the condition to knockout-specific methods.

## Methodology note

Counts were computed by reading each of the six `.yaml` annotation
files and, for each item, checking whether the dimension value is a
concrete value (populated) or one of `null`, the empty list,
`{ annotated_as: not_applicable_or_omitted }`, or `ai_uncertainty`
(not populated). The `annotated_as: not_applicable_or_omitted`
cases were counted as "populated" for always-required dimensions
(the annotator considered and chose not to fill) and as "not
populated" for conditional dimensions where the activation
condition did not hold.

A reproducible script is not yet packaged in the repository; this
file is maintained by hand. Candidate future work: a small
`scripts/compute_coverage.py` that regenerates this table from the
YAML files, so the paper's `tab:coverage` can be kept in sync with
the annotations automatically.
