# GEM → UMLS / OMOP-CDM crosswalk harness

This directory holds a reproducible harness that maps the Genetic Evidence
Model (GEM) dimensional vocabulary to **UMLS** concepts (full, automated) and
positions it against the **OMOP CDM** (a few hand-authored illustrative
examples). It produces a new supplement section and a machine-readable
crosswalk.

It is **separate from** `paper/sections/s15_crosswalk.tex`, the existing
structural crosswalk (SO / HPO / NCBITaxon / ECO / SEPIO / GA4GH-VA / FHIR),
which it does not modify.

## Honesty by construction

The harness never invents concept identifiers.

- Nothing is reported as **mapped** unless a UMLS query actually returned a
  faithful concept (exact, or normalised name-equal).
- A query that returns candidates but no faithful match is **review** — the
  candidates are recorded for a curator to adjudicate, never silently mapped.
- A query that returns nothing is **unmapped** — reported as "no faithful UMLS
  concept", not forced.
- With no API key the harness still runs, but every entry is **pending**; it
  resolves nothing and writes no CUIs.

## Files

| File | Role |
|---|---|
| `dimensions_inventory.yaml` | **Input.** Curated list of every GEM dimension + value, each with the natural-language `query` term and an `expect` prior. Checked against the SHACL enums. |
| `build_umls_crosswalk.py` | **Harness.** Resolves each entry against UMLS (tiered exact → normalised → words) and writes `umls_crosswalk.yaml` + a coverage summary. |
| `uts_client.py` | UTS REST API client (`apiKey` auth), plus a fixture client (offline tests) and a null client (no-key runs). |
| `omop_cdm_examples.yaml` | **Input.** Hand-authored, illustrative OMOP-CDM positioning examples. |
| `render_crosswalk_tex.py` | Renders `umls_crosswalk.yaml` + `omop_cdm_examples.yaml` into the LaTeX supplement section. |
| `test_harness.py` | Offline unit tests (no network, no key). |
| `fixtures/` | Canned UTS responses (synthetic CUIs `C9000001…`) for the tests. |
| `umls_crosswalk.yaml` | **Output.** Machine-readable crosswalk (tracked once populated). |

## Prerequisites

```bash
pip install -r requirements.txt   # pyyaml, rdflib (check), requests (live)
```

A **UMLS licence** is required to resolve concepts. It is free but requires
registration and approval:

1. Request a UMLS Metathesaurus License: <https://uts.nlm.nih.gov/uts/signup-login>
2. Once approved, copy your API key from your UTS profile.
3. Provide it to the harness via the `UMLS_API_KEY` environment variable
   (e.g. in `.envrc`) — do not hard-code it. The key is sent to NLM's UTS
   service (`uts-ws.nlm.nih.gov`) on each query; raw responses are cached
   under `mapping/cache/` (git-ignored) so reruns are offline and auditable.

## Usage

```bash
# 1. Verify the inventory still covers the SHACL enumerations (no network).
python3 mapping/build_umls_crosswalk.py --check-inventory

# 2. Run the offline test suite (no network, no key).
python3 mapping/test_harness.py

# 3. Real run — resolve every dimension/value against UMLS.
export UMLS_API_KEY=...      # your UTS key
python3 mapping/build_umls_crosswalk.py
#   -> writes mapping/umls_crosswalk.yaml with real CUIs + a coverage line.

# 4. Render the supplement section from the crosswalk.
python3 mapping/render_crosswalk_tex.py
#   -> writes paper/sections/s18_umls_crosswalk.tex
```

Without a key, step 3 runs in **scaffold mode** (all entries `pending`); this
is the current committed state until the harness is run against UMLS.

## Wiring into the paper

The renderer writes `paper/sections/s18_umls_crosswalk.tex`. It uses
`longtable` and `booktabs`. To include it in the supplement:

1. Add `\usepackage{longtable}` to `paper/preamble.tex` (if not present).
2. Add `\input{sections/s18_umls_crosswalk}` to `paper/supplement.tex`.

This is deliberately left to the maintainer so the section is wired in only
once the harness has been run with a key and the mappings reviewed.

## After a real run

Inspect `umls_crosswalk.yaml`. Adjudicate every `review` entry (pick a
candidate or accept `unmapped`); for `unmapped` entries that should map,
refine the `query`/`sab` in `dimensions_inventory.yaml` and rerun. Then
regenerate the section and recheck the coverage line reported by the harness.
