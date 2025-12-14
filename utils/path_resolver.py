import json
import os
from typing import Any, Dict

from file_manager import get_base_dir


_SETTINGS_FILENAME = "user_paths.local.json"
_EXAMPLE_FILENAME = "user_paths.example.json"
_settings: Dict[str, Any] = {}
_loaded = False


def _config_dir() -> str:
    return os.path.join(get_base_dir(), "config")


def _settings_path() -> str:
    return os.path.join(_config_dir(), _SETTINGS_FILENAME)


def _example_settings_path() -> str:
    return os.path.join(_config_dir(), _EXAMPLE_FILENAME)


def _ensure_loaded() -> None:
    global _loaded, _settings
    if _loaded:
        return
    path_local = _settings_path()
    path_example = _example_settings_path()
    data = {}
    if os.path.isfile(path_local):
        try:
            with open(path_local, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    data = obj
        except Exception:
            data = {}
    elif os.path.isfile(path_example):
        try:
            with open(path_example, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    data = obj
        except Exception:
            data = {}
    _settings = data
    _loaded = True


def get_setting(key: str, default: Any = "") -> Any:
    _ensure_loaded()
    return _settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    _ensure_loaded()
    _settings[key] = value
    config_dir = _config_dir()
    os.makedirs(config_dir, exist_ok=True)
    path = _settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_settings, f, ensure_ascii=False, indent=4)


def migrate_legacy_paths() -> None:
    _ensure_loaded()
    cfg_dir = _config_dir()
    cfg_path = os.path.join(cfg_dir, "item_category_rules.json")
    if not os.path.isfile(cfg_path):
        return
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            return
    except Exception:
        return
    changed_cfg = False
    changed_settings = False
    for key in ("trainer_poke_dir", "personal_total_bin_path", "main_file_path", "disabled_blocks", "last_mode"):
        if key in cfg:
            if key not in _settings:
                _settings[key] = cfg[key]
                changed_settings = True
            cfg.pop(key, None)
            changed_cfg = True
    if changed_settings:
        os.makedirs(cfg_dir, exist_ok=True)
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(_settings, f, ensure_ascii=False, indent=4)
    if changed_cfg:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)


def get_trainer_poke_dir() -> str:
    value = get_setting("trainer_poke_dir", "")
    return str(value or "")


def get_personal_total_path() -> str:
    value = get_setting("personal_total_bin_path", "")
    return str(value or "")


def get_main_file_path() -> str:
    value = get_setting("main_file_path", "")
    return str(value or "")


def get_disabled_blocks():
    value = get_setting("disabled_blocks", [])
    return value if isinstance(value, list) else []


def get_last_mode() -> int:
    value = get_setting("last_mode", 0)
    try:
        return int(value)
    except Exception:
        return 0


def set_trainer_poke_dir(path: str) -> None:
    set_setting("trainer_poke_dir", path)


def set_personal_total_path(path: str) -> None:
    set_setting("personal_total_bin_path", path)


def set_main_file_path(path: str) -> None:
    set_setting("main_file_path", path)


def set_disabled_blocks(blocks) -> None:
    set_setting("disabled_blocks", list(blocks))


def set_last_mode(mode: int) -> None:
    set_setting("last_mode", int(mode))
