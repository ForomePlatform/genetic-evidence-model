# Model extensions surfaced by the corpus pilot

This file documents the candidate extensions to the Genetic Evidence
Model that were surfaced by the six-paper annotation pilot reported
in the ICBO 2026 paper. It is the detail companion to the grouped
summary table in §6.2 of the paper.

## Promotion rule recap

A candidate extension enters the schema as first-class only when it
is exercised by a second independent paper. A gap seen in a single
paper is recorded in that paper's `candidate_extensions` block and
listed here, but does not change the schema until an additional
annotation confirms it. The aim is to let idiosyncrasies remain
local while growing the schema only in response to convergent
evidence.

Two dimensions have been promoted under this rule so far:
Phenotype Scale (Jossin + Davis + Nelson) and Variant Ascertainment
(Davis + Nelson + Duerr + Inouye). Both now appear in the
always-required vocabulary.

## Candidate extensions, grouped by concern

### Group 1: Finer structural resolution

These candidates propose dimensions or enumeration values that let
the model reason below the gene level: to protein subdomains, to
interactions, to the cross-level variant descriptions that HGVS and
the GA4GH VRS already handle. Much of this group is likely to be
resolved by externally referencing existing vocabularies rather
than by introducing new dimensions.

#### CE-J1: `PROTEIN_SUBDOMAIN` value for Resolution

- **Source paper:** Jossin 2017.
- **Triggering evidence:** the WD14/WD10 domain mapping for the
  LLGL1-N-cadherin interaction.
- **Proposal:** add `PROTEIN_SUBDOMAIN` to the Resolution
  enumeration, ideally grounded in InterPro identifiers.
- **Status:** awaiting a second paper to exercise the same gap.

#### CE-J2: `INTERACTION` and `COMPLEX` values for Target Type

- **Source paper:** Jossin 2017.
- **Triggering evidence:** the in-vivo dominant-negative experiment
  targets the LLGL1-N-cadherin interaction rather than a gene; the
  LLGL1-N-cadherin-beta-catenin tripartite complex motivates
  `COMPLEX`.
- **Proposal:** add `INTERACTION` and `COMPLEX` to the Target Type
  enumeration. Candidate SHACL lines are present in
  `genetic_evidence.shacl.ttl` as commented-out triples.
- **Status:** awaiting a second paper.

#### CE-J3: Additional Gene Relation values

- **Source paper:** Jossin 2017.
- **Triggering evidence:** the existing enumeration
  (`X_has_same_function_as_Y`, `X_regulates_Y`, `X_inhibits_Y`)
  covers functional equivalence, regulation, and inhibition but not
  physical binding or trafficking regulation. The pilot's coverage
  table showed Gene Relation at 1/11, almost entirely because of
  this mismatch.
- **Proposal:** add `X_physically_binds_Y` and
  `X_regulates_trafficking_of_Y` to the enumeration.
- **Status:** awaiting a second paper.

#### CE-N1: Cross-level variant description

- **Source paper:** Nelson 1992.
- **Triggering evidence:** the 12-bp insertion
  (`P247_E248insPSSQ` at protein level;
  `c.739-12C>A` at splice level;
  `rs5030670` at genomic DNA level) is an insertion at the cDNA
  level but a single-nucleotide substitution on gDNA. The splice
  alteration creates the apparent cDNA insertion.
- **Proposal:** rather than introduce a new dimension, reference
  HGVS nomenclature and the GA4GH VRS model as the canonical
  vocabulary for variant description. Target values for variants
  should be VRS-compatible identifiers when possible rather than
  free-text strings.
- **Status:** resolved by reference to external vocabulary; no
  internal dimension promotion needed. Retained here for
  traceability.


### Group 2: Polygenic-score machinery

These candidates are concentrated in the Inouye annotation and
reflect a genuine category shift from variant-level to
aggregate-score-level evidence. Whether they become first-class
dimensions or whether polygenic scores warrant a distinct
`GeneticEvidence` subtype is a question for a second polygenic-score
annotation. All six are currently exercised via placeholder values
in `annotations/inouye2018.yaml`.

#### CE-IN1: `SCORE` value for Target Type

- **Triggering evidence:** the metaGRS is neither gene nor variant
  nor segment but a derived composite predictor spanning 1,745,180
  variants weighted by effect size.
- **Proposal:** add `SCORE` to the Target Type enumeration, possibly
  with subtypes `POLYGENIC_SCORE` and `COMPOSITE_SCORE`.

#### CE-IN2: `WHOLE_GENOME_AGGREGATE` value for Resolution

- **Triggering evidence:** the metaGRS spans the entire genome
  non-contiguously. The existing Resolution enumeration presupposes
  a contiguous or pointwise target.
- **Proposal:** add `WHOLE_GENOME_AGGREGATE`. The name was chosen
  over `GENOME_WIDE` (to avoid collision with
  genome-wide-significance terminology) and over `INDIVIDUAL_GENOME`
  (which would imply one person's sequence).

#### CE-IN3: `target_composition` dimension

- **Triggering evidence:** the question "does the Target refer to a
  single entity or an aggregate of many?" is orthogonal to
  Resolution. The metaGRS is an aggregate; a variant or gene is
  SINGLE.
- **Proposal:** a new `target_composition` dimension with
  enumeration `SINGLE | AGGREGATE | COMPOSITE`. CE-IN2 and CE-IN3
  are complementary framings of the same gap; promotion of either
  resolves the strain.

#### CE-IN4: Epidemiological Measurement Target values

- **Triggering evidence:** the existing Measurement Target
  enumeration (`EXISTENCE`, `EXPRESSION`, `STABILITY`, `BINDING`,
  `LOCALIZATION`, `ACTIVITY`, `CATALYSIS`) is oriented toward
  molecular-biology assays. Population-genetics evidence uses a
  different natural vocabulary.
- **Proposal:** extend the enumeration, activated when Knowledge
  Domain contains `POPULATION_GENETICS`, with
  `HAZARD_RATIO`, `ODDS_RATIO`, `C_INDEX`, `AUROC`,
  `CUMULATIVE_INCIDENCE`, `POSITIVE_PREDICTIVE_VALUE`,
  `PRECISION_RECALL_AREA`.

#### CE-IN5: Structured cohort sub-block

- **Triggering evidence:** the credibility of population-genetics
  evidence depends on cohort properties that currently live as
  unstructured text in `special_considerations`: sample size,
  ancestry composition, follow-up duration, ascertainment bias.
- **Proposal:** a structured `cohort` sub-block with named fields
  `n_total`, `n_cases`, `n_controls`, `mean_followup`,
  `ancestry_pct`, `age_range`, `ascertainment_source`. Reusable
  across Duerr, Davis, and future cohort studies.

#### CE-IN6: `derived_artifact` flag

- **Triggering evidence:** the metaGRS is a human construction, not
  a natural kind. Evidence about its behaviour (HR, C-index, risk
  stratification) is analogous to evidence about clinical tools,
  imaging biomarkers, or ML classifiers. The current schema assumes
  all targets are natural kinds.
- **Proposal:** a boolean `derived_artifact` flag on Target, or a
  distinct `target_nature` dimension with enumeration
  `NATURAL | DERIVED`.


### Group 3: Effect-size direction and curation

The smallest and most heterogeneous group. Each candidate responds
to a specific curator judgement that the current schema does not
have a named place for.

#### CE-DU1: `direction_of_effect` dimension

- **Source paper:** Duerr 2006.
- **Triggering evidence:** Duerr reports a *protective* allele (Gln
  at rs11209026, OR 0.26 in non-Jewish cases, OR 0.45 in Jewish
  cases). The current schema encodes direction implicitly via the
  sign of the odds ratio (OR<1 protective; OR>1 risk-conferring).
  ACMG/AMP evidence codes explicitly separate BP (benign
  supporting) from PM (pathogenic moderate), so direction matters
  downstream.
- **Proposal:** a `direction` dimension with enumeration
  `RISK_CONFERRING | PROTECTIVE | NEUTRAL | UNKNOWN`. Or keep the
  direction implicit via effect-size sign and document the
  convention in the schema.

#### CE-D1: Knowledge-domain priority

- **Source paper:** Davis 2011.
- **Triggering evidence:** the annotator's original compound value
  was "Model Organism (primary) Human Genetics Functional
  (somewhat)", an explicitly ordered compound that the current
  Knowledge Domain dimension does not express.
- **Proposal:** attach an ordinal priority to each
  `knowledge_domain` value, or introduce a scalar
  `primary_knowledge_domain` field analogous to `primary_method`.

#### CE-D2: `curator_critique` sub-block on Assertion

- **Source paper:** Davis 2011.
- **Triggering evidence:** the annotator's callout "Looks
  unrealistic, they have twice as many cases ..." is a
  methodological critique attached to a specific assertion in the
  paper, with no schema slot to record it in.
- **Proposal:** attach a `curator_critique` sub-block to
  `GeneticEvidenceAssertion` with fields `raised_by`, `concern`,
  and `status`.


## Withdrawn candidates

### CE-DU2: Negated-assertion handling

Initially proposed from the Duerr annotation: GE-5 asserts "no
significant association at IL12RB1/IL23A/IL12B", and an initial
review of the AI-drafted annotation proposed a new dimension for
negated-polarity assertions. On curator review the candidate was
retracted. An `EvidenceAssertion` is a predicate, and a predicate
can state the absence of something just as readily as its
presence; the polarity is carried by the statement itself. No
schema change is needed. CE-DU2 is preserved as a positive example
of the two-papers rule blocking a false positive: under a looser
single-paper rule, the schema would have acquired a redundant
polarity field.


## Summary counts

- **Promoted to first-class:** 2 (Phenotype Scale, Variant
  Ascertainment).
- **Candidate, awaiting second-paper confirmation:** 13 (CE-J1,
  CE-J2, CE-J3, CE-IN1 through CE-IN6, CE-DU1, CE-D1, CE-D2; plus
  CE-N1 resolved by external reference).
- **Withdrawn after review:** 1 (CE-DU2).

