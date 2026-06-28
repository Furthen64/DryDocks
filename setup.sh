#!/usr/bin/env bash
set -euo pipefail

output_file="${PWD}/drydocks.json"
default_endpoint="http://localhost:8080/v1"

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

prompt_with_default() {
  local label="$1"
  local default_value="$2"
  local value=""
  read -r -p "${label} [${default_value}]: " value
  if [[ -n "${value}" ]]; then
    printf '%s' "${value}"
  else
    printf '%s' "${default_value}"
  fi
}

probe_models() {
  local base_url="$1"
  local api_key="$2"

  python3 - <<'PY' "${base_url}" "${api_key}"
import json
import sys
import urllib.error
import urllib.request

base_url = sys.argv[1].rstrip("/")
api_key = sys.argv[2]
models_url = f"{base_url}/models"

request = urllib.request.Request(models_url)
request.add_header("Accept", "application/json")
if api_key:
    request.add_header("Authorization", f"Bearer {api_key}")

try:
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.load(response)
except urllib.error.HTTPError as exc:
    print(f"Model probe failed: HTTP {exc.code} from {models_url}")
    sys.exit(0)
except urllib.error.URLError as exc:
    print(f"Model probe failed: could not reach {models_url} ({exc.reason})")
    sys.exit(0)
except Exception as exc:
    print(f"Model probe failed: {exc}")
    sys.exit(0)

items = payload.get("data", [])
if not isinstance(items, list) or not items:
    print(f"Model probe succeeded, but {models_url} did not return any models.")
    sys.exit(0)

def aliases_for(model):
    alias_values = []
    for key in ("aliases", "alias", "names", "name"):
        value = model.get(key)
        if isinstance(value, list):
            alias_values.extend(str(item) for item in value if item)
        elif isinstance(value, str) and value:
            alias_values.append(value)

    for key in ("id", "root", "parent"):
        value = model.get(key)
        if isinstance(value, str) and value:
            alias_values.append(value)

    seen = set()
    result = []
    for value in alias_values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

primary_ids = []
print("Available models:")
for index, model in enumerate(items, start=1):
    if not isinstance(model, dict):
        continue

    aliases = aliases_for(model)
    primary = model.get("id")
    if isinstance(primary, str) and primary:
        primary_ids.append(primary)
    elif aliases:
        primary_ids.append(aliases[0])

    if aliases:
        print(f"  {index}. " + " | ".join(aliases))
    else:
        print(f"  {index}. <unnamed model entry>")

if len(primary_ids) == 1:
    print(f"DEFAULT_MODEL={primary_ids[0]}")
PY
}

echo "DryDocks setup"
echo "This will create: ${output_file}"
echo "Default target: llama.cpp server at ${default_endpoint}"

endpoint="$(prompt_with_default "Base URL" "${default_endpoint}")"
read -r -p "API key (optional, llama.cpp usually leaves this blank): " api_key

model_probe_output="$(probe_models "${endpoint}" "${api_key}")"
if [[ -n "${model_probe_output}" ]]; then
  printf '%s\n' "${model_probe_output}" | sed '/^DEFAULT_MODEL=/d'
fi

discovered_default_model="$(printf '%s\n' "${model_probe_output}" | sed -n 's/^DEFAULT_MODEL=//p' | head -n 1)"

if [[ -n "${discovered_default_model}" ]]; then
  model="$(prompt_with_default "Model name" "${discovered_default_model}")"
else
  model="$(prompt_required "Model name (required by the API request)")"
fi

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
echo "Next step: activate your environment and run ./runtests.sh"
