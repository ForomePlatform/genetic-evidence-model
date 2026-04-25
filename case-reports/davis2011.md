# Case report: Davis et al. 2011 (TTC21B)

## Publication

Davis EE, Zhang Q, Liu Q, Diplas BH, Davey LM, Hartley J,
Stoetzel C, Szymanska K, Ramaswami G, Logan CV, Muzny DM, Young AC,
Wheeler DA, Cruz P, Morgan M, Lewis LR, Cherukuri P, Maskeri B,
Hansen NF, Mullikin JC, Blakesley RW, Bouffard GG, Gyapay G,
Rieger S, Tönshoff B, Kern I, Soliman NA, Neuhaus TJ, Swoboda KJ,
Kayserili H, Gallagher TE, Lewis RA, Bergmann C, Otto EA, Saunier S,
Scambler PJ, Beales PL, Gleeson JG, Maher ER, Attié-Bitach T,
Dollfus H, Johnson CA, Green ED, Gibbs RA, Hildebrandt F,
Pierce EA, Katsanis N.
*TTC21B contributes both causal and modifying alleles across the
ciliopathy spectrum.*
**Nature Genetics** 43 (3): 189--196, 2011.
DOI: [10.1038/ng.756](https://doi.org/10.1038/ng.756)

## Role in the corpus

Breadth exemplar. The paper combines case-control resequencing,
zebrafish in vivo complementation of forty individual missense
variants, in vitro rescue, and pedigree segregation across six
families to argue that *TTC21B* contributes both causal and
modifying alleles across the ciliopathy spectrum. The diversity of
methods and target populations in a single paper exercised the
`variant_ascertainment` dimension across multiple modes (patient-observed,
functionally-tested, database-derived) and motivated its promotion
to the always-required core dimensions.

- **Annotation source:** Manual (human curator).
- **Evidence items:** 6.
- **Credibility:** High.
- **Candidate extensions surfaced:** 2 (CE-D1, CE-D2).
- **Reviewer flags:** 1 suggestion, 0 queries, 1 disagreement.

## Summary of the paper

The authors resequence *TTC21B* in 753 unrelated nephronophthisis
(NPHP) and ciliopathy patients and 1,048 controls and identify a
significant excess of rare nonsynonymous variants in cases. To
distinguish causal from neutral missense variants, they perform
zebrafish in vivo complementation on forty individual missense
alleles, scoring rescue of a *ttc21b* morphant phenotype. Sixteen
variants fail to rescue and are classified as functionally
deleterious. The paper presents pedigree segregation evidence in
six independent families and a founder haplotype analysis of the
recurrent p.Pro209Leu allele. A subset of variants are tested in
mIMCD3 cells for cilia-length defects, and a single rat retinal
in vivo electroporation experiment functionally interrogates a
specific mutant allele.

## Decomposition into GeneticEvidence items

| ID   | Method                          | Brief description                                                                          |
| ---- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| GE-1 | Statistical genetics + Clinical | Case-control resequencing showing pathogenic-allele enrichment in *TTC21B*.                |
| GE-2 | Experimental, in vivo (zebrafish) | Zebrafish in vivo complementation of 40 *TTC21B* missense variants.                      |
| GE-3 | Experimental, in vitro          | mIMCD3 in vitro rescue of cilia-length defects.                                            |
| GE-4 | Experimental, in vivo (rat)     | Rat retinal in vivo electroporation of a mutant *TTC21B* allele.                           |
| GE-5 | Clinical evidence               | Pedigree segregation across six families with biallelic *TTC21B* variants.                 |
| GE-6 | Statistical genetics            | Founder-haplotype analysis of the recurrent p.Pro209Leu allele.                            |

The key methodological observation is that variants in this paper
enter the analysis via at least three distinct ascertainment modes:
patient-observed (GE-1, GE-5), functionally-tested by construction
(GE-2, GE-3, GE-4), and database-derived for population comparisons.
Without `variant_ascertainment` as a first-class dimension, the
schema cannot distinguish "this variant is in the analysis because
it was found in a patient" from "this variant is in the analysis
because we engineered it to test the assay" -- a distinction that
matters for downstream pathogenicity reasoning.

## Candidate extensions surfaced

**CE-D1: Ordered `knowledge_domain` values.** The annotator's
summary used a compound value with explicit priority -- "Model
Organism (primary), Human Genetics, Functional (somewhat)" --
declaring an ordering, not just a set. The current schema represents
`knowledge_domain` as an unordered multi-valued field. Candidate:
add an optional `priority_rank` per value, or a scalar
`primary_knowledge_domain` field analogous to `primary_method`.

**CE-D2: Curator-critique sub-block on `EvidenceAssertion`.** The
sole curator callout on this paper is a methodological critique of
an assertion (concerning the statistical interpretation of the
case-control enrichment), not a slot-label. The current model has
no structured way to attach a curator's concern to a specific
publication-level assertion. Candidate: a `curator_critique`
sub-block on `GeneticEvidenceAssertion` with `raised_by` / `concern`
/ `status` fields.

Neither candidate has yet been promoted under the two-papers rule.

## Reviewer flags

- **Disagreement (1):** The curator's summary listed the organism
  set as `{mouse, zebrafish}`, but the paper also reports a rat
  retinal electroporation experiment (GE-4). The annotation extends
  the organism set with `rat` per `reviewer_disagreement` on GE-4.
  This is the only disagreement across the four manually annotated
  papers in the corpus, and it illustrates a benign failure mode of
  human curation: a summary table can omit experimental details
  that the full annotation must capture.
- **Suggestion (1):** HPO term candidates for ciliopathy clinical
  presentations, deferred pending curator decision.

## Notes for downstream consumers

The Davis annotation is the corpus's most diverse single paper in
terms of methods and target populations. Any consumer that expects
each `GeneticEvidence` item to have a single dominant `method` will
need to handle GE-1, where statistical-genetics and clinical-evidence
methods are intertwined. The annotation also illustrates the value
of preserving the curator's editorial judgement (CE-D1's priority
ordering) as a structured signal rather than discarding it as
prose.
