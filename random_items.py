import json
import random
import os
import struct
from type_exclusive_function import select_item, select_attribute_item

try:
    from file_manager import safe_load_file
except ImportError:
    safe_load_file = None

if safe_load_file is not None:
    rules = safe_load_file("item_category_rules.json", "json") or {}
else:
    with open("item_category_rules.json", "r", encoding="utf-8") as f:
        rules = json.load(f)

valid_items = rules["valid_items"]
skip_items = rules["skip_items"]
use_random = rules["use_random"]
replace_all = rules["replace_all"]
trainer_poke_dir = rules["trainer_poke_dir"]
item_categories = rules["item_categories"]
type_map = rules.get("type_map", {})

if safe_load_file is not None:
    pokemon_types = safe_load_file("pokemon_types_final.json", "json") or {}
else:
    with open("pokemon_types_final.json", "r", encoding="utf-8") as f:
        pokemon_types = json.load(f)

# constants -> pokemon data structure
POKEMON_SIZE = 0x20
ITEM_OFFSET = 0x10
POKEMON_ID_OFFSET = 0x0C

reverse_type_map = {v: k for k, v in type_map.items()}

def main():
    # counters
    total_pokemon = 0
    replaced_count = 0
    for file in os.listdir(trainer_poke_dir):
        if not file.startswith("trainer_poke_") or not file.endswith(".bin"):
            continue

        filepath = os.path.join(trainer_poke_dir, file)

        with open(filepath, "rb") as f:
            data = bytearray(f.read())
        
        num_pokemon = len(data) // POKEMON_SIZE

        for i in range(num_pokemon):
            total_pokemon += 1
            offset = i * POKEMON_SIZE
            item_offset = offset + ITEM_OFFSET
            pokemon_id_offset = offset + POKEMON_ID_OFFSET

            if offset + 2 > len(data): continue

            if not replace_all:
                item_id = struct.unpack("<H", data[offset:offset+2])[0]

                if item_id in valid_items or item_id in skip_items:
                    continue

                if use_random and valid_items:
                    new_item = random.choice(valid_items)
                else:
                    new_item = 234
                
                data[offset:offset+2] = struct.pack("<H", new_item)
                replaced_count += 1
            else:
                pokemon_id = struct.unpack("<H", data[pokemon_id_offset:pokemon_id_offset+2])[0]
                new_item = select_item(pokemon_id)
                data[item_offset:item_offset+2] = struct.pack("<H", new_item)
                replaced_count += 1
        
        with open(filepath, "wb") as f:
            f.write(data)

    print(f"\n处理完成！")
    print(f"检查宝可梦: {total_pokemon} 只")
    print(f"替换道具: {replaced_count} 个")
    if not replace_all:
        print(f"有效道具列表: {valid_items[:10]}{'...' if len(valid_items) > 10 else ''} (共 {len(valid_items)} 种道具)")
        print(f"跳过道具ID: {skip_items}")

if __name__ == "__main__":
    main()
