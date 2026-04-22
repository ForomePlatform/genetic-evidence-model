# Dimension coverage and reviewer flags in the six-paper pilot

This file reports per-paper detail for the six annotated papers that
form the corpus pilot of the Genetic Evidence Model. It has two
parts:

1. **Dimension coverage** (sections below): per-dimension population
   counts, with the definition of "applicable" for each dimension
   and the rationale for every zero-populated or under-populated
   cell. The aggregate counts are reported in §5.1 of the ICBO 2026
   paper (`tab:coverage`).

2. **Reviewer-flag counts** (final section): per-paper counts of the
   five flag types recorded during annotation. The ICBO 2026 paper
   gives only the aggregate totals in §5.2 prose; this file is the
   authoritative per-paper breakdown.

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

## Reviewer-flag counts per paper

The annotation workflow records five flag types across two tracks
(§5.2 of the ICBO 2026 paper). The table below gives per-paper
counts. Manual-track flags (Query, Suggestion, Disagree) apply to
the four manually annotated papers; AI-track flags (ai_uncertainty,
ai_assumption) to the two AI-drafted papers.

| Paper  | Track       | Query | Suggestion | Disagree | AI unc. | AI assum. |
| ------ | ----------- | ----: | ---------: | -------: | ------: | --------: |
| Jossin | manual      |   3   |    1       |    0     |    —    |    —      |
| Davis  | manual      |   2   |    1       |    1     |    —    |    —      |
| Nelson | manual      |   0   |    3       |    0     |    —    |    —      |
| Gupta  | manual      |   0   |    1       |    0     |    —    |    —      |
| Duerr  | AI-drafted  |   —   |    —       |    —     |    3    |    2      |
| Inouye | AI-drafted  |   —   |    —       |    —     |    0    |    2      |
| **Total** |          | **5** | **6**      | **1**    | **3**   | **4**     |

### Observations

- **Disagreements are rare (1/4 manual papers).** Davis is the only
  manual paper with a `reviewer_disagreement`: the curator's
  summary listed the organism set as {mouse, zebrafish} but the
  paper also reported a rat retinal electroporation experiment.
  Other manual papers produced no factual corrections because the
  annotator also authored the summary being compared against, so
  factual drift between summary and annotation was minimal.

- **Suggestions and queries are the workhorses (6 of each).**
  Typical cases are edge mappings where human judgement beyond the
  schema is needed: HPO-term candidates for patient phenotypes
  (recurring across Davis, Nelson, Gupta); preservation of
  curator-entered values that don't fit the schema cleanly (Nelson
  `specificity_of_phenotype = SNV`, kept with a `reviewer_query`
  rather than silently corrected).

- **Nelson has 3 suggestions and 0 queries**, the most suggestion-
  heavy paper in the corpus. This reflects the 1992 vintage: the
  paper predates HPO and several of the paper's phenotype
  descriptions map naturally onto HPO terms the curator chose to
  propose rather than invent.

- **Inouye generated 0 AI-uncertainties despite stressing the
  model** (5 GE items, 6 candidate extensions). The AI identified
  every stress-test point as a candidate extension (the model is
  missing a feature) rather than an uncertain mapping (the AI is
  unsure which existing value applies). This is consistent with
  the paper being a polygenic-score study: the gaps are
  structural, not enumerative.

- **Duerr generated 3 AI-uncertainties** concentrated on scoping
  and enumeration decisions:
  - GE-1 knowledge-domain scoping (human-genetics vs. statistical-
    genetics for a GWAS)
  - GE-3 mode-of-inheritance enumeration (`COMPLEX` as a missing
    value for the family-based TDT analysis)
  - GE-6 cited-vs-generated boundary (whether mouse-model work
    cited by the paper belongs in its annotation or warrants a
    separate representational layer)

- **Duerr `ai_assumption` cases (2)** are source-phrase selection
  (which short phrase to use for the source span) and placeholder
  choice for GE-3 (what value to record while flagging the
  enumeration as missing).

- **Inouye `ai_assumption` cases (2)** are measurement-target
  encoding choices (how to record hazard ratio and C-index while
  flagging the epidemiological-measurement gap as a candidate
  extension).

### Methodology note (flag counts)

Flag counts were computed by reading the `flags` section of each
annotation YAML file and counting occurrences by `type`. The
`normalization_note` entries of `type = ai_normalization` (used
during the manual track to record enumeration mappings made during
YAML conversion) are not counted in the totals above, because they
are provenance records rather than flags requiring review. There
are 11 normalization notes across the manual annotations.
