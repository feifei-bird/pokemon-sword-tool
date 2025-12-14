import json
import os
from typing import Any, Dict

from file_manager import get_base_dir


_FILENAME = "dev_paths.local.json"
_settings: Dict[str, Any] = {}
_loaded = False


def _config_dir() -> str:
    return os.path.join(get_base_dir(), "config")


def _settings_path() -> str:
    return os.path.join(_config_dir(), _FILENAME)


def _ensure_loaded() -> None:
    global _loaded, _settings
    if _loaded:
        return
    path = _settings_path()
    data: Dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    data = obj
        except Exception:
            data = {}
    _settings = data
    _loaded = True


def get_dev_path(key: str, default: str = "") -> str:
    _ensure_loaded()
    value = _settings.get(key, default)
    return str(value or "")

