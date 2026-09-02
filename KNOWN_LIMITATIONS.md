# Known limitations

What the model, the released schema, the corpus, and the tooling do not yet
do. This file is the honest counterpart to the feature list in `README.md`:
each entry says what is missing, why, and where the gap is tracked. The
status vocabulary is

| Status | Meaning |
| --- | --- |
| **enforced** | in the schema and checked by an executable SHACL shape (`gem-validate`) |
| **documented** | in the schema and the paper, checked by the curator, no executable shape |
| **candidate** | surfaced by one corpus paper, recorded as a candidate extension (CE code in `schema/EXTENSIONS.md`), not in the schema |
| **out of scope** | deliberately not represented; a named external standard covers it |

The manuscript's own limitations subsection (§6.2) and its coverage matrix
(Supplementary Table ST1) discuss the same gaps in prose; this file is the
repository-side list and is updated when the status of an item changes.

## 1. Scope of the evidence

- **Six papers, one annotator.** Four papers were annotated by hand and two
  by the AI track with curator review. The corpus supports a feasibility
  claim, not inter-annotator agreement, recall, or generalizability
  figures. Status: documented.
- **No clinical deployment.** The model is motivated by variant
  interpretation but has not been applied in a live curation workflow.
  Status: documented.
- **Primary versus cited evidence.** An item whose support is the paper's
  own data and an item that relays a cited result are both `GeneticEvidence`
  items. The distinction is carried by the boolean `cited_evidence` flag on
  the item (used in `annotations/v1/duerr2006.yaml` GE-8, a cited mouse-model
  finding), not by a separate class, and nothing prevents a consumer from
  counting cited items as primary. The cited anti-p40 clinical trial in the
  same paper (GE-new-1) is recorded with Knowledge Domain left unresolved
  because no genetic domain fits (CE-DU3). Status: documented / candidate.

## 2. Forced fits recorded as candidate extensions

These are patterns the corpus exercised that the schema could represent
only by choosing the nearest existing value. Each is recorded in the
annotation's `candidate_extensions` block and in `schema/EXTENSIONS.md`;
none enters the schema until a second independent paper exercises it
(the promotion rule).

- **Polygenic scores (CE-IN1 to CE-IN6).** All four Inouye 2018 items are
  forced fits: the score is typed `target_type: VARIANT` because no value
  describes a genome-wide aggregate, Resolution cannot localize it, and
  Variant Ascertainment is set to the explicit `not_applicable_or_omitted`
  escape that the SHACL shape accepts. Score construction, tuning and
  validation cohorts, ancestry composition, and effect-size direction have
  no home. Status: candidate; awaiting a second polygenic-score paper.
- **Direction of effect (CE-DU1).** A protective allele and a risk allele
  are annotated identically; the sign of the effect lives in free text.
  Status: candidate.
- **Activation scope for Human Genetics with a Variant target (CE-DU4).**
  The family-based transmission test in Duerr 2006 (GE-3) activates no
  conditional dimension that captures it, and the pedigree items Gupta GE-1
  and Davis GE-5 populate Mode of Inheritance and Mendelian Segregation on
  Variant targets, outside the documented Human Genetics + Gene activation
  condition. Status: candidate.
- **Protein-subdomain resolution (CE-J1), interaction or complex as target
  (CE-J2), relation vocabulary (CE-J3).** Jossin 2017 needed a
  protein-subdomain resolution, a protein--protein interaction as the
  target (GE-6, forced onto a Gene target), and binding/trafficking
  relations; Gene Relation currently has three values
  (`X_has_same_function_as_Y`, `X_regulates_Y`, `X_inhibits_Y`), so the
  binding relation in GE-4 was left unpopulated. Status: candidate.
- **Cross-level (CE-N1) and transcript-level (CE-C1) variant
  description.** Resolution presupposes genomic coordinates. Nelson 1992
  describes one allele as a 12-bp insertion in cDNA coordinates that is a
  single-nucleotide substitution in genomic coordinates; the UMLS crosswalk
  surfaced the transcript-level pattern (`VARIANT_IN_TRANSCRIPT`). Status:
  candidate (CE-N1 resolved by reference to HGVS/VRS; CE-C1
  curator-surfaced, outside the pilot counts).
- **Cohort composition (CE-IN5).** Case and control counts and ancestry are
  recorded only as free text (`special_considerations`), not as structured
  fields. Status: candidate.

## 3. Conditional-activation rules that are not executable

The paper's Table 3 lists eight conditionally required dimensions. Three
activation conditions are enforced by SHACL shapes in
`schema/genetic_evidence.shacl.ttl` and tested in both directions in
`src/python/test/forome/gem/validation/test_shacl_activation.py`:

| Dimension | Condition | Status |
| --- | --- | --- |
| Variant Ascertainment | Target Type = Variant | enforced |
| Mode of Inheritance | Knowledge Domain ⊇ Human Genetics and Target Type = Gene | enforced |
| Organism | Method ⊇ In Vivo or Knowledge Domain ⊇ Model Organism | enforced |
| Mendelian Segregation | Knowledge Domain ⊇ Human Genetics and Target Type = Gene | documented |
| Penetrance | Knowledge Domain ⊇ Human Genetics and Target Type = Variant | documented |
| Measurement Target | Knowledge Domain ⊇ Gene Function | documented |
| Gene Relation | Knowledge Domain ⊇ Gene Function | documented |
| Knockout Type | Knowledge Domain ⊇ Model Organism | documented |

For the five documented rules a missing dimension is not reported by
`gem-validate`; the enumeration of the value is still checked when the
dimension is present (`MeasurementTargetShape`, `GeneRelationShape`,
`KnockoutTypeShape`). `schema/dimensions.md` lists further conditional
fields with no shape at all (`exact_variant`, `subdomain`,
`environmental_factors`, `genetic_background_considered`,
`specificity_of_phenotype`). The remaining shapes are scoped as future
work.

## 4. Vocabulary grounding that is planned rather than implemented

- **Method and assay type.** Methods are recorded at the level of the GEM
  hierarchy (In Vitro, In Vivo, GWAS, ...); the specific assay is free text.
  Grounding Method values to ECO and OBI terms is planned; the UMLS
  crosswalk (`data/umls/`) is the first step and records, per value, an
  anchor concept and the relation to it (close, broader, narrower, related)
  or an explicit *unmapped* decision.
- **Intersective tokens.** Several tokens (`STATISTICAL_GENETICS`,
  `BIOINFORMATICS_INFERENCE`, `RELATED_GENE`) are compounds that no single
  UMLS concept expresses; the crosswalk records the nearest anchor and keeps
  the intended composition in the curator note (`data/umls/DECISIONS.md`).
  Concept-level post-coordination is future work.
- **Phenotype vocabularies.** The phenotype-mapping field (`hpo_terms`,
  under the accuracy-of-mapping facet) expects HPO terms.
  Model-organism phenotype vocabularies (MP, ZP) are not bound, so the
  zebrafish, rat, and mouse phenotypes in Davis 2011 and Jossin 2017 are
  mapped only loosely. The Phenotype Scale axis has no external equivalent;
  GO biological process is a possible alignment for its molecular and
  cellular end.
- **Variant identifiers.** The model relies on GA4GH identifiers by design,
  but target identifiers are not yet bound to VRS objects or HGVS
  expressions in the released annotations.
- **Knowledge Domain** has no single external equivalent; it is a GEM-native
  axis.
- **OWL / LinkML renderings.** The canonical schema is SHACL plus the
  YAML-to-RDF transform. OWL, JSON Schema, and LinkML renderings from one
  source of truth, and alignment to IAO, OBI, and PROV-O at the class level,
  are future work.
- **`GeneticEvidenceAssertion` naming.** In the released RDF the class types
  object-level assertions so that assertion-level SHACL shapes apply; the
  paper reserves the class for the reasoning-layer meta-predicate. A future
  schema revision separates the two.

## 5. Out of scope by design

- **Therapeutic response** (intervention tested in patients): no
  intervention construct. FHIR Evidence and the GA4GH VA Variant
  Therapeutic Response profile cover it. The candidate CE-DU3 (two
  within-paper instances in Duerr 2006) leaves open whether translational
  claims get a higher-order construct or are declared out of scope.
- **Cross-publication synthesis** (combining evidence lines into a
  classification): GEM represents per-publication items; synthesis belongs
  to FHIR `EvidenceReport`, VA `Statement`s with evidence lines, SEPIO, and
  the ClinGen / ACMG-AMP rubrics. The reasoning layer is developed
  separately.
- **Segregation strength.** Mendelian Segregation is Boolean; meiosis counts
  and LOD scores have no structured field (pedigree size appears only as
  free text in Gupta GE-1).
- **Rescue experiments** are not distinguished from other in vivo evidence.

## 6. Tooling

- **UMLS access.** Concept search, expansion, and rebuilds in the Mapping
  Studio need a UMLS API key (free UTS account). Without one the Studio
  opens, shows a banner, and walks through obtaining a key; the harness
  returns explicit `needs_key` errors. The key and any local UMLS index
  live outside the repository and are never distributed.
- **Local index.** The PostgreSQL MRCONSO index (`data/umls/README.md`) is
  optional and serves search and source-vocabulary listing only; hierarchy
  expansion still requires UTS.
- **Sweep results.** Credibility-sweep result files carry UMLS-derived
  strings (including SNOMED CT) and are not redistributed; the repository
  ships the queries and the adjudicated decisions.
- **Studio is single-user.** `adjudications.yaml` is rewritten in place on
  every decision with no file locking; run one Studio per checkout.
- **Packaging.** The PyPI 0.2.2 wheel predates the Connect UMLS walkthrough
  and fails silently without a key; the fix ships with the next package
  release.
