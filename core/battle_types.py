from typing import Dict, List

from core.static_data import type_defense_effectiveness, type_code_map


def calculate_weaknesses(types: List[str]) -> Dict[str, float]:
    weaknesses: Dict[str, float] = {t: 1.0 for t in type_defense_effectiveness.keys()}
    for pokemon_type in types:
        if pokemon_type in type_defense_effectiveness:
            row = type_defense_effectiveness[pokemon_type]
            for i, value in enumerate(row):
                attr = type_code_map.get(i)
                if attr is not None:
                    weaknesses[attr] *= value
    return weaknesses

