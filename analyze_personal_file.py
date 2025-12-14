import struct
import json

from utils.dev_paths import get_dev_path

original_file = get_dev_path("origin_personal_total_dir")
modified_file = get_dev_path("modified_personal_total_dir")

record_size = 0xB0  # 176字节
ABILITY_OFFSET_1 = 0x18  # 第一个特性的偏移量
ABILITY_OFFSET_2 = 0x1A  # 第二个特性的偏移量
ABILITY_OFFSET_H = 0x1C  # 隐藏特性的偏移量

# 更新后的属性映射表
type_map = {
    0: "normal",      # 一般
    1: "fighting",    # 格斗
    2: "flying",      # 飞行
    3: "poison",      # 毒
    4: "ground",      # 地面
    5: "rock",        # 岩石
    6: "bug",         # 虫
    7: "ghost",       # 幽灵
    8: "steel",       # 钢
    9: "fire",        # 火
    10: "water",      # 水
    11: "grass",      # 草
    12: "electric",   # 电
    13: "psychic",    # 超能力
    14: "ice",        # 冰
    15: "dragon",     # 龙
    16: "dark",       # 恶
    17: "fairy"       # 妖精
}

def extract_all_pokemon_types():
    """提取所有宝可梦的属性信息"""
    type_offset_1 = 6   # 第一个属性字段的偏移量
    type_offset_2 = 7   # 第二个属性字段的偏移量
    
    pokemon_types = {}
    
    with open(original_file, "rb") as f:
        data = f.read()
        
        num_records = len(data) // record_size
        
        for record_id in range(0, num_records):
            record_start = record_id * record_size
            
            if record_start + type_offset_2 >= len(data):
                continue
                
            type1 = data[record_start + type_offset_1]
            type2 = data[record_start + type_offset_2]
            
            type1_name = type_map.get(type1, f"unknown({type1})")
            type2_name = type_map.get(type2, f"unknown({type2})")
            
            # 如果第二个属性与第一个相同或者是0，则认为是单属性
            if type2 == type1 or type2 == 0:
                pokemon_types[record_id] = [type1_name]
            else:
                pokemon_types[record_id] = [type1_name, type2_name]
    
    return pokemon_types

def extract_all_pokemon_abilities():
    """提取所有宝可梦的特性信息"""
    abilities = {}
    
    with open(original_file, "rb") as f:
        data = f.read()
        
        num_records = len(data) // record_size
        
        for record_id in range(0, num_records):
            record_start = record_id * record_size
            
            if record_start + ABILITY_OFFSET_H + 2 >= len(data):
                continue
                
            # 读取三个特性
            ability1 = struct.unpack("<H", data[record_start + ABILITY_OFFSET_1:record_start + ABILITY_OFFSET_1 + 2])[0]
            ability2 = struct.unpack("<H", data[record_start + ABILITY_OFFSET_2:record_start + ABILITY_OFFSET_2 + 2])[0]
            ability_h = struct.unpack("<H", data[record_start + ABILITY_OFFSET_H:record_start + ABILITY_OFFSET_H + 2])[0]
            
            abilities[record_id] = {
                "ability1": ability1,
                "ability2": ability2,
                "ability_h": ability_h
            }
    
    return abilities

def load_ability_map():
    """加载特性ID到名称的映射表"""
    try:
        with open("pokemon_ability.json", "r", encoding="utf-8") as f:
            ability_data = json.load(f)
            return ability_data.get("ability_map", {})
    except FileNotFoundError:
        print("警告: 未找到 pokemon_ability.json 文件")
        return {}

def main():
    # 提取所有宝可梦的属性
    print("提取所有宝可梦的属性...")
    pokemon_types = extract_all_pokemon_types()
    
    # 保存到JSON文件
    with open("pokemon_types_final.json", "w", encoding="utf-8") as f:
        json.dump(pokemon_types, f, indent=2, ensure_ascii=False)
    
    print(f"提取完成! 共提取了 {len(pokemon_types)} 只宝可梦的属性信息")
    print("已保存到 pokemon_types_final.json")
    
    # 提取所有宝可梦的特性
    print("\n提取所有宝可梦的特性...")
    pokemon_abilities = extract_all_pokemon_abilities()
    
    # 保存宝可梦特性信息
    with open("pokemon_abilities_final.json", "w", encoding="utf-8") as f:
        json.dump(pokemon_abilities, f, indent=2, ensure_ascii=False)
    
    print("宝可梦特性信息已保存到 pokemon_abilities_final.json")
    

if __name__ == "__main__":
    main()
