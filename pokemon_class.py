"""
宝可梦类模块
定义了宝可梦的基本属性和行为
"""

import json
import os

try:
    from file_manager import safe_load_file
except ImportError:
    pass

class Pokemon:
    """宝可梦类，封装宝可梦的数据和行为"""
    
    def __init__(self, data, position=None):
        """
        初始化宝可梦对象
        
        Args:
            data: 宝可梦的原始数据字典
            position: 宝可梦的位置信息，包含type和index
        """
        self.data = data
        self.position = position or {}
        
        # 基本属性
        self.species = data.get("species", 0)
        self.nickname = data.get("nickname", "")
        self.level = data.get("level", 1)
        self.is_egg = data.get("is_egg", False)
        self.is_nicknamed = data.get("is_nicknamed", False)
        self.shiny = data.get("shiny", False)
        
        # 战斗属性
        self.moves = data.get("moves", {})
        self.held_item = data.get("held_item", 0)
        self.ability_id = data.get("ability_id", 0)
        self.ability_num = data.get("ability_num", 1)
        self.nature_value = data.get("nature_value", 0)
        
        # 努力值和个体值
        self.evs = data.get("evs", {})
        self.ivs = data.get("ivs", {})
        
        # 能力值
        self.stats = data.get("stats", {})
        
        # 其他属性
        self.friendship = data.get("friendship", 0)
        self.met_date = data.get("met_date", [])
        self.met_location = data.get("met_location", 0)
        
        # 唯一标识符
        self.pid = data.get("pid", 0)
        self.tid16 = data.get("tid16", 0)
        self.sid16 = data.get("sid16", 0)
        self.index = data.get("index", 0)
        self.offset = data.get("offset", 0)
        self.ec = data.get("ec", 0)
        
        # 宝可梦名称（从ID映射获取）
        self.name = self._get_pokemon_name()
        
        # 如果没有昵称，使用宝可梦名称
        if not self.nickname:
            self.nickname = self.name
    
    def _get_pokemon_name(self):
        """根据species ID获取宝可梦名称"""
        try:
            # 加载宝可梦ID和名称映射
            id_name_map = safe_load_file("pokemon_internal_id_name.json", "json")
            if id_name_map:
                species_id = str(self.species)
                return id_name_map.get(species_id, f"未知宝可梦({species_id})")
            else:
                return f"未知宝可梦({self.species})"
        except Exception as e:
            print(f"获取宝可梦名称时出错: {e}")
            return f"未知宝可梦({self.species})"
    
    def get_position_string(self):
        """获取宝可梦位置的字符串表示"""
        if not self.position:
            return "未知位置"
        
        pos_type = self.position.get("type", "")
        pos_index = self.position.get("index", 0)
        
        if pos_type == "team":
            return f"队伍位置 {pos_index + 1}"
        elif pos_type == "box":
            box_num = self.position.get("box", 1)
            slot_num = pos_index + 1
            return f"盒子 {box_num} 位置 {slot_num}"
        else:
            return "未知位置"
    
    def is_in_team(self):
        """检查宝可梦是否在队伍中"""
        return self.position.get("type") == "team"
    
    def is_in_box(self):
        """检查宝可梦是否在盒子中"""
        return self.position.get("type") == "box"
    
    def get_box_number(self):
        """获取宝可梦所在的盒子编号"""
        if self.is_in_box():
            return self.position.get("box", 1)
        return None
    
    def get_slot_index(self):
        """获取宝可梦所在的槽位索引"""
        return self.position.get("index", 0)
    
    def equals(self, other):
        """
        判断两个宝可梦是否相同（基于昵称和种类ID）
        
        Args:
            other: 另一个宝可梦对象或字典
            
        Returns:
            bool: 如果相同返回True，否则返回False
        """
        if isinstance(other, Pokemon):
            return (self.nickname == other.nickname and 
                    self.species == other.species)
        elif isinstance(other, dict):
            return (self.nickname == other.get("nickname", "") and 
                    self.species == other.get("species", 0))
        return False
    
    def to_dict(self):
        """将宝可梦对象转换为字典"""
        result = {
            "name": self.name,
            "nickname": self.nickname,
            "species": self.species,
            "level": self.level,
            "position": self.position
        }
        
        # 将data字典中的所有属性直接添加到结果字典中
        if hasattr(self, 'data') and isinstance(self.data, dict):
            for key, value in self.data.items():
                result[key] = value
        
        return result
    
    def __str__(self):
        return f"{self.name} ({self.nickname})"
    
    def __repr__(self):
        return f"Pokemon(name='{self.name}', nickname='{self.nickname}', species={self.species}, position={self.position})"


class PokemonManager:
    """宝可梦管理器，负责加载和管理所有宝可梦数据"""
    
    def __init__(self, main_info_path=None):
        """初始化宝可梦管理器"""
        self.team = []  # 队伍中的宝可梦
        self.boxes = {}  # 盒子中的宝可梦，格式为 {box_key: [Pokemon]}
        self.all_pokemon = []  # 所有宝可梦的列表
        self.last_modified_time = 0  # 最后修改时间
        
        # 处理main_info_path，确保使用正确的配置目录
        if main_info_path is None:
            # 尝试使用file_manager.get_config_dir()获取正确的配置目录
            try:
                from file_manager import get_config_dir
                config_dir = get_config_dir()
                self.main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
            except ImportError:
                # 如果无法导入file_manager，使用默认路径
                self.main_info_path = "pokemon_main_info.json"
        else:
            self.main_info_path = main_info_path
    
    def load_pokemon_data(self):
        """从JSON文件加载宝可梦数据"""
        try:
            # 加载宝可梦主要信息
            main_info = safe_load_file(self.main_info_path, "json")
            if main_info is None:  # 文件不存在或无法解析
                # 不再打印警告信息，允许程序使用空数据继续运行
                main_info = {}  # 使用空字典作为默认值
            
            # 清空现有数据
            self.team = []
            self.boxes = {}
            self.all_pokemon = []
            
            # 处理队伍数据
            party_data = main_info.get("party", {})
            for i in range(1, 7):  # 队伍有6个位置
                pokemon_info = party_data.get(str(i))
                if pokemon_info and not pokemon_info.get("is_egg", False):
                    position = {"type": "team", "index": i - 1}
                    pokemon = Pokemon(pokemon_info, position)
                    self.team.append(pokemon)
                    self.all_pokemon.append(pokemon)
                else:
                    self.team.append(None)
            
            # 处理盒子数据
            box_data = main_info.get("box", {})
            for box_name, box_info in box_data.items():
                box_num = box_name.replace("box", "")
                box_key = f"box_{box_num}"
                self.boxes[box_key] = []
                
                for slot_num in range(1, 31):  # 每个盒子有30个位置
                    pokemon_info = box_info.get(str(slot_num))
                    if pokemon_info and not pokemon_info.get("is_egg", False):
                        position = {"type": "box", "box": int(box_num), "index": slot_num - 1}
                        pokemon = Pokemon(pokemon_info, position)
                        self.boxes[box_key].append(pokemon)
                        self.all_pokemon.append(pokemon)
                    else:
                        self.boxes[box_key].append(None)
            
            # 更新最后修改时间
            import os
            if os.path.exists(self.main_info_path):
                self.last_modified_time = os.path.getmtime(self.main_info_path)
            else:
                self.last_modified_time = 0
            return True
                    
        except Exception as e:
            print(f"加载宝可梦数据时出错: {e}")
            return False
    
    def get_pokemon_by_nickname_and_species(self, nickname, species=None):
        """
        根据昵称和种类ID查找宝可梦
        
        Args:
            nickname: 宝可梦昵称
            species: 宝可梦种类ID（可选）
            
        Returns:
            Pokemon: 找到的宝可梦对象，如果没找到返回None
        """
        for pokemon in self.all_pokemon:
            if pokemon.nickname == nickname:
                if species is None or pokemon.species == species:
                    return pokemon
        return None
    
    def get_team_pokemon(self):
        """获取队伍中的所有宝可梦（过滤掉空槽位）"""
        return [p for p in self.team if p is not None]
    
    def get_box_pokemon(self, box_key):
        """
        获取指定盒子中的所有宝可梦（过滤掉空槽位）
        
        Args:
            box_key: 盒子键名，如"box_1"
            
        Returns:
            list: 宝可梦对象列表
        """
        if box_key in self.boxes:
            return [p for p in self.boxes[box_key] if p is not None]
        return []
    
    def get_all_available_pokemon(self, disabled_pokemon=None, drawn_pokemon=None):
        """
        获取所有可用的宝可梦（过滤掉禁用和已抽取的宝可梦）
        
        Args:
            disabled_pokemon: 禁用的宝可梦列表
            drawn_pokemon: 已抽取的宝可梦列表
            
        Returns:
            list: 可用的宝可梦对象列表
        """
        disabled_pokemon = disabled_pokemon or []
        drawn_pokemon = drawn_pokemon or []
        
        available_pokemon = []
        
        for pokemon in self.all_pokemon:
            # 检查是否被禁用
            is_disabled = False
            for disabled_p in disabled_pokemon:
                if pokemon.equals(disabled_p):
                    is_disabled = True
                    break
            
            # 检查是否已被抽取
            is_drawn = False
            for drawn_p in drawn_pokemon:
                if pokemon.equals(drawn_p):
                    is_drawn = True
                    break
            
            if not is_disabled and not is_drawn:
                available_pokemon.append(pokemon)
        
        return available_pokemon
    
    def refresh_data(self):
        """强制刷新数据"""
        self.last_modified_time = 0
        # 确保使用正确的配置目录
        if self.main_info_path == "pokemon_main_info.json":
            try:
                from file_manager import get_config_dir
                config_dir = get_config_dir()
                self.main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
            except ImportError:
                # 如果无法导入file_manager，使用默认路径
                pass
        return self.load_pokemon_data()
    
    def get_pokemon_list(self, location_id):
        """
        获取指定位置的宝可梦列表
        
        Args:
            location_id: 位置ID，0表示队伍，1-32表示盒子
            
        Returns:
            list: 宝可梦对象列表
        """
        if location_id == 0:
            # 队伍位置
            return self.get_team_pokemon()
        elif 1 <= location_id <= 32:
            # 盒子位置
            box_index = location_id - 1
            box_key = f"box_{box_index + 1}"
            return self.get_box_pokemon(box_key)
        
        return []
    
    def get_all_box_pokemon(self):
        """
        获取所有盒子中的宝可梦
        
        Returns:
            dict: 包含所有盒子宝可梦的字典，格式为 {box_key: [Pokemon]}
        """
        all_boxes = {}
        for box_key in self.boxes:
            all_boxes[box_key] = self.get_box_pokemon(box_key)
        return all_boxes
    
    def get_team_data(self):
        """
        获取队伍数据
        
        Returns:
            list: 队伍中的宝可梦列表
        """
        return self.team
    
    def get_all_boxes_data(self):
        """
        获取所有盒子数据
        
        Returns:
            dict: 包含所有盒子宝可梦的字典，格式为 {box_key: [Pokemon]}
        """
        return self.boxes


# 创建全局宝可梦管理器实例
pokemon_manager = PokemonManager()