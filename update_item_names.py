import json
import os
import re

from utils.dev_paths import get_dev_path


def update_item_names():
    base_dir = get_dev_path("replace_items_dir")
    if not base_dir:
        raise RuntimeError("请在 config/dev_paths.local.json 中配置 replace_items_dir")

    path_itemdata = os.path.join(base_dir, "ItemData.txt")
    path_item_names = os.path.join(base_dir, "pokemon_item_name.json")

    with open(path_itemdata, "r", encoding="utf-8") as f:
        item_data_lines = f.readlines()

    with open(path_item_names, "r", encoding="utf-8") as f:
        item_names = json.load(f)
    
    # 解析ItemData.txt，提取带有括号的物品名称
    bracket_items = {}
    for line in item_data_lines[1:]:  # 跳过标题行
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            item_id = parts[0]
            item_name = parts[1]
            # 检查是否包含括号
            if '(' in item_name and ')' in item_name:
                bracket_items[item_id] = item_name
    
    # 更新pokemon_item_name.json
    updated_count = 0
    for item_id, new_name in bracket_items.items():
        if item_id in item_names:
            old_name = item_names[item_id]
            # 只有当旧名称不包含括号时才更新
            if '(' not in old_name and ')' not in old_name:
                item_names[item_id] = new_name
                print(f"更新物品ID {item_id}: '{old_name}' -> '{new_name}'")
                updated_count += 1
    
    with open(path_item_names, "w", encoding="utf-8") as f:
        json.dump(item_names, f, ensure_ascii=False, indent=2)
    
    print(f"更新完成，共更新了 {updated_count} 个物品名称")

if __name__ == '__main__':
    update_item_names()
