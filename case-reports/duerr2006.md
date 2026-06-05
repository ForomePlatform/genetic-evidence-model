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

- **Annotation source:** AI-drafted; curator-reviewed 2026-06-04 (see
  [`annotations/reviews/duerr2006-review-2026-06-04.yaml`](../annotations/reviews/duerr2006-review-2026-06-04.yaml)).
- **Evidence items:** 7 (6 original + GE-new-1, added in review).
- **Credibility:** High.
- **Candidate extensions surfaced:** 3 (CE-DU1 direction of effect; CE-DU3
  cross-item/translational synthesis; CE-DU4 conditional-activation gap).
  CE-DU2 was proposed then retracted.

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

Method values are leaf-level per the hierarchy (migrated in the
2026-06-04 review; ROADMAP §1.b). Credibility reflects the annotation YAML.

| ID | Label | target_type | method | credibility |
| --- | --- | --- | --- | --- |
| GE-1 | rs11209026 protective in non-Jewish ileal CD (discovery) | VARIANT | GWAS | High |
| GE-2 | rs11209026 protective in Jewish ileal CD (replication) | VARIANT | ASSOCIATION_STUDY | High |
| GE-3 | Family-based transmission disequilibrium (FBAT) | VARIANT | TRANSMISSION_DISEQUILIBRIUM_TEST | High |
| GE-4 | Multiple independent IL23R signals (conditional) | VARIANT | FINE_MAPPING | High |
| GE-5 | Negative association at IL12RB1/IL23A/IL12B | GENE | GWAS | High |
| GE-6 | Cited mouse-model and functional support (external) | GENE | IN_VIVO, IN_VITRO | High |
| GE-new-1 | Cited anti-p40 (IL12B) antibody trial (external, clinical) | GENE | CLINICAL_EVIDENCE | High |

## GE-1: GWAS discovery (abridged annotation)

```yaml
id: GE-1
label: "rs11209026 (Arg381Gln) in IL23R confers protection against ileal CD in non-Jewish discovery cohort"
source: ai_drafted
knowledge_domain: [POPULATION_GENETICS]
method: [GWAS]
target_type: VARIANT
target: "rs11209026 (c.1142G>A, p.Arg381Gln) in IL23R"
resolution: VARIANT
variant_ascertainment: [OBSERVED_IN_CASES, OBSERVED_IN_CONTROLS]
phenotype_scale: CLINICAL
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
      key_phrase: "allelic frequency of 1.9% in the non-Jewish patients with ileal CD and 7.0% in non-Jewish controls"
```

The full annotation including GE-2 through GE-6 is in the
repository at
[`annotations/v0/duerr2006.yaml`](../annotations/v0/duerr2006.yaml).

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

## Candidate extension CE-DU3: cross-item / translational synthesis

The paper's central recommendation — *"blockade of the IL-23 signaling
pathway would be a rational therapeutic strategy for IBD"* (p.3) — is a
higher-order claim that references several GE items jointly. The original
annotation captured it in an invented `meta_assertions` top-level key
(MA-1); on review this was retired (inventing top-level structure is
disallowed) and the gap logged as CE-DU3. Two framings: add a construct
for higher-order claims referencing multiple `GeneticEvidence` items, or
treat translational/therapeutic recommendations as out of GEM scope.
CE-DU3 now has **two independent instances** in this paper — the
therapeutic-strategy statement (former MA-1) and GE-new-1 (the cited
anti-p40 antibody trial) — which under the two-papers rule is the kind of
recurrence that motivates promotion.

## Candidate extension CE-DU4: conditional-activation gap

GE-3 is a family-based transmission test on a specific variant
(HUMAN_GENETICS + VARIANT) for which `mode_of_inheritance` is genuinely
relevant, but the conditional set `{mode_of_inheritance,
mendelian_segregation, exact_variant, subdomain}` activates only for
HUMAN_GENETICS + GENE. Proposed fix: extend activation to
HUMAN_GENETICS + (GENE or VARIANT). Two sub-gaps: `mode_of_inheritance`
has no COMPLEX/non-Mendelian value (GE-3 used COMPLEX as a placeholder),
and `subdomain` has no family-based value (the previously-forced `GWAS`
value was simply wrong on a transmission test).

## GE-new-1: cited anti-p40 antibody trial

Added during the review's Phase-1 missing-evidence check. The Discussion
cites an anti-p40 (IL12B) monoclonal antibody trial in Crohn's disease
(ref 25) as therapeutic support. It is a `cited_evidence` item, distinct
from GE-6 (cited *mouse* work) in method, target, and credibility. It
records a genuine tension: the antibody targets the p40 subunit (IL12B) —
the same gene GE-5 found genetically *unassociated* — yet pharmacological
blockade works. Its `knowledge_domain` is intentionally left unresolved
(drug-response evidence with no fitting genetic domain), which is the
second CE-DU3 instance.

## Reviewer flag summary

Counts reflect the post-review (2026-06-04) state. In AI-drafted output
these are annotator-emitted flags.

- **ai_uncertainties:** 3 (GE-3 `mode_of_inheritance` = COMPLEX
  enumeration question; GE-6 cited-vs-generated boundary; GE-new-1 no
  fitting `knowledge_domain`). The GE-1 Population/Human Genetics scoping
  uncertainty was resolved in review (POPULATION_GENETICS only).
- **ai_assumptions:** 2 (GE-2.A1 paraphrase anchor pending verbatim
  confirmation; GE-3 `mode_of_inheritance` COMPLEX placeholder). The
  GE-1 mode-of-inheritance flag was demoted to a rule outcome.
- **candidate_extensions surfaced:** 3 (CE-DU1, CE-DU3, CE-DU4;
  CE-DU2 retracted).
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
  (activates for HUMAN_GENETICS + GENE) does not fire for GE-1 because
  the knowledge domain is Population Genetics and the target type is
  Variant. The AI-drafted annotation correctly recognised this.
- GE-3, by contrast, is HUMAN_GENETICS + VARIANT where
  `mode_of_inheritance` *is* relevant, yet the same rule does not
  activate. The review kept the dimension and logged the gap as CE-DU4
  (extend activation to HUMAN_GENETICS + (GENE or VARIANT)), an example
  of a conditional-activation condition that is too narrow.
