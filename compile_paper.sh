#!/usr/bin/env bash
# Compile the CEUR-art LaTeX paper in paper/ with latexmk.
# All intermediate and output files go to paper/target/.
set -euo pipefail

PAPER_DIR="$(cd "$(dirname "$0")/paper" && pwd)"
TARGET="$PAPER_DIR/target"
MAIN="main"
ENGINE="${LATEX_ENGINE:-pdflatex}"

mkdir -p "$TARGET"
cd "$PAPER_DIR"

latexmk -"$ENGINE" -bibtex -f -output-directory="$TARGET" "$MAIN.tex"

echo "==> Done: $TARGET/$MAIN.pdf"
