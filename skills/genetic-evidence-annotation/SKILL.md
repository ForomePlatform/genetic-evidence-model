---
name: genetic-evidence-annotation
description: Produce a YAML annotation of a genetics paper under the Genetic Evidence Model (GEM) schema. Use when the user asks to annotate, parse, or extract structured evidence from a genetics, model-organism, population-genetics, or polygenic-score publication, especially when they reference the GEM schema, the ForomePlatform/genetic-evidence-model repository, or files like dimensions.md, EXTENSIONS.md, or existing annotations in annotations/. Triggers on phrases like "annotate this paper with GEM", "produce a GEM annotation", "extract GeneticEvidence items", or "draft an annotation under the genetic-evidence model".
version: 1.1.1
---

# Genetic Evidence Model annotation

A skill for producing autonomous YAML annotations of genetics
papers under the GEM schema, following the protocol documented in
`protocols/PROTOCOL.md` and `protocols/PROTOCOL_AUTONOMOUS.md`.

This skill (v1.1.1) targets **GEM schema v1.1** and **PROTOCOL v1.1**.
The v1.1 schema machine-checks the always-required dimensions, the value
enumerations, and a mandatory `source_span` on every assertion; output
should conform to `schema/genetic_evidence.shacl.ttl` (validate with
`scripts/validate_annotations.py`).

## What this skill does

This skill produces a single YAML file that annotates one paper
under the Genetic Evidence Model schema. The output matches the
format of the existing annotations in the
`ForomePlatform/genetic-evidence-model` repository. The four
curator-led annotations (Jossin 2017, Davis 2011, Nelson 1992,
Gupta 2015) are the canonical exemplars: they are the
ground-truth applications of the schema by a human domain expert.

The skill operates in **autonomous mode only**: a single pass
that produces a complete annotation without a curator in the
loop. Future versions may add an interactive mode; for now,
interactive annotation is out of scope.

## Always ask first

Before doing any annotation work, the skill confirms three
inputs with the user. It does not assume.

1. **Which paper?** A file path to the PDF or HTML, or a URL.
2. **Where should the output go?** A target path. The
   convention is `annotations/<paper-id>.yaml` where
   `<paper-id>` is lowercase first-author surname plus
   publication year (e.g., `smith2024`). Confirm this convention
   or accept an override.
3. **Where is the schema?** The skill needs to read
   `schema/dimensions.md` and at least one prior annotation as
   exemplar. By default it looks in the current working directory
   for these paths. Confirm or override.

If the user has not provided a paper, the skill asks for one and
stops. It does not invent a paper to annotate.

## What this skill does not do

- It does not interact with the user during annotation. Inputs
  are gathered upfront; the annotation runs to completion
  without further questions.
- It does not produce case reports. Case reports are a separate
  downstream artefact.
- SHACL validation is a separate, optional step. The bundle ships the
  canonical validator: after `pip install pyshacl rdflib pyyaml`, run
  `python scripts/validate_annotations.py <annotation>.yaml` to check the
  output against `schema/genetic_evidence.shacl.ttl`. Do not hand-roll the
  YAML-to-RDF mapping; `scripts/yaml_to_rdf.py` is authoritative.
- It does not modify the schema or `EXTENSIONS.md`. Candidate
  extensions are emitted in the annotation but schema changes
  require human action (per `protocols/PROTOCOL.md` section 5.2).
- It does not handle papers outside the GEM scope (review
  articles, methods-only papers, non-genetics papers, papers in
  languages other than English). If the paper is out of scope,
  the skill refuses and explains why.

## Workflow

The skill follows `protocols/PROTOCOL_AUTONOMOUS.md` exactly. The high-level
phases are:

1. **Read inputs.** The paper, the schema, the exemplar
   annotations. Verify input quality. If the PDF text is poor or
   the paper is out of scope, refuse and explain.
2. **Decompose.** Produce a list of `GeneticEvidence` items
   following the lumper default rule in `protocols/PROTOCOL.md` section 2.
   Self-consistency-check before committing.
3. **Annotate.** For each GE item, fill in dimensions, source
   spans, candidate extensions, normalisation notes, and
   annotator-emitted flags per `protocols/PROTOCOL.md` sections 3, 4, and 6.
4. **Verify.** Run the self-consistency invariants listed in
   `protocols/PROTOCOL_AUTONOMOUS.md` section 5. Correct violations.
5. **Emit.** Write the YAML to the target path. Include the
   mandatory `provenance` and `confidence_summary` blocks per
   `protocols/PROTOCOL_AUTONOMOUS.md` sections 3.6 and 3.7.

## Reading order

When invoked, read these files in this order before starting:

1. `protocols/PROTOCOL.md` (the mode-agnostic rules)
2. `protocols/PROTOCOL_AUTONOMOUS.md` (the autonomous workflow)
3. `schema/dimensions.md` (the dimension reference)
4. `schema/genetic_evidence.shacl.ttl` (the formal schema)
5. The four curator-led annotations as exemplars:
   `annotations/jossin2017.yaml`, `annotations/davis2011.yaml`,
   `annotations/nelson1992.yaml`, `annotations/gupta2015.yaml`.
   These are the ground-truth applications of the schema.
   Do not use prior AI-drafted annotations as exemplars: they
   are the same kind of output this skill produces, and using
   them as templates would propagate any weaknesses they carry.
6. `schema/EXTENSIONS.md` (to avoid duplicating already-surfaced
   candidate extensions)

If any of these files is missing from the working directory, the
skill asks the user where to find it. It does not proceed with
guesses.

## Failure modes

Per `protocols/PROTOCOL_AUTONOMOUS.md` section 6, the skill refuses (rather
than producing best-effort output) when:

- The paper text quality is inadequate.
- The paper is out of scope for the GEM schema.
- Schema gaps are pervasive (more candidate extensions than
  populated dimensions).
- The self-consistency invariants cannot be satisfied.

A refusal is a short report explaining the issue and suggesting
an alternative.

## Output structure

The output YAML must contain:

- `publication`: paper metadata (title, authors, year, DOI).
- `provenance`: mode, protocol version, annotator identifier,
  timestamp, exemplars used.
- `evidence`: the list of `GeneticEvidence` items, each with
  dimensions, assertions, and per-item flags.
- `candidate_extensions`: schema gaps surfaced during this
  annotation.
- `flags`: annotator-emitted flags (`ai_uncertainty`,
  `ai_assumption`, `ai_normalization`) referenced from the
  appropriate evidence items.
- `confidence_summary`: the mandatory end-of-annotation
  self-assessment.

Match the structure of existing annotations in the repository
exactly. Do not invent new top-level keys.

## When the user has not yet decided autonomous vs interactive

If the user's request is ambiguous about mode, ask once: "Do
you want autonomous mode (a single complete annotation, no
curator review during the process) or interactive mode (staged
annotation with curator review of the decomposition before
filling in details)?"

If the user picks interactive, this skill does not handle it;
inform them and stop. Interactive mode is planned but not yet
specified.

If the user picks autonomous, proceed.

## Related documents

- `protocols/PROTOCOL.md`: canonical, mode-agnostic protocol rules.
- `protocols/PROTOCOL_AUTONOMOUS.md`: the operational workflow this skill
  implements.
- `schema/dimensions.md`: human-readable dimension reference.
- `annotations/`: exemplar annotations and source of truth for
  the existing corpus.
- The companion paper "A Semantic Model of Genetic Evidence"
  (ICBO 2026) for the conceptual background.
