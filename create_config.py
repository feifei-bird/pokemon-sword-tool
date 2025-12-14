import json
import re

from utils.dev_paths import get_dev_path

input_file = "ItemData.txt"
output_file = "item_category_rules.json"
mod_dir = get_dev_path("mod_dir")

with open(input_file, encoding="utf-8") as f:
    lines = f.readlines()

valid_items = []
for line in lines:
    if line.startswith("Index\tItems"):continue

    match = re.match(r"^(\d+)\t", line)
    if match:
        item_id = int(match.group(1))
        valid_items.append(item_id)

# 属性相克表 (按照type_map的顺序)
type_attack_effectiveness = {
    "normal":   [1, 1, 1, 1, 1, 0.5, 1, 0, 0.5, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    "fighting": [2, 1, 0.5, 0.5, 1, 2, 0.5, 0, 2, 1, 1, 1, 1, 0.5, 2, 1, 2, 0.5],
    "flying":   [1, 2, 1, 1, 1, 0.5, 2, 1, 0.5, 1, 1, 2, 0.5, 1, 1, 1, 1, 1],
    "poison":   [1, 1, 1, 0.5, 0.5, 0.5, 1, 0.5, 0, 1, 1, 2, 1, 1, 1, 1, 1, 2],
    "ground":   [1, 1, 0, 2, 1, 2, 0.5, 1, 2, 2, 1, 0.5, 2, 1, 1, 1, 1, 1],
    "rock":     [1, 0.5, 2, 1, 0.5, 1, 2, 1, 0.5, 2, 1, 1, 1, 1, 2, 1, 1, 1],
    "bug":      [1, 0.5, 0.5, 0.5, 1, 1, 1, 0.5, 0.5, 0.5, 1, 2, 1, 2, 1, 1, 2, 0.5],
    "ghost":    [0, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 0.5, 1],
    "steel":    [1, 1, 1, 1, 1, 2, 1, 1, 0.5, 0.5, 0.5, 1, 0.5, 1, 2, 1, 1, 2],
    "fire":     [1, 1, 1, 1, 1, 0.5, 2, 1, 2, 0.5, 0.5, 2, 1, 1, 2, 0.5, 1, 1],
    "water":    [1, 1, 1, 1, 2, 2, 1, 1, 1, 2, 0.5, 0.5, 1, 1, 1, 0.5, 1, 1],
    "grass":    [1, 1, 0.5, 0.5, 2, 2, 0.5, 1, 0.5, 0.5, 2, 0.5, 1, 1, 1, 0.5, 1, 1],
    "electric": [1, 1, 2, 1, 0, 1, 1, 1, 1, 1, 2, 0.5, 0.5, 1, 1, 0.5, 1, 1],
    "psychic":  [1, 2, 1, 2, 1, 1, 1, 1, 0.5, 1, 1, 1, 1, 0.5, 1, 1, 0, 1],
    "ice":      [1, 1, 2, 1, 2, 1, 1, 1, 0.5, 0.5, 0.5, 2, 1, 1, 0.5, 2, 1, 1],
    "dragon":   [1, 1, 1, 1, 1, 1, 1, 1, 0.5, 1, 1, 1, 1, 1, 1, 2, 1, 0],
    "dark":     [1, 0.5, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 0.5, 0.5],
    "fairy":    [1, 2, 1, 0.5, 1, 1, 1, 1, 0.5, 0.5, 1, 1, 1, 1, 1, 2, 2, 1]
}

type_defense_effectiveness = {}

for defense_type in type_attack_effectiveness.keys():
    type_defense_effectiveness[defense_type] = [1.0] * len(type_attack_effectiveness)

for attack_type, multipliers in type_attack_effectiveness.items():
    for i, multiplier in enumerate(multipliers):
        defense_type = list(type_defense_effectiveness.keys())[i]
        type_defense_effectiveness[defense_type][list(type_attack_effectiveness.keys()).index(attack_type)] = multiplier

# 道具分类
item_categories = {
    "special":{
        "name": "特殊道具",
        "weight": 0.1,
        "items": [
            63, 112, 135, 136, 218, 223, 224, 228, 231, 319, 320, 631, 632, 1267, 1587, 1589
        ]
    },
    "bad":{
        "name": "交叉道具",
        "weight": 9.9,
        "items": [
            215, 219, 225, 229, 236, 253, 258, 259, 271, 272, 273, 274, 278, 279, 289, 290, 291, 292, 293, 294, 316, 538, 539, 543, 544, 846, 881, 882, 883, 884, 1122
        ]
    },
    "normal":{
        "name": "普通道具",
        "weight": 20,
        "items": [
            149, 150, 151, 152, 153, 154, 155, 156, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 217, 230, 280, 282, 283, 284, 285, 286, 288, 295, 296, 547, 650, 687, 688, 879, 880, 1118, 1123
        ]
    },
    "great":{
        "name": "不戳道具",
        "weight": 40,
        "items": [
            157, 158, 159, 160, 161, 162, 163, 213, 214, 220, 221, 232, 234, 255, 265, 266, 267, 268, 269, 270, 275, 276, 277, 287, 297, 326, 540, 541, 542, 639, 640, 1119, 1120, 1121
        ]
    },
    "type":{
        "name": "属性：空道具",
        "weight": 30,
        "items": [
            184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 222, 233, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 254, 281, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 317, 318, 545, 546, 564, 644, 648, 649, 686
        ],
        "attack": {
            # 攻击类道具: 属性加成道具
            "normal": [251, 564],   # 丝绸围巾, 一般宝石
            "fighting": [241, 303], # 黑带, 拳头石板
            "flying": [244, 306],   # 锐利鸟嘴, 蓝天石板
            "poison": [245, 304],   # 毒针, 剧毒石板
            "ground": [237, 305],   # 柔软沙子, 大地石板
            "rock": [238, 309, 315],     # 硬石头, 岩石石板, 岩石熏香
            "bug": [222, 308],      # 银粉, 玉虫石板
            "ghost": [247, 310],    # 诅咒之符, 妖怪石板
            "steel": [233, 313],    # 金属膜, 钢铁石板
            "fire": [249, 298],     # 木炭, 火球石板
            "water": [243, 254, 299, 317],    # 神秘水滴, 水滴石板, 海潮熏香, 涟漪熏香
            "grass": [239, 301, 318],    # 奇迹种子, 碧绿石板, 花草熏香
            "electric": [242, 300], # 磁铁, 雷电石板
            "psychic": [248, 307, 314],  # 弯曲的汤匙, 神奇石板, 奇异熏香
            "ice": [246, 302],      # 不融冰, 冰柱石板
            "dragon": [250, 311],   # 龙之牙, 龙之石板
            "dark": [240, 312],     # 黑色眼镜, 恶颜石板
            "fairy": [644]          # 妖精石板
        },
        "defend": {
            # 防御类道具: 属性抗性果实
            "normal": [200],  # 灯浆果(一般)
            "fighting": [189], # 莲蒲果(格)
            "flying": [192],  # 棱瓜果(飞)
            "poison": [190],  # 通通果(毒)
            "ground": [191],  # 腰木果(地)
            "rock": [195],    # 草蚕果(岩)
            "bug": [194],     # 扁樱果(虫)
            "ghost": [196],   # 佛柑果(幽)
            "steel": [199],   # 霹霹果(钢)
            "fire": [184],    # 巧可果(火)
            "water": [185],   # 千香果(水)
            "grass": [187],   # 罗子果(草)
            "electric": [186], # 烛木果(电)
            "psychic": [193], # 福禄果(超)
            "ice": [188],     # 番荔果(冰)
            "dragon": [197],  # 莓榴果(龙)
            "dark": [198],    # 刺耳果(恶)
            "fairy": [686],    # 洛玫果(妖)
            "snowball": [649],      # 雪球(冰)
            "battery": [546],       # 充电电池(电)
            "root": [545],          # 球根(水)
            "light_moss": [648]     # 光苔(水)
        },
        "special": {
            # 特殊效果道具
            "black_sludge": [281],  # 黑色污泥
        }
    }
}

type_map = {
    "normal": 0,
    "fighting": 1,
    "flying": 2,
    "poison": 3,
    "ground": 4,
    "rock": 5,
    "bug": 6,
    "ghost": 7,
    "steel": 8,
    "fire": 9,
    "water": 10,
    "grass": 11,
    "electric": 12,
    "psychic": 13,
    "ice": 14,
    "dragon": 15,
    "dark": 16,
    "fairy": 17
}

config = {
    "use_random": True,
    "replace_all": True,
    "trainer_poke_dir": rf"{mod_dir}\romfs\bin\trainer\trainer_poke",
    "valid_items": valid_items,
    "skip_items": [0],
    "item_categories": item_categories,
    "type_map": type_map,
    "type_attack_effectiveness": type_attack_effectiveness,
    "type_defense_effectiveness": type_defense_effectiveness
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print(f"配置文件已生成！共找到 {len(valid_items)} 个有效道具。")
print(f"配置文件路径: {output_file}")
print(f"训练家宝可梦数据目录: {config['trainer_poke_dir']}")
