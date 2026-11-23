# Pre-tag deviations and out-of-protocol events

Events before the study tag that bear on the evaluation study
(`protocols/EVALUATION_PROTOCOL.md`). Reviewed when the tag is assembled;
events affecting papers that remain in the study are carried into
`study/AMENDMENTS.md` as pre-existing deviations.

## D-pre-1 (2026-10-11): Study-lead AI-assisted review of an annotator draft

- Paper: Marques et al. 2025, J. Psychiatry Neurosci. 50:E323–E333
  (doi:10.1139/jpn-25-0017); approved stress-stratum paper, first exercise
  of `EPIGENETICS`.
- The study lead reviewed the annotator's draft with AI assistance
  (claude.ai session, Claude Fable 5), outside every review route defined in
  §8 (not SR, WR, or RH). §8.1 binds the annotator, not the study lead, but
  the pass is out of protocol.
- Consequences recorded:
  1. The study lead is no longer provenance-blind for this paper (§11.1).
     The paper remains in the stress stratum; its alignment and
     disagreement coding are handled as a documented exception and it
     contributes no headline agreement estimate.
  2. No content from the AI session reaches the annotator before his sealed
     passes on this paper, including the Stage-5 washout re-annotation, are
     complete (§3.4, §8.5, §9).
  3. Schema clarifications arising from the review were adopted by the
     study lead on 2026-10-11 and applied pre-tag on 2026-10-11 as
     documentation notes in `schema/dimensions.md` and candidates
     CE-M1/CE-M2 in `KNOWN_LIMITATIONS.md`. The annotator's existing drafts
     of this paper predate those notes; disagreements attributable to them
     are coded to the protocol-ambiguity category, not against the
     annotator. This includes differences between those drafts and the
     Stage-5 washout re-annotation of this paper, which will run under the
     notes: such differences are rule change, not annotator instability.

## D-pre-2 (2026-10-24): Typical-stratum H0 may begin before the study tag

- Decision by the study lead: the annotator may begin H0 on accepted
  typical-stratum papers before the study tag is assembled, and may
  interleave intake screening (§6.4) and annotation in any order. Papers
  are annotated in the order in which they filled their slots
  (`study/PAPERS.md` §1.9), starting with PMID 41703050.
- §4 requires the tag before Stage 1 begins; Stage 1 already began pre-tag
  with the marques2025 H0 (ledger entry S-1). At this date the following
  §4 items are incomplete: the skill bundles and their hashes (item 2),
  the AI model and execution settings (items 4 and 5), the extraction tool
  and the canonical texts (items 6 and 7), the analysis code and the open
  decision in `study/PAPERS.md` §3 item 4 (item 8), and `study/RULINGS.md`
  (item 10). The study lead chose not to hold the annotator's work for
  them.
- Safeguards:
  1. Each H0 runs under the schema, annotation protocol and worksheet
     (version 2) committed when it starts. Any change to these before the
     tag is recorded here, and disagreements attributable to it are coded
     as rule change, not against the annotator (as in D-pre-1).
  2. The canonical text of each study paper is extracted mechanically with
     the tool fixed under item 6, and hashed, before the study lead reads
     that paper's H0 output.
  3. The remaining §4 items, including the AI materials and the analysis
     code, are completed and tagged before Stage 3 begins; H0 content is
     not used in completing them.
  4. Intake outcomes recorded after the annotator's first typical-stratum
     H0 began are identifiable from the draw-log dates and the worksheet
     start dates, so the analysis can compare them with earlier outcomes.

## D-pre-3 (2026-11-23): Clarification of intake criterion 4 for non-human evidence

- The study lead adopted the following clarification of the §6.4
  criterion-4 scope judgement: "Non-human genetic evidence is eligible
  when the genetic-entity-to-phenotype claims have a clear, substantiated
  connection to human biology or health. This includes relevant
  comparative or experimental organism research and pathogen genetics
  bearing on human infection, virulence, or antimicrobial resistance.
  Generic statements of potential human relevance are insufficient."
- Applied pre-tag on 2026-11-23 as a documentation note under §6.4 in
  `protocols/EVALUATION_PROTOCOL.md` and as a sub-note on question 4 of
  the intake screening page (`scripts/intake_screen/index.html`); the
  frame, candidate order and draw procedure (`draw_data.json`,
  `scripts/study_draw.py`) are unchanged.
- The clarification restates the judgement as applied rather than
  changing it. All 29 outcomes recorded before this date (5 passes, 24
  fails) were reviewed: the 5 passed papers are human-subject studies,
  and no rejected paper was pathogen genetics bearing on human
  infection, virulence or antimicrobial resistance, so no recorded
  outcome turns on the clarified text. Intake outcomes are final (§6.4)
  and stand as recorded; outcomes from this date run under the
  clarified text and are identifiable from the draw-log dates (as in
  D-pre-2, safeguard 4).
