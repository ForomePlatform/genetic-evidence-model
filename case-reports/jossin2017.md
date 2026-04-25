# Case report: Jossin et al. 2017 (Llgl1)

## Publication

Jossin Y, Lee M, Klezovitch O, Kon E, Cossard A, Lien W-H,
Fernandez TE, Cooper JA, Vasioukhin V.
*Llgl1 Connects Cell Polarity with Cell-Cell Adhesion in Embryonic
Neural Stem Cells.*
**Developmental Cell** 41 (5): 481--495.e5, 2017.
DOI: [10.1016/j.devcel.2017.05.002](https://doi.org/10.1016/j.devcel.2017.05.002)

## Role in the corpus

Molecular-mechanism case study from a model-organism paper that
reports phenotypes at multiple biological scales in a single
publication. The paper exercised our schema's ability to represent
phenotypes ranging from the molecular (binding, post-translational
regulation) through cellular and histological to the organismal
(periventricular heterotopia in conditional knockouts), and
motivated the promotion of `phenotype_scale` to the always-required
core dimensions.

- **Annotation source:** Manual (human curator).
- **Evidence items:** 6.
- **Credibility:** Very high.
- **Candidate extensions surfaced:** 3 (CE-J1, CE-J2, CE-J3).
- **Reviewer flags:** 1 suggestion, 3 queries, 0 disagreements.

## Summary of the paper

The authors characterise the role of LLGL1 (a polarity-regulating
WD-repeat protein) in mouse embryonic neural stem cells and demonstrate
that LLGL1 connects apico-basal cell polarity with cell-cell adhesion
through a direct physical interaction with the cell-adhesion
molecule N-cadherin. Conditional inactivation of *Llgl1* in the
embryonic neural epithelium produces periventricular heterotopia
(PH) -- ectopic neural tissue at the ventricular surface -- a
phenotype consistent with disrupted neural stem cell polarity. The
paper layers evidence at multiple scales: organismal (PH in
conditional knockouts), histological (composition and architecture
of ectopic gray matter), cellular (disruption of the apical
junction complex and loss of the ventricular ENSC monolayer),
molecular (LLGL1 directly binds N-cadherin via its WD14 domain),
and regulatory (atypical PKC phosphorylation of LLGL1 inhibits the
LLGL1-N-cadherin interaction). A final dominant-negative rescue
experiment in vivo demonstrates that disruption of the
LLGL1-N-cadherin interaction is sufficient to cause PH.

## Decomposition into GeneticEvidence items

| ID   | Scale of claim                  | Brief description                                                                              |
| ---- | ------------------------------- | ---------------------------------------------------------------------------------------------- |
| GE-1 | Organismal                      | Periventricular heterotopia in *Llgl1* conditional knockout mice.                              |
| GE-2 | Histological                    | Composition of the ectopic gray matter (cell types, layering).                                 |
| GE-3 | Cellular                        | Disruption of the apical junction complex and loss of the ENSC ventricular monolayer.          |
| GE-4 | Molecular -- binding            | LLGL1 directly binds N-cadherin via its WD14 (primarily) and WD10 domains.                     |
| GE-5 | Molecular -- regulation         | aPKC phosphorylation of LLGL1 inhibits the LLGL1-N-cadherin interaction.                       |
| GE-6 | Mechanistic -- in vivo rescue   | A dominant-negative LLGL1 fragment that disrupts the LLGL1-N-cadherin interaction causes PH.   |

The key methodological observation is that all six items concern
the *same gene* and the *same biological process*, but at different
scales. Without `phenotype_scale` as a first-class dimension, the
schema would either collapse the six items into a single
gene-function claim (losing the scale stratification that makes the
mechanism convincing) or fail to distinguish the molecular binding
data from the organismal phenotype.

## Candidate extensions surfaced

The paper exercised three independent gaps in the schema:

**CE-J1: `RESOLUTION = PROTEIN_SUBDOMAIN`.** The paper localises the
LLGL1-N-cadherin interaction to the WD14 (primarily) and WD10
domains of LLGL1, and to the beta-catenin-binding region of
N-cadherin. The current `Resolution` enumeration (`WINDOW`, `GENE`,
`FUNCTIONAL_ELEMENT`, `POSITION`, `VARIANT`) does not capture this.
Candidate value: `PROTEIN_SUBDOMAIN`.

**CE-J2: `target_type` values for relationships.** The in vivo
dominant-negative rescue (GE-6) targets the LLGL1-N-cadherin
*interaction*, not a gene; the paper also documents a tripartite
LLGL1-N-cadherin-beta-catenin complex. Candidate `target_type`
values: `INTERACTION` and `COMPLEX`.

**CE-J3: Gene-relation enumeration gap.** The current `gene_relation`
enumeration (`X_has_same_function_as_Y`, `X_regulates_Y`,
`X_inhibits_Y`) does not cover physical binding or trafficking
regulation, both central to this paper. Candidate values:
`X_physically_binds_Y`, `X_regulates_trafficking_of_Y`. This is the
gap discussed in §6.1 of the ICBO 2026 paper -- ten of eleven
`Gene_Function` items in the corpus involve binding or trafficking,
which the current three-value enumeration cannot represent.

None of the three candidates has yet been promoted under the
two-papers rule.

## Reviewer flags

- **Suggestion (1):** HPO terms candidates for the heterotopia
  phenotype, deferred pending curator decision.
- **Queries (3):** Edge-case mappings flagged for curator review,
  including organism-set ambiguity (one experiment uses rat, not
  mouse) and the cited-vs-generated boundary on therapeutic-rationale
  citations.

## Notes for downstream consumers

The Jossin annotation is the corpus's clearest stress test for
multi-scale phenotype representation. Any downstream consumer that
expects a single `phenotype_scale` value per paper will need to be
adapted to handle the case where one paper produces multiple items
at different scales. The annotation also illustrates how the schema
is designed to support a single physical mechanism described at
several scales: the items share `target` (LLGL1) and `gene_relation`
intent (binding/regulation of N-cadherin), but differ in
`phenotype_scale`, `method`, and the evidential weight of each.
