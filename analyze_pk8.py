import struct
import json
import os
from collections import defaultdict

try:
    from file_manager import safe_load_file, safe_save_file
except ImportError:
    safe_load_file = None
    safe_save_file = None
    print("警告: 无法导入file_manager模块，某些功能可能不可用")

# 基于PKHeX的G8PKM.cs修正的偏移量（适用于PK8格式）
offset_map = {
    'species': 0x08,
    'ability_num': 0x16,  # 低3位，且与AbilityNumber属性对应
    'held_item': 0x0A,
    'nature': 0x20,
    'ev_hp': 0x26,
    'ev_atk': 0x27,
    'ev_def': 0x28,
    'ev_spe': 0x29,
    'ev_spa': 0x2A,
    'ev_spd': 0x2B,
    'nickname': 0x58,
    'move1': 0x72,
    'move2': 0x74,
    'move3': 0x76,
    'move4': 0x78,
    'friendship': 0x112,  # OriginalTrainerFriendship
    'met_year': 0x11C,
    'met_month': 0x11D,
    'met_day': 0x11E,
    'met_location': 0x122,
    'level': 0x148,
    'iv32': 0x8C,  # 32位存储所有个体值
    'stat_hp_current': 0x8A,
    'stat_hp_max': 0x14A,
    'stat_atk': 0x14C,
    'stat_def': 0x14E,
    'stat_spe': 0x150,
    'stat_spa': 0x152,
    'stat_spd': 0x154,
    'pid': 0x1C,
    'tid16': 0x0C,
    'sid16': 0x0E,
    'ability': 0x14,  # Ability属性
}

# 从correct_decrypt_pokemon.py整合的解密函数
def decrypt_pokemon_data(data):
    """
    使用PKHeX的解密逻辑解密宝可梦数据
    """
    if len(data) < 0x148:  # SIZE_8PARTY
        return data
    
    # 读取EC值（前4字节）
    ec = struct.unpack('<I', data[0:4])[0]
    
    # 计算sv值
    sv = (ec >> 13) & 31
    
    # 复制数据以避免修改原始数据
    decrypted = bytearray(data)
    
    # 调用CryptPKM进行解密
    crypt_pkm(decrypted, ec, 0x50)  # SIZE_8BLOCK = 0x50
    
    # 调用ShuffleArray进行数据块重排
    decrypted = shuffle_array(decrypted, sv, 0x50)  # SIZE_8BLOCK = 0x50
    
    return decrypted

def crypt_pkm(data, pv, block_size):
    """
    实现PKHeX中的CryptPKM方法
    """
    start = 8
    end = (4 * block_size) + start
    crypt_array(data, pv, start, end)
    
    # 如果数据长度大于end，则解密剩余部分（Party Stats）
    if len(data) > end:
        crypt_array(data, pv, end, len(data))

def crypt_array(data, seed, start, end):
    """
    实现PKHeX中的CryptArray方法
    """
    i = start
    while i < end:
        seed = crypt(data, i, seed)
        i += 2
        seed = crypt(data, i, seed)
        i += 2

def crypt(data, offset, seed):
    """
    实现PKHeX中的Crypt方法
    """
    # 更新种子
    seed = (0x41C64E6D * seed) + 0x6073
    
    # 读取当前值
    current = struct.unpack('<H', data[offset:offset+2])[0]
    
    # 异或操作
    current ^= (seed >> 16) & 0xFFFF
    
    # 写回数据
    data[offset:offset+2] = struct.pack('<H', current)
    
    return seed

def shuffle_array(data, sv, block_size):
    """
    实现PKHeX中的ShuffleArray方法
    """
    # BlockPosition数组来自PKHeX源码
    block_position = [
        0, 1, 2, 3,
        0, 1, 3, 2,
        0, 2, 1, 3,
        0, 3, 1, 2,
        0, 2, 3, 1,
        0, 3, 2, 1,
        1, 0, 2, 3,
        1, 0, 3, 2,
        2, 0, 1, 3,
        3, 0, 1, 2,
        2, 0, 3, 1,
        3, 0, 2, 1,
        1, 2, 0, 3,
        1, 3, 0, 2,
        2, 1, 0, 3,
        3, 1, 0, 2,
        2, 3, 0, 1,
        3, 2, 0, 1,
        1, 2, 3, 0,
        1, 3, 2, 0,
        2, 1, 3, 0,
        3, 1, 2, 0,
        2, 3, 1, 0,
        3, 2, 1, 0,
        
        # duplicates of 0-7 to eliminate modulus
        0, 1, 2, 3,
        0, 1, 3, 2,
        0, 2, 1, 3,
        0, 3, 1, 2,
        0, 2, 3, 1,
        0, 3, 2, 1,
        1, 0, 2, 3,
        1, 0, 3, 2,
    ]
    
    result = bytearray(data)
    index = sv * 4
    start = 8
    
    for block in range(4):
        ofs = block_position[index + block]
        src_start = start + (block_size * ofs)
        dest_start = start + (block_size * block)
        
        # 复制数据块
        result[dest_start:dest_start+block_size] = data[src_start:src_start+block_size]
    
    return result


def is_shiny(pid, tid16, sid16):
    """判断是否是闪光"""
    xor = (pid >> 16) ^ (pid & 0xFFFF) ^ tid16 ^ sid16
    return xor < 16

def display_full_hex_dump(file_path, description):
    """显示.pk8文件的完整十六进制转储"""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"无法打开文件: {e}")
        return None
    
    if len(data) != 344:
        print(f"警告: .pk8文件大小应为344字节，实际为 {len(data)} 字节")
        return None
    
    print(f"=== {description} ===")
    print(f"文件: {os.path.basename(file_path)}")
    print(f"文件大小: {len(data)} 字节\n")

    # 显示完整十六进制转储
    print("完整十六进制转储:")
    for i in range(0, len(data), 16):
        # 地址
        address = f"0x{i:04X}"

        # 十六进制部分
        hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
        hex_part = hex_part.ljust(48)  # 补齐到固定宽度

        # ASCII部分
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])

        print(f"{address}: {hex_part} {ascii_part}")

    print()
    return True


def parse_pk8_to_dict(data, encrypted=False):
    """解析PK8数据并返回字典
    
    Args:
        data: 宝可梦数据
        encrypted: 是否为加密数据，如果是则先解密
    """
    # 如果数据是加密的，先解密
    if encrypted:
        data = decrypt_pokemon_data(data)
    
    result = {}

    # 物种
    species = struct.unpack_from('<H', data, offset_map['species'])[0]
    result['species'] = species

    # 昵称
    nickname_data = data[offset_map['nickname']:offset_map['nickname']+24]
    try:
        end_pos = 0
        for i in range(0, len(nickname_data)-1, 2):
            if nickname_data[i] == 0 and nickname_data[i+1] == 0:
                end_pos = i
                break
        else:
            end_pos = len(nickname_data)
        
        if end_pos > 0:
            nickname = nickname_data[:end_pos].decode('utf-16le')
            result['nickname'] = nickname
        else :
            result['nickname'] = ''
    except Exception as e:
        result['nickname'] = f"解析失败 - {e}"
    
    # 等级
    level = data[offset_map['level']]
    result['level'] = level
    
    # 技能
    move_offsets = ['move1', 'move2', 'move3', 'move4']
    moves = {}
    for i, move_key in enumerate(move_offsets):
        offset = offset_map[move_key]
        move_id = struct.unpack_from('<H', data, offset)[0]
        moves[f'move{i+1}'] = move_id
    result['moves'] = moves
    
    # 持有物品
    held_item = struct.unpack_from('<H', data, offset_map['held_item'])[0]
    result['held_item'] = held_item
    
    # 亲密度
    friendship = data[offset_map['friendship']]
    result['friendship'] = friendship
    
    # 特性
    ability_id = struct.unpack_from('<H', data, offset_map['ability'])[0]
    result['ability_id'] = ability_id
    
    # 特性编号
    ability_num = data[offset_map['ability_num']] & 0x7  # 取低3位
    result['ability_num'] = ability_num
    
    # 性格
    nature_value = data[offset_map['nature']]
    result['nature_value'] = nature_value
    
    # 努力值
    ev_keys = ['ev_hp', 'ev_atk', 'ev_def', 'ev_spa', 'ev_spd', 'ev_spe']
    evs = {}
    for key in ev_keys:
        ev = data[offset_map[key]]
        evs[key.split('_')[1]] = ev  # 提取出HP/ATK/DEF等部分作为键
    result['evs'] = evs
    
    # 个体值 (从32位值中提取)
    iv32 = struct.unpack_from('<I', data, offset_map['iv32'])[0]
    iv_hp = (iv32 >> 0) & 0x1F
    iv_atk = (iv32 >> 5) & 0x1F
    iv_def = (iv32 >> 10) & 0x1F
    iv_spe = (iv32 >> 15) & 0x1F
    iv_spa = (iv32 >> 20) & 0x1F
    iv_spd = (iv32 >> 25) & 0x1F
    is_egg = ((iv32 >> 30) & 1) == 1
    is_nicknamed = ((iv32 >> 31) & 1) == 1
    
    result['ivs'] = {
        'hp': iv_hp,
        'atk': iv_atk,
        'def': iv_def,
        'spa': iv_spa,
        'spd': iv_spd,
        'spe': iv_spe
    }
    result['is_egg'] = is_egg
    result['is_nicknamed'] = is_nicknamed
    
    # 能力值
    stat_hp_current = struct.unpack_from('<H', data, offset_map['stat_hp_current'])[0]
    stat_hp_max = struct.unpack_from('<H', data, offset_map['stat_hp_max'])[0]
    stat_atk = struct.unpack_from('<H', data, offset_map['stat_atk'])[0]
    stat_def = struct.unpack_from('<H', data, offset_map['stat_def'])[0]
    stat_spe = struct.unpack_from('<H', data, offset_map['stat_spe'])[0]
    stat_spa = struct.unpack_from('<H', data, offset_map['stat_spa'])[0]
    stat_spd = struct.unpack_from('<H', data, offset_map['stat_spd'])[0]
    
    result['stats'] = {
        'hp_current': stat_hp_current,
        'hp_max': stat_hp_max,
        'atk': stat_atk,
        'def': stat_def,
        'spa': stat_spa,
        'spd': stat_spd,
        'spe': stat_spe
    }
    
    # 相遇信息
    met_year = data[offset_map['met_year']]
    met_month = data[offset_map['met_month']]
    met_day = data[offset_map['met_day']]
    met_location = struct.unpack_from('<H', data, offset_map['met_location'])[0]
    
    result['met_date'] = (2000 + met_year, met_month, met_day)
    result['met_location'] = met_location
    
    # 是否闪光
    pid = struct.unpack_from('<I', data, offset_map['pid'])[0]
    tid16 = struct.unpack_from('<H', data, offset_map['tid16'])[0]
    sid16 = struct.unpack_from('<H', data, offset_map['sid16'])[0]
    shiny = is_shiny(pid, tid16, sid16)
    
    result['shiny'] = shiny
    result['pid'] = pid
    result['tid16'] = tid16
    result['sid16'] = sid16
    
    return result


def analyze_kbox_data(kbox_path, encrypted=True):
    """分析KBoxData.bin文件中的宝可梦数据
    
    Args:
        kbox_path: KBoxData.bin文件路径
        encrypted: 数据是否加密
        
    Returns:
        包含所有宝可梦数据的列表
    """
    # 读取KBoxData.bin文件
    with open(kbox_path, 'rb') as f:
        kbox_data = f.read()
    
    # print(f"KBox数据大小: {len(kbox_data)}字节")
    
    # 盒子中每只宝可梦的大小
    pokemon_size = 0x158  # SIZE_8PARTY
    
    # 计算盒子中宝可梦的数量
    pokemon_count = len(kbox_data) // pokemon_size
    # print(f"盒子中宝可梦数量: {pokemon_count}")
    
    results = []
    
    # 分析每只宝可梦
    for i in range(pokemon_count):
        offset = i * pokemon_size
        pokemon_data = kbox_data[offset:offset+pokemon_size]
        
        # 解析宝可梦数据
        result = parse_pk8_to_dict(pokemon_data, encrypted=encrypted)
        result['index'] = i  # 添加索引
        
        results.append(result)
        
        # # 打印关键信息
        # print(f"宝可梦 {i+1}: 物种={result['species']}, 等级={result['level']}, "
        #       f"OT亲密度={result['friendship']}, "
        #       f"持有物={result['held_item']}, 性格={result['nature_value']}, "
        #       f"IVs: HP={result['ivs']['hp']}, ATK={result['ivs']['atk']}, DEF={result['ivs']['def']}, "
        #       f"SPA={result['ivs']['spa']}, SPD={result['ivs']['spd']}, SPE={result['ivs']['spe']}")
    
    return results

def analyze_kparty_data(kparty_path, target_ec=0xAB62D4EB, encrypted=True):
    """分析KPartyData.bin文件中的宝可梦数据
    
    Args:
        kparty_path: KPartyData.bin文件路径
        target_ec: 目标EC值，用于找到队伍第一只宝可梦
        encrypted: 数据是否加密
        
    Returns:
        包含所有宝可梦数据的列表
    """
    # 读取KPartyData.bin文件
    with open(kparty_path, 'rb') as f:
        kparty_data = f.read()
    
    print(f"KParty数据大小: {len(kparty_data)}字节")
    
    # 搜索目标EC值（小端序）
    target_ec_bytes = struct.pack('<I', target_ec)
    ec_position = kparty_data.find(target_ec_bytes)
    
    if ec_position == -1:
        print(f"未找到EC值 0x{target_ec:08X}")
        return []
    
    # print(f"找到EC值 0x{target_ec:08X} 在位置 0x{ec_position:X}")
    
    # 盒子中每只宝可梦的大小
    pokemon_size = 0x158  # SIZE_8PARTY
    
    # 直接使用找到的EC位置作为第一只宝可梦的起始位置
    results = []
    first_pokemon_offset = ec_position
    # print(f"使用第一只宝可梦偏移量: 0x{first_pokemon_offset:X}")
    
    # 假设队伍中最多有6只宝可梦
    for i in range(6):
        offset = first_pokemon_offset + i * pokemon_size
        
        # 如果超出文件范围，跳过
        if offset + pokemon_size > len(kparty_data):
            continue
            
        pokemon_data = kparty_data[offset:offset+pokemon_size]
        
        # 获取当前宝可梦的EC值
        current_ec = struct.unpack('<I', pokemon_data[:4])[0]
        # print(f"队伍宝可梦 {i+1} (偏移量 0x{offset:X}): EC=0x{current_ec:08X}")
        
        # 解析宝可梦数据
        result = parse_pk8_to_dict(pokemon_data, encrypted=encrypted)
        result['index'] = i  # 添加索引
        result['offset'] = offset  # 添加偏移量
        result['ec'] = current_ec  # 添加EC值
        
        results.append(result)
        
        # # 打印关键信息
        # print(f"  物种={result['species']}, 等级={result['level']}, "
        #       f"OT亲密度={result['friendship']}, "
        #       f"持有物={result['held_item']}, 性格={result['nature_value']}, "
        #       f"IVs: HP={result['ivs']['hp']}, ATK={result['ivs']['atk']}, DEF={result['ivs']['def']}, "
        #       f"SPA={result['ivs']['spa']}, SPD={result['ivs']['spd']}, SPE={result['ivs']['spe']}")
    
    # 检查数据是否合理
    if results and (results[0]['species'] > 1000 or results[0]['level'] > 100):
        print("\n*** 数据异常，尝试不同的偏移量计算方法 ***")
        
        # 方法2: 假设每只宝可梦前有4字节的其他数据
        results = []
        pokemon_with_header_size = pokemon_size + 4
        party_count = len(kparty_data) // pokemon_with_header_size
        print(f"估计队伍中宝可梦数量: {party_count}")
        
        # 分析每只宝可梦
        for i in range(party_count):
            offset = i * pokemon_with_header_size
            # 跳过4字节的头部数据
            pokemon_data = kparty_data[offset+4:offset+4+pokemon_size]
            
            # 如果数据长度不足，跳过
            if len(pokemon_data) < pokemon_size:
                continue
            
            # 获取当前宝可梦的EC值
            current_ec = struct.unpack('<I', pokemon_data[:4])[0]
            # print(f"队伍宝可梦 {i+1} (偏移量 0x{offset:X}): EC=0x{current_ec:08X}")
            
            # 解析宝可梦数据
            result = parse_pk8_to_dict(pokemon_data, encrypted=encrypted)
            result['index'] = i  # 添加索引
            result['offset'] = offset  # 添加偏移量
            result['ec'] = current_ec  # 添加EC值
            
            results.append(result)
            
            # # 打印关键信息
            # print(f"  物种={result['species']}, 等级={result['level']}, "
            #       f"OT亲密度={result['friendship']}, "
            #       f"持有物={result['held_item']}, 性格={result['nature_value']}, "
            #       f"IVs: HP={result['ivs']['hp']}, ATK={result['ivs']['atk']}, DEF={result['ivs']['def']}, "
            #       f"SPA={result['ivs']['spa']}, SPD={result['ivs']['spd']}, SPE={result['ivs']['spe']}")
    
    return results

def generate_party_json_from_data(kparty_data, encrypted=True):
    """生成队伍宝可梦的JSON数据
    
    Args:
        kparty_data: KParty数据（bytes对象）
        encrypted: 数据是否加密
        
    Returns:
        包含队伍宝可梦数据的字典
    """
    print(f"KParty数据大小: {len(kparty_data)}字节")
    
    # 每只宝可梦的大小
    pokemon_size = 0x158  # SIZE_8PARTY
    
    # 使用偏移量0作为起始位置
    party_data = {}
    first_pokemon_offset = 0
    # print(f"使用第一只宝可梦偏移量: 0x{first_pokemon_offset:X}")
    
    # 队伍中最多有6只宝可梦
    for i in range(6):
        offset = first_pokemon_offset + i * pokemon_size
        
        # 如果超出文件范围，跳过
        if offset + pokemon_size > len(kparty_data):
            party_data[str(i+1)] = None
            continue
            
        pokemon_data = kparty_data[offset:offset+pokemon_size]
        
        # 获取当前宝可梦的EC值
        current_ec = struct.unpack('<I', pokemon_data[:4])[0]
        # print(f"队伍宝可梦 {i+1} (偏移量 0x{offset:X}): EC=0x{current_ec:08X}")
        
        # 如果EC为0，表示该位置为空
        if current_ec == 0:
            party_data[str(i+1)] = None
            continue
        
        # 解析宝可梦数据
        result = parse_pk8_to_dict(pokemon_data, encrypted=encrypted)
        result['index'] = i  # 添加索引
        result['offset'] = offset  # 添加偏移量
        result['ec'] = current_ec  # 添加EC值
        
        # 转换nickname为中文
        if 'nickname' in result and result['nickname']:
            try:
                # 尝试将nickname转换为UTF-8字符串
                nickname_bytes = result['nickname']
                if isinstance(nickname_bytes, bytes):
                    result['nickname'] = nickname_bytes.decode('utf-8', errors='replace')
                elif isinstance(nickname_bytes, str):
                    # 如果已经是字符串，确保它是UTF-8编码
                    result['nickname'] = nickname_bytes
            except Exception as e:
                print(f"转换nickname时出错: {e}")
                result['nickname'] = str(nickname_bytes)
        
        party_data[str(i+1)] = result
        
        # # 打印关键信息
        # print(f"  物种={result['species']}, 等级={result['level']}, "
        #       f"OT亲密度={result['friendship']}, "
        #       f"持有物={result['held_item']}, 性格={result['nature_value']}, "
        #       f"IVs: HP={result['ivs']['hp']}, ATK={result['ivs']['atk']}, DEF={result['ivs']['def']}, "
        #       f"SPA={result['ivs']['spa']}, SPD={result['ivs']['spd']}, SPE={result['ivs']['spe']}")
    
    return party_data


def generate_box_json_from_data(kbox_data, encrypted=True):
    """生成盒子宝可梦的JSON数据
    
    Args:
        kbox_data: KBox数据（bytes对象）
        encrypted: 数据是否加密
        
    Returns:
        包含盒子宝可梦数据的字典
    """
    print(f"KBox数据大小: {len(kbox_data)}字节")
    
    # 盒子中每只宝可梦的大小
    pokemon_size = 0x158  # SIZE_8PARTY
    
    # 计算盒子中宝可梦的数量
    pokemon_count = len(kbox_data) // pokemon_size
    # print(f"盒子中宝可梦数量: {pokemon_count}")
    
    # 每个盒子有30个位置
    box_count = 32
    pokemon_per_box = 30
    
    box_data = {}
    
    # 处理每个盒子
    for box_idx in range(box_count):
        box_name = f"box{box_idx+1}"
        box_data[box_name] = {}
        
        # 处理盒子中的每个位置
        for slot_idx in range(pokemon_per_box):
            global_idx = box_idx * pokemon_per_box + slot_idx
            
            # 如果超出宝可梦总数，该位置为空
            if global_idx >= pokemon_count:
                box_data[box_name][str(slot_idx+1)] = None
                continue
            
            offset = global_idx * pokemon_size
            pokemon_data = kbox_data[offset:offset+pokemon_size]
            
            # 获取当前宝可梦的EC值
            current_ec = struct.unpack('<I', pokemon_data[:4])[0]
            # print(f"盒子{box_idx+1} 位置{slot_idx+1} (偏移量 0x{offset:X}): EC=0x{current_ec:08X}")
            
            # 如果EC为0，表示该位置为空
            if current_ec == 0:
                box_data[box_name][str(slot_idx+1)] = None
                continue
            
            # 解析宝可梦数据
            result = parse_pk8_to_dict(pokemon_data, encrypted=encrypted)
            result['index'] = global_idx  # 添加索引
            result['offset'] = offset  # 添加偏移量
            result['ec'] = current_ec  # 添加EC值
            
            # 转换nickname为中文
            if 'nickname' in result and result['nickname']:
                try:
                    # 尝试将nickname转换为UTF-8字符串
                    nickname_bytes = result['nickname']
                    if isinstance(nickname_bytes, bytes):
                        result['nickname'] = nickname_bytes.decode('utf-8', errors='replace')
                    elif isinstance(nickname_bytes, str):
                        # 如果已经是字符串，确保它是UTF-8编码
                        result['nickname'] = nickname_bytes
                except Exception as e:
                    print(f"转换nickname时出错: {e}")
                    result['nickname'] = str(nickname_bytes)
            
            box_data[box_name][str(slot_idx+1)] = result
            
            # # 打印关键信息
            # print(f"  物种={result['species']}, 等级={result['level']}, "
            #       f"OT亲密度={result['friendship']}, "
            #       f"持有物={result['held_item']}, 性格={result['nature_value']}, "
            #       f"IVs: HP={result['ivs']['hp']}, ATK={result['ivs']['atk']}, DEF={result['ivs']['def']}, "
            #       f"SPA={result['ivs']['spa']}, SPD={result['ivs']['spd']}, SPE={result['ivs']['spe']}")
    
    return box_data


def generate_party_json(kparty_path, encrypted=True):
    """生成队伍宝可梦的JSON数据
    
    Args:
        kparty_path: KPartyData.bin文件路径
        encrypted: 数据是否加密
        
    Returns:
        包含队伍宝可梦数据的字典
    """
    # 读取KPartyData.bin文件
    with open(kparty_path, 'rb') as f:
        kparty_data = f.read()
    
    return generate_party_json_from_data(kparty_data, encrypted)


def generate_box_json(kbox_path, encrypted=True):
    """生成盒子宝可梦的JSON数据
    
    Args:
        kbox_path: KBoxData.bin文件路径
        encrypted: 数据是否加密
        
    Returns:
        包含盒子宝可梦数据的字典
    """
    # 读取KBoxData.bin文件
    with open(kbox_path, 'rb') as f:
        kbox_data = f.read()
    
    return generate_box_json_from_data(kbox_data, encrypted)


def generate_pokemon_main_info_json(kparty_path, kbox_path, encrypted=True, output_file="config/pokemon_main_info.json"):
    """生成包含队伍和盒子宝可梦信息的JSON文件
    
    Args:
        kparty_path: KPartyData.bin文件路径
        kbox_path: KBoxData.bin文件路径
        encrypted: 数据是否加密
        output_file: 输出JSON文件名
        
    Returns:
        生成的JSON数据
    """
    print("=== 生成队伍宝可梦数据 ===")
    party_data = generate_party_json(kparty_path, encrypted)
    
    print("\n=== 生成盒子宝可梦数据 ===")
    box_data = generate_box_json(kbox_path, encrypted)
    
    # 组合最终数据
    main_info = {
        "party": party_data,
        "box": box_data
    }
    
    # 写入JSON文件
    if safe_save_file:
        # 确保目录存在
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        safe_save_file(main_info, os.path.basename(output_file), ensure_config_dir=False)
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(main_info, f, ensure_ascii=False, indent=4)
    
    print(f"\n=== 已生成 {output_file} 文件 ===")
    
    return main_info


def generate_pokemon_main_info_json_from_data(kparty_data, kbox_data, encrypted=True, output_file="config/pokemon_main_info.json"):
    """生成包含队伍和盒子宝可梦信息的JSON文件
    
    Args:
        kparty_data: KParty数据（bytes对象）
        kbox_data: KBox数据（bytes对象）
        encrypted: 数据是否加密
        output_file: 输出JSON文件名
        
    Returns:
        生成的JSON数据
    """
    print("=== 生成队伍宝可梦数据 ===")
    party_data = generate_party_json_from_data(kparty_data, encrypted)
    
    print("\n=== 生成盒子宝可梦数据 ===")
    box_data = generate_box_json_from_data(kbox_data, encrypted)
    
    # 组合最终数据
    main_info = {
        "party": party_data,
        "box": box_data
    }
    
    # 写入JSON文件
    if safe_save_file:
        # 确保目录存在
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        safe_save_file(main_info, os.path.basename(output_file), ensure_config_dir=False)
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(main_info, f, ensure_ascii=False, indent=4)
    
    print(f"\n=== 已生成 {output_file} 文件 ===")
    
    return main_info


if __name__ == '__main__':
    
    # # KBoxData.bin文件路径
    # kbox_path = r"real main/main_KBoxData.bin"
    # kbox_cope_path = r"real main/main - 副本_KBoxData.bin"
    
    # # KPartyData.bin文件路径
    # kparty_main_path = r"real main/main_KPartyData.bin"
    # kparty_copy_path = r"real main/main - 副本_KPartyData.bin"
    
    # # 生成main的JSON数据
    # print("\n=== 生成main的宝可梦信息JSON ===")
    # generate_pokemon_main_info_json(kparty_main_path, kbox_path, encrypted=True)
    
    # # 生成main - 副本的JSON数据
    # print("\n=== 生成main - 副本的宝可梦信息JSON ===")
    # generate_pokemon_main_info_json(kparty_copy_path, kbox_cope_path, encrypted=True, output_file="pokemon_main_copy_info.json")

    kbox_path = r"real_main_python/KBoxData_direct.bin"
    kparty_path = r"real_main_python/KPartyData_direct.bin"
    generate_pokemon_main_info_json(kparty_path, kbox_path, encrypted=True, output_file="config/pokemon_main_python_info.json")
