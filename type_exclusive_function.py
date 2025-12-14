import random
import json
import os
from typing import List, Dict
from core.battle_types import calculate_weaknesses

try:
    from file_manager import safe_load_file
except ImportError:
    pass

# 安全地加载配置文件
def load_config():
    try:
        config = safe_load_file("item_category_rules.json", "json")
        if config:
            return config
    except:
        pass
    
    # 如果找不到配置文件，返回默认配置
    return {
        "item_categories": {
            "type": {
                "attack": {},
                "defend": {},
                "special": {}
            }
        }
    }

# 安全地加载宝可梦类型数据
def load_pokemon_types_data():
    try:
        data = safe_load_file("pokemon_types_final.json", "json")
        if data:
            return data
    except:
        pass
    
    # 如果找不到数据文件，返回空字典
    return {}

# 重新加载配置文件的函数
def reload_config():
    global config, item_categories, type_category
    config = load_config()
    item_categories = config["item_categories"]
    type_category = item_categories["type"]

# 重新加载宝可梦类型数据的函数
def reload_pokemon_types_data():
    global pokemon_types_data
    pokemon_types_data = load_pokemon_types_data()

config = load_config()
pokemon_types_data = load_pokemon_types_data()

item_categories = config["item_categories"]
type_category = item_categories["type"]

def get_pokemon_types(pokemon_id: int) -> List[str]:
    pokemon_id_str = str(pokemon_id)
    if pokemon_id_str in pokemon_types_data:
        return pokemon_types_data[pokemon_id_str]
    else:
        print(f"无法获取宝可梦ID为{pokemon_id}的属性")
        return []

def select_item(pokemon_id: int) -> int:
    categories = list(item_categories.values())
    weights = [cat["weight"] for cat in categories]
    selected_category = random.choices(categories, weights=weights, k=1)[0]
    if selected_category["name"] == "属性：空道具":
        return select_attribute_item(pokemon_id)
    return random.choice(selected_category["items"])

def get_item_category(item_id: int) -> str:
    for category_name, category_data in item_categories.items():
        if category_name == "type":
            if "attack" in category_data:
                for attr, items in category_data["attack"].items():
                    if item_id in items:
                        return "属性道具-攻击"
            if "defend" in category_data:
                for attr, items in category_data["defend"].items():
                    if item_id in items:
                        return "属性道具-防御"
            if "special" in category_data:
                for key, items in category_data["special"].items():
                    if item_id in items:
                        return "属性道具-特殊"
            if "items" in category_data and item_id in category_data["items"]:
                return "属性道具"
        else:
            if "items" in category_data and item_id in category_data["items"]:
                return category_data["name"]
    return "未知类别"

def select_attribute_item(pokemon_id: int) -> int:
    """根据宝可梦选择道具"""
    pokemon_types = get_pokemon_types(pokemon_id)

    if not pokemon_types:
        all_type_items = []
        for attr_items in type_category["attack"].values():
            all_type_items.extend(attr_items)
        for attr_items in type_category["defend"].values():
            all_type_items.extend(attr_items)
        for attr_items in type_category["special"].values():
            all_type_items.extend(attr_items)
        print("未找到宝可梦，随机选择type道具")
        return random.choice(all_type_items)
    
    attack_weight = 3.0
    defend_weight = 2.0
    sludge_weight = 0.01

    if "poison" in pokemon_types:
        sludge_weight += 2.0
    
    weaknesses = calculate_weaknesses(pokemon_types)

    double_weak = [attr for attr, multiplier in weaknesses.items() if multiplier == 2.0]
    quadruple_weak = [attr for attr, multiplier in weaknesses.items() if multiplier == 4.0]

    item_weights = {}
    
    category_weights = [attack_weight, defend_weight, sludge_weight]

    rand_val = random.uniform(0, sum(category_weights))

    if rand_val < attack_weight:
        for attr, items in type_category["attack"].items():
            for item_id in items:
                base_weight = 0.01
                if attr in pokemon_types:
                    base_weight += 2.0 / len(pokemon_types)

                    if attr == "normal":
                        if item_id == 564:
                            base_weight *= 0.8
                        elif item_id == 251:
                            base_weight *= 1.2
                
                item_weights[item_id] = base_weight
        attack_items = []
        for items in type_category["attack"].values():
            attack_items.extend(items)
        items = attack_items
        
    elif rand_val < attack_weight + defend_weight:
        for attr, items in type_category["defend"].items():
            for item_id in items:
                base_weight = 0.01
                if attr in double_weak:
                    factor = 2.0 / len(double_weak)
                    base_weight += factor if double_weak else 0

                    if attr == "ice":
                        if item_id == 649:  # 雪球(冰)
                            base_weight += 0.02
                    elif attr == "electric":
                        if item_id == 546:  # 充电电池(电)
                            base_weight += 0.02
                    elif attr == "water":
                        if item_id == 545:  # 球根(水)
                            base_weight /= 2
                            base_weight += 0.01
                        if item_id == 648:  # 光苔(水)
                            base_weight /= 2
                            base_weight += 0.01

                if attr in quadruple_weak:
                    base_weight += 2.0 / len(quadruple_weak) if quadruple_weak else 0

                item_weights[item_id] = base_weight
        defend_items = []
        for items in type_category["defend"].values():
            defend_items.extend(items)
        items = defend_items
    else:
        items = type_category["special"]["black_sludge"]
    
    weights = [item_weights.get(item_id, 0.01) for item_id in items]

    selected_item = random.choices(items, weights=weights, k=1)[0]

    return selected_item



if __name__ == "__main__":
    pokemon_id = 1
    types = get_pokemon_types(pokemon_id)
    weaknesses = calculate_weaknesses(types)
    print(f"宝可梦ID为{pokemon_id}的弱点属性为：{weaknesses}")
