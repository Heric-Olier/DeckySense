#!/usr/bin/env bash
# Package the plugin into a .zip with the layout Decky Loader expects.
#
# Output: out/<name>-v<version>.zip containing a single top-level directory
# named after the plugin (read from package.json) with dist/, package.json,
# plugin.json, main.py, README.md, LICENSE, defaults/ and py_modules/.
#
# Used locally and by the release GitHub Action.
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION=$(node -p "require('./package.json').version")
NAME=$(node -p "require('./package.json').name")
OUT_DIR="out"
ZIP="${OUT_DIR}/${NAME}-v${VERSION}.zip"

if [[ ! -f dist/index.js ]]; then
  echo "dist/index.js not found. Run 'pnpm run build' first." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
rm -f "${ZIP}"

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
mkdir "${STAGE}/${NAME}"

cp -r dist "${STAGE}/${NAME}/"
find "${STAGE}/${NAME}/dist" -name '*.map' -delete

cp -r defaults py_modules "${STAGE}/${NAME}/"
cp package.json plugin.json main.py README.md LICENSE "${STAGE}/${NAME}/"

( cd "${STAGE}" && zip -r -q "${OLDPWD}/${ZIP}" "${NAME}" )

echo "Created ${ZIP}"
unzip -l "${ZIP}" | head -25
