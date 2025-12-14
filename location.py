import json
import os

from utils.dev_paths import get_dev_path


def create_location_mapping():
    """创建地点ID到地名的映射表"""
    base_dir = get_dev_path("replace_items_dir")
    if not base_dir:
        raise RuntimeError("请在 config/dev_paths.local.json 中配置 replace_items_dir")

    path_00000 = os.path.join(base_dir, "text_swsh_00000_zh-Hans.txt")
    path_30000 = os.path.join(base_dir, "text_swsh_30000_zh-Hans.txt")

    with open(path_00000, "r", encoding="utf-8") as f:
        locations_00000 = [line.strip() for line in f.readlines() if line.strip()]

    with open(path_30000, "r", encoding="utf-8") as f:
        locations_30000 = [line.strip() for line in f.readlines() if line.strip()]
    
    # 从Locations8.txt中提取ID列表
    # Met0范围: 00000系列
    met0_ids = [
        2, 4, 6, 8,
        12, 14, 16, 18,
        20, 22, 24, 28,
        30, 32, 34, 36,
        40, 44, 46, 48,
        52, 54, 56, 58,
        60, 64, 66, 68,
        70, 72, 76, 78,
        80, 84, 86, 88,
        90, 92, 94, 96, 98,
        102, 104, 106, 108,
        110, 112, 114, 116, 118,
        120, 122, 124, 126, 128,
        130, 132, 134, 136, 138,
        140, 142, 144, 146, 148,
        150, 152, 154, 156, 158,
        160, 162, 164, 166, 168,
        170, 172, 174, 176, 178,
        180, 182, 184, 186, 188,
        190, 192, 194, 196, 198,
        200, 202, 204, 206, 208,
        210, 212, 214, 216, 218,
        220, 222, 224, 226, 228,
        230, 232, 234, 236, 238,
        240, 242, 244, 246
    ]
    
    # Met3范围: 30000系列
    met3_ids = [
        30001, 30003, 30004, 30005, 30006, 30007, 30008, 30009,
        30010, 30011, 30012, 30013, 30014, 30015, 30016, 30017, 30018
    ]
    
    # Met4范围: 40000系列 (从文本推断)
    met4_ids = [
        40001, 40002, 40003, 40005, 40006, 40007, 40008, 40009,
        40010, 40011, 40012, 40013, 40014, 40016, 40017, 40018, 40019,
        40020, 40021, 40022, 40024, 40025, 40026, 40027, 40028, 40029,
        40030, 40032, 40033, 40034, 40035, 40036, 40037, 40038, 40039,
        40040, 40041, 40042, 40043, 40044, 40045, 40047, 40048, 40049,
        40050, 40051, 40052, 40053, 40055, 40056, 40057, 40058, 40059,
        40060, 40061, 40063, 40064, 40065, 40066, 40067, 40068, 40069,
        40070, 40071, 40072, 40074, 40075, 40076, 40077, 40078, 40079,
        40080, 40081, 40082, 40083, 40084, 40085, 40086
    ]
    
    # 创建映射表
    location_mapping = {}
    
    # 处理00000系列 (注意索引需要-1，因为列表从0开始但地点ID从1开始)
    # 但需要考虑空行占位符"－－－－－－－－－－"的影响
    valid_index = 0
    for location_id in met0_ids:
        # 跳过占位符行
        while valid_index < len(locations_00000) and locations_00000[valid_index] == "":
            valid_index += 1
        
        if valid_index < len(locations_00000):
            location_name = locations_00000[valid_index]
            # 跳过占位符
            if location_name != "－－－－－－－－－－":
                location_mapping[location_id] = location_name
            valid_index += 1
    
    # 处理30000系列
    for i, location_id in enumerate(met3_ids):
        if i < len(locations_30000):
            location_name = locations_30000[i]
            if location_name != "－－－－－－－－－－":  # 跳过占位符
                location_mapping[location_id] = location_name
    
    # 输出映射表
    print("地点ID到地名映射表:")
    print("=" * 50)
    for location_id in sorted(location_mapping.keys()):
        print(f"{location_id}: {location_mapping[location_id]}")
    
    locations = {"location_map": location_mapping}

    output_dir = base_dir
    output_path = os.path.join(output_dir, "pokemon_location.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)
    
    print(f"\n映射表已保存到 pokemon_location.json，共 {len(location_mapping)} 个地点")
    
    return location_mapping

if __name__ == "__main__":
    mapping = create_location_mapping()
