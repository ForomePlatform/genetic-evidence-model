# Worksheet SOP: Converting a Google Sheet into Repository YAML

## Purpose

This standard operating procedure explains how to convert a completed manual-annotation worksheet from Google Sheets into a validated YAML annotation file in the repository.

The **study lead** performs the export, conversion, validation, and repository steps. The **annotator** completes the worksheet only. The annotator does not edit YAML files or use the repository.

This procedure applies to manual study passes, including:

- `h0.yaml`: initial manual annotation;
- `h1.yaml`: annotation after manual self-review; and
- `h0r.yaml`: washout re-annotation.

For the meaning of these pass names and the rules for sealing study outputs, see [EVALUATION_PROTOCOL.md](../protocols/EVALUATION_PROTOCOL.md).

---

## Prerequisites

Before starting, the study lead needs:

- a local checkout of this repository;
- Python 3.10 or later; and
- the GEM package installed from the repository root with the `[xl]`
  (worksheet) extra:

```shell
python3 -m venv .venv                  # Python 3.10 or later
source .venv/bin/activate
python -m pip install --upgrade pip    # editable installs need pip 21.3+
pip install -e '.[xl]'
```

Run every command below with this environment active. This one install
provides both tools used below: the worksheet converter
`gem-worksheet-to-yaml` (the `[xl]` extra adds `openpyxl`, which it needs)
and the validator `gem-validate`. Both can also be run as Python modules,
which helps if the console scripts are not on your `PATH`; see
[Step 3](#3-convert-the-worksheet-to-yaml) and
[Step 4](#4-validate-the-yaml).

---

## 1. Create one worksheet copy for each pass

The shared Google Sheet named `GEM_annotation_worksheet` is the clean master template. No study annotations are entered into the master sheet.

Every pass of every paper gets its own copy. Each pass has a **pass
code** from [EVALUATION_PROTOCOL.md](../protocols/EVALUATION_PROTOCOL.md)
§8 and a **pass name**, the name of its output:

| Manual pass | Pass code | Pass name |
|---|---|---|
| Initial manual annotation | `H0` | `h0` |
| Manual self-review | `SR` | `h1` |
| Washout re-annotation | `WR` | `h0r` |

The pass name names the Google Sheet copy, the raw export, the output
directory and the YAML; the pass code goes on the copy's `Paper` tab:

1. **Initial annotation.** The annotator copies the master
   (**File → Make a copy**, ticking *Share it with the same people* so the
   study lead can open the copy), names the copy
   `<paper-id>-<pass name>`, for example `marques2025-h0`, and on the
   `Paper` tab sets `paper_id` and `pass_code` (`H0`).
2. **Self-review.** Once the study lead has confirmed the `h0` sheet is
   final, the annotator copies it — not the master — names the copy, for
   example, `marques2025-h1`, and on the copy:
   - changes `pass_code` to `SR`;
   - replaces `annotation_started` and `annotation_finished` with the
     self-review's own dates; and
   - deletes the `Effort` rows from row 3 down, keeping the header and
     hint rows. The H0 sittings stay recorded in the `h0` sheet; left in
     the copy, they would be reported a second time, as self-review
     effort.

   Then the annotator revises that copy. The `h0` sheet is never edited
   again.
3. **Washout re-annotation (one or two papers only).** The annotator
   copies the master afresh, names it, for example, `marques2025-h0r`,
   sets `paper_id` and `pass_code` (`WR`), and annotates from scratch
   without consulting any earlier pass, per §8.5.

The annotator completes that copy, and only that copy. The grey cells on
the `Paper` tab, `protocol_version` and `worksheet_version`, are
prefilled and stay as they are.

The [master template](../templates/GEM_annotation_worksheet.xlsx) is
also stored in this repository.

The repository version is the archival template. The shared Google Sheet is the working template used by the annotator.

Do not change the worksheet structure, column names, dropdown values,
or worksheet tab names during the study. If a structural change is
needed, it must be handled through the amendment process in
[EVALUATION_PROTOCOL.md](../protocols/EVALUATION_PROTOCOL.md).

---

## 2. Export the completed worksheet from Google Sheets

When the annotator reports that a worksheet is complete:

1. Open the completed per-pass Google Sheet.
2. Select **File → Download → Microsoft Excel (.xlsx)**.
3. Save the downloaded file in `study/raw/<paper-id>/`, named by pass,
   for example: `study/raw/marques2025/h0.xlsx`.

`study/raw/` holds the exported worksheets, the converter's inputs — one
directory per paper, one file per pass. A later pass must never overwrite
an earlier pass's export: a sealed pass's input is part of the study
record. Never save an export under `annotations/`.

Do not export or convert the clean master worksheet. Only convert the completed copy for the relevant paper and pass.

---

## 3. Convert the worksheet to YAML

Run:

```shell
scripts/study-convert.sh <paper-id> <pass>
```

For example:

```shell
scripts/study-convert.sh marques2025 h0
```

The script works from any directory, prints the command it expands to, and
takes no other options; in particular it cannot pass `--force`. It is
equivalent to running, from the repository root:

```shell
gem-worksheet-to-yaml study/raw/<paper-id>/<pass>.xlsx \
    study/processed/<paper-id>/<pass>/<pass>.yaml \
    --effort study/processed/<paper-id>/<pass>/effort.csv
```

(module form: `python3 -m forome.gem.extraction.worksheet_to_yaml`, same
arguments). The converter creates `study/processed/<paper-id>/<pass>/` if
it does not exist yet.

Here `<pass>` is the pass name from the table in
[Step 1](#1-create-one-worksheet-copy-for-each-pass).

### What the converter does

The converter is deterministic. It does not use AI and does not make annotation decisions.

It converts values entered or selected by the annotator into repository YAML. It records the `Paper` tab's `pass_code`, `protocol_version` and `worksheet_version` in the YAML's provenance. When `--effort` is given and the conversion succeeds, it also copies the worksheet's `Effort` tab, as typed, into that CSV, replacing any file already there; each row is prefixed with `paper_id`, `pass_code` and `annotator`, so the CSV carries every field of protocol §10. It checks that:

- values selected from controlled lists match the workbook’s `Enums` sheet;
- required fields are present;
- every evidence item has at least one assertion, and every assertion
  names an item on the `Items` tab;
- item ids and candidate-extension ids are unique, and assertion numbers
  are whole numbers;
- every candidate-extension reference on the `Items` tab names an id on
  the `Candidate Extensions` tab;
- the worksheet is version 2: `worksheet_version`, a `protocol_version`
  that reads as a version such as `1.1`, and a `pass_code` of `H0`, `SR`
  or `WR` are on the `Paper` tab, and the `Effort` tab has all of its
  columns (see [Worksheet versions](#worksheet-versions)); and
- the `pass_code` matches the output: `SR` must be written to `h1.yaml`,
  and so on, and the output's paper directory must equal `paper_id`. This
  catches a sheet copied from an earlier pass that still carries the old
  code.

It reports as warnings, without blocking the conversion:

- key phrases longer than 15 words;
- `Effort` sittings dated before `annotation_started` (typically rows
  copied from an earlier pass) or in the future (typically a mistyped
  year);
- a blank `annotation_finished` on the `Paper` tab, in which case the
  YAML's `annotated_at` defaults to the conversion date and the YAML
  records `annotated_at_defaulted: true` in its conversion block;
- candidate-extension ids not in the `CE-1`, `CE-2`, … form the worksheet
  asks for. An id typed as a bare number, such as `1`, is accepted and kept
  exactly as typed: the converter does not renumber or rename ids; and
- some conditional fields that look missing or out of place. These checks
  are advisory and incomplete: a blank `mode_of_inheritance` on a
  `HUMAN_GENETICS` + `GENE` item, for example, is caught only by the
  validator in [Step 4](#4-validate-the-yaml), which is authoritative.

`candidate_extension_refs` may separate ids with semicolons or commas.
`hpo_terms` and `special_considerations` must use semicolons: a comma
there stays inside a single value, without a warning.

### If conversion fails

If the converter finds an error, it prints an error report and writes
nothing. Any YAML or effort CSV from an earlier run stays at the output
paths untouched — so validate or seal a file only if the converter's most
recent run printed `Wrote <that path>`.

When this happens:

1. Send the error lines to the annotator. Annotation values are the
   annotator's decisions; the study lead does not fill in or change them.
   One exception: a `predates version 2` error is not about annotation
   content. The study lead fixes it by migrating the sheet, as described
   in [Worksheet versions](#worksheet-versions).
2. The annotator corrects their Google Sheet.
3. Export again ([Step 2](#2-export-the-completed-worksheet-from-google-sheets))
   and convert again.

Do not use the `--force` option the converter mentions: it writes YAML
despite errors, and such a file must not be validated or sealed. Do not
correct the generated YAML by hand, and do not ask the annotator to edit
YAML or repository files.

---

## 4. Validate the YAML

After conversion, validate the YAML file.

Run:

```shell
gem-validate study/processed/<paper-id>/<pass>/<pass>.yaml
```

For example:

```shell
gem-validate study/processed/marques2025/h0/h0.yaml
```

Alternatively, run the validator as a module:

```shell
python3 -m forome.gem.validation.validate_annotations \
    study/processed/marques2025/h0/h0.yaml
```

A validation failure means the worksheet must be corrected — never the
YAML. Send the annotator the validator's messages and the item ids they
name; the fix is an annotation decision, and annotation decisions are the
annotator's. For a conditional-dimension failure, such as
`mode_of_inheritance is required` on a `HUMAN_GENETICS` + `GENE` item,
the annotator enters a value in that cell, records the reasoning in
`notes_uncertainties`, and adds a candidate extension if no value fits.
Listing the dimension on the `Omitted Dimensions` tab does not satisfy
the validator.

Then re-export
([Step 2](#2-export-the-completed-worksheet-from-google-sheets)) and
re-convert ([Step 3](#3-convert-the-worksheet-to-yaml)). Never edit the
YAML file manually to resolve a validation failure.

---

## 5. Store and seal the study files

During the evaluation study, exported worksheets are stored in
`study/raw/` and outputs in `study/processed/` — one directory per paper,
one subdirectory per pass:

```text
study/
├── raw/
│   └── marques2025/
│       ├── h0.xlsx             exported worksheets (converter inputs)
│       └── h1.xlsx
└── processed/
    └── marques2025/
        ├── h0/
        │   ├── h0.yaml
        │   └── effort.csv
        ├── h1/
        │   ├── h1.yaml
        │   ├── effort.csv
        │   └── changelog.md    self-review change log (protocol §8)
        └── h0r/                washout papers only (§8.5)
```

Each pass's effort log lives in that pass's directory. The `h1` change
log records what the self-review changed relative to `h0`; the study lead
compiles it from the differences between the two worksheets and anything
the annotator reports. It records only the annotator's decisions and is
compiled without AI assistance (§8.1). The study-level files named in the protocol
(`study/RULINGS.md`, `study/PAPERS.md`, `study/AMENDMENTS.md`), and the
seal ledger `study/SEALS.md`, sit at the top of `study/`.

### Sealing

Per [EVALUATION_PROTOCOL.md](../protocols/EVALUATION_PROTOCOL.md) §9,
each completed stage receives a commit, a tag, a timestamp, and file
hashes. Concretely, for a pass:

1. Stage the pass's raw export and processed directory, and commit.
2. Record the file hashes. Use git's own content hashes rather than
   hashing the bytes on disk with an OS tool: the converter writes LF
   line endings on every platform, and git hashes content after its
   line-ending normalisation, so these hashes reproduce everywhere:

   ```shell
   git ls-files -s study/raw/<paper-id> study/processed/<paper-id>
   ```

3. Tag the commit, for example `study-marques2025-h0`, putting the hash
   listing, the date, and the time in the tag message.
4. Append the same record (timestamp, seal commit id, tag name, file
   list with hashes, any notes) to `study/SEALS.md`, the append-only
   seal ledger, and commit that as its own small commit. The ledger
   exists because a commit cannot contain the hashes of its own
   content; the annotated tag and the ledger both carry the record, and
   the ledger is the copy a reader browsing the repository will find.

A recorded hash can be verified later, on any platform, with
`git hash-object <file>`; for a stronger digest alongside git's, record
`git cat-file blob <hash> | shasum -a 256` for each listed hash.

During the study:

- do not place study annotations in `annotations/`;
- do not use study annotations as examples for an autonomous AI run;
- do not replace a sealed output without following the documented amendment or correction procedure; and
- keep each pass's effort log in that pass's directory.

After the study closes, validated study annotations may be merged into `annotations/` with their full provenance.

---

## Notes

- The worksheet’s `Example` tab is reference material for the annotator. The converter never reads it, so whether it is present makes no difference.
- The effort CSV is study data. It lives in `study/processed/<paper-id>/<pass>/` beside the YAML file.
- The converter creates YAML from the worksheet. It is not a substitute for validation.
- A successful conversion is not sufficient on its own. Every converted YAML file must also pass `gem-validate`.

## Worksheet versions

The converter reads worksheet **version 2**, stated by the prefilled
`worksheet_version` cell on the `Paper` tab. Version 2 added:

- on the `Paper` tab: `pass_code` (dropdown), and the prefilled
  `protocol_version` and `worksheet_version`;
- on the `Effort` tab: `start_time`, `stop_time`, `interruptions`,
  `external_resources` and `technical_problems`, completing the fields
  required by protocol §10;
- on the `Enums` tab: the `PASS_CODE` and `CE_ID` lists, and the
  `correction` and `calibration` activities; and
- a dropdown for `ce_id` on the `Candidate Extensions` tab.

A sheet copied from the earlier, unversioned template is rejected with
`'worksheet_version' is empty: this worksheet predates version 2`. To
migrate one, the study lead edits the annotator's Google Sheet:

1. On the `Paper` tab, add three rows below the existing ones, keys in
   column A and values in column B: `pass_code` with the pass code,
   `protocol_version` with the version of
   [`protocols/PROTOCOL.md`](../protocols/PROTOCOL.md) (currently `1.1`),
   and `worksheet_version` with `2`. Format the two version cells as plain
   text (**Format → Number → Plain text**) before typing, so `1.1` is not
   stored as a number.
2. On the `Effort` tab, add five columns with the header names
   `start_time`, `stop_time`, `interruptions`, `external_resources` and
   `technical_problems`, and copy the hint texts in row 2 from the
   template. The converter finds columns by header name, so they may go
   after the existing ones. Leave the cells of sittings already logged
   blank rather than reconstructing them.
3. On the `Enums` tab, add `correction` and `calibration` to the
   `ACTIVITY` list, and widen the data validation on the `Effort`
   activity column (**Data → Data validation**) to include them.
   Otherwise the annotator cannot log correction time, which protocol §10
   requires.
4. Re-export and convert as usual.

The other version-2 dropdowns (`pass_code`, `ce_id`) are not needed for
conversion and need not be migrated. Migration requires edit access to
the annotator's sheet.
