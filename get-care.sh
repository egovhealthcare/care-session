#!/usr/bin/env bash
# Clone the CARE workshop repo (with CARE sources) and start it.
#
#   curl -fsSL https://raw.githubusercontent.com/egovhealthcare/care-session/main/get-care.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/egovhealthcare/care-session/main/get-care.sh | bash -s -- --demo-data
#
# Clones into ./care-session (override with CARE_DIR=/path). If that directory
# already exists it is updated instead. Any arguments go to run-care.sh.
set -euo pipefail

REPO_URL="${CARE_REPO_URL:-https://github.com/egovhealthcare/care-session.git}"
CARE_DIR="${CARE_DIR:-$PWD/care-session}"

command -v git >/dev/null || { echo "ERROR: git is not installed" >&2; exit 1; }

if [ -d "$CARE_DIR/.git" ]; then
  echo "==> Updating existing checkout in $CARE_DIR"
  git -C "$CARE_DIR" pull --ff-only
  git -C "$CARE_DIR" submodule update --init --depth 1
else
  echo "==> Cloning $REPO_URL into $CARE_DIR"
  git clone --recurse-submodules --shallow-submodules "$REPO_URL" "$CARE_DIR"
fi

cd "$CARE_DIR"
exec ./run-care.sh "$@"
