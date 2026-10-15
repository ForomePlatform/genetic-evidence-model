#!/usr/bin/env bash
#
# study-convert.sh - convert one study pass's worksheet export to YAML.
#
# Usage:
#   scripts/study-convert.sh <paper-id> <pass>     # pass: h0 | h1 | h0r
#
# Expands to the study-layout converter call documented in
# docs/WORKSHEET_SOP.md step 3:
#
#   gem-worksheet-to-yaml study/raw/<paper-id>/<pass>.xlsx \
#       study/processed/<paper-id>/<pass>/<pass>.yaml \
#       --effort study/processed/<paper-id>/<pass>/effort.csv
#
# Runs from any directory: paths resolve against the repository root. Takes
# no other options; in particular it cannot pass --force.

set -euo pipefail

usage() {
  echo "usage: $0 <paper-id> <pass>    # pass: h0 | h1 | h0r" >&2
  exit 2
}

err() {
  echo "ERROR: $*" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
paper="$1"
pass="$2"

[[ "$paper" =~ ^[a-z0-9][a-z0-9-]*$ ]] \
  || err "paper-id '$paper' is not lowercase surname+year, e.g. marques2025"
case "$pass" in
  h0|h1|h0r) ;;
  *) err "pass '$pass' is not one of: h0 h1 h0r" ;;
esac

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

raw="study/raw/$paper/$pass.xlsx"
out="study/processed/$paper/$pass/$pass.yaml"
eff="study/processed/$paper/$pass/effort.csv"

[[ -f "$raw" ]] || err "no export at $root/$raw
       Save the Google Sheets download there first (docs/WORKSHEET_SOP.md, step 2)."

# Prefer the installed console script; fall back to the in-repo module file
# (its own error message explains the openpyxl dependency if that is missing).
if command -v gem-worksheet-to-yaml >/dev/null 2>&1; then
  conv=(gem-worksheet-to-yaml)
else
  conv=(python3 src/python/main/forome/gem/extraction/worksheet_to_yaml.py)
fi

echo "+ ${conv[*]} $raw $out --effort $eff"
"${conv[@]}" "$raw" "$out" --effort "$eff"
echo
echo "Next: gem-validate $out    (docs/WORKSHEET_SOP.md, step 4)"
