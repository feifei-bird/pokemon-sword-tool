import struct
import os
import re
import json

from core.static_data import type_map, nature_map, nature_effect_map, v_names
from utils.dev_paths import get_dev_path
from file_manager import safe_load_file

trainer_poke_dir = get_dev_path("modified_trainer_poke_dir")
if not trainer_poke_dir:
    raise RuntimeError("请在 config/dev_paths.local.json 中配置 modified_trainer_poke_dir")
POKEMON_SIZE = 0x20
ITEM_OFFSET = 0x10
POKEMON_ID_OFFSET = 0x0C
LEVEL_OFFSET = 0x0A
NATURE_OFFSET = 0x01
IV_OFFSET = 0x1C
EV_OFFSET = 0x02
ABILITY_OFFSET = 0x00
MOVE1_OFFSET = 0x12
MOVE2_OFFSET = 0x14
MOVE3_OFFSET = 0x16
MOVE4_OFFSET = 0x18

pokemon_types_data = safe_load_file("pokemon_types_final.json", "json") or {}

item_id_to_name = {}
item_lines = safe_load_file("ItemData.txt", "txt") or []
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

pokemon_name_map = safe_load_file("pokemon_internal_id_name.json", "json") or {}

pokemon_abilities_data = safe_load_file("pokemon_abilities_final.json", "json") or {}

ability_data = safe_load_file("pokemon_ability.json", "json") or {}
ability_map = ability_data.get("ability_map", {})

move_data = safe_load_file("pokemon_move.json", "json") or {}
move_map = move_data.get("move_map", {})

def get_pokemon_types(pokemon_id):
    """根据宝可梦ID获取其属性"""
    pokemon_id_str = str(pokemon_id)
    return pokemon_types_data.get(pokemon_id_str, [])

def get_pokemon_name(pokemon_id):
    """根据宝可梦ID获取其名称（使用第八世代内部编号）"""
    pokemon_id_str = str(pokemon_id)
    return pokemon_name_map.get(pokemon_id_str, f"未知({pokemon_id})")

def get_nature_name(nature_value):
    """根据性格值获取性格名称"""
    return nature_map.get(nature_value, f"未知({nature_value})")

def parse_ivs(iv_data):
    """解析个体值数据"""
    # 将4字节数据转换为32位整数
    iv_value = struct.unpack("<I", iv_data)[0]
    
    # 提取各个个体值
    ivs = []
    for i in range(6):
        # 每5位表示一个个体值
        iv = (iv_value >> (5 * i)) & 0x1F
        ivs.append(iv)
    
    return ivs

def parse_evs(ev_data):
    """解析努力值数据"""
    # 直接读取6个字节作为努力值
    evs = list(ev_data)
    return evs

def get_ability_name(ability_id):
    """根据特性ID获取特性名称"""
    if ability_id == 0:
        return "无"
    key = str(ability_id)
    return ability_map.get(key, f"未知特性({ability_id})")

def get_pokemon_abilities(pokemon_id):
    """根据宝可梦ID获取其所有特性"""
    pokemon_id_str = str(pokemon_id)
    if pokemon_id_str in pokemon_abilities_data:
        return pokemon_abilities_data[pokemon_id_str]
    return {"ability1": 0, "ability2": 0, "ability_h": 0}

def get_ability_display(pokemon_id, ability_value):
    """根据宝可梦ID和特性值获取特性显示名称"""
    abilities = get_pokemon_abilities(pokemon_id)
    
    # 获取特性ID
    ability_id = 0
    ability_type = ""
    
    if ability_value == 1:
        ability_id = abilities["ability1"]
        ability_type = "1"
    elif ability_value == 2:
        ability_id = abilities["ability2"]
        ability_type = "2"
    elif ability_value == 3:
        ability_id = abilities["ability_h"]
        ability_type = "H"
    else:
        return f"未知特性({ability_value})"
    
    # 获取特性名称
    ability_name = get_ability_name(ability_id)
    
    # 格式化显示
    return f"{ability_name} ( {ability_type} )"

def get_move_name(move_id):
    """根据技能ID获取技能名称"""
    if move_id == 0:
        return "无"
    key = str(move_id)
    return move_map.get(key, f"未知技能({move_id})")

def main(check16 = True, file_number = "019"):
    """主函数，查看训练家文件"""

    file_number = file_number.zfill(3)

    # 选择一个文件进行验证
    sample_file = os.path.join(trainer_poke_dir, "trainer_poke_" + file_number + ".bin")

    if not os.path.exists(sample_file):
        print(f"文件不存在: {sample_file}")
        return False

    with open(sample_file, "rb") as f:
        data = f.read()

    if check16:
        # 检查文件大小
        # file_size = len(data)
        # num_pokemon = file_size // POKEMON_SIZE
        # print(f"文件大小: {file_size} 字节")
        # print(f"预计宝可梦数量: {num_pokemon}")
        # print(f"实际宝可梦数量: {file_size / POKEMON_SIZE}")

        # 打印第一个宝可梦的数据结构
        print("\n第一个宝可梦数据 (十六进制):")
        for i in range(0, min(POKEMON_SIZE, len(data))):
            if i % 16 == 0:
                print(f"\nOffset 0x{i:02X}: ", end="")
            print(f"{data[i]:02X} ", end="")

        # # 检查道具位置
        # if ITEM_OFFSET < len(data):
        #     item_id = struct.unpack("<H", data[ITEM_OFFSET:ITEM_OFFSET+2])[0]
        #     print(f"\n\n道具ID (位置 0x{ITEM_OFFSET:02X}): {item_id}")
        
        # # 检查等级位置
        # if LEVEL_OFFSET < len(data):
        #     level = data[LEVEL_OFFSET]
        #     print(f"等级 (位置 0x{LEVEL_OFFSET:02X}): {level}")
        
        # # 检查性格位置
        # if NATURE_OFFSET < len(data):
        #     nature_value = data[NATURE_OFFSET]
        #     nature_name = get_nature_name(nature_value)
        #     print(f"性格 (位置 0x{NATURE_OFFSET:02X}): {nature_name} ({nature_value})")
        
        # # 检查努力值位置
        # if EV_OFFSET + 6 <= len(data):
        #     ev_data = data[EV_OFFSET:EV_OFFSET+6]
        #     print(f"努力值 (位置 0x{EV_OFFSET:02X}-0x{EV_OFFSET+5:02X}): {ev_data.hex(' ').upper()}")
            
        #     # 解析并显示努力值
        #     evs = parse_evs(ev_data)
        #     ev_str = ", ".join([f"{name}:{value}" for name, value in zip(v_names, evs)])
        #     print(f"解析努力值: {ev_str}")
        
        # # 检查个体值位置
        # if IV_OFFSET + 4 <= len(data):
        #     iv_data = data[IV_OFFSET:IV_OFFSET+4]
        #     print(f"个体值 (位置 0x{IV_OFFSET:02X}-0x{IV_OFFSET+3:02X}): {iv_data.hex(' ').upper()}")
            
        #     # 解析并显示个体值
        #     ivs = parse_ivs(iv_data)
        #     iv_str = ", ".join([f"{name}:{value}" for name, value in zip(v_names, ivs)])
        #     print(f"解析个体值: {iv_str}")
        # else:
        #     print("\n错误: 个体值偏移超出文件范围!")
    else:
        file_size = len(data)
        num_pokemon = file_size // POKEMON_SIZE
        print(f"文件: trainer_poke_{file_number}.bin")
        print(f"宝可梦数量: {num_pokemon}")
        print("-" * 80)

        for i in range(num_pokemon):
            offset = i * POKEMON_SIZE
            if offset + POKEMON_SIZE > file_size:
                print(f"警告: 宝可梦{i}的数据不完整!")
                break

            # 飘移
            pokemon_id_offset = offset + POKEMON_ID_OFFSET
            item_offset = offset + ITEM_OFFSET
            level_offset = offset + LEVEL_OFFSET
            nature_offset = offset + NATURE_OFFSET
            ev_offset = offset + EV_OFFSET
            iv_offset = offset + IV_OFFSET
            move1_offset = offset + MOVE1_OFFSET
            move2_offset = offset + MOVE2_OFFSET
            move3_offset = offset + MOVE3_OFFSET
            move4_offset = offset + MOVE4_OFFSET

            pokemon_id = struct.unpack("<H", data[pokemon_id_offset:pokemon_id_offset+2])[0]
            item_id = struct.unpack("<H", data[item_offset:item_offset+2])[0]
            level = data[level_offset]
            nature_value = data[nature_offset]

            pokemon_name = get_pokemon_name(pokemon_id)

            pokemon_types = get_pokemon_types(pokemon_id)
            pokemon_types_chinese = [type_map.get(t, "未知{t}") for t in pokemon_types]

            item_name = item_id_to_name.get(item_id, f"未知道具({item_id})")

            nature_name = nature_map.get(nature_value, f"未知({nature_value})")
            nature_effect = nature_effect_map.get(nature_name, ("", ""))
            if nature_effect[0] and nature_effect[1]:
                nature_display = f"{nature_name}( +{nature_effect[0]}, -{nature_effect[1]} )"
            else:
                nature_display = nature_name

            evs = []
            if ev_offset + 6 <= len(data):
                ev_data = data[ev_offset:ev_offset+6]
                evs = parse_evs(ev_data)
            
            ivs = []
            if iv_offset + 4 <= len(data):
                iv_data = data[iv_offset:iv_offset+4]
                ivs = parse_ivs(iv_data)
            
            # 解析特性
            ability_value = (data[offset + ABILITY_OFFSET] >> 4) & 0x0F
            ability_display = get_ability_display(pokemon_id, ability_value)
            
            # 解析技能
            move1 = struct.unpack("<H", data[move1_offset:move1_offset+2])[0]
            move2 = struct.unpack("<H", data[move2_offset:move2_offset+2])[0]
            move3 = struct.unpack("<H", data[move3_offset:move3_offset+2])[0]
            move4 = struct.unpack("<H", data[move4_offset:move4_offset+2])[0]
            
            move1_name = get_move_name(move1)
            move2_name = get_move_name(move2)
            move3_name = get_move_name(move3)
            move4_name = get_move_name(move4)

            # 打印宝可梦信息
            print(f"宝可梦 {i+1}:")
            print(f"  宝可梦ID: {pokemon_id} ( {pokemon_name} )")
            print(f"  道具ID: {item_id} ( {item_name} )")
            print(f"  等级: {level}")
            print(f"  性格: {nature_display}")
            print(f"  属性: {', '.join(pokemon_types)}( {', '.join(pokemon_types_chinese) })")
            print(f"  特性: {ability_display}")
            print(f"  技能: {move1_name}, {move2_name}, {move3_name}, {move4_name}")
            print(f"  个体值: {', '.join([f'{name}:{value}' for name, value in zip(v_names, ivs)])}")
            print(f"  努力值: {', '.join([f'{name}:{value}' for name, value in zip(v_names, evs)])}")
            print("-" * 80)
    
    return True


def list_all_trainer_files():

    if not os.path.exists(trainer_poke_dir):
        print(f"{trainer_poke_dir} 不存在")
        return False

    files = [f for f in os.listdir(trainer_poke_dir) if f.startswith("trainer_poke_") and f.endswith(".bin")]
    files.sort()

    file_numbers = []
    pattern = re.compile(r"trainer_poke_(\d+)\.bin")
    for f in files:
        match = pattern.match(f)
        if match:
            file_numbers.append(int(match.group(1)))
        else:
            print(f"无法解析文件名：{f}")
    
    # 检查缺失的文件编号
    all_possible_numbers = set(range(0, 437))  # 0到436
    existing_numbers = set(file_numbers)
    missing_numbers = sorted(all_possible_numbers - existing_numbers)

    print("可用的训练家文件：")
    
    if len(files) <= 6:
        # 显示所有文件
        for i, f in enumerate(files):
            file_num = file_numbers[i]
            print(f"  {file_num:3d}. {f}")
    else:
        # 显示前3个和后2个文件
        for i in range(3):
            file_num = file_numbers[i]
            print(f"  {file_num:3d}. {files[i]}")
        
        print(f"  ... 省略 {len(files) - 5} 个文件 ...")
        
        for i in range(-2, 0):
            file_num = file_numbers[i]
            print(f"  {file_num:3d}. {files[i]}")
    
    # 显示缺失的文件
    if missing_numbers:
        # 如果缺失文件太多，也只显示部分
        if len(missing_numbers) > 10:
            first_five = missing_numbers[:5]
            last_five = missing_numbers[-5:]
            print(f"\n缺失的文件编号: {', '.join(map(str, first_five))}, ..., {', '.join(map(str, last_five))}")
            print(f"共缺失 {len(missing_numbers)} 个文件")
        else:
            print(f"\n缺失的文件编号: {', '.join(map(str, missing_numbers))}")
    
    return file_numbers


if __name__ == "__main__":
    # 列出所有可用的训练家文件
    file_numbers = list_all_trainer_files()
    
    if not file_numbers:
        print("未找到任何训练家文件")
        exit(1)
    
    # 询问用户要查看哪个文件
    try:
        choice = input("\n请输入要查看的文件编号:").strip()
        # choice = "1192"
        
        if choice == "1192":
            file_number = input("请输入要查看二进制结构的文件编号: ").strip()
            main(check16=True, file_number=file_number)
        elif choice.isdigit() and int(choice) in file_numbers:
            file_number = choice
            success = main(check16=False, file_number=file_number)
            if not success:
                print(f"文件 trainer_poke_{file_number.zfill(3)}.bin 不存在")
        else:
            print("无效的选择或文件不存在")
    except ValueError:
        print("请输入有效的数字")
