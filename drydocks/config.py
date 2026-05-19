"""
Configuration management for DryDocks test suite.
Handles loading/saving config from ~/.config/drydocks/drydocks.json
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import urllib.request
import urllib.error


class ConfigManager:
    """Manages DryDocks configuration file."""

    CONFIG_DIR = Path.home() / ".config" / "drydocks"
    CONFIG_FILE = CONFIG_DIR / "drydocks.json"

    DEFAULT_CONFIG = {
        "version": "1.0",
        "endpoint": "http://127.0.0.1:8080/v1/messages",
        "api_key": "dummy",
        "model": "qwen",
        "timeout_seconds": 120,
        "max_retries": 2,
        "retry_delay_seconds": 1,
    }

    def __init__(self):
        """Initialize ConfigManager."""
        self.config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load config from file or use defaults."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                raise RuntimeError(
                    f"Failed to load config from {self.CONFIG_FILE}: {e}"
                )
        else:
            self.config = self.DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save current config to file."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        os.chmod(self.CONFIG_FILE, 0o600)  # Restrict permissions (API key inside)

    def validate(self) -> tuple[bool, str]:
        """
        Validate config and test connection to endpoint.
        Returns (is_valid, message).
        """
        required_keys = ["endpoint", "api_key", "model", "timeout_seconds"]
        missing = [k for k in required_keys if k not in self.config]
        if missing:
            return False, f"Missing config keys: {', '.join(missing)}"

        endpoint = self.config.get("endpoint", "").strip()
        if not endpoint:
            return False, "Endpoint URL is empty"

        if not endpoint.startswith(("http://", "https://")):
            return False, "Endpoint must start with http:// or https://"

        # Test connectivity
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps({
                    "model": self.config["model"],
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "test"}]
                }).encode("utf-8"),
                method="POST",
                headers={
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01",
                    "x-api-key": self.config["api_key"],
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(
                req, timeout=self.config.get("timeout_seconds", 10)
            ) as response:
                response.read()
            return True, "Connection successful"
        except urllib.error.URLError as e:
            return False, f"Failed to connect to endpoint: {e.reason}"
        except Exception as e:
            return False, f"Connection test failed: {e}"

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value."""
        self.config[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return config as dict (without sensitive keys for display)."""
        return self.config.copy()

    def to_display_dict(self) -> Dict[str, Any]:
        """Return config for display (mask API key)."""
        display = self.config.copy()
        if "api_key" in display:
            key = display["api_key"]
            if len(key) > 8:
                display["api_key"] = key[:4] + "***" + key[-4:]
            else:
                display["api_key"] = "***"
        return display

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.CONFIG_FILE.exists()

    def delete(self) -> None:
        """Delete config file."""
        if self.CONFIG_FILE.exists():
            self.CONFIG_FILE.unlink()
        self.config = self.DEFAULT_CONFIG.copy()
