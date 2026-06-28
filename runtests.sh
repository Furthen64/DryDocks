#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv."
  echo "Run: uv venv .venv --python 3.12"
  echo "Then: source .venv/bin/activate"
  exit 1
fi

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "No active virtual environment."
  echo "Activate it first: source .venv/bin/activate"
  exit 1
fi

python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "${python_version}" != "3.12" ]]; then
  echo "Python 3.12 is required, found ${python_version}."
  echo "Recreate venv with: uv venv .venv --python 3.12"
  exit 1
fi

if [[ ! -f "${PWD}/drydocks.json" ]]; then
  echo "Missing ${PWD}/drydocks.json."
  echo "Run ./setup.sh first."
  exit 1
fi

if ! python3 -c "import pytest" >/dev/null 2>&1; then
  echo "pytest is not installed in the active environment."
  echo "Install it with: uv pip install pytest"
  exit 1
fi

python3 -m pytest tests "$@"
echo "Latest report: ${PWD}/reports/latest-report.txt"
