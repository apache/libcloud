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

# If the user has explicitly specified a virtual environment, then we install
# `pip-audit` into it rather than into whatever environment the default
# `python -m pip install ...` invocation might happen to choose.
if [[ -n "${GHA_PIP_AUDIT_VIRTUAL_ENVIRONMENT}" ]] ; then
  if [[ -d "${GHA_PIP_AUDIT_VIRTUAL_ENVIRONMENT}" ]]; then
    source "${GHA_PIP_AUDIT_VIRTUAL_ENVIRONMENT}/bin/activate"
  else
    die "Fatal: virtual environment is not a directory"
  fi
fi
