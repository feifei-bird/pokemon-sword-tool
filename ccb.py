import tkinter as tk
from tkinter import ttk, Canvas, Frame, Scrollbar, Listbox, StringVar, IntVar, messagebox
import json
import os
import random
import math
import time
from pokemon_class import PokemonManager
from utils.path_resolver import get_disabled_blocks, set_disabled_blocks, get_last_mode, set_last_mode

try:
    from file_manager import safe_load_file, safe_save_file
except ImportError:
    safe_load_file = None
    safe_save_file = None
    print("警告: 无法导入file_manager模块，某些功能可能不可用")

# 全局变量，用于存储CCB实例，以便在pokemon_home.py中调用
ccb_instance = None

# 转盘颜色循环
WHEEL_COLORS = ["#00BFFF", "#FFC0CB", "#E6E6FA", "#FFD700", "#F0FFF0", "#FF6347", "#1E90FF", "#B0E0E6", "#FFF0F5", "#D8BFD8", "#FFFACD", "#F5FFFA", "#FFA07A", "#87CEEB"]  # 天蓝、亮粉、淡紫、金色、淡绿、番茄红、道奇蓝、淡蓝、淡粉红、淡紫、淡金、淡薄荷、淡鲑鱼、淡天蓝

# 宝可梦数据全局变量
pokemon_data = {
    "team": [],
    "boxes": {}
}

class CCB:
    def __init__(self, parent, pokemon_home_instance=None):
        self.parent = parent
        self.pokemon_home_instance = pokemon_home_instance  # 添加宝可梦之家实例引用
        
        # 当前模式（0: 转盘, 1: 翻牌）
        self.current_mode = IntVar(value=0)
        
        # 当前选中的队伍/盒子（"队伍": 队伍, "盒子1"-"盒子32": 盒子）
        self.current_location = StringVar(value="队伍")
        
        # 禁用列表
        self.disabled_pokemon = []  # 统一使用disabled_pokemon名称
        
        # 中奖名单列表
        self.winner_list = []
        
        # 已抽取的宝可梦列表
        self.drawn_pokemon = []
        
        # 转盘扇形区域列表
        self.wheel_sections = []
        
        # 当前选中的宝可梦索引
        self.selected_pokemon_index = -1
        
        # 转盘是否正在旋转
        self.is_spinning = False
        
        # 转盘旋转角度
        self.wheel_angle = 0
        
        # 初始化PokemonManager
        main_info_path = "pokemon_main_info.json"
        self.pokemon_manager = PokemonManager(main_info_path)
        
        # 设置CCB标签页
        self.setup_ccb_tab()
        
        # 加载上次保存的模式
        self.load_current_mode_from_config()
        
        # 加载宝可梦数据
        self.load_pokemon_data()
        
        # 加载禁用信息
        self.load_disabled_info()
        
        # 重绘转盘或重随卡片（确保在加载禁用信息后更新显示）
        if self.current_mode.get() == 0:
            self.draw_wheel()
        elif self.current_mode.get() == 1:
            self.resample_cards()
        
        # 设置全局实例
        global ccb_instance
        ccb_instance = self
        
    def load_pokemon_data(self):
        """加载宝可梦数据"""
        global pokemon_data
        
        try:
            # 使用PokemonManager加载宝可梦数据
            self.pokemon_manager.load_pokemon_data()
            
            # 从PokemonManager获取数据
            team_data = self.pokemon_manager.get_team_data()
            boxes_data = self.pokemon_manager.get_all_boxes_data()
            
            # 转换数据格式以适配CCB类
            pokemon_data = {
                "team": [],
                "boxes": {}
            }
            
            # 处理队伍数据
            for pokemon in team_data:
                if pokemon:
                    # 将Pokemon对象转换为字典格式
                    pokemon_data["team"].append(pokemon.to_dict())
                else:
                    pokemon_data["team"].append(None)
            
            # 处理盒子数据
            for box_key, box_data in boxes_data.items():
                pokemon_data["boxes"][box_key] = []
                for pokemon in box_data:
                    if pokemon:
                        # 将Pokemon对象转换为字典格式
                        pokemon_data["boxes"][box_key].append(pokemon.to_dict())
                    else:
                        pokemon_data["boxes"][box_key].append(None)
            
            # 更新位置选择下拉框
            self.update_location_options()
            
            # 更新所有宝可梦昵称列表
            self.update_all_nickname_list()
            
            # 更新禁用列表显示
            self.update_disabled_list_display()
                
        except Exception as e:
            print(f"加载宝可梦数据失败: {e}")
            messagebox.showerror("错误", f"加载宝可梦数据失败: {e}")

    def _load_pokemon_data_without_ui(self):
        """仅加载宝可梦数据到内存，不更新UI元素"""
        global pokemon_data
        
        try:
            # 使用PokemonManager加载宝可梦数据
            self.pokemon_manager.load_pokemon_data()
            
            # 从PokemonManager获取数据
            team_data = self.pokemon_manager.get_team_data()
            boxes_data = self.pokemon_manager.get_all_boxes_data()
            
            # 转换数据格式以适配CCB类
            pokemon_data = {
                "team": [],
                "boxes": {}
            }
            
            # 处理队伍数据
            for pokemon in team_data:
                if pokemon:
                    # 将Pokemon对象转换为字典格式
                    pokemon_data["team"].append(pokemon.to_dict())
                else:
                    pokemon_data["team"].append(None)
            
            # 处理盒子数据
            for box_key, box_data in boxes_data.items():
                pokemon_data["boxes"][box_key] = []
                for pokemon in box_data:
                    if pokemon:
                        # 将Pokemon对象转换为字典格式
                        pokemon_data["boxes"][box_key].append(pokemon.to_dict())
                    else:
                        pokemon_data["boxes"][box_key].append(None)
            
            print("CCB数据已刷新（无UI更新）")
                
        except Exception as e:
            print(f"加载宝可梦数据失败（无UI）: {e}")
    
    def get_pokemon_list(self, location_id):
        """获取指定位置的宝可梦列表"""
        global pokemon_data
        
        if not pokemon_data or 'team' not in pokemon_data:
            return []
            
        # 解析位置ID
        if location_id == 0:
            # 队伍位置
            if pokemon_data['team']:
                return [p for p in pokemon_data['team'] if p]
        elif 1 <= location_id <= 32:
            # 盒子位置
            box_index = location_id - 1
            box_key = f"box_{box_index + 1}"  # pokemon_home中使用box_1, box_2等格式
            if 'boxes' in pokemon_data and box_key in pokemon_data['boxes']:
                # 过滤掉空槽位
                return [p for p in pokemon_data['boxes'][box_key] if p]
            # 尝试使用数字索引作为备用方案
            elif 'boxes' in pokemon_data and box_index < len(pokemon_data['boxes']):
                # 过滤掉空槽位
                return [p for p in pokemon_data['boxes'][box_index] if p]
                
        return []
        
    def get_all_available_pokemon(self):
        """获取所有不在禁用列表中的宝可梦"""
        global pokemon_data
        
        if not pokemon_data or ('team' not in pokemon_data and 'boxes' not in pokemon_data):
            return []
            
        all_pokemon = []
        
        # 添加队伍中的宝可梦
        if 'team' in pokemon_data and pokemon_data['team']:
            all_pokemon.extend([p for p in pokemon_data['team'] if p])
            
        # 添加盒子中的宝可梦
        if 'boxes' in pokemon_data:
            for box_data in pokemon_data['boxes'].values():
                if box_data:
                    all_pokemon.extend([p for p in box_data if p])
        
        # 过滤掉禁用的宝可梦
        available_pokemon = []
        for pokemon in all_pokemon:
            is_disabled = False
            for disabled_pokemon in self.disabled_pokemon:
                if (disabled_pokemon["nickname"] == pokemon["nickname"] and 
                    disabled_pokemon["species"] == pokemon["species"]):
                    is_disabled = True
                    break
            
            # 过滤掉已抽取的宝可梦
            is_drawn = False
            for drawn_pokemon in self.drawn_pokemon:
                if (drawn_pokemon["nickname"] == pokemon["nickname"] and 
                    drawn_pokemon["species"] == pokemon["species"]):
                    is_drawn = True
                    break
            
            if not is_disabled and not is_drawn:
                available_pokemon.append(pokemon)
        
        return available_pokemon
    
    def update_location_options(self):
        """更新位置选择下拉框选项"""
        global pokemon_data
        
        # 清空现有选项
        location_options = ["队伍"]
        
        if pokemon_data and 'boxes' in pokemon_data:
            # 检查是否使用box_1, box_2等格式
            if any(key.startswith('box_') for key in pokemon_data['boxes'].keys()):
                # pokemon_home格式：box_1, box_2等
                for i in range(1, 33):
                    box_key = f"box_{i}"
                    # 检查盒子是否存在且包含至少一个宝可梦
                    if box_key in pokemon_data['boxes'] and pokemon_data['boxes'][box_key]:
                        # 进一步检查盒子中是否有非空槽位
                        if any(pokemon for pokemon in pokemon_data['boxes'][box_key] if pokemon):
                            location_options.append(f"盒子{i}")
            else:
                # 原始格式：数字索引
                for i, box in enumerate(pokemon_data['boxes']):
                    # 检查盒子中是否有宝可梦
                    if any(p for p in box if p):
                        location_options.append(f"盒子{i+1}")
        
        # 更新下拉框选项
        self.location_combobox['values'] = location_options
        
        # 如果有选项，保持当前选择或选择第一个
        current_value = self.location_var.get()
        if current_value in location_options:
            self.location_combobox.set(current_value)
        elif location_options:
            self.location_combobox.current(0)
            self.on_location_change(None)
        
    def setup_ccb_tab(self):
        """设置CCB标签页"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建顶部控制区域
        self.setup_top_controls()
        
        # 创建主内容区域（左右布局）
        self.main_content_frame = ttk.Frame(self.main_frame)
        self.main_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建左侧禁用列表区域（竖直小块）
        self.setup_disabled_list()
        
        # 创建中间内容区域
        self.setup_content_area()
        
        # 创建右侧中奖名单区域（竖直小块）
        self.setup_winner_list()
        
    def setup_top_controls(self):
        """设置顶部控制区域"""
        top_frame = ttk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 模式切换按钮（左转盘右翻牌，当前模式高亮显示）
        self.mode_frame = ttk.Frame(top_frame)
        self.mode_frame.pack(side=tk.LEFT, padx=5)
        
        self.wheel_button = ttk.Button(self.mode_frame, text="转盘")
        self.wheel_button.pack(side=tk.LEFT, padx=2)
        
        self.card_button = ttk.Button(self.mode_frame, text="翻牌")
        self.card_button.pack(side=tk.LEFT, padx=2)
        
        # 初始化按钮状态
        self.update_button_states()
        
        # 队伍/盒子选择下拉框
        location_frame = ttk.Frame(top_frame)
        location_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(location_frame, text="选择位置:").pack(side=tk.LEFT, padx=5)
        
        self.location_var = StringVar()
        location_options = ["队伍"] + [f"盒子{i}" for i in range(1, 33)]
        self.location_combobox = ttk.Combobox(location_frame, textvariable=self.location_var, values=location_options, state="readonly", width=10)
        self.location_combobox.current(0)  # 默认选择队伍
        self.location_combobox.pack(side=tk.LEFT, padx=5)
        self.location_combobox.bind("<<ComboboxSelected>>", self.on_location_change)
        
        # 块禁用按钮
        self.disable_all_button = ttk.Button(top_frame, text="块禁用", command=self.disable_all)
        self.disable_all_button.pack(side=tk.LEFT, padx=5)
        
        # 块启用按钮
        self.enable_all_button = ttk.Button(top_frame, text="块启用", command=self.enable_all)
        self.enable_all_button.pack(side=tk.LEFT, padx=5)
        
        # 移除了单只宝可梦的禁用和启用功能
        
        # 抽取重置按钮（保留在顶部）
        self.reset_wheel_button = ttk.Button(top_frame, text="抽取重置", command=self.reset_wheel)
        self.reset_wheel_button.pack(side=tk.LEFT, padx=5)
        
    def setup_mode_switch(self):
        """设置模式切换区域"""
        # 这里可以添加更多模式切换相关的UI元素
        pass
        
    def setup_content_area(self):
        """设置内容区域（中间大部分空间）"""
        self.content_frame = ttk.Frame(self.main_content_frame)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 根据当前模式显示不同的内容
        self.update_content_area()
        
    def setup_disabled_list(self):
        """设置禁用列表区域（左侧竖直小块）"""
        disabled_frame = ttk.LabelFrame(self.main_content_frame, text="禁用列表")
        disabled_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 创建滚动条和列表框
        scrollbar = Scrollbar(disabled_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.disabled_listbox = Listbox(disabled_frame, yscrollcommand=scrollbar.set, height=15, width=15)
        self.disabled_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.disabled_listbox.yview)
        
        # 更新禁用列表显示
        self.update_disabled_list_display()
        
    def switch_mode(self, mode):
        """切换模式"""
        # 保存当前模式
        old_mode = self.current_mode.get()
        self.current_mode.set(mode)
        self.update_button_states()
        self.update_content_area()
        
        # 如果从转盘模式切换到翻牌模式，自动重随一批卡片
        if old_mode == 0 and mode == 1 and hasattr(self, 'resample_button'):
            self.resample_cards()
        
        # 保存当前模式到配置文件
        self.save_current_mode_to_config()
        
    def save_current_mode_to_config(self):
        try:
            set_last_mode(self.current_mode.get())
        except Exception as e:
            print(f"保存当前模式到配置失败: {e}")
    
    def load_current_mode_from_config(self):
        try:
            last_mode = get_last_mode()
            self.current_mode.set(last_mode)
            self.update_button_states()
            self.update_content_area()
        except Exception as e:
            print(f"从配置加载上次模式失败: {e}")
            
    def update_button_states(self):
        """更新按钮状态"""
        if self.current_mode.get() == 0:  # 转盘模式
            self.wheel_button.config(state="disabled")  # 禁用但显示为白色
            self.card_button.config(state="normal")  # 显示为可点击但实际禁用
            # 为翻牌按钮添加点击事件处理，使其在转盘模式下点击时切换到翻牌模式
            self.card_button.config(command=lambda: self.switch_mode(1))
        else:  # 翻牌模式
            self.wheel_button.config(state="normal")  # 显示为可点击但实际禁用
            self.card_button.config(state="disabled")  # 禁用但显示为白色
            # 为转盘按钮添加点击事件处理，使其在翻牌模式下点击时切换到转盘模式
            self.wheel_button.config(command=lambda: self.switch_mode(0))
            
    def update_content_area(self):
        """更新内容区域"""
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if self.current_mode.get() == 0:  # 转盘模式
            self.setup_wheel_mode()
        else:  # 翻牌模式
            self.setup_card_mode()
            
    def setup_wheel_mode(self):
        """设置转盘模式"""
        # 创建转盘画布（占据更大面积）
        self.wheel_canvas = Canvas(self.content_frame, width=600, height=600, bg="white")
        self.wheel_canvas.pack(pady=20, expand=True)
        
        # 初始化转盘更新定时器
        self.wheel_update_timer = None
        
        # 为画布添加点击事件
        self.wheel_canvas.bind("<Button-1>", lambda e: self.handle_wheel_click(e))
        
        # 为画布添加鼠标悬停效果
        self.wheel_canvas.bind("<Enter>", lambda e: self.wheel_canvas.config(cursor="hand2"))
        self.wheel_canvas.bind("<Leave>", lambda e: self.wheel_canvas.config(cursor=""))
        
        # 绘制转盘
        self.draw_wheel()
        
        # 在转盘画布内创建选中结果显示区域（转盘上方，避免被截断）
        center_x, center_y = 300, 300
        radius = 250
        result_y = center_y - radius - 30  # 转盘中心向上偏移转盘半径再多30像素
        self.result_text_id = self.wheel_canvas.create_text(center_x, result_y, text="", font=("宋体", 20, "bold"), fill="#FFEA00")
        
    def setup_card_mode(self):
        """设置翻牌模式"""
        # 创建顶部控制区域（包含"重随一批"和"揭开全部"按钮）
        top_control_frame = ttk.Frame(self.content_frame)
        top_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建显示选中宝可梦昵称的标签（使用和转盘相同的样式）
        self.selected_pokemon_label = ttk.Label(top_control_frame, text="", font=("宋体", 20, "bold"), foreground="#FFEA00")
        self.selected_pokemon_label.pack(pady=10)
        
        # 创建按钮区域
        button_frame = ttk.Frame(top_control_frame)
        button_frame.pack(pady=5)
        
        # "重随一批"按钮
        self.resample_button = ttk.Button(button_frame, text="重随一批", command=self.resample_cards)
        self.resample_button.pack(side=tk.LEFT, padx=5)
        
        # "揭开全部"按钮
        self.reveal_all_button = ttk.Button(button_frame, text="揭开全部", command=self.reveal_all_cards)
        self.reveal_all_button.pack(side=tk.LEFT, padx=5)
        
        # 创建翻牌区域（5×5布局）
        self.card_frame = Frame(self.content_frame, bg="lightgray")
        self.card_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        # 初始化翻牌相关变量
        self.cards = []  # 存储所有卡片对象
        self.card_pokemon = []  # 存储每张卡片对应的宝可梦
        self.revealed_cards = []  # 存储已翻开的卡片索引
        self.card_colors = []  # 存储每张卡片的颜色
        
        # 初始化时启用位置选择下拉框、块禁用和块启用按钮
        self.location_combobox.config(state="readonly")
        self.disable_all_button.config(state="normal")
        self.enable_all_button.config(state="normal")
        
        # 初始化翻牌区域
        self.resample_cards()
        
    def draw_wheel(self):
        """绘制转盘"""
        # 清空画布
        self.wheel_canvas.delete("all")
        
        # 重新创建指针（固定在右侧，指向转盘中心）
        radius = 250
        center_x, center_y = 300, 300
        pointer_length = radius + 90  # 进一步增加指针长度以确保可见性
        # 创建更大更明显的三角形箭头
        self.wheel_canvas.create_line(center_x + pointer_length, center_y, center_x + radius, center_y, 
                                   arrow=tk.LAST, arrowshape=(30, 40, 15), width=6, fill="#FF0000", tags="pointer")
        
        # 重新创建结果显示区域（转盘上方，避免被截断）
        result_y = center_y - radius - 30  # 转盘中心向上偏移转盘半径再多30像素
        self.result_text_id = self.wheel_canvas.create_text(center_x, result_y, text="", font=("宋体", 20, "bold"), fill="#FFEA00")
        
        # 如果有选中的宝可梦，恢复显示结果
        if hasattr(self, 'selected_pokemon_index') and self.selected_pokemon_index >= 0 and self.selected_pokemon_index < len(self.wheel_sections):
            selected_pokemon = self.wheel_sections[self.selected_pokemon_index]["pokemon"]
            self.wheel_canvas.itemconfig(self.result_text_id, text=f"{selected_pokemon['nickname']}", font=("宋体", 20, "bold"), fill="#FFEA00")
        
        # 获取所有不在禁用列表中的宝可梦
        pokemon_list = self.get_all_available_pokemon()
        
        # 如果没有宝可梦，显示提示信息
        if not pokemon_list:
            self.wheel_canvas.create_text(300, 300, text="没有可用的宝可梦", font=("宋体", 16), fill="red")
            return
        
        # 清空扇形区域列表
        self.wheel_sections = []
        
        # 转盘中心点和半径（使用已定义的变量）
        radius = 250
        
        # 绘制外圆
        self.wheel_canvas.create_oval(center_x - radius, center_y - radius, 
                                     center_x + radius, center_y + radius, 
                                     fill="white", outline="black", width=2, tags="wheel")
        
        # 调试信息：打印转盘绘制状态
        print(f"转盘已绘制，中心位置：({center_x}, {center_y})，半径：{radius}")
        
        # 计算每个扇形的角度
        pokemon_count = len(pokemon_list)
        angle_per_section = 360 / pokemon_count
        
        # 应用当前旋转角度（保持上一次旋转结束时的角度）
        current_rotation = getattr(self, 'wheel_angle', 0) % 360
        
        # 绘制扇形区域
        for i, pokemon in enumerate(pokemon_list):
            start_angle = i * angle_per_section + current_rotation
            end_angle = (i + 1) * angle_per_section + current_rotation
            
            # 计算扇形的点
            points = [center_x, center_y]
            for angle in range(int(start_angle), int(end_angle) + 1):
                rad = math.radians(angle)
                x = center_x + radius * math.cos(rad)
                y = center_y + radius * math.sin(rad)
                points.extend([x, y])
                
            # 选择颜色（按指定循环）
            color = WHEEL_COLORS[i % len(WHEEL_COLORS)]
            
            # 绘制扇形
            section = self.wheel_canvas.create_polygon(points, fill=color, outline="black")
            
            # 保存扇形区域信息
            self.wheel_sections.append({
                "id": section,
                "start_angle": start_angle - current_rotation,  # 保存原始角度（不考虑旋转）
                "end_angle": end_angle - current_rotation,      # 保存原始角度（不考虑旋转）
                "pokemon": pokemon
            })
            
            # 计算文本位置（扇形中间）
            text_angle = math.radians((start_angle + end_angle) / 2)
            text_radius = radius * 0.7
            text_x = center_x + text_radius * math.cos(text_angle)
            text_y = center_y + text_radius * math.sin(text_angle)
            
            # 添加宝可梦昵称（白色文字带黑色轮廓）
            # 先创建黑色轮廓文本（稍微偏移）
            outline_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # 四个方向的偏移
            outline_ids = []
            for dx, dy in outline_offsets:
                outline_id = self.wheel_canvas.create_text(text_x + dx, text_y + dy, text=pokemon["nickname"], 
                                             font=("宋体", 12, "bold"), fill="black")
                outline_ids.append(outline_id)
            
            # 再创建白色填充文本
            text_id = self.wheel_canvas.create_text(text_x, text_y, text=pokemon["nickname"], 
                                         font=("宋体", 12, "bold"), fill="white")
            
            # 保存文本ID，以便在旋转时更新位置
            self.wheel_sections[-1]["text_id"] = text_id
            self.wheel_sections[-1]["outline_ids"] = outline_ids
            
    def handle_wheel_click(self, event):
        """处理转盘点击事件"""
        # 如果正在旋转，则不响应
        if self.is_spinning:
            return
            
        # 检查点击位置是否在转盘范围内
        center_x, center_y = 300, 300
        radius = 250
        
        # 计算点击位置与转盘中心的距离
        distance = math.sqrt((event.x - center_x)**2 + (event.y - center_y)**2)
        
        # 如果点击位置在转盘范围内，则触发旋转
        if distance <= radius:
            # 取消任何待执行的转盘更新定时器
            if hasattr(self, 'wheel_update_timer') and self.wheel_update_timer is not None:
                self.wheel_canvas.after_cancel(self.wheel_update_timer)
                self.wheel_update_timer = None
            
            # 调用提前点击方法处理非自动更新下的点击
            self.handle_early_click()
    
    def handle_early_click(self):
        """处理提前点击（非自动更新下的点击）"""
        # 保存当前显示的文本
        current_text = ""
        if hasattr(self, 'result_text_id'):
            current_text = self.wheel_canvas.itemcget(self.result_text_id, "text")
        
        # 立即禁用转盘点击事件并隐藏鼠标光标
        self.wheel_canvas.unbind("<Button-1>")
        self.wheel_canvas.config(cursor="none")
        
        # 立即更新转盘（移除已选中的宝可梦）
        self.draw_wheel()
        
        # 恢复之前显示的文本
        if hasattr(self, 'result_text_id') and current_text:
            self.wheel_canvas.itemconfig(self.result_text_id, text=current_text)
        
        # 0.3秒后开始旋转（给用户视觉反馈）
        self.wheel_canvas.after(300, self.spin_wheel)
    
    def spin_wheel(self):
        """旋转转盘"""
        # 如果正在旋转，则不响应
        if self.is_spinning:
            return
            
        # 如果没有扇形区域，则不旋转
        if not self.wheel_sections:
            return
            
        # 取消任何待执行的转盘更新定时器
        if hasattr(self, 'wheel_update_timer') and self.wheel_update_timer is not None:
            self.wheel_canvas.after_cancel(self.wheel_update_timer)
            self.wheel_update_timer = None
            
        # 在旋转前更新转盘，以反映已抽取的宝可梦
        self.draw_wheel()
            
        # 设置旋转状态为True
        self.is_spinning = True
        
        # 在旋转开始时清空最上方的选中显示
        if hasattr(self, 'result_text_id'):
            self.wheel_canvas.itemconfig(self.result_text_id, text="")
        
        # 在旋转过程中，禁用转盘点击事件
        self.wheel_canvas.unbind("<Button-1>")
        self.wheel_canvas.config(cursor="none")  # 隐藏鼠标光标
        
        # 禁用顶部控制按钮
        self.disable_all_button.config(state="disabled")
        self.enable_all_button.config(state="disabled")
        self.reset_wheel_button.config(state="disabled")
        
        # 禁用位置选择下拉框
        self.location_combobox.config(state="disabled")
        
        # 禁用模式切换按钮
        self.wheel_button.config(state="disabled")
        self.card_button.config(state="disabled")
        
        # 播放开始旋转音效
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            pass  # 如果无法播放音效，忽略错误
        
        # 随机选择一个扇形区域
        import random
        selected_index = random.randint(0, len(self.wheel_sections) - 1)
        self.selected_pokemon_index = selected_index
        
        # 随机旋转圈数（8-12圈），调整总旋转圈数以匹配新的减速效果
        full_rotations = random.uniform(8, 12)
        
        # 计算参考目标角度，用于确定旋转的总圈数和大致方向
        # 注意：虽然这里计算了目标角度，但最终选中的宝可梦是根据转盘自然停止后的实际位置确定的
        # 这样做是为了确保转盘旋转足够的圈数，同时保持结果的自然随机性
        selected_section = self.wheel_sections[selected_index]
        section_middle_angle = (selected_section["start_angle"] + selected_section["end_angle"]) / 2
        
        # 添加随机偏移量，使结果更自然（-2度到+2度之间）
        random_offset = random.uniform(-2, 2)
        
        # 计算总旋转角度（多转几圈后接近选中的扇形中间）
        # 指针指向右侧（0度），所以需要计算使选中扇形中间接近指针的角度
        # 添加当前旋转角度作为基础，保持扇区弧线起点不变
        current_base_angle = getattr(self, 'wheel_angle', 0)
        target_angle = current_base_angle + full_rotations * 360 + (360 - section_middle_angle + random_offset)
        
        # 确保目标角度是360的倍数加上一个精确的偏移量，使旋转更自然
        # 这样可以确保每次旋转都是完整的圈数加上一个精确的偏移
        target_angle = round(target_angle / 360) * 360 + (target_angle % 360)
        
        # 保存参考的扇形索引，仅用于记录，不影响最终结果
        self.target_pokemon_index = selected_index
        
        # 保存当前旋转角度作为下一次绘制的基础
        self.wheel_angle = current_base_angle
        
        # 重置减速开始时的剩余角度
        if hasattr(self, 'deceleration_start_remaining_angle'):
            delattr(self, 'deceleration_start_remaining_angle')
        
        # 重置上一次旋转的速度记录，避免影响新的旋转
        if hasattr(self, 'previous_speed'):
            delattr(self, 'previous_speed')
        
        # 开始旋转动画
        self.animate_wheel_rotation(target_angle)
        
    def animate_wheel_rotation(self, target_angle):
        """转盘旋转动画"""
        # 重置滑行状态变量，避免多次旋转之间的状态干扰
        if hasattr(self, 'coasting_started'):
            delattr(self, 'coasting_started')
        if hasattr(self, 'coasting_start_time'):
            delattr(self, 'coasting_start_time')
        if hasattr(self, 'coasting_duration'):
            delattr(self, 'coasting_duration')
        if hasattr(self, 'coasting_start_speed'):
            delattr(self, 'coasting_start_speed')
        if hasattr(self, 'coasting_target_speed'):
            delattr(self, 'coasting_target_speed')
        
        current_angle = 0
        # 初始速度
        initial_speed = 15
        # 高速速度，降低高速速度使整体旋转更平滑
        high_speed = 25
        # 最小速度，进一步降低最小速度使最后阶段更加缓慢
        min_speed = 0.3
        # 随机高速旋转时间（6-8秒），增加高速旋转时间以延长整体旋转时间
        high_speed_time = random.uniform(6, 8) * 1000  # 转换为毫秒
        # 高速旋转开始时间
        high_speed_start_time = None
        # 加速阶段时间（1.0秒），缩短加速时间
        acceleration_time = 1.0 * 1000  # 转换为毫秒
        # 加速开始时间
        acceleration_start_time = time.time() * 1000
        # 减速阶段时间（10秒），调整减速总时间以匹配CSS3缓动效果
        deceleration_duration = 10 * 1000  # 转换为毫秒
        # 减速开始时间
        deceleration_start_time = None
        # 减速开始角度（占总角度的20%），更早开始减速以匹配CSS3缓动效果
        deceleration_start_angle = target_angle * 0.2
        
        def rotate_step():
            nonlocal current_angle, high_speed_start_time, deceleration_start_time
            
            # 初始化当前速度
            current_speed = initial_speed
            
            # 计算剩余角度
            remaining_angle = target_angle - current_angle
            
            # 检查是否需要进入滑行阶段
            if not hasattr(self, 'coasting_started') and remaining_angle < 10 and current_speed > min_speed * 2:
                # 稳定进入滑行阶段（100%概率）
                self.coasting_started = True
                self.coasting_start_time = time.time() * 1000
                self.coasting_duration = random.uniform(500, 1500)  # 随机滑行时间0.1-0.9秒
                self.coasting_start_speed = current_speed
                self.coasting_target_speed = current_speed * 0.9  # 滑行目标速度为当前速度的90%，避免过于缓慢
            
            # 滑行阶段处理
            if hasattr(self, 'coasting_started') and self.coasting_started:
                coasting_progress = min(1.0, (time.time() * 1000 - self.coasting_start_time) / self.coasting_duration)
                
                # 使用缓动函数让滑行更加平滑
                ease_factor = 1 - math.cos(coasting_progress * math.pi / 2)
                
                # 计算滑行阶段的速度，从当前速度逐渐降低到目标速度
                current_speed = self.coasting_start_speed - (self.coasting_start_speed - self.coasting_target_speed) * ease_factor
                
                # 如果滑行结束，继续正常减速
                if coasting_progress >= 1.0:
                    self.coasting_started = False
            
            # 如果已经达到或超过目标角度，或者速度已经降到极低且接近目标角度，停止旋转
            if current_angle >= target_angle or (current_speed < min_speed * 0.1 and remaining_angle < 0.5):
                # 让转盘自然停止在当前位置，不强制对齐预设的宝可梦
                # 确保最终角度精确对齐目标角度
                self.wheel_angle = target_angle
                
                center_x, center_y = 300, 300
                for section in self.wheel_sections:
                    # 获取扇形的原始点
                    points = []
                    for angle in range(int(section["start_angle"]), int(section["end_angle"]) + 1):
                        rad = math.radians(angle + target_angle)
                        x = center_x + 250 * math.cos(rad)
                        y = center_y + 250 * math.sin(rad)
                        points.extend([x, y])
                    
                    # 更新扇形位置
                    self.wheel_canvas.coords(section["id"], center_x, center_y, *points)
                    
                    # 更新文本位置
                    if "text_id" in section:
                        # 计算文本的新位置（扇形中间）
                        start_angle = section["start_angle"]
                        end_angle = section["end_angle"]
                        text_angle = math.radians((start_angle + end_angle) / 2 + target_angle)
                        text_radius = 250 * 0.7
                        text_x = center_x + text_radius * math.cos(text_angle)
                        text_y = center_y + text_radius * math.sin(text_angle)
                        
                        # 更新文本位置
                        self.wheel_canvas.coords(section["text_id"], text_x, text_y)
                
                self.is_spinning = False
                
                # 恢复默认光标（手型光标）
                self.wheel_canvas.config(cursor="hand2")
                
                # 重新绑定画布点击事件
                self.wheel_canvas.unbind("<Button-1>")
                self.wheel_canvas.bind("<Button-1>", lambda e: self.handle_wheel_click(e))
                
                # 重新启用抽取重置按钮
                self.reset_wheel_button.config(state="normal")
                # 注意：不重新启用块禁用和块启用按钮，除非点击重置按钮
                
                # 播放停止音效
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except:
                    pass  # 如果无法播放音效，忽略错误
                
                # 根据指针指向确定选中的宝可梦
                self.determine_selected_pokemon_by_pointer()
                
                # 设置2.5秒后自动更新转盘的定时器
                self.wheel_update_timer = self.wheel_canvas.after(2500, self.update_wheel_after_spin)
                return
            
            current_time = time.time() * 1000
            
            # 记录高速旋转开始时间
            if high_speed_start_time is None and current_speed >= high_speed * 0.9:
                high_speed_start_time = current_time
            
            # 计算当前速度
            if current_time - acceleration_start_time < acceleration_time:
                # 加速阶段（1.5秒）
                # 使用正弦缓动函数实现更平滑的加速效果
                progress = (current_time - acceleration_start_time) / acceleration_time
                # 使用正弦函数实现缓动效果，使加速更平滑
                speed_factor = 1 - math.cos(progress * math.pi / 2)
                current_speed = initial_speed + (high_speed - initial_speed) * speed_factor
            elif current_angle < deceleration_start_angle:
                # 高速旋转阶段（直到达到减速开始角度）
                current_speed = high_speed
                
                # 如果高速旋转时间超过预设时间，强制进入减速阶段
                if high_speed_start_time is not None and current_time - high_speed_start_time > high_speed_time:
                    # 强制进入减速阶段
                    deceleration_start_time = current_time
                    self.deceleration_start_remaining_angle = target_angle - current_angle
                    
                    # 添加过渡阶段，让减速开始更加平滑
                    self.transition_start_time = current_time
                    self.transition_duration = 500  # 500毫秒的过渡时间
                    self.transition_start_speed = high_speed
            else:
                # 减速阶段（10秒）
                if deceleration_start_time is None:
                    deceleration_start_time = current_time
                    
                # 检查是否在过渡阶段
                if hasattr(self, 'transition_start_time') and current_time - self.transition_start_time < self.transition_duration:
                    # 过渡阶段：从高速平滑过渡到减速开始
                    transition_progress = (current_time - self.transition_start_time) / self.transition_duration
                    # 使用缓动函数让过渡更加平滑
                    ease_factor = 1 - math.cos(transition_progress * math.pi / 2)
                    
                    # 计算过渡阶段的速度，从高速逐渐降低
                    current_speed = self.transition_start_speed * (1 - ease_factor * 0.3)
                    
                    # 继续下一步旋转
                    step = min(current_speed, target_angle - current_angle)
                    current_angle += step
                    self.wheel_angle = current_angle
                    
                    # 更新转盘显示
                    self.update_wheel_display(current_angle)
                    
                    # 使用固定延迟继续动画
                    delay = 33  # 高速阶段延迟
                    self.wheel_canvas.after(delay, rotate_step)
                    return
                
                # 计算剩余角度
                remaining_angle = target_angle - current_angle
                
                # 计算减速进度（基于时间因素，确保至少运行10秒）
                time_progress = min(1.0, (current_time - deceleration_start_time) / 10000)
                
                # 计算角度进度，基于减速开始时的剩余角度
                if not hasattr(self, 'deceleration_start_remaining_angle'):
                    self.deceleration_start_remaining_angle = remaining_angle
                
                angle_progress = 1 - (remaining_angle / self.deceleration_start_remaining_angle)
                
                # 综合时间和角度进度，以时间因素为主导，但不超过1
                deceleration_progress = min(1.0, time_progress * 0.7 + angle_progress * 0.3)
                
                # 使用物理模型模拟减速过程，遵循"快速启动-保持-缓慢减速"的节奏模式
                # 模拟摩擦力作用下的角速度衰减，使减速更加自然平滑
                
                # 计算减速开始后的时间比例
                time_factor = min(1.0, (current_time - deceleration_start_time) / deceleration_duration)
                
                # 使用改进的减速模型，参考 https://cn.piliapp.com/random/wheel/ 的转盘效果
                # 实现更自然的减速曲线，特别是在最后阶段增加缓慢移动时间以增强紧张感
                
                # 使用统一的减速进度计算速度
                progress = deceleration_progress
                
                # 精确模拟CSS3 cubic-bezier(0.1, 0.7, 0.1, 1)缓动函数的减速效果
                # 使用贝塞尔曲线的数学近似，实现更自然的先快后慢减速
                if progress < 0.4:
                    # 前期：快速减速阶段（类似cubic-bezier的0.1, 0.7部分）
                    # 使用二次贝塞尔曲线近似
                    t = progress / 0.4
                    speed_factor = 1 - 0.9 * t * t
                elif progress < 0.85:
                    # 中期：平稳减速阶段
                    t = (progress - 0.4) / 0.45
                    # 使用线性过渡，保持平稳减速
                    speed_factor = 0.64 - 0.5 * t
                else:
                    # 后期：极度缓慢减速阶段（类似cubic-bezier的0.1, 1部分）
                    t = (progress - 0.85) / 0.15
                    # 使用指数衰减实现极度缓慢的最终减速
                    speed_factor = 0.39 * math.exp(-3 * t)
                
                # 优化角度微调，与CSS3缓动函数更好地配合
                # 使用更平滑的过渡，避免速度突变
                if remaining_angle < 20:
                    # 最后20度，使用平滑过渡到最小速度
                    angle_factor = 0.4 + 0.6 * (remaining_angle / 20) ** 0.8
                else:
                    angle_factor = 1.0
                
                # 综合时间和角度因素计算当前速度
                current_speed = min_speed + (high_speed - min_speed) * speed_factor * angle_factor
                
                # 确保速度不会因为计算误差而突然增加
                if hasattr(self, 'previous_speed') and current_speed > self.previous_speed * 1.1:
                    # 如果新速度比前一次速度增加超过10%，则限制速度增长
                    current_speed = self.previous_speed * 0.95
                
                # 保存当前速度供下次比较
                self.previous_speed = current_speed
                
                # 优化速度限制，使其更符合CSS3缓动效果的自然减速
                # 使用更宽松的速度限制，让缓动函数主导减速过程
                min_visible_speed = max(min_speed, remaining_angle * 0.08)
                max_allowed_speed = max(min_visible_speed, remaining_angle * 0.6)  # 更宽松的上限
                if current_speed > max_allowed_speed:
                    current_speed = max_allowed_speed
                # 确保最后阶段有可见的移动，但不过度干预缓动效果
                if current_speed < min_visible_speed and remaining_angle > 2:
                    current_speed = min_visible_speed
            
            # 计算本次旋转的角度
            step = min(current_speed, target_angle - current_angle)
            current_angle += step
            
            # 更新转盘显示
            self.update_wheel_display(current_angle)
            
            # 继续下一步旋转，使用固定帧率控制动画速度
            # 为了达到预期的10秒减速时间，使用固定延迟时间
            # 高速阶段：30fps（约33ms/帧），中速阶段：20fps（50ms/帧），低速阶段：10fps（100ms/帧）
            if current_speed > 10:
                delay = 33  # 高速阶段：约30fps
            elif current_speed > 1:
                delay = 50  # 中速阶段：20fps
            else:
                delay = 100 # 低速阶段：10fps
            self.wheel_canvas.after(delay, rotate_step)
        
        # 开始旋转
        rotate_step()
    
    def update_wheel_display(self, current_angle):
        """更新转盘显示"""
        # 更新转盘旋转角度
        self.wheel_angle = current_angle
        
        # 旋转所有扇形区域
        center_x, center_y = 300, 300
        for section in self.wheel_sections:
            # 获取扇形的原始点
            points = []
            for angle in range(int(section["start_angle"]), int(section["end_angle"]) + 1):
                rad = math.radians(angle + current_angle)
                x = center_x + 250 * math.cos(rad)
                y = center_y + 250 * math.sin(rad)
                points.extend([x, y])
            
            # 更新扇形位置
            self.wheel_canvas.coords(section["id"], center_x, center_y, *points)
            
            # 更新文本位置
            if "text_id" in section:
                # 计算文本的新位置（扇形中间）
                start_angle = section["start_angle"]
                end_angle = section["end_angle"]
                text_angle = math.radians((start_angle + end_angle) / 2 + current_angle)
                text_radius = 250 * 0.7
                text_x = center_x + text_radius * math.cos(text_angle)
                text_y = center_y + text_radius * math.sin(text_angle)
                
                # 更新主文本位置
                self.wheel_canvas.coords(section["text_id"], text_x, text_y)
                
                # 更新轮廓文本位置（如果存在）
                if "outline_ids" in section and section["outline_ids"]:
                    # 轮廓文本有4个，分别位于上下左右偏移1像素的位置
                    outline_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]
                    for i, (dx, dy) in enumerate(outline_offsets):
                        if i < len(section["outline_ids"]):
                            outline_x = text_x + dx
                            outline_y = text_y + dy
                            self.wheel_canvas.coords(section["outline_ids"][i], outline_x, outline_y)
        
    def update_wheel_after_spin(self):
        """旋转结束后更新转盘"""
        # 如果正在旋转，则不更新
        if self.is_spinning:
            return
            
        # 保存当前选中的宝可梦信息
        last_selected_pokemon = None
        if hasattr(self, 'selected_pokemon_index') and self.selected_pokemon_index >= 0 and self.selected_pokemon_index < len(self.wheel_sections):
            last_selected_pokemon = self.wheel_sections[self.selected_pokemon_index]["pokemon"]
            
        # 清除定时器引用
        self.wheel_update_timer = None
        
        # 恢复默认光标（手型光标）
        self.wheel_canvas.config(cursor="hand2")
        
        # 重新绑定画布点击事件
        self.wheel_canvas.unbind("<Button-1>")
        self.wheel_canvas.bind("<Button-1>", lambda e: self.handle_wheel_click(e))
        
        # 恢复模式切换按钮状态
        self.update_button_states()
        
        # 注意：不重新启用块禁用和块启用按钮，除非点击重置按钮
        
        # 重新启用抽取重置按钮
        self.reset_wheel_button.config(state="normal")
        
        # 更新转盘（保持当前旋转角度）
        self.draw_wheel()
        
        # 如果有上次选中的宝可梦，恢复显示
        if last_selected_pokemon and hasattr(self, 'result_text_id'):
            self.wheel_canvas.itemconfig(self.result_text_id, text=f"{last_selected_pokemon['nickname']}", font=("宋体", 20, "bold"), fill="#FFEA00")
        
        # 应用随机初始偏移角度
        self.apply_random_offset()
    
    def apply_random_offset(self):
        """应用随机初始偏移角度"""
        # 生成随机偏移角度（0-359度）
        import random
        random_offset = random.randint(0, 359)
        
        # 保存当前显示的文本内容
        current_text = ""
        if hasattr(self, 'result_text_id'):
            current_text = self.wheel_canvas.itemcget(self.result_text_id, "text")
        
        # 保存随机偏移角度
        self.wheel_angle = random_offset
        
        # 重绘转盘以应用随机偏移
        self.draw_wheel()
        
        # 恢复显示的文本内容
        if current_text and hasattr(self, 'result_text_id'):
            self.wheel_canvas.itemconfig(self.result_text_id, text=current_text, font=("宋体", 20, "bold"), fill="#FFEA00")
    
    def determine_selected_pokemon_by_pointer(self):
        """根据指针指向确定选中的宝可梦"""
        # 不再强制使用预设的宝可梦索引，而是根据转盘自然停止后的位置确定选中的宝可梦
        # 指针指向右侧（0度），所以需要计算转盘旋转后，哪个扇形区域位于指针位置
        
        # 获取当前旋转角度（相对于初始位置）
        # 转盘是顺时针旋转，角度计算是逆时针的，所以需要调整
        # 注意：转盘旋转角度是顺时针增加的，而数学上的角度是逆时针增加的
        current_rotation = self.wheel_angle % 360
        
        # 指针指向右侧（0度），所以我们需要找到位于0度位置的扇形
        # 注意：在Tkinter坐标系中，0度指向右侧，90度指向下方（与标准数学坐标系不同）
        pointer_angle = 0
        
        # 遍历所有扇形区域，找到最接近指针角度的扇形
        closest_section_index = 0
        closest_distance = float('inf')
        
        # 调试信息：打印当前旋转角度
        print(f"当前旋转角度: {self.wheel_angle}, 调整后角度: {current_rotation}")
        
        for i, section in enumerate(self.wheel_sections):
            # 计算扇形区域的当前角度范围（考虑旋转）
            # 在Tkinter坐标系中，角度是顺时针增加的，与转盘旋转方向一致
            # 所以我们需要加上旋转角度来计算扇形的当前位置
            start_angle = (section["start_angle"] + current_rotation) % 360
            end_angle = (section["end_angle"] + current_rotation) % 360
            
            # 调试信息：打印每个扇形的角度范围
            print(f"扇形 {i} ({section['pokemon']['nickname']}): 原始范围 {section['start_angle']}-{section['end_angle']}, 旋转后范围 {start_angle}-{end_angle}")
            
            # 计算扇形中间角度
            if start_angle > end_angle:
                # 处理跨越0度的情况
                middle_angle = (start_angle + end_angle + 360) / 2
                if middle_angle > 360:
                    middle_angle -= 360
            else:
                middle_angle = (start_angle + end_angle) / 2
            
            # 计算扇形中间角度与指针角度的距离
            # 由于转盘是顺时针旋转，我们需要调整距离计算方式
            distance = min(abs(middle_angle - pointer_angle), 360 - abs(middle_angle - pointer_angle))
            
            # 调试信息：打印更多角度信息
            print(f"扇形 {i} ({section['pokemon']['nickname']}): 中间角度={middle_angle}, 指针角度={pointer_angle}, 距离={distance}")
            
            # 调试信息：打印距离
            print(f"扇形 {i} 中间角度: {middle_angle}, 与指针距离: {distance}")
            
            # 如果距离更近，则更新最接近的扇形
            if distance < closest_distance:
                closest_distance = distance
                closest_section_index = i
        
        # 调试信息：打印选中的扇形
        print(f"选中扇形: {closest_section_index}, 宝可梦: {self.wheel_sections[closest_section_index]['pokemon']['nickname']}")
        
        # 选择最接近指针的扇形
        self.selected_pokemon_index = closest_section_index
        
        # 将选中的宝可梦添加到中奖名单
        self.add_to_winner_list()
    
    def reset_wheel(self):
        """重置转盘"""
        # 清空中奖名单
        self.winner_list = []
        self.update_winner_list_display()
        
        # 清空已抽取列表
        self.drawn_pokemon = []
        
        # 重置选中索引
        self.selected_pokemon_index = -1
        
        # 清空转盘画布内的选中结果显示（仅在转盘模式下）
        if self.current_mode.get() == 0 and hasattr(self, 'result_text_id') and hasattr(self, 'wheel_canvas'):
            try:
                self.wheel_canvas.itemconfig(self.result_text_id, text="")
            except:
                pass  # 如果画布对象无效，忽略错误
        
        # 清空翻牌模式下的选中显示
        if self.current_mode.get() == 1 and hasattr(self, 'selected_pokemon_label'):
            self.selected_pokemon_label.config(text="")
        
        # 重新启用位置选择下拉框
        self.location_combobox.config(state="readonly")
        
        # 重新启用块禁用和块启用按钮
        self.disable_all_button.config(state="normal")
        self.enable_all_button.config(state="normal")
        
        # 重新启用抽取重置按钮
        self.reset_wheel_button.config(state="normal")
        
        # 如果有宝可梦之家的实例，通知其取消所有选中状态
        if hasattr(self, 'pokemon_home_instance') and self.pokemon_home_instance:
            self.pokemon_home_instance.unselect_all_pokemon()
        
        # 如果当前是转盘模式，重新绘制转盘
        if self.current_mode.get() == 0:  # 转盘模式
            self.draw_wheel()
        
        # 如果当前是翻牌模式，重随一批卡片
        if self.current_mode.get() == 1:  # 翻牌模式
            self.resample_cards()
    
    def add_to_winner_list(self):
        """将选中的宝可梦添加到中奖名单"""
        if self.selected_pokemon_index >= 0 and self.selected_pokemon_index < len(self.wheel_sections):
            selected_pokemon = self.wheel_sections[self.selected_pokemon_index]["pokemon"]
            
            # 添加到中奖名单
            self.winner_list.append(selected_pokemon)
            
            # 添加到已抽取列表
            self.drawn_pokemon.append(selected_pokemon)
            
            # 更新中奖名单显示
            self.update_winner_list_display()
            
            # 在转盘画布内显示选中的宝可梦
            if hasattr(self, 'result_text_id'):
                self.wheel_canvas.itemconfig(self.result_text_id, text=f"{selected_pokemon['nickname']}", font=("宋体", 20, "bold"), fill="#FFEA00")
            
            # 通知宝可梦之家选中该宝可梦（不取消之前的选中状态）
            if self.pokemon_home_instance:
                self.pokemon_home_instance.select_pokemon(selected_pokemon)
    
    def initialize_cards(self):
        """初始化翻牌区域"""
        # 清空现有卡片
        for widget in self.card_frame.winfo_children():
            widget.destroy()
            
        # 重置卡片相关变量
        self.cards = []
        self.card_pokemon = []
        self.revealed_cards = []
        self.card_colors = []
        
        # 获取所有可用的宝可梦（不在禁用列表和中奖列表中的宝可梦）
        available_pokemon = self.get_all_available_pokemon()
        
        # 检查是否有可用的宝可梦
        if not available_pokemon:
            # 无可抽取宝可梦时显示提示
            self.selected_pokemon_label.config(text="无可抽取宝可梦", foreground="red")
            return
        
        # 随机打乱可用宝可梦列表
        import random
        random.shuffle(available_pokemon)
        
        # 确定需要显示的宝可梦数量（最多25个，即5×5）
        card_count = min(25, len(available_pokemon))
        
        # 如果可用宝可梦数量不足25个，则全部显示
        # 如果超过25个，则随机选择25个
        if len(available_pokemon) > 25:
            selected_pokemon = available_pokemon[:25]
        else:
            selected_pokemon = available_pokemon
            
        # 为每张卡片分配宝可梦
        self.card_pokemon = selected_pokemon
        
        # 为每张卡片分配颜色（从转盘颜色中随机选择）
        for i in range(card_count):
            color = random.choice(WHEEL_COLORS)
            self.card_colors.append(color)
        
        # 创建5×5的卡片网格（包含实块和虚块）
        total_slots = 25  # 5×5总共25个位置
        
        # 创建所有位置的列表（0-24）
        all_positions = list(range(total_slots))
        
        # 随机打乱位置，让实块和虚块混合分布
        import random
        random.shuffle(all_positions)
        
        # 设置网格权重，让所有单元格均匀分布
        for i in range(5):
            self.card_frame.grid_rowconfigure(i, weight=1, uniform="card_row")
            self.card_frame.grid_columnconfigure(i, weight=1, uniform="card_col")
        
        # 创建所有卡片（实块和虚块）
        for position_index in range(total_slots):
            row = position_index // 5
            col = position_index % 5
            
            # 检查这个位置是否应该放置实块
            slot_index = all_positions[position_index]
            is_real_card = slot_index < len(self.card_pokemon)
            
            if is_real_card:
                # 创建实块卡片
                card_index = slot_index
                card = Frame(self.card_frame, bg=self.card_colors[card_index], relief=tk.RAISED, bd=2)
                card.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                
                # 创建卡片内容（初始为背面，显示问号）
                card_content = tk.Label(card, text="?", bg=self.card_colors[card_index], 
                                      font=("宋体", 14, "bold"), fg="white")
                card_content.pack(expand=True, fill=tk.BOTH)
                
                # 保存卡片引用（记录卡片在网格中的位置和对应的宝可梦索引）
                card_info = {
                    "frame": card, 
                    "content": card_content, 
                    "revealed": False, 
                    "real": True,
                    "pokemon_index": card_index,  # 对应的宝可梦在card_pokemon列表中的索引
                    "grid_position": position_index  # 卡片在网格中的位置（0-24）
                }
                self.cards.append(card_info)
                
                # 绑定点击事件，传递卡片在self.cards列表中的索引
                card.bind("<Button-1>", lambda e, idx=len(self.cards)-1: self.on_card_click(idx))
                card_content.bind("<Button-1>", lambda e, idx=len(self.cards)-1: self.on_card_click(idx))
            else:
                # 创建虚块（占位符，灰色背景，没有点击事件）
                placeholder = Frame(self.card_frame, bg="#D3D3D3", relief=tk.FLAT, bd=1)
                placeholder.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                
                # 保存虚块引用（用于布局但不可点击）
                self.cards.append({
                    "frame": placeholder, 
                    "content": None, 
                    "revealed": False, 
                    "real": False,
                    "pokemon_index": -1,  # 虚块没有对应的宝可梦
                    "grid_position": position_index  # 卡片在网格中的位置（0-24）
                })
    
    def on_card_click(self, index):
        """处理卡片点击事件"""
        # 如果卡片已经翻开，则不处理
        if self.cards[index]["revealed"]:
            return
            
        # 检查是否为虚块，虚块不可点击
        if not self.cards[index]["real"]:
            return
            
        # 获取卡片对应的宝可梦索引
        pokemon_index = self.cards[index]["pokemon_index"]
            
        # 翻开卡片（手动翻开）
        self.reveal_card(index, auto_reveal=False)
        
        # 将宝可梦添加到中奖列表
        self.add_to_winner_list_from_card(pokemon_index)
        
        # 禁用已翻开的卡片
        self.cards[index]["frame"].unbind("<Button-1>")
        if self.cards[index]["content"]:
            self.cards[index]["content"].unbind("<Button-1>")
        
        # 在顶部显示选中的宝可梦昵称
        self.selected_pokemon_label.config(text=self.card_pokemon[pokemon_index]["nickname"])
    
    def reveal_card(self, index, auto_reveal=False):
        """翻开指定索引的卡片
        
        Args:
            index: 卡片在self.cards列表中的索引
            auto_reveal: 是否为自动翻开（一键翻开全部），默认为False
        """
        if index < 0 or index >= len(self.cards):
            return
            
        # 检查是否为虚块，虚块不可翻开
        if not self.cards[index]["real"]:
            return
            
        # 标记卡片为已翻开
        self.cards[index]["revealed"] = True
        self.revealed_cards.append(index)
        
        # 获取卡片对应的宝可梦索引
        pokemon_index = self.cards[index]["pokemon_index"]
        
        # 获取宝可梦昵称，如果太长则截断（最多6个中文字符）
        nickname = self.card_pokemon[pokemon_index]["nickname"]
        if len(nickname) > 6:  # 如果昵称超过6个字符，则截断
            nickname = nickname[:6] + "..."
        
        # 根据翻开方式设置不同的样式
        if auto_reveal:
            # 自动翻开（一键翻开全部）：灰色背景，较小字体
            self.cards[index]["content"].config(text=nickname, 
                                                 bg="#F0F0F0", fg="#666666", 
                                                 font=("宋体", 9, "bold"))
        else:
            # 手动翻开：白色背景，较大字体
            self.cards[index]["content"].config(text=nickname, 
                                                 bg="white", fg="black", 
                                                 font=("宋体", 12, "bold"))
    
    def add_to_winner_list_from_card(self, index):
        """将翻牌选中的宝可梦添加到中奖名单"""
        if index < 0 or index >= len(self.card_pokemon):
            return
            
        selected_pokemon = self.card_pokemon[index]
        
        # 添加到中奖名单
        self.winner_list.append(selected_pokemon)
        
        # 添加到已抽取列表
        self.drawn_pokemon.append(selected_pokemon)
        
        # 更新中奖名单显示
        self.update_winner_list_display()
        
        # 通知宝可梦之家选中该宝可梦（不取消之前的选中状态）
        if self.pokemon_home_instance:
            self.pokemon_home_instance.select_pokemon(selected_pokemon)
            
        # 禁用位置选择下拉框
        self.location_combobox.config(state="disabled")
        
        # 禁用块禁用和块启用按钮
        self.disable_all_button.config(state="disabled")
        self.enable_all_button.config(state="disabled")
    
    def resample_cards(self):
        """重随一批卡片"""
        # 获取所有可用的宝可梦（不在禁用列表和中奖列表中的宝可梦）
        available_pokemon = self.get_all_available_pokemon()
        
        # 检查是否有可用的宝可梦
        if not available_pokemon:
            # 无可抽取宝可梦时显示提示
            self.selected_pokemon_label.config(text="无可抽取宝可梦", foreground="red")
            return
        
        # 随机打乱可用宝可梦列表
        import random
        random.shuffle(available_pokemon)
        
        # 确定需要显示的宝可梦数量（最多25个，即5×5）
        card_count = min(25, len(available_pokemon))
        
        # 如果可用宝可梦数量不足25个，则全部显示
        # 如果超过25个，则随机选择25个
        if len(available_pokemon) > 25:
            selected_pokemon = available_pokemon[:25]
        else:
            selected_pokemon = available_pokemon
            
        # 更新卡片对应的宝可梦
        self.card_pokemon = selected_pokemon
        
        # 重置已翻开卡片列表
        self.revealed_cards = []
        
        # 清空顶部显示的宝可梦昵称
        self.selected_pokemon_label.config(text="")
        
        # 重新创建卡片
        self.initialize_cards()
    
    def reveal_all_cards(self):
        """揭开所有卡片"""
        # 翻开所有未翻开的实块卡片
        for i in range(len(self.cards)):
            if self.cards[i]["real"] and not self.cards[i]["revealed"]:
                self.reveal_card(i, auto_reveal=True)
                
                # 禁用已翻开的卡片
                self.cards[i]["frame"].unbind("<Button-1>")
                if self.cards[i]["content"]:
                    self.cards[i]["content"].unbind("<Button-1>")
    
    def flip_cards(self):
        """翻牌（保留方法名以兼容现有代码）"""
        # 此方法已不再使用，翻牌逻辑由on_card_click方法处理
        pass
        
    def on_location_change(self, event):
        """位置选择变化事件"""
        selected_value = self.location_combobox.get()
        self.current_location.set(selected_value)
        
        # 只在转盘模式下操作转盘画布
        if self.current_mode.get() == 0 and hasattr(self, 'wheel_canvas'):
            # 保存当前显示的文本
            current_text = ""
            if hasattr(self, 'result_text_id'):
                try:
                    current_text = self.wheel_canvas.itemcget(self.result_text_id, "text")
                except:
                    current_text = ""
            
            # 不再自动重绘转盘，只在必要时更新按钮状态
            self.update_button_states()
            
            # 恢复之前显示的文本（如果存在）
            if hasattr(self, 'result_text_id') and current_text:
                try:
                    self.wheel_canvas.itemconfig(self.result_text_id, text=current_text)
                except:
                    pass
        else:
            # 在翻牌模式下只更新按钮状态
            self.update_button_states()
        
    def update_nickname_list(self):
        """更新宝可梦昵称列表（已移除昵称下拉框功能）"""
        # 此方法已不再使用，因为移除了单只宝可梦的禁用功能
        pass
            
    def update_all_nickname_list(self):
        """更新所有宝可梦昵称列表（已移除昵称下拉框功能）"""
        # 此方法已不再使用，因为移除了单只宝可梦的禁用功能
        pass
            
    def on_nickname_key_release(self, event):
        """昵称输入框键盘释放事件，用于搜索（已移除昵称下拉框功能）"""
        # 此方法已不再使用，因为移除了单只宝可梦的禁用功能
        pass
        
    def disable_all(self):
        """块禁用"""
        # 获取当前选中的位置
        location = self.current_location.get()
        
        # 处理不同格式的位置信息
        if isinstance(location, int):
            # 已经是数字格式，直接使用
            location_id = location
        elif isinstance(location, str):
            # 字符串格式，需要转换
            if location == "队伍":
                location_id = 0
            elif location.startswith("盒子"):
                try:
                    box_num = int(location[2:])  # 提取盒子编号
                    location_id = box_num
                except ValueError:
                    return
            else:
                return
        else:
            return
        
        # 获取该位置的宝可梦列表
        pokemon_list = self.get_pokemon_list(location_id)
        
        if not pokemon_list:
            return
            
        # 统计新增的禁用数量
        new_disabled_count = 0
        
        # 禁用该位置的所有宝可梦
        for pokemon in pokemon_list:
            # 检查是否已经在禁用列表中
            is_duplicate = False
            for disabled_pokemon in self.disabled_pokemon:
                if (disabled_pokemon["nickname"] == pokemon["nickname"] and 
                    disabled_pokemon["species"] == pokemon["species"]):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # 创建宝可梦副本并添加位置信息
                pokemon_copy = pokemon.copy()
                if location_id == 0:
                    pokemon_copy['location'] = "team:0"
                else:
                    pokemon_copy['location'] = f"box:{location_id-1}"
                
                self.disabled_pokemon.append(pokemon_copy)
                new_disabled_count += 1
        
        if new_disabled_count == 0:
            return
            
        # 保存禁用信息
        self.save_disabled_info()
        
        # 更新显示
        self.update_disabled_list_display()
        
        # 更新昵称下拉框
        self.update_all_nickname_list()
        
        # 根据当前模式更新显示
        if self.current_mode.get() == 0:
            # 转盘模式下重绘转盘
            self.draw_wheel()
        else:
            # 翻牌模式下重随卡片
            self.resample_cards()
        
    # 移除了单只宝可梦的禁用功能
        
    # 移除了单只宝可梦的启用功能
    
    def enable_all(self):
        """块启用"""
        # 获取当前选中的位置
        location = self.current_location.get()
        
        # 处理不同格式的位置信息
        if isinstance(location, int):
            # 已经是数字格式，直接使用
            location_id = location
        elif isinstance(location, str):
            # 字符串格式，需要转换
            if location == "队伍":
                location_id = 0
            elif location.startswith("盒子"):
                try:
                    box_num = int(location[2:])  # 提取盒子编号
                    location_id = box_num
                except ValueError:
                    return
            else:
                return
        else:
            return
        
        # 获取该位置的宝可梦列表
        pokemon_list = self.get_pokemon_list(location_id)
        
        if not pokemon_list:
            return
            
        # 统计启用的数量
        enabled_count = 0
        
        # 启用该位置的所有宝可梦
        for pokemon in pokemon_list:
            # 使用更可靠的比较方式检查是否在禁用列表中
            for i, disabled_pokemon in enumerate(self.disabled_pokemon):
                if (disabled_pokemon["nickname"] == pokemon["nickname"] and 
                    disabled_pokemon["species"] == pokemon["species"]):
                    self.disabled_pokemon.pop(i)
                    enabled_count += 1
                    break
        
        if enabled_count == 0:
            return
            
        # 保存禁用信息
        self.save_disabled_info()
        
        # 更新显示
        self.update_disabled_list_display()
        
        # 更新昵称下拉框
        self.update_all_nickname_list()
        
        # 根据当前模式更新显示
        if self.current_mode.get() == 0:
            # 转盘模式下重绘转盘
            self.draw_wheel()
        else:
            # 翻牌模式下重随卡片
            self.resample_cards()
        
    def update_disabled_list_display(self):
        """更新禁用列表显示"""
        self.disabled_listbox.delete(0, tk.END)
        
        # 按位置分组禁用的宝可梦
        team_pokemon = []
        box_pokemon = {}
        
        for pokemon in self.disabled_pokemon:
            location = pokemon.get("location", "")
            if location.startswith("team:"):
                team_pokemon.append(pokemon["nickname"])
            elif location.startswith("box:"):
                try:
                    box_num = int(location[4:])
                    if box_num not in box_pokemon:
                        box_pokemon[box_num] = []
                    box_pokemon[box_num].append(pokemon["nickname"])
                except ValueError:
                    pass
        
        # 显示队伍中的禁用宝可梦
        if team_pokemon:
            self.disabled_listbox.insert(tk.END, "队伍：")
            for pokemon in team_pokemon:
                self.disabled_listbox.insert(tk.END, pokemon)
            self.disabled_listbox.insert(tk.END, "")  # 空行分隔
        
        # 显示盒子中的禁用宝可梦，按盒子编号排序
        for box_num in sorted(box_pokemon.keys()):
            self.disabled_listbox.insert(tk.END, f"盒子{box_num+1}：")
            for pokemon in box_pokemon[box_num]:
                self.disabled_listbox.insert(tk.END, pokemon)
            self.disabled_listbox.insert(tk.END, "")  # 空行分隔
            
    def setup_winner_list(self):
        """设置中奖名单区域（右侧竖直小块）"""
        winner_frame = ttk.LabelFrame(self.main_content_frame, text="中奖名单")
        winner_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # 创建滚动条和列表框
        scrollbar = Scrollbar(winner_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.winner_listbox = Listbox(winner_frame, yscrollcommand=scrollbar.set, height=15, width=15)
        self.winner_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.winner_listbox.yview)
        
        # 更新中奖名单显示
        self.update_winner_list_display()
        
    def update_winner_list_display(self):
        """更新中奖名单显示"""
        self.winner_listbox.delete(0, tk.END)
        
        # 显示中奖宝可梦的昵称
        for winner in self.winner_list:
            self.winner_listbox.insert(tk.END, winner["nickname"])
            
    def load_disabled_info(self):
        try:
            disabled_blocks = get_disabled_blocks()
            self.disabled_pokemon = []
            for block_location in disabled_blocks:
                if isinstance(block_location, int) or (isinstance(block_location, str) and block_location.isdigit()):
                    block_num = int(block_location)
                    if block_num == 0 and "team" in pokemon_data:
                        for pokemon in pokemon_data["team"]:
                            if pokemon:
                                pokemon_copy = pokemon.copy()
                                pokemon_copy["location"] = "team:0"
                                is_duplicate = False
                                for disabled_pokemon in self.disabled_pokemon:
                                    if disabled_pokemon["nickname"] == pokemon_copy["nickname"] and disabled_pokemon["species"] == pokemon_copy["species"]:
                                        is_duplicate = True
                                        break
                                if not is_duplicate:
                                    self.disabled_pokemon.append(pokemon_copy)
                    elif 1 <= block_num <= 32 and "boxes" in pokemon_data:
                        if any(key.startswith("box") and not key.startswith("box_") for key in pokemon_data["boxes"].keys()):
                            box_key = f"box{block_num}"
                            if box_key in pokemon_data["boxes"]:
                                box = pokemon_data["boxes"][box_key]
                                for pokemon in box:
                                    if pokemon:
                                        pokemon_copy = pokemon.copy()
                                        pokemon_copy["location"] = f"box:{block_num-1}"
                                        is_duplicate = False
                                        for disabled_pokemon in self.disabled_pokemon:
                                            if disabled_pokemon["nickname"] == pokemon_copy["nickname"] and disabled_pokemon["species"] == pokemon_copy["species"]:
                                                is_duplicate = True
                                                break
                                        if not is_duplicate:
                                            self.disabled_pokemon.append(pokemon_copy)
                        elif any(key.startswith("box_") for key in pokemon_data["boxes"].keys()):
                            box_key = f"box_{block_num}"
                            if box_key in pokemon_data["boxes"]:
                                box = pokemon_data["boxes"][box_key]
                                for pokemon in box:
                                    if pokemon:
                                        pokemon_copy = pokemon.copy()
                                        pokemon_copy["location"] = f"box:{block_num-1}"
                                        is_duplicate = False
                                        for disabled_pokemon in self.disabled_pokemon:
                                            if disabled_pokemon["nickname"] == pokemon_copy["nickname"] and disabled_pokemon["species"] == pokemon_copy["species"]:
                                                is_duplicate = True
                                                break
                                        if not is_duplicate:
                                            self.disabled_pokemon.append(pokemon_copy)
            self.update_disabled_list_display()
        except Exception as e:
            print(f"加载禁用信息时出错: {str(e)}")
            
    def save_disabled_info(self):
        try:
            disabled_blocks = set()
            for pokemon in self.disabled_pokemon:
                location = pokemon.get("location", "")
                if location.startswith("team:"):
                    disabled_blocks.add(0)
                elif location.startswith("box:"):
                    try:
                        box_num = int(location[4:]) + 1
                        if 1 <= box_num <= 32:
                            disabled_blocks.add(box_num)
                    except ValueError:
                        pass
            set_disabled_blocks(list(disabled_blocks))
        except Exception as e:
            print(f"保存禁用信息时出错: {str(e)}")
            messagebox.showerror("错误", f"保存禁用信息时出错: {str(e)}")


def setup_ccb(parent, pokemon_home_instance=None):
    """设置CCB标签页的函数"""
    ccb = CCB(parent, pokemon_home_instance)
    return ccb
