#!/usr/bin/env bash
# Compile the LaTeX paper and its supplement in paper/ with latexmk.
# All intermediate and output files go to paper/target/.
#   main.tex       (ceurart) -> target/Semantic-GEM.pdf
#   supplement.tex (article) -> target/Semantic-GEM-SupplementaryMaterial.pdf
set -euo pipefail

PAPER_DIR="$(cd "$(dirname "$0")/paper" && pwd)"
TARGET="$PAPER_DIR/target"
ENGINE="${LATEX_ENGINE:-pdflatex}"

# Map the engine name to latexmk's PDF-mode flag (latexmk has no bare -pdflatex).
case "$ENGINE" in
  pdflatex) ENGINE_FLAG="-pdf"    ;;
  xelatex)  ENGINE_FLAG="-pdfxe"  ;;
  lualatex) ENGINE_FLAG="-pdflua" ;;
  *) echo "Unknown LATEX_ENGINE: '$ENGINE' (use pdflatex|xelatex|lualatex)" >&2; exit 2 ;;
esac

# Documents to build, as "source-basename:output-jobname" (order preserved).
DOCS=(
  "main:Semantic-GEM"
  "supplement:Semantic-GEM-SupplementaryMaterial"
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
  else
    echo "==> FAILED: $src.tex (see $TARGET/$job.log)" >&2
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  echo "==> Done. PDFs in $TARGET/"
else
  echo "==> Completed WITH ERRORS; check the .log file(s) in $TARGET/" >&2
fi
exit $status
