# Paper selection (Corpus-2 annotation study)

Status: **frame, sampling design and seed adopted by the study lead on
2026-10-15**; the paper counts (Section 3, item 4) remain open. This file
implements Section 6 of `protocols/EVALUATION_PROTOCOL.md`. It is frozen
at the study tag (Section 4); any later change is an amendment under
Section 5.

Provenance note: the literature frame below was designed and executed with
AI assistance on behalf of the study lead. The venue set, the
computational-biology group, the somatic-genomics exclusion and the
decision to keep low-yield venues were fixed by the study lead on
2026-10-15 (Section 1.6 records the history). No individual paper in the
typical stratum is chosen by a person or a model: selection is governed
solely by the recorded query, the recorded post-retrieval rule, and the
sampling procedure and seed in Section 1.5. This removes the risk that an
AI assistant steers the sample toward literature familiar to AI models
(intake criterion 8).

## 1. Typical stratum

### 1.1 Source and search

- Source: PubMed, queried through the NCBI E-utilities (`esearch` then
  `esummary`), on **2026-10-15**. The term exceeds URL limits (HTTP 414 on
  GET), so `esearch` was executed as an HTTP POST to the same endpoint
  with identical parameters; this is recorded for reproducibility.
- The frame has three parts, all sharing the same date, language,
  publication-type and open-access filters, and all subject to a
  frame-wide somatic-genomics exclusion (Section 1.3):
  1. nineteen specialist genetics and genomics venues, taken whole;
  2. five multidisciplinary or mixed venues (Nature, Science, PNAS, Cell,
     Blood), admitted only through a recorded genetics content filter,
     since most of their output is not genetic evidence;
  3. eight computational biology and genomics-methods venues, admitted
     through the same genetics filter plus a disease or phenotype term
     requirement, to select papers whose bioinformatic inference produces
     genetic-evidence claims while excluding pure tool, benchmark and
     pipeline papers.
- Exact query term, executed verbatim as a single line:

```
((("Am J Hum Genet"[jour] OR "Eur J Hum Genet"[jour] OR "Hum Genet"[jour] OR "J Med Genet"[jour] OR "Genet Med"[jour] OR "HGG Adv"[jour] OR "NPJ Genom Med"[jour] OR "Hum Genomics"[jour] OR "Mol Genet Genomic Med"[jour] OR "Clin Genet"[jour] OR "Hum Mol Genet"[jour] OR "PLoS Genet"[jour] OR "Genet Epidemiol"[jour] OR "Ann Hum Genet"[jour] OR "Nat Genet"[jour] OR "Genome Biol"[jour] OR "BMC Med Genomics"[jour] OR "BMC Genomics"[jour] OR "BMC Genomic Data"[jour]) OR (("Nature"[jour] OR "Science"[jour] OR "Proc Natl Acad Sci U S A"[jour] OR "Cell"[jour] OR "Blood"[jour]) AND ("genome-wide association"[tiab] OR GWAS[tiab] OR "exome sequencing"[tiab] OR "genome sequencing"[tiab] OR "whole-exome"[tiab] OR "whole-genome sequencing"[tiab] OR "pathogenic variant"[tiab] OR "pathogenic variants"[tiab] OR "de novo variant"[tiab] OR "de novo variants"[tiab] OR "de novo mutation"[tiab] OR "de novo mutations"[tiab] OR "germline variant"[tiab] OR "germline variants"[tiab] OR "germline mutation"[tiab] OR "germline mutations"[tiab] OR "loss-of-function variant"[tiab] OR "loss-of-function variants"[tiab] OR "segregation analysis"[tiab] OR "linkage analysis"[tiab] OR heritability[tiab] OR "polygenic risk"[tiab] OR "polygenic score"[tiab] OR "polygenic scores"[tiab] OR "susceptibility locus"[tiab] OR "susceptibility loci"[tiab] OR "risk locus"[tiab] OR "risk loci"[tiab] OR "risk variant"[tiab] OR "risk variants"[tiab] OR "candidate gene"[tiab] OR "candidate genes"[tiab] OR monogenic[tiab] OR Mendelian[tiab] OR haploinsufficiency[tiab] OR "gene-environment interaction"[tiab] OR eQTL[tiab] OR "expression quantitative trait"[tiab] OR "fine-mapping"[tiab] OR "fine mapping"[tiab] OR "mutations in"[ti] OR "variants in"[ti] OR "mutation in"[ti] OR "variant in"[ti])) OR (("PLoS Comput Biol"[jour] OR "Bioinformatics"[jour] OR "Brief Bioinform"[jour] OR "BMC Bioinformatics"[jour] OR "NAR Genom Bioinform"[jour] OR "GigaScience"[jour] OR "Genome Res"[jour] OR "Genome Med"[jour]) AND ("genome-wide association"[tiab] OR GWAS[tiab] OR "exome sequencing"[tiab] OR "genome sequencing"[tiab] OR "whole-exome"[tiab] OR "whole-genome sequencing"[tiab] OR "pathogenic variant"[tiab] OR "pathogenic variants"[tiab] OR "de novo variant"[tiab] OR "de novo variants"[tiab] OR "de novo mutation"[tiab] OR "de novo mutations"[tiab] OR "germline variant"[tiab] OR "germline variants"[tiab] OR "germline mutation"[tiab] OR "germline mutations"[tiab] OR "loss-of-function variant"[tiab] OR "loss-of-function variants"[tiab] OR "segregation analysis"[tiab] OR "linkage analysis"[tiab] OR heritability[tiab] OR "polygenic risk"[tiab] OR "polygenic score"[tiab] OR "polygenic scores"[tiab] OR "susceptibility locus"[tiab] OR "susceptibility loci"[tiab] OR "risk locus"[tiab] OR "risk loci"[tiab] OR "risk variant"[tiab] OR "risk variants"[tiab] OR "candidate gene"[tiab] OR "candidate genes"[tiab] OR monogenic[tiab] OR Mendelian[tiab] OR haploinsufficiency[tiab] OR "gene-environment interaction"[tiab] OR eQTL[tiab] OR "expression quantitative trait"[tiab] OR "fine-mapping"[tiab] OR "fine mapping"[tiab] OR "mutations in"[ti] OR "variants in"[ti] OR "mutation in"[ti] OR "variant in"[ti]) AND (disease[tiab] OR diseases[tiab] OR disorder[tiab] OR disorders[tiab] OR syndrome[tiab] OR phenotype[tiab] OR phenotypes[tiab] OR patient[tiab] OR patients[tiab] OR trait[tiab] OR traits[tiab]))) AND ("2026/02/01"[Date - Publication] : "2026/10/15"[Date - Publication]) AND english[la] AND (journal article[pt] NOT (review[pt] OR editorial[pt] OR comment[pt] OR published erratum[pt] OR meta-analysis[pt] OR systematic review[pt] OR preprint[pt] OR case reports[pt])) AND "pubmed pmc open access"[filter]) NOT ("somatic mutation"[tiab] OR "somatic mutations"[tiab] OR "somatic variant"[tiab] OR "somatic variants"[tiab] OR "clonal hematopoiesis"[tiab] OR "clonal haematopoiesis"[tiab])
```

- PubMed's own parse of the term (the `querytranslation` field returned
  with the result), recorded to show no term was dropped or reinterpreted:

```
(("Am J Hum Genet"[Journal] OR "Eur J Hum Genet"[Journal] OR "Hum Genet"[Journal] OR "J Med Genet"[Journal] OR "Genet Med"[Journal] OR "HGG Adv"[Journal] OR "NPJ Genom Med"[Journal] OR "Hum Genomics"[Journal] OR "Mol Genet Genomic Med"[Journal] OR "Clin Genet"[Journal] OR "Hum Mol Genet"[Journal] OR "PLoS Genet"[Journal] OR "Genet Epidemiol"[Journal] OR "Ann Hum Genet"[Journal] OR "Nat Genet"[Journal] OR "Genome Biol"[Journal] OR "BMC Med Genomics"[Journal] OR "BMC Genomics"[Journal] OR "BMC Genomic Data"[Journal] OR (("Nature"[Journal] OR "Science"[Journal] OR "Proc Natl Acad Sci U S A"[Journal] OR "Cell"[Journal] OR "Blood"[Journal]) AND ("genome-wide association"[Title/Abstract] OR "GWAS"[Title/Abstract] OR "exome sequencing"[Title/Abstract] OR "genome sequencing"[Title/Abstract] OR "whole-exome"[Title/Abstract] OR "whole-genome sequencing"[Title/Abstract] OR "pathogenic variant"[Title/Abstract] OR "pathogenic variants"[Title/Abstract] OR "de novo variant"[Title/Abstract] OR "de novo variants"[Title/Abstract] OR "de novo mutation"[Title/Abstract] OR "de novo mutations"[Title/Abstract] OR "germline variant"[Title/Abstract] OR "germline variants"[Title/Abstract] OR "germline mutation"[Title/Abstract] OR "germline mutations"[Title/Abstract] OR "loss-of-function variant"[Title/Abstract] OR "loss-of-function variants"[Title/Abstract] OR "segregation analysis"[Title/Abstract] OR "linkage analysis"[Title/Abstract] OR "heritability"[Title/Abstract] OR "polygenic risk"[Title/Abstract] OR "polygenic score"[Title/Abstract] OR "polygenic scores"[Title/Abstract] OR "susceptibility locus"[Title/Abstract] OR "susceptibility loci"[Title/Abstract] OR "risk locus"[Title/Abstract] OR "risk loci"[Title/Abstract] OR "risk variant"[Title/Abstract] OR "risk variants"[Title/Abstract] OR "candidate gene"[Title/Abstract] OR "candidate genes"[Title/Abstract] OR "monogenic"[Title/Abstract] OR "Mendelian"[Title/Abstract] OR "haploinsufficiency"[Title/Abstract] OR "gene-environment interaction"[Title/Abstract] OR "eQTL"[Title/Abstract] OR "expression quantitative trait"[Title/Abstract] OR "fine-mapping"[Title/Abstract] OR "fine-mapping"[Title/Abstract] OR "mutations in"[Title] OR "variants in"[Title] OR "mutation in"[Title] OR "variant in"[Title])) OR (("PLoS Comput Biol"[Journal] OR "Bioinformatics"[Journal] OR "Brief Bioinform"[Journal] OR "BMC Bioinformatics"[Journal] OR "NAR Genom Bioinform"[Journal] OR "GigaScience"[Journal] OR "Genome Res"[Journal] OR "Genome Med"[Journal]) AND ("genome-wide association"[Title/Abstract] OR "GWAS"[Title/Abstract] OR "exome sequencing"[Title/Abstract] OR "genome sequencing"[Title/Abstract] OR "whole-exome"[Title/Abstract] OR "whole-genome sequencing"[Title/Abstract] OR "pathogenic variant"[Title/Abstract] OR "pathogenic variants"[Title/Abstract] OR "de novo variant"[Title/Abstract] OR "de novo variants"[Title/Abstract] OR "de novo mutation"[Title/Abstract] OR "de novo mutations"[Title/Abstract] OR "germline variant"[Title/Abstract] OR "germline variants"[Title/Abstract] OR "germline mutation"[Title/Abstract] OR "germline mutations"[Title/Abstract] OR "loss-of-function variant"[Title/Abstract] OR "loss-of-function variants"[Title/Abstract] OR "segregation analysis"[Title/Abstract] OR "linkage analysis"[Title/Abstract] OR "heritability"[Title/Abstract] OR "polygenic risk"[Title/Abstract] OR "polygenic score"[Title/Abstract] OR "polygenic scores"[Title/Abstract] OR "susceptibility locus"[Title/Abstract] OR "susceptibility loci"[Title/Abstract] OR "risk locus"[Title/Abstract] OR "risk loci"[Title/Abstract] OR "risk variant"[Title/Abstract] OR "risk variants"[Title/Abstract] OR "candidate gene"[Title/Abstract] OR "candidate genes"[Title/Abstract] OR "monogenic"[Title/Abstract] OR "Mendelian"[Title/Abstract] OR "haploinsufficiency"[Title/Abstract] OR "gene-environment interaction"[Title/Abstract] OR "eQTL"[Title/Abstract] OR "expression quantitative trait"[Title/Abstract] OR "fine-mapping"[Title/Abstract] OR "fine-mapping"[Title/Abstract] OR "mutations in"[Title] OR "variants in"[Title] OR "mutation in"[Title] OR "variant in"[Title]) AND ("disease"[Title/Abstract] OR "diseases"[Title/Abstract] OR "disorder"[Title/Abstract] OR "disorders"[Title/Abstract] OR "syndrome"[Title/Abstract] OR "phenotype"[Title/Abstract] OR "phenotypes"[Title/Abstract] OR "patient"[Title/Abstract] OR "patients"[Title/Abstract] OR "trait"[Title/Abstract] OR "traits"[Title/Abstract]))) AND 2026/02/01:2026/10/15[Date - Publication] AND "english"[Language] AND ("journal article"[Publication Type] NOT ("review"[Publication Type] OR "editorial"[Publication Type] OR "comment"[Publication Type] OR "published erratum"[Publication Type] OR "meta-analysis"[Publication Type] OR "systematic review"[Publication Type] OR "preprint"[Publication Type] OR "case reports"[Publication Type])) AND "pubmed pmc open access"[Filter]) NOT ("somatic mutation"[Title/Abstract] OR "somatic mutations"[Title/Abstract] OR "somatic variant"[Title/Abstract] OR "somatic variants"[Title/Abstract] OR "clonal hematopoiesis"[Title/Abstract] OR "clonal haematopoiesis"[Title/Abstract])
```

  Two harmless normalisations in the translation, noted for the record:
  PubMed flattened one level of redundant parentheses around the venue
  disjunction, and it normalised "fine-mapping" and "fine mapping" to the
  same quoted phrase, which therefore appears twice.
- Retrieval: `esearch` (POST, `retmode=json&retmax=10000`) returned
  **2055** PMIDs; metadata for all 2055 came from `esummary` in batches
  of at most 200 ids. The count was independently re-run the same day and
  the full id list diffed against the recorded CSV with zero differences.
- Post-retrieval date rule, applied deterministically to all 2055
  records: parse `pubdate` and `epubdate` as `YYYY[ Mon[ D]]`, a missing
  month or day counting as 01 and a month range such as `Jan-Feb`
  counting as its first month; `earliest_date` is the earlier of the two
  parsed dates. Records with `earliest_date` before **2026-02-01** are
  excluded. This is needed because PubMed's `[Date - Publication]` range
  matches print or electronic dates, so a paper e-published in 2024 or
  2025 can enter the window through a 2026 print-issue date. The rule
  excluded **80** records (earliest dates 2024-01-12 to 2026-01-30),
  leaving an eligible frame of **1975** papers, all with earliest dates
  between 2026-02-01 and 2026-10-13.
- Citation snapshot: on **2026-10-15** the Europe PMC REST API
  (`searchPOST`, `SRC:MED`, `resultType=lite`, batches of at most 100
  ids) returned `citedByCount` for 2030 of the 2055 records; the 25
  misses are very recent papers not yet indexed in Europe PMC, recorded
  as blank and treated as 0 by any screen. The snapshot is the column
  `citedby_epmc_20261015`. Citation counts change daily; only this
  recorded snapshot is used by the study.
- Full list: `study/papers_frame.csv` holds all 2055 records (columns
  `pmid,pmcid,doi,journal,pubdate,epubdate,earliest_date,excluded_reason,citedby_epmc_20261015,title`,
  sorted by integer `pmid` ascending, LF line endings). The eligible
  frame is exactly the 1975 rows whose `excluded_reason` is empty. The
  `journal` column uses PubMed's NLM abbreviations; note that BMC Genomic
  Data appears there under its official abbreviation `BMC Genom Data`.
- PubMed is a live database, so re-running the query on a later date can
  return a different set. The authoritative frame is the recorded PMID
  list in the CSV; the query and date document how it was obtained.

### 1.2 Eligibility criteria

1. Primary research article (PubMed publication type Journal Article)
   reporting original data.
2. Published in one of the thirty-two venues of Section 1.4: a specialist
   venue taken whole, a multidisciplinary venue passing the genetics
   content filter, or a computational biology venue passing the genetics
   filter plus the disease or phenotype clause (all recorded verbatim in
   Section 1.1). Venues are identified by exact NLM title abbreviation.
3. Earliest public date (electronic or print, per the Section 1.1 rule)
   between 2026-02-01 and the search date. Rationale: the candidate
   pinned AI models have a January 2026 training cutoff, so papers first
   public from February 2026 cannot be in training data, removing the
   memorisation confound (intake criteria 7 and 8).
4. Written in English (intake criterion 1).
5. In the PMC Open Access subset, so canonical full text is extractable
   through the Europe PMC `fullTextXML` route for both the human and the
   AI passes (the same route used for the first stress paper). Per-paper
   `fullTextXML` availability is confirmed at intake (criterion 2).
6. Not somatic-genomics-focused: the typical stratum targets germline,
   heritable and functional genetic evidence. The frame-wide exclusion in
   Section 1.3 encodes this coarsely; intake criterion 4 applies the
   scope judgement per paper.
7. Passes the Section 6.4 intake screen at sampling time, in particular:
   at least two separate claims linking a genetic entity to a phenotype
   (criterion 3), and in scope or deliberately adjacent to GEM's current
   scope (criterion 4). Intake additionally checks that no earlier public
   version of the paper (preprint, accepted manuscript, ahead-of-print
   posting) predates 2026-02-01; the earliest version found is decisive.

### 1.3 Exclusion criteria

- Somatic genomics (frame-wide `NOT` on the phrases "somatic mutation(s)",
  "somatic variant(s)", "clonal hematopoiesis", "clonal haematopoiesis"):
  GEM currently has no machinery for somatic evidence, so tumour-genome
  and clonal-haematopoiesis work is out of scope for this study.
  **Recorded by the study lead on 2026-10-15 as provisional, with an
  explicit revisit note: somatic genomics is regarded as the most
  promising near-term extension area, and this exclusion is to be
  revisited when the model has the machinery.** Measured cost and
  coverage (2026-10-15): the exclusion removes 22 of 1832
  specialist-venue records (1.2 percent), almost all genuinely somatic
  (tumour co-mutation evolution, pan-cancer mutational signatures, clonal
  haematopoiesis); two recorded edge cases are one Nature Genetics paper
  using germline variation as its exposure and one non-cancer somatic
  study (brain mosaicism in ALS). The phrase test under-catches tumour
  genomics that avoids these exact words, notably in Blood, where most
  surviving filtered papers are still lymphoma or myeloma genomics;
  intake criterion 4 remains the real gate there.
- Reviews, systematic reviews and meta-analyses: secondary syntheses, not
  primary source-anchored genetic evidence.
- Editorials and comments: no extractable evidence items.
- Published errata: not standalone evidence; a correction to a sampled
  paper is instead noted at intake.
- Preprints: not the version of record, and frequently posted before the
  training cutoff.
- Case reports: a single proband typically yields one
  genetic-entity-to-phenotype claim and would fail intake criterion 3;
  excluding them at frame level saves screening effort. (A multi-family
  case series, if ever wanted, belongs in the stress stratum.)
- Records whose earliest public date predates 2026-02-01 (the Section 1.1
  rule): reintroduces the memorisation confound.
- In the filtered venues, papers not matching their entry filter: a
  consequence of the frame boundary, recorded as such; an evidence paper
  phrased without any listed term is missed.
- Papers from the original six-paper pilot corpus: used in annotator
  training and, for four papers, as AI exemplars (protocol Section 6.4).
  All six predate the window, so this is automatic here.
- Retraction status is re-checked at intake for every sampled paper; the
  query did not filter on it, and publication-type flags on recent
  records are incomplete (see Section 1.7), so intake re-verifies article
  type manually.

### 1.4 Venue set and composition of the eligible frame

Thirty-two venues fixed by the study lead on 2026-10-15, spanning the
literature GEM targets: human, clinical, population, statistical,
molecular, model-organism, polygenic-score and bioinformatic-inference
genetics, including the flagship venues. Prominent venues are familiarity
risks under intake criterion 8; the post-cutoff window removes
training-data exposure, and residual familiarity is recorded per paper at
intake. Venues the filters reduce to a handful of papers are kept
deliberately (study-lead decision, 2026-10-15): dropping them would only
rename the frame, and keeping them preserves coverage.

Entry: W = whole venue, F1 = genetics filter, F2 = genetics filter plus
phenotype clause. Group letters refer to the sampling strata of Section
1.5.

| Journal (as in the CSV) | Entry | Group | Eligible |
| --- | --- | --- | ---: |
| BMC Genomics | W | D | 607 |
| Genome Biol | W | C | 226 |
| PLoS Genet | W | C | 212 |
| Nat Genet | W | A | 86 |
| BMC Med Genomics | W | B | 80 |
| Hum Genomics | W | B | 78 |
| HGG Adv | W | B | 73 |
| Proc Natl Acad Sci U S A | F1 | E | 66 |
| BMC Genom Data | W | D | 60 |
| Eur J Hum Genet | W | A | 56 |
| Hum Mol Genet | W | C | 55 |
| Mol Genet Genomic Med | W | A | 42 |
| Am J Hum Genet | W | A | 41 |
| Genome Med | F2 | F | 37 |
| NPJ Genom Med | W | B | 35 |
| Hum Genet | W | A | 28 |
| Brief Bioinform | F2 | F | 28 |
| Nature | F1 | E | 27 |
| Bioinformatics | F2 | F | 24 |
| J Med Genet | W | A | 23 |
| Clin Genet | W | A | 20 |
| Genet Epidemiol | W | B | 14 |
| PLoS Comput Biol | F2 | F | 12 |
| BMC Bioinformatics | F2 | F | 11 |
| Genome Res | F2 | F | 10 |
| NAR Genom Bioinform | F2 | F | 9 |
| Blood | F1 | E | 7 |
| Genet Med | W | A | 3 |
| Ann Hum Genet | W | B | 2 |
| Cell | F1 | E | 2 |
| Science | F1 | E | 1 |
| GigaScience | F2 | F | 0 |
| **Total** | | | **1975** |

Composition notes, from recorded title samples (2026-10-15): BMC Genomics
is roughly 70 percent non-human (crops, livestock, microbes, wild
species). Filter precision for genetic-evidence content is about 40 to 50
percent in Nature, PLoS Comput Biol, Genome Res and Genome Med, about 30
to 40 percent in Blood (germline share), about 15 to 20 percent in PNAS
(plant, microbial and evolutionary genetics dominate) and about 10 to 15
percent in Bioinformatics and Brief Bioinform (methodology papers trip
the phenotype words). Low precision costs intake-screening effort, not
validity: the intake screen is the per-paper gate and the allocation in
Section 1.5 bounds every filtered group. GigaScience contributes 0
records through a dating and PMC-deposit artefact recorded in Section
1.7, not a wrong abbreviation.

### 1.5 Sampling method (adopted by the study lead 2026-10-15)

- Primary stratification variable: venue group, assigned mechanically by
  journal (Section 1.4 table). Eligible papers per group: A human and
  clinical genetics 299; B population, statistical and genomic medicine
  282; C molecular and functional genomics 493; D broad and largely
  non-human genomics 667; E multidisciplinary and mixed venues 103; F
  computational biology and bioinformatic inference 131.
- Allocation for 8 typical papers: 2 from A, 2 from B, 1 from C, 1 from
  D, 1 from E, 1 from F. Rationale: the headline estimates should rest
  mainly on venues where genetic evidence is the core subject, while
  every frame component stays represented and none dominates. If the
  study runs with 9 or 10 typical papers, the extra slots go to C, then
  A, in that order (pre-specified).
- Citation strata (secondary, overlaid on the venue slots; design basis
  and feasibility numbers in Section 1.8): computed from the frozen
  snapshot column `citedby_epmc_20261015` and age from `earliest_date`
  to 2026-10-15, so the draw is reproducible from the CSV alone. WELL
  means at least 2 recorded citations (the top 14 percent of this young
  frame); ZERO means zero recorded citations at an age of at least 183
  days; FREE means no citation constraint. A missing count is 0. The
  slot map realises the study lead's 50/30/20 target (well cited,
  ungated, uncited) as 4/2/2 of 8 papers: WELL for slots A1, B1, C1 and
  E1; ZERO for slots B2 and D1; FREE for slots A2 and F1. If the study
  runs with 9 or 10 typical papers, slot 9 (group C) is WELL and slot 10
  (group A) is ZERO, keeping the target exact at ten papers. The strata
  measure visibility at the snapshot, not quality (Section 1.8); they
  are a balance constraint, and the stratum of every sampled paper is
  recorded at intake.
- Procedure: slots are filled strictly in the slot-map order (A1, A2,
  B1, B2, C1, D1, E1, F1, then any extension slots). Within each group,
  collect the eligible PMIDs in ascending order and shuffle them once
  with Python's `random.Random(f"{SEED}:{group}")`. Each slot walks its
  group's shuffled list restricted to its stratum, skipping papers
  already drawn for an earlier slot or already screened; the first paper
  passing the Section 6.4 intake screen fills the slot. A paper that
  fails intake is out of the study for all slots. Every draw and every
  screen outcome, pass or fail with reasons, is appended to this file.
  High intake rejection is expected in groups D, E and F (Section 1.4)
  and is part of the recorded design, not a deviation. The per-slot
  candidate lists printed by the command below overlap (a WELL paper
  also matches FREE); the skip rule above resolves the overlap at fill
  time.
- Exact command (run from the repository root):

```
python3 - <<'EOF'
import csv, datetime, random
SEED = "0"
SNAP = datetime.date(2026, 10, 15)
SLOTS = [  # filled strictly in this order
    ("A1", "A", "WELL"), ("A2", "A", "FREE"),
    ("B1", "B", "WELL"), ("B2", "B", "ZERO"),
    ("C1", "C", "WELL"), ("D1", "D", "ZERO"),
    ("E1", "E", "WELL"), ("F1", "F", "FREE"),
    # extension slots, only if the study runs with 9 or 10 papers:
    # ("C2", "C", "WELL"), ("A3", "A", "ZERO"),
]
GROUPS = {
    "Am J Hum Genet": "A", "Eur J Hum Genet": "A", "Hum Genet": "A",
    "J Med Genet": "A", "Genet Med": "A", "Clin Genet": "A",
    "Mol Genet Genomic Med": "A", "Nat Genet": "A",
    "Genet Epidemiol": "B", "Ann Hum Genet": "B", "HGG Adv": "B",
    "NPJ Genom Med": "B", "Hum Genomics": "B", "BMC Med Genomics": "B",
    "Hum Mol Genet": "C", "PLoS Genet": "C", "Genome Biol": "C",
    "BMC Genomics": "D", "BMC Genom Data": "D",
    "Nature": "E", "Science": "E", "Proc Natl Acad Sci U S A": "E",
    "Cell": "E", "Blood": "E",
    "PLoS Comput Biol": "F", "Bioinformatics": "F", "Brief Bioinform": "F",
    "BMC Bioinformatics": "F", "NAR Genom Bioinform": "F",
    "GigaScience": "F", "Genome Res": "F", "Genome Med": "F",
}
rows = [r for r in csv.DictReader(open("study/papers_frame.csv"))
        if not r["excluded_reason"]]
def in_stratum(r, s):
    c = int(r["citedby_epmc_20261015"] or 0)
    age = (SNAP - datetime.date.fromisoformat(r["earliest_date"])).days
    if s == "WELL":
        return c >= 2
    if s == "ZERO":
        return c == 0 and age >= 183
    return True
by_pmid = {int(r["pmid"]): r for r in rows}
order = {}
for g in "ABCDEF":
    pool = sorted(p for p, r in by_pmid.items() if GROUPS[r["journal"]] == g)
    random.Random(f"{SEED}:{g}").shuffle(pool)
    order[g] = pool
for slot, g, s in SLOTS:
    cand = [p for p in order[g] if in_stratum(by_pmid[p], s)]
    print(slot, g, s, len(cand), cand[:10])
EOF
```

- Pre-specified fallbacks, recorded before any draw: if a constrained
  slot exhausts its stratum within its group (every matching paper drawn
  or screened out), the slot drops its citation constraint and becomes
  FREE within the same group; if group E exhausts entirely, collapse it
  into group A; if group F exhausts, collapse it into group C; if group
  D exhausts, collapse it into group C; if any other group exhausts,
  fall back to simple random sampling over all remaining eligible rows
  under the same seed.
- Random seed: **0**, chosen for convention and recorded here by the
  study lead on 2026-10-15, before any draw (protocol Section 6.2).

### 1.6 Considered variants and selection history

All counts were taken on 2026-10-15 over the same window, language,
publication-type and open-access filters.

| Variant | Raw count | Status |
| --- | ---: | --- |
| v5: as executed (Section 1.1); three-part venue set, frame-wide somatic exclusion | 2055 (1975 eligible) | **executed** |
| v4: 19 specialist venues plus 5 filtered multidisciplinary venues, no somatic exclusion | 1952 (1873 eligible) | superseded by v5 |
| v1: 14-journal specialist core set | 757 (691 eligible) | superseded; executed first under a pre-committed count rule |
| v2: v1 plus Genetics, G3 (Bethesda), Dis Model Mech, Genome Med, Eur J Med Genet | 1331 | not executed |
| v3: journal-agnostic content-term query | 3256 | not executed; no crisp boundary |
| v1 / v2 without the open-access filter | 1362 / 2207 | comparison only |
| v2 with case reports kept | 1422 | comparison only |

History. v1 was executed first, selected among v1 to v3 by a rule
committed before any count was seen (prefer v2, then v1, then v3, first
count in [60, 450], else closest to 220; all counts exceeded the range,
so the rule picked v1 at 757). The study lead then directed the venue
extension of v4 on 2026-10-15 (Nature Genetics, Genome Biology, Cell,
Blood, genetics papers from Nature, Science and PNAS, and the BMC
genomics journals), and the same day directed v5: a computational
biology group entering through a stricter filter, the frame-wide somatic
exclusion, and keeping the low-yield venues. Superseded result lists are
archived outside version control.

Comp-bio entry filter measurement (2026-10-15): two candidates were
probed, F1 (genetics filter alone) and F2 (genetics filter plus the
phenotype clause). F2 was adopted: per venue it removes 8 to 40 percent
of F1's hits (Bioinformatics 37 to 24, PLoS Comput Biol 20 to 12, Brief
Bioinform 38 to 28, Genome Med 44 to 37, Genome Res 13 to 10, BMC
Bioinformatics 12 to 11, NAR Genom Bioinform 13 to 11), and the removed
hits in title samples were almost entirely tool, benchmark and non-human
papers mentioning GWAS or variants without disease or patient language.
The earlier blanket exclusion of these venues (considered in v4) was
reversed by the study lead: GEM wants papers whose method is
bioinformatic inference, and they are often published in these venues.

Somatic-exclusion measurement (2026-10-15): specialist venues 1832 to
1810 records (22 removed); filtered multidisciplinary counts Nature 37 to
34, PNAS 69 to 68, Blood 10 to 7, Cell 3 to 2, Science 1 to 1. Title
review of the removed Nature Genetics papers confirmed nearly all are
genuinely somatic; the recorded edge cases are in Section 1.3.

### 1.7 Known limitations

- Open-access bias: the OA filter keeps roughly half of specialist-venue
  records and the loss is uneven. Genet Med falls from 132 records to 4,
  Ann Hum Genet from 27 to 2, Science from 776 to 31, Cell from 363 to
  28; fully open venues (the BMC titles, PLoS journals, Genome Biol, Hum
  Genomics, HGG Adv) are correspondingly over-represented. The frame is
  typical of openly licensed publishing in these venues, not of the
  venues as a whole.
- Content-filter precision is limited and venue-dependent (Section 1.4),
  and its recall boundary is recorded: evidence papers phrased without
  any listed term are missed. A `humans[mh]` tightening was considered
  and rejected because most 2026 records are not yet MeSH-indexed, so it
  would collapse recall rather than improve precision.
- The somatic-genomics phrase exclusion has high precision but low recall
  against tumour genomics that avoids the exact phrases, notably in
  Blood; intake criterion 4 applies the scope judgement per paper
  (Section 1.3).
- Group D (BMC Genomics, BMC Genomic Data) is 34 percent of the eligible
  frame and roughly 70 percent non-human per a recorded title sample;
  such papers are judged at intake under criterion 4, and the allocation
  caps the group at one sampled paper.
- GigaScience resolves correctly but contributes 0 records: only 3 of its
  records fall in the window at all and none carried the OA-subset flag
  at search time, consistent with volume-year dating around January and
  PMC deposit lag. Recorded as an artefact, not an identity failure.
- Date-field quirks run in both directions: records with late-2026 print
  dates but in-window electronic dates remain eligible, and 80 records
  with 2026 print dates but pre-window electronic dates were excluded by
  the Section 1.1 rule.
- Publication-type flags on recent, not yet MEDLINE-indexed records are
  incomplete, so the type exclusions under-exclude; intake re-verifies
  article type, and MeSH terms were unusable for a 2026 window for the
  same reason.
- Preprint leakage: the date rule uses PubMed dates only; a paper may
  still have a preprint predating the cutoff. This matters especially for
  Nature, Science, Cell and Nat Genet, where pre-publication preprints
  are routine. Intake searches for earlier public versions of every
  sampled paper (Section 1.2, criterion 7).
- Prominence and familiarity: the frame includes flagship venues whose
  subject matter is heavily curated in public databases. The post-cutoff
  window removes verbatim training-data exposure; residual familiarity is
  recorded per paper under intake criterion 8 rather than excluded by
  design.
- Citation counts in the snapshot reflect Europe PMC indexing as of the
  snapshot date; citing papers take months to appear and be indexed, so
  young papers' counts are systematically censored (Section 1.8), and 25
  very recent records have no count at all.
- The frame is frozen as the recorded PMID list; retractions or licence
  changes after the search date are handled at intake for sampled papers
  only.

### 1.8 Citation snapshot: the screen (not adopted) and the strata (adopted)

The study lead proposed screening frame papers on citations scaled by
age, about 2 citations per 6 months. Two readings were formalised and
measured against the recorded snapshot (age from `earliest_date` to
2026-10-15; missing counts treated as 0):

- step rule: required citations = 2 x (age in days // 183);
- linear rule: required citations = age in days // 91.

Measured on the 1975 eligible papers:

| Age | Papers | Median citations | Share with zero |
| --- | ---: | ---: | ---: |
| 8 to 10 months | 167 | 1 | 47 percent |
| 6 to 8 months | 624 | 0 | 52 percent |
| 4 to 6 months | 544 | 0 | 71 percent |
| 2 to 4 months | 446 | 0 | 80 percent |
| 0 to 2 months | 194 | 0 | 90 percent |

Survival: step rule 1366 of 1975 (69 percent); linear rule 723 of 1975
(37 percent). The linear rule removes 220 of group B's 282 papers and 566
of group D's 667. The pattern shows that at these ages citation counts
measure citation lag and venue visibility, not paper quality: the median
paper 6 to 8 months old has zero recorded citations.

Status of the screen: **not adopted** (decided by the study lead
2026-10-15, on the measured numbers above). Instead, on the same date
the study lead adopted citation **stratification of the draw**: the
frame is not gated, and sampling slots carry citation strata (Section
1.5) with a 50/30/20 target of well cited, ungated and uncited papers.
The intent is to keep low-visibility papers in the sample deliberately
rather than screen them out, since papers of low credibility are useful
test material for the model.

Feasibility numbers behind the stratum definitions (eligible papers,
snapshot of 2026-10-15, age from `earliest_date`):

| Group | Eligible | Cited 2 or more | Cited 3 or more | Zero at 6+ months |
| --- | ---: | ---: | ---: | ---: |
| A | 299 | 80 | 56 | 39 |
| B | 282 | 17 | 5 | 76 |
| C | 493 | 107 | 49 | 57 |
| D | 667 | 24 | 10 | 205 |
| E | 103 | 27 | 23 | 11 |
| F | 131 | 13 | 5 | 18 |

- WELL is set at 2 or more citations, not 3 or more: at 3 the WELL pools
  in groups B and F hold only 5 candidates each and would likely exhaust
  under expected intake rejection. Across this young frame, 2 or more
  citations is already the top 14 percent.
- The study lead's original idea, papers uncited two years after
  publication, cannot be implemented inside this frame: intake criterion
  7 restricts the window to papers published after the model cutoff, so
  the oldest eligible paper is about 8.5 months old. ZERO (zero
  citations at 183 or more days) is the recorded nearest analogue. At
  these ages it marks low visibility more than low quality: 47 to 52
  percent of papers 6 to 10 months old have zero recorded citations.
  Deliberate selection of a suspected low-credibility paper remains
  open as a stress-stratum option (Section 2).
- Both constrained strata skew the draw toward the oldest slice of the
  window (WELL papers have a median age of about 6.5 months; ZERO
  requires 6 or more months by construction). This is accepted and
  recorded.

The snapshot column stays in the CSV, intake records every sampled
paper's citation count and stratum, and the strata are evaluated only
against the frozen dated column, never against live citation counts.

## 2. Stress stratum

Stress papers are selected deliberately (protocol Section 6.3). Each
receives an entry here, stating the expected challenge and the candidate
extensions it tests, before acceptance.

### Stress paper 1 (accepted): Marques et al. 2025

- Marques et al., *Differential DNA methylation and gene expression in
  stem cell-derived cardiomyocytes from patients with and without a
  history of clozapine-induced myocarditis*, J. Psychiatry Neurosci.
  50:E323-E333, doi:10.1139/jpn-25-0017, PMID 41170773, PMC12677137.
- Expected challenge: first exercise of the `EPIGENETICS` knowledge
  domain; targets of methylation findings (gene-attributed marks versus
  unattributed regions); domain assignment for per-group contrasts in
  patient-derived cell models.
- Candidate extensions tested: surfaced CE-M1 (epigenetics and the
  activation rules) and CE-M2 (epigenetic entity as target), both
  registered in `KNOWN_LIMITATIONS.md` Section 2.
- Status: H0 sealed 2026-10-15 (tag `study-marques2025-h0`, ledger entry
  S-1 in `study/SEALS.md`). Selected before this frame was built; not
  part of the typical frame. See `study/DEVIATIONS.md` D-pre-1 for the
  documented exception affecting this paper.

### Remaining stress slots (one to three)

Planned areas, from protocol Section 6.3, in proposed priority order:

1. Family-based inference: a rare-variant family segregation study,
   exercising family-based activation (CE-DU4) and direction of effect
   (CE-DU1).
2. Interaction targets (CE-J2): a gene-environment or gene-gene
   interaction study.
3. Polygenic-score extensions (CE-IN1 to CE-IN6), only if those
   candidates need direct stress testing beyond the pilot's Inouye 2018.

Candidates will be selected deliberately by the study lead, screened
under Section 6.4, and recorded here before acceptance. The somatic
revisit note in Section 1.3 also marks somatic genomics as a natural
future stress area once the model has machinery for it.

## 3. Decisions before the freeze

1. Citation screen: **decided 2026-10-15, not adopted.** Citations
   stratify the draw instead of gating the frame (Sections 1.5 and 1.8).
2. Sampling design: **adopted 2026-10-15**, with the citation-strata
   overlay; the 2/2/1/1/1/1 allocation and the extension order C then A
   are unchanged (Section 1.5).
3. Random seed: **recorded 2026-10-15: 0** (Section 1.5).
4. **Open:** confirm the number of typical papers (8; slots 9 and 10 are
   pre-specified in Section 1.5) and the number of stress slots to fill
   (one to three more).
