# PROTOCOL.md

Annotation protocol for the Genetic Evidence Model (GEM).

This document specifies the mode-agnostic rules that govern any
annotation of a paper under the GEM schema, regardless of whether
the annotation is produced by a human curator, by an AI assistant,
or by a hybrid workflow.

Operational workflows for specific annotation modes are documented
separately:

- `protocols/PROTOCOL_AUTONOMOUS.md` (single-pass AI annotation without a
  curator in the loop)
- `protocols/PROTOCOL_INTERACTIVE.md` (future: staged AI + curator
  collaboration; not yet specified)

---

## 1. Scope

The protocol covers annotation of primary-literature publications
in human genetics, model-organism genetics, population genetics,
and polygenic-score genetics. It assumes:

- A single source publication per annotation (one PDF or HTML
  article in).
- A single output YAML file conforming to the GEM schema.
- The schema (`schema/dimensions.md` and
  `schema/genetic_evidence.shacl.ttl`) is current and authoritative.

Annotation of other artefact types (review articles, datasets,
guidelines) is out of scope.

---

## 2. Decomposition rules

The annotator decomposes the paper into one or more
`GeneticEvidence` items (GE items).

### 2.1 Lumper default

When in doubt, prefer fewer, larger GE items over more, smaller
ones. The default rule for grouping claims:

> Two evidential claims belong in the **same** GE item if they
> share method, target, and credibility. They belong in
> **separate** GE items if any of method, target, or credibility
> differs.

Method, target, and credibility are the three dimensions whose
divergence justifies a split. Differences in other dimensions
(`measurement_target`, `gene_relation`, `organism`, etc.) do not
by themselves warrant separation.

### 2.2 What this looks like in practice

- A GWAS discovery cohort and its replication in a different
  cohort: **separate items** (target the same, method the same,
  but credibility differs because replication is an independent
  test).
- A case-control association and a family-based transmission
  test for the same variant: **separate items** (method differs).
- Three sequential statistical tests within the same analytical
  framework, on the same cohort, with cumulative p-values: **one
  item** (method, target, credibility all align).
- Cited evidence from a different paper supporting the same
  variant: **separate item, flagged** (see section 3.3).
- A negative result at a different locus during the same analysis:
  **separate item** (target differs).

### 2.3 When the lumper default is hard to apply

Some papers genuinely contain unresolvable decomposition
ambiguity. In those cases, the annotator chooses the lumper
option and emits `ai_uncertainty` (in autonomous mode) or
proposes the alternative to the curator (in interactive mode).
**It is easier to retroactively split a GE item than to merge
two.**

### 2.4 What an item's label should be

Each GE item's `label` field is an **evidential statement**:
it names the subject of the claim, the claim itself, and the
relevant qualifier (cohort, condition, scale). A label is not
a description of the *kind of evidence* the item contains, nor
a description of the *role* the item plays in the paper.

The label is the answer to "what does this item assert?": not
"what kind of analysis produced it?" or "what does this item
do in the paper's argument?"

Good label patterns:

- `"<variant or gene> <verb> <effect> in <cohort or condition>"`
  e.g., `"rs11209026 (Arg381Gln) in IL23R confers protection
  against ileal CD in non-Jewish discovery cohort"`
- `"<protein A> binds <protein B> via <domain>"`
- `"<gene> conditional knockout produces <phenotype> at <scale>"`
- `"<variant> shows <pattern> in <study design>"`

Bad label patterns (avoid):

- `"GWAS discovery of <gene>"`: describes the study type, not
  the claim.
- `"Confirmation of <X> in <cohort>"`: forward reference; the
  reader must know what X is before "confirmation" parses, and
  the *claim* (rather than the act of confirming) should be
  named.
- `"Allelic architecture: multiple independent signals"`,
  a thematic summary rather than a statement.
- `"<gene> annotation and characterisation"`: describes the
  item's content abstractly rather than naming the claim.

When an item lumps several related claims (per the lumper rule),
the label names the strongest or most representative claim,
with the others appearing as `assertions`. The label is not a
generalised summary that abstracts away from any specific
claim.

If no single label captures all the lumped claims clearly,
this is a signal that the items should be split, not that the
label should be generalised further.

---

## 3. Dimension assignment

Every GE item must populate all always-required dimensions
(`knowledge_domain`, `method`, `target_type`, `target`,
`target_resolution`, `phenotype_scale`, `credibility`). Conditional
dimensions — including `variant_ascertainment`, required when
`target_type = VARIANT` — are populated only when their activation
condition holds, as specified by the SHACL schema. Where a curator
considers a dimension and chooses not to fill it, it is marked
`not_applicable_or_omitted` rather than left silently absent.

### 3.1 Enumeration mapping

Dimension values must be drawn from the enumerations in
`schema/dimensions.md`. When the paper describes a value not
present in the enumeration, see section 3.3 (forced-fit
handling).

### 3.2 Normalisation notes

When mapping the paper's terminology to a schema enumeration
involves judgement (e.g., the paper says "localisation and
protein expression" and the annotator maps this to
`{LOCALIZATION, EXISTENCE}`), record the mapping as a
`normalization_note` on the GE item. In AI-drafted annotations,
the `type` field is `ai_normalization`. The note is for later
audit, not for review-time discussion.

### 3.3 Forced-fit rule

When a paper's claim genuinely does not fit any value in the
schema's enumeration, the annotator **does not silently coerce**.
Instead:

1. Mark the relevant dimension with `annotated_as:
   not_applicable_or_omitted` or the closest enumeration value
   with a flag, whichever the schema currently supports for that
   dimension.
2. Emit a `candidate_extension` block proposing what the
   enumeration would need to look like to accommodate the claim.
3. Emit an `ai_assumption` flag if a closest-fit value was
   chosen, or an `ai_uncertainty` flag if no value was chosen.

Candidate extensions are local to the paper that surfaced them
until they are promoted (section 5).

### 3.4 Hierarchical dimensions

Some dimensions have a hierarchical structure with parent-child
relationships rather than a flat enumeration. The `method`
dimension is the first to receive this treatment (see
`schema/dimensions.md` for the hierarchy).

When a dimension is hierarchical, the annotator follows these
rules:

1. **Pick the most specific applicable value.** If the paper
   supports a leaf value (`GWAS`, `IN_VIVO`, `META_ANALYSIS`),
   use the leaf. Do not redundantly list ancestors; parent
   relationships are recoverable from the schema.

2. **Intermediate values are valid when leaf values are not
   supported.** If the paper says "statistical genetics" without
   specifying the design, or "experiment" without specifying
   in-vivo / in-vitro / in-silico, the intermediate value
   (`STATISTICAL_GENETICS`, `EXPERIMENT`) is the correct
   annotation. In this case, **emit `ai_uncertainty`** on the
   dimension to record that the value is intermediate by
   epistemic necessity, not by oversight.

3. **Multiple values from the same dimension are interpreted
   as additive, not hierarchical.** If `method: [GWAS,
   META_ANALYSIS]`, both apply (e.g., a meta-analysis of
   multiple GWASes). Do not list a leaf and its ancestor
   together unless both genuinely apply.

4. **For items decomposed by method differences** (see §2.2
   and §3.5), the new hierarchical structure usually replaces
   the need for the `ai_uncertainty` / candidate-extension
   handling described in §3.5. A GWAS discovery cohort
   (`method: [GWAS]`) and a family-based transmission test
   (`method: [TRANSMISSION_DISEQUILIBRIUM_TEST]`) now have
   distinguishable method values without forcing both into
   `STATISTICAL_GENETICS`. §3.5 still applies when even the
   leaf values fail to distinguish methodologically distinct
   items.

### 3.5 When two items share a method enumeration value

Sometimes the decomposition rule (section 2.2) splits two items
based on differing methods (case-control vs family-based
transmission test, for example), but the `method` dimension's
enumeration is too coarse to reflect the distinction at the
schema level: both items end up with `method:
[STATISTICAL_GENETICS]`.

This is not a labelling problem; it is a real schema-granularity
question. When it arises, the annotator must do one of:

1. **Cite the specific design in `credibility_comment`** and
   proceed. This is the default when the decomposition rule was
   correctly applied (the items ARE distinct on credibility or
   target) and the method-dimension collapse is incidental rather
   than load-bearing.

2. **Emit a `candidate_extension`** proposing finer
   enumeration values (e.g., distinguishing case-control,
   family-based, transmission-disequilibrium, conditional, and
   meta-analytic statistical methods). Do this when the
   collapse loses information that downstream consumers would
   plausibly want.

3. **Flag as `ai_uncertainty`** on the `method` dimension if
   the annotator is unsure whether the collapse is acceptable.

Do not silently assign the same `method` value to multiply
decomposed items without naming the distinction somewhere in
the annotation. The decomposition into separate items is a
claim that they are evidentially distinct; the dimension
assignment must not contradict that claim by appearing
identical across items.

---

## 4. Source anchoring

Every `GeneticEvidenceAssertion` must carry a `source_span`
field.

### 4.1 Required fields

- `page`: the page number in the source PDF (1-indexed).
- `phrase`: a short identifying phrase that lets a reader locate
  the supporting passage.

### 4.2 Phrase length and form

- **Length:** under 15 words. This is a hard limit. A phrase
  longer than 15 words is rejected at validation time.
- **Form:** verbatim by default. The phrase must be a literal
  substring of the source text.
- **Paraphrase exception:** if the verbatim phrase that captures
  the claim would exceed 15 words, the annotator may use a short
  paraphrase (also under 15 words) that identifies the passage.
  Paraphrased phrases are flagged with
  `source_span_is_paraphrase: true`.

### 4.3 Coverage

Source anchoring is not optional. An annotation in which any
assertion lacks a `source_span` is rejected at validation time.

### 4.4 Fair use

The 15-word limit is grounded in fair-use norms for excerpting
copyrighted publisher material. Annotators should not concatenate
multiple short phrases from the same passage to circumvent this
limit. If a passage cannot be anchored with a single under-15-word
phrase (verbatim or paraphrase), the annotator should reconsider
whether the assertion is appropriately granular.

---

## 5. Candidate extensions

A candidate extension is a proposal to extend the schema
(typically by adding an enumeration value, occasionally by adding
a dimension) that emerged during annotation of a specific paper.

### 5.1 Candidate-extension fields

Each candidate has:

- An identifier (`CE-<initial>N`, e.g., `CE-J3` for Jossin's third
  candidate).
- A description of the gap.
- The dimension or dimensions affected.
- Proposed enumeration values or schema changes.
- The GE item(s) in the current paper that exhibit the gap.

### 5.2 Two-papers promotion rule

A candidate extension that appears in only one paper is recorded
locally and does not enter the schema. A candidate that appears
**independently in a second paper** is promoted to a first-class
dimension or enumeration value. The promotion requires:

- The schema (`dimensions.md` and SHACL) updated.
- The candidate's status in `schema/EXTENSIONS.md` changed from
  `unpromoted` to `promoted`.
- All affected papers' annotations updated to use the new
  enumeration value.

Promotion is rare and is not done autonomously; it requires
explicit curator action.

### 5.3 Retraction

A candidate that, on review, is found to be redundant with
existing schema features (the canonical example: a polarity
field, which the predicate-based `EvidenceAssertion` already
supports) is **retracted**, not deleted. Retraction is recorded
in `schema/EXTENSIONS.md` with rationale.

---

## 6. Flag taxonomy

Two flag categories exist: **annotator-emitted** (recorded during
annotation) and **curator-emitted** (recorded during review). The
autonomous protocol concerns only annotator-emitted flags;
curator-emitted flags are out of scope for this document.

### 6.1 Annotator-emitted flag types

| Flag                  | When to use                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `ai_uncertainty`      | The annotator was unsure about a schema mapping and wants human input. No commitment is made.                 |
| `ai_assumption`       | The annotator made a judgement call without strong textual evidence. A commitment is made; a reviewer should verify. |
| `ai_normalization`    | A `normalization_note` recording a mechanical mapping from the paper's terminology to a schema enumeration.    |

### 6.2 Decision tree

For each annotation choice:

1. **Is the choice fully supported by the paper's text?**
   - Yes → no flag.
   - No → continue.
2. **Was a commitment made (a value assigned)?**
   - Yes → `ai_assumption`.
   - No → `ai_uncertainty`.

The choice between `ai_uncertainty` and `ai_assumption` is
**not** about confidence per se; it is about commitment. If the
annotator filled in a value, the flag is `ai_assumption`. If the
annotator left a slot empty or marked
`not_applicable_or_omitted`, the flag is `ai_uncertainty`.

### 6.3 When to flag rather than candidate-extend

If the gap is in the schema (the enumeration is genuinely
insufficient): emit `candidate_extension`.

If the gap is in the annotator's confidence (the schema is fine
but the paper is unclear): emit `ai_uncertainty` or
`ai_assumption`.

Both can co-occur on the same dimension if both apply.

---

## 7. What the annotator does not do

- The annotator does not propose changes to the schema. Schema
  changes are made only by promoting candidate extensions
  (section 5.2).
- The annotator does not evaluate the *quality* of the paper's
  science. Credibility is recorded as a dimension value
  reflecting what the paper claims and how, not the annotator's
  assessment of whether the claims are correct.
- The annotator does not add citations to other works. If the
  paper cites another work as evidence (for example, a clinical
  paper citing prior mouse-model work to support a therapeutic
  rationale), that becomes a separate GE item in the annotation,
  flagged as `cited_evidence: true`.

---

## 8. Versioning

This protocol is versioned. Annotations produced under a given
version of the protocol should record the version in their
metadata block (`provenance.protocol_version`).

**Current version: 1.0**

Changes to the protocol that affect annotation outputs (rule
changes, not editorial revisions) require a major-version bump.
Editorial changes are minor-version bumps.

---

## 9. Related documents

- `schema/dimensions.md`: the human-readable dimension reference.
- `schema/genetic_evidence.shacl.ttl`: the machine-checkable SHACL schema.
- `schema/EXTENSIONS.md`: the log of all candidate extensions.
- `annotations/coverage.md`: per-paper dimension and flag counts.
- `protocols/PROTOCOL_AUTONOMOUS.md`: operational workflow for autonomous mode.
- `protocols/PROTOCOL_INTERACTIVE.md`: (planned) operational workflow for interactive mode.

