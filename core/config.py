"""Application configuration management with JSON persistence."""

import json
import os
import tempfile
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
        # zlib level for PNG export. 6 is the default (see png_utils); 9 is
        # ~5% smaller and 2-4x slower.
        "compress_level": 6,
    },
    "ui": {
        "last_platform": "PS2",
        "last_case_type": "DVD Case",
        "last_image_directory": "",
        "window_geometry": None,
        "recent_files": [],
        "theme": "Midnight Blue",
        "auto_filename": False,
        "last_export_directory": "",
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
        # Set by load(); save() refuses while true. See load().
        self.load_failed = False
        self.load_error = ""
        self.load()

    def load(self) -> None:
        """Load configuration from disk, merging with defaults.

        Sets `load_failed` when an existing file could not be read or parsed.
        Callers MUST check it before saving: the in-memory state is defaults
        at that point, and writing it out would destroy the stored
        credentials the unreadable file still holds.
        """
        self._data = _deep_copy(DEFAULT_CONFIG)
        self.load_failed = False
        self.load_error = ""
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
        except (ValueError, OSError) as e:
            # ValueError covers the UnicodeDecodeError a non-UTF-8 file raises.
            self.load_failed = True
            self.load_error = str(e)
            return
        if not raw.strip():
            # An empty file holds nothing to lose, so this is not a failed
            # read -- saving over it is correct.
            return
        try:
            _deep_merge(self._data, json.loads(raw))
        except ValueError as e:
            self.load_failed = True
            self.load_error = str(e)

    def save(self) -> None:
        """Save current configuration to disk, atomically.

        Writes a sibling temp file created 0600, fsyncs it, then renames over
        the target -- POSIX rename(2) within one directory is atomic, so an
        interrupted save can never leave a truncated credential file. The mode
        is set at creation rather than after the write, so the password is
        never briefly world-readable.

        Raises OSError on failure; callers surface it to the user.
        """
        if self.load_failed:
            raise OSError(
                f"refusing to save: {self._path} could not be read "
                f"({self.load_error}), so saving now would overwrite it with "
                f"defaults and lose whatever it holds"
            )
        self._path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=".config-", suffix=".tmp"
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, self._path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

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
    result: dict = {}
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
