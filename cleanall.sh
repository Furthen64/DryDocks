#!/usr/bin/env bash
set -euo pipefail

targets=(
  "agent_test_out"
  "calculator_test_out"
  "repo_edit_test_out"
  "repo_debug_test_out"
  "reports"
)

echo "DryDocks cleanup"

for target in "${targets[@]}"; do
  if [[ -e "${target}" ]]; then
    rm -rf "${target}"
    echo "Removed ${PWD}/${target}"
  else
    echo "Missing ${PWD}/${target}, skipping"
  fi
done
