# Case report: Duerr et al. 2006 (IL23R)

## Publication

Duerr RH, Taylor KD, Brant SR, Rioux JD, Silverberg MS, Daly MJ, et al.
*A genome-wide association study identifies IL23R as an inflammatory
bowel disease gene.*
**Science** 314 (5804): 1461-1463, 2006.
DOI: [10.1126/science.1135245](https://doi.org/10.1126/science.1135245)

## Role in the corpus

Clean-exemplar case for a classical GWAS. The paper has an evidence
shape our schema was designed to accommodate: a variant-level
population-genetic claim with explicit cohort descriptors, multiple-testing
correction, external replication, and supporting mouse-model citation.

- **Annotation source:** AI-drafted, pending full curator review.
- **Evidence items:** 6.
- **Credibility:** High.
- **Candidate extensions surfaced:** 1 (CE-DU1, direction of effect).

## Summary of the paper

The authors typed 308,332 autosomal SNPs in 547 non-Jewish
European-ancestry cases with ileal Crohn's disease and 548 matched
controls, using the Illumina HumanHap300 BeadChip. A coding variant
(rs11209026; p.Arg381Gln) in IL23R, the gene encoding a subunit of
the receptor for the pro-inflammatory cytokine IL-23, reached
genome-wide significance after Bonferroni correction. The minor (Gln)
allele was protective: odds ratio 0.26 (95% CI 0.15 to 0.43), with a
minor-allele frequency of 1.9% in cases versus 7.0% in controls. The
association was replicated in a Jewish-ancestry case-control cohort
and via family-based transmission disequilibrium testing in 883
nuclear families. A conditional analysis at the IL23R locus showed
that rs11209026 and additional non-coding variants carry independent
signals. Negative results at three related IL-23 pathway genes
(IL12RB1, IL23A, IL12B) were reported in the same analysis. The
discussion connected the finding to prior murine IL-23 pathway
knockout evidence suggesting a therapeutic rationale.

## Decomposition into evidence items

| ID | Label | target_type | method | credibility |
| --- | --- | --- | --- | --- |
| GE-1 | GWAS discovery of rs11209026 in IL23R | VARIANT | STATISTICAL_GENETICS | High |
| GE-2 | Case-control replication in Jewish ileal CD cohort | VARIANT | STATISTICAL_GENETICS | High |
| GE-3 | Family-based transmission disequilibrium (FBAT) | VARIANT | STATISTICAL_GENETICS | High |
| GE-4 | Conditional analysis: independent IL23R signals | INTERVAL | STATISTICAL_GENETICS | Medium |
| GE-5 | Negative association at IL12RB1/IL23A/IL12B | GENE | STATISTICAL_GENETICS | Medium |
| GE-6 | Cited mouse-model and functional support (external) | GENE | IN_VIVO_EXPERIMENT | Low |

## GE-1: GWAS discovery (abridged annotation)

```yaml
id: GE-1
label: "GWAS discovery: rs11209026 (Arg381Gln) in IL23R"
source: ai_drafted
knowledge_domain: [POPULATION_GENETICS]
method: [STATISTICAL_GENETICS]
target_type: VARIANT
target: "rs11209026 (c.1142G>A, p.Arg381Gln) in IL23R"
resolution: VARIANT
variant_ascertainment: [OBSERVED_IN_CASES, OBSERVED_IN_CONTROLS]
phenotype_scale: CLINICAL
subdomain: "GWAS"
credibility: HIGH
credibility_comment: >
  Genome-wide significance after Bonferroni correction
  (corrected P = 1.56e-3). Effect size large (OR = 0.26). CI wide
  (0.15 to 0.43) because the allele is uncommon in cases (MAF 1.9%).
  Independent replication follows in GE-2.
special_considerations:
  - key: "cohort_size_post_QC"
    value: "547 cases, 548 controls"
  - key: "platform"
    value: "Illumina HumanHap300 BeadChip (308,332 autosomal SNPs)"
  - key: "multiple_testing"
    value: "Bonferroni correction across 308,332 tested SNPs"
  - key: "ancestry_restriction"
    value: "European, non-Jewish; minimises population stratification"
candidate_extension_exercised: CE-DU1   # direction of effect
assertions:
  - id: GE-1.A1
    statement: "rs11209026 (Arg381Gln) is genome-wide significantly associated with ileal Crohn's disease"
    source_span:
      page: 1
      key_phrase: "rs11209026 (P = 5.05e-9, corrected P = 1.56e-3)"
  - id: GE-1.A2
    statement: "The Gln allele is protective (OR = 0.26, 95% CI 0.15 to 0.43)"
    source_span:
      page: 2
      key_phrase: "glutamine allele appears to protect against development of CD"
    note: >
      Candidate extension CE-DU1 (direction of effect) exercised here,
      numerically encoded via OR<1.
  - id: GE-1.A3
    statement: "The Gln allele has MAF 1.9% in ileal CD cases vs 7.0% in controls"
    source_span:
      page: 2
      key_phrase: "allelic frequency of 1.9% in non-Jewish ileal CD patients"
```

The full annotation including GE-2 through GE-6 is in the
repository at
[`annotations/duerr2006.yaml`](../annotations/duerr2006.yaml).

## Candidate extension CE-DU1: direction of effect

Duerr reports a **protective** allele (OR 0.26), not a risk allele.
Current schema encodes the direction implicitly in the odds-ratio
value (OR<1 protective; OR>1 risk-conferring). ACMG/AMP evidence
codes separate BP (benign supporting) from PM (pathogenic moderate)
evidence, so the direction does matter downstream. Two plausible
fixes:

1. A dedicated `direction` dimension with enumeration
   `RISK_CONFERRING | PROTECTIVE | NEUTRAL | UNKNOWN`.
2. Keep the direction implicit via the sign of the effect size, and
   document the convention in the schema.

Marked as CE-DU1, awaiting a second paper that would exercise the
same gap before promotion under the two-papers rule.

## Initially proposed, then retracted: CE-DU2

During AI drafting, GE-5 (which asserts *no significant association*
at IL12RB1, IL23A, and IL12B) initially prompted a candidate
extension CE-DU2 for handling negated assertions. On curator review
this was retracted. An `EvidenceAssertion` is a predicate, and a
predicate can state the absence of something just as readily as its
presence; the polarity is carried by the statement itself. No new
dimension is required. CE-DU2 is preserved here as a concrete example
of the review process catching a premature candidate extension.

## Reviewer flag summary

- **ai_uncertainties:** 1 (ambiguity between Population Genetics and
  Human Genetics scoping for a coding variant; reviewer confirmation
  requested).
- **ai_assumptions:** 2 (Mendelian mode-of-inheritance omission for
  complex disease; subdomain labelling as GWAS).
- **candidate_extensions surfaced:** 1 (CE-DU1, pending second-paper
  confirmation).
- **Promoted dimensions applied:** 2 (Phenotype Scale, Variant
  Ascertainment; both apply cleanly).

## Lessons

- The schema accommodates a classical GWAS with minimal friction,
  which is a necessary condition for the model: if this paper had
  stressed the schema, the schema would be too narrow to be useful.
- Variant Ascertainment applies naturally even for a simple
  case-control design (variants are ascertained in both groups by
  construction). This reinforces the decision to make it a core
  dimension.
- Negated assertions ("no significant association") do not require
  schema extension. The lesson for AI-drafted annotations is that
  candidate extensions proposed by the drafter must be reviewed
  against the schema's existing expressive power before promotion;
  the CE-DU2 retraction is an instance of the process working.
- The conditional-activation rule for `mode_of_inheritance`
  (activates for HUMAN_GENETICS + GENE) does not fire here because
  the knowledge domain is Population Genetics and the target type is
  Variant. The AI-drafted annotation correctly recognised this.
