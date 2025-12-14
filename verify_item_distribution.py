import json
import os
import struct
from collections import Counter, defaultdict
from type_exclusive_function import calculate_weaknesses, get_item_category

try:
    from file_manager import safe_load_file
except ImportError:
    safe_load_file = None

if safe_load_file is not None:
    config = safe_load_file("item_category_rules.json", "json") or {}
else:
    with open("item_category_rules.json", "r", encoding="utf-8") as f:
        config = json.load(f)

trainer_poke_dir = config["trainer_poke_dir"]
item_categories = config["item_categories"]
type_map = config.get("type_map", {})

if safe_load_file is not None:
    pokemon_types_data = safe_load_file("pokemon_types_final.json", "json") or {}
else:
    with open("pokemon_types_final.json", "r", encoding="utf-8") as f:
        pokemon_types_data = json.load(f)

item_id_to_name = {}
if safe_load_file is not None:
    item_lines = safe_load_file("ItemData.txt", "txt") or []
else:
    with open("ItemData.txt", "r", encoding="utf-8") as f:
        item_lines = f.readlines()

for line in item_lines:
    if line.startswith("Index\tItems"):
        continue
    parts = line.strip().split("\t")
    if len(parts) >= 2:
        try:
            item_id = int(parts[0])
            item_name = parts[1]
            item_id_to_name[item_id] = item_name
        except ValueError:
            continue

POKEMON_SIZE = 0x20
ITEM_OFFSET = 0x10
POKEMON_ID_OFFSET = 0x0C

def get_pokemon_types(pokemon_id):
    pokemon_id_str = str(pokemon_id)
    return pokemon_types_data.get(pokemon_id_str, [])

def analyze_trainer_files(sample_count=5):
    """分析训练家文件中的道具分布"""
    all_files = [f for f in os.listdir(trainer_poke_dir) 
                if f.startswith("trainer_poke_") and f.endswith(".bin")]
    
    # 随机选择一些文件进行分析
    import random
    sample_files = random.sample(all_files, min(sample_count, len(all_files)))
    
    results = {
        "total_pokemon": 0,
        "item_distribution": Counter(),
        "category_distribution": Counter(),
        "type_match_analysis": defaultdict(list),
        "pokemon_with_items": [],
        "category_weights": {
            "特殊道具": 0.1,
            "交叉道具": 9.9,
            "普通道具": 20,
            "不戳道具": 40,
            "属性道具": 30
        }
    }
    
    for file_name in sample_files:
        filepath = os.path.join(trainer_poke_dir, file_name)
        
        with open(filepath, "rb") as f:
            data = f.read()
        
        num_pokemon = len(data) // POKEMON_SIZE
        
        for i in range(num_pokemon):
            offset = i * POKEMON_SIZE
            item_offset = offset + ITEM_OFFSET
            pokemon_id_offset = offset + POKEMON_ID_OFFSET
            
            if item_offset + 2 > len(data) or pokemon_id_offset + 2 > len(data):
                continue
            
            # 读取宝可梦ID和道具ID
            pokemon_id = struct.unpack("<H", data[pokemon_id_offset:pokemon_id_offset+2])[0]
            item_id = struct.unpack("<H", data[item_offset:item_offset+2])[0]
            
            # 获取宝可梦属性和道具信息
            pokemon_types = get_pokemon_types(pokemon_id)
            item_name = item_id_to_name.get(item_id, f"未知道具({item_id})")
            item_category = get_item_category(item_id)
            
            # 记录结果
            results["total_pokemon"] += 1
            results["item_distribution"][item_id] += 1
            results["category_distribution"][item_category] += 1
            
            # 记录宝可梦和道具的详细信息
            pokemon_info = {
                "file": file_name,
                "pokemon_id": pokemon_id,
                "pokemon_types": pokemon_types,
                "item_id": item_id,
                "item_name": item_name,
                "item_category": item_category
            }
            results["pokemon_with_items"].append(pokemon_info)
            
            # 分析属性匹配情况
            if item_category.startswith("属性道具"):
                # 检查道具是否与宝可梦属性匹配
                is_match = False
                match_reason = ""
                
                if item_category == "属性道具-攻击":
                    # 攻击道具应该匹配宝可梦的属性
                    for attr, items in item_categories["type"]["attack"].items():
                        if item_id in items:
                            if attr in pokemon_types:
                                is_match = True
                                match_reason = f"攻击道具匹配宝可梦属性: {attr}"
                                break
                
                elif item_category == "属性道具-防御":
                    # 防御道具应该匹配宝可梦的弱点
                    weaknesses = calculate_weaknesses(pokemon_types)
                    double_weak = [attr for attr, multiplier in weaknesses.items() if multiplier == 2.0]
                    quad_weak = [attr for attr, multiplier in weaknesses.items() if multiplier == 4.0]
                    
                    for attr, items in item_categories["type"]["defend"].items():
                        if item_id in items:
                            if attr in double_weak or attr in quad_weak:
                                is_match = True
                                match_reason = f"防御道具匹配弱点属性: {attr}"
                                break
                
                elif item_category == "属性道具-特殊":
                    # 特殊道具（如黑色污泥）有特殊规则
                    if item_id in item_categories["type"]["special"]["black_sludge"]:
                        if "poison" in pokemon_types:
                            is_match = True
                            match_reason = "黑色污泥匹配毒属性"
                    
                    # 其他特殊道具的匹配规则
                    elif item_id in item_categories["type"]["special"].get("snowball", []):
                        weaknesses = calculate_weaknesses(pokemon_types)
                        if "ice" in weaknesses and weaknesses["ice"] >= 2.0:
                            is_match = True
                            match_reason = "雪球匹配冰弱点"
                    
                    elif item_id in item_categories["type"]["special"].get("battery", []):
                        weaknesses = calculate_weaknesses(pokemon_types)
                        if "electric" in weaknesses and weaknesses["electric"] >= 2.0:
                            is_match = True
                            match_reason = "充电电池匹配电弱点"
                    
                    elif item_id in item_categories["type"]["special"].get("root", []) or \
                         item_id in item_categories["type"]["special"].get("light_moss", []):
                        weaknesses = calculate_weaknesses(pokemon_types)
                        if "water" in weaknesses and weaknesses["water"] >= 2.0:
                            is_match = True
                            match_reason = "球根/光苔匹配水弱点"
                
                # 添加匹配原因到信息中
                pokemon_info["match_reason"] = match_reason if is_match else "不匹配"
                results["type_match_analysis"][is_match].append(pokemon_info)
    
    return results

def print_results(results):
    """打印分析结果"""
    print(f"分析完成！共检查了 {results['total_pokemon']} 只宝可梦")
    print("\n=== 道具分布 ===")
    for item_id, count in results["item_distribution"].most_common(20):
        item_name = item_id_to_name.get(item_id, f"未知道具({item_id})")
        print(f"{item_name}: {count} 次")
    
    print("\n=== 类别分布 ===")
    total = results['total_pokemon']
    category_counts = results["category_distribution"]
    
    # 合并所有属性道具类别
    type_items_count = 0
    for cat in list(category_counts.keys()):
        if cat.startswith("属性道具"):
            type_items_count += category_counts[cat]
            del category_counts[cat]
    
    category_counts["属性道具"] = type_items_count
    
    # 计算实际比例和期望比例
    expected_weights = results["category_weights"]
    total_weight = sum(expected_weights.values())
    
    print("类别\t\t实际数量\t实际比例\t期望比例")
    print("-" * 60)
    
    for category, count in category_counts.most_common():
        actual_percentage = count / total * 100
        expected_percentage = expected_weights.get(category, 0) / total_weight * 100
        print(f"{category:12}\t{count}\t\t{actual_percentage:.2f}%\t\t{expected_percentage:.2f}%")
    
    print("\n=== 属性道具匹配分析 ===")
    matched = len(results["type_match_analysis"].get(True, []))
    not_matched = len(results["type_match_analysis"].get(False, []))
    total_type_items = matched + not_matched
    
    if total_type_items > 0:
        match_rate = matched / total_type_items * 100
        print(f"属性道具匹配率: {match_rate:.2f}% ({matched}/{total_type_items})")
        
        # 打印一些匹配和不匹配的例子
        print("\n匹配的例子:")
        for example in results["type_match_analysis"].get(True, [])[:3]:
            print(f"  宝可梦{example['pokemon_id']}({example['pokemon_types']}) -> {example['item_name']}")
            print(f"    原因: {example['match_reason']}")
        
        print("\n不匹配的例子:")
        for example in results["type_match_analysis"].get(False, [])[:3]:
            print(f"  宝可梦{example['pokemon_id']}({example['pokemon_types']}) -> {example['item_name']}")
            print(f"    原因: {example.get('match_reason', '未知原因')}")
    else:
        print("未找到属性道具")
    
    # 保存详细结果到文件
    with open("item_distribution_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细结果已保存到 item_distribution_analysis.json")

if __name__ == "__main__":
    results = analyze_trainer_files(sample_count=20)  # 分析10个训练家文件
    print_results(results)
