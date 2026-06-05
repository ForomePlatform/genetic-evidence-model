# REVIEW_PROTOCOL.md

Annotation-review protocol for the Genetic Evidence Model (GEM).

This document specifies the mode-agnostic rules that govern any
review of an annotation under the GEM schema, regardless of
whether the review is conducted by a human curator alone, by an
AI assistant in dialogue with a curator, or by an automated
batch process.

Operational workflows for specific review modes are documented
separately:

- `REVIEW_PROTOCOL_INTERACTIVE.md` (curator-in-dialogue with AI
  assistant; the workflow this version operationalises)
- `REVIEW_PROTOCOL_BATCH.md` (planned: autonomous review without
  curator interaction; not yet specified)

---

## 1. Scope

The protocol covers review of a single annotation YAML file
against its source paper and the current schema.

Reviewing an annotation means producing a structured judgement
about:

- Whether the annotation is structurally valid (parses, conforms
  to SHACL, has required fields).
- Whether the annotation is internally consistent (source spans
  appear in the paper verbatim, dimension assignments do not
  contradict one another).
- Whether the annotation is evidentially adequate (the GE items
  fairly partition the paper's evidential content, assertion
  text accurately reflects the source, dimension values are
  appropriate to the claim).

Review is independent of who produced the annotation. The same
protocol applies to AI-drafted, manually authored, or hybrid
annotations. The annotation's `provenance.mode` field informs
the reviewer what to expect (e.g., annotator-emitted
`ai_uncertainty` flags in autonomous-mode output) but does not
change the substantive review rules.

---

## 2. The three levels of review

Every review observation is associated with one of three
levels. The level matters because it determines the reviewer's
confidence and the appropriate response.

### 2.1 Structural

The annotation as a data artefact. Does it parse? Do required
fields exist? Are types correct? Does it match the SHACL
schema?

Structural issues are high-confidence: an absent required
field is an absent required field.

Examples:
- A `GeneticEvidenceAssertion` lacks a `source_span`.
- A required dimension is unpopulated and no
  `not_applicable_or_omitted` marker is present.
- A YAML key is misspelled.
- A top-level or item-level key is not defined in the schema (an
  invented structure).

#### 2.1.1 Invented (non-schema) keys

Structural validation checks not only for missing required fields
but for **extra keys that the schema does not define**. An invented
key (for example, a top-level `meta_assertions` block used to hold a
cross-item claim) is a structural defect. The recommended handling
has two parts, and they are separate: the gap the invented key was
trying to fill is logged as a `candidate_extension` (the schema is
missing a slot), while the non-schema key itself is recorded as a
structural defect to remove. Do not absorb invented structure into
the annotation; route the underlying need to a candidate extension
instead.

### 2.2 Consistency

Internal coherence of the annotation, including its relationship
to the paper at the textual level.

Consistency issues are high-confidence when they involve
verbatim checking, lower-confidence when they involve
dimension-interaction reasoning.

Examples:
- A `source_span` phrase does not appear verbatim in the paper
  at the cited page.
- A `phenotype_scale` value is `MOLECULAR` but the assertion
  text describes a clinical phenotype.
- A `candidate_extension` block proposes an enumeration value
  already promoted in `schema/EXTENSIONS.md`.

#### 2.2.1 Source-span defect severity tiers

Source-span defects are classified into two severity tiers, so they
are handled consistently without a per-session ruling. The
source-span word limit defined in `protocols/PROTOCOL.md` §4.2 is a
**soft** cap (keep the number itself in `PROTOCOL.md`; do not
redefine it here).

- **Blocking** (emit `reviewer_disagreement`; forces an Edit
  verdict): a wrong page or locator; wrong content; a non-verbatim
  span whose wording changes the meaning.
- **Non-blocking** (emit `reviewer_suggestion`): length over the
  soft cap by a small margin; notation or formatting drift where the
  value is correct; faithful-but-stitched (ellipsised) spans.

Only blocking defects force an Edit; the rest are recommendations.
This tiering subsumes what would otherwise be per-session rulings
about how strictly to apply the span rules.

### 2.3 Evidential

The annotation's faithfulness to the paper as evidence.

Evidential observations are the most valuable and the most
AI-prone-to-error. They should always be presented as
recommendations to the curator, not assertions of fact.

Examples:
- An assertion summary distorts what the paper actually claims.
- A GE item bundles two claims that differ in method or
  credibility (should be split per `PROTOCOL.md` §2).
- A claim made in the paper is missing from the annotation
  entirely (this is the missing-evidence check; see §5).
- A dimension value is a forced fit not flagged as such.

### 2.4 Protocol-version baseline

An annotation is reviewed against the protocol version it was
**produced** under, not the latest version. Rules introduced
**after** the annotation's production version are recorded as
**forward-notes** (non-blocking `reviewer_suggestion`), never as
blocking `reviewer_disagreement` defects. This keeps a review from
charging an older annotation with requirements that did not exist
when it was written.

The mechanism is keyed to the version. The annotation's production
version is read from its `provenance` (the
`annotation_production_protocol` field, recorded in the review log;
see §4.1); if absent, the reviewer asks the curator and records the
answer. Observation severity (§2.1 to §2.3) is then modulated by the
baseline: a defect that exists only because of a post-baseline rule
is downgraded to a forward-note.

The current worked instance is the **v0 → v1.0** delta. The v1.0
additions, relative to the v0 annotations in the corpus, are the
mandatory `confidence_summary`, the full `provenance` block,
conditional-activation strictness, and the hierarchical `method`
dimension. Cross-check this list against `protocols/PROTOCOL.md`
rather than treating it as the only possible delta; future version
gaps are handled by the same mechanism.

---

## 3. Review flag vocabulary

The reviewer emits flags drawn from the existing vocabulary.
No new flag types are introduced by this protocol.

| Flag                     | Use                                                                                                       |
| ------------------------ | --------------------------------------------------------------------------------------------------------- |
| `reviewer_disagreement`  | A clear factual correction. The annotation says X; the paper says Y. The annotation should be changed.    |
| `reviewer_suggestion`    | An optional addition or improvement. The annotation is not wrong, but could be more complete or specific. |
| `reviewer_query`         | A case where the mapping is itself unclear. The reviewer is uncertain whether the annotation is right.    |

### 3.1 Sub-category: migration

A `reviewer_suggestion` may carry an optional `subcategory:
migration` to indicate that the suggestion is about moving an
annotation from an older protocol version to a newer one
(typically: flat method value to leaf value under the
hierarchy). Migration suggestions are non-blocking; the
annotation as-is remains valid.

### 3.2 Sub-category: promotion

A `reviewer_suggestion` may carry an optional `subcategory:
promotion` to record that a candidate extension now has a **second
independent occurrence** and is eligible for promotion under the
two-papers rule (`protocols/PROTOCOL.md` §5.2). The reviewer only
**records the recommendation**; applying a promotion (edits to
`schema/dimensions.md`, the SHACL schema, and `schema/EXTENSIONS.md`)
is a separate workflow. See the promotion check in
`protocols/REVIEW_PROTOCOL_INTERACTIVE.md` §3.4.

### 3.3 What the reviewer does not do

- The reviewer does not silently change the source annotation. The
  reviewer emits a proposed **updated annotation** as a third
  artefact (see §4.3) that applies only the curator-approved
  verdicts; it does not overwrite the source until the curator
  accepts it.
- The reviewer does not silently accept anything. Every GE item
  must be explicitly reviewed (approved, rejected, or marked
  for edit) before the review is considered complete.
- The reviewer does not invent items. The missing-evidence
  check (see §5) surfaces possible additions, but additions are
  curator-confirmed before being treated as items in their own
  right.
- The reviewer does not apply candidate-extension promotions to the
  schema, and does not re-annotate from scratch (that is the
  `genetic-evidence-annotation` skill).

---

## 4. Output

A review pass produces three artefacts: the review log (§4.1), the
review report (§4.2), and the updated annotation (§4.3).

### 4.1 The review log (YAML)

A structured record of every observation made during the
review, plus the curator's verdict on every GE item.

The log is keyed by the annotation it reviews. Top-level fields:

- `reviewed_annotation`: path or identifier of the annotation.
- `annotation_production_protocol`: the protocol version the
  annotation was produced under (see §2.4), read from its
  `provenance` or supplied by the curator. Governs the
  protocol-version baseline.
- `reviewer`: identifier of the reviewer (human name or AI
  model identifier).
- `reviewed_at`: ISO 8601 timestamp.
- `protocol_version`: the version of this protocol under which
  the review was conducted.
- `session_rulings`: a list of curator-set governing conventions
  for the session (see `protocols/REVIEW_PROTOCOL_INTERACTIVE.md`
  §3.1). Each entry has `id` (SR-1, SR-2, ...), `topic`, `ruling`
  (the text), and optional `pre_cleared` (item/assertion ids) or
  `note`.
- `verdicts`: a list of per-item verdicts, one per GE item in
  the annotation (and one per item added during the
  missing-evidence check, if any).
- `observations`: a list of review observations not tied to a
  specific GE item (paper-level concerns, candidate-extension
  comments, structural issues spanning items).
- `migration_suggestions`: a list of `reviewer_suggestion`
  entries with `subcategory: migration`, gathered for easy
  consumption by a later migration workflow.

Each verdict entry contains:

- `ge_item`: the GE item id.
- `decision`: one of `approved`, `approved_despite_flags`,
  `rejected`, `marked_for_edit`.
- `flags_recorded`: any flags the reviewer wishes to attach to
  this item.
- `notes`: optional free-text curator notes.

### 4.2 The review report (markdown)

A human-readable narrative of the review, suitable for
attaching to a pull request, including in a paper supplement,
or sharing with co-authors.

The report covers:

- Header (annotation reviewed, reviewer, date).
- Summary of verdicts (counts of approved / rejected / etc.).
- Missing-evidence section (what the review proposed adding,
  what was accepted).
- Per-item commentary (for items with non-trivial verdicts).
- Recommendations (next steps, follow-up review if needed).

The report is generated from the log; the log is the
authoritative artefact.

### 4.3 The updated annotation (YAML)

The review also emits the **updated annotation**: the source
annotation with the curator-approved verdicts applied, so the
curator does not have to request it as a separate step. It is
generated from the verdicts in the log and contains only
curator-approved changes:

- `marked_for_edit` items: the agreed edits applied (label,
  dimension, source-span, and structural corrections recorded in
  the verdict).
- `approved` / `approved_despite_flags` items: left as-is; their
  non-blocking flags are recorded in the log but not applied.
- `rejected` items: removed.
- Items accepted in the missing-evidence check (§5): added.
- Invented non-schema keys (§2.1.1): removed, with the underlying
  gap logged as a `candidate_extension`.
- `provenance`: a `review_applied` entry recording the review log,
  date, and a short summary of what was applied.

Migration suggestions (`subcategory: migration`) and promotion
recommendations (`subcategory: promotion`) are non-blocking: apply
migrations to the updated annotation only when the curator endorses
them in-session; never apply promotions (they change the schema, not
the annotation).

The updated annotation does **not** overwrite the source file
automatically. Phase 4 (`protocols/REVIEW_PROTOCOL_INTERACTIVE.md`
§3.5) emits it and asks the curator where to write it (a sidecar
path, or replacing the source after explicit confirmation). When the
edits move numbers cited in a downstream artefact (the paper, the
coverage file), those are handled by the relevant sync workflow, not
silently here.

---

## 5. Missing-evidence check

A review pass that only inspects what is *in* the annotation
cannot catch claims the annotator missed. Missing-evidence
checking is therefore a discrete phase of the review.

The missing-evidence check is conducted **before** per-item
review, not after. The reasoning: surfacing possible new items
at the start sets a frame ("what should be here") before the
reviewer descends into per-item judgement. Items proposed in
this phase are added to the per-item review queue and
reviewed under the same workflow as pre-existing items.

The check has two outputs:

1. A list of candidate missed claims, each with a brief
   description and a source-span pointing to the paper passage
   that motivates it.
2. The curator's verdict on each: accepted (becomes a new GE
   item in the review queue), rejected (recorded as considered
   but not added), or deferred (curator wants to think; the
   item is parked).

---

## 6. Per-item review

Each GE item in the annotation receives an explicit verdict.
This includes items where the reviewer has no concerns:
implicit approval is not allowed.

### 6.1 Decision options

For each item, the reviewer chooses one of:

- **Approve as a whole.** The item stands as-is.
- **Approve despite flags.** The reviewer notes one or more
  concerns but accepts the item rather than requiring an edit.
  (This is the option offered when the AI has surfaced issues
  but the curator has decided to accept the item anyway.)
- **Reject.** The item should be removed from the annotation.
- **Mark for edit.** The item should be modified. The specific
  edit is recorded in the verdict's `notes` field.

When the reviewer (AI or human) has surfaced flags for the
item, the default offered to the curator is **Mark for edit**;
the curator may override with **Approve despite flags**.

When the reviewer has surfaced no flags, the default is
**Approve as a whole**.

### 6.2 Granularity of approval

Approval is at the GE-item level, not the assertion level. If
some assertions within an item are flagged and others are not,
the verdict applies to the item as a whole and the verdict's
notes record per-assertion judgements.

This is a simplification chosen for tractability. Future
versions may add assertion-level verdict granularity.

---

## 7. Second-round triggers

A review pass may surface enough changes that a second review
round is warranted. The protocol does not trigger this
automatically; the reviewer flags it as a recommendation.

A second round is recommended when:

- Items were added during the missing-evidence check
  (substantively new content needs the same scrutiny as
  pre-existing content).
- Multiple `marked_for_edit` decisions accumulated (the edited
  annotation will be substantially different).
- Cross-cutting issues surfaced (e.g., the schema's method
  hierarchy is exercised inconsistently across items, requiring
  a coordinated rework).

The recommendation is recorded in the review log under
`recommendations.second_round_warranted` (boolean) with a
free-text `recommendations.rationale`.

---

## 8. Versioning

This protocol is versioned. Reviews produced under a given
version of the protocol should record the version in their
`protocol_version` field.

**Current version: 1.0**

Changes that affect review outputs (rule changes, not editorial
revisions) require a major-version bump. Editorial changes are
minor-version bumps.

---

## 9. Related documents

- `protocols/PROTOCOL.md`: canonical annotation-protocol rules.
- `protocols/PROTOCOL_AUTONOMOUS.md`: autonomous-annotation
  workflow.
- `schema/dimensions.md`: dimension reference (the reviewer
  consults this to check whether dimension assignments are
  legitimate).
- `schema/EXTENSIONS.md`: candidate-extensions log (the
  reviewer consults this to check whether candidate extensions
  in the annotation are novel or duplicated).
- `notes/ROADMAP.md`: expected leaf-value migrations under
  the method hierarchy (the reviewer consults this to populate
  `subcategory: migration` suggestions).
- `protocols/LABELING_EXAMPLES.md`: label-style reference (the reviewer
  consults this to check whether item labels are evidential
  statements per `PROTOCOL.md` section 2.4).
- `REVIEW_PROTOCOL_INTERACTIVE.md`: operational workflow for
  interactive review with curator in the loop.
-
