# Case report: Gupta et al. 2015 (ATP6AP2)

## Publication

Gupta HV, Vengoechea J, Sahaya K, Virmani T.
*A splice site mutation in ATP6AP2 causes X-linked intellectual
disability, epilepsy, and parkinsonism.*
**Parkinsonism & Related Disorders** 21 (12): 1473--1475, 2015.
DOI: [10.1016/j.parkreldis.2015.10.001](https://doi.org/10.1016/j.parkreldis.2015.10.001)

## Role in the corpus

Low-credibility edge case and positive finding for the schema. The
paper reports a small pedigree (two affected brothers, one obligate
carrier mother, two unaffected uncles) with a splice-site
intronic variant in *ATP6AP2*. The clinical evidence is suggestive
but limited. The schema accommodates the paper without strain and
**no candidate extensions are surfaced** -- making this the
canonical "the model fits cleanly" case discussed in §6.1 of the
ICBO 2026 paper.

- **Annotation source:** Manual (human curator).
- **Evidence items:** 2.
- **Credibility:** Low.
- **Candidate extensions surfaced:** 0.
- **Reviewer flags:** 1 suggestion, 0 queries, 0 disagreements.

## Summary of the paper

The authors describe a family in which two brothers (ages 20 and
31) present with overlapping but distinct neurological phenotypes:
both have intellectual disability and global developmental delay,
the older brother has childhood-onset generalized epilepsy without
parkinsonism, and the younger brother has adult-onset parkinsonism
without epilepsy. Targeted gene-panel sequencing (an X-linked
mental-retardation panel covering 81 genes) identifies a novel
intronic variant in *ATP6AP2* (c.168+6T>A). The variant is
hemizygous in both affected brothers, heterozygous in the
unaffected mother, and absent in two unaffected maternal uncles, a
pattern consistent with X-linked recessive inheritance. *In silico*
splice-effect prediction suggests disruption of the canonical donor
splice site of intron 2.

## Decomposition into GeneticEvidence items

| ID   | Method               | Brief description                                                              |
| ---- | -------------------- | ------------------------------------------------------------------------------ |
| GE-1 | Clinical evidence    | X-linked recessive *ATP6AP2* c.168+6T>A segregating in two affected brothers.  |
| GE-2 | Bioinformatics inference | *In silico* splice-effect prediction for *ATP6AP2* c.168+6T>A.             |

Both items share `target_type = VARIANT`, `target = ATP6AP2
c.168+6T>A`, and `target_resolution = VARIANT`. They differ in
`method` (clinical evidence versus bioinformatics inference) and
`phenotype_scale` (clinical versus molecular). This separation
illustrates a strength of the dimensional vocabulary: a single
variant generates multiple `GeneticEvidence` items when distinct
methodological lines support it, even when the underlying genomic
event is the same.

## Candidate extensions surfaced

None. All required dimensions are populated; activation conditions
fire correctly; no part of the paper required forced fitting into
an inappropriate enumeration. This is the schema's canonical
"happy path" case.

The §6.1 discussion in the ICBO 2026 paper names this as a
positive finding: a paper reporting a family with an X-linked
splice-site mutation and careful pedigree segregation -- the
canonical evidence shape the model was designed for -- accommodates
without strain. The Gupta annotation grounds that claim concretely.

## Reviewer flags

- **Suggestion (1):** HPO term candidates for the four clinical
  phenotypes explicitly highlighted in the paper (intellectual
  disability `HP:0001249`, seizure `HP:0001250`, parkinsonism
  `HP:0001300`, global developmental delay `HP:0001263`), deferred
  pending curator decision. Like Nelson 1992, the suggestion arises
  from the curator declining to silently invent HPO terms and
  flagging them for explicit acceptance instead.

## Notes for downstream consumers

The Gupta annotation is the corpus's smallest and cleanest. For
consumers building ACMG/AMP-style classifiers, this annotation
illustrates the credibility-handling features of the schema:
`credibility = LOW` with explicit `credibility_comment` capturing
the small-pedigree, no-functional-validation context, plus
`special_considerations` recording pedigree size, phenotype
heterogeneity between siblings, and the targeted (not exome-wide)
detection method. The annotation does not claim more than the paper
supports, which is itself a useful demonstration of how the schema
preserves epistemic humility through structured `credibility` and
`special_considerations` rather than a single PASS/FAIL flag.
