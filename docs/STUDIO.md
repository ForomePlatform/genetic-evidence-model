# Mapping Studio — usage guide

A local, single-user web app for curating a crosswalk from a dimensional
vocabulary to UMLS. Despite living in the GEM repository, **nothing in the
tool is genomics-specific**: it operates on a workspace of *dimensions*
(each bound to a UMLS Semantic Type as its search axis) and *values*
(tokens adjudicated to UMLS concepts), whatever the domain. GEM's own
mapping (`data/umls/`) is one such workspace.
The `gem-` prefix marks the tool's origin in the GEM project, not its
scope; if you prefer the letters to mean something here, read them as
*Generic Evidence Mapping* Studio.

Console script: `gem-mapping-studio` (alias `gem-umls-adjudicate`).

## Two ways to use it

|  | **A new mapping** | **The GEM mapping** |
| --- | --- | --- |
| what you are building | your own vocabulary → UMLS crosswalk, in any domain | the crosswalk published in this repository |
| install | `pip install gem-mapping-studio` | the same, or `pip install -e '.[local,dev]'` in a checkout |
| workspace | a new, empty directory you choose | the repo's `data/umls/` |
| start from | [A new mapping from scratch](#a-new-mapping-from-scratch) | [Working on the GEM mapping](#working-on-the-gem-mapping) |

Either way the Studio needs your own (free) UMLS API key: see
[The UMLS key](#the-umls-key). Without one it starts, and the workspace is
fully browsable, but it is **read-only** — every control that would change a
dimension, a value or a decision is disabled. An axis, a value or a mapping
the Metathesaurus has not confirmed is not a mapping, so there is no offline
editing mode.

---

## A new mapping from scratch

Nothing below mentions genetics because nothing about it is genetic. The
worked example maps a two-value `severity` vocabulary; substitute your own.

### 1. Install

```bash
pip install gem-mapping-studio
```

That is the whole dependency: the released tool needs a UTS key and nothing
else. (A local UMLS index is an optional accelerator — see
[Local UMLS index](#local-umls-index-optional-but-recommended).)

### 2. Start it on an empty directory

```bash
mkdir ~/my-mapping
gem-mapping-studio --data-dir ~/my-mapping      # opens the browser on port 8765
```

The directory may be empty or may not exist yet; the Studio treats an empty
workspace as a fresh one and says so on the Home screen.

### 3. Connect UMLS

The first run without a key opens the **Connect UMLS** dialog. See
[The UMLS key](#the-umls-key) for what it walks you through. Until a key is
accepted the Studio is read-only, so do this before curating.

### 4. Create a dimension

**New dimension** (rail foot, or the Home button) defines an *axis*:

* **dimension** — its name, e.g. `severity`. Letters, digits, `_` and `-`.
* **tier** — `core`, `conditional` or `candidate`; drives the navigation
  grouping. **activation** records the rule that switches a conditional
  dimension on (e.g. `knowledge_domain: GENE_FUNCTION`).
* **query** + **Run query** — search UMLS and read off the semantic *types*
  of the matching concepts. An axis maps to a **type**, not a concept.
* the **semantic type** itself — chosen from those results or from the full
  127-type Semantic Network browser, with each candidate's subtree and the
  filter breadth it implies shown before you commit.
* **note**, **preferred vocabularies** (optional) — the latter overrides the
  workspace-wide order from ⚙ Settings for this dimension only.

For the example: dimension `severity`, query *Qualitative concept*, type
**T080 Qualitative Concept**. **Create axis** writes it.

The type's subtree becomes the search scope for every value of the
dimension, so axis and values reconcile by construction.

### 5. Add values

On the dimension page, **Add value**:

* **token** — the identifier in your vocabulary, e.g. `MILD`. No spaces.
* **query** — the term sent to UMLS for it, e.g. *Mild*. It is pre-filled
  from the token as you type (`HUMAN_GENETICS` becomes *Human genetics*);
  edit it when the UMLS term is worded differently.
* **expect** — your honest prior that a faithful concept exists: `likely`,
  `uncertain` or `unlikely`. Triage only; it never overrides the harness.
* **preferred source vocabulary** (optional) — e.g. `MSH`.
* **note** (optional) — what the token means, or why the query is worded so.
* **kind** — `value` for an enumerated token, or `common_value` for a
  convention on an open dimension (free-text values, listed by custom).

Saving writes the value to the workspace inventory and re-resolves that
dimension immediately, so the token comes back with its candidates and a
status rather than waiting for a rebuild. The pencil and bin on each row
edit and remove it. Two behaviours worth knowing:

* **Renaming a token carries its decision with it** — the adjudication is
  re-keyed, so a corrected token does not abandon an argued mapping.
* **Deleting a value deletes its decision** — leaving it behind would
  resurrect a mapping you never re-made if the token were added again. The
  confirmation says so when there is one to lose.

Values may equally be added by editing `dimensions_inventory.yaml` by hand;
the Studio round-trips that file, so your comments and layout survive every
write it makes.

### 6. Adjudicate and rebuild

Open a value to search UMLS, read the evidence, and record a decision — see
[Search](#search-when-the-obvious-query-fails) and
[Recording decisions](#recording-decisions). **Rebuild** (all, or one
dimension) re-queries UMLS for the values the inventory defines and rewrites
`umls_crosswalk.yaml`; it never invents values. A value in the inventory but
not yet in the crosswalk shows as `pending`, flagged *not resolved* in the
worklist.

The three YAML files in `~/my-mapping` are the deliverable: readable,
diff-friendly, and yours.

---

## Working on the GEM mapping

The workspace is the repository's `data/umls/`. Two equivalent ways in:

**From a checkout** — the usual choice when you are also changing the
schema, the paper or the harness, since the Studio then runs the code in
your working tree:

```bash
git clone https://github.com/ForomePlatform/genetic-evidence-model
cd genetic-evidence-model
pip install -e '.[local,dev]'      # editable; [local] adds the PostgreSQL index, [dev] pytest
gem-mapping-studio                 # workspace defaults to the repo's data/umls
```

**With the released tool** — when you only want to curate:

```bash
pip install gem-mapping-studio
gem-mapping-studio --data-dir /path/to/genetic-evidence-model/data/umls
```

Run from inside a checkout with no `--data-dir`, the Studio finds the repo
root by walking up and uses `data/umls` as the workspace; `$GEM_DATA_DIR`
overrides it. Reference data (the Semantic Network, the SHACL schema,
`dimensions.md`) resolves to the repo's copies in a checkout and to the
copies packaged in the wheel otherwise.

Edits land in `data/umls/dimensions_inventory.yaml`,
`adjudications.yaml` and `umls_crosswalk.yaml` — commit them like any other
change. GEM's value set is checked against the SHACL enumerations by
`gem-umls-crosswalk --check-inventory`, so adding a value here means adding
it to `schema/genetic_evidence.shacl.ttl` too, or the check will report the
drift. The narrative record of the decisions behind the published mapping is
[`data/umls/DECISIONS.md`](../data/umls/DECISIONS.md).

---

## The UMLS key

The Studio searches UMLS through the NLM UTS API with your own (free) key.
The **Connect UMLS** dialog walks through it:

1. Create a UTS account and request the UMLS license at
   <https://uts.nlm.nih.gov/uts/signup-login>. NLM reviews the request,
   usually within a few business days; the key does not work before approval.
2. Sign in and copy the API key from your profile,
   <https://uts.nlm.nih.gov/uts/profile>.
3. Paste it into the dialog. The Studio makes one test request before
   accepting it, and (if you leave *Remember on this machine* ticked) stores
   it in `~/.config/forome-gem/umls_api_key`, readable by you only.

The key never leaves your machine: the browser sends it to the local Studio
server, which proxies UMLS. Alternatives to the dialog: `export
UMLS_API_KEY=...` before starting (never commit it), or a repository
`.envrc` under direnv. Lookup order is the environment, then `.envrc`, then
the key file; ⚙ Settings shows which one is in use.

## Options

`--data-dir DIR` (workspace; defaults to the repo's `data/umls` or
`$GEM_DATA_DIR`; may be empty), `--port N` (or `$PORT`), `--no-browser`,
`--search-backend auto|uts|local`.

The **?** next to ⚙ Settings opens this guide; `$GEM_STUDIO_HELP_URL`
repoints it at a deployment's own copy.

## The workspace

Three YAML files, all human-readable and diff-friendly:

| file | role |
| --- | --- |
| `dimensions_inventory.yaml` | the configuration: dimensions, tiers/order/activation, axis (query + semantic type), values, preferred vocabularies. Comments are preserved on every write. |
| `adjudications.yaml` | the curator's decisions: accepted CUI + relation + note, or an argued `unmapped` with a structured rationale (rejected candidates with A–D criteria, search protocol). |
| `umls_crosswalk.yaml` | the built snapshot the UI tables render; regenerated by **Rebuild** (never edit by hand). |

A decision is recorded immediately in `adjudications.yaml` but appears in
the dimension tables only after a **Rebuild** (scoped to the dimension, or
full). Until then the value's own page shows it as a pending acceptance.

## Search, when the obvious query fails

The value page offers an escalation ladder:

1. **Match modes** — exact / normalized words / normalized string / words /
   partial (typo-tolerant trigram, local index only).
2. **Scope** — restrict to the axis semantic type, or lift the restriction.
3. **Expand terms** — substitutes each query word with its narrower
   (is_a-descendant) concepts across major vocabularies ("organism" also
   searches "animal", "plant", ...).
4. **↓ desc** — walk a found concept's source hierarchies down (multi-SAB
   breadth-first), e.g. from *Genetics* down to *Genomics*.
5. **Browse axis** — enumerate every concept of the axis semantic type with
   a live filter (local index only).
6. **CUI paste** — a pasted `C0000000` looks the concept up directly.

Every result row shows the preferred source atom (configure preferred
vocabularies under ⚙ Settings), semantic type as STN/STY, definitions,
and relation/rollup views for evidence gathering.

## Recording decisions

* **accept** — pick a concept, choose *accept as* (exact / close / broader
  / narrower / related). Direction convention: **narrower = your token is
  more specific than the concept; broader = more general**. Changing
  *accept as* re-records the decision live, including on a harness mapping
  not yet confirmed.
* **Confirm mapping** — one click to adopt the harness's automatic match
  as a curated decision.
* **No faithful concept** — an `unmapped` verdict must carry an argument:
  rejected near-misses (each with the criterion it fails: A denotation,
  B granularity, C set membership, D domain sense) and the search protocol
  that failed to find a proxy. "We could not find one" is a gap
  (`unresolved`), not a verdict.
* The Home **worklist** tracks everything still needing eyes: not-resolved /
  review / unconfirmed / unresolved / no-rationale / untyped-axis, with
  filters.

## Local UMLS index (optional but recommended)

The released tool needs only a UTS API key. A licensed UMLS copy can be
loaded into PostgreSQL for fast, controllable matching (full-text,
trigram, axis enumeration):

```bash
createdb umls && psql -d umls -c 'CREATE EXTENSION pg_trgm'
gem-umls-load-local --rrf-dir /path/to/2026AA/META --release 2026AA
export GEM_UMLS_DSN=postgresql://localhost/umls   # if not the default
```

`--search-backend auto` (default) uses the index when present and falls
back to UTS; ⚙ Settings shows which backend is live and why. The index is
**never redistributed** — it is derived from licensed UMLS content. It
accelerates search only: it does not unlock editing, which still requires a
UTS key.

## Companion command-line tools

| command | purpose |
| --- | --- |
| `gem-umls-crosswalk` | rebuild the crosswalk snapshot outside the UI |
| `gem-umls-render` | render the crosswalk as a LaTeX supplement table |
| `gem-umls-load-local` | load MRCONSO/MRSTY RRF into PostgreSQL |
| `gem-umls-sweep` | run a pre-registered search-protocol sweep (results stay local: they contain UMLS-derived strings) |
| `gem-umls-classify-credibility` | classify sweep results by rejection family |

## Conventions the workspace enforces

* Nothing is written without a connected UMLS key.
* The axis semantic type is a **search scope, not a validity constraint**:
  a curator may deliberately accept an out-of-axis concept (note why).
* Within one ordered scale, two values must not share an anchor concept
  (criterion C) — across dimensions, reuse is fine.
* Comments in the inventory survive every write (ruamel round-trip).
* The harness never fabricates identifiers: an accepted CUI must be a
  query candidate or confirmable live against UMLS.
