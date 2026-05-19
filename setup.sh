#!/usr/bin/env bash
set -euo pipefail

output_file="${PWD}/drydocks.json"

prompt_required() {
  local label="$1"
  local value=""
  while true; do
    read -r -p "${label}: " value
    if [[ -n "${value}" ]]; then
      printf '%s' "${value}"
      return 0
    fi
    echo "${label} cannot be empty."
  done
}

echo "DryDocks setup"
echo "This will create: ${output_file}"

endpoint="$(prompt_required "OpenAI-compatible base URL (example: http://localhost:11434/v1)")"
model="$(prompt_required "Model name (example: llama3.1:8b)")"
read -r -p "API key (optional, press enter to leave blank): " api_key

python3 - <<'PY' "${output_file}" "${endpoint}" "${model}" "${api_key}"
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
base_url = sys.argv[2]
model = sys.argv[3]
api_key = sys.argv[4]

config = {
    "base_url": base_url,
    "model": model,
    "api_key": api_key,
}

output_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY

echo "Wrote configuration to ${output_file}"
