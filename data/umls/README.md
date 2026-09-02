# GEM → UMLS / OMOP-CDM crosswalk harness

This directory holds a reproducible harness that maps the Genetic Evidence
Model (GEM) dimensional vocabulary to **UMLS** concepts (full, automated) and
positions it against the **OMOP CDM** (a few hand-authored illustrative
examples). It produces a new supplement section and a machine-readable
crosswalk.

The narrative record of the mapping decisions --- the evidence weighed,
the alternatives rejected, and the argument for each verdict --- lives in
[`DECISIONS.md`](DECISIONS.md).

The curation app itself is documented in the usage guide
[`STUDIO.md`](STUDIO.md).

It is **separate from** `paper/sections/s15_crosswalk.tex`, the existing
structural crosswalk (SO / HPO / NCBITaxon / ECO / SEPIO / GA4GH-VA / FHIR),
which it does not modify.

## Honesty by construction

The harness never invents concept identifiers.

- Nothing is reported as **mapped** unless a UMLS query actually returned a
  faithful concept (exact, or normalized name-equal).
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
| `build_umls_crosswalk.py` | **Harness.** Resolves each entry against UMLS (tiered exact → normalized → words), applies curator adjudications, and writes `umls_crosswalk.yaml` + a coverage summary. |
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
pip install -e .                  # dependencies are declared in pyproject.toml
```

A **UMLS license** is required to resolve concepts. It is free but requires
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

## Local UMLS index (PostgreSQL)

The UTS REST API is rate-limited, offers no fuzzy search and no "every concept
of semantic type X" query. For bulk mapping work you can index a UMLS release
locally and point the tooling at it through `PgUMLSClient`
(`forome.gem.umls.local_umls`), which implements the same `search()` /
`get_concept()` / `atoms()` / `sources()` contract as `UTSClient`, plus
`concepts_by_tui()`, `strings_like()` (trigram fuzzy match) and `release()`.
Relations, definitions and hierarchy rollups are **not** indexed locally and
stay on UTS.

### 1. Download the release

From <https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html>
(a UMLS license is required) take either

- the **UMLS Metathesaurus Full Release** (RRF; ~30 GB unpacked), or
- a **MetamorphoSys subset** you built yourself (RRF format, e.g. English only,
  a handful of vocabularies) — smaller and faster to load.

Only two files are used: `MRCONSO.RRF` (atoms/strings) and `MRSTY.RRF`
(semantic types). Gzipped copies (`MRCONSO.RRF.gz`) are read transparently.

### 2. Keep it outside the repository

The UMLS license forbids redistribution: keep the files **outside** the
checkout, e.g.

```
~/umls/2026AA/META/MRCONSO.RRF
~/umls/2026AA/META/MRSTY.RRF
```

**Never commit the RRF files, a subset, or a database dump.** Nothing under
`data/umls/` may contain Metathesaurus rows; the crosswalk only records the
CUIs and names the harness resolved.

### 3. PostgreSQL

Postgres.app (15+) works as is. Once, as a superuser:

```bash
PSQL=/Applications/Postgres.app/Contents/Versions/15/bin/psql
$PSQL -c 'CREATE DATABASE umls'
$PSQL -d umls -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm'   # trigram fuzzy search
# optional, for a later embedding index:  CREATE EXTENSION IF NOT EXISTS vector
```

Install the driver: `pip install -e '.[local]'` (psycopg 3).

### 4. Load

```bash
export GEM_UMLS_DSN=postgresql:///umls          # default if unset
gem-umls-load-local --rrf-dir ~/umls/2026AA/META --release 2026AA --dry-run   # counts + SQL, no DB
gem-umls-load-local --rrf-dir ~/umls/2026AA/META --release 2026AA
```

Options: `--lang ENG` (default; `ALL` keeps every language), `--sabs
SNOMEDCT_US,MSH,NCI` to keep only some vocabularies, `--skip-indexes` to load
the tables only, `--replace` to truncate a previous load. The loader streams
the files through `COPY` (never in memory), builds the indexes, prunes
semantic-type rows for concepts with no loaded atom, and appends a row to
`umls_release` (version, loaded_at, source_dir, row counts, filters).

Expectations for the English full release (~9 M `MRCONSO` rows, ~4 M
`MRSTY` rows) on a laptop: 10–20 minutes for the copy, a further 20–40
minutes for the indexes (the trigram GIN is the slow one), and roughly 10 GB
of database on disk (tables ~3 GB, indexes the rest). A MetamorphoSys subset is
proportionally faster.

### 5. Use it

```python
from forome.gem.umls.local_umls import PgUMLSClient
c = PgUMLSClient()                                  # reads GEM_UMLS_DSN
c.search("gene locus", search_type="exact")
c.search("locus", partial=True, semantic_types="T082")   # fuzzy, within a TUI
c.strings_like("genom wide assoc")                  # trigram neighbors
c.concepts_by_tui("T028,T087", limit=50)
c.release()
```

Search types map onto SQL as: `exact` → `lower(str) = lower(term)`; `words` →
English full-text (`plainto_tsquery`); `normalizedWords` → the `simple`
configuration (no stemming); `normalizedString` → whole punctuation-folded
string equality; `partial=True` → any-word match OR trigram similarity > 0.3,
ranked by similarity. `sabs` and `semantic_types` (TUIs) filter in SQL, as with
UTS.

### Loading straight from the full-release download (no MetamorphoSys)

The full release (`2026AA-full/`) ships the Metathesaurus as zip archives
(`2026aa-1-meta.nlm`, `2026aa-2-meta.nlm`) holding gzipped, split RRF parts. The two
files the index needs can be pulled out directly:

```bash
mkdir -p /opt/local/umls/2026AA/META && cd /opt/local/umls/2026AA/META
unzip -o -j /opt/local/umls/2026AA-full/2026aa-1-meta.nlm \
  '2026AA/META/MRCONSO.RRF.aa.gz' '2026AA/META/MRCONSO.RRF.ab.gz' '2026AA/META/MRCONSO.RRF.ac.gz' \
  '2026AA/META/MRSTY.RRF.gz' '2026AA/META/MRSAB.RRF.gz'
gunzip -c MRCONSO.RRF.aa.gz MRCONSO.RRF.ab.gz MRCONSO.RRF.ac.gz > MRCONSO.RRF && rm MRCONSO.RRF.a?.gz
gunzip -f MRSTY.RRF.gz MRSAB.RRF.gz
createdb umls && psql -d umls -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm'
gem-umls-load-local --rrf-dir /opt/local/umls/2026AA/META --release 2026AA \
  --dsn postgresql://$USER@localhost/umls --lang ENG
```

Measured on 2026AA (Apple Silicon, Postgres.app 15): MRCONSO 18,064,970 rows read,
10,755,691 English rows kept; MRSTY 3,876,406 rows; ~4 min COPY + ~5 min indexes;
3.4 GB on disk. Note that the raw full-release `MRSTY.RRF` carries only `CUI|TUI` (STN/STY
blank) — the loader fills the type names and tree numbers from the repository's Semantic
Network reference (`semantic_types.yaml`) after loading.
