#!/usr/bin/env bash
# =====================================================================
# compile_paper.sh
#
# Single build script for the ICBO 2026 paper AND its supplement.
# (Combines the former compile_paper.sh + build_supplementary.sh: the
# supplement now embeds the SHACL schema and the six annotation YAMLs
# directly as Appendix A / Appendix B via \lstinputlisting in
# paper/sections/s3_appendices.tex, so there is no separate pandoc
# bundle to build. Editing any annotation YAML or the schema and
# re-running this script regenerates the supplement with the new
# content and the full table of contents.)
#
# Builds with latexmk; all intermediate and output files go to
# paper/target/:
#   main.tex       (ceurart) -> target/Semantic-GEM.pdf
#   supplement.tex (article) -> target/Semantic-GEM-SupplementaryMaterial.pdf
#
# The supplement's table of contents lists S1 Notes, S2 Tables, and
# S3 Appendices, with every appendix entry (the schema and each of the
# six papers, B.1-B.6) shown individually.
#
# Usage:
#   ./compile_paper.sh                 # build both documents
#   LATEX_ENGINE=xelatex ./compile_paper.sh
#
# Dependencies: latexmk + a LaTeX engine (pdflatex by default).
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
PAPER_DIR="$REPO_ROOT/paper"
TARGET="$PAPER_DIR/target"
ENGINE="${LATEX_ENGINE:-pdflatex}"

err() { echo "ERROR: $*" >&2; exit 1; }

# Map the engine name to latexmk's PDF-mode flag (latexmk has no bare -pdflatex).
case "$ENGINE" in
  pdflatex) ENGINE_FLAG="-pdf"    ;;
  xelatex)  ENGINE_FLAG="-pdfxe"  ;;
  lualatex) ENGINE_FLAG="-pdflua" ;;
  *) err "Unknown LATEX_ENGINE: '$ENGINE' (use pdflatex|xelatex|lualatex)" ;;
esac

# ----- preflight: dependencies --------------------------------------
command -v latexmk >/dev/null 2>&1 || err "missing dependency: latexmk"
command -v "$ENGINE" >/dev/null 2>&1 || err "missing dependency: $ENGINE"

# ----- preflight: input files the supplement embeds -----------------
# The supplement \lstinputlistings these; a missing one fails the build
# late and noisily, so check up front.
APPENDIX_INPUTS=(
  "schema/genetic_evidence.shacl.ttl"
  "annotations/jossin2017.yaml"
  "annotations/davis2011.yaml"
  "annotations/nelson1992.yaml"
  "annotations/gupta2015.yaml"
  "annotations/v0/duerr2006.yaml"
  "annotations/v0/inouye2018.yaml"
  "paper/sections/s3_appendices.tex"
)
missing=0
for f in "${APPENDIX_INPUTS[@]}"; do
  if [[ ! -f "$REPO_ROOT/$f" ]]; then
    echo "  MISSING: $f" >&2
    missing=$((missing + 1))
  fi
done
[[ $missing -eq 0 ]] || err "$missing supplement input file(s) missing."

# Documents to build, as "source-basename:output-jobname" (order preserved).
# Order matters: the supplement builds FIRST so its .aux exists for the
# main paper's xr cross-document references (Supplementary Table/Note numbers).
DOCS=(
  "supplement:Semantic-GEM-SupplementaryMaterial"
  "main:Semantic-GEM"
)

mkdir -p "$TARGET"
cd "$PAPER_DIR"

status=0
for entry in "${DOCS[@]}"; do
  src="${entry%%:*}"
  job="${entry##*:}"
  echo "==> Building $src.tex -> $TARGET/$job.pdf"
  # 'if' guards latexmk so 'set -e' does not abort the loop on one doc's failure.
  if latexmk "$ENGINE_FLAG" -bibtex -f -interaction=nonstopmode \
             -jobname="$job" -output-directory="$TARGET" "$src.tex"; then
    echo "==> OK:     $TARGET/$job.pdf"
    if [ "$src" = "supplement" ]; then
      # Labels-only aux for the main paper's xr cross-references: the raw aux
      # carries \citation/\@writefile lines that xr cannot digest in the
      # preamble, so extract just the \newlabel lines.
      grep '^\\newlabel' "$TARGET/$job.aux" > "$TARGET/supp-labels.aux"
      echo "==> wrote $TARGET/supp-labels.aux ($(grep -c . "$TARGET/supp-labels.aux") labels)"
    fi
  else
    echo "==> FAILED: $src.tex (see $TARGET/$job.log)" >&2
    status=1
  fi
done

# ----- undefined-reference check -------------------------------------
# Cross-document numbers are now real \ref*{supp:...} references resolved by
# xr, so a broken one shows up as an undefined-reference warning; fail on it.
if [ "$status" -eq 0 ]; then
  for job in Semantic-GEM Semantic-GEM-SupplementaryMaterial; do
    if grep -q "LaTeX Warning: Reference .* undefined" "$TARGET/$job.log"; then
      grep "LaTeX Warning: Reference .* undefined" "$TARGET/$job.log" >&2
      err "undefined references in $job (stale supplement label? rebuild both)"
    fi
  done
  echo "==> reference check: no undefined references in either document"
fi

if [ "$status" -eq 0 ]; then
  echo "==> Done. PDFs in $TARGET/"
else
  echo "==> Completed WITH ERRORS; check the .log file(s) in $TARGET/" >&2
fi
exit $status
