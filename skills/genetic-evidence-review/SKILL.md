---
name: genetic-evidence-review
description: Review an existing YAML annotation of a genetics paper under the Genetic Evidence Model (GEM) schema in interactive dialogue with the curator. Use when the user asks to review, audit, evaluate, or curate a GEM annotation; when the user has an annotation YAML file and wants a structured second opinion; when the user mentions reviewing AI-drafted or manually-authored annotations against the schema and the source paper. Triggers on phrases like "review this annotation", "curate this GEM YAML", "audit the genetic-evidence annotation", "let's go through this annotation item by item", or "review the annotation of the paper".
---

# Genetic Evidence Model annotation review

A skill for interactive review of a GEM annotation, in dialogue
with a curator. Implements the protocol documented in
`protocols/REVIEW_PROTOCOL.md` and
`protocols/REVIEW_PROTOCOL_INTERACTIVE.md` at the repository
root.

## What this skill does

This skill conducts a multi-turn review session in which:

1. The AI reads the annotation YAML, the source paper, and the
   schema.
2. The AI proposes potentially missed evidence (the
   missing-evidence check) and the curator decides what to add.
3. The AI walks through each GE item in turn, surfacing
   structural, consistency, and evidential observations, and
   the curator decides to approve, reject, or mark for edit.
4. The AI surfaces paper-level observations not tied to a
   specific item, and runs the two-papers promotion check
   against the other annotations.
5. The AI emits three artefacts: a YAML review log, a markdown
   review report, and the updated annotation YAML (the source
   with the curator-approved edits applied).

The skill is **interactive**: the conversation drives the
review. The AI presents one or a few items at a time, the
curator responds, the AI moves forward. State is tracked
explicitly so a long session does not lose the thread.

The skill works on any annotation regardless of provenance:
AI-drafted, manually authored, or hybrid. The annotation's
`provenance.mode` field informs the AI what to expect but does
not change the substantive review rules.

## Always ask first

Before doing any review work, the skill confirms inputs with
the curator. It does not assume.

1. **Which annotation?** A file path to the YAML, or pasted
   content.
2. **Which source paper?** A file path (PDF or HTML) or pasted
   text. The skill needs the paper to verify source spans and
   to detect missed evidence.
3. **Where should the review artefacts be saved?** The
   convention is `annotations/reviews/<paper-id>-review-<YYYY-MM-DD>.yaml`
   (log) and `annotations/reviews/<paper-id>-review-<YYYY-MM-DD>.md`
   (report). The updated annotation defaults to a sidecar,
   `annotations/<paper-id>.reviewed-<YYYY-MM-DD>.yaml`, and replaces
   the source only on explicit confirmation. The skill asks before
   creating the `annotations/reviews/` directory.

If any input is missing, the skill asks for it and waits. It
does not invent annotations to review or papers to compare
against.

## Reading order

When invoked, read these files in this order before the
session begins:

1. `protocols/REVIEW_PROTOCOL.md` (the canonical review rules)
2. `protocols/REVIEW_PROTOCOL_INTERACTIVE.md` (the interactive
   workflow this skill implements)
3. `protocols/PROTOCOL.md` (the annotation protocol; needed to
   assess whether the annotation conforms to its own rules)
4. `protocols/LABELING_EXAMPLES.md` (for label-style checks per
   `PROTOCOL.md` §2.4)
5. `schema/dimensions.md` (the dimension reference)
6. `schema/genetic_evidence.shacl.ttl` (the formal schema)
7. `schema/EXTENSIONS.md` (so candidate extensions can be
   de-duplicated against already-known ones)
8. `notes/ROADMAP.md` (so migration suggestions can be
   populated for items at intermediate-hierarchy values)
9. The other corpus annotations in `annotations/` (consulted in
   Phase 3 for the two-papers promotion check: a candidate with an
   independent second occurrence becomes a promotion
   recommendation)

If any of these is missing from the working directory, the
skill asks the curator where to find it. It does not proceed
with guesses.

## What this skill does not do

- It does not silently overwrite the source annotation. It emits
  an updated annotation as a third artefact (the source with the
  curator-approved edits applied); replacing
  `annotations/<paper-id>.yaml` needs explicit curator
  confirmation.
- It does not re-annotate from scratch. The updated annotation
  carries only curator-approved review edits; for a fresh
  annotation use the `genetic-evidence-annotation` skill.
- It does not reconcile downstream artefacts (case report,
  `annotations/coverage.md`, paper numbers) the edits move; those
  go to the relevant sync workflow.
- It does not apply candidate-extension promotions to the schema;
  it only records promotion recommendations.
- It does not validate against SHACL in a formal sense.
  Structural checks are best-effort.
- It does not silently approve. Every GE item gets an explicit
  curator verdict, even when the AI has no concerns.
- It does not emit annotator flags (`ai_uncertainty`,
  `ai_assumption`, `ai_normalization`). Those are
  annotator-emitted. The reviewer emits the `reviewer_*`
  vocabulary only.

## Workflow at a glance

Per `REVIEW_PROTOCOL_INTERACTIVE.md`:

**Phase 0**: confirm inputs; read annotation, paper, protocols
and schema; do structural validation (including the check for
invented non-schema keys). Then set the **protocol-version
baseline** (state once that rules newer than the annotation's
production version are forward-notes, not defects) and ask once for
any **session rulings** (governing conventions recorded for the
whole session). Keep both lightweight.

**Phase 1**: missing-evidence check. Show existing items as a
table; ask the curator if any evidence is missed. Optionally,
propose AI-detected candidates. Curator accepts, rejects, or
defers each. Accepted items join the review queue.

**Phase 2**: per-item review. For each GE item (existing +
newly added):
- AI surfaces observations (structural, consistency,
  evidential), classifying source-span defects by the blocking
  vs non-blocking severity tiers. For model-straining AI-drafted
  annotations with few or no uncertainty flags, the edit signal is
  the candidate extensions and forced fits, not the flags.
- AI presents the item with any flags.
- AI asks for verdict:
  - **No issues surfaced**: Approve as a whole / Reject / Edit
    before approval. Recommendation: Approve as a whole.
  - **Issues surfaced**: Approve despite flags / Reject / Edit.
    Recommendation: Edit.
- Curator decides. If Edit, AI asks "what should be changed?"
  and records the answer.

**Phase 3**: paper-level observations (cross-cutting issues not
tied to a specific item) and the **two-papers promotion check**
(for each candidate extension, check `schema/EXTENSIONS.md` and the
other annotations for an independent second occurrence; record any
eligible one as a promotion recommendation only).

**Phase 4**: emit three artefacts: YAML log, markdown report, and
the updated annotation YAML (source + curator-approved edits, saved
to a sidecar by default; replacing the source needs explicit
confirmation). Recommend a second-round review if items were added
in Phase 1 or many edits accumulated.

## State maintenance

The AI maintains explicit state across turns:

- **Phase** (0 through 4).
- **Item queue** with status per item (pending, in-review,
  reviewed).
- **Verdicts collected so far.**
- **Observations collected so far.**
- **Migration suggestions collected.**

The curator may ask "where are we?" at any time; the AI
responds with the current phase, items reviewed, items
remaining, and a verdict summary.

The curator may revisit an item already reviewed; the AI
updates the verdict.

The curator may pause or abort; the AI offers to save a
partial review log marked `incomplete: true`, or to discard.

## Output

Three artefacts, per `REVIEW_PROTOCOL.md` §4:

1. **YAML review log** with per-item verdicts, observations,
   `session_rulings`, `annotation_production_protocol`, migration
   suggestions, promotion recommendations, second-round
   recommendation.
2. **Markdown review report** generated from the log;
   human-readable narrative suitable for sharing.
3. **Updated annotation YAML**: the source annotation with the
   curator-approved verdicts applied (agreed edits, removals,
   Phase-1 additions, invented-key removals routed to candidate
   extensions, a `provenance.review_applied` entry). Saved to a
   sidecar by default; replacing `annotations/<paper-id>.yaml`
   requires explicit curator confirmation.

The log is the authoritative artefact. The report is derivative and
may be regenerated from the log. The updated annotation applies
only what the log's verdicts approved.

## Failure modes

Per `REVIEW_PROTOCOL_INTERACTIVE.md` §6, the skill stops and
explains when:

- The annotation is severely malformed (offers structural-only
  review).
- The source paper is unavailable (offers schema-only review).
- The annotation is for a paper outside the protocol's scope
  (flags this as the primary observation; asks how to proceed).

The curator may always override and ask the AI to continue,
with explicit caveats recorded in the review log.

## On reviewing AI-drafted vs manual annotations

The protocol is mode-agnostic by design. The same rules apply
to all annotations. However, the AI's expectations differ:

- For AI-drafted annotations (`provenance.mode: autonomous`):
  expect `ai_uncertainty` and `ai_assumption` flags from the
  annotator; treat them as annotator-flagged items deserving
  curator attention. These often correlate with items needing
  Edit verdicts. **Exception, model-straining papers:** an
  AI-drafted annotation of a structurally novel paper (a polygenic
  score, for instance) may carry few or no uncertainty flags yet
  many candidate extensions and forced fits, because it expresses
  strain as "the model is missing a feature" rather than "I am
  unsure which value applies." Do not rely on uncertainty flags as
  the edit signal there; scrutinise the candidate extensions and
  forced fits, and confirm each forced fit is logged as a
  candidate.
- For manual annotations (`provenance.mode` absent or
  `manual`): no AI flags; the review is the first AI
  inspection of the work. Be especially careful with the
  evidential level; the human curator may have made
  context-aware judgements the AI should respect.
- For hybrid annotations: read the provenance carefully and
  attend to which parts were AI-emitted vs human-edited.

In all cases, the curator's verdict in this session is
authoritative.

## Related documents

- `protocols/REVIEW_PROTOCOL.md`: canonical review rules.
- `protocols/REVIEW_PROTOCOL_INTERACTIVE.md`: the operational
  workflow this skill implements.
- `protocols/PROTOCOL.md`: the annotation protocol the
  annotations under review were produced against.
- `protocols/LABELING_EXAMPLES.md`: label-style reference.
- `schema/dimensions.md`: human-readable dimension reference.
- `schema/EXTENSIONS.md`: candidate-extensions log.
- `notes/ROADMAP.md`: expected leaf-value migrations.
-
