# LABELING_EXAMPLES.md

Concrete examples of well-formed GE item labels, drawn from the
four curator-led annotations in the corpus.

Use this file alongside `PROTOCOL.md` section 2.4 for grounding
the style of `label` fields. The pattern across all curator-led
labels: **the label is the evidential claim the item makes**, not
a description of what kind of evidence the item contains.

---

## From Jossin 2017 (Llgl1; molecular-mechanism paper)

- `"Llgl1 binds N-cadherin via WD14 domain in mouse embryonic neural stem cells"`
- `"Conditional Llgl1 knockout produces periventricular heterotopia in mouse"`
- `"Loss of Llgl1 disrupts apical junction complex in neural epithelium"`
- `"aPKC phosphorylation of Llgl1 inhibits LLGL1-N-cadherin interaction"`
- `"Dominant-negative LLGL1 fragment causes PH via disrupted N-cadherin binding in vivo"`

Pattern: **subject** (Llgl1, conditional knockout, aPKC) +
**verb** (binds, produces, disrupts, inhibits) +
**object/effect** (N-cadherin, PH, junction complex) +
**qualifier** (cohort, condition, scale).

## From Davis 2011 (TTC21B; breadth exemplar)

- `"Rare TTC21B nonsynonymous variants enriched in NPHP/ciliopathy patients"`
- `"40 TTC21B missense alleles tested for rescue of zebrafish ttc21b morphant phenotype"`
- `"mIMCD3 cells with TTC21B variants show cilia-length defects"`
- `"TTC21B biallelic variants segregate with disease in 6 ciliopathy families"`
- `"p.Pro209Leu shares a founder haplotype across multiple families"`

Pattern: **variant/gene** (TTC21B variants, p.Pro209Leu) +
**verb of evidential relation** (enriched in, tested for, show,
segregate with) + **specific outcome** (NPHP, rescue, defects,
disease).

## From Nelson 1992 (CD18; classical molecular genetics)

- `"12-bp insertion (rs5030670) abolishes beta-2 integrin surface expression in COS cells"`
- `"R586W (c.C1756T) impairs beta-2 integrin surface expression in COS cells"`
- `"N351S (c.A1052G) impairs beta-2 integrin surface expression in COS cells"`

Pattern: **specific variant** + **functional consequence** +
**experimental system**. Even when several items share the
same verb and object, the label distinguishes them by the
specific variant they describe, not by abstracting to "three
loss-of-function variants in CD18."

## From Gupta 2015 (ATP6AP2; low-credibility edge case)

- `"ATP6AP2 c.168+6T>A segregates X-linked recessively in family with ID, epilepsy, parkinsonism"`
- `"In silico splice prediction supports disruption of ATP6AP2 intron 2 donor site"`

Pattern: even small papers with only 2 items use labels that
state the specific claim, not "a candidate splice-site
variant" or "computational support."

---

## How to derive a label

For any GE item, ask in order:

1. **What does this item assert?**: One sentence, no
   hand-waving. ("rs11209026 confers protection against ileal
   CD in non-Jewish cases.")
2. **Is there a qualifier the reader needs to know?**: Cohort,
   condition, scale, study design. Append it.
   ("...in non-Jewish discovery cohort.")
3. **Is the subject specific?**: If you wrote "the gene" or
   "this variant", rewrite with the actual gene or variant.
4. **Is the verb evidential rather than meta?**: "binds,"
   "confers," "segregates," "abolishes" are evidential.
   "Discovery of," "characterisation of," "confirmation of,"
   "analysis of" are meta and should be replaced.

---

## Common failure modes to avoid

- **Meta-labels:** "Genome-wide association study identifies
  IL23R." Better: "rs11209026 in IL23R confers protection
  against ileal CD in non-Jewish discovery cohort."
- **Forward references:** "Confirmation of the IL23R
  association." Better: "rs11209026 confers protection against
  CD also in Jewish replication cohort."
- **Thematic summaries:** "Allelic architecture of IL23R."
  Better: "Multiple independent IL23R variants contribute to
  CD risk by conditional analysis."
- **Hedging via abstraction:** "TTC21B variants in
  ciliopathy." Better: "Rare TTC21B nonsynonymous variants
  enriched in NPHP/ciliopathy patients."
- **Role descriptions:** "Cited mouse-model evidence
  supporting therapeutic rationale." Better: "IL-23 pathway
  blockade ameliorates murine colitis (cited from refs 13, 18)."

---

## When a single label cannot capture a lumped item

If you have lumped multiple claims into one GE item per the
lumper rule, and no single label states all of them clearly,
this is a signal that the lump may be too broad. Reconsider
splitting before settling for a generalised label.

The exception: when claims share subject, verb, and qualifier
but differ in a fine detail (three missense variants in CD18,
each impairing surface expression), the label may name the
representative claim and let `assertions` carry the specific
variants.
