"""Configuration helpers for DryDocks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(config_path: str | Path = "drydocks.json") -> dict[str, Any]:
    """Load the user-provided DryDocks config file."""
    path = Path(config_path)
    config = json.loads(path.read_text(encoding="utf-8"))

    for key in ("base_url", "model"):
        if not config.get(key):
            raise RuntimeError(f"Missing required config field: {key}")

    if "api_key" not in config:
        config["api_key"] = ""

    return config
