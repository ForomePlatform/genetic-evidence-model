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
| `build_umls_crosswalk.py` | **Harness.** Resolves each entry against UMLS (tiered exact → normalised → words), applies curator adjudications, and writes `umls_crosswalk.yaml` + a coverage summary. |
| `uts_client.py` | UTS REST API client (`apiKey` auth; search + concept/definition lookups), plus a fixture client (offline tests) and a null client (no-key runs). |
| `adjudicate_ui.py` | **Curation UI.** A local, Metathesaurus-integrated web app for reviewing/curating the mappings (see below). |
| `adjudications.yaml` | **Input.** Curator decisions (accept a CUI / mark unmapped), applied by the harness. Edited via the UI. |
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

## Curating with the adjudication UI

`umls_crosswalk.yaml` is not a good review surface. Use the local UI instead:

```bash
export UMLS_API_KEY=...            # or have it in .envrc
python3 mapping/adjudicate_ui.py   # opens http://127.0.0.1:8765/
```

For each dimension/value it shows the GEM meaning (from `dimensions.md`), the
query used, the current decision, and the query's candidate concepts. You can:

- **search the Metathesaurus live** for a better concept,
- read any concept's **definition + semantic type** (the `def` button),
- **Accept** a concept (from the candidates or a search result), **Mark
  unmapped**, or **Clear** the decision — written straight to
  `adjudications.yaml`,
- **Rebuild crosswalk** to rerun the harness and refresh statuses.

Honest by construction: accepting a concept you found via search (not among the
query's candidates) makes the harness fetch it live from UMLS on rebuild to
confirm it is real; the harness never records a CUI it cannot resolve. The UI
is local (not a hosted page) because it must reach the licensed UTS API with
your key and write files; the key stays server-side and is never sent to the
browser.

## Axis semantic types (values → concepts, axes → types)

A GEM dimension is two levels of thing, mapped to two levels of UMLS:

- a dimension **value** names a specific thing → a Metathesaurus **concept** (CUI);
- a dimension **axis** is a classification kind → a UMLS **Semantic Type** (TUI).

Each axis is assigned a semantic type (`semantic_type: T0xx` on the axis in
`dimensions_inventory.yaml`, or `accept_sty` in `adjudications.yaml` / the UI),
and **that type's subtree constrains the search for the dimension's values** —
so a value is only ever mapped within its axis's semantic branch, and axis and
values reconcile by construction. Example: `resolution` axis = `T082 Spatial
Concept`, so `resolution/GENE` resolves to *Gene Locus* (a spatial concept),
**not** the gene *entity* — the same token maps differently under
`target_type` (Gene or Genome). Where no in-branch concept exists, the value is
honestly **unmapped**.

The Semantic Network reference is fetched by `fetch_semantic_network.py`
(→ `semantic_types.yaml` + a browsable `semantic_network_tree.md`);
`semantic_types.py` provides the subtree lookups. In the UI, an **axis** row
shows a semantic-type picker (the 127 types, filterable); a **value** row's
search is auto-constrained to the axis type.

## After a real run

Curate with the UI above (or, by hand: edit `adjudications.yaml`, or refine a
`query`/`sab` in `dimensions_inventory.yaml` and rerun). Then regenerate the
section (`render_crosswalk_tex.py`) and recheck the coverage line reported by
the harness.
