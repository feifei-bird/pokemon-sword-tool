import json
import os
from typing import Any, Dict, Optional

# 兼容现有模块调用接口：safe_load_file/safe_save_file

def get_base_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__)).rsplit(os.sep, 1)[0]
    except Exception:
        return "."


def _candidate_paths(rel_or_abs: str):
    # 优先按绝对路径
    if os.path.isabs(rel_or_abs):
        yield rel_or_abs
    # 相对路径：尝试 config、data 和当前工作目录
    base = get_base_dir()
    yield os.path.join(base, "config", rel_or_abs)
    yield os.path.join(base, "data", rel_or_abs)
    yield os.path.join(base, rel_or_abs)


def safe_load_file(file_path: str) -> Optional[Dict[str, Any]]:
    candidates = list(_candidate_paths(file_path))
    for p in candidates:
        try:
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            continue
    return None


def safe_save_file(obj: Dict[str, Any], file_path: str) -> bool:
    try:
        base = get_base_dir()
        if not os.path.isabs(file_path):
            # 默认写入 config
            path = os.path.join(base, "config", file_path)
        else:
            path = file_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

