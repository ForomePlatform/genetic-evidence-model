# GEM → UMLS adjudication decision log

Narrative record of the mapping decisions in `adjudications.yaml`: the
evidence weighed, the alternatives rejected, and the argument for each
verdict — at a level of detail the paper and supplements deliberately omit.
The YAML `note` fields hold the compressed verdicts; this log holds the
discussion. Newest entries first. The relation vocabulary and the A–D
adequacy criteria are defined in the supplement (note SN8, the generated
UMLS crosswalk) and in `notes → adjudications.yaml` protocol records.

Recurring principles that emerged from these discussions:

- **Composite tokens.** Several GEM tokens are intersective compounds or
  relational applications (`statistical_genetics` = statistics × genetics,
  `related_gene` = related(genes), `interval` = (coordinate, coordinate) ×
  genomic axis). UMLS pre-coordinates specific instances but lacks a
  post-coordination mechanism, so these map to the nearest single concept
  with an explanatory note (see the Discussion section of the paper).
- **Operator as anchor.** When the relation/operator is the semantic core of
  a composite token, the operator concept anchors the mapping with relation
  `related` (RELATED_GENE, INTERVAL).
- **Sense merging.** A single CUI can merge distinct source senses (MeSH
  population phenomenon vs NCI entity for C0042333); the operative domain
  sense can justify acceptance at `close` even when the CUI-level semantic
  type follows the other sense.
- **Out-of-axis STYs are acceptable when deliberate.** The axis (semantic
  type) is a search scope, not a validity constraint; accepted concepts
  whose STY falls outside the axis are marked as deliberate in the note.

## 2026-08-31 — joint adjudication round (target_type, resolution, method)

### method/STATISTICAL_GENETICS → C2717898 Biostatistics, `narrower`

The token is the intersective compound statistics × genetics
(C0038215 × C0017398); no single UMLS concept carries it. Biometry was
considered and set aside as too different in scope. Biostatistics is the
nearest discipline concept; GEM is more specific (narrower). The
composition is recorded in the note; the general phenomenon (UMLS lacking
a post-coordination mechanism) is discussed in the paper.

### method/BIOINFORMATICS_INFERENCE → C0376528 Computational Biology, `broader`

Sequence Analysis was rejected — the token is closer to machine learning
and software tooling than to sequence algorithms. Computational Biology is
the covering discipline (GEM more general within it: bioinformatics ×
inference, today typically ML C0376284, inference C0679201).

### target_type/RELATED_GENE → C0332281 "Associated with", `related`

Exhaustive four-pass search (exact phrases, words within T028, descent from
Genes C0017337, relation qualifiers) showed UMLS pre-coordinates specific
relatedness kinds — Genes, Modifier C3178895; Homologous Gene C1334043;
Linked gene C0314613; gene interaction C0596610 — but has no generic
"related gene". The token is the composite related(genes) =
C0332281 × C0017337, and the relation is the semantic core, so the bare
operator concept ("Joined in some kind of relationship") anchors the
mapping. STY (Qualitative Concept) outside the T028 axis, deliberate.

### target_type/VARIANT → C0042333 Genetic Variation, `close`

Initially rejected on the MeSH definition ("genotypic differences observed
among individuals in a population" — an aggregate phenomenon, which also
drives the CUI's semantic type, T070 Natural Phenomenon or Process).
Re-examined on the curator's challenge: NCI defines the entity sense
("deviation(s) in the nucleotide sequence of the genetic material of an
individual") and hangs the ACMG classification ladder directly under it
(Pathogenic Variant C3816499, Variant Benign C5239128, Likely Pathogenic
Variant C4264624), and UMLS files "Sequence Variant" / "Sequence
Variation" — the exact SO term — as synonyms of this CUI. No entity-typed
generic variant exists elsewhere (T086 Nucleotide Sequence holds the
classified children only; bare "variant" is a SNOMED qualifier C0205419).
The sense merge is why the relation is `close` rather than `exact`; the
controversy is written up in the s15 supplement note.

### target_type/SEGMENT → C0678933 Genetic Loci, `close`

Token = a defined genomic segment, the material stretch (vs INTERVAL, the
coordinate-specified span). Genetic Loci (T028, in-axis) carries the
identified-position-on-the-genome sense; close, not exact, because it
carries neither contiguity nor arbitrary extent. Near-miss recorded:
C2333586 "DNA molecule region" (FMA:84119, sole source, no definition;
children include Exon, Intron, and Linker DNA) is material parthood of a
DNA *molecule* — exon/intron scale, including explicitly non-functional
stretches — not a segment defined on the genome (fails D; STY T167
Substance). C1517520 "Genomic Segment" is a false friend: an NCI BAC/YAC
library-clone concept (isa UML Entity).

### target_type/INTERVAL → C1707511 Coordinate, `related`

The schema defines the token as "a coordinate interval (bp or cM)" — the
coordinate system is the semantic core, so the composite is
(Coordinate, Coordinate) × genomic axis and the operator-as-anchor
precedent applies. NCI Coordinate ("a number or other designation that
identifies a position relative to an axis or grid") has both generic
children (X/Y/Z, GPS coordinates) and NCI's genomic-position fields (End
Coordinate, From/To Position Dimension). `related`, not `broader`: an
interval is *constituted by* a pair of coordinates, not a kind of them and
not more general. Nothing closer exists — "Interval" is a Temporal Concept
(C1272706) or an HL7 datatype (C1552654); UMLS has no genomic
interval/region concept. Division of labor with SEGMENT recorded above.

### target_type/TRANSCRIPT → C1519595 RNA Transcript, `broader`

The molecule class for the identified transcript under study. NCI
"Transcript Variant" rejected (dysfunction-flavored STY, variant-of-
transcript sense). SO transcript (SO:0000673) remains the exact external
anchor in s15.

### resolution/FUNCTIONAL_ELEMENT → C1517495 Gene Feature, `close`

The schema line is inclusive ("Regulatory or functional element") and Gene
Feature (NCI C13445; T028, in-axis) is precisely the inclusive parent: its
NCI children include both Coding Region and Regulatory Element — the two
narrower readings that had kept this token open — plus Exon, Intron, UTR,
TATA Box, CpG Island, Poly-A Addition Site. Accepting it dissolves the
coding-vs-regulatory definitional question; the schema line stands as
written. Close, not exact, for two mismatches that cut in opposite
directions: the concept is gene-anchored ("elements that comprise a gene
or transcription unit"), so gene-free intergenic elements sit awkwardly,
while its membership is structural (introns, immunoglobulin switch
regions) rather than strictly functional. Rejected: C0314642 Regulatory
Element and Coding Region (each a child, each too narrow for the inclusive
token); C2333586 (see SEGMENT).

### resolution/WINDOW → C0678933 Genetic Loci, `close`

Token = "coarse genomic window" — and *locus* is the idiom of coarse
resolution (linkage peak, GWAS locus; QTL C0597336 existing as its own
T028 concept corroborates that loci-language is how UMLS renders coarse
mapped regions). Same anchor as target_type/SEGMENT: cross-dimension
reuse, precedented by Coordinate (POSITION + INTERVAL) and Linkage Study
(method + subdomain). Reusing INTERVAL's Coordinate was barred by
criterion C: Coordinate is already resolution/POSITION's `exact` anchor,
and two levels of one ordered scale must not share a concept. Rejected:
Chromosome band C1521913 (one banding scheme), chromosomal region
C1953345 (GO/FMA cell-component material sense), "genomic window"
(absent). With this, the resolution scale anchors read as a coherent
family: Genetic Loci → Gene Locus → Gene Feature → Coordinate → Genetic
Variation, distinct at every level.

### resolution/VARIANT → C0042333 Genetic Variation, `close`

Same anchor and argument as target_type/VARIANT (see above); cross-
dimension reuse keeps criterion C intact within the resolution scale.

### phenotype_scale/HISTOLOGICAL → C0040300 Tissue, `related`

Sibling-pattern decision: the phenotype scale anchors each level of
phenotypic organization to the entity kind at that scale, with relation
`related` (level vs entity class) — Molecule (MOLECULAR), Cells
(CELLULAR), Organism (ORGANISMAL). Tissue completes the run: T024, with
MeSH, NCI, SNOMED and FMA atoms all concurring on the denotation.
Replaces a review-flagged earlier accept.

### phenotype_scale/CLINICAL → C0037088 Clinical finding, `related`

The bearer pattern of the sibling levels (Molecule, Cells, Tissue,
Organism) breaks here — the bearer of a clinical phenotype is the
organism again — so the clinical level anchors on its *observable kind*
instead: C0037088, whose SNOMED atom 'Clinical finding' roots the entire
finding/disorder hierarchy (NCI 'Finding' broadly: clinical, laboratory
or molecular evidence of disease; the MeSH 'Signs and Symptoms' atom is
the narrowest of the nested senses). The curator's candidate C3889687
'Clinical Observation' was examined via its relations, which proved
uniformly procedural (active surveillance, watchful waiting, observation
regimes; isa diagnostic procedure) — the healthcare *act* that produces
findings, i.e. method territory, whose adoption would fold observation
method into phenotypic scale. Also rejected: Phenotype C0031437 (the
dimension itself), Patients C0030705 (bearer reading erases the
ORGANISMAL/CLINICAL distinction), Observation (finding) C5890437
(LOINC-only). Closes phenotype_scale.

### variant_ascertainment axis → T062 Research Activity

The hardest axis decision, because the dimension's accepted anchors split
across the Semantic Network's *root* division: OBSERVED_IN_CASES/_CONTROLS
sit on the Event side (Case-Control Studies, T062, B1.3.2) while
FROM_DATABASE and SYNTHETIC sit on the Entity side (Published Database,
T170; synthetic construct, T114). A Entity and B Event meet only at the
root, so no semantic type can cover both halves — and UMLS holds no
ascertainment concept at all (only "Not Ascertained" and dementia-screening
instruments): the missing *category* is the structural twin of the
credibility finding. The axis follows the dimension's intension, not the
anchors' accidents: the schema defines the dimension as the "ascertainment
route by which each variant entered the study" — an event/method-side
notion in study-design vocabulary — and future tokens (population
screening, incidental finding, biobank recall) would all live under
B1.3.2, whereas the two Entity-side anchors are settled metonymic
route-markers (route recorded via its source or product artifact),
deliberately out-of-axis. Rejected: T052 Activity (B1, baggy), T058
Health Care Activity (care, not research), T059 Laboratory Procedure
(covers only SYNTHETIC's lab half), T170 Intellectual Product (artifacts,
not routes).

### subdomain/WGS-WES Study → C3640076 Whole Genome Sequencing, `broader`

The harness's exact-name match had recorded the concept at face value; the
curator corrected the relation: the token covers whole-genome AND
whole-exome sequencing studies, while C3640076 denotes only the WGS half
(UMLS pre-coordinates Whole Exome Sequencing separately; no concept covers
the WGS+WES family) — GEM more general, hence `broader`. The attempt to
record this via the "accept as" dropdown also exposed a Studio bug: on a
harness-mapped entry with no curator decision yet, changing the dropdown
silently did nothing (it only re-recorded *existing* acceptances). Fixed:
the dropdown now records acceptance of the harness mapping at the chosen
relation.

### measurement_target EXPRESSION / BINDING / ACTIVITY; gene_relation/X_inhibits_Y

Batch confirmation of harness mappings, with curated relations. EXPRESSION
→ Gene Expression C0017262 `exact`. BINDING → Protein Binding C0033618
`exact` on the product-binding reading (note records the downgrade path to
`close` should the token later cover nucleic-acid binding). ACTIVITY → GO
molecular_function C1148560 recorded `narrower`, not exact: GO's class
covers all product activities *including binding*, which the scale carries
as its own token — the binding-excluded GEM sense is more specific, and
within-scale anchors stay distinct (criterion C). X_inhibits_Y → GO
negative regulation of gene expression C2611924 `related`: a relational
token, inhibits(X, Y), anchored per the operator-as-anchor pattern, with
the caveat that inhibition need not run via expression regulation.
knockout_type/UNCONDITIONAL deliberately left open for curator review —
the asymmetric-pre-coordination case (CONDITIONAL has its concept,
C0814041; the unmarked default has none).

### knockout_type/UNCONDITIONAL → C0599772 Gene Knockout Techniques, `narrower`

The asymmetric-pre-coordination case resolved: CONDITIONAL has its own
concept (C0814041 "conditional gene knockout technology") while the
unmarked default has none — UMLS holds no "constitutive" or
"conventional" knockout concept. Anchored on the generic technique
(MSH); the token is the unmarked *subtype*, GEM more specific, hence
`narrower` (a relation initially misstated as `broader` in discussion
and corrected before recording — the WGS-WES case runs the other way:
there the token outstrips the concept). Rejected: C1522225 "Knock-out"
(NCI bare qualifier). This closes the value worklist: every value in
the workspace is mapped or argued-unmapped, and every axis is typed.

### Consistency audit: broader / narrower direction

The curator suspected the direction convention was applied inconsistently
and asked for a review. Standard (documented in the s15 supplement and
followed by the majority of records): `narrower` = GEM more specific than
the concept, `broader` = GEM more general. Of six directional records,
four were consistent (STATISTICAL_GENETICS, ACTIVITY, UNCONDITIONAL all
`narrower`; WGS-WES `broader`) and two deviated and were corrected:
method/BIOINFORMATICS_INFERENCE flipped broader->narrower (the token is
inference work *within* Computational Biology — the same shape as
STATISTICAL_GENETICS -> Biostatistics, which was already recorded
narrower); target_type/TRANSCRIPT flipped broader->`close` (the original
direction claim was wrong in either direction — by the dimension's own
pattern, GENE -> Genes `exact` and VARIANT -> Genetic Variation `close`,
the class-of-the-target-kind anchor is a closeness call, with the isoform
nuance keeping it short of exact).

### resolution axis ruled: T082 Spatial Concept stands

The curator kept T082. The intension is spatial granularity of
localization, and UMLS itself types Gene Locus and Coordinate as Spatial
Concepts. That only two of five anchors are in-axis is itself a UMLS
gap: no spatial concept represents a coarse genomic window or segment.
The principled exception is VARIANT, a two-dimensional notion (a
position x a discrete nucleotide change), whose anchor necessarily lies
outside any purely spatial type. With this ruling every typed axis
carries a curator confirmation; only the three untyped-by-design
boolean/free-text dimensions remain unconfirmed, as intended.

### Axis curation pass (accept_sty confirmations)

Every typed axis now carries an explicit curator confirmation
(`accept_sty` + note) rather than an inventory-only binding: 13 of 14
recorded in one pass, each note stating the argument settled earlier
(knowledge_domain's T091 -> T090 lift; phenotype_scale's deliberate
letter-root breadth, under which every scale anchor falls including Sign
or Symptom at A2.2.2; variant_ascertainment's intension-over-anchors
T062; the method/subdomain/knockout technique split; the three T045
conditionals). The credibility axis note was refreshed from the old
SEPIO-anchored wording to the defeasibility definition. The one axis
left unconfirmed is **resolution**: its anchors split 2/2/1 across T082
(Gene Locus, Coordinate), T028 (Genetic Loci, Gene Feature) and T070
(Genetic Variation), so keeping T082 Spatial Concept (the granularity
intension; UMLS itself types Gene Locus as a Spatial Concept) versus
moving to T028 (target_type's axis, home of the coarse levels) is a
genuine judgment call awaiting the curator's ruling.

## Earlier rounds (2026-08-29..30, summarized)

- **credibility/**: all four tiers argued `unmapped` via a pre-registered
  sweep (protocol `sweeps/credibility.yaml`, classifier
  `gem-umls-classify-credibility`); the full argument is the SN9 credibility
  note (`paper/sections/s19_credibility_umls.tex`). Nineteen rejected
  families; the four closest constructs (SNOMED degree qualifiers, NCI
  Level of Evidence, NCI Confidence answer set, SNOMED diagnostic-certainty
  modality) each fail a named criterion.
- **knowledge_domain/ANIMAL_GENETICS → NCI C1510895, exact**: kept the
  faithful concept from the specialized vocabulary rather than a broader
  MeSH descriptor; the tradeoff note is in the s15 supplement.
- **variant_ascertainment/OBSERVED_IN_CASES, OBSERVED_IN_CONTROLS →
  C0007328 Case-Control Studies, `related`**: ascertainment routes anchored
  on the related methodology concept — an early operator/constituent-style
  precedent.
- A full-mapping review (30 confirmed findings) cleared over-confident
  accepts (e.g. RELATED_GENE → "Related (finding)" social sense;
  FUNCTIONAL_ELEMENT → Functional Genomics; SEGMENT/INTERVAL/WINDOW →
  "Part") back to blank state for re-adjudication rather than patching
  them in place — several were then resolved above.
