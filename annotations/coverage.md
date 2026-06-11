# Dimension coverage and reviewer flags in the six-paper pilot

This file reports per-paper detail for the six annotated papers that
form the corpus pilot of the Genetic Evidence Model. It has two
parts:

1. **Dimension coverage** (sections below): per-dimension population
   counts, with the definition of "applicable" for each dimension
   and the rationale for every zero-populated or under-populated
   cell. The aggregate counts are reported in §5.1 of the ICBO 2026
   paper (`tab:supp-coverage`).

2. **Reviewer-flag counts** (final section): per-paper counts of the
   five flag types recorded during annotation. The ICBO 2026 paper
   gives only the aggregate totals in §5.2 prose; this file is the
   authoritative per-paper breakdown.

## Corpus summary

> **Updated 2026-06-04** for the Duerr 2006 re-annotation (curator
> review): Duerr 6 -> 7 items, corpus 28 -> 29. The always-required
> section below is recomputed; the Duerr-affected conditional cells
> (Mode of Inheritance, Mendelian Segregation, Organism) are updated
> with notes. A full corpus-wide recomputation of the conditional
> "applicable" counts (which predate full integration of the
> AI-drafted papers) is still pending the `compute_coverage.py`
> tooling; see the Methodology note.
>
> **Updated 2026-06-08**: the paper now documents the Inouye **`v1`**
> re-annotation (4 items), produced under the protocol matured on the
> Duerr review, in place of the original `v0` draft (5 items). Corpus
> 29 -> 28; assertions 69 -> 95 (Inouye `v1` is more granular: 37 vs
> 11). The always-required and Variant Ascertainment cells and the
> Inouye flag counts are recomputed below. The conditional rows are
> unchanged: both `v0` and `v1` Inouye are `POPULATION_GENETICS`
> score-target papers that activate no conditional dimension except
> Variant Ascertainment. `v0` Inouye is retained in the repository for
> comparison.

- **6 papers, 28 `GeneticEvidence` items** in total.
- **4 manual annotations** (Jossin, Davis, Nelson, Gupta) treated as
  ground truth.
- **2 AI-drafted annotations** (Duerr, Inouye), both curator-reviewed
  (Duerr 2026-06-04 / `v0`; Inouye 2026-06-06 / `v1`).

| Paper | GE items | Source | Credibility | Role |
| ----- | -------: | ------ | ----------- | ---- |
| Jossin 2017 | 6 | manual | Very high | molecular mechanism |
| Davis 2011  | 6 | manual | High      | breadth exemplar |
| Nelson 1992 | 3 | manual | Medium    | classical molecular genetics |
| Gupta 2015  | 2 | manual | Low       | low-credibility edge case |
| Duerr 2006  | 7 | AI-drafted, reviewed (`v0`) | High | clean GWAS exemplar |
| Inouye 2018 | 4 | AI-drafted, reviewed (`v1`) | High/Medium | model-extension stress test |
| **Total**   | **28** | | | |

> **The two coverage tables below are produced by
> `scripts/compute_coverage.py` from the released YAML annotations.**
> Re-run it after any annotation edit; the SHACL shapes in
> `schema/genetic_evidence.shacl.ttl` enforce the always-required
> dimensions and source spans on the same files (CI: `validate.yml`).

## Always-required dimensions

These six dimensions are required of every item, so "applicable" = all 28
items. Population is 28/28 by construction, with one exception
introduced by Duerr GE-new-1 (see below).

| Dimension              | Populated | Applicable |
| ---------------------- | --------: | ---------: |
| Knowledge Domain       | 27 | 28 |
| Method                 | 28 | 28 |
| Target Type            | 28 | 28 |
| Resolution             | 28 | 28 |
| Credibility            | 28 | 28 |
| Phenotype Scale        | 28 | 28 |

**Knowledge Domain (27/28)** is no longer fully populated. Duerr
GE-new-1 (a cited anti-p40 antibody trial added in the 2026-06-04
review) is drug-response evidence with no fitting genetic
`knowledge_domain`; the dimension is left `not_applicable_or_omitted`
with an `ai_uncertainty`, the scope-gap candidate extension CE-DU3. It is
the only corpus item that does not populate an always-required dimension.

## Conditional dimensions

For this group, "applicable" is item-specific: it depends on whether the
dimension's activation condition holds for each item. Variant
Ascertainment is conditional (required when `target_type = VARIANT`).

| Dimension              | Populated | Applicable | Note |
| ---------------------- | --------: | ---------: | --- |
| Variant Ascertainment  | 14 | 18 | 18 variant-target items; the 4 Inouye `v1` items mark it `not_applicable_or_omitted` (CE-IN1) |
| Mode of Inheritance    |  0 |  1 | Davis GE-1 (case-control burden) is the only `HUMAN_GENETICS`+`GENE` item; marked not-applicable |
| Mendelian Segregation  |  0 |  1 | same single item |
| Penetrance             |  2 |  4 | `HUMAN_GENETICS`+`VARIANT` items |
| Measurement Target     | 10 | 11 | `GENE_FUNCTION` items |
| Gene Relation          |  1 | 11 | enumeration gap (CE-J3): binding/trafficking not in the enum |
| Organism               |  8 |  8 | IN_VIVO or MODEL_ORGANISM items |
| Knockout Type          |  1 |  8 | activation fires on non-knockout in-vivo experiments |

## Commentary on the under-populated cells

### Mode of Inheritance (0/1) and Mendelian Segregation (0/1)

The activation condition (`HUMAN_GENETICS` AND `target_type = GENE`)
is satisfied by exactly **one** item: Davis GE-1, the population-scale
case-control burden test of TTC21B
(`[POPULATION_GENETICS, HUMAN_GENETICS]`, `target_type: GENE`). For a
gene-burden item, mode of inheritance is not the operative claim, so
both dimensions are marked `not_applicable_or_omitted` — addressed, not
populated. Hence 0 populated / 1 applicable. This over-broad activation
(the rule fires more widely than the dimension is meaningful) is the gap
behind candidate extension **CE-DU4**.

Duerr GE-3 (the family-based transmission test) does carry
`mode_of_inheritance: COMPLEX` and `mendelian_segregation: false`, but it
targets a `VARIANT`, so it does not activate the `GENE`-scoped rule and
is not counted here; this is the complementary direction of CE-DU4,
which proposes extending activation to `HUMAN_GENETICS` +
(`GENE` or `VARIANT`) and adding a `COMPLEX` value to the enumeration.

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

### Organism (8/8)

Activation condition: `method` contains `IN_VIVO` (or its legacy
synonym `IN_VIVO_EXPERIMENT`) OR `knowledge_domain` contains
`MODEL_ORGANISM`. All eight applicable items are populated, including
Duerr GE-6, whose `organism` field carries "Mouse (various colitis,
EAE, and arthritis models)" for the cited mouse-model work. (A prior
version of this file counted GE-6 as empty; the annotation does
populate it.) GE-6's method values were renamed to the leaf forms
`IN_VIVO` / `IN_VITRO` in the 2026-06-04 review.

### Knockout Type (1/8)

Activation condition: method contains `IN_VIVO` or `knowledge_domain`
contains `MODEL_ORGANISM` (the same activation as Organism).
Only Jossin GE-3 (the conditional Llgl1 knockout) populates the
dimension. The other seven applicable items are in vivo experiments
that are not knockouts (dominant-negative injections, retinal
electroporation, and so on). The low population is not a schema
shortcoming but an artefact of the activation condition firing on
items where the dimension is not literally meaningful; a future
refinement could narrow the condition to knockout-specific methods.

## Methodology note

The two coverage tables are regenerated by
`scripts/compute_coverage.py`, which reads each annotation `.yaml`,
determines for every item whether each dimension's activation condition
holds ("applicable") and whether it carries a concrete value
("populated"). A value of `not_applicable_or_omitted` (or null/absent)
counts as applicable-but-not-populated. The script is the source of
truth for the paper's `tab:supp-coverage` (SN7); re-run it after any
annotation edit. The SHACL shapes in
`schema/genetic_evidence.shacl.ttl` enforce the always-required
dimensions, the enumerations, and the mandatory `source_span` on the
same files, and the `validate.yml` CI workflow converts each annotation
to RDF (`extraction/yaml_to_rdf.py`) and runs `pyshacl` over it.

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
| Duerr  | AI-drafted (`v0`) |   —   |    —       |    —     |    3    |    2      |
| Inouye | AI-drafted (`v1`) |   —   |    —       |    —     |    3    |    4      |
| **Total** |          | **5** | **6**      | **1**    | **6**   | **6**     |

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

- **Inouye `v1` carries 3 AI-uncertainties and 4 AI-assumptions**
  (4 GE items, 6 candidate extensions). This reverses the `v0` reading
  (which had 0 uncertainties): the 2026-06-06 review explicitly added
  `ai_uncertainty` flags where the score target makes a mapping
  genuinely undecidable rather than merely a missing feature -
  variant ascertainment (F-VA: no ascertainment mode applies to a
  score), method (F-METH: no leaf fits polygenic-score association),
  and measurement target (F-MT: epidemiological outcomes have no
  activated home). The structural gaps remain captured as the six
  candidate extensions; the uncertainties mark where even the
  least-wrong placeholder is contestable.

- **Duerr generated 3 AI-uncertainties** (post-2026-06-04 review;
  the count is unchanged but the content shifted):
  - GE-3 mode-of-inheritance enumeration (`COMPLEX` as a missing
    value for the family-based TDT analysis)
  - GE-6 cited-vs-generated boundary (whether mouse-model work
    cited by the paper belongs in its annotation)
  - GE-new-1 `knowledge_domain` (cited drug-response evidence with
    no fitting genetic domain; the CE-DU3 scope gap)
  The GE-1 human-vs-population scoping uncertainty was resolved in
  the review (POPULATION_GENETICS only) and is no longer a flag.

- **Duerr `ai_assumption` cases (2)** are the GE-2.A1 source-span
  anchor (a paraphrase pending verbatim confirmation) and the GE-3
  placeholder choice (recording `COMPLEX` while flagging the
  enumeration gap).

- **Inouye `v1` `ai_assumption` cases (4)** are the forced target-type
  (F-TT: `VARIANT` for a score), the forced resolution (F-RES:
  `VARIANT` for a whole-genome aggregate), the holistic credibility
  tier (F-CRED: curator to confirm), and the decomposition into four
  label-coherent items (F-DECOMP).

### Methodology note (flag counts)

Flag counts were computed by reading the `flags` section of each
annotation YAML file and counting occurrences by `type`. The
`normalization_note` entries of `type = ai_normalization` (used
during the manual track to record enumeration mappings made during
YAML conversion) are not counted in the totals above, because they
are provenance records rather than flags requiring review. There
are 11 normalization notes across the manual annotations.
