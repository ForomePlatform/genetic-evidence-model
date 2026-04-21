#!/usr/bin/env bash
# Compile the CEUR-art LaTeX paper in paper/ with latexmk.
# All intermediate and output files go to paper/target/.
set -euo pipefail

PAPER_DIR="$(cd "$(dirname "$0")/paper" && pwd)"
TARGET="$PAPER_DIR/target"
MAIN="main"
JOBNAME="Semantic-GEM"        # pick whatever you want here
ENGINE="${LATEX_ENGINE:-pdflatex}"

mkdir -p "$TARGET"
cd "$PAPER_DIR"

latexmk -"$ENGINE" -bibtex -f -jobname="$JOBNAME" -output-directory="$TARGET" "$MAIN.tex"

echo "==> Done: $TARGET/$JOBNAME.pdf"
