import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_pokemon_abilities():
    """从52poke网站抓取宝可梦特性数据并生成JSON文件"""
    
    # url = "https://wiki.52poke.com/wiki/%E7%89%B9%E6%80%A7%E5%88%97%E8%A1%A8" # 特性列表
    url = "https://wiki.52poke.com/wiki/%E6%8B%9B%E5%BC%8F%E5%88%97%E8%A1%A8%EF%BC%88%E5%89%91%EF%BC%8F%E7%9B%BE%EF%BC%89"  # 招式列表
    
    # 发送HTTP请求
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    
    if response.status_code != 200:
        print(f"无法访问网页，状态码: {response.status_code}")
        return
    
    # 解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 查找所有特性表格
    # tables = soup.find_all('table', class_=lambda x: x and 'fulltable' in x and 'eplist' in x)
    tables = soup.find_all('table', class_=lambda x: x and 'hvlist' in x and 'fulltable' in x)
    
    # 存储所有特性
    ability_map = {}
    
    # 遍历所有表格
    for table in tables:
        # 查找表格中的所有行
        rows = table.find_all('tr')
        
        # 跳过表头行，从第二行开始处理
        for row in rows[1:]:  # 跳过th行
            cells = row.find_all('td')
            if len(cells) >= 2:
                # 提取编号和特性名
                try:
                    # 编号在第一个td中
                    number_text = cells[0].get_text(strip=True)
                    # # 特性名在第二个td中的a标签里
                    # name_link = cells[1].find('a')
                    # if name_link:
                    #     ability_name = name_link.get_text(strip=True)
                        
                    #     # 处理编号，去除可能的*号
                    #     number = number_text.replace('*', '')
                    #     if number.isdigit():
                    #         ability_map[number] = ability_name
                    # 处理编号，去除可能的*号
                    number = number_text.replace('*', '')
                    if not number.isdigit():
                        continue

                    if len(cells) > 8:
                        description_text1 = cells[4].get_text(strip=True)   # 属性
                        description_text2 = cells[5].get_text(strip=True)   # 分类
                        description_text3 = cells[6].get_text(strip=True)   # 威力
                        description_text4 = cells[7].get_text(strip=True)   # 命中
                        description_text5 = cells[8].get_text(strip=True)   # PP
                        description_text6 = cells[9].get_text(strip=True)   # 说明

                        move_info = f"{description_text1}--{description_text2}--{description_text3}--{description_text4}--{description_text5}\n{description_text6}"
                        ability_map[number] = move_info
                    else:
                        col7_text = cells[6].get_text(strip=True)
                        if "不可用" in col7_text:
                            ability_map[number] = "不可用"
                            continue
                except Exception as e:
                    print(f"处理行时出错: {e}")
                    continue
    
    # 保存到JSON文件
    output_data = {
        "ability_map": ability_map
    }
    
    with open("pokemon_move_explanation.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"成功抓取 {len(ability_map)} 个招式数据并保存到 pokemon_move_explanation.json")
    
    # 显示前几个和后几个特性作为示例
    ability_items = list(ability_map.items())
    print("\n前10个:")
    for i, (num, name) in enumerate(ability_items[:10]):
        print(f"  {num}: {name}")
    
    print("\n后10个:")
    for i, (num, name) in enumerate(ability_items[-10:]):
        print(f"  {num}: {name}")



def create_location_map_from_list():
    """根据提供的地点列表创建地点映射"""
    
    # 你提供的地点列表（按顺序）
    locations = [
        "三岔平原",
        "专注森林",
        "九路隧道",
        "伦度罗瑟",
        "伽勒爾礦山",
        "健身之海",
        "冰山遺跡（伽勒爾）",
        "冰點雪原",
        "凍凝村",
        "凍海",
        "列島海域",
        "化朗鎮",
        "卧室",
        "含羞苞旅店",
        "圓環海灣",
        "塔頂",
        "宝可梦巢穴",
        "寶物庫",
        "宮門市",
        "宮門競技場",
        "對戰塔（剑／盾）",
        "對戰咖啡館",
        "尖釘鎮",
        "岩山遺跡（伽勒爾）",
        "巨人凳岩",
        "巨人帽岩",
        "巨人睡榻",
        "巨人鏡池",
        "巨人鞋底",
        "巨石原野",
        "微寐森林",
        "惡之塔",
        "戰競鎮",
        "戰鬥洞窟",
        "抉擇遺跡",
        "拳關丘陵",
        "拳關市",
        "挑戰之路",
        "挑戰海灘",
        "揖礼原野",
        "旷野地带",
        "木桿鎮",
        "極巨巢穴",
        "橋間空地",
        "機擎市",
        "機擎市郊外",
        "機擎河岸",
        "水之塔",
        "水舟鎮",
        "沐光森林",
        "沙塵窪地",
        "洛茲大廈",
        "海鳴洞窟",
        "清涼濕原",
        "湖畔洞窟",
        "溯傳鎮",
        "煦麗草原",
        "熱身洞穴",
        "爱奥尼亚酒店",
        "牙牙湖之眼",
        "牙牙湖東岸",
        "牙牙湖西岸",
        "王冠神殿",
        "王冠雪原",
        "球湖湖畔",
        "登頂隧道",
        "瞭望塔舊址",
        "第二礦山",
        "美发沙龙（伽勒尔）",
        "美納斯湖北岸",
        "美纳斯湖南岸",
        "能源工廠",
        "舞姿鎮",
        "草路鎮",
        "蜂巢島",
        "蜂巢海",
        "起橇雪原",
        "迷光森林",
        "逆鱗湖",
        "通頂雪道",
        "遠古墓地",
        "鍋底沙漠",
        "鍛鍊平原",
        "鎧島",
        "集匯空地",
        "雙拳塔",
        "離島海域",
        "雪中溪谷",
        "馬師傅武館",
        "鬥志洞窟",
        "黑金遺跡（伽勒爾）",
        "１号道路（伽勒尔）",
        "１０号道路（伽勒尔）",
        "２号道路（伽勒尔）",
        "３号道路（伽勒尔）",
        "４号道路（伽勒尔）",
        "５号道路（伽勒尔）",
        "６号道路（伽勒尔）",
        "７號道路（伽勒爾）",
        "８号道路（伽勒尔）",
        "９號道路（伽勒爾）"
    ]
    
    # 按顺序创建映射
    location_map = {}
    for i, location in enumerate(locations, 1):
        location_map[i] = location
    
    # 保存到JSON文件
    output_data = {
        "location_map": location_map
    }
    
    with open("pokemon_location.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"成功创建包含 {len(location_map)} 个地点的映射文件")
    
    # 显示前几个和后几个地点作为示例
    print("\n前10个地点:")
    for i in range(1, min(11, len(location_map) + 1)):
        print(f"  {i}: {location_map[i]}")
    
    print("\n后10个地点:")
    start_index = max(1, len(location_map) - 9)
    for i in range(start_index, len(location_map) + 1):
        print(f"  {i}: {location_map[i]}")
    
    return location_map

def get_location_name_by_id(location_id):
    """根据ID获取地点名称"""
    try:
        with open("pokemon_location.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            location_map = data.get("location_map", {})
            
        return location_map.get(location_id, f"未知地点({location_id})")
    except FileNotFoundError:
        print("未找到地点映射文件，请先运行创建脚本")
        return f"未知地点({location_id})"

if __name__ == "__main__":
    print("根据提供的地点列表创建地点映射...")
    
    # 创建地点映射
    location_map = create_location_map_from_list()
    
    # 测试查找功能
    print("\n测试查找功能:")
    test_ids = [1, 10, 30, 50, 70]
    for location_id in test_ids:
        location_name = get_location_name_by_id(location_id)
        print(f"  ID {location_id}: {location_name}")