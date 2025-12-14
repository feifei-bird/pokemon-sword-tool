import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import re
import struct
import random
from collections import defaultdict, Counter
import threading

try:
    from type_exclusive_function import select_item, get_item_category, select_attribute_item, calculate_weaknesses, reload_config, reload_pokemon_types_data
    from file_manager import safe_load_file, safe_save_file
    from utils.path_resolver import (
        get_trainer_poke_dir,
        get_personal_total_path,
        get_main_file_path,
        set_trainer_poke_dir,
        set_personal_total_path,
        set_main_file_path,
        migrate_legacy_paths,
    )
    from core.static_data import (
        type_map,
        type_code_map,
        nature_map,
        nature_effect_map,
        type_attack_effectiveness,
        type_effectiveness_map,
        type_defense_effectiveness,
        v_names,
    )
except ImportError:
    messagebox.showerror("错误", "缺少必要模块，请确保所有必要文件都在同一目录下")

try:
    migrate_legacy_paths()
except Exception:
    pass

# 全局变量
config = {}
pokemon_types_data = {}
item_id_to_name = {}
pokemon_name_map = {}
pokemon_abilities_data = {}
ability_map = {}
move_map = {}
move_explanation_map = {}
ability_explanation_map = {}
pokemon_main_info = {}
trainer_poke_dir = get_trainer_poke_dir()
personal_total_bin_path = get_personal_total_path()
main_file_path = get_main_file_path()
file_numbers = []

# 宝可梦数据结构常量
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

# personal_total.bin 数据结构常量
PERSONAL_RECORD_SIZE = 0xB0
TYPE_OFFSET_1 = 6
TYPE_OFFSET_2 = 7
ABILITY_OFFSET_1 = 0x18
ABILITY_OFFSET_2 = 0x1A
ABILITY_OFFSET_H = 0x1C


# 主应用程序类
class PokemonToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("宝可梦剑工具")
        self.root.geometry("1200x800")

        # 创建标签页
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.status_timers = {}  # 用于存储定时器ID
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 主页标签页
        self.setup_home_tab()

        # 训练家文件查看标签页
        self.setup_trainer_view_tab()

        # 道具分布验证标签页
        self.setup_verify_tab()

        # 属性克制表标签页
        self.setup_type_chart_tab()

        # 宝可梦之家标签页
        self.setup_pokemon_home_tab()
        
        # CCB标签页
        self.setup_ccb_tab()

        # 初始化
        self.load_data()

    def setup_home_tab(self):
        """设置首页标签页"""
        self.home_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.home_tab, text="首页")

        # 路径设置部分
        path_frame = ttk.LabelFrame(self.home_tab, text="路径设置")
        path_frame.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)

        ttk.Label(path_frame, text="训练家文件目录:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.trainer_dir_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.trainer_dir_var, width=60).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_trainer_dir).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(path_frame, text="保存训练家目录", command=self.save_trainer_dir).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(path_frame, text="personal_total.bin文件:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.personal_file_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.personal_file_var, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_personal_file).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(path_frame, text="保存personal路径", command=self.save_personal_file).grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Label(path_frame, text="main文件:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.main_file_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.main_file_var, width=60).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_main_file).grid(row=2, column=2, padx=5, pady=5)
        ttk.Button(path_frame, text="保存main路径", command=self.save_main_file).grid(row=2, column=3, padx=5, pady=5)

        ttk.Button(path_frame, text="保存全部路径", command=self.save_paths).grid(row=3, column=1, pady=10)

        # 状态显示 - 移到下一行避免遮挡按钮
        self.path_status_var = tk.StringVar()
        ttk.Label(path_frame, textvariable=self.path_status_var).grid(row=4, column=0, columnspan=3, pady=5)

        # 配置文件生成部分
        config_frame = ttk.LabelFrame(self.home_tab, text="配置文件生成")
        config_frame.grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)

        ttk.Button(config_frame, text="生成道具配置文件", command=self.generate_config).grid(row=0, column=0, padx=5, pady=5)
        self.generate_types_btn = ttk.Button(config_frame, text="生成属性配置文件", command=lambda: self.generate_personal_data(gen_types=True, gen_abilities=False))
        self.generate_types_btn.grid(row=0, column=1, padx=5, pady=5)
        self.generate_abilities_btn = ttk.Button(config_frame, text="生成特性配置文件", command=lambda: self.generate_personal_data(gen_types=False, gen_abilities=True))
        self.generate_abilities_btn.grid(row=0, column=2, padx=5, pady=5)

        # 配置文件状态
        self.config_status_var = tk.StringVar()
        ttk.Label(config_frame, textvariable=self.config_status_var).grid(row=1, column=0, columnspan=3, pady=5)

        # 道具随机化部分
        random_frame = ttk.LabelFrame(self.home_tab, text="道具随机化")
        random_frame.grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)

        # 替换策略框架
        strategy_frame = ttk.Frame(random_frame)
        strategy_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # 策略替换选项
        self.strategy_var = tk.StringVar(value="strategy")
        ttk.Radiobutton(strategy_frame, text="策略替换(五类权重系统)", variable=self.strategy_var, 
                       value="strategy", command=self.on_strategy_change).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 随机替换选项
        ttk.Radiobutton(strategy_frame, text="随机替换(有效列表中随机)", variable=self.strategy_var, 
                       value="random", command=self.on_strategy_change).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 单一替换选项
        ttk.Radiobutton(strategy_frame, text="单一替换(指定道具)", variable=self.strategy_var, 
                       value="single", command=self.on_strategy_change).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 单一道具ID输入
        ttk.Label(strategy_frame, text="道具ID:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.single_item_id_var = tk.StringVar(value="234")
        self.single_item_entry = ttk.Entry(strategy_frame, textvariable=self.single_item_id_var, width=10, state="disabled")
        self.single_item_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Button(random_frame, text="开始随机化", command=self.randomize_items).grid(row=1, column=0, padx=5, pady=10)

        # 随机化状态
        self.random_status_var = tk.StringVar()
        ttk.Label(random_frame, textvariable=self.random_status_var).grid(row=2, column=0, pady=5)

        # 结果显示区域
        self.random_text = scrolledtext.ScrolledText(random_frame, width=80, height=10)
        self.random_text.grid(row=3, column=0, padx=5, pady=5)

    def setup_trainer_view_tab(self):
        """设置训练家宝可梦查看标签页"""
        self.trainer_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.trainer_tab, text="训练家宝可梦查看")
        
        # 创建顶部控制框架
        control_frame = ttk.Frame(self.trainer_tab)
        control_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 文件选择
        ttk.Label(control_frame, text="选择文件编号：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_num_var = tk.StringVar()
        self.file_num_combo = ttk.Combobox(control_frame, textvariable=self.file_num_var, state="readonly", width=10)
        self.file_num_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 查看按钮
        self.view_trainer_btn = ttk.Button(control_frame, text="查看", command=self.view_trainer_file)
        self.view_trainer_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # 刷新文件列表按钮
        self.refresh_file_list_btn = ttk.Button(control_frame, text="刷新文件列表", command=self.refresh_file_list)
        self.refresh_file_list_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # 编码ID复选框
        self.show_ids_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="编码ID", variable=self.show_ids_var).grid(row=0, column=4, padx=5, pady=5)
        
        # 创建用于放置宝可梦信息的框架
        self.pokemon_container = ttk.Frame(self.trainer_tab)
        self.pokemon_container.grid(row=1, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        # 配置网格权重
        self.trainer_tab.grid_rowconfigure(1, weight=1)
        self.trainer_tab.grid_columnconfigure(0, weight=1)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(self.trainer_tab)
        scrollbar.grid(row=1, column=3, sticky=tk.N+tk.S)
        
        # 创建画布用于滚动
        self.canvas = tk.Canvas(self.trainer_tab, yscrollcommand=scrollbar.set)
        self.canvas.grid(row=1, column=0, columnspan=3, sticky=tk.N+tk.S+tk.E+tk.W)
        scrollbar.config(command=self.canvas.yview)
        
        # 在画布上创建框架用于放置宝可梦信息
        self.pokemon_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.pokemon_frame, anchor="nw")
        
        # 绑定事件以调整画布大小
        self.pokemon_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 绑定鼠标滚轮事件
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.pokemon_frame.bind("<MouseWheel>", self.on_mousewheel)
    
    def on_frame_configure(self, event):
        """当框架大小改变时调整画布滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """当画布大小改变时调整内部框架宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def setup_verify_tab(self):
        """设置道具分布验证标签页"""
        self.verify_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.verify_tab, text="道具分布验证")
        
        ttk.Label(self.verify_tab, text="样本数量:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.sample_count_var = tk.StringVar(value="20")
        ttk.Entry(self.verify_tab, textvariable=self.sample_count_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        self.verify_button = ttk.Button(self.verify_tab, text="验证分布", command=self.verify_distribution)
        self.verify_button.grid(row=1, column=0, columnspan=2, padx=5, pady=10)
        
        # 验证状态
        self.verify_status_var = tk.StringVar()
        ttk.Label(self.verify_tab, textvariable=self.verify_status_var).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 结果显示区域
        self.verify_text = scrolledtext.ScrolledText(self.verify_tab, width=120, height=40)
        self.verify_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
    
    def setup_type_chart_tab(self):
        """设置属性克制表标签页"""
        self.type_chart_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.type_chart_tab, text="属性克制表")
        
        # 创建顶部说明
        title_label = ttk.Label(self.type_chart_tab, text="竖击横御", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=20, pady=10)
        
        # 创建模式说明
        self.mode_label = ttk.Label(self.type_chart_tab, text="当前模式：单属性计算（按Shift切换为双属性计算）", font=("Arial", 10))
        self.mode_label.grid(row=1, column=0, columnspan=20, pady=5)
        
        # 创建表格框架
        table_frame = ttk.Frame(self.type_chart_tab)
        table_frame.grid(row=2, column=0, columnspan=20, padx=10, pady=10)
        
        # 创建表格
        self.type_cells = {}
        self.selected_row = None
        self.selected_col = None
        self.cell_selection_state = {}
        self.dual_type_mode = False  # 双属性模式标志
        self.selected_defense_types = []  # 选中的防御属性列表
        self.resistance_column = None  # 抗性列引用

        self.types_order = [
            "一般", "格斗", "飞行", "毒", "地面", "岩石", 
            "虫", "幽灵", "钢", "火", "水", "草", 
            "电", "超能", "冰", "龙", "恶", "妖精"
        ]
        
        # 绑定Shift键事件
        self.root.bind("<Shift_L>", self.toggle_dual_type_mode)
        self.root.bind("<Shift_R>", self.toggle_dual_type_mode)
        
        # 创建空白的左上角单元格，并绑定点击事件
        empty_cell = ttk.Label(table_frame, text="", width=7, borderwidth=1, relief="solid")
        empty_cell.grid(row=0, column=0, padx=1, pady=1)
        empty_cell.bind("<Button-1>", lambda e: self.clear_selection())  # 点击清空所有选择
        self.type_cells[(0, 0)] = empty_cell
        
        # 创建第一行（防御属性）
        for col, type_name in enumerate(self.types_order, 1):
            label = ttk.Label(table_frame, text=type_name, width=7, borderwidth=1, 
                             relief="solid", anchor="center", background="lightgray")
            label.grid(row=0, column=col, padx=1, pady=1)
            label.bind("<Button-1>", lambda e, c=col: self.select_column(c))
            self.type_cells[(0, col)] = label
        
        # 创建第一列（攻击属性）和表格内容
        for row, type_name in enumerate(self.types_order, 1):
            # 攻击属性标签
            label = ttk.Label(table_frame, text=type_name, width=7, borderwidth=1, 
                             relief="solid", anchor="center", background="lightgray")
            label.grid(row=row, column=0, padx=1, pady=1)
            label.bind("<Button-1>", lambda e, r=row: self.select_row(r))
            self.type_cells[(row, 0)] = label
            
            # 表格内容
            effectiveness_list = type_effectiveness_map[type_name]
            for col, effectiveness in enumerate(effectiveness_list, 1):
                # 设置字体颜色
                fg_color = "white"  # 默认黑色
                
                if effectiveness == 2:
                    bg_color = "green"
                elif effectiveness == 0.5:
                    bg_color = "red"
                elif effectiveness == 0:
                    bg_color = "black"  # 0倍保持黑色
                elif effectiveness == 1:
                    fg_color = "black"  # 1倍使用白色
                    bg_color = "white"
                
                # 创建单元格
                cell = ttk.Label(table_frame, text=str(effectiveness), width=7, borderwidth=1, 
                                relief="solid", anchor="center", background=bg_color, foreground=fg_color)
                cell.grid(row=row, column=col, padx=1, pady=1)
                # 绑定点击事件
                cell.bind("<Button-1>", lambda e, r=row, c=col: self.on_cell_click(r, c))
                self.type_cells[(row, col)] = cell
                # 存储单元格的原始颜色信息
                cell.original_bg = bg_color
                cell.original_fg = fg_color
    
    def on_cell_click(self, row, col):
        """当点击单元格时，选择对应的行和列"""
        self.select_row(row)
        self.select_column(col)
    
    def select_row(self, row):
        """选择一行"""
        # 清除之前的选择
        if self.selected_row is not None:
            self.clear_row_selection(self.selected_row)
        
        # 高亮选中的行 - 使用浅蓝色背景
        for col in range(0, 20):  # 0到19列（包括抗性列）
            if (row, col) in self.type_cells:
                cell = self.type_cells[(row, col)]
                # 保存原始颜色信息
                if not hasattr(cell, 'original_bg'):
                    cell.original_bg = cell.cget("background")
                if not hasattr(cell, 'original_fg'):
                    cell.original_fg = cell.cget("foreground")
                
                # 更新单元格选中状态
                cell_key = (row, col)
                if cell_key not in self.cell_selection_state:
                    self.cell_selection_state[cell_key] = {'row': False, 'col': False}
                self.cell_selection_state[cell_key]['row'] = True
                
                # 设置选中样式
                cell.config(background="lightblue", relief="raised", borderwidth=2)

                # 根据数值设置文字颜色
                if row > 0 and col > 0:  # 只对数值单元格应用颜色
                    try:
                        value = float(cell.cget("text"))
                        if value == 0:
                            cell.config(foreground="black")
                        elif value == 0.5:
                            cell.config(foreground="red")
                        elif value == 1:
                            cell.config(foreground="white")
                        elif value == 2:
                            cell.config(foreground="green")
                    except ValueError:
                        pass  # 如果不是数值，保持原样
                
                # 如果是抗性列，特殊处理
                if col == self.resistance_column and row > 0:
                    # 获取抗性值
                    try:
                        resistance = float(cell.cget("text"))
                        # 使用原始背景色作为前景色
                        if resistance >= 4:  # 4倍弱点 - 橙色
                            cell.config(foreground="orange")
                        elif resistance <= 0.25:  # 0.25倍超级抗性 - 粉色
                            cell.config(foreground="pink")
                        elif resistance >= 2:  # 2倍弱点 - 绿色
                            cell.config(foreground="green")
                        elif resistance <= 0.5:  # 0.5倍抗性 - 红色
                            cell.config(foreground="red")
                        else:  # 1倍 - 白色
                            cell.config(foreground="white")
                    except ValueError:
                        pass  # 如果不是数值，保持原样
        
        self.selected_row = row
        
        # 在双属性模式下，如果存在选中的防御属性，恢复它们的高亮状态
        if self.dual_type_mode and len(self.selected_defense_types) > 0:
            for defense_col in self.selected_defense_types:
                for r in range(0, 19):
                    if (r, defense_col) in self.type_cells:
                        cell = self.type_cells[(r, defense_col)]
                        # 更新单元格选中状态
                        cell_key = (r, defense_col)
                        if cell_key not in self.cell_selection_state:
                            self.cell_selection_state[cell_key] = {'row': False, 'col': False}
                        self.cell_selection_state[cell_key]['col'] = True
                        
                        # 设置选中样式
                        cell.config(background="lightblue", relief="raised", borderwidth=2)
                        
                        # 根据数值设置文字颜色
                        if r > 0 and defense_col > 0:  # 只对数值单元格应用颜色
                            try:
                                value = float(cell.cget("text"))
                                if value == 0:
                                    cell.config(foreground="black")
                                elif value == 0.5:
                                    cell.config(foreground="red")
                                elif value == 1:
                                    cell.config(foreground="white")
                                elif value == 2:
                                    cell.config(foreground="green")
                            except ValueError:
                                pass  # 如果不是数值，保持原样
            
            # 恢复抗性列的显示
            if self.resistance_column is not None:
                self.update_resistance_column()
    
    def toggle_dual_type_mode(self, event):
        """切换单/双属性计算模式"""
        self.dual_type_mode = not self.dual_type_mode
        
        # 清空所有选中状态
        self.clear_selection()
        
        if self.dual_type_mode:
            self.mode_label.config(text="当前模式：双属性计算（按Shift切换为单属性计算）")
        else:
            self.mode_label.config(text="当前模式：单属性计算（按Shift切换为双属性计算）")
            self.selected_defense_types = []
            # 确保在切换回单属性模式时移除抗性列
            if self.resistance_column is not None:
                self.remove_resistance_column()
            # 确保清除所有防御属性列的高亮状态
            for col in range(1, 19):
                if (0, col) in self.type_cells:
                    self.clear_column_selection(col)
    
    def add_resistance_column(self):
        """添加抗性列"""
        if self.resistance_column is not None:
            return  # 已经存在抗性列
        
        table_frame = self.type_cells[(0, 0)].master
        
        # 添加抗性列标题
        resistance_header = ttk.Label(table_frame, text="抗性", width=7, borderwidth=1, 
                                     relief="solid", anchor="center", background="lightgray")
        resistance_header.grid(row=0, column=19, padx=1, pady=1)
        self.type_cells[(0, 19)] = resistance_header
        
        # 为每一行添加抗性值单元格
        for row in range(1, 19):
            cell = ttk.Label(table_frame, text="1.0", width=7, borderwidth=1, 
                            relief="solid", anchor="center", background="white", foreground="black")
            cell.grid(row=row, column=19, padx=1, pady=1)
            self.type_cells[(row, 19)] = cell
            cell.original_bg = "white"
            cell.original_fg = "black"
        
        self.resistance_column = 19
    
    def remove_resistance_column(self):
        """移除抗性列"""
        if self.resistance_column is None:
            return  # 不存在抗性列
        
        # 移除抗性列的所有单元格
        for row in range(0, 19):
            if (row, self.resistance_column) in self.type_cells:
                self.type_cells[(row, self.resistance_column)].grid_forget()
                del self.type_cells[(row, self.resistance_column)]
        
        self.resistance_column = None
    
    def update_resistance_column(self):
        """更新抗性列的值"""
        if self.resistance_column is None or len(self.selected_defense_types) == 0:
            return
        
        # 计算每个防御属性对选中防御属性的抗性
        for row in range(1, 19):
            defense_type_index = row - 1
            defense_type = self.types_order[defense_type_index]
            
            # 计算双属性抗性
            resistance = 1.0
            for selected_col in self.selected_defense_types:
                selected_defense_type_index = selected_col - 1
                selected_defense_type = self.types_order[selected_defense_type_index]
                
                # 获取当前防御属性对选中防御属性的相克倍率
                defense_effectiveness = type_effectiveness_map[defense_type][selected_defense_type_index]
                resistance *= defense_effectiveness
            
            # 更新抗性列的值和颜色
            cell = self.type_cells[(row, self.resistance_column)]
            cell.config(text=f"{resistance:.2f}")
            
            # 保存原始颜色信息（如果还没有保存）
            if not hasattr(cell, 'original_bg'):
                cell.original_bg = cell.cget("background")
            if not hasattr(cell, 'original_fg'):
                cell.original_fg = cell.cget("foreground")
            
            # 检查当前行是否被选中
            cell_key = (row, self.resistance_column)
            has_row_selection = (
                cell_key in self.cell_selection_state and 
                self.cell_selection_state[cell_key]['row']
            ) if self.selected_row is not None else False
            
            if has_row_selection:
                # 如果行被选中，使用浅蓝色背景，原始背景色作为前景色
                cell.config(background="lightblue", relief="raised", borderwidth=2)
                # 使用原始背景色作为前景色
                if hasattr(cell, 'original_bg'):
                    # 根据抗性值确定原始背景色
                    if resistance >= 4:  # 4倍弱点 - 橙色
                        cell.config(foreground="orange")
                    elif resistance <= 0.25:  # 0.25倍超级抗性 - 粉色
                        cell.config(foreground="pink")
                    elif resistance >= 2:  # 2倍弱点 - 绿色
                        cell.config(foreground="green")
                    elif resistance <= 0.5:  # 0.5倍抗性 - 红色
                        cell.config(foreground="red")
                    else:  # 1倍 - 白色
                        cell.config(foreground="white")
            else:
                # 如果行未被选中，根据抗性值设置颜色
                if resistance >= 4:  # 4倍弱点 - 橙色
                    cell.config(background="orange", foreground="white")
                elif resistance <= 0.25:  # 0.25倍超级抗性 - 粉色
                    cell.config(background="pink", foreground="black")
                elif resistance >= 2:  # 2倍弱点 - 绿色
                    cell.config(background="green", foreground="white")
                elif resistance <= 0.5:  # 0.5倍抗性 - 红色
                    cell.config(background="red", foreground="white")
                else:  # 1倍 - 白色
                    cell.config(background="white", foreground="black")
                
                # 恢复边框样式
                cell.config(relief="solid", borderwidth=1)
    
    def select_column(self, col):
        """选择一列"""
        # 在双属性模式下处理防御属性选择
        if self.dual_type_mode and col > 0 and col <= 18:
            # 如果点击的是已选中的列，则取消选中
            if col in self.selected_defense_types:
                self.selected_defense_types.remove(col)
                # 清除该列的高亮
                self.clear_column_selection(col)
                # 如果没有选中的防御属性了，移除抗性列
                if len(self.selected_defense_types) == 0:
                    self.remove_resistance_column()
                else:
                    # 更新抗性列
                    self.update_resistance_column()
                return
            
            # 如果已经选中了两列，移除最先选中的
            if len(self.selected_defense_types) >= 2:
                removed_col = self.selected_defense_types.pop(0)
                self.clear_column_selection(removed_col)
            
            # 添加新选中的列
            self.selected_defense_types.append(col)
            
            # 高亮选中的防御属性列
            for row in range(0, 19):  # 0到18行
                if (row, col) in self.type_cells:
                    cell = self.type_cells[(row, col)]
                    # 保存原始颜色信息
                    if not hasattr(cell, 'original_bg'):
                        cell.original_bg = cell.cget("background")
                    if not hasattr(cell, 'original_fg'):
                        cell.original_fg = cell.cget("foreground")
                    
                    # 更新单元格选中状态
                    cell_key = (row, col)
                    if cell_key not in self.cell_selection_state:
                        self.cell_selection_state[cell_key] = {'row': False, 'col': False}
                    self.cell_selection_state[cell_key]['col'] = True
                    
                    # 设置选中样式
                    cell.config(background="lightblue", relief="raised", borderwidth=2)
                    
                    # 根据数值设置文字颜色
                    if row > 0 and col > 0:  # 只对数值单元格应用颜色
                        try:
                            value = float(cell.cget("text"))
                            if value == 0:
                                cell.config(foreground="black")
                            elif value == 0.5:
                                cell.config(foreground="red")
                            elif value == 1:
                                cell.config(foreground="white")
                            elif value == 2:
                                cell.config(foreground="green")
                        except ValueError:
                            pass  # 如果不是数值，保持原样
            
            # 添加抗性列（如果还没有）
            if self.resistance_column is None:
                self.add_resistance_column()
            
            # 更新抗性列
            self.update_resistance_column()
            
            # 不继续执行下面的代码，避免清除选中的防御属性
            return
        
        # 清除之前的选择
        if self.selected_col is not None:
            self.clear_column_selection(self.selected_col)
        
        # 高亮选中的列 - 使用浅蓝色背景
        for row in range(0, 19):  # 0到18行
            if (row, col) in self.type_cells:
                cell = self.type_cells[(row, col)]
                # 保存原始颜色信息
                if not hasattr(cell, 'original_bg'):
                    cell.original_bg = cell.cget("background")
                if not hasattr(cell, 'original_fg'):
                    cell.original_fg = cell.cget("foreground")
                
                # 更新单元格选中状态
                cell_key = (row, col)
                if cell_key not in self.cell_selection_state:
                    self.cell_selection_state[cell_key] = {'row': False, 'col': False}
                self.cell_selection_state[cell_key]['col'] = True
                
                # 设置选中样式
                cell.config(background="lightblue", relief="raised", borderwidth=2)

                # 根据数值设置文字颜色
                if row > 0 and col > 0:  # 只对数值单元格应用颜色
                    try:
                        value = float(cell.cget("text"))
                        if value == 0:
                            cell.config(foreground="black")
                        elif value == 0.5:
                            cell.config(foreground="red")
                        elif value == 1:
                            cell.config(foreground="white")
                        elif value == 2:
                            cell.config(foreground="green")
                    except ValueError:
                        pass  # 如果不是数值，保持原样
        
        self.selected_col = col
    
    def clear_row_selection(self, row):
        """清除行选择"""
        for col in range(0, 20):  # 0到19列（包括抗性列）
            if (row, col) in self.type_cells:
                cell = self.type_cells[(row, col)]
                
                cell_key = (row, col)
                
                # 更新单元格选中状态
                if cell_key in self.cell_selection_state:
                    self.cell_selection_state[cell_key]['row'] = False
                
                # 检查是否仍有列选中
                has_col_selection = (
                    cell_key in self.cell_selection_state and 
                    self.cell_selection_state[cell_key]['col']
                ) if self.selected_col is not None else False
                
                if has_col_selection:
                    # 保持列选中状态
                    cell.config(background="lightblue", relief="raised", borderwidth=2)
                    # 根据数值设置文字颜色
                    if row > 0 and col > 0:  # 只对数值单元格应用颜色
                        try:
                            value = float(cell.cget("text"))
                            if value == 0:
                                cell.config(foreground="black")
                            elif value == 0.5:
                                cell.config(foreground="red")
                            elif value == 1:
                                cell.config(foreground="white")
                            elif value == 2:
                                cell.config(foreground="green")
                        except ValueError:
                            pass
                else:
                    # 恢复原始样式
                    if hasattr(cell, 'original_bg') and hasattr(cell, 'original_fg'):
                        cell.config(
                            background=cell.original_bg, 
                            foreground=cell.original_fg,
                            relief="solid", 
                            borderwidth=1
                        )
                    # 对于标题行，恢复特殊背景色
                    if row == 0 and col > 0:
                        cell.config(background="lightgray")
                    elif col == 0 and row > 0:
                        cell.config(background="lightgray")
        
        # 如果是抗性列，更新抗性列的显示
        if self.resistance_column is not None and row > 0:
            self.update_resistance_column()
    
    def clear_column_selection(self, col):
        """清除列选择"""
        for row in range(0, 19):
            if (row, col) in self.type_cells:
                cell = self.type_cells[(row, col)]
                cell_key = (row, col)
                
                # 更新单元格选中状态
                if cell_key in self.cell_selection_state:
                    self.cell_selection_state[cell_key]['col'] = False
                
                # 检查是否仍有行选中
                has_row_selection = (
                    cell_key in self.cell_selection_state and 
                    self.cell_selection_state[cell_key]['row']
                ) if self.selected_row is not None else False
                
                if has_row_selection:
                    # 保持行选中状态
                    cell.config(background="lightblue", relief="raised", borderwidth=2)
                    # 根据数值设置文字颜色
                    if row > 0 and col > 0:  # 只对数值单元格应用颜色
                        try:
                            value = float(cell.cget("text"))
                            if value == 0:
                                cell.config(foreground="black")
                            elif value == 0.5:
                                cell.config(foreground="red")
                            elif value == 1:
                                cell.config(foreground="white")
                            elif value == 2:
                                cell.config(foreground="green")
                        except ValueError:
                            pass
                else:
                    # 恢复原始样式
                    if hasattr(cell, 'original_bg') and hasattr(cell, 'original_fg'):
                        cell.config(
                            background=cell.original_bg, 
                            foreground=cell.original_fg,
                            relief="solid", 
                            borderwidth=1
                        )
                    # 对于标题列，恢复特殊背景色
                    if row == 0 and col > 0:
                        cell.config(background="lightgray")
                    elif col == 0 and row > 0:
                        cell.config(background="lightgray")
        
        # 在双属性模式下，从选中的防御属性列表中移除
        if self.dual_type_mode and col in self.selected_defense_types:
            self.selected_defense_types.remove(col)
            # 更新抗性列
            self.update_resistance_column()
        
        self.selected_col = None
    
    def clear_selection(self):
        """清除所有选择"""
        if self.selected_row is not None:
            self.clear_row_selection(self.selected_row)
            self.selected_row = None
        
        if self.selected_col is not None:
            self.clear_column_selection(self.selected_col)
            self.selected_col = None
        
        # 在双属性模式下，清除所有选中的防御属性
        if self.dual_type_mode:
            # 复制选中的防御属性列表，避免在迭代过程中修改列表
            defense_types_copy = self.selected_defense_types.copy()
            for col in defense_types_copy:
                self.clear_column_selection(col)
            self.selected_defense_types.clear()
            
            # 重置抗性列
            if self.resistance_column is not None:
                for row in range(1, 19):
                    if (row, self.resistance_column) in self.type_cells:
                        cell = self.type_cells[(row, self.resistance_column)]
                        cell.config(text="1.0", background="white", foreground="black")
        
        # 清空选中状态跟踪
        self.cell_selection_state.clear()
    
    def on_strategy_change(self):
        """处理策略变更"""
        strategy = self.strategy_var.get()
        
        # 启用/禁用单一道具输入框
        if strategy == "single":
            self.single_item_entry.config(state="normal")
            # 显示提示
            messagebox.showinfo("提示", "请确保您输入的道具编号在ItemData.txt中的Pouch列下的数值不为-1")
        else:
            self.single_item_entry.config(state="disabled")
    
    def browse_trainer_dir(self):
        """浏览训练家文件目录"""
        old_value = self.trainer_dir_var.get()
        directory = filedialog.askdirectory(title="选择训练家文件目录(trainer_poke)")
        if directory:
            self.trainer_dir_var.set(directory)
            # 如果路径发生变化，显示提示
            if old_value != directory:
                self.set_status(self.path_status_var, "训练家文件目录已更改，请记得保存路径设置！")
    
    def browse_personal_file(self):
        """浏览personal_total.bin文件"""
        old_value = self.personal_file_var.get()
        filepath = filedialog.askopenfilename(title="选择personal_total.bin文件", filetypes=[("BIN files", "*.bin"), ("All files", "*.*")])
        if filepath:
            self.personal_file_var.set(filepath)
            # 如果路径发生变化，显示提示
            if old_value != filepath:
                self.set_status(self.path_status_var, "personal_total.bin文件路径已更改，请记得保存路径设置！")
    
    def browse_main_file(self):
        """浏览main文件"""
        old_value = self.main_file_var.get()
        filepath = filedialog.askopenfilename(title="选择main文件", filetypes=[("All files", "*.*")])
        if filepath:
            self.main_file_var.set(filepath)
            # 如果路径发生变化，显示提示
            if old_value != filepath:
                self.set_status(self.path_status_var, "main文件路径已更改，请记得保存路径设置！")
    
    def save_paths(self):
        """保存路径设置"""
        global trainer_poke_dir, personal_total_bin_path, main_file_path
        
        trainer_dir = self.trainer_dir_var.get()
        personal_file = self.personal_file_var.get()
        main_file = self.main_file_var.get()
        
        if not trainer_dir or not personal_file or not main_file:
            messagebox.showerror("错误", "请先选择并保存全部路径")
            return
        
        # 验证路径是否存在
        if not os.path.isdir(trainer_dir):
            messagebox.showerror("错误", "训练家文件目录不存在")
            return
        
        if not os.path.isfile(personal_file):
            messagebox.showerror("错误", "personal_total.bin文件不存在")
            return
        
        if not os.path.isfile(main_file):
            messagebox.showerror("错误", "main文件不存在")
            return
        
        # 保存路径（写入本地用户配置，而不是规则配置）
        trainer_poke_dir = trainer_dir
        personal_total_bin_path = personal_file
        main_file_path = main_file
        try:
            set_trainer_poke_dir(trainer_poke_dir)
            set_personal_total_path(personal_total_bin_path)
            set_main_file_path(main_file_path)
        except Exception as e:
            messagebox.showerror("错误", f"保存路径时出错: {str(e)}")
            return
        
        self.set_status(self.path_status_var, "全部路径保存成功!")
        
        # 如果main文件路径存在，尝试生成JSON文件
        if main_file and os.path.isfile(main_file):
            self.generate_json_from_main(main_file)
        else:
            # 只在保存后提示路径问题，启动时不提示
            if main_file and not os.path.isfile(main_file):
                messagebox.showwarning("警告", "main文件路径可能不正确，请检查路径设置")
        
        self.refresh_file_list()
        self.reload_item_replacement_rules()
        self.update_feature_availability()

    def _save_single_path(self, key, value):
        global config
        try:
            if key == "trainer_poke_dir":
                set_trainer_poke_dir(value or "")
            elif key == "personal_total_bin_path":
                set_personal_total_path(value or "")
            elif key == "main_file_path":
                set_main_file_path(value or "")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存路径时出错: {str(e)}")
            return False

    def save_trainer_dir(self):
        global trainer_poke_dir
        path = self.trainer_dir_var.get()
        if not path or self._is_demo_path("trainer_poke_dir", path) or not os.path.isdir(path):
            messagebox.showerror("错误", "训练家文件目录不存在")
            return
        trainer_poke_dir = path
        if self._save_single_path("trainer_poke_dir", trainer_poke_dir):
            self.set_status(self.path_status_var, "训练家目录已保存")
            self.refresh_file_list()
            self.reload_item_replacement_rules()
            self.update_feature_availability()

    def save_personal_file(self):
        global personal_total_bin_path
        path = self.personal_file_var.get()
        if not path or self._is_demo_path("personal_total_bin_path", path) or not os.path.isfile(path):
            messagebox.showerror("错误", "personal_total.bin文件不存在")
            return
        personal_total_bin_path = path
        if self._save_single_path("personal_total_bin_path", personal_total_bin_path):
            self.set_status(self.path_status_var, "personal路径已保存")
            self.reload_item_replacement_rules()
            self.update_feature_availability()

    def save_main_file(self):
        global main_file_path
        path = self.main_file_var.get()
        if not path or self._is_demo_path("main_file_path", path) or not os.path.isfile(path):
            messagebox.showerror("错误", "main文件不存在")
            return
        main_file_path = path
        if self._save_single_path("main_file_path", main_file_path):
            self.set_status(self.path_status_var, "main路径已保存")
            self.generate_json_from_main(main_file_path)
            self.reload_item_replacement_rules()
            self.update_feature_availability()

    def update_feature_availability(self):
        trainer_ok = self._is_valid_trainer_dir()
        personal_ok = self._is_valid_personal_file()
        main_ok = self._is_valid_main_file()
        try:
            if hasattr(self, "view_trainer_btn"):
                self.view_trainer_btn.config(state=("normal" if trainer_ok else "disabled"))
            if hasattr(self, "refresh_file_list_btn"):
                self.refresh_file_list_btn.config(state=("normal" if trainer_ok else "disabled"))
            if hasattr(self, "file_num_combo"):
                self.file_num_combo.config(state=("readonly" if trainer_ok else "disabled"))
        except Exception:
            pass
        try:
            if hasattr(self, "verify_button"):
                self.verify_button.config(state=("normal" if trainer_ok else "disabled"))
        except Exception:
            pass
        try:
            if hasattr(self, "generate_types_btn"):
                self.generate_types_btn.config(state=("normal" if personal_ok else "disabled"))
            if hasattr(self, "generate_abilities_btn"):
                self.generate_abilities_btn.config(state=("normal" if personal_ok else "disabled"))
        except Exception:
            pass

    def _load_demo_paths(self):
        demo = {}
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            p = os.path.join(base, "path.md")
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        m = re.search(r'"([^"]+)"\s*:\s*"([^"]+)"', line)
                        if m:
                            demo[m.group(1)] = m.group(2)
        except Exception:
            pass
        return demo

    def _is_demo_path(self, key, value):
        if not value:
            return False
        if "右键->" in value:
            return True
        if not hasattr(self, "_demo_paths"):
            self._demo_paths = self._load_demo_paths()
        return value.strip() == self._demo_paths.get(key, "").strip()

    def _is_valid_trainer_dir(self):
        if not trainer_poke_dir:
            return False
        if self._is_demo_path("trainer_poke_dir", trainer_poke_dir):
            return False
        return os.path.isdir(trainer_poke_dir)

    def _is_valid_personal_file(self):
        if not personal_total_bin_path:
            return False
        if self._is_demo_path("personal_total_bin_path", personal_total_bin_path):
            return False
        return os.path.isfile(personal_total_bin_path)

    def _is_valid_main_file(self):
        if not main_file_path:
            return False
        if self._is_demo_path("main_file_path", main_file_path):
            return False
        return os.path.isfile(main_file_path)
    
    def generate_config(self):
        """生成配置文件"""
        # 安全加载文本文件的辅助函数
        def safe_load_txt(filename):
            return safe_load_file(filename, "txt")
        
        try:
            lines = safe_load_txt("ItemData.txt")
            if not lines:
                messagebox.showerror("错误", "找不到ItemData.txt文件")
                return
            
            valid_items = []
            for line in lines:
                if line.startswith("Index\tItems"):
                    continue
                match = re.match(r"^(\d+)\t", line)
                if match:
                    item_id = int(match.group(1))
                    valid_items.append(item_id)
            
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
            
            
            global config
            config = {
                # "use_random": True,
                # "replace_all": True,
                "trainer_poke_dir": trainer_poke_dir if trainer_poke_dir else "",
                "personal_total_bin_path": personal_total_bin_path if personal_total_bin_path else "",
                "main_file_path": main_file_path if main_file_path else "",
                "valid_items": valid_items,
                "skip_items": [0],
                "item_categories": item_categories
            }
            
            try:
                os.makedirs("config", exist_ok=True)
                if safe_save_file is not None:
                    safe_save_file(config, "item_category_rules.json")
                else:
                    with open(os.path.join("config", "item_category_rules.json"), "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
            except IOError as e:
                messagebox.showerror("错误", f"保存配置文件时出错: {str(e)}")
                return
            
            self.set_status(self.config_status_var, "配置文件生成成功!")

            self.reload_item_replacement_rules()
            reload_config()
            
        except Exception as e:
            messagebox.showerror("错误", f"生成配置文件时出错: {str(e)}")
    
    def generate_personal_data(self, gen_types=True, gen_abilities=True):
        """生成属性/特性数据"""
        if not self._is_valid_personal_file():
            messagebox.showerror("错误", "请先设置personal_total.bin文件路径")
            return
        
        # 在后台线程中执行生成操作
        def generate_thread():
            try:
                if gen_types:
                    self.set_status(self.config_status_var, "正在生成属性数据...")
                    self.extract_all_pokemon_types()
                    self.set_status(self.config_status_var, "属性数据生成完成!")
                    self.reload_pokemon_types_final()
                    reload_pokemon_types_data()
                
                if gen_abilities:
                    self.set_status(self.config_status_var, "正在生成特性数据...")
                    self.extract_all_pokemon_abilities()
                    self.set_status(self.config_status_var, "特性数据生成完成!")
                    self.reload_pokemon_abilities_final()
                
            except Exception as e:
                self.set_status(self.config_status_var, f"生成数据时出错: {str(e)}")
        
        threading.Thread(target=generate_thread).start()
    
    def extract_all_pokemon_types(self):
        """提取所有宝可梦的属性信息"""
        pokemon_types = {}
        
        with open(personal_total_bin_path, "rb") as f:
            data = f.read()
            num_records = len(data) // PERSONAL_RECORD_SIZE
            
            for record_id in range(0, num_records):
                record_start = record_id * PERSONAL_RECORD_SIZE
                
                if record_start + TYPE_OFFSET_2 >= len(data):
                    continue
                
                type1 = data[record_start + TYPE_OFFSET_1]
                type2 = data[record_start + TYPE_OFFSET_2]
                
                type1_name = type_code_map.get(type1, f"unknown({type1})")
                type2_name = type_code_map.get(type2, f"unknown({type2})")
                
                if type2 == type1 or type2 == 0:
                    pokemon_types[record_id] = [type1_name]
                else:
                    pokemon_types[record_id] = [type1_name, type2_name]
        
        # 保存到JSON文件
        try:
            # 确保config目录存在
            os.makedirs("config", exist_ok=True)
            # 保存到config目录
            if safe_save_file is not None:
                safe_save_file(pokemon_types, "pokemon_types_final.json")
            else:
                with open(os.path.join("config", "pokemon_types_final.json"), "w", encoding="utf-8") as f:
                    json.dump(pokemon_types, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.set_status(self.config_status_var, f"保存属性数据时出错: {str(e)}")
            return
        
        global pokemon_types_data
        pokemon_types_data = pokemon_types
    
    def extract_all_pokemon_abilities(self):
        """提取所有宝可梦的特性信息"""
        abilities = {}
        
        with open(personal_total_bin_path, "rb") as f:
            data = f.read()
            num_records = len(data) // PERSONAL_RECORD_SIZE
            
            for record_id in range(0, num_records):
                record_start = record_id * PERSONAL_RECORD_SIZE
                
                if record_start + ABILITY_OFFSET_H + 2 >= len(data):
                    continue
                
                # 读取三个特性
                ability1 = struct.unpack("<H", data[record_start + ABILITY_OFFSET_1:record_start + ABILITY_OFFSET_1 + 2])[0]
                ability2 = struct.unpack("<H", data[record_start + ABILITY_OFFSET_2:record_start + ABILITY_OFFSET_2 + 2])[0]
                ability_h = struct.unpack("<H", data[record_start + ABILITY_OFFSET_H:record_start + ABILITY_OFFSET_H + 2])[0]
                
                abilities[record_id] = {
                    "ability1": ability1,
                    "ability2": ability2,
                    "ability_h": ability_h
                }
        
        # 保存宝可梦特性信息
        try:
            # 确保config目录存在
            os.makedirs("config", exist_ok=True)
            # 保存到config目录
            if safe_save_file is not None:
                safe_save_file(abilities, "pokemon_abilities_final.json")
            else:
                with open(os.path.join("config", "pokemon_abilities_final.json"), "w", encoding="utf-8") as f:
                    json.dump(abilities, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.set_status(self.config_status_var, f"保存特性数据时出错: {str(e)}")
            return
        
        global pokemon_abilities_data
        pokemon_abilities_data = abilities
    
    def refresh_file_list(self):
        """刷新训练家文件列表"""
        global file_numbers
        
        if not self._is_valid_trainer_dir():
            messagebox.showerror("错误", "请先设置训练家文件目录")
            return
        
        if not os.path.exists(trainer_poke_dir):
            messagebox.showerror("错误", "训练家文件目录不存在")
            return
        
        files = [f for f in os.listdir(trainer_poke_dir) if f.startswith("trainer_poke_") and f.endswith(".bin")]
        files.sort()
        
        file_numbers = []
        pattern = re.compile(r"trainer_poke_(\d+)\.bin")
        for f in files:
            match = pattern.match(f)
            if match:
                file_numbers.append(int(match.group(1)))
        
        # 更新下拉框
        self.file_num_combo['values'] = [str(num).zfill(3) for num in file_numbers]
        
        if file_numbers:
            self.file_num_combo.current(0)
    
    def view_trainer_file(self):
        """查看训练家宝可梦文件"""
        if not self._is_valid_trainer_dir():
            messagebox.showerror("错误", "请先设置训练家文件目录")
            return
        if not file_numbers:
            messagebox.showerror("错误", "没有可用的训练家文件，请先刷新文件列表")
            return
        
        file_number = self.file_num_var.get()
        if not file_number:
            messagebox.showerror("错误", "请选择文件编号")
            return
        
        # 在后台线程中执行查看操作
        def view_thread():
            try:
                # 清除现有宝可梦框架内容
                for widget in self.pokemon_frame.winfo_children():
                    widget.destroy()
                
                # 获取宝可梦数据
                pokemon_data_list = self.get_trainer_file_content(file_number)
                
                # 显示宝可梦信息
                for i, pokemon_data in enumerate(pokemon_data_list):
                    row = i // 3
                    col = i % 3
                    self.create_pokemon_display(self.pokemon_frame, pokemon_data, row, col)
                
                # 更新画布滚动区域
                self.pokemon_frame.update_idletasks()
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                
            except Exception as e:
                messagebox.showerror("错误", f"查看文件时出错: {str(e)}")
        
        threading.Thread(target=view_thread).start()
    
    def create_pokemon_display(self, parent, pokemon_data, row, col):
        """创建单个宝可梦信息显示框架"""
        show_ids = self.show_ids_var.get()
        
        # 创建宝可梦框架
        frame = ttk.LabelFrame(parent, text=f"宝可梦 {pokemon_data['index'] + 1}")
        frame.grid(row=row, column=col, sticky=tk.N+tk.S+tk.E+tk.W, padx=5, pady=5)
        
        # 创建左右两个子框架
        left_frame = ttk.Frame(frame)  # 左侧：基本信息
        left_frame.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W, padx=5, pady=5)
        
        right_frame = ttk.Frame(frame)  # 右侧：IVs和EVs
        right_frame.grid(row=0, column=1, sticky=tk.N+tk.S+tk.E+tk.W, padx=5, pady=5)
        
        # 配置框架网格权重
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        
        # 左侧：基本信息
        # 宝可梦名称
        ttk.Label(left_frame, text="宝可梦:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        pokemon_text = f"{pokemon_data['pokemon_name']}" if not show_ids else f"{pokemon_data['pokemon_id']}"
        ttk.Label(left_frame, text=pokemon_text).grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)
        
        # 道具
        ttk.Label(left_frame, text="道具:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        item_text = f"{pokemon_data['item_name']}" if not show_ids else f"{pokemon_data['item_id']}"
        ttk.Label(left_frame, text=item_text).grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)
        
        # 等级
        ttk.Label(left_frame, text="等级:").grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(left_frame, text=str(pokemon_data['level'])).grid(row=2, column=1, sticky=tk.W, padx=2, pady=2)
        
        # 性格
        ttk.Label(left_frame, text="性格:").grid(row=3, column=0, sticky=tk.W, padx=2, pady=2)
        nature_text = f"{pokemon_data['nature_display']}" if not show_ids else f"{pokemon_data['nature_value']}"
        ttk.Label(left_frame, text=nature_text).grid(row=3, column=1, sticky=tk.W, padx=2, pady=2)
        
        # 属性
        ttk.Label(left_frame, text="属性:").grid(row=4, column=0, sticky=tk.W, padx=2, pady=2)
        types_text = "/".join(pokemon_data['pokemon_types_chinese']) if not show_ids else "/".join(pokemon_data['pokemon_types'])
        ttk.Label(left_frame, text=types_text).grid(row=4, column=1, sticky=tk.W, padx=2, pady=2)
        
        # 特性
        ttk.Label(left_frame, text="特性:").grid(row=5, column=0, sticky=tk.W, padx=2, pady=2)
        ability_frame = ttk.Frame(left_frame)
        ability_frame.grid(row=5, column=1, sticky=tk.W, padx=2, pady=2)
        
        ability_text = pokemon_data['ability_display']
        if show_ids:
            # 提取ID部分
            match = re.search(r'\((\d+)\)', ability_text)
            if match:
                ability_text = match.group(1)
            else:
                ability_text = ability_text.split('(')[-1].split(')')[0] if '(' in ability_text else ability_text
        
        ability_label = ttk.Label(ability_frame, text=ability_text, foreground="blue", cursor="hand2")
        ability_label.grid(row=0, column=0, sticky=tk.W)
        ability_label.bind("<Button-1>", lambda e, a=pokemon_data['ability_value']: self.show_ability_explanation(a))
        
        # 技能
        ttk.Label(left_frame, text="技能:").grid(row=6, column=0, sticky=tk.NW, padx=2, pady=2)
        moves_frame = ttk.Frame(left_frame)
        moves_frame.grid(row=6, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=2, pady=2)
        
        for i, move_id in enumerate(pokemon_data['move_ids']):
            if move_id == 0:
                move_text = "无"
            else:
                if show_ids:
                    move_text = str(move_id)
                else:
                    move_name = move_map.get(str(move_id), f"未知({move_id})")
                    move_text = move_name
            
            move_label = ttk.Label(moves_frame, text=f"{i+1}. {move_text}", 
                                  foreground="blue" if move_id != 0 else "black",
                                  cursor="hand2" if move_id != 0 else "")
            move_label.grid(row=i, column=0, sticky=tk.W)
            
            if move_id != 0:
                move_label.bind("<Button-1>", lambda e, m=move_id: self.show_move_explanation(m))
        
        # 右侧：IVs和EVs
        # 获取性格效果
        nature = pokemon_data['nature_name']
        increased_stat, decreased_stat = nature_effect_map.get(nature, ("", ""))
        
        # 创建表头
        ttk.Label(right_frame, text="", width=5).grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)  # 空白占位
        ttk.Label(right_frame, text="个体", width=5).grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)
        ttk.Label(right_frame, text="努力", width=5).grid(row=0, column=2, sticky=tk.W, padx=2, pady=2)
        
        # 显示IVs和EVs，根据性格效果着色
        for i, (name, iv_value, ev_value) in enumerate(zip(v_names, pokemon_data['ivs'], pokemon_data['evs'])):
            # 属性名称
            color = "black"
            if name == increased_stat:
                color = "green"
            elif name == decreased_stat:
                color = "red"
            
            ttk.Label(right_frame, text=f"{name}:", foreground=color).grid(row=i+1, column=0, sticky=tk.W, padx=2, pady=2)
            
            # IV值
            ttk.Label(right_frame, text=str(iv_value)).grid(row=i+1, column=1, sticky=tk.W, padx=2, pady=2)
            
            # EV值
            ttk.Label(right_frame, text=str(ev_value)).grid(row=i+1, column=2, sticky=tk.W, padx=2, pady=2)
        
        # 计算并显示总和和百分比
        ivs_sum = sum(pokemon_data['ivs'])
        ivs_percentage = round(ivs_sum / 186 * 100, 1)
        evs_sum = sum(pokemon_data['evs'])
        evs_percentage = round(evs_sum / 510 * 100, 1)
        
        # 总和行
        ttk.Label(right_frame, text="总和:").grid(row=7, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(right_frame, text=f"{ivs_sum}({ivs_percentage}%)").grid(row=7, column=1, sticky=tk.W, padx=2, pady=2)
        ttk.Label(right_frame, text=f"{evs_sum}({evs_percentage}%)").grid(row=7, column=2, sticky=tk.W, padx=2, pady=2)
    
    def show_ability_explanation(self, ability_value):
        """显示特性说明"""
        # 获取特性ID
        ability_id = str(ability_value)
        explanation = ability_explanation_map.get(ability_id, "无说明")
        
        # 创建弹出窗口
        popup = tk.Toplevel(self.root)
        popup.title("特性说明")
        popup.geometry("400x300")
        popup.transient(self.root)
        popup.grab_set()
        
        # 使窗口居中显示
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建说明框架
        explanation_frame = ttk.Frame(popup, padding="10")
        explanation_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加说明文本
        explanation_text = tk.Text(explanation_frame, wrap=tk.WORD, height=15, width=40, font=("宋体", 12))
        explanation_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置文本居中显示
        explanation_text.tag_configure("center", justify="center")
        
        # 将逗号和句号替换为换行符
        formatted_explanation = explanation.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
        explanation_text.insert(tk.END, formatted_explanation, "center")
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
        
        # 添加关闭按钮
        close_button = ttk.Button(explanation_frame, text="关闭", command=popup.destroy)
        close_button.pack(pady=10)
    
    def show_move_explanation(self, move_id):
        """显示技能说明"""
        explanation = move_explanation_map.get(str(move_id), "无说明")
        
        # 创建弹出窗口
        popup = tk.Toplevel(self.root)
        popup.title("技能说明")
        popup.geometry("500x400")
        popup.transient(self.root)
        popup.grab_set()
        
        # 使窗口居中显示
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建说明框架
        explanation_frame = ttk.Frame(popup, padding="10")
        explanation_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取技能名称
        move_name = move_map.get(str(move_id), f"未知技能({move_id})")
        
        # 显示技能名称
        name_label = ttk.Label(explanation_frame, text=f"技能: {move_name}", font=("宋体", 12, "bold"))
        name_label.pack(pady=10)
        
        # 显示技能说明
        explanation_text = tk.Text(explanation_frame, wrap=tk.WORD, height=15, width=50, font=("宋体", 12))
        explanation_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置文本居中显示
        explanation_text.tag_configure("center", justify="center")
        
        # 解析技能信息
        if "\n" in explanation:
            # 分离技能属性和描述
            parts = explanation.split("\n", 1)
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
                    if "，" in explanation or "," in explanation or "。" in explanation or "." in explanation:
                        formatted_info = explanation.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                        explanation_text.insert(tk.END, formatted_info, "center")
                    else:
                        explanation_text.insert(tk.END, explanation, "center")
            else:
                # 如果没有属性分隔符，直接显示原始信息
                if "，" in explanation or "," in explanation or "。" in explanation or "." in explanation:
                    formatted_info = explanation.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                    explanation_text.insert(tk.END, formatted_info, "center")
                else:
                    explanation_text.insert(tk.END, explanation, "center")
        else:
            # 如果没有换行符，直接显示原始信息
            if "，" in explanation or "," in explanation or "。" in explanation or "." in explanation:
                formatted_info = explanation.replace("，", "\n").replace(",", "\n").replace("。", "\n").replace(".", "\n")
                explanation_text.insert(tk.END, formatted_info, "center")
            else:
                explanation_text.insert(tk.END, explanation, "center")
                
        explanation_text.config(state=tk.DISABLED)
        
        # 关闭按钮
        close_button = ttk.Button(explanation_frame, text="关闭", command=popup.destroy)
        close_button.pack(pady=10)
    
    def get_trainer_file_content(self, file_number):
        """获取训练家文件内容"""
                
        def get_ability_display(pokemon_id, ability_value):
            """根据宝可梦ID和特性值获取特性显示名称"""
            abilities = pokemon_abilities_data.get(str(pokemon_id), {})
            
            # 获取特性ID
            ability_id = 0
            ability_type = ""
            
            if ability_value == 1:
                ability_id = abilities.get("ability1", 0)
                ability_type = "1"
            elif ability_value == 2:
                ability_id = abilities.get("ability2", 0)
                ability_type = "2"
            elif ability_value == 3:
                ability_id = abilities.get("ability_h", 0)
                ability_type = "H"
            else:
                return f"未知特性({ability_value})"
            
            # 获取特性名称
            ability_name = ability_map.get(str(ability_id), f"未知特性({ability_id})")
            
            # 格式化显示
            return f"{ability_name} ({ability_type})", ability_id
        

        file_number = file_number.zfill(3)
        filepath = os.path.join(trainer_poke_dir, f"trainer_poke_{file_number}.bin")
        
        if not os.path.exists(filepath):
            return f"文件不存在: {filepath}"
        
        with open(filepath, "rb") as f:
            data = f.read()
        
        file_size = len(data)
        num_pokemon = file_size // POKEMON_SIZE
        
        # result = f"文件: trainer_poke_{file_number}.bin\n"
        # result += f"宝可梦数量: {num_pokemon}\n"
        # result += "-" * 80 + "\n"

        pokemon_data_list = []
        
        for i in range(num_pokemon):
            offset = i * POKEMON_SIZE
            if offset + POKEMON_SIZE > file_size:
                result += f"警告: 宝可梦{i}的数据不完整!\n"
                break
            
            # 偏移量
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
            
            try:
                # 读取数据
                pokemon_id = struct.unpack("<H", data[pokemon_id_offset:pokemon_id_offset+2])[0]
                item_id = struct.unpack("<H", data[item_offset:item_offset+2])[0]
                level = data[level_offset]
                nature_value = data[nature_offset]
                
                # 读取技能
                move1 = struct.unpack("<H", data[move1_offset:move1_offset+2])[0]
                move2 = struct.unpack("<H", data[move2_offset:move2_offset+2])[0]
                move3 = struct.unpack("<H", data[move3_offset:move3_offset+2])[0]
                move4 = struct.unpack("<H", data[move4_offset:move4_offset+2])[0]
                move_ids = [move1, move2, move3, move4]
                
                # 获取宝可梦信息
                pokemon_name = pokemon_name_map.get(str(pokemon_id), f"未知({pokemon_id})")
                pokemon_types = pokemon_types_data.get(str(pokemon_id), [])
                pokemon_types_chinese = [type_map.get(t, f"未知{t}") for t in pokemon_types]
                item_name = item_id_to_name.get(item_id, f"未知道具({item_id})")
                nature_name = nature_map.get(nature_value, f"未知({nature_value})")
                nature_effect = nature_effect_map.get(nature_name, ("", ""))
                if nature_effect[0] and nature_effect[1]:
                    nature_display = f"{nature_name}( +{nature_effect[0]}, -{nature_effect[1]} )"
                else:
                    nature_display = nature_name
                
                # 解析努力值和个体值
                evs = []
                if ev_offset + 6 <= len(data):
                    ev_data = data[ev_offset:ev_offset+6]
                    evs = list(ev_data)
                
                ivs = []
                if iv_offset + 4 <= len(data):
                    iv_data = data[iv_offset:iv_offset+4]
                    iv_value = struct.unpack("<I", iv_data)[0]
                    for j in range(6):
                        iv = (iv_value >> (5 * j)) & 0x1F
                        ivs.append(iv)
                
                # 解析特性
                ability_value = (data[offset + ABILITY_OFFSET] >> 4) & 0x0F
                ability_display, ability_id = get_ability_display(pokemon_id, ability_value)
                
                # # 格式化输出
                # result += f"宝可梦 {i+1}:\n"
                # result += f"  宝可梦ID: {pokemon_id} ( {pokemon_name} )\n"
                # result += f"  道具ID: {item_id} ( {item_name} )\n"
                # result += f"  等级: {level}\n"
                # result += f"  性格: {nature_display}\n"
                # result += f"  属性: {', '.join(pokemon_types)}( {', '.join(pokemon_types_chinese)} )\n"
                # result += f"  特性: {ability_display}\n"
                
                # result += f"  个体值: {', '.join([f'{name}:{value}' for name, value in zip(v_names, ivs)])}\n"
                # result += f"  努力值: {', '.join([f'{name}:{value}' for name, value in zip(v_names, evs)])}\n"
                # result += "-" * 80 + "\n"

                # 收集宝可梦数据
                pokemon_data = {
                    "index": i,
                    "pokemon_id": pokemon_id,
                    "pokemon_name": pokemon_name,
                    "item_id": item_id,
                    "item_name": item_name,
                    "level": level,
                    "nature_value": nature_value,
                    "nature_name": nature_name,
                    "nature_display": nature_display,
                    "pokemon_types": pokemon_types,
                    "pokemon_types_chinese": pokemon_types_chinese,
                    "ability_value": ability_id,
                    "ability_display": ability_display,
                    "ivs": ivs,
                    "evs": evs,
                    "move_ids": move_ids
                }
                
                pokemon_data_list.append(pokemon_data)
            except Exception as e:
                continue


        return pokemon_data_list
    
    def randomize_items(self):
        """随机化道具"""
        if not self._is_valid_trainer_dir():
            messagebox.showerror("错误", "请先设置正确的训练家目录路径")
            return
        
        if not config:
            messagebox.showerror("错误", "请先生成配置文件")
            return
        
        strategy = self.strategy_var.get()
        single_item_id = self.single_item_id_var.get() if strategy == "single" else None
        
        # 验证单一道具ID
        if strategy == "single":
            try:
                single_item_id = int(single_item_id)
                if single_item_id not in config["valid_items"]:
                    response = messagebox.askokcancel("警告", 
                        f"道具ID {single_item_id} 不在有效道具列表中，这可能导致游戏崩溃\n点击确定继续，取消停止操作")
                    if not response:
                        return
            except ValueError:
                messagebox.showerror("错误", "道具ID必须是数字")
                return
        
        # 在后台线程中执行随机化操作
        def randomize_thread():
            self.set_status(self.random_status_var, "正在随机化道具...")
            try:
                result = self.randomize_items_process(strategy, single_item_id)
                self.random_text.delete(1.0, tk.END)
                self.random_text.insert(tk.END, result)
                self.set_status(self.random_status_var, "道具随机化完成!")
            except Exception as e:
                self.random_text.delete(1.0, tk.END)
                self.random_text.insert(tk.END, f"随机化道具时出错: {str(e)}")
                self.set_status(self.random_status_var, f"随机化道具时出错: {str(e)}")
        
        threading.Thread(target=randomize_thread).start()
    
    def randomize_items_process(self, strategy, single_item_id=None):
        """随机化道具处理过程"""
        if not self._is_valid_trainer_dir():
            raise FileNotFoundError("训练家文件目录无效")
        total_pokemon = 0
        replaced_count = 0
        
        files = [f for f in os.listdir(trainer_poke_dir) if f.startswith("trainer_poke_") and f.endswith(".bin")]
        
        for file in files:
            filepath = os.path.join(trainer_poke_dir, file)
            
            with open(filepath, "rb") as f:
                data = bytearray(f.read())
            
            num_pokemon = len(data) // POKEMON_SIZE
            
            for i in range(num_pokemon):
                total_pokemon += 1
                offset = i * POKEMON_SIZE
                item_offset = offset + ITEM_OFFSET
                pokemon_id_offset = offset + POKEMON_ID_OFFSET
                
                if strategy == "single" and single_item_id is not None:
                    # 单一替换
                    new_item = single_item_id
                elif strategy == "random":
                    # 随机替换
                    new_item = random.choice(config["valid_items"])
                else:
                    pokemon_id = struct.unpack("<H", data[pokemon_id_offset:pokemon_id_offset+2])[0]
                    new_item = select_item(pokemon_id)
                
                # 确保new_item是整数
                if isinstance(new_item, str):
                    try:
                        new_item = int(new_item)
                    except ValueError:
                        self.set_status(self.random_status_var, f"错误: 道具ID '{new_item}' 不是有效的数字")
                        return f"错误: 道具ID '{new_item}' 不是有效的数字"
                
                data[item_offset:item_offset+2] = struct.pack("<H", new_item)
                replaced_count += 1
            
            with open(filepath, "wb") as f:
                f.write(data)
        
        result = f"处理完成!\n"
        result += f"检查宝可梦: {total_pokemon} 只\n"
        result += f"替换道具: {replaced_count} 个\n"
        
        if strategy == "single" and single_item_id is not None:
            result += f"所有道具已替换为: {single_item_id} ({item_id_to_name.get(single_item_id, '未知')})\n"
        
        return result
    
    def verify_distribution(self):
        """验证道具分布"""
        if not self._is_valid_trainer_dir():
            messagebox.showerror("错误", "请先设置训练家文件目录")
            return
        
        try:
            sample_count = int(self.sample_count_var.get())
        except ValueError:
            messagebox.showerror("错误", "样本数量必须是整数")
            return
        
        # 在后台线程中执行验证操作
        def verify_thread():
            self.set_status(self.verify_status_var, "正在验证道具分布...")
            try:
                result = self.analyze_trainer_files(sample_count)
                self.verify_text.delete(1.0, tk.END)
                self.verify_text.insert(tk.END, result)
                self.set_status(self.verify_status_var, "道具分布验证完成!")
            except Exception as e:
                self.verify_text.delete(1.0, tk.END)
                self.verify_text.insert(tk.END, f"验证道具分布时出错: {str(e)}")
                self.set_status(self.verify_status_var, f"验证道具分布时出错: {str(e)}")
        
        threading.Thread(target=verify_thread).start()
    
    def analyze_trainer_files(self, sample_count=5):
        """分析训练家文件中的道具分布"""
        if not self._is_valid_trainer_dir():
            raise ValueError("训练家文件目录无效")
        POKEMON_SIZE = 0x20
        ITEM_OFFSET = 0x10
        POKEMON_ID_OFFSET = 0x0C
        
        all_files = [f for f in os.listdir(trainer_poke_dir) if f.startswith("trainer_poke_") and f.endswith(".bin")]
        
        # 随机选择一些文件进行分析
        sample_files = random.sample(all_files, min(sample_count, len(all_files)))
        
        results = {
            "total_pokemon": 0,
            "item_distribution": Counter(),
            "category_distribution": Counter(),
            "type_match_analysis": defaultdict(list),
            "pokemon_with_items": []
        }
        
        # 用于属性匹配度分析的新变量
        type_item_matches = 0
        total_type_items = 0
        mismatched_cases = []  # 存储不匹配的情况
        
        for file_name in sample_files:
            filepath = os.path.join(trainer_poke_dir, file_name)
            
            with open(filepath, "rb") as f:
                data = f.read()
            
            num_pokemon = len(data) // POKEMON_SIZE
            
            for i in range(num_pokemon):
                offset = i * POKEMON_SIZE
                item_offset = offset + ITEM_OFFSET
                pokemon_id_offset = offset + POKEMON_ID_OFFSET
                
                if item_offset + 2 > len(data) or pokemon_id_offset + 2 > len(data):
                    continue
                
                # 读取宝可梦ID和道具ID
                pokemon_id = struct.unpack("<H", data[pokemon_id_offset:pokemon_id_offset+2])[0]
                item_id = struct.unpack("<H", data[item_offset:item_offset+2])[0]
                
                pokemon_types = pokemon_types_data.get(str(pokemon_id), [])
                item_name = item_id_to_name.get(item_id, f"未知道具({item_id})")
                item_category = get_item_category(item_id)
                
                # 记录结果
                results["total_pokemon"] += 1
                results["item_distribution"][item_id] += 1
                results["category_distribution"][item_category] += 1
                
                # 记录宝可梦和道具的详细信息
                pokemon_info = {
                    "file": file_name,
                    "pokemon_id": pokemon_id,
                    "pokemon_types": pokemon_types,
                    "item_id": item_id,
                    "item_name": item_name,
                    "item_category": item_category
                }
                results["pokemon_with_items"].append(pokemon_info)
                
                # 分析属性道具匹配度
                if item_category in ["属性道具-攻击", "属性道具-防御", "属性道具-特殊", "属性道具"]:
                    total_type_items += 1
                    # 检查是否匹配
                    is_match = self.check_type_item_match(pokemon_types, item_id, item_category)
                    if is_match:
                        type_item_matches += 1
                    else:
                        # 记录不匹配的情况，最多记录5个
                        if len(mismatched_cases) < 5:
                            pokemon_name = pokemon_name_map.get(str(pokemon_id), f"未知({pokemon_id})")
                            mismatched_cases.append({
                                "pokemon": pokemon_name,
                                "pokemon_types": pokemon_types,
                                "item": item_name,
                                "item_id": item_id
                            })
        
        # 格式化输出结果
        result = f"分析完成！共检查了 {results['total_pokemon']} 只宝可梦\n\n"
        result += "=== 道具分布 ===\n"
        for item_id, count in results["item_distribution"].most_common(20):
            item_name = item_id_to_name.get(item_id, f"未知道具({item_id})")
            result += f"{item_name}: {count} 次\n"
        
        result += "\n=== 类别分布 ===\n"
        total = results['total_pokemon']
        category_counts = results["category_distribution"]
        
        # 合并所有属性道具类别
        type_items_count = 0
        for cat in list(category_counts.keys()):
            if cat.startswith("属性道具"):
                type_items_count += category_counts[cat]
                del category_counts[cat]
        
        category_counts["属性道具"] = type_items_count
        
        result += "类别\t\t实际数量\t实际比例\n"
        result += "-" * 40 + "\n"
        
        for category, count in category_counts.most_common():
            actual_percentage = count / total * 100
            result += f"{category:12}\t{count}\t\t{actual_percentage:.2f}%\n"
        
        # 添加属性匹配度分析
        if total_type_items > 0:
            match_percentage = (type_item_matches / total_type_items) * 100
            result += f"\n=== 属性道具匹配度分析 ===\n"
            result += f"属性道具匹配度: {type_item_matches}/{total_type_items} (匹配度: {match_percentage:.1f}%)\n"
            
            # 显示不匹配的情况
            if mismatched_cases:
                result += f"\n=== 不匹配的情况 (最多显示5个) ===\n"
                for case in mismatched_cases:
                    types_str = "/".join(case["pokemon_types"]) if case["pokemon_types"] else "无属性"
                    result += f"{case['pokemon']} ({types_str}) 携带 {case['item']} ({case['item_id']})\n"
        
        # # 保存详细结果到文件
        # try:
        #     with open("item_distribution_analysis.json", "w", encoding="utf-8") as f:
        #         json.dump(results, f, indent=2, ensure_ascii=False)
        # except IOError as e:
        #     result += f"\n保存详细结果时出错: {str(e)}\n"
        
        # result += f"\n详细结果已保存到 item_distribution_analysis.json\n"
        
        return result
    
    def check_type_item_match(self, pokemon_types, item_id, item_category):
        """
        检查属性道具是否与宝可梦属性匹配:
        1. 攻击类道具: 道具属性与宝可梦属性之一匹配
        2. 防御类道具: 道具属性与宝可梦弱点属性匹配
        3. 特殊类道具: 黑色污泥与毒系宝可梦匹配
        """
        if not config or "item_categories" not in config:
            return False

        # 只检查属性道具
        if not item_category.startswith("属性道具"):
            return False
            
        item_categories = config["item_categories"]
        if "type" not in item_categories:
            return False
            
        type_category = item_categories["type"]
        
        # 将英文属性转换为中文属性以便匹配
        chinese_types = [type_map.get(t, t) for t in pokemon_types]
        
        # 检查攻击类道具 (道具属性与宝可梦属性之一匹配)
        if item_category == "属性道具-攻击" and "attack" in type_category:
            for attr, items in type_category["attack"].items():
                # 将英文属性转换为中文进行比较
                chinese_attr = type_map.get(attr, attr)
                if item_id in items and chinese_attr in chinese_types:
                    return True
        
        # 检查防御类道具 (道具属性与宝可梦弱点属性匹配)
        elif item_category == "属性道具-防御" and "defend" in type_category:
            # 计算宝可梦的弱点属性
            weaknesses = calculate_weaknesses(pokemon_types)
            double_weak = [type_map.get(attr, attr) for attr, multiplier in weaknesses.items() if multiplier == 2.0]
            quadruple_weak = [type_map.get(attr, attr) for attr, multiplier in weaknesses.items() if multiplier == 4.0]
            weak_types = double_weak + quadruple_weak
            
            for attr, items in type_category["defend"].items():
                # 将英文属性转换为中文进行比较
                chinese_attr = type_map.get(attr, attr)
                if item_id in items and chinese_attr in weak_types:
                    return True
                    
        # 检查特殊类道具 (如黑色污泥对毒系宝可梦)
        elif item_category == "属性道具-特殊" and "special" in type_category:
            for key, items in type_category["special"].items():
                if item_id in items:
                    # 特殊情况处理，例如黑色污泥对毒系宝可梦
                    if key == "black_sludge" and "毒" in chinese_types:
                        return True
        
        return False
    
    # 添加清除状态的方法
    def clear_status(self, status_var):
        status_var.set("")

    # 添加设置状态的方法，带有自动清除功能
    def set_status(self, status_var, message, delay=5000):
        # 取消之前的定时器（如果存在）
        timer_key = str(id(status_var))
        timer_id = self.status_timers.get(timer_key)
        if timer_id:
            self.root.after_cancel(timer_id)
        
        # 设置新消息
        status_var.set(message)
        
        # 设置定时器清除消息
        new_timer_id = self.root.after(delay, lambda: self.clear_status(status_var))
        self.status_timers[timer_key] = new_timer_id

    # 添加标签页切换事件处理
    def on_tab_changed(self, event):
        self.clear_status(self.path_status_var)
        self.clear_status(self.config_status_var)
        self.clear_status(self.random_status_var)
        self.clear_status(self.verify_status_var)
        for timer_id in self.status_timers.values():
            self.root.after_cancel(timer_id)
        self.status_timers.clear()
        try:
            sel = self.notebook.select()
            text = self.notebook.tab(sel, "text")
            if text in ("训练家宝可梦查看", "道具分布验证"):
                if not self._is_valid_trainer_dir():
                    messagebox.showerror("错误", "请先设置训练家文件目录")
                    self.notebook.select(self.home_tab)
                    return
            if text in ("宝可梦之家", "CCB"):
                if not self._is_valid_main_file():
                    messagebox.showerror("错误", "请先设置main文件路径")
                    self.notebook.select(self.home_tab)
                    return
        except Exception:
            pass

    def load_data(self):
        """加载必要的数据"""
        global item_id_to_name, pokemon_name_map, ability_map, move_map, move_explanation_map, ability_explanation_map
        global config, trainer_poke_dir, personal_total_bin_path, main_file_path
        
        # 安全加载文件的辅助函数
        def safe_load_json(filename):
            """安全加载JSON文件"""
            return safe_load_file(filename, "json")
        
        def safe_load_txt(filename):
            """安全加载文本文件"""
            return safe_load_file(filename, "txt")
        
        # 加载道具数据
        item_data = safe_load_json("pokemon_item_name.json")
        if item_data:
            global item_id_to_name
            item_id_to_name = {}
            for item_id, item_name in item_data.items():
                try:
                    item_id_to_name[int(item_id)] = item_name
                except ValueError:
                    continue
        else:
            messagebox.showerror("错误", "找不到pokemon_item_name.json文件")
        
        # 加载宝可梦名称映射
        pokemon_name_data = safe_load_json("pokemon_internal_id_name.json")
        if pokemon_name_data:
            global pokemon_name_map
            pokemon_name_map = pokemon_name_data
        else:
            messagebox.showerror("错误", "找不到pokemon_internal_id_name.json文件")
        
        # 加载特性映射
        ability_data = safe_load_json("pokemon_ability.json")
        if ability_data:
            global ability_map
            ability_map = ability_data.get("ability_map", {})
        else:
            messagebox.showerror("错误", "找不到pokemon_ability.json文件")
        
        # 加载技能映射
        move_data = safe_load_json("pokemon_move.json")
        if move_data:
            global move_map
            move_map = move_data.get("move_map", {})
        else:
            messagebox.showerror("错误", "找不到pokemon_move.json文件")
        
        # 加载技能说明映射
        move_explanation_data = safe_load_json("pokemon_move_explanation.json")
        if move_explanation_data:
            global move_explanation_map
            move_explanation_map = move_explanation_data.get("move_explanation_map", {})
        else:
            messagebox.showerror("错误", "找不到pokemon_move_explanation.json文件")
        
        # 加载特性说明映射
        ability_explanation_data = safe_load_json("pokemon_ability_explanation.json")
        if ability_explanation_data:
            global ability_explanation_map
            ability_explanation_map = ability_explanation_data.get("ability_explanation_map", {})
        else:
            messagebox.showerror("错误", "找不到pokemon_ability_explanation.json文件")
        
        # 加载配置文件
        config_data = safe_load_json("item_category_rules.json")
        if config_data:
            global config
            config = config_data
            # 更新全局路径变量
            global trainer_poke_dir, main_file_path
            trainer_poke_dir = config.get("trainer_poke_dir", "")
            personal_total_bin_path = config.get("personal_total_bin_path", "")
            main_file_path = config.get("main_file_path", "")
            self.trainer_dir_var.set(trainer_poke_dir)
            self.personal_file_var.set(personal_total_bin_path)
            self.main_file_var.set(main_file_path)
        else:
            messagebox.showwarning("警告", "找不到item_category_rules.json文件，请先生成配置文件")
        
        # 加载宝可梦属性数据
        pokemon_types_data_tmp = safe_load_json("pokemon_types_final.json")
        if pokemon_types_data_tmp:
            global pokemon_types_data
            pokemon_types_data = pokemon_types_data_tmp
        else:
            messagebox.showwarning("警告", "找不到pokemon_types_final.json文件，请先生成属性数据")
        
        # 加载宝可梦特性数据
        pokemon_abilities_data_tmp = safe_load_json("pokemon_abilities_final.json")
        if pokemon_abilities_data_tmp:
            global pokemon_abilities_data
            pokemon_abilities_data = pokemon_abilities_data_tmp
        else:
            messagebox.showwarning("警告", "找不到pokemon_abilities_final.json文件，请先生成特性数据")
        
        # 程序启动时检测main文件路径并生成JSON文件
        if main_file_path and os.path.isfile(main_file_path):
            # 使用线程避免阻塞UI，但不尝试在线程中更新UI
            def generate_json_thread():
                try:
                    # 导入decrypt_main模块
                    import sys
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    if current_dir not in sys.path:
                        sys.path.append(current_dir)
                    
                    import decrypt_main
                    
                    # 调用decrypt_main的process_main_file函数
                    success = decrypt_main.process_main_file(main_file_path)
                    
                    if success:
                        # 不在线程中更新UI，避免线程问题
                        # 用户可以通过重启程序或手动刷新来获取更新后的数据
                        print("启动时JSON文件生成成功!")
                except Exception as e:
                    # 不在线程中更新UI，避免线程问题
                    print(f"启动时生成JSON文件出错: {str(e)}")
            
            # 启动线程
            threading.Thread(target=generate_json_thread, daemon=True).start()
        
        # 程序启动时加载宝可梦主要信息数据
        self.reload_pokemon_main_info()
        self.update_feature_availability()
    
    def reload_pokemon_main_info(self):
        """重新加载宝可梦主要信息数据"""
        # 安全加载JSON文件的辅助函数
        def safe_load_json(filename):
            return safe_load_file(filename, "json")
        
        pokemon_main_info_tmp = safe_load_json("pokemon_main_info.json")
        if pokemon_main_info_tmp is not None:  # 文件存在且可以解析为JSON（即使是空对象{}）
            global pokemon_main_info
            pokemon_main_info = pokemon_main_info_tmp
            self.set_status(self.path_status_var, "宝可梦主要信息数据加载成功!")
        # 如果文件不存在或无法解析，不再显示警告消息，允许程序使用空数据继续运行
    
    def generate_json_from_main(self, main_file_path):
        """从main文件生成JSON文件"""
        try:
            # 导入decrypt_main模块
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.append(current_dir)
            
            import decrypt_main
            
            # 调用decrypt_main的process_main_file函数
            success = decrypt_main.process_main_file(main_file_path)
            
            if success:
                self.set_status(self.path_status_var, "JSON文件生成成功!")
                # 重新加载宝可梦主要信息数据
                self.reload_pokemon_main_info()
                
                # 刷新宝可梦之家数据
                self.refresh_pokemon_home_data()
                
                # 刷新CCB数据
                self.refresh_ccb_data()
        except Exception as e:
            # self.set_status(self.path_status_var, f"生成JSON文件时出错: {str(e)}")
            messagebox.showerror("错误", f"生成JSON文件时出错: {str(e)}")
    
    def reload_item_replacement_rules(self):
        """重新加载配置文件"""
        # 安全加载JSON文件的辅助函数
        def safe_load_json(filename):
            return safe_load_file(filename, "json")
        
        config_data = safe_load_json("item_category_rules.json")
        if config_data:
            global config
            config = config_data
            # 更新全局路径变量
            global trainer_poke_dir, main_file_path
            trainer_poke_dir = config.get("trainer_poke_dir", "")
            personal_total_bin_path = config.get("personal_total_bin_path", "")
            main_file_path = config.get("main_file_path", "")
            self.trainer_dir_var.set(trainer_poke_dir)
            self.personal_file_var.set(personal_total_bin_path)
            self.main_file_var.set(main_file_path)
        else:
            messagebox.showwarning("警告", "找不到item_category_rules.json文件，请先生成配置文件")
    
    def reload_pokemon_types_final(self):
        """重新加载宝可梦属性数据"""
        # 安全加载JSON文件的辅助函数
        def safe_load_json(filename):
            return safe_load_file(filename, "json")
        
        pokemon_types_data_tmp = safe_load_json("pokemon_types_final.json")
        if pokemon_types_data_tmp:
            global pokemon_types_data
            pokemon_types_data = pokemon_types_data_tmp
        else:
            messagebox.showwarning("警告", "找不到pokemon_types_final.json文件，请先生成属性数据")
    
    def reload_pokemon_abilities_final(self):
        """重新加载宝可梦特性数据"""
        # 安全加载JSON文件的辅助函数
        def safe_load_json(filename):
            return safe_load_file(filename, "json")
        
        pokemon_abilities_data_tmp = safe_load_json("pokemon_abilities_final.json")
        if pokemon_abilities_data_tmp:
            global pokemon_abilities_data
            pokemon_abilities_data = pokemon_abilities_data_tmp
        else:
            messagebox.showwarning("警告", "找不到pokemon_abilities_final.json文件，请先生成特性数据")
    
    def setup_pokemon_home_tab(self):
        """设置宝可梦之家标签页"""
        # 导入pokemon_home模块
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        try:
            import pokemon_home
            # 创建宝可梦之家标签页
            self.pokemon_home_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.pokemon_home_tab, text="宝可梦之家")
            
            # 调用pokemon_home模块中的setup_pokemon_home函数
            self.pokemon_home_instance = pokemon_home.setup_pokemon_home(self.pokemon_home_tab)
        except ImportError as e:
            # 如果导入失败，显示错误信息
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="宝可梦之家")
            
            error_label = ttk.Label(error_frame, text=f"无法加载宝可梦之家模块: {str(e)}")
            error_label.pack(pady=20, padx=20)
            
            error_label2 = ttk.Label(error_frame, text="请确保pokemon_home.py文件存在")
            error_label2.pack(pady=10, padx=20)
    
    def setup_ccb_tab(self):
        """设置CCB标签页"""
        # 导入ccb模块
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        try:
            import ccb
            # 创建CCB标签页
            self.ccb_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.ccb_tab, text="CCB")
            
            # 调用ccb模块中的setup_ccb函数，传递pokemon_home实例
            pokemon_home_instance = getattr(self, 'pokemon_home_instance', None)
            self.ccb_instance = ccb.setup_ccb(self.ccb_tab, pokemon_home_instance)
        except ImportError as e:
            # 如果导入失败，显示错误信息
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="CCB")
            
            error_label = ttk.Label(error_frame, text=f"无法加载CCB模块: {str(e)}")
            error_label.pack(pady=20, padx=20)
            
            error_label2 = ttk.Label(error_frame, text="请确保ccb.py文件存在")
            error_label2.pack(pady=10, padx=20)
    
    def refresh_pokemon_home_data(self):
        """刷新宝可梦之家的数据"""
        try:
            # 检查宝可梦之家标签页是否存在
            if hasattr(self, 'pokemon_home_tab') and self.pokemon_home_tab:
                # 导入pokemon_home模块
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.append(current_dir)
                
                import pokemon_home
                
                # 获取宝可梦之家标签页中的所有子组件
                for widget in self.pokemon_home_tab.winfo_children():
                    # 查找PokemonHome类的实例
                    if isinstance(widget, pokemon_home.PokemonHome):
                        # 调用刷新数据方法
                        widget.refresh_data()
                        self.set_status(self.path_status_var, "宝可梦之家数据已刷新!")
                        return
                
                # 如果没有找到PokemonHome实例，尝试重新加载整个标签页
                self.notebook.forget(self.pokemon_home_tab)
                self.setup_pokemon_home_tab()
                self.set_status(self.path_status_var, "宝可梦之家标签页已重新加载!")
        except Exception as e:
            print(f"刷新宝可梦之家数据时出错: {str(e)}")
            # 不显示错误对话框，避免干扰用户
    
    def refresh_ccb_data(self):
        """刷新CCB的数据"""
        try:
            # 检查CCB标签页是否存在
            if hasattr(self, 'ccb_tab') and self.ccb_tab:
                # 导入ccb模块
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.append(current_dir)
                
                import ccb
                
                # 获取CCB标签页中的所有子组件
                for widget in self.ccb_tab.winfo_children():
                    # 查找CCB类的实例
                    if isinstance(widget, ccb.CCB):
                        # 调用刷新数据方法
                        widget.load_pokemon_data()
                        self.set_status(self.path_status_var, "CCB数据已刷新!")
                        return
                
                # 如果没有找到CCB实例，尝试重新加载整个标签页
                self.notebook.forget(self.ccb_tab)
                self.setup_ccb_tab()
                self.set_status(self.path_status_var, "CCB标签页已重新加载!")
        except Exception as e:
            print(f"刷新CCB数据时出错: {str(e)}")
            # 不显示错误对话框，避免干扰用户

# 主函数
def main():
    root = tk.Tk()
    app = PokemonToolsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
