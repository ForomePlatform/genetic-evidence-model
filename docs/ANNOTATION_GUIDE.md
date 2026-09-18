# Annotating a paper — usage guide

How to produce a GEM annotation of a genetics publication using the
`genetic-evidence-annotation` skill, from a standing start.

This guide assumes **no prior knowledge**: not of Claude, not of skills, not
of the terminal. It explains the vocabulary first, then gives three routes —
pick one. Its companion is [`REVIEW_GUIDE.md`](REVIEW_GUIDE.md), which covers
reviewing an annotation that already exists.

**What you end up with:** one YAML file describing the paper's genetic
evidence under the GEM schema, source-anchored assertion by assertion, and
passing SHACL validation.

**What you do *not* end up with:** a finished annotation. Everything the skill
produces is a **draft**, and the project treats it as one. It is not admitted
to the corpus until a curator has reviewed it — see
[After the draft](#after-the-draft-review-is-not-optional).

Product details (menus, plans, file limits) were checked against Anthropic's
documentation on 2026-09-17 and change without notice.

---

## The vocabulary

| term | what it means here |
| --- | --- |
| **Claude** | The AI assistant this repository's skills are written for. You reach it through a chat app, or through a terminal program called Claude Code. |
| **Claude account** | Your login. Everything below needs one; see [Prerequisites](#prerequisites). |
| **Claude Code** | Claude as a command-line program that runs on your machine, inside a folder you choose, and can read and write files there. This is the mode the corpus was produced in. |
| **The Claude app** | Claude in a browser (claude.ai) or the desktop/mobile app. No checkout; you upload the skill as a `.zip` and attach the paper to the conversation. |
| **Curator** | The human who decides what is recorded. The skill drafts; the curator approves. Nothing this skill produces enters the corpus until a curator has reviewed it. |

And the word the whole guide turns on: a **skill** is a folder containing a
file called `SKILL.md` — natural-language instructions plus the material they
refer to — that an assistant loads on demand to perform one task the same way
every time. A skill is the executable
counterpart of a written protocol: `protocols/PROTOCOL.md` tells a human what
an annotation must satisfy; `skills/genetic-evidence-annotation/` tells the
assistant. Skills follow the [Agent Skills](https://agentskills.io/specification)
convention, so they are not Claude-specific — other agents read the same
folder.

One more thing decides how this skill behaves: it runs in **autonomous mode**.
It asks three questions up front, then works to completion without consulting
you. Interactive annotation — curator review of the decomposition before the
details are filled in — is planned but not yet specified, and the skill will
decline it.

---

## Which route should you use?

| | **A. Claude Code** | **B. The Claude app (chat)** | **C. Agentic mode** |
| --- | --- | --- | --- |
| you need | a terminal and a checkout | a browser, plus the skill `.zip` | the Claude desktop app, plus the `.zip` |
| the skill comes from | the `skills/` folder in the checkout | a zip you upload once | the same upload as B |
| the paper is | a file in the folder | attached to the conversation | a file in a folder you grant |
| the result is | written straight to disk | downloaded or copy-pasted | written into that folder |
| you can validate | yes, locally | usually, in Claude's sandbox | yes |
| best for | producing annotations for this repository | one paper, minimal setup | file output without a terminal |

Building that `.zip` takes one shell command in a checkout — so routes B and C
need a terminal exactly once, or a colleague who runs it for them. It is the
same file for everyone.

If you are contributing to this repository, use **A**.

---

## Prerequisites

1. **A Claude account.** Sign up at [claude.ai](https://claude.ai).
   - Custom skills in the **Claude app** work on the Free plan and above,
     provided code execution is enabled (see [B1](#b1-turn-on-code-execution)).
   - **Claude Code** requires a paid plan (Pro, Max, Team or Enterprise) or a
     Claude Console account billed through the API. There is no Free-plan path
     to Claude Code.
   - On **Team** and **Enterprise**, both Skills and code execution are an
     organization owner's decision. Check them before assuming an upload will
     work.
2. **The paper, as a paginated PDF**, in English, machine-readable (not a
   scan). The skill checks quality and refuses degraded input rather than
   guessing.

   Take *paginated* literally. Every assertion must carry a `source_span` with
   a page number, and the schema requires it to be an integer — so a paper you
   can only obtain as HTML cannot be annotated honestly, and neither can one
   published with article numbers instead of page ranges. Download the PDF to
   a local file before you start. Do not expect the assistant to fetch the
   article for you: web-fetching tools routinely decline to return a full
   article text on copyright grounds, even for open-access papers, and a
   summary is useless here — the protocol requires every quoted phrase to be
   verified as a verbatim substring of the source.
3. **The right to use it.** Only short key phrases (under fifteen words) are
   quoted into the annotation, which is what keeps the corpus within fair-use
   norms — but you still need lawful access to the paper itself.
4. **git and a terminal — once, for every route.** Route A needs a checkout
   throughout. Routes B and C need one only to build the upload zip
   ([B2](#b2-build-the-bundle)); after that, neither.

You do not need to know Python, YAML or SHACL. You do need to be able to judge
whether the annotation you get back is right — that is the part no tool does
for you.

The shell commands below are macOS/Linux. On Windows, use the PowerShell
equivalents noted where they differ, or work inside WSL.

---

## Route A — Claude Code

The mode the corpus was produced in. Claude runs inside your checkout, reads
the protocols and the reference annotations directly, and writes the YAML to
disk.

### A1. Install Claude Code

macOS and Linux:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Windows PowerShell — your prompt starts with `PS`:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Windows CMD — the prompt starts with `C:\` and no `PS`:

```
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

Package managers work too: `brew install --cask claude-code` on macOS,
`winget install Anthropic.ClaudeCode` on Windows, or
`npm install -g @anthropic-ai/claude-code` anywhere (Node.js 22 or newer is
expected; an older Node warns but still installs, because the package ships a
native binary).

Check it landed:

```bash
claude --version
```

If that says *command not found*, open a new terminal window — the installer
adds `claude` to your `PATH`, which an already-open shell has not picked up.

The first time you run `claude`, a browser window opens and asks you to log in
with your Claude account. That is the only authentication step; the login
persists across sessions until it expires, and Claude Code warns you before it
does. `/login` re-runs the sign-in; to move to a different account, run
`/logout` first.

### A2. Get the repository

```bash
git clone https://github.com/ForomePlatform/genetic-evidence-model
cd genetic-evidence-model
```

Everything below is run from that directory — the *repository root*. The skill
reads `protocols/`, `schema/` and `annotations/` by relative path, so the
working directory matters.

### A3. Install the skill

Claude Code looks for skills in several places; the two that matter here are
`.claude/skills/` inside the project and `~/.claude/skills/` for your account
as a whole. A symlink into either works:

```bash
mkdir -p .claude/skills
ln -s "$PWD/skills/genetic-evidence-annotation" .claude/skills/
```

On Windows, copy the folder instead
(`Copy-Item -Recurse skills\genetic-evidence-annotation .claude\skills\`) and
re-copy it when the skill changes.

Two notes. The symlink creates an untracked `.claude/` directory in your
checkout; leave it untracked, or add it to `.git/info/exclude`. And a personal
install (`ln -s "$PWD/skills/genetic-evidence-annotation" ~/.claude/skills/`)
works identically as long as you still start Claude Code at the repository
root — it is the *working directory*, not the skill's location, that makes
`protocols/PROTOCOL.md` resolve.

### A4. Start Claude Code and confirm the skill is loaded

```bash
claude
```

Then, at the prompt:

```
/skills
```

`genetic-evidence-annotation` should be in the list with its description.

If it is not, the usual cause is that `.claude/skills/` did not exist when the
session started. Claude Code notices new and edited skills inside a running
session, but only in a skills directory it was already watching — so the first
time you create that directory, quit with `Ctrl-D` and start `claude` again.
If it is still missing, check the link:

```bash
ls -l .claude/skills/
```

You should see `genetic-evidence-annotation -> .../skills/genetic-evidence-annotation`.

### A5. Put the paper where Claude can read it

Anywhere inside the checkout. A `papers/` folder is convenient:

```bash
mkdir -p papers
cp ~/Downloads/smith2024.pdf papers/
```

`.gitignore` already excludes `*.pdf`, so a publisher PDF dropped into the
checkout will not be committed by accident.

Download the PDF yourself rather than giving Claude a URL and hoping. A URL
sends it to a web-fetching tool that may return a summary, or may decline to
return the article text at all — and a source span can only be certified
against text you actually have. If a paper is available in several forms,
prefer the publisher's printable PDF: it is paginated, and its page numbers
are the ones a reader will use to check your spans.

### A6. Run it

Either name the skill explicitly:

```
/genetic-evidence-annotation
```

or describe the task — the skill's description is written to catch phrasings
like this:

```
Annotate papers/smith2024.pdf under the genetic-evidence model.
```

Being explicit is more reliable. A skill fires on a *description match*, and a
vague request ("have a look at this paper") may not trigger it at all.

### A7. What it asks you

The skill confirms three things before it starts, and does not assume:

1. **Which paper.** The path you just gave it.
2. **Where the output goes.** It offers `annotations/<paper-id>.yaml`, where
   the paper id is the lowercase first-author surname plus year —
   `smith2024`. **Override it.** That path puts an unreviewed AI draft
   directly into the curated corpus, beside the four curator-authored
   reference annotations. This repository's own practice keeps AI drafts
   apart, in `annotations/v0/` and `annotations/v1/`. Note that CI validates
   everything under `annotations/` recursively, subdirectories included; to
   keep a draft out of CI entirely until it has been reviewed, put it outside
   `annotations/` altogether. This guide uses
   `annotations/v0/smith2024.yaml` from here on.
3. **Where the schema is.** `schema/dimensions.md` and at least one reference
   annotation. In a checkout the defaults are correct; press on.

It may also ask once whether you want autonomous or interactive mode. Answer
**autonomous**: interactive annotation is not implemented, and the skill will
stop if you ask for it.

Then it works to completion — reading `protocols/PROTOCOL.md`,
`protocols/PROTOCOL_AUTONOMOUS.md`, `schema/dimensions.md`, the SHACL shapes,
the four curator-authored reference annotations (called *curator-led* in
`README.md` and the skill files), and `schema/EXTENSIONS.md`, in that order —
without further questions. For a typical paper this takes a few minutes.

### A8. What you get

One YAML file, with these top-level blocks:

| block | what it holds |
| --- | --- |
| `publication` | title, authors, year, DOI |
| `provenance` | `mode: autonomous`, protocol version, which model wrote it, timestamp, which reference annotations it consulted |
| `evidence` | the list of `GeneticEvidence` items — the substance. Each carries its dimensions and its assertions, and every assertion carries a `source_span` with a page and a short verbatim phrase. An item that relays a result from another paper carries `cited_evidence: true` (`protocols/PROTOCOL.md` §7) |
| `candidate_extensions` | places where the schema did not fit and the annotator had to force it. Every forced fit must produce one |
| `flags` | `ai_uncertainty`, `ai_assumption`, `ai_normalization` — see [Reading a draft](#reading-a-draft) |
| `confidence_summary` | mandatory in autonomous mode: overall and per-item confidence, the forced fits, and the decomposition alternatives it considered and rejected |

The only untouched autonomous draft in the repository is
`annotations/v1/duerr2006.yaml`, and its top-level blocks are exactly those
six. Open it beside your own output. (`annotations/v1/inouye2018.yaml` looks
similar but is a post-review artefact — it carries `provenance.review_applied`
and two extra blocks that a fresh draft will not have.)

Read the flags and the confidence summary **first**. They are the map of where
to look hardest.

### A9. Validate it

SHACL validation is a separate step; the skill does not run it for you. Once,
per checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyshacl rdflib pyyaml
```

Then, for each annotation:

```bash
python3 src/python/main/forome/gem/validation/validate_annotations.py annotations/v0/smith2024.yaml
```

Success looks like this:

```
PASS  annotations/v0/smith2024.yaml

All annotations conform to the SHACL shapes.
```

and exit status 0 — `echo $?` prints it, and it is what CI reads. Failure
looks like this:

```
FAIL  annotations/v0/smith2024.yaml
      Focus Node: gem:item_GE_1
      Message: GeneticEvidence must declare exactly one credibility rating.
      Focus Node: gem:item_GE_1_a0
      Message: Every assertion must carry exactly one source_span.

1 annotation(s) failed SHACL validation: annotations/v0/smith2024.yaml
```

`Focus Node: gem:item_GE_1` is evidence item GE-1; `gem:item_GE_1_a0` is its
first assertion. Paste the failure back into the same Claude Code session and
ask it to fix the annotation — it has the schema open.

**One trap worth memorising.** *"must declare exactly one X"* when the YAML
plainly has exactly one X means the **value** is not in the enumeration — a
typo, or a token that does not exist. Check `schema/dimensions.md` for the
legal tokens.

With no arguments the same command validates the whole corpus. That is
byte-for-byte the command CI runs — on pull requests, and on pushes to
`master` touching `annotations/`, `schema/`, `src/python/` or
`pyproject.toml`. A push on any other branch validates nothing, so run it
yourself.

If you would rather use the console scripts, `pip install -e .` in the
checkout gives you `gem-validate annotations/v0/smith2024.yaml`. Note that a
bare `gem-validate` validates the corpus of the checkout it was *installed
from*, not your current directory — with two checkouts you can silently
validate the wrong one. `gem-coverage` prints the dimension-coverage table to
standard output; it does not rewrite `annotations/coverage.md`.

### What a PASS is worth

Drafts often conform on the first attempt, and that is much weaker evidence
than it looks. SHACL checks the always-required dimensions, the enumeration
values, three conditional-activation rules (variant ascertainment under
`VARIANT`, mode of inheritance under human genetics + gene, organism under
in-vivo work), and that every assertion carries a source span with an integer
page and a phrase.

It does **not** check that the phrases are verbatim, that they are under
fifteen words, that the page is the right page, or that `provenance`, `flags`
and `confidence_summary` exist at all — that is, most of what the protocols
spend their pages on. Those are enforced by the annotator and by the reviewer,
and by nothing else.

Worth doing once, so you trust the tool: copy an annotation, rename its
`credibility:` key, and validate it. You should get a `FAIL` and exit status 1.

### A10. When the skill refuses

A refusal is a correct outcome, not a malfunction. Per
`protocols/PROTOCOL_AUTONOMOUS.md` §6 the skill stops and explains itself when
the paper text is inadequate (OCR damage, not English), when the paper is out
of scope (a review article, a methods paper with no evidential claims, not
genetics at all), when schema gaps are pervasive enough that candidate
extensions would outnumber populated dimensions, or when it cannot satisfy its
own self-consistency invariants. It does not produce best-effort output in
autonomous mode. Take the refusal at face value and either fix the input or
annotate the paper by hand.

---

## Route B — The Claude app (chat)

No checkout to maintain — but one terminal step, to build the upload bundle.
If you cannot run it, ask a colleague for the `.zip`.

### B1. Turn on code execution

Skills are gated behind it. **Settings → Capabilities → "Code execution and
file creation"**.

On Team and Enterprise this is an owner's decision, under **Organization
settings → Skills**, with both "Code execution and file creation" and "Skills"
enabled. (Anthropic's help centre also documents the code-execution toggle
under **Organization settings → Capabilities**; either path reaches it.)

### B2. Build the bundle

The skill folder alone is not enough: it references the protocols, the schema
and the reference annotations, which live outside it. `build_skill_bundle.sh`
gathers them into one self-contained zip.

```bash
git clone https://github.com/ForomePlatform/genetic-evidence-model
cd genetic-evidence-model
./build_skill_bundle.sh --skill annotation --check   # dry run: verifies every input exists
./build_skill_bundle.sh --skill annotation           # -> genetic-evidence-annotation-skill.zip
```

This is the only terminal step in route B; you can delete the checkout
afterwards and keep the zip.

It lands in the repository root at about 70 KB and is covered by `.gitignore`,
so building does not dirty the working tree. Inside it: `SKILL.md`, both
license files, `BUNDLE_README.md`, `PROTOCOL.md`, `PROTOCOL_AUTONOMOUS.md`,
`LABELING_EXAMPLES.md`, `schema/`, `scripts/` (the validator and the YAML→RDF
converter) and `exemplars/` (the four curator-authored reference annotations)
— all under a single top-level `genetic-evidence-annotation/` folder, which is
the layout the uploader expects.

### B3. Upload it

**Customize → Skills → "+" → "+ Create skill" → "Upload a skill"**, then pick
the zip. It appears in your skills list with a toggle; make sure the toggle is
on.

Uploaded skills are private to your account. Colleagues upload their own copy,
or you share it from the "…" menu next to the skill (Team and Enterprise).

If the upload is rejected because the description is too long, see
[Known rough edges](#known-rough-edges).

### B4. Attach the paper

Start a new conversation. Click **"+" → "Add files or photos"** in the chat
box, or drag the PDF in. Up to 20 files per conversation, 500 MB each, PDFs up
to 1000 pages. Papers of 100 pages or fewer are read as **text and images**;
past 100 pages Claude sees text only and loses the figure panels — so attach
the article and the supplement as separate files rather than one merged PDF.

Those are the limits for attaching a file to the conversation. Anything that
passes through Claude's code-execution sandbox — the validator in
[B7](#b7-validate-it), and any file handed back as a download — is capped at
30 MB each way. An annotation YAML is nowhere near either limit.

### B5. Run the annotation

Name the skill. This is the phrasing Anthropic's own documentation recommends:

```
Use the genetic-evidence-annotation skill to annotate the attached paper.
Use the schema and exemplars bundled with the skill: schema/dimensions.md
and the four YAML files in exemplars/. Write the annotation to smith2024.yaml.
```

Naming `exemplars/` up front matters: the bundled `SKILL.md` still asks for
the reference annotations at `annotations/…`, which is where they live in the
repository, not where the bundle puts them. It is a bug in the bundle builder,
harmless once you have said the sentence above. Otherwise the skill will ask
the same three questions as in [A7](#a7-what-it-asks-you).

### B6. Get the YAML out

Ask for it explicitly:

```
Save that as smith2024.yaml and give me the download link.
```

If no download appears, fall back to the reliable route: ask Claude to print
the complete YAML in a fenced code block and copy it into a file yourself.
Check the end of the file — a truncated paste is the most common way a chat
annotation goes wrong.

### B7. Validate it

The skill bundle ships the same validator CI uses, and Claude can run it in
its sandbox:

```
Install pyshacl, rdflib and pyyaml, then run
scripts/validate_annotations.py on the annotation and show me the output.
```

Two caveats. Installing packages needs sandbox network access, which an
administrator controls on Team and Enterprise — if the install fails, that is
the first thing to check. And the validator must always be given an explicit
file path: run bare inside a bundle it prints "No annotation files found",
because a bundle has no `annotations/` directory.

If validation is not available in your sandbox, save the YAML locally and
validate it as in [A9](#a9-validate-it), or hand it to someone who can.

---

## Route C — Agentic mode (Cowork)

Claude working on its own against a **folder on your computer**: it reads the
files there, runs the steps, and writes the result back as a real file. Same
underlying agent as Claude Code, without a terminal — after the one terminal
step that builds the zip, or none at all if a colleague sends you one.

Local-folder access needs the Claude **desktop** app. At the time of writing
it also needs a paid plan; Anthropic has said the merged Claude experience
will reach Free plans, so check your own account rather than taking that as
fixed.

### C1. Upload the skill

Exactly as in [B2](#b2-build-the-bundle) and [B3](#b3-upload-it). This is not
optional and not substitutable: agentic sessions load the skills enabled on
your claude.ai account, and do **not** read `~/.claude/skills/` or this
repository's `skills/` folder. Re-upload whenever the skill changes.

### C2. Make a working folder

One folder per paper — not the repository, and not your home directory.
Inside a folder you grant, Claude can read, write and permanently delete. Put
in it: the paper PDF, `schema/dimensions.md`, and the four reference
annotations from `annotations/`.

### C3. Start the task and grant the folder

Pick that folder as the working folder for the task, and keep approvals on.
Of the three approval modes, **never choose "Skip all approvals"** — the whole
point of this workflow is that the curator, not the model, is the authority
for what gets recorded.

### C4. Run the annotation

```
Use the genetic-evidence-annotation skill to annotate smith2024.pdf in this
folder. Use dimensions.md and the four exemplar annotations here as the
schema and exemplars. Write the annotation to smith2024.yaml in this folder.
```

It asks the same three questions as in [A7](#a7-what-it-asks-you), then works
to completion and leaves the YAML in the folder.

### C5. Validate it

Either ask Claude to install `pyshacl rdflib pyyaml` and run the bundled
`scripts/validate_annotations.py` against the file, or copy the YAML into a
checkout and validate it as in [A9](#a9-validate-it). The second is the one to
prefer when the annotation is destined for this repository.

As of this writing, Anthropic is merging Cowork and chat into a single Claude
interface — announced 2026-09-16, reaching Pro and Max first over several
weeks, with Team and Free to follow and Enterprise organizations given at
least 30 days' notice. Whether you see a separate Cowork surface therefore
depends on your plan and your build. Look for the capability — "work in a
folder on my computer" — rather than for a tab with a particular name.

---

## Reading a draft

Four things about the output that the skill's own documentation does not make
obvious.

**The flag vocabulary turns on commitment, not confidence**
(`protocols/PROTOCOL.md` §6.2). You filled in a value you are unsure about →
`ai_assumption`. You left it empty or marked it not applicable →
`ai_uncertainty`. You mapped free text onto an enumeration value →
`ai_normalization`. A gap in the *schema* is not a flag at all — it is a
`candidate_extension`, and both can apply to the same decision.

**A recurring gap is a finding, not a duplicate.** When the paper re-hits a
gap that `schema/EXTENSIONS.md` already records, say so. Under the two-papers
rule (`protocols/PROTOCOL.md` §5.2) an independent second occurrence is
exactly what promotes a candidate into the schema, and it is one of the most
valuable things a new annotation can contribute.

**`method` is a hierarchy, not a flat list** (`protocols/PROTOCOL.md` §3.4).
Intermediate values such as `STATISTICAL_GENETICS` validate and stay valid,
but where the paper supports a leaf (`GWAS`, `ASSOCIATION_STUDY`, `IN_VIVO`)
use it, or the review will raise a migration suggestion. `notes/ROADMAP.md`
§1.b lists the migrations already expected for the corpus.

**Two field names have changed.** The current protocol uses
**`target_resolution`** and **`source_span.phrase`**; the curator-authored
reference annotations predate the rename and write `resolution` and
`key_phrase`. The YAML→RDF converter accepts both as aliases, so validation
passes either way — use the new ones in new annotations.

That last point is why `SKILL.md`'s instruction to *"Match the structure of
existing annotations in the repository exactly. Do not invent new top-level
keys."* cannot be followed literally on its first sentence: the
curator-authored files carry `reviewer_flag_summary` and
`summary_table_crosswalk`, which an autonomous run cannot produce, and none of
the autonomous `provenance` fields. Match the dimension vocabulary and the
per-item shape; use the autonomous blocks listed in [A8](#a8-what-you-get).
The second sentence, though, is enforced: a review treats an invented
top-level key as a structural defect (`protocols/REVIEW_PROTOCOL.md` §2.1.1).

---

## After the draft: review is not optional

The standing commitment behind this workflow is that **the curator, not the
model, is the authority for the recorded annotation.** An autonomous
annotation is a draft, and the project treats it as one.

Of the nine AI-drafted evidence items in the pilot corpus, one was approved as
written; the rest were approved with flags or edited, and the reviewer added
two items the drafts had missed. The drafts were reliable for specific,
directly stated claims and least reliable for synthetic conclusions and cited
translational evidence — the things that need reading across items to notice.

So: run the review skill next, with a human in the loop. That is
[`REVIEW_GUIDE.md`](REVIEW_GUIDE.md). It produces a log, a report and an
updated annotation, and it is the review's verdicts — not the draft — that
make an annotation citable under this protocol.

Two smaller follow-ups, both out of scope for this skill: the per-paper **case
report** in `case-reports/`, written by hand, and any **schema change** a
candidate extension might justify. Extensions are promoted only when a second,
independent paper exercises the same gap, and promotion is always a human
decision.

---

## Troubleshooting

| symptom | cause and fix |
| --- | --- |
| `claude: command not found` after installing | Open a new terminal window; the running shell has not picked up the new `PATH`. |
| `/skills` does not list the skill | `.claude/skills/` did not exist when the session started, so Claude Code is not watching it. Restart Claude Code. Edits to an already-visible `SKILL.md` are picked up live and need no restart. |
| Claude answers the question but never loads the skill | The description did not match your phrasing, or the request looked too simple to need a skill. Invoke it by name: `/genetic-evidence-annotation`. |
| "I cannot find `protocols/PROTOCOL.md`" | Claude Code was not started at the repository root. Quit, `cd` to the checkout, start again. |
| "I cannot find `annotations/jossin2017.yaml`" (chat) | Bundle-layout bug; the reference annotations are in `exemplars/`. Tell it so — see [B5](#b5-run-the-annotation). |
| `python3: can't open file '.../scripts/validate_annotations.py'` | That path does not exist in the repository, whatever `README.md` and `SKILL.md` say. Use `src/python/main/forome/gem/validation/validate_annotations.py`, or `gem-validate` after `pip install -e .`. |
| `FAIL <path>` with a file-not-found note | Not a validation failure — the path is wrong. Check where you actually wrote the annotation. |
| Validator prints "No annotation files found" | It was run with no arguments somewhere without an `annotations/` directory. Pass the file path explicitly. |
| `ModuleNotFoundError: No module named 'forome'` | You invoked it as a module. Use the plain script path above, or set `PYTHONPATH=src/python/main`. |
| "must declare exactly one X" but X is right there | The value is not in the enumeration. Check `schema/dimensions.md`. |
| The skill refuses the paper | Usually correct. See [A10](#a10-when-the-skill-refuses). |
| Upload rejected: description too long | See [Known rough edges](#known-rough-edges). |

---

## Known rough edges

Audited 2026-09-17 against the repository as it stands. None of them blocks
the workflow; all of them will waste your time if you meet them cold.

- **`scripts/validate_annotations.py` does not exist in the repository.** Both
  `SKILL.md` files, `README.md` and the SHACL header still name it. The
  validator moved into the package at
  `src/python/main/forome/gem/validation/validate_annotations.py` (console
  script `gem-validate`). The bundled chat copy at `scripts/` *is* real — the
  path is correct inside a bundle and wrong in a checkout.
- **The annotation bundle's exemplar paths are wrong.** `SKILL.md` asks for
  `annotations/*.yaml`; the builder ships them at `exemplars/`. See
  [B5](#b5-run-the-annotation) for the workaround.
- **The `description` field in both `SKILL.md` files is around 620
  characters.** The Agent Skills specification allows 1024, but Anthropic's
  help centre documents a 200-character maximum for custom skills uploaded to
  the Claude app. If an upload is rejected, shorten the description — keeping
  the trigger phrases, which are what make the skill fire — and rebuild.
- **`version:` is a non-standard frontmatter key.** The specification puts it
  under `metadata:`. Harmless in Claude Code; if the app's uploader ever
  rejects the zip, this is the second thing to try removing.
- **`gem-coverage` does not regenerate `annotations/coverage.md`**, contrary
  to what both `README.md` and the paper say. It prints the table; redirect it
  yourself.
- **`mode_of_inheritance` has no published enumeration.** The SHACL shapes
  hard-require it for human-genetics gene-targeted items, but
  `schema/dimensions.md` gives no value table, so any token you coin will
  validate. Use the corpus spellings — `AUTOSOMAL_RECESSIVE`,
  `X_LINKED_RECESSIVE`, the sentinel `not_applicable_or_omitted`, and
  `COMPLEX` — and flag any further coinage.

---

## Where things live

| path | what it is |
| --- | --- |
| `skills/genetic-evidence-annotation/SKILL.md` | the skill itself |
| `protocols/PROTOCOL.md` | the mode-agnostic rules: decomposition, dimensions, source anchoring, flags, extensions |
| `protocols/PROTOCOL_AUTONOMOUS.md` | the autonomous workflow this skill implements, including its refusal conditions |
| `protocols/LABELING_EXAMPLES.md` | worked cases for the recurring judgement calls |
| `schema/dimensions.md` | every dimension and its legal values — the reference you will open most |
| `schema/genetic_evidence.shacl.ttl` | the machine-checkable schema |
| `schema/EXTENSIONS.md` | every candidate extension surfaced so far, and whether it was promoted |
| `annotations/` | the corpus; the four top-level files are the curator-authored reference annotations |
| `notes/ROADMAP.md` | the method-hierarchy migration, and what is planned but not yet specified |
| `build_skill_bundle.sh` | builds the upload zip for the Claude app |
| `docs/REVIEW_GUIDE.md` | the next step |
| `docs/STUDIO.md` | the Mapping Studio, for the UMLS crosswalk |
| `KNOWN_LIMITATIONS.md` | what the model, schema, corpus and tooling do not yet do |
