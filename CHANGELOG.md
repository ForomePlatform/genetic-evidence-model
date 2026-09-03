# Changelog

All notable changes to this repository are recorded here. The format follows
[Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/). Version numbers
from 0.2.0 on follow [Semantic Versioning](https://semver.org/) and are the
version of the `gem-mapping-studio` Python package; the two earlier tags
(`v-1.0`, `icbo-final`) predate the package and mark manuscript submissions.
Each tagged release from 0.2.1 on is archived on Zenodo (concept DOI
[10.5281/zenodo.22260686](https://doi.org/10.5281/zenodo.22260686)).

## [0.2.5] - 2026-09-03

*(Tags `v0.2.3` and `v0.2.4` were `gem-mapping-studio` package-version bumps
without a repository release; their changes are recorded here.)*

### Added
- Mapping Studio: **value curation**. A dimension's values could only ever be
  added by hand-editing `dimensions_inventory.yaml`, so a workspace built from
  scratch in the UI could acquire dimensions but never a single value, and the
  empty-state hint pointed at **Rebuild**, which only re-resolves values the
  inventory already defines. The dimension page now has **Add value** and
  per-row edit / remove controls (`POST /api/value`, `/api/value/delete`),
  writing token / query / `expect` / `sab` / note to the inventory through the
  comment-preserving round-trip and re-resolving that dimension on the spot.
  Renaming a token re-keys its adjudication; deleting a value drops its
  adjudication, so a re-added token cannot resurrect a mapping nobody re-made.
  The **New value** dialog pre-fills the UMLS query from the token as it is
  typed (`HUMAN_GENETICS` becomes *Human genetics*) until the query is
  edited by hand; previously the field opened empty and a save without one
  was refused.
- Mapping Studio: a **?** control in the brand row opening the usage guide
  (`docs/STUDIO.md`); `$GEM_STUDIO_HELP_URL` repoints it.
- Mapping Studio: a value defined in the inventory but absent from the
  crosswalk (just added, or a rebuild that failed) now appears as `pending`
  with a new **not resolved** (`unbuilt`) need code, instead of not appearing
  at all.
- Supplementary Table ST1, a requirements × standards coverage matrix: ten
  evidence patterns against HL7 FHIR Evidence R5, GA4GH VA 1.0 / VRS, SEPIO,
  ECO, ClinGen / ACMG-AMP, and GEM, with per-row notes and identifiers
  verified against the source vocabularies (`paper/sections/s11_background.tex`;
  pointers from main-text §2 and §6; references `strande2017`, `wand2021`, `schmidt2024`).
- `KNOWN_LIMITATIONS.md`: what the model, schema, and tooling do not yet do.
- This changelog.

### Changed
- Mapping Studio: **a connected UMLS key is now required to change anything.**
  Without one the workspace is fully browsable but read-only: every mutating
  endpoint (`/api/decide`, `/api/axis`, `/api/prefs`, `/api/rebuild`,
  `/api/value*`) answers `needs_key`, and every control that writes is disabled
  in the browser with the reason. `/api/state` and `/api/umls-key` stay open so
  the workspace still renders and a key can still be entered. Rationale: an
  axis, value or decision the Metathesaurus has not confirmed is not a mapping.
- Mapping Studio: UMLS-backed `/api/*` requests without a key now return an
  explicit `needs_key` error instead of failing silently; a "Connect UMLS"
  dialog walks through obtaining a free UTS key, tests it, and optionally
  saves it to `~/.config/forome-gem/umls_api_key` (mode 0600). Key lookup
  order is `UMLS_API_KEY` → repo `.envrc` → key file; ⚙ Settings shows the
  source. Not in the PyPI 0.2.2 wheel; ships with the next package release.
- `pyproject.toml`: PEP 639 license metadata (`license = "Apache-2.0"`,
  `license-files`), `setuptools>=77`.
- `CITATION.cff`, `README.md`, `.zenodo.json`: record the Zenodo concept and
  version DOIs and the PyPI distribution.

### Documentation
- The Mapping Studio guide moved from `data/umls/STUDIO.md` to
  **`docs/STUDIO.md`** and is linked from `README.md`. Rewritten around the
  two ways the tool is used: building a new mapping from scratch in any domain
  (install from PyPI → UMLS key → create a dimension → add values), and working
  on the GEM mapping in this repository (from a checkout with
  `pip install -e .`, or with the released tool pointed at `data/umls`). New
  material on value curation and on what rename and delete do to a recorded
  decision; the UMLS key is documented as a precondition rather than an
  accelerator.
- `data/umls/README.md`: Connect UMLS walkthrough and key-file location.
- Manuscript: "ground truth" replaced by "curator-authored reference
  annotations" throughout; one formulation of human-curator authority over
  AI drafts and AI-assisted review in §5, SN2, and SN4; the `resolution` /
  `target_resolution` (v0/v1) rename documented next to `key_phrase` /
  `phrase` in SN2 and the traceability table; conclusion states that three
  activation rules are machine-enforced.
- `case-reports/nelson1992.md`: method string corrected to
  `IN_VITRO_EXPERIMENT` (matches `annotations/nelson1992.yaml`); the corpus
  table (ST14) now credits Nelson with CE-N1.

### Tests
- `src/python/test/forome/gem/umls/test_umls_key.py`: key discovery, the
  `needs_key` contract for each UMLS-backed endpoint, and `POST /api/umls-key`.

## [0.2.2] - 2026-09-02

Release described in the manuscript. Archived on Zenodo as
[10.5281/zenodo.22260773](https://doi.org/10.5281/zenodo.22260773); published
on PyPI as `gem-mapping-studio` 0.2.2.

### Added
- Main text: "Reproducibility and conformance" subsection with an
  artifact-to-claim traceability table (`tab:conformance`) listing where each
  claim can be verified in the tagged release.
- `src/python/test/forome/gem/validation/test_shacl_activation.py`: the three
  enforced SHACL activation rules (Variant Ascertainment, Mode of Inheritance,
  Organism) tested in both directions, plus one released annotation validated
  end-to-end.

### Changed
- The conditional-dimension table (`tab:dimensions-cond`) now marks which
  activation conditions are enforced by an executable SHACL shape; the text
  states that the remaining conditions are documented and curator-checked.
- Supplement: Protocol-suite note records the `key_phrase` → `phrase`
  field-name normalization performed by `yaml_to_rdf.py`.
- `CITATION.cff` version 0.2.2 with `date-released`; package version 0.2.2.

### Removed
- Supplement appendices (`paper/sections/s3_appendices.tex`) that embedded the
  SHACL schema and the six annotation YAMLs via `\lstinputlisting`; they are
  now cited by repository path at the tagged release. `compile_paper.sh` no
  longer preflights the embedded inputs.

## [0.2.1] - 2026-09-02

Archived on Zenodo as
[10.5281/zenodo.22260687](https://doi.org/10.5281/zenodo.22260687).

### Changed
- American-spelling sweep and prose refinement across the main text, all
  supplementary notes, `README.md`, `data/umls/README.md`, `schema/`, and
  code comments and UI strings; `uts_client._normalise` renamed
  `_normalize`.
- Package version in `pyproject.toml` bumped 0.1.0 → 0.2.0 (not published;
  0.2.2 is the first version on PyPI).

## [0.2.0] - 2026-09-01

The `gem-mapping-studio` package (renamed from `genetic-evidence-model`,
`pyproject.toml` version 0.1.0); manuscript refactored from the ICBO
conference paper into an extended article plus supplement.

### Added
- UMLS crosswalk of the GEM dimensional vocabulary (`data/umls/`):
  `dimensions_inventory.yaml` (input), `umls_crosswalk.yaml` (output),
  curator `adjudications.yaml`, `semantic_types.yaml` and the semantic-network
  tree, the public decision log `DECISIONS.md`, and a hand-authored OMOP CDM
  positioning (`omop_cdm_examples.yaml`). Rendered as Supplementary Note
  "UMLS crosswalk and illustrative OMOP CDM positioning" (`s18`).
- Credibility sweep (`data/umls/sweeps/credibility.yaml`) and Supplementary
  Note "Credibility tiers: definitions, the UMLS finding, and external
  alignment" (`s19`); defeasibility-based level definitions in
  `schema/dimensions.md`.
- GEM Mapping Studio (`forome.gem.umls.adjudicate_ui`): a local,
  UMLS-integrated web app for defining mapping axes and adjudicating
  value-level mappings; usage guide `data/umls/STUDIO.md`.
- `forome.gem.umls` package: UTS REST client with fixture and null clients
  (`uts_client.py`), tiered crosswalk harness (`build_umls_crosswalk.py`),
  LaTeX renderer (`render_crosswalk_tex.py`), semantic-network fetcher,
  optional local UMLS index on PostgreSQL (`local_umls.py`, extra `local`),
  sweep and credibility-classification tools.
- Console scripts: `gem-validate`, `gem-coverage`, `gem-mapping-studio`
  (alias `gem-umls-adjudicate`), `gem-umls-crosswalk`, `gem-umls-render`,
  `gem-umls-semantic-network`, `gem-umls-load-local`, `gem-umls-sweep`,
  `gem-umls-classify-credibility`.
- Packaged reference copies of `semantic_types.yaml`, the SHACL schema, and
  `dimensions.md` (`forome.gem._reference`) for standalone installs, kept in
  sync by `scripts/release-pypi.sh` and asserted by `test_packaging.py`.
- Tests under `src/python/test/forome/gem/umls/` (harness, local index,
  packaging, sweep).
- `.zenodo.json` release metadata; `scripts/release-pypi.sh`.
- `schema/EXTENSIONS.md`: curator-surfaced candidate CE-C1
  (`VARIANT_IN_TRANSCRIPT` Resolution value), kept outside the pilot counts.

### Changed
- Manuscript split into an extended main paper (standard `article` class,
  off `ceurart`) and a separate supplement sharing `paper/preamble.tex`;
  `compile_paper.sh` builds the supplement first and resolves cross-document
  references with `xr`, failing on any undefined reference.
- Python code moved to a src layout under `src/python/main` with the
  `forome.gem` namespace: `extraction/` → `forome.gem.extraction`,
  `scripts/validate_annotations.py` and `compute_coverage.py` →
  `forome.gem.validation`. CI (`.github/workflows/validate.yml`) follows the
  new paths.
- `pyproject.toml`: package metadata, dependencies (`rdflib`, `pyshacl`,
  `ruamel.yaml`, `requests`), optional extras `dev` and `local`.
- `README.md`: manuscript status (arXiv / journal), licensing summary
  (CC-BY-4.0 content, Apache-2.0 code), UMLS crosswalk and Studio section.
- `.gitignore`: `.envrc`, the UMLS cache and UMLS-derived sweep results
  (not redistributable), `internal/`, `dist/`.

### Removed
- Console scripts `extract-annotations` and `extract-annotations-pypdf`
  (the modules remain under `forome.gem.extraction`).

## [icbo-final] - 2026-06-10

Final ICBO 2026 submission (paper cut to 12 pages, claims softened).

### Added
- Enforceable SHACL validation: schema 1.1 (`schema/genetic_evidence.shacl.ttl`)
  adds shapes for resolution, credibility, and a mandatory `source_span`,
  enumerations for the categorical conditional dimensions, and the
  `not_applicable_or_omitted` sentinel.
- `extraction/yaml_to_rdf.py` (YAML → RDF converter),
  `scripts/validate_annotations.py` (pyshacl over the corpus), and
  `scripts/compute_coverage.py` (regenerates `annotations/coverage.md`).
- CI workflow `.github/workflows/validate.yml`: `parse-yaml`,
  `shacl-validate`, and `coverage` jobs on every push and pull request.
- Skill bundles ship both license files and the validation scripts
  (`build_skill_bundle.sh`).

### Changed
- Annotations brought into conformance with schema 1.1 (explicit
  `not_applicable_or_omitted` for Davis 2011 mode of inheritance and the
  Inouye 2018 variant ascertainment; organism recorded for the Jossin 2017
  in vivo co-IP item).
- `protocols/PROTOCOL.md`, `schema/dimensions.md`, `schema/examples.md`
  updated for the sentinel and the enforced rules.

## [v-1.0] - 2026-06-09

Initial tagged release: the ICBO 2026 submission as first submitted. Contains
the SHACL schema (1.0), dimension documentation and candidate extensions
(`schema/`), the annotation protocols and skills, the six-paper annotation
corpus with case reports, and the paper sources.

[Unreleased]: https://github.com/ForomePlatform/genetic-evidence-model/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/ForomePlatform/genetic-evidence-model/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ForomePlatform/genetic-evidence-model/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ForomePlatform/genetic-evidence-model/compare/icbo-final...v0.2.0
[icbo-final]: https://github.com/ForomePlatform/genetic-evidence-model/compare/v-1.0...icbo-final
[v-1.0]: https://github.com/ForomePlatform/genetic-evidence-model/releases/tag/v-1.0
