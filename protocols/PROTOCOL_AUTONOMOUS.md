# PROTOCOL_AUTONOMOUS.md

Operational workflow for **autonomous AI annotation** under the
Genetic Evidence Model.

This document specifies how an AI assistant, with no curator in
the loop, produces a YAML annotation of a single paper. It
references `protocols/PROTOCOL.md` for substantive rules (decomposition,
dimension assignment, source anchoring, candidate extensions,
flag taxonomy); this document covers only what is specific to
autonomous mode.

**Audience:** AI assistants executing this protocol, and
researchers who need to understand what guarantees an autonomous
annotation carries.

---

## 1. When to use autonomous mode

Autonomous mode is appropriate when:

- A curator is not available, or the volume of papers makes
  per-paper curator review impractical.
- The annotation will receive a downstream review pass before
  consumption (in which case the autonomous output is a draft).
- The annotation is being used for purposes that tolerate
  AI-emitted flags as substitutes for curator judgement.

Autonomous mode is **not** appropriate when:

- The annotation must be treated as ground truth from the moment
  it is produced.
- The paper is in a domain (e.g., disease the AI has little
  exposure to) where the AI's calibration is uncertain.
- The output will be used for clinical decision-making without
  any subsequent review.

For these cases, use the interactive protocol (when available)
or a manual annotation.

---

## 2. Inputs

The AI assistant requires:

1. **The paper.** A PDF or HTML article. Text quality must be
   adequate (see section 3.1).
2. **The schema.** `schema/dimensions.md` and
   `schema/genetic_evidence.shacl.ttl`.
3. **Exemplar annotations.** At least one prior annotation in the
   repository's `annotations/` directory, used to ground the AI's
   sense of corpus conventions. The four curator-led annotations
   (Jossin 2017, Davis 2011, Nelson 1992, Gupta 2015) are the
   canonical exemplars: they are the ground-truth applications of
   the schema by a human domain expert. Existing AI-drafted
   annotations should not be used as exemplars when producing
   further AI-drafted annotations, because using past output of
   this protocol as a template for new output would propagate any
   weaknesses it carries.

Optionally:

4. **The candidate-extensions log** (`schema/EXTENSIONS.md`) so
   the AI does not propose extensions that have already been
   surfaced.

---

## 3. Workflow

### 3.1 Input quality check

Before any annotation work, the AI verifies the paper text is of
adequate quality:

- The PDF text extracts cleanly. No widespread OCR artefacts.
- Tables, figures, and equations are referenced in the
  surrounding prose well enough that their contribution is
  parseable.
- The paper is in English (the corpus is English-only at this
  time).

If quality is inadequate, the AI **stops and reports the
issue** (see section 6). It does not attempt a best-effort
annotation on degraded input.

### 3.2 Decomposition

The AI produces a list of GE items following the lumper default
rule in `protocols/PROTOCOL.md` section 2. For each item, the AI records:

- An identifier (`GE-1`, `GE-2`, ...).
- A one-sentence label.
- (Internal, not in output) Whether decomposition alternatives
  were considered and rejected.

**Self-consistency check:** before committing the decomposition,
the AI re-reads its own list and asks:

- Do any two items duplicate evidence?
- Does any item bundle claims with differing methods, targets,
  or credibilities?
- Are there evidential claims in the paper that no item covers?

If any check fails, the AI revises the decomposition before
proceeding.

### 3.3 Dimension assignment

For each GE item, the AI populates dimensions per `protocols/PROTOCOL.md`
sections 3 and 6.

**No silent decisions.** Every choice that involves a judgement
call is flagged. The autonomous protocol's invariant: a curator
reading the annotation after the fact must be able to identify
every place the AI was uncertain or made an assumption. If a
choice required judgement and is not flagged, the protocol has
been violated.

### 3.4 Source-span extraction

For each `GeneticEvidenceAssertion`, the AI extracts a
`source_span` per `protocols/PROTOCOL.md` section 4. The AI verifies that
the verbatim phrase appears in the source text before emitting
it. (Verbatim verification is the autonomous protocol's
substitute for curator review of source anchoring.)

### 3.5 Candidate-extension emission

When the schema enumeration genuinely does not fit, the AI emits
a `candidate_extension` block per `protocols/PROTOCOL.md` section 3.3 and
section 5. The candidate-extension threshold in autonomous mode
is the same as for any other mode: **every forced fit must
generate a candidate extension**. There is no informal "I'll let
this one slide" option.

### 3.6 Provenance recording

The AI records in the annotation's `provenance` block:

- `mode: autonomous`
- `protocol_version: 1.0` (or current)
- `annotator: <model identifier>` (e.g., `claude-opus-4-7`)
- `annotated_at: <ISO 8601 timestamp>`
- `exemplars_used: [<list of paper IDs whose annotations were
  consulted>]`

### 3.7 Confidence summary

Before emitting the final YAML, the AI produces a
**confidence summary** appended to the annotation. This is the
autonomous protocol's permanent record of what the AI was sure
and unsure about. Format:

```yaml
confidence_summary:
  overall: high | medium | low
  decomposition_confidence: high | medium | low
  per_item:
    - id: GE-1
      confidence: high | medium | low
      notes: <optional brief explanation if not high>
    - id: GE-2
      ...
  forced_fits:
    - dimension: <name>
      ge_items: [GE-1, GE-3]
      candidate_extension: CE-<id>
  decomposition_alternatives_considered:
    - description: <e.g., "considered splitting GE-2 into
      a discovery-vs-replication pair">
      reason_rejected: <e.g., "credibility identical; lumper rule applies">
```

The confidence summary is mandatory in autonomous mode. An
annotation without it is incomplete.

---

## 4. Output

The output is a single YAML file matching the structure of the
existing annotations in `annotations/` (see the four curator-led
annotations: Jossin, Davis, Nelson, Gupta). The file should be placed at
`annotations/<paper-id>.yaml` where `<paper-id>` follows the
existing convention (lowercase first-author surname + year, e.g.,
`smith2024`).

If a corresponding case report is desired, it is **not** produced
by the autonomous skill; case reports are a separate downstream
artefact and are out of scope for this protocol.

---

## 5. Self-consistency invariants

After producing the annotation, the AI verifies:

- **Every GE item has all always-required dimensions populated.**
- **Every assertion has a `source_span`.**
- **Every `source_span` phrase is under 15 words.**
- **Every forced fit has a corresponding candidate extension.**
- **No candidate extension overlaps with an already-promoted
  schema feature** (consult `schema/EXTENSIONS.md`).
- **The confidence summary covers every GE item.**

If any invariant fails, the AI corrects before emitting.

---

## 6. Failure handling

If the AI cannot produce a usable annotation, it **refuses and
explains why**. It does not produce a partial or best-effort
annotation in autonomous mode.

Specific refusal conditions:

- **Input quality inadequate** (PDF OCR artefacts, non-English,
  unparseable structure).
- **Paper outside the schema's intended scope** (e.g., review
  article, non-genetics paper, methods-only paper without
  evidential claims).
- **Schema gaps are pervasive** (the paper is so far from
  anything the schema accommodates that emitting candidate
  extensions for every dimension would be more noise than signal).
- **Self-consistency invariants cannot be satisfied** (the AI
  produced an annotation but cannot make it internally consistent
  after multiple revisions).

Refusal output: a short report (one or two paragraphs)
describing the issue and suggesting an alternative (manual
annotation, interactive mode, schema extension before
attempting).

---

## 7. What this protocol does not do

- It does not validate against the SHACL schema. SHACL validation
  is a separate step run by the curator or by a CI pipeline.
- It does not produce case reports. Case reports are downstream
  human-written artefacts.
- It does not interact with the user during annotation. Any input
  is gathered upfront (see the skill specification).
- It does not consume or emit `reviewer_*` flags. Those belong to
  the (future) interactive and review protocols.
-
