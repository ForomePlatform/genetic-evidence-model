# Case report: Nelson et al. 1992 (CD18)

## Publication

Nelson C, Rabb H, Arnaout MA.
*Genetic cause of leukocyte adhesion molecule deficiency:
Abnormal splicing and a missense mutation in a conserved region of
CD18 impair cell surface expression of beta 2 integrins.*
**Journal of Biological Chemistry** 267 (5): 3351--3357, 1992.
PMID: [1737790](https://pubmed.ncbi.nlm.nih.gov/1737790)

## Role in the corpus

Classical molecular-genetics paper -- pre-HPO, pre-ClinVar, pre-VEP --
that produced clean variant-level functional evidence in a tight
three-item annotation. The paper anchors the corpus at its
historical end and provides a useful test of whether the schema can
represent older publications without modification.

- **Annotation source:** Manual (human curator).
- **Evidence items:** 3.
- **Credibility:** Medium.
- **Candidate extensions surfaced:** 1 (CE-N1, retired to discussion).
- **Reviewer flags:** 3 suggestions, 0 queries, 0 disagreements.

## Summary of the paper

The authors investigate the genetic basis of leukocyte adhesion
molecule deficiency (LAD), a primary immunodeficiency caused by
defective surface expression of the beta-2 integrin family. They
identify three distinct mutations in *CD18* (now *ITGB2*) by cDNA
analysis of patient leukocytes and demonstrate the functional
consequence of each by transfecting cDNA constructs into COS cells
and assaying surface expression. The three variants are: (1) a
12-bp insertion (P247_E248insPSSQ at the protein level) caused by
a single splice-altering substitution at the genomic level; (2)
R586W (c.C1756T); and (3) N351S (c.A1052G). Each is shown by
COS-cell expression to abolish or severely impair surface display
of beta-2 integrins. The paper establishes the molecular cause of
LAD in three families and contributes to the broader understanding
of beta-2 integrin biogenesis.

## Decomposition into GeneticEvidence items

| ID   | Variant         | Brief description                                                                       |
| ---- | --------------- | --------------------------------------------------------------------------------------- |
| GE-1 | 12-bp insertion (rs5030670) | Splice-altering substitution producing a 12-bp insertion at protein level. |
| GE-2 | R586W (c.C1756T) | Missense in a conserved region of the cytoplasmic tail.                                |
| GE-3 | N351S (c.A1052G) | Missense in the I-domain.                                                              |

All three items share method (`EXPERIMENTAL_IN_VITRO` plus
`CLINICAL_EVIDENCE`), `target_type = VARIANT`, and `phenotype_scale
= MOLECULAR`. The schema accommodates them cleanly without
extension. The paper's age (1992) does not stress the model: the
fundamental epistemic shape of variant-level functional evidence
has been stable for decades.

## Candidate extensions surfaced

**CE-N1: Variant description across coordinate levels.** The
annotator's "Special Considerations" note that the 12-bp insertion
allele (GE-1) is described differently at three coordinate levels:
P247_E248insPSSQ at the protein level, c.739-12C>A at the splice
level, and rs5030670 on genomic DNA -- the splice alteration
creates the apparent cDNA insertion. The current schema's
`Resolution = VARIANT` assumes single-level variant description and
does not distinguish genomic / transcript / protein coordinates.
The annotator wrote: "tool to convert description to real SNPs
seemed useful."

**Resolution.** This observation is well covered by HGVS
nomenclature and the GA4GH VRS model (referenced in §2 of the ICBO
paper). Rather than introduce a new schema dimension, the model's
target value for a variant should be a VRS-compatible identifier
rather than an unstructured string. The candidate has therefore
been **retired to a discussion-section observation** rather than
recorded as a candidate extension awaiting promotion. This
illustrates a positive use of the candidate-extension workflow: not
every gap surfaces a schema feature; some surface integration
points with existing standards.

## Reviewer flags

- **Suggestions (3):** All three are HPO term candidates for
  patient phenotypes (recurrent immunodeficiency, leukocytosis,
  delayed wound healing), deferred pending curator decision. This
  paper has the highest suggestion-to-item ratio in the corpus,
  reflecting its 1992 vintage: the paper predates HPO by roughly
  fifteen years, so almost every clinical phenotype it describes
  maps onto HPO terms the curator chose to flag rather than
  silently invent.

There were no factual disagreements on this paper, consistent with
the small set of items and the absence of summary-table-versus-text
ambiguity.

## Notes for downstream consumers

The Nelson annotation is a good baseline for testing schema-only
operations: the items are clean, the methods are uniform, no
candidate extensions remain unresolved. For consumers building
ACMG/AMP-style classifiers, GE-1 is a useful test case for handling
splice-altering single-nucleotide substitutions whose protein-level
consequence is an in-frame insertion -- a real-world
non-trivial-but-well-understood mapping that downstream tools like
SpliceAI plus VRS would now resolve automatically but had to be
worked out by hand in 1992.
