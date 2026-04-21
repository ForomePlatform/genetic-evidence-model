# Case report: Inouye et al. 2018 (metaGRS for coronary artery disease)

## Publication

Inouye M, Abraham G, Nelson CP, Wood AM, Sweeting MJ, Dudbridge F, et al.
*Genomic risk prediction of coronary artery disease in 480,000 adults:
implications for primary prevention.*
**Journal of the American College of Cardiology** 72 (16): 1883-1893, 2018.
DOI: [10.1016/j.jacc.2018.07.079](https://doi.org/10.1016/j.jacc.2018.07.079)

## Role in the corpus

Model-stress-test case. Every claim in this paper is genuine genetic
evidence, and every claim stretches the schema: the target is a
derived score, the resolution is the whole genome in aggregate, the
measurement targets are epidemiological rather than molecular, and the
underlying object of study is a human construction, not a natural
kind. Annotating this paper surfaces six candidate extensions, more
than the other five papers in the corpus combined.

- **Annotation source:** AI-drafted, pending full curator review.
- **Evidence items:** 5.
- **Credibility:** High (training), High (UKB validation), Medium
  (age-stratified risk trajectories).
- **Candidate extensions surfaced:** 6 (CE-IN1 through CE-IN6).

## Summary of the paper

The authors combined three previously published polygenic scores for
coronary artery disease using linear weighting to produce a
meta-genomic risk score (metaGRS) spanning 1,745,180 SNPs. They
validated the metaGRS externally in 482,629 UK Biobank participants
with a median 8-year follow-up. Headline findings:

- **Hazard ratio per standard deviation** of 1.71 (95% CI 1.68 to
  1.73) for incident coronary artery disease.
- **C-index 0.623** (95% CI 0.615 to 0.631) in UK Biobank, exceeding
  every conventional risk factor measured individually.
- **Substantial independence** from conventional risk factors:
  addition of the metaGRS to a conventional risk model produces a
  net reclassification improvement of 4.4%.
- **Age-stratified risk trajectories:** individuals in the top
  quintile of metaGRS reach the equivalent of a conventional-risk
  individual's CAD incidence 5 years earlier.
- **Predictive power persists under medication:** the metaGRS
  retains its discriminative ability within a subgroup taking statin
  or antihypertensive therapy at the time of UKB enrolment.

## Decomposition into evidence items

| ID | Label | target_type | method | credibility |
| --- | --- | --- | --- | --- |
| GE-1 | Construction and internal metrics of metaGRS | GENE (placeholder) | STATISTICAL_GENETICS | High |
| GE-2 | External validation of metaGRS in UK Biobank | GENE (placeholder) | STATISTICAL_GENETICS | High |
| GE-3 | Independence of metaGRS from conventional risk factors | GENE (placeholder) | STATISTICAL_GENETICS | High |
| GE-4 | Age-stratified risk trajectories by metaGRS quintile | GENE (placeholder) | STATISTICAL_GENETICS | Medium |
| GE-5 | Predictive power persists under current therapies | GENE (placeholder) | STATISTICAL_GENETICS | Medium |

The "GENE (placeholder)" `target_type` value appears throughout
because the schema's current enumeration has no better fit for a
polygenic score. The correct value would be `SCORE`, proposed as
CE-IN1 below. Every evidence item in this annotation exercises at
least CE-IN1, CE-IN2, CE-IN3, and CE-IN6, and most also exercise
CE-IN4. This uniform stretching is why the annotation surfaces so
many candidate extensions.

## GE-2: UK Biobank validation (abridged annotation)

```yaml
id: GE-2
label: "External validation of metaGRS in UK Biobank"
source: ai_drafted
knowledge_domain: [POPULATION_GENETICS]
method: [STATISTICAL_GENETICS]
target_type: GENE              # placeholder; CE-IN1 proposes SCORE
candidate_extension_exercised: [CE-IN1, CE-IN2, CE-IN3, CE-IN4]
target: "metaGRS"
resolution: GENE               # placeholder; CE-IN2 proposes WHOLE_GENOME_AGGREGATE
variant_ascertainment: [FROM_DATABASE]
phenotype_scale: CLINICAL
credibility: HIGH
credibility_comment: >
  Prospective cohort of 482,629 independent of training set.
  <5% non-European ancestry limits generalisability.
assertions:
  - id: GE-2.A1
    statement: "Hazard ratio per standard deviation of metaGRS is 1.71"
    measurement_type: HAZARD_RATIO    # candidate value per CE-IN4
    source_span:
      page: 1
      key_phrase: "HR for CAD was 1.71 (95% CI 1.68 to 1.73) per SD"
  - id: GE-2.A2
    statement: "metaGRS C-index exceeds every conventional risk factor"
    measurement_type: C_INDEX         # candidate value per CE-IN4
    source_span:
      page: 1
      key_phrase: "C-index = 0.623 (95% CI 0.615 to 0.631) for incident CAD"
```

The full annotation including GE-1 and GE-3 through GE-5 is in the
repository at
[`annotations/inouye2018.yaml`](../annotations/inouye2018.yaml).

## Candidate extensions surfaced

### CE-IN1: `SCORE` value for Target Type

The metaGRS is neither gene nor variant nor segment: it is a derived
composite predictor weighted across 1,745,180 variants. Current
enumeration `GENE | RELATED_GENE | VARIANT | SEGMENT | INTERVAL |
TRANSCRIPT` has no matching value. Proposed addition: `SCORE`
(possibly subtyped as `POLYGENIC_SCORE | COMPOSITE_SCORE`).

### CE-IN2: `WHOLE_GENOME_AGGREGATE` value for Resolution

The metaGRS spans the whole genome non-contiguously. Current
Resolution enumeration presupposes a contiguous or pointwise target.
Proposed value: `WHOLE_GENOME_AGGREGATE`, chosen over `GENOME_WIDE`
to avoid collision with genome-wide-significance terminology, and
over `INDIVIDUAL_GENOME` to avoid implying one person's sequence.

### CE-IN3: `target_composition` dimension

Orthogonal to Resolution: does the Target refer to a single entity or
an aggregate of many? The metaGRS target is an aggregate; a variant
or gene is SINGLE. Proposed: new dimension `target_composition` with
values `SINGLE | AGGREGATE | COMPOSITE`. CE-IN2 and CE-IN3 are
complementary framings of the same decision; either fully resolves
the gap.

### CE-IN4: Extended measurement_target for epidemiological quantities

Current measurement_target enumeration (EXISTENCE, EXPRESSION,
STABILITY, BINDING, LOCALIZATION, ACTIVITY, CATALYSIS) is oriented
toward molecular-biology assays. Population-genetics evidence has a
different natural vocabulary. Proposed extension, activated when
Knowledge Domain contains `POPULATION_GENETICS`:
`HAZARD_RATIO | ODDS_RATIO | C_INDEX | AUROC | CUMULATIVE_INCIDENCE
| POSITIVE_PREDICTIVE_VALUE | PRECISION_RECALL_AREA`.

### CE-IN5: Structured cohort descriptor sub-block

Credibility of population-genetics evidence depends heavily on cohort
properties that currently live in free-text `special_considerations`:
sample size, ancestry composition, follow-up duration, ascertainment
bias. Proposed: a structured sub-block with named fields
(`n_total`, `n_cases`, `n_controls`, `mean_followup`, `ancestry_pct`,
`age_range`, `ascertainment_source`). Would be reusable across
Duerr, Davis, and future cohort studies.

### CE-IN6: Natural vs derived-artifact targets

The metaGRS is a human construction, not a natural entity. The
evidence items in this paper are about the score's behaviour (HR,
C-index, risk stratification), not about nature directly. Analogous
to evidence about clinical tools, imaging biomarkers, or ML
classifiers. Current model treats all targets as natural kinds.
Proposed: a boolean `derived_artifact` flag on Target, or a distinct
`target_nature` dimension with values `NATURAL | DERIVED`.

## Reviewer flag summary

- **ai_uncertainties:** 0.
- **ai_assumptions:** 2 (measurement_target left empty on GE-2
  pending CE-IN4 resolution; key phrase extraction for HR per SD).
- **candidate_extensions surfaced:** 6 (CE-IN1 through CE-IN6).
- **Promoted dimensions applied:** 2 (Phenotype Scale, Variant
  Ascertainment; apply cleanly despite the model-stress-test nature
  of the paper).

## Author-reported limitations (carried over from the paper)

- UK Biobank has no lipid or biochemistry measurements at time of
  analysis; direct comparison with Framingham-style risk scores is
  not possible.
- UK Biobank minimum enrolment age of 40 excludes early CAD events
  from the validation analysis.
- UK Biobank participants are healthier than the UK general
  population (volunteer bias).
- <5% non-European ancestry in UK Biobank limits generalisability.
- The medicated-subgroup analysis is susceptible to reverse
  causation (individuals with higher baseline risk may be more likely
  to receive therapy).

## Lessons

- Where the model strains is itself informative. The six candidate
  extensions from this annotation are a direct consequence of the
  paper's evidence shape, not failures of annotation; the schema
  is behaving correctly by requiring the annotator to mark the
  forced fit.
- Polygenic score evidence is a recurrent literature pattern, not an
  edge case. A second PRS paper exercising CE-IN1 through CE-IN4
  would trigger promotion under the two-papers rule. This is a
  priority for the next round of corpus expansion.
- CE-IN2 and CE-IN3 are complementary framings of the same gap
  (aggregate-vs-single target). Promotion of one would resolve the
  strain; promoting both would be redundant. Curator decision
  pending.
- The existing core dimensions Phenotype Scale and Variant
  Ascertainment apply cleanly even under heavy stretching
  elsewhere in the annotation. This is evidence that their earlier
  promotion was justified.
- AI-drafted annotations that surface many candidate extensions are
  not failures: they are signals of genuine model gaps. The flag
  vocabulary (`ai_assumption`, `ai_uncertainty`,
  `candidate_extension_exercised`) is what makes the distinction
  between a misfit and a bug in the annotation recoverable on
  curator review.
