#!/usr/bin/env bash

set -eo pipefail

die() {
  echo "::error::${1}"
  exit 1
}

# NOTE: This file is meant to be sourced, not executed as a script.
if [[ "${0}" == "${BASH_SOURCE[0]}" ]]; then
  die "Internal error: setup harness was executed instead of being sourced?"
fi

# Load the virtual environment, if there is one.
source "${GITHUB_ACTION_PATH}/setup/venv.bash"

# Check the Python version, making sure it's new enough (3.7+)
# The installation step immediately below will technically catch this,
# but doing it explicitly gives us the opportunity to produce a better
# error message.
vers=$(python -V | cut -d ' ' -f2)
maj_vers=$(cut -d '.' -f1 <<< "${vers}")
min_vers=$(cut -d '.' -f2 <<< "${vers}")

[[ "${maj_vers}" == "3" && "${min_vers}" -ge 7 ]] || die "Bad Python version: ${vers}"

python -m pip install --requirement "${GITHUB_ACTION_PATH}/requirements.txt"
