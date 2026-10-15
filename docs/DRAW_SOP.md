# SOP: running the typical-stratum draw

The draw executes the sampling procedure adopted in `study/PAPERS.md`
Section 1.5 (seed 0, venue slots, citation strata, fallbacks). Two roles
are involved:

- the **human annotator** screens candidates in a web page, one at a
  time, against the protocol Section 6.4 intake criteria;
- the **study lead** appends the recorded outcomes to the repository
  log, where `scripts/study_draw.py` revalidates them, and commits.

Neither role chooses papers: the candidate order is fixed by the seed
and the frozen frame, and both the page and the script refuse anything
out of order.

## Annotator: screening in the web page

Open the screening page at the address the study lead gives you. Use
one browser and one tab for all screening, since unsent outcomes are
held in that browser.

1. The page shows one paper awaiting intake: title, journal, dates,
   citation count, and links to PubMed, Europe PMC and the publisher.
   Read the paper through those links. **No AI assistance** of any kind
   during screening (protocol Section 8.1); ordinary literature
   databases are allowed.
2. Answer the four gates (criteria 1 to 4). All four must hold for a
   pass. If any fails, describe the evidence; keep it factual and
   anchored to the criterion. The failed criterion number is recorded
   with it.
3. On a pass, record the two classifications: expected
   candidate-extension load (criterion 5) and model familiarity
   (criterion 8). These never affect acceptance; they are recorded for
   the analysis.
4. Enter your screening time in whole minutes (logged as intake effort,
   separate from annotation effort), then record the verdict and
   confirm. **Outcomes are final**; the "Remove last outcome" button is
   only for use on the study lead's explicit instruction, and only
   works on outcomes not yet synchronised.
5. After each session, copy the rows under "Outcomes awaiting
   synchronisation" and email them to the study lead. Until the study
   lead commits them, they exist only in your browser, so do not clear
   the browser's site data; the amber banner reminds you while any are
   pending. They disappear from the pending list on their own once the
   synchronised log includes them.
6. An amber fallback banner (a slot dropping its citation stratum, or a
   group collapsing into another) is part of the recorded design and
   needs no action. Stop and contact the study lead only on a red
   "does not match the procedure" lock.

## Study lead: synchronising outcomes into the repository

On receiving rows from the annotator:

1. Append them, in the order sent, to `study/draw_log.csv`.
2. Run `python3 scripts/study_draw.py sync` from the repository root.
   This replays the whole log against the recorded procedure and
   regenerates the draw record in PAPERS.md Section 1.9. A refusal
   means the rows deviate from the procedure; investigate before
   committing anything.
3. Commit `study/draw_log.csv` and `study/PAPERS.md` together and push.
   On GitHub Pages the push redeploys the page with the updated log;
   on a plain web server, re-copy `study/draw_log.csv` to the site
   directory.

`python3 scripts/study_draw.py status` shows the slot board;
`list <SLOT> -n 20` shows a slot's upcoming candidate order for audit.
The CLI `record` subcommand remains available as a fallback path if the
web page is unusable; it enforces the same rules.

## Deployment

The page is fully static: three files served from one directory,
`index.html` and `draw_data.json` (from `scripts/intake_screen/`) plus
the current `study/draw_log.csv`.

- GitHub Pages: the workflow `.github/workflows/intake-pages.yml`
  assembles and deploys the three files on every push to `master` that
  touches them. Enable it once in the repository settings (Pages,
  Source: GitHub Actions). Note that a GitHub Pages site is public.
- Any other web server: copy the three files into a served directory,
  and re-copy `study/draw_log.csv` after every sync commit.

`draw_data.json` is regenerated with `python3
scripts/export_draw_data.py` and changes only if the frame or the
procedure changes, which after adoption means an amendment.

## Extension slots

The base draw fills 8 slots (A1, A2, B1, B2, C1, D1, E1, F1). If the
study lead decides on 9 or 10 typical papers, the annotator opens the
page with `?typical=9` or `?typical=10` appended to the address, and
script commands take `--typical 9` or `--typical 10`; this opens the
pre-specified slots C2 then A3.

## Rules and recovery

- Never edit `study/draw_log.csv` or the Section 1.9 block by hand
  (appending the annotator's exported rows verbatim is the one
  exception). Both the page and the script replay the full log on
  every use and lock on any deviation; that lock is the tamper guard
  working, not a bug.
- If the script refuses a sync, restore the log from git
  (`git checkout -- study/draw_log.csv`) and compare it with the rows
  the annotator sent; discrepancies are investigated before any
  further screening.
- A genuinely mis-entered outcome is handled by the study lead: if it
  is still pending in the annotator's browser, the annotator removes it
  on instruction ("Remove last outcome"); if it is already committed,
  the correction is recorded in `study/DEVIATIONS.md`. Outcomes are an
  audit record, not editable state.
- If the annotator's browser loses its pending outcomes before they
  were sent (cleared site data, crashed profile), the affected papers
  are simply re-screened: the candidate order recomputes identically.
- The study lead may audit recorded outcomes at any time; audits
  cannot reverse outcomes (protocol Section 6.4).
