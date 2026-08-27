"""Application configuration management with JSON persistence."""

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "api": {
        "screenscraper": {
            "username": "",
            "password": "",
            "devid": "",
            "devpassword": "",
        },
        "thegamesdb": {
            "api_key": "",
        },
    },
    "rendering": {
        "angle": 30.0,
        "output_width": 512,
        "background": "transparent",
        "reflection": True,
        "shadow": True,
        "texture": True,
        "supersample": 2,
    },
    "ui": {
        "last_platform": "PS2",
        "last_case_type": "DVD Case",
        "last_image_directory": "",
        "window_geometry": None,
        "recent_files": [],
        "theme": "Midnight Blue",
    },
}


class Config:
    """JSON-based application configuration."""

    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            config_dir = Path.home() / ".config" / "slipcase"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_dir.chmod(0o700)
            self._path = config_dir / "config.json"
        else:
            self._path = Path(config_path)

        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from disk, merging with defaults."""
        self._data = _deep_copy(DEFAULT_CONFIG)
        if self._path.exists():
            try:
                with open(self._path) as f:
                    saved = json.load(f)
                _deep_merge(self._data, saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        """Save current configuration to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)
        self._path.chmod(0o600)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested config value. e.g. config.get('api', 'screenscraper', 'username')."""
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, *keys_and_value: Any) -> None:
        """Set a nested config value. Last arg is the value.
        e.g. config.set('api', 'screenscraper', 'username', 'myuser')
        """
        if len(keys_and_value) < 2:
            raise ValueError("Need at least one key and a value")

        keys = keys_and_value[:-1]
        value = keys_and_value[-1]

        current = self._data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value


def _deep_copy(d: dict) -> dict:
    """Deep copy a nested dict."""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy(v)
        elif isinstance(v, list):
            result[k] = list(v)
        else:
            result[k] = v
    return result


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base recursively, modifying base in place."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
