#!/usr/bin/env bash
#
# build_skill_bundle.sh
#
# Assemble a self-contained ZIP bundle of one of the GEM skills
# for upload to claude.ai (Customize > Skills > + Create skill).
#
# Two skills are currently supported:
#
#   genetic-evidence-annotation   (autonomous annotation; default)
#   genetic-evidence-review       (interactive review of an annotation)
#
# Usage:
#   ./build_skill_bundle.sh                                # builds annotation skill (default)
#   ./build_skill_bundle.sh --skill annotation             # same as above
#   ./build_skill_bundle.sh --skill review                 # builds review skill
#   ./build_skill_bundle.sh --skill annotation --check     # dry-run
#
# Layout of an annotation-skill bundle:
#
#   genetic-evidence-annotation-skill.zip
#   └── genetic-evidence-annotation/
#       ├── SKILL.md
#       ├── LICENSE.txt                 (CC BY 4.0: docs, protocols, annotations)
#       ├── LICENSE-code.txt            (Apache 2.0: schema and tooling)
#       ├── PROTOCOL.md
#       ├── PROTOCOL_AUTONOMOUS.md
#       ├── LABELING_EXAMPLES.md
#       ├── schema/
#       │   ├── dimensions.md
#       │   ├── EXTENSIONS.md
#       │   └── genetic_evidence.shacl.ttl
#       └── exemplars/                  (four curator-led annotations)
#           ├── jossin2017.yaml
#           ├── davis2011.yaml
#           ├── nelson1992.yaml
#           └── gupta2015.yaml
#
# Layout of a review-skill bundle:
#
#   genetic-evidence-review-skill.zip
#   └── genetic-evidence-review/
#       ├── SKILL.md
#       ├── LICENSE.txt                 (CC BY 4.0: docs, protocols, annotations)
#       ├── LICENSE-code.txt            (Apache 2.0: schema and tooling)
#       ├── REVIEW_PROTOCOL.md
#       ├── REVIEW_PROTOCOL_INTERACTIVE.md
#       ├── PROTOCOL.md                 (annotation protocol; reviewer needs it)
#       ├── LABELING_EXAMPLES.md
#       ├── ROADMAP.md
#       └── schema/
#           ├── dimensions.md
#           ├── EXTENSIONS.md
#           └── genetic_evidence.shacl.ttl
#
# Path references in SKILL.md and the protocol files are rewritten
# during bundling so the bundled skill is self-contained without
# modifying the in-repo files.
#
# Requirements:
#   bash, zip, sed
#
# Run from the repository root.
#

set -euo pipefail

# ----- argument parsing ---------------------------------------------

SKILL_KIND="annotation"
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill)
      SKILL_KIND="$2"
      shift 2
      ;;
    --skill=*)
      SKILL_KIND="${1#*=}"
      shift
      ;;
    --check)
      CHECK_ONLY=true
      shift
      ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \?//' | head -70
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1 (try --help)" >&2
      exit 1
      ;;
  esac
done

# Normalise SKILL_KIND
case "$SKILL_KIND" in
  annotation|genetic-evidence-annotation)
    SKILL_KIND="annotation"
    SKILL_NAME="genetic-evidence-annotation"
    ;;
  review|genetic-evidence-review)
    SKILL_KIND="review"
    SKILL_NAME="genetic-evidence-review"
    ;;
  *)
    echo "ERROR: unknown --skill value: $SKILL_KIND" >&2
    echo "       valid options: annotation, review" >&2
    exit 1
    ;;
esac

OUTPUT_ZIP="${SKILL_NAME}-skill.zip"

# ----- helpers ------------------------------------------------------

err()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo "[$(date +%H:%M:%S)] $*"; }

# ----- per-skill configuration --------------------------------------

# Common files (used by both skills)
SKILL_MD="skills/${SKILL_NAME}/SKILL.md"
LABELING_MD="protocols/LABELING_EXAMPLES.md"
SCHEMA_FILES=(
  "schema/dimensions.md"
  "schema/EXTENSIONS.md"
  "schema/genetic_evidence.shacl.ttl"
)
# License files shipped with every bundle: the documentation/protocols/
# annotations are CC BY 4.0; the schema and tooling are Apache 2.0.
LICENSE_FILES=(
  "LICENSE.txt"
  "LICENSE-code.txt"
)

# Skill-specific files
if [[ "$SKILL_KIND" == "annotation" ]]; then
  TOP_LEVEL_MD_FILES=(
    "protocols/PROTOCOL.md"
    "protocols/PROTOCOL_AUTONOMOUS.md"
    "$LABELING_MD"
  )
  # Only the four curator-led annotations are bundled. The two
  # AI-drafted annotations (Duerr, Inouye) are deliberately excluded:
  # they are the same kind of output this skill produces, and using
  # them as templates would propagate any weaknesses they carry.
  EXEMPLAR_FILES=(
    "annotations/jossin2017.yaml"
    "annotations/davis2011.yaml"
    "annotations/nelson1992.yaml"
    "annotations/gupta2015.yaml"
  )
else  # review
  TOP_LEVEL_MD_FILES=(
    "protocols/REVIEW_PROTOCOL.md"
    "protocols/REVIEW_PROTOCOL_INTERACTIVE.md"
    "protocols/PROTOCOL.md"
    "$LABELING_MD"
    "notes/ROADMAP.md"
  )
  # The review skill does not bundle exemplar annotations: the
  # annotation under review is supplied by the user at runtime.
  EXEMPLAR_FILES=()
fi

# ----- preflight ----------------------------------------------------

info "Building bundle for skill: $SKILL_NAME"
info "Checking dependencies..."

for cmd in zip sed; do
  command -v "$cmd" >/dev/null 2>&1 \
    || err "missing dependency: $cmd"
done

info "Checking input files..."

ALL_INPUTS=("$SKILL_MD" "${TOP_LEVEL_MD_FILES[@]}"
            "${SCHEMA_FILES[@]}" "${LICENSE_FILES[@]}" "${EXEMPLAR_FILES[@]:-}")

missing=0
for f in "${ALL_INPUTS[@]}"; do
  [[ -z "$f" ]] && continue
  if [[ ! -f "$f" ]]; then
    echo "  MISSING: $f" >&2
    missing=$((missing + 1))
  fi
done

if [[ $missing -gt 0 ]]; then
  err "$missing input file(s) missing. Run from repository root."
fi

info "All inputs present."

if [[ "$CHECK_ONLY" == "true" ]]; then
  info "--check passed. No bundle built."
  exit 0
fi

# ----- assemble in temp dir -----------------------------------------

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

STAGE="$WORK_DIR/$SKILL_NAME"
mkdir -p "$STAGE/schema"
[[ ${#EXEMPLAR_FILES[@]} -gt 0 ]] && mkdir -p "$STAGE/exemplars"

info "Staging files in $STAGE..."

# Path-rewriting sed expression: strips protocols/ prefix from all
# protocol file references so the bundled paths resolve in the flat
# bundle layout.
SED_REWRITE='
  s|`protocols/PROTOCOL\.md`|`PROTOCOL.md`|g
  s|`protocols/PROTOCOL_AUTONOMOUS\.md`|`PROTOCOL_AUTONOMOUS.md`|g
  s|`protocols/PROTOCOL_INTERACTIVE\.md`|`PROTOCOL_INTERACTIVE.md`|g
  s|`protocols/REVIEW_PROTOCOL\.md`|`REVIEW_PROTOCOL.md`|g
  s|`protocols/REVIEW_PROTOCOL_INTERACTIVE\.md`|`REVIEW_PROTOCOL_INTERACTIVE.md`|g
  s|`protocols/REVIEW_PROTOCOL_BATCH\.md`|`REVIEW_PROTOCOL_BATCH.md`|g
  s|`protocols/LABELING_EXAMPLES\.md`|`LABELING_EXAMPLES.md`|g
  s|`notes/ROADMAP\.md`|`ROADMAP.md`|g
'

# SKILL.md (always present)
sed -E "$SED_REWRITE" "$SKILL_MD" > "$STAGE/SKILL.md"

# Top-level markdown files (protocols, labeling, migration notes)
for f in "${TOP_LEVEL_MD_FILES[@]}"; do
  sed -E "$SED_REWRITE" "$f" > "$STAGE/$(basename "$f")"
done

# Schema files: straight copy
for f in "${SCHEMA_FILES[@]}"; do
  cp "$f" "$STAGE/schema/$(basename "$f")"
done

# License files: straight copy to the bundle root
for f in "${LICENSE_FILES[@]}"; do
  cp "$f" "$STAGE/$(basename "$f")"
done

# Exemplars: straight copy (annotation skill only)
for f in "${EXEMPLAR_FILES[@]:-}"; do
  [[ -z "$f" ]] && continue
  cp "$f" "$STAGE/exemplars/$(basename "$f")"
done

# Bundle README, customised per skill kind
if [[ "$SKILL_KIND" == "annotation" ]]; then
  cat > "$STAGE/BUNDLE_README.md" <<'BUNDLE_EOF'
# Skill bundle: genetic-evidence-annotation

This is a self-contained bundle of the genetic-evidence-annotation
skill, suitable for upload to claude.ai via Customize > Skills.

Entry point: SKILL.md

Layout:
  SKILL.md                            Skill entry point
  LICENSE.txt                         CC BY 4.0 (docs, protocols, annotations)
  LICENSE-code.txt                    Apache 2.0 (schema and tooling)
  PROTOCOL.md                         Canonical protocol rules
  PROTOCOL_AUTONOMOUS.md              Autonomous-mode workflow
  LABELING_EXAMPLES.md                Concrete label patterns from exemplars
  schema/                             Schema files (read-only reference)
  exemplars/                          Four curator-led exemplar annotations

Exemplars policy: only the four curator-led annotations (Jossin,
Davis, Nelson, Gupta) are bundled. The two AI-drafted annotations
in the source corpus (Duerr, Inouye) are deliberately excluded:
they are the same kind of output this skill produces, and using
them as templates would propagate any weaknesses they carry.

Path references in SKILL.md and the protocol files have been
rewritten for the bundled layout (e.g., `PROTOCOL.md` instead of
`protocols/PROTOCOL.md`). They do not match the repository layout
used by Claude Code; for Claude Code, install the skill folder
from the repository directly, not this bundle.

Licensing: the documentation, protocols, and annotations in this bundle
are licensed CC BY 4.0 (LICENSE.txt); the schema and tooling are licensed
Apache 2.0 (LICENSE-code.txt).

Canonical source repository:
https://github.com/ForomePlatform/genetic-evidence-model

Bundle built by build_skill_bundle.sh
BUNDLE_EOF
else  # review
  cat > "$STAGE/BUNDLE_README.md" <<'BUNDLE_EOF'
# Skill bundle: genetic-evidence-review

This is a self-contained bundle of the genetic-evidence-review
skill, suitable for upload to claude.ai via Customize > Skills.

Entry point: SKILL.md

Layout:
  SKILL.md                            Skill entry point
  LICENSE.txt                         CC BY 4.0 (docs, protocols, annotations)
  LICENSE-code.txt                    Apache 2.0 (schema and tooling)
  REVIEW_PROTOCOL.md                  Canonical review rules
  REVIEW_PROTOCOL_INTERACTIVE.md      Interactive review workflow
  PROTOCOL.md                         Annotation protocol (the rules under
                                      which annotations are produced; the
                                      reviewer consults these to evaluate
                                      conformance)
  LABELING_EXAMPLES.md                Label-style reference (for label checks)
  ROADMAP.md                          Project roadmap; includes method-
                                      hierarchy migration plan
  schema/                             Schema files (read-only reference)

This bundle does not include exemplar annotations: the
annotation under review is supplied by the user at runtime.

The skill conducts review interactively in dialogue with the
curator. See SKILL.md for the workflow.

Path references in SKILL.md and the protocol files have been
rewritten for the bundled layout (e.g., `PROTOCOL.md` instead of
`protocols/PROTOCOL.md`). They do not match the repository layout
used by Claude Code; for Claude Code, install the skill folder
from the repository directly, not this bundle.

Licensing: the documentation, protocols, and annotations in this bundle
are licensed CC BY 4.0 (LICENSE.txt); the schema and tooling are licensed
Apache 2.0 (LICENSE-code.txt).

Canonical source repository:
https://github.com/ForomePlatform/genetic-evidence-model

Bundle built by build_skill_bundle.sh
BUNDLE_EOF
fi

info "Stage prepared: $(find "$STAGE" -type f | wc -l) files."

# ----- zip ----------------------------------------------------------

[[ -f "$OUTPUT_ZIP" ]] && rm "$OUTPUT_ZIP"

( cd "$WORK_DIR" && zip -rq "${OLDPWD}/$OUTPUT_ZIP" "$SKILL_NAME" )

if [[ ! -f "$OUTPUT_ZIP" ]]; then
  err "zip command did not produce $OUTPUT_ZIP"
fi

SIZE=$(du -h "$OUTPUT_ZIP" | cut -f1)
COUNT=$(unzip -l "$OUTPUT_ZIP" | tail -1 | awk '{print $2}')

info "Done. $OUTPUT_ZIP ($SIZE, $COUNT files)"
echo ""
echo "To upload to claude.ai:"
echo "  1. Open claude.ai > Customize > Skills"
echo "  2. Click + Create skill"
echo "  3. Upload $OUTPUT_ZIP"
echo ""
echo "Contents preview:"
unzip -l "$OUTPUT_ZIP" | head -30
