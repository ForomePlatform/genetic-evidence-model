# REVIEW_PROTOCOL_INTERACTIVE.md

Operational workflow for **interactive curator-with-AI review**
of an annotation under the Genetic Evidence Model.

This document specifies how an AI assistant, in dialogue with a
human curator, conducts a review of an annotation YAML and
produces the review log and report described in
`REVIEW_PROTOCOL.md`.

The mode is **interactive**: the AI surfaces observations one at
a time (or in small batches), the curator responds, the AI moves
to the next. The session may span many turns. The final
artefacts are built incrementally as the conversation progresses
and emitted at the end when the curator confirms the review is
complete.

This document references `REVIEW_PROTOCOL.md` for substantive
rules. It covers only what is specific to interactive mode.

---

## 1. When to use interactive mode

Interactive mode is appropriate when:

- The annotation is being reviewed by a curator with the
  intention of producing an authoritative verdict.
- The annotation contains substantive judgement calls that
  benefit from per-item curator engagement.
- A final decision (approve/reject/edit) is needed for every GE
  item, not just for items the AI flags.

Interactive mode is **not** appropriate when:

- A large batch of annotations needs quick screening (use a
  future batch mode).
- No curator is available (review is deferred entirely).

---

## 2. Inputs

The AI assistant requires:

1. **The annotation YAML.** A file path or pasted content.
2. **The source paper.** A PDF, HTML, or pasted text. Quality
   must be adequate for source-span verification.
3. **The schema.** `schema/dimensions.md` and
   `schema/genetic_evidence.shacl.ttl`.
4. **The protocol documents.** `protocols/PROTOCOL.md` (the
   annotation protocol; needed to assess whether the annotation
   conforms), `protocols/LABELING_EXAMPLES.md` (for label-style checks),
   `schema/EXTENSIONS.md` (for candidate-extension de-duplication),
   `notes/ROADMAP.md` (the migration roadmap) (for migration-suggestion targets).

If any input is missing, the AI asks for it and stops. It does
not proceed with guesses.

---

## 3. Workflow

The session has four phases. The AI walks the curator through
them in order, maintaining explicit state between turns.

### 3.1 Phase 0: setup and orientation

The AI:

1. Confirms the inputs (annotation, paper, schema location).
2. Reads the annotation and the schema.
3. Performs structural validation per `REVIEW_PROTOCOL.md` §2.1,
   including the check for invented non-schema keys (§2.1.1). Any
   structural issue is surfaced immediately. If the annotation is
   structurally invalid (e.g., un-parseable YAML), the AI reports
   this and asks the curator whether to proceed with a partial
   review or abort.
4. **Sets the protocol-version baseline** (`REVIEW_PROTOCOL.md`
   §2.4). The AI reads the annotation's production version from its
   `provenance` (`annotation_production_protocol`); if absent, it
   asks the curator. It then states the baseline in one line, for
   example: "This annotation was produced under protocol v0, so
   v1.0-only requirements (the `confidence_summary`, the full
   `provenance` block, conditional-activation strictness, the
   hierarchical `method` dimension) will be recorded as
   forward-notes, not defects." The version is recorded in the log
   as `annotation_production_protocol`.
5. **Sets session rulings** (`REVIEW_PROTOCOL.md` §4.1
   `session_rulings`). The AI asks once, in a single short prompt:
   "Any governing conventions to set before we start?" The AI may
   also propose a ruling if it anticipates a recurring call (for
   example: "this corpus repeatedly hits the human-genetics vs
   population-genetics distinction; shall we fix a rule?"). Each
   ruling gets an `id` (SR-1, SR-2, ...), a `topic`, the `ruling`
   text, and optional `pre_cleared` ids or a `note`. Rulings apply
   session-wide; later phases honour them rather than re-asking.
6. Reads the paper at a level sufficient to begin Phase 1.
7. Tells the curator: "I have read the annotation (<n> GE items)
   and the paper, set the v<x> baseline, and recorded <k> session
   rulings. I will now check for missing evidence before reviewing
   the existing items. Ready to proceed?"

The curator confirms; the session moves to Phase 1. Keep Phase 0
lightweight: the baseline is one line and the rulings prompt is a
single question, not a checklist.

### 3.2 Phase 1: missing-evidence check

Per `REVIEW_PROTOCOL.md` §5.

The AI:

1. Presents a table summarising the annotation's existing GE
   items, one row per item:

   ```
   | id   | label                      | method               |
   | ---- | -------------------------- | -------------------- |
   | GE-1 | rs11209026 protects vs CD  | GWAS                 |
   | GE-2 | CARD15 markers in same scan| GWAS                 |
   ...
   ```

2. Asks the curator: "Before we review these, do you see any
   evidential claims in the paper that aren't captured here?
   I can also propose candidates if you'd like."

3. If the curator wants AI proposals: the AI reviews the paper
   afresh and proposes candidate missed items, each with:
   - A brief description.
   - A source-span pointing to the motivating passage.
   - A level-of-confidence indicator (high if the omission is
     obvious, low if the AI is uncertain).

4. For each curator-proposed or AI-proposed missing item, the
   curator decides:
   - **Accept:** the item is added to the per-item review queue
     with a temporary id (`GE-new-1`, `GE-new-2`, ...) and will
     be reviewed in Phase 2.
   - **Reject:** the item is recorded as considered-and-declined
     in the review log under `phase_1_rejected_candidates`.
   - **Defer:** the item is parked; the AI will mention deferred
     items at the end of the session.

5. When the curator confirms no further missing items are to be
   added, the AI summarises: "We will review <n_existing>
   existing items and <n_added> newly accepted items, for a
   total of <total> items. Proceeding to per-item review."

### 3.3 Phase 2: per-item review

Per `REVIEW_PROTOCOL.md` §6.

For each item (existing + newly accepted), the AI:

1. **Performs the three-level analysis** per
   `REVIEW_PROTOCOL.md` §2:
   - Structural: are all fields present and well-typed? Are there
     any invented non-schema keys (§2.1.1)? An invented key is a
     structural defect to remove, with the underlying gap routed to
     a `candidate_extension`.
   - Consistency: do source spans appear verbatim in the paper?
     Classify any span defect by the severity tiers in
     `REVIEW_PROTOCOL.md` §2.2.1 (blocking vs non-blocking). Are
     dimension assignments internally coherent? Is the item label
     an evidential statement per `PROTOCOL.md` §2.4? Are candidate
     extensions de-duplicated against `EXTENSIONS.md`?
   - Evidential: does the item fairly summarise the paper's
     claim at the cited passages? Are dimension values
     appropriate? Per `notes/ROADMAP.md` (the migration roadmap), is the method value
     a candidate for leaf-value migration?

   For AI-drafted annotations that **strain** the model (typical of
   polygenic-score or other structurally novel papers), the edit
   signal may not be the `ai_uncertainty` / `ai_assumption` flags:
   such annotations can carry few or no uncertainty flags yet many
   candidate extensions and forced fits. In that case do not rely on
   uncertainty flags as the signal; scrutinise the candidate
   extensions and forced fits directly, and confirm each forced fit
   is logged as a candidate extension.

2. **Presents the item** to the curator with:

   ```
   ## GE-3: <label>

   Method: <method values>
   Phenotype scale: <value>
   Target: <target> (<target_type>, <resolution>)
   <other non-default fields>

   Source spans: <n> assertions, all source-anchored.

   <If any analysis surfaced issues, list them here under
   level headings: Structural, Consistency, Evidential. Each
   issue is one to three sentences with the relevant passage.>

   <If migration suggestion applies (e.g., method:
   STATISTICAL_GENETICS → GWAS), note it explicitly:
   "Migration suggestion: method could be migrated to
   leaf-level value GWAS per the migration roadmap in `notes/ROADMAP.md`.">
   ```

3. **Asks for verdict.** Two presentations:

   - **If no issues were surfaced**, the prompt is:

     > "GE-3 looks clean. Approve as a whole / Reject / Edit
     > before approval?"
     >
     > Recommendation: Approve as a whole.

   - **If issues were surfaced**, the prompt is:

     > "GE-3 has <n> flagged points (see above). Approve
     > despite flags / Reject / Edit?"
     >
     > Recommendation: Edit.

4. **Records the verdict** in the in-session state. If the
   curator chose **Edit**, the AI asks a follow-up: "What
   should be changed?" and records the answer as
   `verdict.notes`. The verdict's `flags_recorded` field
   captures any new `reviewer_disagreement`,
   `reviewer_suggestion`, or `reviewer_query` flags the curator
   accumulates for this item.

5. **Moves to the next item.** The AI restates progress at
   regular intervals (every 3-5 items, or at the curator's
   request): "We have reviewed <n> of <total> items.
   Approved: <n>. Rejected: <n>. Marked for edit: <n>."

### 3.4 Phase 3: paper-level observations and promotion check

Some observations do not belong to a specific GE item:

- The annotation's overall provenance block is incomplete.
- A candidate extension applies across multiple items.
- The paper's bibliography points to a related work the
  annotation could profitably cite.

The AI surfaces these after per-item review is complete. Each
becomes an entry in the review log's `observations` list (not
under a specific `ge_item`).

The curator approves or rejects each.

**Two-papers promotion check.** Also in this phase, for each
candidate extension surfaced in this review or already present in the
annotation, the AI checks both `schema/EXTENSIONS.md` **and** the
other corpus annotations for an independent second occurrence. If a
second independent occurrence exists, the candidate is eligible for
promotion under the two-papers rule (`protocols/PROTOCOL.md` §5.2);
the AI records a **promotion recommendation** (a `reviewer_suggestion`
with `subcategory: promotion`, or a paper-level observation). The
reviewer only records the recommendation: applying a promotion (edits
to `schema/dimensions.md`, the SHACL schema, and
`schema/EXTENSIONS.md`) is a separate workflow. De-duplicate against
the **current** `EXTENSIONS.md`; if a candidate from an earlier
review (for example the Duerr CE-DU3 / CE-DU4) has not yet been logged
there, note that as a prerequisite rather than re-deriving it here.

### 3.5 Phase 4: emit artefacts

The AI:

1. Generates the YAML review log per `REVIEW_PROTOCOL.md` §4.1.
2. Generates the markdown review report per
   `REVIEW_PROTOCOL.md` §4.2.
3. Generates the **updated annotation** per `REVIEW_PROTOCOL.md`
   §4.3: the source annotation with the curator-approved verdicts
   applied (agreed edits on `marked_for_edit` items, removals of
   `rejected` items, additions accepted in Phase 1, removal of
   invented non-schema keys with the gap routed to a candidate
   extension, and a `provenance.review_applied` entry). Items
   approved or approved-despite-flags are left as-is. Curator-
   endorsed migrations are applied; promotions are not.
4. Determines whether a second-round review is recommended
   per `REVIEW_PROTOCOL.md` §7 (items added in Phase 1; many
   `marked_for_edit` verdicts; cross-cutting issues).
5. Presents the three artefacts and the second-round recommendation
   to the curator.
6. Asks the curator where to save them. The convention is:
   - Log: `annotations/reviews/<paper-id>-review-<YYYY-MM-DD>.yaml`
   - Report: `annotations/reviews/<paper-id>-review-<YYYY-MM-DD>.md`
   - Updated annotation: by default a sidecar,
     `annotations/<paper-id>.reviewed-<YYYY-MM-DD>.yaml`; it
     replaces the source `annotations/<paper-id>.yaml` only on
     explicit curator confirmation.

   (The `annotations/reviews/` directory may not yet exist; the AI
   asks before creating it.)
7. Notes any downstream artefacts the applied edits affect (the
   per-paper case report, `annotations/coverage.md`, and any paper
   numbers), to be reconciled by the relevant sync workflow rather
   than in this session.
8. Asks: "Review complete. Anything else before we end the
   session?"

---

## 4. State management

The interactive workflow can be long. The AI maintains explicit
state and resurfaces it on request.

State includes:

- **Phase**: 0 (setup), 1 (missing-evidence), 2 (per-item), 3
  (paper-level), 4 (emit).
- **Item queue**: existing GE items + newly accepted items,
  in review order. Each item has a status (pending, in-review,
  reviewed).
- **Verdicts so far**: a running list of {ge_item, decision,
  flags_recorded, notes} tuples.
- **Phase 1 rejected/deferred candidates**: for inclusion in
  the final log.
- **Observations**: paper-level issues collected for Phase 3.
- **Migration suggestions**: collected across items for the
  log's `migration_suggestions` section.

The curator may ask "where are we?" at any time. The AI
responds with the current phase, the items reviewed so far,
the items remaining, and a brief summary of accumulated
verdicts.

The curator may ask to revisit an item already reviewed. The
AI updates the verdict.

The curator may ask to abort. The AI offers to emit a partial
review log marked as `incomplete: true`, or to discard the
session entirely.

---

## 5. Invariants

After the session, the AI verifies:

- **The protocol-version baseline is set and recorded** in the log
  as `annotation_production_protocol`, and no post-baseline rule was
  charged as a blocking defect.
- **Every existing GE item has a verdict.** No implicit
  approvals.
- **Every newly added GE item (from Phase 1) has a verdict.**
- **Every observation is associated with either a GE item or
  the paper-level set.** No orphan observations.
- **Source-span verbatim checks have been performed** for every
  assertion in every item, and each span defect is classified by
  the §2.2.1 severity tiers.
- **Migration suggestions are populated** for items whose
  method or other dimension values are at intermediate-level
  under the current hierarchy.
- **The two-papers promotion check has been run** against
  `schema/EXTENSIONS.md` and the other annotations, with any
  eligible candidate recorded as a promotion recommendation.
- **The updated annotation reflects exactly the curator-approved
  verdicts** (no edit that was not approved; no approved edit
  omitted) and carries a `provenance.review_applied` entry.

If any invariant fails, the AI reports it and offers to
correct before emitting.

---

## 6. Failure handling

If the AI cannot conduct a useful review, it stops and
explains why. Specific refusal conditions:

- **The annotation is severely malformed.** Cannot be parsed
  or has so many structural issues that per-item review is
  meaningless. The AI offers to do a structural-only review
  and stop.
- **The source paper is unavailable or unreadable.** Without
  the paper, source-span and evidential checks are
  impossible; only structural and consistency-against-schema
  checks can be performed. The AI offers to do a
  schema-only review and stop.
- **The annotation is for a paper outside the protocol's
  scope** (review article, methods paper, non-genetics
  publication). The AI flags this as the primary observation
  and asks the curator whether to proceed.

The curator may always override and ask the AI to continue.
The AI will, with explicit caveats recorded in the review log.

---

## 7. What this protocol does not do

- It does not silently overwrite the source annotation. It emits a
  proposed updated annotation as a third artefact (§3.5 step 3,
  `REVIEW_PROTOCOL.md` §4.3) that applies only curator-approved
  verdicts; writing it over the source `annotations/<paper-id>.yaml`
  requires explicit curator confirmation.
- It does not reconcile downstream artefacts. Numbers the edits move
  in the case report, `annotations/coverage.md`, or the paper are
  left to the relevant sync workflow.
- It does not validate against the SHACL schema in a formal
  sense. The structural check is best-effort; full SHACL
  validation is a separate pipeline step.
- It does not maintain a corpus-wide tally. The review covers
  one annotation per session. Cross-corpus analysis is out of
  scope.
- It does not emit any flags the annotator might have emitted
  (`ai_uncertainty`, `ai_assumption`, `ai_normalization`).
  Those are annotator-emitted; the reviewer emits the
  `reviewer_*` vocabulary only.
-
