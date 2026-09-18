# Reviewing an annotation — usage guide

How to review an existing GEM annotation — AI-drafted, hand-written, or
somewhere in between — using the `genetic-evidence-review` skill.

This guide assumes **no prior knowledge**: not of Claude, not of skills, not of
the terminal. It explains the vocabulary first, then gives three routes — pick
one. Its companion is [`ANNOTATION_GUIDE.md`](ANNOTATION_GUIDE.md), which
covers producing an annotation in the first place.

**What you end up with:** three files — a YAML review log, a markdown review
report, and an updated annotation carrying the edits you approved.

**What makes this different from the annotation skill:** the review skill is
**interactive**. It does not run to completion and hand you a result. It walks
you through the annotation item by item, asks for a decision on every one, and
records what you said. The session is the deliverable as much as the files
are. Expect an hour or two on a six-item annotation, and expect to be asked
questions you have to think about.

Product details (menus, plans, file limits) were checked against Anthropic's
documentation on 2026-09-17 and change without notice.

---

## The vocabulary

| term | what it means here |
| --- | --- |
| **Claude** | The AI assistant this repository's skills are written for. You reach it through a chat app, or through a terminal program called Claude Code. |
| **Claude account** | Your login. Everything below needs one; see [Prerequisites](#prerequisites). |
| **Claude Code** | Claude as a command-line program that runs on your machine, inside a folder you choose, and can read and write files there. |
| **The Claude app** | Claude in a browser (claude.ai) or the desktop/mobile app. No checkout; you upload the skill as a `.zip` and attach your files to the conversation. |
| **Curator** | You. The skill surfaces observations and recommends verdicts; you decide. Nothing is recorded that you did not approve. |
| **Evidence item** (`GE-1`, `GE-2`, …) | One unit of genetic evidence from the paper: a method applied to a target, with a credibility. The unit a verdict applies to. |
| **Assertion** | One claim inside an item. Every assertion carries a **source span** — a page number and a short verbatim phrase from the paper, so a reader can check it. |
| **Candidate extension** | A place where the schema did not fit and the annotator had to force it. Recorded, not fixed. |
| **Flag** | A recorded doubt. The annotator's are `ai_uncertainty`, `ai_assumption`, `ai_normalization`; yours as reviewer are `reviewer_query`, `reviewer_suggestion`, `reviewer_disagreement` — see [Your job as curator](#your-job-as-curator). |

A **skill** is a folder containing a file called `SKILL.md` — natural-language
instructions plus the material they refer to — that an assistant loads on
demand to perform one task the same way every time. A skill is the executable
counterpart of a written protocol: `protocols/REVIEW_PROTOCOL.md` tells a
human what a review must do; `skills/genetic-evidence-review/` tells the
assistant. Skills follow the
[Agent Skills](https://agentskills.io/specification) convention, so they are
not Claude-specific.

---

## What a review session looks like

Five phases, in order (`protocols/REVIEW_PROTOCOL_INTERACTIVE.md` §3.1–§3.5;
its §3 opening line says "four phases" because it counts Phase 0 as setup,
while §4 lists all five):

| phase | what happens | what you do |
| --- | --- | --- |
| **0 — Setup** | Confirms inputs, reads the annotation and the paper, runs structural checks, sets the protocol-version baseline, asks once for session rulings | Answer four or five short questions |
| **1 — Missing evidence** | Shows the existing items as a table and asks what the annotation missed, then proposes its own candidates | Accept, reject or defer each |
| **2 — Per-item review** | For each item: surfaces observations, then asks for a verdict | Decide on **every** item, including the ones with no concerns |
| **3 — Paper level** | Cross-cutting observations, then the two-papers promotion check | Confirm or overrule |
| **4 — Emit** | Writes the three artefacts and says whether a second round is needed | Say where files go; confirm before anything replaces the source |

Two rules shape all of it. **Nothing is silently approved** — an item with no
concerns still needs an explicit verdict from you. And **the source annotation
is never silently overwritten** — the updated annotation is emitted as a
separate file, and replacing the original takes an explicit word from you.

---

## Your job as curator

The protocol gives the reviewer a vocabulary of three flags, and they are not
interchangeable:

| flag | use it when |
| --- | --- |
| `reviewer_disagreement` | a clear factual correction — the organism set is wrong |
| `reviewer_suggestion` | an optional improvement whose inclusion is a matter of preference — add HPO terms for the patient phenotypes |
| `reviewer_query` | the mapping to the schema is genuinely unclear and should not be silently corrected |

`reviewer_query` is the one people under-use. A question recorded is worth
more than a guess applied: the corpus keeps disagreements visible on purpose
rather than resolving them out of sight.

You never emit the annotator's flags. `ai_uncertainty` and `ai_assumption`
belong to whoever wrote the annotation and stay as a record of what they
thought at the time; `ai_normalization` is a normalization note rather than a
doubt, and appears in hand-written and AI-drafted annotations alike. Leave all
three alone. (The paper presents the three reviewer flags as the manual
track's vocabulary because it is describing flags recorded *inside*
annotations. As a reviewer you emit them against either track, and both pilot
logs do.)

One naming trap: several curator-authored annotations carry *keys* called
`reviewer_suggestion`, `reviewer_query` or `reviewer_disagreement` inside the
annotation itself — slots the annotator left for a curator's decision. Those
are not flags from a previous review, and reporting them as such double-counts
them.

And the standing commitment behind all of it: **the curator, not the model, is
the authority for the recorded annotation.** AI-drafted content and
AI-suggested edits are proposals. What lands in the corpus is what a human
approved, and the log is the evidence that someone did.

---

## Which route should you use?

| | **A. Claude Code** | **B. The Claude app (chat)** | **C. Agentic mode** |
| --- | --- | --- | --- |
| you need | a terminal and a checkout | a browser, plus the skill `.zip` | the Claude desktop app, plus the `.zip` |
| the corpus is | right there — Phase 3 works fully | not bundled — Phase 3 is limited | in the folder you grant |
| artefacts land | in `annotations/reviews/` directly | downloaded or copy-pasted | in that folder |
| session length | as long as you like | long conversations get unwieldy | long sessions are its strength |
| best for | reviews that go into this repository | one annotation, minimal setup | file output without a terminal |

Building that `.zip` takes one shell command in a checkout, so routes B and C
need a terminal exactly once — or a colleague who runs it.

Use **A** for anything destined for the corpus: the two-papers promotion check
in Phase 3 needs the other annotations on disk, and only route A has them.

---

## Prerequisites

1. **A Claude account.** Sign up at [claude.ai](https://claude.ai).
   - Custom skills in the **Claude app** work on the Free plan and above,
     provided code execution is enabled.
   - **Claude Code** requires a paid plan (Pro, Max, Team or Enterprise), or a
     Claude Console account billed through the API. There is no Free-plan path
     to Claude Code.
   - On **Team** and **Enterprise**, both Skills and code execution are an
     organization owner's decision. Check them before assuming an upload will
     work.
2. **The annotation** to review — a YAML file.
3. **The source paper**, ideally the same PDF the annotation was made from.
   Without it the skill can only check the annotation against the schema, not
   against reality: source spans cannot be verified and missed evidence cannot
   be detected. It will offer that reduced review and say so; take it only if
   the paper is genuinely unobtainable.
4. **git and a terminal — once, for every route.** Route A needs a checkout
   throughout. Routes B and C need one only to build the upload zip
   ([B2](#b2-build-and-upload-the-bundle)).
5. **Time and attention.** This is the step where a human judgement is
   recorded. If you are going to approve everything without reading it, the
   review adds nothing.

You do not need to know YAML or SHACL. You do need enough domain knowledge to
say whether an evidence item is fairly described — or the honesty to record a
`reviewer_query` when you are not sure.

The shell commands below are macOS/Linux; on Windows use the PowerShell
equivalents or work inside WSL.

---

## Route A — Claude Code

### A1. Install Claude Code

macOS and Linux:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Then `claude --version` to confirm — if that says *command not found*, open a
new terminal window — and run `claude` once, which opens a browser for the
login. Package-manager and npm routes, and the CMD one-liner, are in
[`ANNOTATION_GUIDE.md` §A1](ANNOTATION_GUIDE.md#a1-install-claude-code).

### A2. Get the repository

```bash
git clone https://github.com/ForomePlatform/genetic-evidence-model
cd genetic-evidence-model
```

Everything below runs from that directory. The skill reads `protocols/`,
`schema/`, `notes/` and `annotations/` by relative path.

### A3. Install the skill

```bash
mkdir -p .claude/skills
ln -s "$PWD/skills/genetic-evidence-review" .claude/skills/
```

Copy the folder instead if symlinks are awkward on your platform. The symlink
creates an untracked `.claude/` directory in the checkout; leave it untracked
or add it to `.git/info/exclude`. A personal install
(`ln -s "$PWD/skills/genetic-evidence-review" ~/.claude/skills/`) works
identically as long as you still start Claude Code at the repository root — it
is the working directory, not the skill's location, that makes
`protocols/REVIEW_PROTOCOL.md` resolve.

### A4. Start the session and confirm the skill is loaded

```bash
claude
```

then

```
/skills
```

`genetic-evidence-review` should be listed. If it is not, the usual cause is
that `.claude/skills/` did not exist when the session started: quit with
`Ctrl-D` and start `claude` again. Both skills can be installed at once; they
trigger on different phrasings.

### A5. Have your inputs ready

```bash
mkdir -p papers
cp ~/Downloads/smith2024.pdf papers/
```

`.gitignore` excludes `*.pdf`, so a publisher PDF in the checkout will not be
committed by accident. Download the PDF yourself rather than giving Claude a
URL — see
[`ANNOTATION_GUIDE.md` §A5](ANNOTATION_GUIDE.md#a5-put-the-paper-where-claude-can-read-it)
for why.

### A6. Start the review

```
/genetic-evidence-review
```

or in your own words:

```
Review the GEM annotation in annotations/v0/smith2024.yaml against
papers/smith2024.pdf.
```

Naming the skill is more reliable. A skill fires on a description match, and a
vague opening may not trigger it at all.

### A7. Phase 0 — setup

It confirms three inputs (the annotation, the paper, where artefacts go),
reads the protocols and the schema, and runs structural validation —
including a check for **invented keys**, which
`protocols/REVIEW_PROTOCOL.md` §2.1.1 defines as "extra keys that the schema
does not define". Those are a defect, not a harmless extra; the underlying gap
gets recorded as a candidate extension instead.

That check is not decidable as written — nothing in the repository enumerates
the legal keys — so settle it once, at the start, as a session ruling:
documented open keys and free-text `*_note` siblings are fine; anything that
installs a *new dimension* inline is not, and its content goes to
`candidate_extensions`. (The reason it is open: the SHACL shapes constrain
*values*, not keys, and `schema/dimensions.md` explicitly declares
`special_considerations` and the credibility facets open-ended.)

Then two short set-up steps that pay for themselves later:

**The protocol-version baseline.** The annotation was produced under some
version of `PROTOCOL.md`. Rules added *after* that version are recorded as
forward-notes, not defects — an annotation is not wrong for having been
written before a rule existed. The skill states the baseline once; correct it
if it read the wrong version.

As things stand there is a real skew to know about: `PROTOCOL.md` is at 1.1,
while every AI-drafted annotation in the corpus records
`protocol_version: "1.0"` (and `README.md` still says 1.0 — the protocol file
is authoritative). The 1.1 additions are the ones to treat as forward-notes:
`variant_ascertainment` becoming conditional on `target_type = VARIANT`, and a
considered-but-empty dimension being marked `not_applicable_or_omitted` rather
than left absent.

**Session rulings.** Governing conventions for the whole session, recorded as
`SR-1`, `SR-2`, … in the log. This is where you say things like *"strip the
inline candidate-dimension keys from every item"* or *"`variant_ascertainment`
does not apply to a polygenic score anywhere in this paper"* once, instead of
re-arguing them item by item. Real examples are in
`annotations/reviews/inouye2018-review-2026-06-06.yaml`. If you have none yet,
say so — you can add them mid-session when a pattern shows up.

### A8. Phase 1 — what did the annotation miss?

You get a table of the existing items and one question: is anything missing?
Then the skill offers its own candidates.

This comes *before* per-item review deliberately: it sets the frame "what
should be here" before you descend into judging what is here. It is also where
the pilot found the real gaps. Neither AI-draft missed a granular finding
badly enough to need a whole new item — though the Inouye draft did miss two
that entered as new *assertions*. What both drafts missed were **higher-level**
items: a paper's headline synthesis, a cited translational study — precisely
the things that need reading across items to notice. A cited study becomes its
own item with `cited_evidence: true` (`protocols/PROTOCOL.md` §7), not
background prose.

Answer **accept**, **reject** or **defer** for each. Accepted items join the
Phase 2 queue and get reviewed like any other.

In practice most of what you find missing is not a whole item but an
**assertion inside an existing one** — a clinical detail, a negative family
history, a control result — which the lumper rule (`protocols/PROTOCOL.md`
§2.1: prefer one item with several assertions over several thin items) says
must not be split out into an item of its own. The protocol only describes
accepted candidates becoming new items (`GE-new-1`, `GE-new-2`, …), so say
which of the three resolutions you want: a new item, a new assertion on an
existing item (it then rides on that item's Phase-2 verdict), or a paper-level
observation for Phase 3. Left unsaid, this is where a review quietly loses
findings.

### A9. Phase 2 — item by item

For each evidence item the skill surfaces what it found — structural problems,
internal inconsistencies, evidential concerns, source-span defects classified
as blocking or non-blocking — and then asks for your verdict:

| verdict | meaning | recorded as |
| --- | --- | --- |
| **Approve as a whole** | the item stands | `approved` |
| **Approve despite flags** | you noted the concerns and accept it anyway | `approved_despite_flags` |
| **Reject** | remove the item from the annotation | `rejected` |
| **Edit before approval** | change it; you say what changes | `marked_for_edit` |

The default offered to you follows a rule: **no issues surfaced → approve**;
**issues surfaced → edit**. That default ignores severity — it fires whether
the issue is a wrong organism or a stylistic quibble — so overriding it with
*approve despite flags* is legitimate and expected. The right test is
`REVIEW_PROTOCOL.md` §2.2.1's blocking / non-blocking distinction, even though
it is written as if it applied only to source spans.

If you choose Edit, you will be asked *what* should change, and your answer
goes into the verdict's notes verbatim — so answer in terms someone can apply
six months from now.

Approval is at the item level, not the assertion level. If three assertions in
an item are fine and one is doubtful, the verdict covers the item and the
notes carry the per-assertion detail. That is a deliberate simplification.

Three things to keep in mind while answering:

- **Flags are not the edit signal on model-straining papers.** An AI draft of
  a structurally novel paper — a polygenic score, say — may carry almost no
  uncertainty flags and a long list of candidate extensions, because it
  expressed strain as *"the schema is missing a feature"* rather than *"I am
  unsure."* On such papers, scrutinise the candidate extensions and the forced
  fits instead.
- **For a hand-written annotation, respect the human's calibration.** The
  curator may have made context-aware judgements — especially on credibility —
  that the AI reviewer reads as errors.
- **Verify spans against normalised text.** PDF extraction introduces hyphens
  at line wraps, ligatures, curly quotes and en-dashes. Fold those and
  collapse whitespace before deciding a phrase is not verbatim, or you will
  raise defects that are artefacts of the extractor. And an HTML rendition
  cannot verify *pages* at all — a wrong page is the one blocking span defect,
  so if you are working without the PDF, record that in the log's caveats
  rather than approving page numbers you did not check.

You may go back: ask to revisit any item already reviewed and the verdict is
updated. Useful things to type at any point: **"where are we?"** (phase, items
reviewed, items remaining, verdict summary), **"let's pause"** (it offers to
save a partial log marked `incomplete: true`).

### A10. Phase 3 — the paper as a whole

Two things happen here.

**Paper-level observations**: cross-cutting issues that belong to no single
item — the method hierarchy being exercised inconsistently across items, a
decomposition that should have been split differently, a translational claim
that is not a genetic-target assertion at all.

**The two-papers promotion check**: for every candidate extension in the
annotation, the skill checks `schema/EXTENSIONS.md` and the other annotations
in `annotations/` for an *independent second occurrence*. A gap seen in one
paper stays a candidate; a gap seen independently in a second paper becomes a
promotion recommendation — that is the rule that grew `phenotype_scale` and
`variant_ascertainment` into real dimensions.

The review only **records** the recommendation. Changing
`schema/dimensions.md`, the SHACL shapes and `EXTENSIONS.md` is a separate,
human workflow — and one that lags: recommendations made in the 2026-06
reviews are still not reflected in `EXTENSIONS.md`. Treat that file as a
partial record.

Three things make the check harder than it sounds:

- **`annotations/` is not one file per paper.** Eight files, six papers. The
  directories are consistent — `v0/` holds the protocol-v0 draft, `v1/` the
  re-annotation under the current protocol — but which one is *canonical*
  flips between papers: the Duerr review was run against the v0 draft, the
  Inouye review against the v1 re-annotation. The canonical set is
  `davis2011.yaml`, `gupta2015.yaml`, `jossin2017.yaml`, `nelson1992.yaml`,
  `annotations/v0/duerr2006.yaml` and `annotations/v1/inouye2018.yaml`.
- **One paper is one occurrence.** Two versions of the same paper are still
  one. But read the other version anyway: a candidate dropped between v0 and
  v1 still counts as having occurred.
- **Candidate identity is free text, and it drifts.** The same gap can be
  spelled differently in two annotations, so string matching finds nothing.
  Match on the *symptom* — "cohort facts are sitting in free-text
  `special_considerations`" — rather than on the candidate id, and read the
  grouped narrative in `EXTENSIONS.md` first.

### A11. Phase 4 — the three artefacts

```
annotations/reviews/<paper-id>-review-<YYYY-MM-DD>.yaml   the log
annotations/reviews/<paper-id>-review-<YYYY-MM-DD>.md     the report
<somewhere you choose>                                    the updated annotation
```

**The log is the authoritative artefact.** Everything else is derived from it.
It carries: which annotation was reviewed, the protocol version it was
produced under, who reviewed it and when, your session rulings, a verdict for
every item, the observations, migration suggestions, promotion
recommendations, and whether a second round is warranted.

**The report** is the same content as narrative prose — the thing you attach
to a pull request or a paper supplement. It can be regenerated from the log.

**The updated annotation** is the source with your approved verdicts applied:
edits made, rejected items removed, Phase-1 additions added, invented keys
stripped (with the gap rerouted to a candidate extension), and a
`provenance.review_applied` entry recording what was done. It never overwrites
the source automatically; replacing the original takes an explicit word from
you.

**Redirect it.** The skill offers
`annotations/<paper-id>.reviewed-<YYYY-MM-DD>.yaml`, which drops a freshly
edited file into the curated corpus directory beside the four curator-authored
reference annotations — and the skill asks permission before creating
`annotations/reviews/` but not before writing there. Put it next to the source
annotation instead. In practice the two reviews in this repository landed
theirs at `annotations/v0/duerr2006.yaml` and `annotations/v1/inouye2018.yaml`,
and no `.reviewed-<date>.yaml` file has ever actually been written. Agree the
path in Phase 4 rather than assuming.

Two habits worth having before you ship the artefacts:

- **Parse your own review log.** Nothing validates it — no schema, no shape,
  no CI — and a free-text verdict containing a colon-space will break the YAML
  silently. One
  `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <log>.yaml`
  is the whole fix.
- **Pick one shape for `flags_recorded` and stick to it.** The two logs in
  this repository disagree: Duerr uses `{type, level, subcategory, note}` and
  Inouye uses `{flag, subject, note}`. The Duerr shape is the better model —
  the flag's own name under `type`, and the `REVIEW_PROTOCOL.md` §2 review
  level (`structural` / `consistency` / `evidential`) under `level`. Severity
  is not carried in the log at all; §2.2.1's blocking / non-blocking call
  shows up only in the choice between `reviewer_disagreement` and
  `reviewer_suggestion`.

What the review deliberately does **not** do: re-annotate from scratch (that
is the annotation skill), apply promotions to the schema, or reconcile the
downstream artefacts your edits move — the case report in `case-reports/`,
`annotations/coverage.md`, the numbers quoted in the paper. Those are separate
steps, and the log tells you which ones are now stale.

### A12. Validate the updated annotation

The review does not validate for you. Once per checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyshacl rdflib pyyaml
```

then, against whatever path you agreed in Phase 4:

```bash
python3 src/python/main/forome/gem/validation/validate_annotations.py annotations/v0/smith2024.reviewed-2026-09-17.yaml
```

Success is `PASS <path>` followed by `All annotations conform to the SHACL
shapes.` and exit status 0 (`echo $?` prints it). A failure prints a
`Focus Node:` — `gem:item_GE_1` is item GE-1, `gem:item_GE_1_a0` its first
assertion — and a message. Paste the failure back into the session and ask for
a fix. `gem-validate <path>` does the same after `pip install -e .`, but note
that a bare `gem-validate` validates the corpus of the checkout it was
installed *from*.

**Know what this verdict is worth.** SHACL checks the always-required
dimensions, the enumeration values, three conditional activations (variant
ascertainment under `VARIANT`, mode of inheritance under human genetics +
gene, organism under in-vivo work), and that every assertion carries a source
span with an integer page and a phrase. It does *not* check that the phrases
are verbatim, that they are under fifteen words, that the page is right, or
that `provenance`, `flags` and `confidence_summary` are present and
well-formed.

In particular, **an annotation full of invented keys still passes**: the
YAML→RDF converter silently drops every key it does not recognise, so §2.1.1's
check is entirely yours. Never quote a PASS as evidence that the structural
review is done.

One trap: *"must declare exactly one X"* when the YAML plainly has exactly one
X means the **value** is not in the enumeration. Check `schema/dimensions.md`.

### A13. Second round

The skill recommends a second review pass when items were added in Phase 1,
when several items were marked for edit, or when a cross-cutting issue
surfaced. Both pilot reviews recommended one: each paper gained an item and
several were edited, and substantively new content deserves the same scrutiny
as the old.

A second round is a fresh session against the updated annotation, and it goes
faster — but the skill does not know it is a second round, so tell it:

```
This is a second-round review. The annotation's provenance.review_applied
points at the previous log — read that first, carry its session rulings
forward, and do not reopen anything it settled.
```

Three things only a re-review can catch: whether the prior round's paper-level
observations have since been resolved upstream (leaving a stale note inside
the annotation), whether its promotion recommendations ever reached
`schema/EXTENSIONS.md`, and whether `provenance.review_applied` needs to
become a list to hold a second entry.

---

## Route B — The Claude app (chat)

No checkout to maintain — but one terminal step, to build the upload bundle.

### B1. Turn on code execution

**Settings → Capabilities → "Code execution and file creation"**. On Team and
Enterprise this is an owner's decision, under **Organization settings →
Skills**, with both that toggle and "Skills" enabled.

### B2. Build and upload the bundle

```bash
git clone https://github.com/ForomePlatform/genetic-evidence-model
cd genetic-evidence-model
./build_skill_bundle.sh --skill review --check   # dry run
./build_skill_bundle.sh --skill review           # -> genetic-evidence-review-skill.zip
```

This is the only terminal step in route B; you can delete the checkout
afterwards and keep the zip.

It lands in the repository root at about 65 KB (`.gitignore` covers `*.zip`)
and contains `SKILL.md`, both license files, `BUNDLE_README.md`, both review
protocols, the annotation protocol, the labeling examples, `ROADMAP.md`, the
schema and the validator — all under a single top-level
`genetic-evidence-review/` folder, which is the layout the uploader expects.

Upload it at **Customize → Skills → "+" → "+ Create skill" → "Upload a
skill"**, then make sure its toggle is on. Uploaded skills are private to your
account; colleagues upload their own copy, or you share it from the "…" menu
(Team and Enterprise).

### B3. Start the session

Attach **both** the annotation YAML and the paper PDF to a new conversation
("+" → "Add files or photos", or drag them in). Up to 20 files, 500 MB each;
PDFs up to 1000 pages, with PDFs of 100 pages or fewer read as text *and*
images and larger ones as text only — attach a long supplement as its own
file.

Then:

```
Use the genetic-evidence-review skill to review the attached annotation
against the attached paper. Let's go item by item.
```

The phases run exactly as in route A. Keep the conversation in one thread —
the skill tracks phase, queue and verdicts across turns, and starting a new
conversation loses that state.

### B4. What is different in chat

- **Phase 3 is limited.** The review bundle ships no annotation corpus, so the
  two-papers promotion check has nothing to check against beyond
  `EXTENSIONS.md`. Either attach the other corpus annotations to the
  conversation, or accept that the review will record candidate extensions
  without promotion recommendations — and say so in the log.
- **Ask for the artefacts explicitly** at the end: *"Save the review log, the
  report and the updated annotation, and give me download links."* If no
  download appears, ask for each file printed in a fenced code block and copy
  it out. Check the end of each file: a truncated paste is the most common way
  a chat review goes wrong.
- **Validation may not be available.** The bundled validator needs
  `pip install pyshacl rdflib pyyaml` in Claude's sandbox, which needs network
  access — an administrator controls that on Team and Enterprise, so if the
  install fails, check there first. If it is unavailable, validate the updated
  annotation locally afterwards, as in
  [A12](#a12-validate-the-updated-annotation). The bundled validator must
  always be given an explicit file path; run bare inside a bundle it reports
  "No annotation files found", because a bundle has no `annotations/`
  directory.
- **Long sessions drift.** Ask "where are we?" periodically and check the
  answer against your own count of items.

---

## Route C — Agentic mode (Cowork)

Claude working against a **folder on your computer**, reading and writing real
files without a terminal — after the one terminal step that builds the zip, or
none at all if a colleague sends you one. For a review this is the strongest
of the three routes on one axis: a long, multi-turn session survives across
turns and devices, and the state lives in the folder rather than in chat
scrollback.

Local-folder access needs the Claude **desktop** app. At the time of writing
it also needs a paid plan; Anthropic has said the merged Claude experience
will reach Free plans, so check your own account.

### C1. Upload the skill

Exactly as in [B2](#b2-build-and-upload-the-bundle). Agentic sessions load the
skills enabled on your claude.ai account and do **not** read
`~/.claude/skills/` or this repository's `skills/` folder, so the upload is
not optional. Re-upload whenever the skill changes.

### C2. Make a working folder

One folder per review — not the repository. Inside a folder you grant, Claude
can read, write and permanently delete. Put in it: the annotation, the paper,
`schema/dimensions.md`, `schema/EXTENSIONS.md`, and the other corpus
annotations you want Phase 3 to see.

### C3. Start the task with approvals on

Of the three approval modes, **never choose "Skip all approvals"**. This
workflow exists to record a human judgement; a review nobody adjudicated is
not a review.

### C4. Run the review

```
Use the genetic-evidence-review skill to review smith2024.yaml in this folder
against smith2024.pdf. Let's go item by item. Write the review log, the
report and the updated annotation into this folder.
```

The five phases run as in route A, with the corpus files you provided standing
in for `annotations/`.

### C5. Validate and file the artefacts

Copy the three files into a checkout, validate the updated annotation as in
[A12](#a12-validate-the-updated-annotation), and put the log and report under
`annotations/reviews/`.

As of this writing, Anthropic is merging Cowork and chat into a single Claude
interface — announced 2026-09-16, reaching Pro and Max first over several
weeks, with Team and Free to follow and Enterprise organizations given at
least 30 days' notice. Where this sits in the UI therefore depends on your
plan and your build. Look for the capability — "work in a folder on my
computer" — rather than for a tab with a particular name.

---

## Worked examples in this repository

The two pilot reviews are in `annotations/reviews/`, and they are the best
documentation of what a good log looks like:

- `duerr2006-review-2026-06-04.{yaml,md}` — a clean GWAS paper; six drafted
  items, four edited, one added on review.
- `inouye2018-review-2026-06-06.{yaml,md}` — a polygenic-score paper that
  strains the model; three session rulings, one item added, and a candidate
  extension enriched with a SHACL-unsatisfiability finding. Read this one for
  how session rulings save a session from re-litigating the same point.

Across both, no item was rejected, and most edits were about schema-level
judgement — knowledge domain, method placement, credibility calibration. Not
all: the Duerr review corrected a page citation (GE-2.A2, 3 → 2), restated a
label that said "associated" where the finding was protective (GE-1), and
restated an assertion whose claim was not in the main text at all (GE-4.A1).
Expect a handful of factual corrections per annotation, not none.

---

## Troubleshooting

| symptom | cause and fix |
| --- | --- |
| `/skills` does not list the skill | `.claude/skills/` did not exist when the session started, so Claude Code is not watching it. Restart Claude Code. Edits to an already-visible `SKILL.md` are picked up live. |
| Claude discusses the annotation but never loads the skill | The description did not match your phrasing. Invoke it by name: `/genetic-evidence-review`. |
| It skips items, or approves without asking | Say "every item needs an explicit verdict, including the ones you have no concerns about" — that is the protocol, and it will comply. |
| It cannot find the other annotations for Phase 3 | Route B: the corpus is not bundled. Attach the annotations, or accept a promotion-check-free review and record that in the log. |
| It offers a "schema-only review" | It could not read the paper. Re-attach it, or accept the reduced review knowingly — source spans will not be verified. |
| It has lost the thread in a long session | Ask "where are we?", then correct it. If the answer is badly wrong, ask it to save a partial log (`incomplete: true`) and start fresh against the updated annotation. |
| `python3: can't open file '.../scripts/validate_annotations.py'` | That path does not exist in the repository, whatever `README.md` and `SKILL.md` say. Use `src/python/main/forome/gem/validation/validate_annotations.py`, or `gem-validate` after `pip install -e .`. |
| `ModuleNotFoundError: No module named 'forome'` | You invoked it as a module. Use the plain script path, or set `PYTHONPATH=src/python/main`. |
| Validator prints "No annotation files found" | Run with no arguments somewhere without an `annotations/` directory. Pass the file path explicitly. |
| "must declare exactly one X" but X is right there | The value is not in the enumeration. Check `schema/dimensions.md`. |

---

## Known rough edges

Audited 2026-09-17 against the repository as it stands. None blocks a review;
all of them will waste your time if you meet them cold.

- **`scripts/validate_annotations.py` does not exist in the repository.**
  `SKILL.md`, `README.md` and the SHACL header still name it. The validator
  moved into the package at
  `src/python/main/forome/gem/validation/validate_annotations.py` (console
  script `gem-validate`). Inside an uploaded bundle the `scripts/` path *is*
  correct — it is only wrong in a checkout.
- **The `.reviewed-<date>.yaml` sidecar has never actually been written.** The
  protocol and the skill both name it as the default, and the Inouye review
  report even cites one, but no such file exists in this repository's history.
  Agree the path in Phase 4 rather than assuming.
- **The review bundle ships no annotations**, so the Phase-3 two-papers check
  and the Phase-4 checklist item that depends on it cannot be completed from
  the bundle alone. Its `SKILL.md` still lists `annotations/` in its reading
  order. Route A is unaffected.
- **The `description` field in both `SKILL.md` files is around 620
  characters**, and `version:` is a non-standard frontmatter key (the Agent
  Skills specification puts it under `metadata:` and allows 1024 characters
  for a description, while Anthropic's help centre documents a 200-character
  maximum for custom skills uploaded to the Claude app). If an upload is
  rejected, shorten the description first and drop `version:` second.
- **Nothing validates a review log** — no schema, no shape, no CI. Parse it
  yourself before shipping it. The two worked examples also differ in field
  set and in the `flags_recorded` shape.
- **`mode_of_inheritance` has no published enumeration.** The SHACL shapes
  hard-require it for human-genetics gene-targeted items, but
  `schema/dimensions.md` gives no value table, so any token coined will
  validate. The corpus spellings are `AUTOSOMAL_RECESSIVE`,
  `X_LINKED_RECESSIVE`, the sentinel `not_applicable_or_omitted`, and
  `COMPLEX` — the last coined as a placeholder in
  `annotations/v0/duerr2006.yaml` and logged as a sub-gap of CE-DU4. Flag any
  further coinage in the log.
- **Promotion recommendations are not synced.** Those recorded in the 2026-06
  reviews have not reached `schema/EXTENSIONS.md`, which in turn cites a
  `PAPER_ERRATA.md` that does not exist. Treat `EXTENSIONS.md` as a partial
  record when running the two-papers check.

---

## Where things live

| path | what it is |
| --- | --- |
| `skills/genetic-evidence-review/SKILL.md` | the skill itself |
| `protocols/REVIEW_PROTOCOL.md` | the canonical review rules: what a review must do and produce |
| `protocols/REVIEW_PROTOCOL_INTERACTIVE.md` | the phase-by-phase workflow this skill implements |
| `protocols/PROTOCOL.md` | the annotation protocol the annotation under review was produced against |
| `protocols/LABELING_EXAMPLES.md` | worked cases for the recurring judgement calls |
| `schema/dimensions.md` | every dimension and its legal values |
| `schema/EXTENSIONS.md` | every candidate extension surfaced so far, and its promotion status |
| `notes/ROADMAP.md` | expected leaf-value migrations, the targets for migration suggestions |
| `annotations/reviews/` | the two worked review logs and reports |
| `build_skill_bundle.sh` | builds the upload zip for the Claude app |
| `docs/ANNOTATION_GUIDE.md` | the step before this one |
| `docs/STUDIO.md` | the Mapping Studio, for the UMLS crosswalk |
| `KNOWN_LIMITATIONS.md` | what the model, schema, corpus and tooling do not yet do |
