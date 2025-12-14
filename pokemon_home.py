import tkinter as tk
from tkinter import ttk
import json
import os

from utils.path_resolver import get_main_file_path as _get_main_file_path_setting
from tkinter import messagebox
from pokemon_class import PokemonManager
from core.static_data import nature_map, nature_effect_map

try:
    from file_manager import safe_load_file
except ImportError:
    safe_load_file = None
    print("警告: 无法导入file_manager模块，某些功能可能不可用")

def setup_pokemon_home(parent):
    """设置宝可梦之家界面"""
    # 创建宝可梦之家实例
    pokemon_home = PokemonHome(parent)
    return pokemon_home

class PokemonHome:
    def __init__(self, parent):
        self.parent = parent
        self.main_file_path = ""  # 暂时为空，后续可以添加获取main文件路径的逻辑
        self.config = {}  # 暂时为空字典
        self.current_box = 1
        self.total_boxes = 32
        self.pokemon_data = {}  # 存储从main文件中读取的宝可梦数据
        self.team_data = []  # 存储队伍宝可梦数据
        self.box_data = {}  # 存储盒子宝可梦数据
        self.last_modified_time = 0  # 记录json文件最后修改时间
        self.selected_pokemon = []  # 存储选中的宝可梦列表
        
        # 设置高亮样式
        style = ttk.Style()
        style.configure("Highlighted.TFrame", background="#90EE90")
        style.configure("Selected.TFrame", background="#00FF00")
        
        # 创建主框架
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建标题
        self.title_label = ttk.Label(self.main_frame, text="宝可梦之家", font=("宋体", 16, "bold"))
        self.title_label.pack(pady=10)
        
        # 创建内容区域
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧队伍区域
        self.team_frame = ttk.LabelFrame(self.content_frame, text="队伍")
        self.team_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 创建队伍格子
        self.team_slots = []
        for i in range(6):
            slot_frame = ttk.Frame(self.team_frame, width=150, height=100, relief=tk.RIDGE, borderwidth=2)
            slot_frame.pack(padx=5, pady=5)
            slot_frame.pack_propagate(False)
            
            slot_label = ttk.Label(slot_frame, text="空", justify=tk.CENTER)
            slot_label.pack(expand=True)
            
            # 绑定点击事件和鼠标悬停事件
            slot_frame.bind("<Button-1>", lambda e, idx=i: self.on_team_slot_click(idx))
            slot_label.bind("<Button-1>", lambda e, idx=i: self.on_team_slot_click(idx))
            slot_frame.bind("<Enter>", lambda e, idx=i: self.on_slot_enter(idx, 'team'))
            slot_frame.bind("<Leave>", lambda e, idx=i: self.on_slot_leave(idx, 'team'))
            slot_label.bind("<Enter>", lambda e, idx=i: self.on_slot_enter(idx, 'team'))
            slot_label.bind("<Leave>", lambda e, idx=i: self.on_slot_leave(idx, 'team'))
            
            self.team_slots.append((slot_frame, slot_label))
        
        # 创建右侧盒子区域
        self.box_frame = ttk.LabelFrame(self.content_frame, text="盒子")
        self.box_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建盒子导航
        self.nav_frame = ttk.Frame(self.box_frame)
        self.nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 上一个盒子按钮
        self.prev_button = ttk.Button(self.nav_frame, text="<<", command=self.prev_box)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        # 盒子选择下拉列表
        self.box_var = tk.StringVar(value=f"盒子 {self.current_box}")
        self.box_selector = ttk.Combobox(self.nav_frame, textvariable=self.box_var, state="readonly", width=10)
        self.box_selector['values'] = [f"盒子 {i}" for i in range(1, self.total_boxes + 1)]
        self.box_selector.pack(side=tk.LEFT, padx=5)
        self.box_selector.bind("<<ComboboxSelected>>", self.on_box_selected)
        
        # 下一个盒子按钮
        self.next_button = ttk.Button(self.nav_frame, text=">>", command=self.next_box)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮
        self.refresh_button = ttk.Button(self.nav_frame, text="刷新", command=self.refresh_main_data)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # 创建盒子内容区域
        self.box_content_frame = ttk.Frame(self.box_frame)
        self.box_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建盒子格子
        self.box_slots = []
        for row in range(5):
            row_slots = []
            row_frame = ttk.Frame(self.box_content_frame)
            row_frame.pack(fill=tk.BOTH, expand=True)
            
            for col in range(6):
                slot_frame = ttk.Frame(row_frame, width=120, height=80, relief=tk.RIDGE, borderwidth=2)
                slot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
                slot_frame.pack_propagate(False)
                
                slot_label = ttk.Label(slot_frame, text="空", justify=tk.CENTER)
                slot_label.pack(expand=True)
                
                # 绑定点击事件和鼠标悬停事件
                slot_index = row * 6 + col
                slot_frame.bind("<Button-1>", lambda e, idx=slot_index: self.on_box_slot_click(idx))
                slot_label.bind("<Button-1>", lambda e, idx=slot_index: self.on_box_slot_click(idx))
                slot_frame.bind("<Enter>", lambda e, idx=slot_index: self.on_slot_enter(idx, 'box'))
                slot_frame.bind("<Leave>", lambda e, idx=slot_index: self.on_slot_leave(idx, 'box'))
                slot_label.bind("<Enter>", lambda e, idx=slot_index: self.on_slot_enter(idx, 'box'))
                slot_label.bind("<Leave>", lambda e, idx=slot_index: self.on_slot_leave(idx, 'box'))
                
                row_slots.append((slot_frame, slot_label))
            
            self.box_slots.append(row_slots)
        
        # 加载宝可梦数据
        self.load_pokemon_data()
        
        # 更新显示
        self.update_display()
    
    def load_pokemon_data(self):
        """从main文件中加载宝可梦数据"""
        try:
            # 使用PokemonManager加载宝可梦数据
            if not hasattr(self, 'pokemon_manager'):
                # 使用file_manager.get_config_dir()获取正确的配置目录
                try:
                    from file_manager import get_config_dir
                    config_dir = get_config_dir()
                    main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
                except ImportError:
                    # 如果无法导入file_manager，使用默认路径
                    main_info_path = "pokemon_main_info.json"
                
                self.pokemon_manager = PokemonManager(main_info_path)
            
            # 加载宝可梦数据
            success = self.pokemon_manager.load_pokemon_data()
            # 不再检查success，允许程序使用空数据继续运行
            
            # 获取队伍和盒子数据
            self.team_data = self.pokemon_manager.get_team_pokemon()
            self.box_data = {}
            
            # 获取所有盒子数据
            for i in range(1, 33):  # 32个盒子
                box_key = f"box_{i}"
                self.box_data[box_key] = self.pokemon_manager.get_box_pokemon(box_key)
            
            # 更新最后修改时间
            self.last_modified_time = self.pokemon_manager.last_modified_time
                    
        except Exception as e:
            messagebox.showerror("错误", f"加载宝可梦数据时出错: {str(e)}")
    
    def update_display(self):
        """更新队伍和盒子的显示"""
        # 更新队伍显示
        for i, (frame, label) in enumerate(self.team_slots):
            if i < len(self.team_data):
                pokemon = self.team_data[i]
                # 检查pokemon是Pokemon对象还是字典
                if hasattr(pokemon, 'name') and hasattr(pokemon, 'nickname'):
                    # 是Pokemon对象
                    name = pokemon.name
                    nickname = pokemon.nickname
                else:
                    # 是字典对象
                    name = pokemon.get('name', '')
                    nickname = pokemon.get('nickname', '')
                
                # 使用HTML样式的文本，让昵称变成蓝色并带下划线，表示可点击
                label.config(text=f"{name}\n{nickname}", foreground="blue")
            else:
                label.config(text="", foreground="black")
        
        # 更新盒子显示
        box_key = f"box_{self.current_box}"
        box_pokemon = self.box_data.get(box_key, [])
        
        for row in range(5):
            for col in range(6):
                index = row * 6 + col
                frame, label = self.box_slots[row][col]
                
                if index < len(box_pokemon):
                    pokemon = box_pokemon[index]
                    # 检查pokemon是Pokemon对象还是字典
                    if hasattr(pokemon, 'name') and hasattr(pokemon, 'nickname'):
                        # 是Pokemon对象
                        name = pokemon.name
                        nickname = pokemon.nickname
                    else:
                        # 是字典对象
                        name = pokemon.get('name', '')
                        nickname = pokemon.get('nickname', '')
                    
                    # 使用HTML样式的文本，让昵称变成蓝色并带下划线，表示可点击
                    label.config(text=f"{name}\n{nickname}", foreground="blue")
                else:
                    label.config(text="", foreground="black")
    
    def prev_box(self):
        """切换到上一个盒子"""
        if self.current_box > 1:
            self.current_box -= 1
        else:
            # 如果当前是盒子1，则切换到盒子32
            self.current_box = self.total_boxes
        self.box_var.set(f"盒子 {self.current_box}")
        # 重新应用选中宝可梦的高亮状态
        self.reapply_highlights()
        self.update_display()
    
    def next_box(self):
        """切换到下一个盒子"""
        if self.current_box < self.total_boxes:
            self.current_box += 1
        else:
            # 如果当前是盒子32，则切换到盒子1
            self.current_box = 1
        self.box_var.set(f"盒子 {self.current_box}")
        # 重新应用选中宝可梦的高亮状态
        self.reapply_highlights()
        self.update_display()
    
    def on_box_selected(self, event):
        """通过下拉列表选择盒子"""
        box_str = self.box_var.get()
        self.current_box = int(box_str.split()[1])
        # 重新应用选中宝可梦的高亮状态
        self.reapply_highlights()
        self.update_display()
    
    def on_team_slot_click(self, index):
        """点击队伍格子时的处理"""
        if index < len(self.team_data):
            # 显示宝可梦具体信息
            self.show_pokemon_info(self.team_data[index])
        else:
            # 空格子，可以添加宝可梦
            pass
    
    def on_box_slot_click(self, index):
        """点击盒子格子时的处理"""
        box_key = f"box_{self.current_box}"
        box_pokemon = self.box_data.get(box_key, [])
        
        if index < len(box_pokemon):
            # 显示宝可梦具体信息
            self.show_pokemon_info(box_pokemon[index])
        else:
            # 空格子，可以添加宝可梦
            pass
    
    def on_slot_enter(self, index, slot_type):
        """鼠标进入格子时的处理"""
        if slot_type == 'team':
            if index < len(self.team_data):
                # 如果有宝可梦，设置手型光标
                self.team_slots[index][0].config(cursor="hand2")
                self.team_slots[index][1].config(cursor="hand2")
        else:  # slot_type == 'box'
            box_key = f"box_{self.current_box}"
            box_pokemon = self.box_data.get(box_key, [])
            if index < len(box_pokemon):
                # 如果有宝可梦，设置手型光标
                row = index // 6
                col = index % 6
                self.box_slots[row][col][0].config(cursor="hand2")
                self.box_slots[row][col][1].config(cursor="hand2")
    
    def on_slot_leave(self, index, slot_type):
        """鼠标离开格子时的处理"""
        if slot_type == 'team':
            # 恢复默认光标
            self.team_slots[index][0].config(cursor="")
            self.team_slots[index][1].config(cursor="")
        else:  # slot_type == 'box'
            # 恢复默认光标
            row = index // 6
            col = index % 6
            self.box_slots[row][col][0].config(cursor="")
            self.box_slots[row][col][1].config(cursor="")
    
    def show_pokemon_info(self, pokemon):
        """显示宝可梦具体信息"""
        info_window = tk.Toplevel(self.parent)
        info_window.title("宝可梦具体信息")
        info_window.geometry("666x520")
        
        # 使窗口居中显示
        info_window.update_idletasks()  # 更新窗口以确保正确的尺寸
        width = info_window.winfo_width()
        height = info_window.winfo_height()
        x = (info_window.winfo_screenwidth() // 2) - (width // 2)
        y = (info_window.winfo_screenheight() // 2) - (height // 2)
        info_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建信息框架
        info_frame = ttk.Frame(info_window, padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分栏框架
        left_frame = ttk.Frame(info_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = ttk.Frame(info_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 加载映射数据
        try:
            # 获取配置目录路径
            from file_manager import get_config_dir
            config_dir = get_config_dir()
            
            # 初始化所有映射为空字典
            ability_map = {}
            ability_explanation_map = {}
            move_map = {}
            move_explanation_map = {}
            item_map = {}
            location_map = {}
            
            # 尝试加载每个映射文件，如果失败则使用空字典
            try:
                ability_data = safe_load_file('pokemon_ability.json', 'json')
                if ability_data and isinstance(ability_data, dict) and 'ability_map' in ability_data:
                        ability_map = ability_data['ability_map']
            except Exception:
                ability_map = {}
            
            try:
                ability_explanation_data = safe_load_file('pokemon_ability_explanation.json', 'json')
                if ability_explanation_data and isinstance(ability_explanation_data, dict) and 'ability_explanation_map' in ability_explanation_data:
                        ability_explanation_map = ability_explanation_data['ability_explanation_map']
            except Exception:
                ability_explanation_map = {}
            
            try:
                move_data = safe_load_file('pokemon_move.json', 'json')
                if move_data and isinstance(move_data, dict) and 'move_map' in move_data:
                        move_map = move_data['move_map']
            except Exception:
                move_map = {}
            
            try:
                move_explanation_data = safe_load_file('pokemon_move_explanation.json', 'json')
                if move_explanation_data and isinstance(move_explanation_data, dict) and 'move_explanation_map' in move_explanation_data:
                        move_explanation_map = move_explanation_data['move_explanation_map']
            except Exception:
                move_explanation_map = {}
            
            try:
                item_data = safe_load_file('pokemon_item_name.json', 'json')
                if item_data and isinstance(item_data, dict):
                    item_map = item_data
            except Exception:
                item_map = {}
            
            try:
                location_data = safe_load_file('pokemon_location.json', 'json')
                if location_data and isinstance(location_data, dict) and 'location_map' in location_data:
                    location_map = location_data['location_map']
            except Exception:
                location_map = {}
        except Exception as e:
            # 只有在获取配置目录路径时出错才显示错误并返回
            messagebox.showerror("错误", f"获取配置目录时出错: {str(e)}")
            return
        
        # 检查pokemon是Pokemon对象还是字典
        if hasattr(pokemon, 'name') and hasattr(pokemon, 'nickname'):
            # 是Pokemon对象
            data = pokemon.to_dict()  # 将Pokemon对象转换为字典
            name = data.get('name', '')
            nickname = data.get('nickname', '')
        else:
            # 是字典对象
            data = pokemon
            name = data.get('name', '')
            nickname = data.get('nickname', '')
        
        # 左侧显示基本信息
        # 显示宝可梦名称和昵称
        name_frame = ttk.Frame(left_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text="物种名:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(name_frame, text=name, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(name_frame, text="昵称:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(name_frame, text=nickname, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 等级
        level_frame = ttk.Frame(left_frame)
        level_frame.pack(fill=tk.X, pady=5)
        ttk.Label(level_frame, text="等级:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(level_frame, text=str(data.get("level", "未知")), font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 性格
        nature_frame = ttk.Frame(left_frame)
        nature_frame.pack(fill=tk.X, pady=5)
        ttk.Label(nature_frame, text="性格:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        # 获取性格名称
        nature_value = data.get("nature_value", 0)
        from Pokemon import nature_map
        nature_name = nature_map.get(nature_value, "未知")
        ttk.Label(nature_frame, text=nature_name, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 特性
        ability_frame = ttk.Frame(left_frame)
        ability_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ability_frame, text="特性:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        ability_id = data.get('ability_id', 0)
        ability_num = data.get('ability_num', '未知')
        ability_name = ability_map.get(str(ability_id), "未知")
        
        # 创建可点击的特性标签（无下划线）
        ability_label = ttk.Label(ability_frame, text=f"{ability_name} ({ability_num})", 
                                 font=("宋体", 12), foreground="blue", cursor="hand2")
        ability_label.pack(side=tk.LEFT, padx=5)
        ability_label.bind("<Button-1>", lambda e: self.show_ability_explanation(ability_id, ability_name, ability_explanation_map))
        
        # 持有物
        item_frame = ttk.Frame(left_frame)
        item_frame.pack(fill=tk.X, pady=5)
        ttk.Label(item_frame, text="持有物:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        held_item_id = data.get("held_item", 0)
        item_name = item_map.get(str(held_item_id), "无")
        ttk.Label(item_frame, text=item_name, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 亲密度
        friendship_frame = ttk.Frame(left_frame)
        friendship_frame.pack(fill=tk.X, pady=5)
        ttk.Label(friendship_frame, text="亲密度:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(friendship_frame, text=str(data.get("friendship", "未知")), font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 是否闪光
        shiny_frame = ttk.Frame(left_frame)
        shiny_frame.pack(fill=tk.X, pady=5)
        ttk.Label(shiny_frame, text="闪光:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        shiny_text = "是" if data.get("shiny", False) else "否"
        ttk.Label(shiny_frame, text=shiny_text, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 相遇地点
        location_frame = ttk.Frame(left_frame)
        location_frame.pack(fill=tk.X, pady=5)
        ttk.Label(location_frame, text="相遇地点:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        met_location = data.get("met_location", 0)
        location_name = location_map.get(str(met_location), "未知")
        ttk.Label(location_frame, text=location_name, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 相遇年月日
        met_date_frame = ttk.Frame(left_frame)
        met_date_frame.pack(fill=tk.X, pady=5)
        ttk.Label(met_date_frame, text="相遇日期:", font=("宋体", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        met_date = data.get("met_date", [])
        if len(met_date) == 3:
            met_year, met_month, met_day = met_date
            met_date_str = f"{met_year}年{met_month}月{met_day}日"
        else:
            met_date_str = "未知"
        ttk.Label(met_date_frame, text=met_date_str, font=("宋体", 12)).pack(side=tk.LEFT, padx=5)
        
        # 右侧显示能力值、个体值和努力值
        stats_frame = ttk.LabelFrame(right_frame, text="能力值", padding="5")
        stats_frame.pack(fill=tk.X, pady=5)
        
        stats = data.get("stats", {})
        ivs = data.get("ivs", {})
        evs = data.get("evs", {})
        
        # 获取当前血量和最大血量
        current_hp = stats.get("hp_current", stats.get("hp", 0))
        max_hp = stats.get("hp_max", stats.get("hp", 1))
        
        nature_value = data.get("nature_value", 0)
        nature_name = nature_map.get(nature_value, "未知")
        increased_stat, decreased_stat = nature_effect_map.get(nature_name, ("", ""))
        
        # 创建表头
        header_frame = ttk.Frame(stats_frame)
        header_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(header_frame, text="", font=("宋体", 10, "bold"), width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="个体", font=("宋体", 10, "bold"), width=9).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="努力", font=("宋体", 10, "bold"), width=11).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="能力值", font=("宋体", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)
        
        stats_labels = [
            ("体力", "hp"),
            ("攻击", "atk"),
            ("防御", "def"),
            ("特攻", "spa"),
            ("特防", "spd"),
            ("速度", "spe")
        ]
        
        # 计算个体值和努力值的总和
        total_iv = 0
        total_ev = 0
        
        for stat_name, stat_key in stats_labels:
            stat_frame = ttk.Frame(stats_frame)
            stat_frame.pack(fill=tk.X, pady=2)
            
            # 根据性格效果设置能力值名称的颜色
            stat_color = "black"
            if stat_name == increased_stat:
                stat_color = "green"  # 增加的能力值用绿色
            elif stat_name == decreased_stat:
                stat_color = "red"    # 减少的能力值用红色
            
            ttk.Label(stat_frame, text=f"{stat_name}:", font=("宋体", 10, "bold"), width=8, foreground=stat_color).pack(side=tk.LEFT, padx=5)
            
            # 显示个体值
            iv_value = ivs.get(stat_key, 0)
            total_iv += iv_value
            ttk.Label(stat_frame, text=str(iv_value), font=("宋体", 10), width=10).pack(side=tk.LEFT, padx=5)
            
            # 显示努力值
            ev_value = evs.get(stat_key, 0)
            total_ev += ev_value
            ttk.Label(stat_frame, text=str(ev_value), font=("宋体", 10), width=12).pack(side=tk.LEFT, padx=5)
            
            # 显示能力值（当前血量/最大血量格式（仅对HP））
            if stat_key == "hp":
                stat_value = f"{current_hp}/{max_hp}"
            else:
                stat_value = str(stats.get(stat_key, 0))
            
            ttk.Label(stat_frame, text=stat_value, font=("宋体", 10), width=12).pack(side=tk.LEFT, padx=5)
        
        # 显示总和行
        total_frame = ttk.Frame(stats_frame)
        total_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(total_frame, text="总和:", font=("宋体", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(total_frame, text=f"{total_iv}({total_iv/186*100:.1f}%)", font=("宋体", 10), width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(total_frame, text=f"{total_ev}({total_ev/510*100:.1f}%)", font=("宋体", 10), width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(total_frame, text="", font=("宋体", 10), width=12).pack(side=tk.LEFT, padx=5)
        
        # 显示技能（2×2网格排列）
        moves_frame = ttk.LabelFrame(right_frame, text="技能", padding="5")
        moves_frame.pack(fill=tk.X, pady=10)
        
        # 直接从data中获取move1至move4
        move_keys = ["move1", "move2", "move3", "move4"]
        
        # 创建2×2网格布局
        for row in range(2):
            row_frame = ttk.Frame(moves_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            for col in range(2):
                # 计算当前技能索引
                move_index = row * 2 + col
                if move_index < len(move_keys):
                    move_key = move_keys[move_index]
                    
                    # 创建左侧和右侧框架，实现两列布局
                    if col == 0:
                        # 左侧列
                        left_col_frame = ttk.Frame(row_frame)
                        left_col_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
                        
                        # 从data的moves字典中获取技能ID
                        moves_data = data.get("moves", {})
                        move_id = moves_data.get(move_key, 0)
                        
                        if move_id > 0:
                            move_name = move_map.get(str(move_id), "未知")
                            
                            # 创建可点击的技能标签（无下划线）
                            move_label = ttk.Label(left_col_frame, text=f"{move_index+1}. {move_name}", 
                                                 font=("宋体", 11), foreground="blue", cursor="hand2")
                            move_label.pack(anchor="w")
                            move_label.bind("<Button-1>", lambda e, mid=move_id, mname=move_name, memap=move_explanation_map: self.show_move_explanation(mid, mname, memap))
                        else:
                            ttk.Label(left_col_frame, text=f"{move_index+1}. 无", font=("宋体", 11)).pack(anchor="w")
                    else:
                        # 右侧列
                        right_col_frame = ttk.Frame(row_frame)
                        right_col_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
                        
                        # 从data的moves字典中获取技能ID
                        moves_data = data.get("moves", {})
                        move_id = moves_data.get(move_key, 0)
                        
                        if move_id > 0:
                            move_name = move_map.get(str(move_id), "未知")
                            
                            # 创建可点击的技能标签（无下划线）
                            move_label = ttk.Label(right_col_frame, text=f"{move_index+1}. {move_name}", 
                                                 font=("宋体", 11), foreground="blue", cursor="hand2")
                            move_label.pack(anchor="w")
                            move_label.bind("<Button-1>", lambda e, mid=move_id, mname=move_name, memap=move_explanation_map: self.show_move_explanation(mid, mname, memap))
                        else:
                            ttk.Label(right_col_frame, text=f"{move_index+1}. 无", font=("宋体", 11)).pack(anchor="w")
        
        # 注释掉关闭按钮，因为窗口右上角已经有"X"按钮
        # close_button = ttk.Button(info_frame, text="关闭", command=info_window.destroy)
        # close_button.pack(pady=10)
    
    def show_ability_explanation(self, ability_id, ability_name, ability_explanation_map):
        """显示特性说明"""
        explanation_window = tk.Toplevel(self.parent)
        explanation_window.title(f"特性说明: {ability_name}")
        explanation_window.geometry("500x400")
        
        # 使窗口居中显示
        explanation_window.update_idletasks()
        width = explanation_window.winfo_width()
        height = explanation_window.winfo_height()
        x = (explanation_window.winfo_screenwidth() // 2) - (width // 2)
        y = (explanation_window.winfo_screenheight() // 2) - (height // 2)
        explanation_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建说明框架
        explanation_frame = ttk.Frame(explanation_window, padding="10")
        explanation_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取特性说明
        explanation = ability_explanation_map.get(str(ability_id), "暂无说明")
        
        # 显示特性名称
        name_label = ttk.Label(explanation_frame, text=f"特性: {ability_name}", font=("宋体", 12, "bold"))
        name_label.pack(pady=10)
        
        # 显示特性说明
        explanation_text = tk.Text(explanation_frame, wrap=tk.WORD, height=15, width=50, font=("宋体", 12))
        explanation_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置文本居中显示和行间距
        explanation_text.tag_configure("center", justify="center", spacing1=10, spacing2=10, spacing3=10)
        
        # 处理逗号分隔的内容，将其转换为多行显示（每个逗号换一行）
        if "，" in explanation or "," in explanation:
            # 将逗号替换为换行符
            formatted_explanation = explanation.replace("，", "\n").replace(",", "\n")
            explanation_text.insert(tk.END, formatted_explanation, "center")
        else:
            # 如果没有逗号，仍然居中显示
            explanation_text.insert(tk.END, explanation, "center")
            
        explanation_text.config(state=tk.DISABLED)
        
        # 添加垂直居中的功能
        def center_text_vertically(event=None):
            # 计算文本总高度
            total_lines = int(explanation_text.index('end-1c').split('.')[0])
            visible_lines = 15  # Text组件的高度
            
            # 如果文本行数少于可见行数，则垂直居中
            if total_lines < visible_lines:
                # 计算需要插入的空行数（上下各一半）
                empty_lines = (visible_lines - total_lines) // 2
                # 在开头插入空行
                explanation_text.insert('1.0', '\n' * empty_lines)
                explanation_text.see('1.0')  # 滚动到顶部
        
        # 绑定配置事件，在文本显示后执行垂直居中
        explanation_text.bind('<Configure>', center_text_vertically)
        
        # 关闭按钮
        close_button = ttk.Button(explanation_frame, text="关闭", command=explanation_window.destroy)
        close_button.pack(pady=10)
    
    def show_move_explanation(self, move_id, move_name, move_explanation_map):
        """显示技能说明"""
        explanation_window = tk.Toplevel(self.parent)
        explanation_window.title(f"技能说明: {move_name}")
        explanation_window.geometry("500x400")
        
        # 使窗口居中显示
        explanation_window.update_idletasks()
        width = explanation_window.winfo_width()
        height = explanation_window.winfo_height()
        x = (explanation_window.winfo_screenwidth() // 2) - (width // 2)
        y = (explanation_window.winfo_screenheight() // 2) - (height // 2)
        explanation_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建说明框架
        explanation_frame = ttk.Frame(explanation_window, padding="10")
        explanation_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取技能说明
        move_info = move_explanation_map.get(str(move_id), "暂无说明")
        
        # 显示技能名称
        name_label = ttk.Label(explanation_frame, text=f"技能: {move_name}", font=("宋体", 12, "bold"))
        name_label.pack(pady=10)
        
        # 显示技能说明
        explanation_text = tk.Text(explanation_frame, wrap=tk.WORD, height=15, width=50, font=("宋体", 12))
        explanation_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置文本居中显示
        explanation_text.tag_configure("center", justify="center")
        
        # 解析技能信息
        if "\n" in move_info:
            # 分离技能属性和描述
            parts = move_info.split("\n", 1)
            attributes_part = parts[0]
            description_part = parts[1] if len(parts) > 1 else ""
            
            # 解析属性部分
            if "--" in attributes_part:
                attributes = attributes_part.split("--")
                if len(attributes) >= 5:
                    # 第一部分：属性和类型
                    type_info = f"{attributes[0]}    {attributes[1]}"
                    
                    # 第二部分：威力、命中、PP
                    power_info = f"威力：{attributes[2]}\n命中：{attributes[3]}\nPP：{attributes[4]}"
                    
                    # 第三部分：描述（按逗号和句号换行）
                    if "，" in description_part or "," in description_part or "。" in description_part or "." in description_part:
                        formatted_description = description_part.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                    else:
                        formatted_description = description_part
                    
                    # 插入三部分内容，每部分之间用空行分隔
                    explanation_text.insert(tk.END, type_info, "center")
                    explanation_text.insert(tk.END, "\n\n")
                    explanation_text.insert(tk.END, power_info, "center")
                    explanation_text.insert(tk.END, "\n\n")
                    explanation_text.insert(tk.END, formatted_description, "center")
                else:
                    # 如果属性格式不正确，直接显示原始信息
                    if "，" in move_info or "," in move_info or "。" in move_info or "." in move_info:
                        formatted_info = move_info.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                        explanation_text.insert(tk.END, formatted_info, "center")
                    else:
                        explanation_text.insert(tk.END, move_info, "center")
            else:
                # 如果没有属性分隔符，直接显示原始信息
                if "，" in move_info or "," in move_info or "。" in move_info or "." in move_info:
                    formatted_info = move_info.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                    explanation_text.insert(tk.END, formatted_info, "center")
                else:
                    explanation_text.insert(tk.END, move_info, "center")
        else:
            # 如果没有换行符，直接显示原始信息
            if "，" in move_info or "," in move_info or "。" in move_info or "." in move_info:
                formatted_info = move_info.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                explanation_text.insert(tk.END, formatted_info, "center")
            else:
                explanation_text.insert(tk.END, move_info, "center")
            
        explanation_text.config(state=tk.DISABLED)
        
        # 关闭按钮
        close_button = ttk.Button(explanation_frame, text="关闭", command=explanation_window.destroy)
        close_button.pack(pady=10)
    
    def refresh_data(self):
        """刷新宝可梦数据"""
        # 强制重新加载数据
        if hasattr(self, 'pokemon_manager'):
            self.pokemon_manager.refresh_data()
        else:
            # 使用file_manager.get_config_dir()获取正确的配置目录
            try:
                from file_manager import get_config_dir
                config_dir = get_config_dir()
                main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
            except ImportError:
                # 如果无法导入file_manager，使用默认路径
                main_info_path = os.path.join("config", "pokemon_main_info.json")
            
            self.pokemon_manager = PokemonManager(main_info_path)
            self.pokemon_manager.load_pokemon_data()
        
        # 重新加载本地数据
        self.load_pokemon_data()
        self.update_display()
        
        # 通知CCB刷新数据
        self.notify_ccb_refresh()
        
        messagebox.showinfo("提示", "宝可梦数据已刷新")
    
    def notify_ccb_refresh(self):
        """通知CCB刷新数据"""
        try:
            # 导入ccb模块
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.append(current_dir)
            
            import ccb
            
            # 使用全局ccb_instance变量来访问CCB实例
            if hasattr(ccb, 'ccb_instance') and ccb.ccb_instance:
                # 检查CCB实例是否有效
                if hasattr(ccb.ccb_instance, 'parent') and ccb.ccb_instance.parent:
                    try:
                        # 检查应用程序是否已经被销毁
                        if not ccb.ccb_instance.parent.winfo_exists():
                            print("应用程序已销毁，跳过CCB刷新")
                            return
                            
                        # 检查CCB标签页是否可见（避免在隐藏状态下操作UI元素）
                        if hasattr(ccb.ccb_instance, 'main_frame'):
                            try:
                                is_mapped = ccb.ccb_instance.main_frame.winfo_ismapped()
                                if is_mapped:
                                    # 使用after方法在主线程中安全调用，避免Tkinter命令错误
                                    def safe_load_pokemon_data():
                                        try:
                                            # 确保CCB实例也有PokemonManager实例
                                            if not hasattr(ccb.ccb_instance, 'pokemon_manager'):
                                                # 使用file_manager.get_config_dir()获取正确的配置目录
                                                try:
                                                    from file_manager import get_config_dir
                                                    config_dir = get_config_dir()
                                                    main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
                                                except ImportError:
                                                    # 如果无法导入file_manager，使用默认路径
                                                    main_info_path = os.path.join("config", "pokemon_main_info.json")
                                                ccb.ccb_instance.pokemon_manager = PokemonManager(main_info_path)
                                            
                                            # 刷新CCB的PokemonManager数据
                                            ccb.ccb_instance.pokemon_manager.refresh_data()
                                            
                                            # 重新加载CCB的宝可梦数据
                                            ccb.ccb_instance.load_pokemon_data()
                                            print("CCB数据已刷新!")
                                        except Exception as e:
                                            print(f"CCB数据刷新时出错: {str(e)}")
                                    
                                    # 延迟100毫秒执行，确保UI操作安全
                                    self.parent.after(100, safe_load_pokemon_data)
                                else:
                                    # CCB标签页未显示时，只刷新数据但不更新UI，避免Tkinter错误
                                    print("CCB标签页未显示，仅刷新数据不更新UI")
                                    # 直接重新加载宝可梦数据到内存，但不操作UI元素
                                    if not hasattr(ccb.ccb_instance, 'pokemon_manager'):
                                        # 使用file_manager.get_config_dir()获取正确的配置目录
                                        try:
                                            from file_manager import get_config_dir
                                            config_dir = get_config_dir()
                                            main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
                                        except ImportError:
                                            # 如果无法导入file_manager，使用默认路径
                                            main_info_path = os.path.join("config", "pokemon_main_info.json")
                                        ccb.ccb_instance.pokemon_manager = PokemonManager(main_info_path)
                                    ccb.ccb_instance.pokemon_manager.refresh_data()
                                    ccb.ccb_instance._load_pokemon_data_without_ui()
                            except Exception as e:
                                # 如果检查CCB标签页状态时出错，尝试只刷新数据不更新UI
                                print(f"检查CCB标签页状态时出错: {str(e)}，尝试仅刷新数据不更新UI")
                                if not hasattr(ccb.ccb_instance, 'pokemon_manager'):
                                    # 使用file_manager.get_config_dir()获取正确的配置目录
                                    try:
                                        from file_manager import get_config_dir
                                        config_dir = get_config_dir()
                                        main_info_path = os.path.join(config_dir, "pokemon_main_info.json")
                                    except ImportError:
                                        # 如果无法导入file_manager，使用默认路径
                                        main_info_path = os.path.join("config", "pokemon_main_info.json")
                                    ccb.ccb_instance.pokemon_manager = PokemonManager(main_info_path)
                                ccb.ccb_instance.pokemon_manager.refresh_data()
                                ccb.ccb_instance._load_pokemon_data_without_ui()
                        else:
                            # 如果没有main_frame属性，尝试只刷新数据不更新UI
                            print("CCB实例没有main_frame属性，尝试仅刷新数据不更新UI")
                            if not hasattr(ccb.ccb_instance, 'pokemon_manager'):
                                main_info_path = os.path.join("config", "pokemon_main_info.json")
                                ccb.ccb_instance.pokemon_manager = PokemonManager(main_info_path)
                            ccb.ccb_instance.pokemon_manager.refresh_data()
                            ccb.ccb_instance._load_pokemon_data_without_ui()
                    except Exception as e:
                        # 如果检查应用程序状态时出错，尝试只刷新数据不更新UI
                        print(f"检查应用程序状态时出错: {str(e)}，尝试仅刷新数据不更新UI")
                        if not hasattr(ccb.ccb_instance, 'pokemon_manager'):
                            main_info_path = os.path.join("config", "pokemon_main_info.json")
                            ccb.ccb_instance.pokemon_manager = PokemonManager(main_info_path)
                        ccb.ccb_instance.pokemon_manager.refresh_data()
                        ccb.ccb_instance._load_pokemon_data_without_ui()
                else:
                    print("CCB实例无效，跳过数据刷新")
            else:
                print("CCB实例不存在，跳过数据刷新")
        except Exception as e:
            print(f"通知CCB刷新数据时出错: {str(e)}")
            # 不显示错误对话框，避免干扰用户
    
    def refresh_main_data(self):
        """刷新main数据并更新宝可梦之家"""
        try:
            # 获取main文件路径
            main_file_path = self.get_main_file_path()
            if not main_file_path:
                messagebox.showwarning("警告", "找不到main文件路径，请先在宝可梦工具中设置main文件路径")
                return
            
            # 调用Pokemon.py中的generate_json_from_main函数
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.append(current_dir)
            
            # 导入Pokemon模块
            from Pokemon import PokemonToolsApp
            
            # 使用after方法确保在主线程中执行UI操作
            def update_data():
                # 创建一个临时根窗口
                temp_root = tk.Tk()
                temp_root.withdraw()  # 隐藏窗口
                
                # 创建PokemonToolsApp实例
                app = PokemonToolsApp(temp_root)
                
                # 调用generate_json_from_main函数
                app.generate_json_from_main(main_file_path)
                
                # 销毁临时窗口
                temp_root.destroy()
                
                # 刷新宝可梦之家数据
                self.refresh_data()
            
            # 使用after方法在主线程中执行
            self.parent.after(100, update_data)
        except Exception as e:
            messagebox.showerror("错误", f"刷新main数据时出错: {str(e)}")
    
    def get_main_file_path(self):
        """获取main文件路径"""
        try:
            path = _get_main_file_path_setting()
            if path:
                return path
            config_path = os.path.join("config", "item_category_rules.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("main_file_path", "")
            return ""
        except Exception as e:
            print(f"获取main文件路径时出错: {str(e)}")
            return ""
    
    def show(self):
        """显示宝可梦之家页面"""
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建刷新按钮
        refresh_button = ttk.Button(self.main_frame, text="刷新数据", command=self.refresh_data)
        refresh_button.pack(pady=5)
        
        # 加载宝可梦数据
        self.load_pokemon_data()
        
        # 更新显示
        self.update_display()
    
    def hide(self):
        """隐藏宝可梦之家页面"""
        self.main_frame.pack_forget()
    
    def highlight_pokemon(self, pokemon):
        """高亮显示指定的宝可梦"""
        # 检查pokemon是Pokemon对象还是字典
        if hasattr(pokemon, 'nickname'):
            # 是Pokemon对象
            nickname = pokemon.nickname
        else:
            # 是字典对象
            nickname = pokemon.get("nickname", "")
        
        # 在队伍中查找并高亮
        for i, (slot_frame, slot_label) in enumerate(self.team_slots):
            if i < len(self.team_data):
                team_pokemon = self.team_data[i]
                # 检查team_pokemon是Pokemon对象还是字典
                team_nickname = team_pokemon.nickname if hasattr(team_pokemon, 'nickname') else team_pokemon.get("nickname", "")
                if team_nickname == nickname:
                    slot_frame.configure(style="Highlighted.TFrame")
                    return
        
        # 在当前盒子中查找并高亮
        box_key = f"box_{self.current_box}"
        if box_key in self.box_data:
            for row in range(5):
                for col in range(6):
                    slot_index = row * 6 + col
                    if slot_index < len(self.box_data[box_key]):
                        box_pokemon = self.box_data[box_key][slot_index]
                        # 检查box_pokemon是Pokemon对象还是字典
                        box_nickname = box_pokemon.nickname if hasattr(box_pokemon, 'nickname') else box_pokemon.get("nickname", "")
                        if box_nickname == nickname:
                            self.box_slots[row][col][0].configure(style="Highlighted.TFrame")
                            return
    
    def unhighlight_pokemon(self, pokemon):
        """取消高亮显示指定的宝可梦"""
        # 检查pokemon是Pokemon对象还是字典
        if hasattr(pokemon, 'nickname'):
            # 是Pokemon对象
            nickname = pokemon.nickname
        else:
            # 是字典对象
            nickname = pokemon.get("nickname", "")
        
        # 在队伍中查找并取消高亮
        for i, (slot_frame, slot_label) in enumerate(self.team_slots):
            if i < len(self.team_data):
                team_pokemon = self.team_data[i]
                # 检查team_pokemon是Pokemon对象还是字典
                team_nickname = team_pokemon.nickname if hasattr(team_pokemon, 'nickname') else team_pokemon.get("nickname", "")
                if team_nickname == nickname:
                    slot_frame.configure(style="TFrame")
                    return
        
        # 在当前盒子中查找并取消高亮
        box_key = f"box_{self.current_box}"
        if box_key in self.box_data:
            for row in range(5):
                for col in range(6):
                    slot_index = row * 6 + col
                    if slot_index < len(self.box_data[box_key]):
                        box_pokemon = self.box_data[box_key][slot_index]
                        # 检查box_pokemon是Pokemon对象还是字典
                        box_nickname = box_pokemon.nickname if hasattr(box_pokemon, 'nickname') else box_pokemon.get("nickname", "")
                        if box_nickname == nickname:
                            self.box_slots[row][col][0].configure(style="TFrame")
                            return
    
    def select_pokemon(self, pokemon):
        """选中指定的宝可梦（高亮显示）"""
        # 检查传入的是Pokemon对象还是字典
        if hasattr(pokemon, 'nickname') and hasattr(pokemon, 'species'):
            # 是Pokemon对象
            nickname = pokemon.nickname
            species = pokemon.species
            # 将宝可梦添加到选中列表（如果尚未选中）
            if not any(p.get('nickname') == nickname and p.get('species') == species for p in self.selected_pokemon):
                self.selected_pokemon.append({
                    'nickname': nickname,
                    'species': species,
                    'is_pokemon_object': True
                })
        else:
            # 是字典对象
            nickname = pokemon.get("nickname", "")
            species = pokemon.get("species", "")
            # 将宝可梦添加到选中列表（如果尚未选中）
            if not any(p.get('nickname') == nickname and p.get('species') == species for p in self.selected_pokemon):
                self.selected_pokemon.append({
                    'nickname': nickname,
                    'species': species,
                    'is_pokemon_object': False
                })
        
        # 在队伍中查找并高亮
        for i, (slot_frame, slot_label) in enumerate(self.team_slots):
            if i < len(self.team_data):
                team_pokemon = self.team_data[i]
                # 检查team_pokemon是Pokemon对象还是字典
                if hasattr(team_pokemon, 'nickname') and hasattr(team_pokemon, 'species'):
                    # 是Pokemon对象
                    team_nickname = team_pokemon.nickname
                    team_species = team_pokemon.species
                else:
                    # 是字典对象
                    team_nickname = team_pokemon.get("nickname", "")
                    team_species = team_pokemon.get("data", {}).get("species", "") if "data" in team_pokemon else ""
                
                # 使用昵称和种类ID双重匹配，提高准确性
                if (team_nickname == nickname and 
                    (not species or team_species == species)):
                    slot_frame.configure(style="Selected.TFrame")
                    return
        
        # 在当前盒子中查找并高亮
        box_key = f"box_{self.current_box}"
        if box_key in self.box_data:
            for row in range(5):
                for col in range(6):
                    slot_index = row * 6 + col
                    if slot_index < len(self.box_data[box_key]):
                        box_pokemon = self.box_data[box_key][slot_index]
                        # 检查box_pokemon是Pokemon对象还是字典
                        if hasattr(box_pokemon, 'nickname') and hasattr(box_pokemon, 'species'):
                            # 是Pokemon对象
                            box_nickname = box_pokemon.nickname
                            box_species = box_pokemon.species
                        else:
                            # 是字典对象
                            box_nickname = box_pokemon.get("nickname", "")
                            box_species = box_pokemon.get("data", {}).get("species", "") if "data" in box_pokemon else ""
                        
                        # 使用昵称和种类ID双重匹配，提高准确性
                        if (box_nickname == nickname and 
                            (not species or box_species == species)):
                            self.box_slots[row][col][0].configure(style="Selected.TFrame")
                            return
        
        # 如果双重匹配失败，尝试仅使用昵称匹配（向后兼容）
        # 在队伍中查找并高亮
        for i, (slot_frame, slot_label) in enumerate(self.team_slots):
            if i < len(self.team_data):
                team_pokemon = self.team_data[i]
                # 检查team_pokemon是Pokemon对象还是字典
                team_nickname = team_pokemon.nickname if hasattr(team_pokemon, 'nickname') else team_pokemon.get("nickname", "")
                if team_nickname == nickname:
                    slot_frame.configure(style="Selected.TFrame")
                    return
        
        # 在当前盒子中查找并高亮
        box_key = f"box_{self.current_box}"
        if box_key in self.box_data:
            for row in range(5):
                for col in range(6):
                    slot_index = row * 6 + col
                    if slot_index < len(self.box_data[box_key]):
                        box_pokemon = self.box_data[box_key][slot_index]
                        # 检查box_pokemon是Pokemon对象还是字典
                        box_nickname = box_pokemon.nickname if hasattr(box_pokemon, 'nickname') else box_pokemon.get("nickname", "")
                        if box_nickname == nickname:
                            self.box_slots[row][col][0].configure(style="Selected.TFrame")
                            return
    
    def unselect_all_pokemon(self):
        """取消所有宝可梦的选中状态（仅UI，不清空选中列表）"""
        # 取消队伍中的所有选中状态
        for slot_frame, slot_label in self.team_slots:
            slot_frame.configure(style="TFrame")
        
        # 取消盒子中的所有选中状态
        for row in range(5):
            for col in range(6):
                self.box_slots[row][col][0].configure(style="TFrame")
    
    def clear_selected_pokemon(self):
        """清空选中的宝可梦列表"""
        self.selected_pokemon = []
        self.unselect_all_pokemon()
    
    def reapply_highlights(self):
        """重新应用选中宝可梦的高亮状态"""
        # 先清除所有高亮
        self.unselect_all_pokemon()
        
        # 重新应用选中宝可梦的高亮
        for selected in self.selected_pokemon:
            nickname = selected.get('nickname', '')
            species = selected.get('species', '')
            
            # 在队伍中查找并高亮
            for i, (slot_frame, slot_label) in enumerate(self.team_slots):
                if i < len(self.team_data):
                    team_pokemon = self.team_data[i]
                    # 检查team_pokemon是Pokemon对象还是字典
                    if hasattr(team_pokemon, 'nickname') and hasattr(team_pokemon, 'species'):
                        # 是Pokemon对象
                        team_nickname = team_pokemon.nickname
                        team_species = team_pokemon.species
                    else:
                        # 是字典对象
                        team_nickname = team_pokemon.get("nickname", "")
                        team_species = team_pokemon.get("data", {}).get("species", "") if "data" in team_pokemon else ""
                    
                    # 使用昵称和种类ID双重匹配，提高准确性
                    if (team_nickname == nickname and 
                        (not species or team_species == species)):
                        slot_frame.configure(style="Selected.TFrame")
                        break
            
            # 在当前盒子中查找并高亮
            box_key = f"box_{self.current_box}"
            if box_key in self.box_data:
                for row in range(5):
                    for col in range(6):
                        slot_index = row * 6 + col
                        if slot_index < len(self.box_data[box_key]):
                            box_pokemon = self.box_data[box_key][slot_index]
                            # 检查box_pokemon是Pokemon对象还是字典
                            if hasattr(box_pokemon, 'nickname') and hasattr(box_pokemon, 'species'):
                                # 是Pokemon对象
                                box_nickname = box_pokemon.nickname
                                box_species = box_pokemon.species
                            else:
                                # 是字典对象
                                box_nickname = box_pokemon.get("nickname", "")
                                box_species = box_pokemon.get("data", {}).get("species", "") if "data" in box_pokemon else ""
                            
                            # 使用昵称和种类ID双重匹配，提高准确性
                            if (box_nickname == nickname and 
                                (not species or box_species == species)):
                                self.box_slots[row][col][0].configure(style="Selected.TFrame")
                                break
    
    def refresh_display(self):
        """刷新显示，重新应用高亮"""
        # 先清除所有高亮
        self.unselect_all_pokemon()
        
        # 更新显示
        self.update_display()
        
        # 重新应用选中宝可梦的高亮状态
        self.reapply_highlights()


