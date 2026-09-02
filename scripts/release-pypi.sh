#!/usr/bin/env bash
# =====================================================================
# release-pypi.sh — build, verify, and (on request) upload gem-mapping-studio.
#
# PyPI project: gem-mapping-studio   (account: https://pypi.org/user/mmcentre/)
#
# Usage:
#   scripts/release-pypi.sh              # sync + build + twine check + smoke test
#   scripts/release-pypi.sh --test       # ...then upload to TestPyPI
#   scripts/release-pypi.sh --upload     # ...then upload to PyPI (asks to confirm)
#
# Auth: create an API token at https://pypi.org/manage/account/token/ and
# either put it in ~/.pypirc, or export it for one run: set TWINE_USERNAME
# to __token__ and TWINE_PASSWORD to the token value (never commit or echo
# the token; secret scanners also flag literal assignments in docs).
# (TestPyPI needs its own token from https://test.pypi.org)
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
PY="${PYTHON:-python3}"

err() { echo "ERROR: $*" >&2; exit 1; }

MODE="build"
case "${1:-}" in
  --upload) MODE="upload" ;;
  --test)   MODE="test" ;;
  "")       ;;
  *) err "unknown option: $1 (use --test or --upload)" ;;
esac

# ----- preflight ------------------------------------------------------
VERSION=$("$PY" - <<'EOF'
import tomllib
print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])
EOF
)
echo "==> gem-mapping-studio version $VERSION"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "WARNING: working tree has uncommitted changes; the sdist is built" \
       "from the files on disk, not from a git state." >&2
fi
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
  echo "==> tag v$VERSION exists"
else
  echo "NOTE: no git tag v$VERSION yet — consider 'git tag v$VERSION' at the release commit."
fi

# ----- sync packaged reference data (sources of truth -> _reference) --
REF="src/python/main/forome/gem/_reference"
cp data/umls/semantic_types.yaml "$REF/"
cp schema/genetic_evidence.shacl.ttl "$REF/"
cp schema/dimensions.md "$REF/"
echo "==> packaged reference data synced from data/umls/ and schema/"

# ----- test suite -----------------------------------------------------
PYTHONPATH=src/python/main:src/python/test "$PY" -m pytest src/python/test -q \
  || err "test suite failed; not building"

# ----- build ----------------------------------------------------------
"$PY" -m pip install --quiet --upgrade build twine
rm -rf dist
"$PY" -m build
"$PY" -m twine check dist/*

# ----- smoke test: install the wheel OUTSIDE the repo -----------------
# Exercises the standalone story: console scripts resolve, and the packaged
# reference fallback serves semantic types and the SHACL schema with no
# repo checkout present.
SMOKE=$(mktemp -d)
trap 'rm -rf "$SMOKE"' EXIT
"$PY" -m venv "$SMOKE/venv"
"$SMOKE/venv/bin/pip" install --quiet dist/*.whl
( cd "$SMOKE" && "$SMOKE/venv/bin/python" - <<'EOF'
from forome.gem.umls import semantic_types as st
t = st.get("T028")
assert t and t["name"] == "Gene or Genome", t
from forome.gem.umls._paths import SCHEMA_DIR
assert (SCHEMA_DIR / "genetic_evidence.shacl.ttl").is_file(), SCHEMA_DIR
print("smoke: packaged reference fallback OK")
EOF
)
( cd "$SMOKE" && "$SMOKE/venv/bin/gem-mapping-studio" --help >/dev/null ) \
  && echo "smoke: gem-mapping-studio --help OK"

echo "==> build verified: $(ls dist)"

# ----- upload ---------------------------------------------------------
case "$MODE" in
  test)
    "$PY" -m twine upload --repository testpypi dist/*
    echo "==> uploaded to TestPyPI: https://test.pypi.org/project/gem-mapping-studio/$VERSION/"
    ;;
  upload)
    printf "Upload gem-mapping-studio %s to PyPI (account mmcentre)? [y/N] " "$VERSION"
    read -r ans
    [ "$ans" = "y" ] || err "aborted"
    "$PY" -m twine upload dist/*
    echo "==> uploaded: https://pypi.org/project/gem-mapping-studio/$VERSION/"
    echo "    tag the release: git tag v$VERSION && git push origin v$VERSION"
    ;;
  build)
    echo "==> dry run complete. Use --test for TestPyPI or --upload for PyPI."
    ;;
esac
