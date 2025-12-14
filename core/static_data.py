from typing import Any, Dict, List, Tuple

from file_manager import safe_load_file


def _load_static_mappings() -> Dict[str, Any]:
    data = safe_load_file("static_mappings.json")
    if isinstance(data, dict):
        return data
    return {}


_raw = _load_static_mappings()

type_map: Dict[str, str] = _raw.get("type_map", {})

_raw_type_code = _raw.get("type_code_map", {})
type_code_map: Dict[int, str] = {}
for k, v in _raw_type_code.items():
    try:
        type_code_map[int(k)] = v
    except Exception:
        continue

_raw_nature = _raw.get("nature_map", {})
nature_map: Dict[int, str] = {}
for k, v in _raw_nature.items():
    try:
        nature_map[int(k)] = v
    except Exception:
        continue

nature_effect_map: Dict[str, Tuple[str, str]] = {}
for name, pair in _raw.get("nature_effect_map", {}).items():
    if isinstance(pair, list) and len(pair) == 2:
        nature_effect_map[name] = (str(pair[0]), str(pair[1]))

type_attack_effectiveness: Dict[str, List[float]] = _raw.get("type_attack_effectiveness", {})
type_effectiveness_map: Dict[str, List[float]] = _raw.get("type_effectiveness_map", {})
type_defense_effectiveness: Dict[str, List[float]] = _raw.get("type_defense_effectiveness", {})

v_names: List[str] = _raw.get("v_names", ["体力", "攻击", "特攻", "防御", "特防", "速度"])

