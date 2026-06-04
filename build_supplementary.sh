#!/usr/bin/env bash
#
# build_supplementary.sh
#
# Regenerate the ICBO 2026 supplementary material PDF from the
# current SHACL schema and YAML annotations.
#
# Source of truth:
#   schema/genetic_evidence.shacl.ttl
#   annotations/<paper>.yaml  for each of six papers
#
# Output:
#   supplementary.pdf  (at repo root)
#
# Dependencies (must be on PATH):
#   pandoc       (tested with 3.1.3)
#   xelatex      (tested with TeX Live 2023; needs lmodern.sty)
#   python3      (any recent version)
#
# Usage:
#   ./build_supplementary.sh
#
# To regenerate after editing any annotation YAML, just run this
# script again. Output is deterministic: identical inputs produce
# identical PDFs (modulo the embedded build timestamp).
#

set -euo pipefail

# ----- configuration ------------------------------------------------

REPO_BASE_URL="https://github.com/ForomePlatform/genetic-evidence-model/blob/master"
W3ID_NS="https://w3id.org/genetic-evidence-model/"

SCHEMA_FILE="schema/genetic_evidence.shacl.ttl"

# Papers in the order they should appear in the supplementary.
# Each entry: yaml-stem  display-name  role-blurb
PAPERS=(
  "jossin2017|Jossin et al. 2017 (Llgl1)|Manual annotation. 6 GeneticEvidence items. Multi-scale phenotype exemplar. Surfaces three candidate extensions (CE-J1, CE-J2, CE-J3) including the gene-relation enumeration gap referenced in section 6.1."
  "davis2011|Davis et al. 2011 (TTC21B)|Manual annotation. 6 GeneticEvidence items. Breadth exemplar combining case-control resequencing, zebrafish in vivo complementation, in vitro rescue, and pedigree segregation. The sole reviewer_disagreement in the corpus arises from this paper. Surfaces two candidate extensions (CE-D1, CE-D2)."
  "nelson1992|Nelson et al. 1992 (CD18)|Manual annotation. 3 GeneticEvidence items. Classical molecular-genetics paper from before HPO, ClinVar, and VEP existed. Surfaces one candidate extension (CE-N1) which on review was retired to a discussion-section observation about VRS integration."
  "gupta2015|Gupta et al. 2015 (ATP6AP2)|Manual annotation. 2 GeneticEvidence items. Low-credibility edge case and the corpus's schema-fits-cleanly positive finding. Surfaces no candidate extensions."
  "duerr2006|Duerr et al. 2006 (IL23R)|AI-drafted annotation, curator-reviewed. 6 GeneticEvidence items. Reference example of a classical variant-level association study. Three ai_uncertainty flags concentrated on scoping and enumeration decisions. One candidate extension (CE-DU1); one earlier candidate (CE-DU2) was retracted on review."
  "inouye2018|Inouye et al. 2018 (metaGRS)|AI-drafted annotation, curator-reviewed. 5 GeneticEvidence items. Polygenic-score model-extension stress test. Surfaces six candidate extensions (CE-IN1 through CE-IN6) covering score target type, whole-genome aggregate resolution, target composition, epidemiological measurement targets, structured cohort descriptors, and the natural-vs-derived-artifact distinction."
)

# ----- helpers ------------------------------------------------------

err() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "[$(date +%H:%M:%S)] $*"; }

# ----- preflight checks ---------------------------------------------

info "Checking dependencies..."

for cmd in pandoc xelatex python3; do
  command -v "$cmd" >/dev/null 2>&1 \
    || err "missing dependency: $cmd. Install it and retry."
done

# Check xelatex can find lmodern (the previous build failure mode)
if ! kpsewhich lmodern.sty >/dev/null 2>&1; then
  err "xelatex cannot find lmodern.sty. On Debian/Ubuntu: sudo apt-get install lmodern texlive-fonts-recommended"
fi

info "Checking input files..."

[[ -f "$SCHEMA_FILE" ]] || err "schema file not found: $SCHEMA_FILE"

for entry in "${PAPERS[@]}"; do
  stem="${entry%%|*}"
  yaml="annotations/${stem}.yaml"
  [[ -f "$yaml" ]] || err "annotation file not found: $yaml"
done

info "All inputs present."

# ----- build the markdown source ------------------------------------

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

MD="$WORK_DIR/supplementary.md"

info "Building markdown source at $MD..."

# Front matter and cover material
cat > "$MD" <<EOF
---
title: |
  Supplementary Material for
  "A Semantic Model of Genetic Evidence:
  A Step Toward Bridging the Basic-Science--Clinic Gap"
author: |
  Michael Bouzinier, Dmitry Etin
date: ICBO 2026 submission
geometry: margin=2cm
fontsize: 10pt
colorlinks: true
linkcolor: blue
urlcolor: blue
toc: true
toc-depth: 1
---

\\newpage

# About this document

This supplementary material bundles the core technical artefacts
referenced in the paper, so reviewers can verify schema and
annotation claims directly from the submission system without
leaving for the public repository.

The complete repository, including case reports, walkthroughs,
the full candidate-extensions log, the human-readable dimension
reference, and the extraction tooling, is available at:

<${REPO_BASE_URL%/blob/master}>

The namespace <${W3ID_NS}> resolves to the same repository.

Each section below cites the file's authoritative URL in the
repository. The repository is the single source of truth; this
PDF is a static snapshot for reviewer convenience.

\\newpage

# Appendix A: SHACL schema (\`genetic_evidence.shacl.ttl\`)

**Authoritative source:**
<${REPO_BASE_URL}/${SCHEMA_FILE}>

The SHACL distribution covers class declarations, dimension
enumerations, and conditional-activation rules expressed as
SPARQL-based shapes. Together with the human-readable dimension
reference in \`schema/dimensions.md\` (not included here; see
repository), it constitutes the complete machine-checkable
representation of the model.

\`\`\`turtle
EOF

# Append schema content
cat "$SCHEMA_FILE" >> "$MD"

cat >> "$MD" <<'EOF'
```

\newpage

# Appendix B: Annotation YAML files

**Authoritative source:**
EOF

echo "<${REPO_BASE_URL%/blob/master}/tree/master/annotations>" >> "$MD"

cat >> "$MD" <<'EOF'

The six YAML files below are the per-paper annotations whose
aggregate counts are reported in section 5.1 (`tab:coverage`) and
section 5.2 (flag totals) of the paper. Each annotation contains
the paper's publication metadata, the curator's summary table, the
`GeneticEvidence` items with their dimension values and
source-anchored assertions, the `candidate_extensions` block
listing schema gaps surfaced during annotation, the reviewer
flags, and an annotator-omitted-dimensions audit log.

The four manual annotations (Jossin, Davis, Nelson, Gupta) were
authored by Vladimir Seplyarskiy and are treated as ground truth.
The two AI-drafted annotations (Duerr, Inouye) were produced by
Claude Opus 4.7 Adaptive working from the schema, the four
manual annotations, and the source PDFs; they were
curator-reviewed assertion-by-assertion.

EOF

# Append each paper's section
i=1
for entry in "${PAPERS[@]}"; do
  stem="${entry%%|*}"
  rest="${entry#*|}"
  name="${rest%%|*}"
  blurb="${rest#*|}"
  yaml="annotations/${stem}.yaml"

  cat >> "$MD" <<EOF

\\newpage

## B.${i} ${name}

**Authoritative source:**
<${REPO_BASE_URL}/${yaml}>

${blurb}

\`\`\`yaml
EOF
  cat "$yaml" >> "$MD"
  echo '```' >> "$MD"
  echo "" >> "$MD"

  i=$((i + 1))
done

info "Markdown source built ($(wc -l < "$MD") lines)."

# ----- run pandoc ---------------------------------------------------

OUT="supplementary.pdf"

info "Running pandoc to produce $OUT..."

pandoc "$MD" \
  --pdf-engine=xelatex \
  --highlight-style=tango \
  -V geometry:margin=2cm \
  -V fontsize=10pt \
  -o "$OUT"

PAGES=$(python3 -c "from pypdf import PdfReader; print(len(PdfReader('$OUT').pages))" 2>/dev/null || echo "?")
SIZE=$(du -h "$OUT" | cut -f1)

info "Done. Output: $OUT ($PAGES pages, $SIZE)"
