import os
import sys
import json
from typing import List, Optional, Dict, Any

def get_base_dir():
    """获取程序的基础目录"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_dir():
    """获取PyInstaller资源目录"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe，获取PyInstaller的临时资源目录
        return sys._MEIPASS
    else:
        # 如果是开发环境，返回脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))

def get_config_dir():
    """获取配置文件目录"""
    base_dir = get_base_dir()
    return os.path.join(base_dir, "config")

def safe_load_file(filename: str, file_type: str = "json") -> Optional[Any]:
    """
    安全加载文件，支持JSON和文本文件
    
    优先级（双重读取机制）：
    1. 外部数据：当前目录/config/文件名（用户生成的数据）
    2. 外部数据：当前目录/文件名（用户生成的数据）
    3. 内置数据：资源目录/config/文件名（打包时包含的数据）
    4. 内置数据：资源目录/文件名（打包时包含的数据）
    
    Args:
        filename: 文件名
        file_type: 文件类型，"json"或"txt"
    
    Returns:
        文件内容，如果找不到返回None
    """
    base_dir = get_base_dir()
    resource_dir = get_resource_dir()

    if filename == "static_mappings.json":
        search_paths = [
            os.path.join(base_dir, "config", filename),
            os.path.join(base_dir, "data", filename),
            os.path.join(resource_dir, "config", filename),
            os.path.join(resource_dir, "data", filename)
        ]
    else:
        search_paths = [
            os.path.join(base_dir, "config", filename),
            os.path.join(base_dir, "data", filename),
            os.path.join(base_dir, filename),
            os.path.join(resource_dir, "config", filename),
            os.path.join(resource_dir, "data", filename),
            os.path.join(resource_dir, filename)
        ]
    
    for file_path in search_paths:
        try:
            if file_type == "json":
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:  # txt
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.readlines()
        except (FileNotFoundError, IOError, json.JSONDecodeError):
            continue
    
    return None

def safe_save_file(data: Any, filename: str, file_type: str = "json", ensure_config_dir: bool = False) -> bool:
    """
    安全保存文件，支持JSON和文本文件
    
    Args:
        data: 要保存的数据
        filename: 文件名
        file_type: 文件类型，"json"或"txt"
        ensure_config_dir: 是否确保在config目录下保存
    
    Returns:
        是否保存成功
    """
    base_dir = get_base_dir()
    
    if ensure_config_dir or filename in ["item_category_rules.json", "pokemon_abilities_final.json", "pokemon_types_final.json"]:
        # 确保config目录存在
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, filename)
    else:
        file_path = os.path.join(base_dir, "config", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        if file_type == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:  # txt
            with open(file_path, "w", encoding="utf-8") as f:
                if isinstance(data, list):
                    f.writelines(data)
                else:
                    f.write(str(data))
        return True
    except IOError as e:
        print(f"保存文件 {filename} 时出错: {e}")
        return False

def get_file_path(filename: str) -> Optional[str]:
    """
    获取文件的完整路径，但不加载内容
    
    Args:
        filename: 文件名
    
    Returns:
        文件完整路径，如果找不到返回None
    """
    base_dir = get_base_dir()
    
    search_paths = [
        os.path.join(base_dir, "config", filename),
        os.path.join(base_dir, filename),
        os.path.join(os.path.dirname(__file__) if not getattr(sys, 'frozen', False) else base_dir, "config", filename),
        os.path.join(os.path.dirname(__file__) if not getattr(sys, 'frozen', False) else base_dir, filename)
    ]
    
    for file_path in search_paths:
        if os.path.exists(file_path):
            return file_path
    
    return None

def file_exists(filename: str) -> bool:
    """检查文件是否存在"""
    return get_file_path(filename) is not None

def ensure_config_directory():
    """确保config目录存在"""
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    return config_dir
