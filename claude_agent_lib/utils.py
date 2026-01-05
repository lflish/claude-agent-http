"""
工具函数模块
提供一些辅助功能
"""
from typing import Dict, Any, Optional
import json
import os


def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """
    从 JSON 文件加载配置

    Args:
        file_path: 配置文件路径

    Returns:
        Dict[str, Any]: 配置字典
    """
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load config from {file_path}: {e}")


def save_config_to_file(config: Dict[str, Any], file_path: str) -> bool:
    """
    保存配置到 JSON 文件

    Args:
        config: 配置字典
        file_path: 配置文件路径

    Returns:
        bool: 是否成功
    """
    try:
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        raise ValueError(f"Failed to save config to {file_path}: {e}")


def load_session_id_from_file(file_path: str = ".sessionid") -> Optional[str]:
    """
    从文件加载 session_id（用于 CLI 兼容）

    Args:
        file_path: session 文件路径

    Returns:
        Optional[str]: session_id 或 None
    """
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('session_id')
    except Exception:
        return None


def save_session_id_to_file(session_id: str, file_path: str = ".sessionid") -> bool:
    """
    保存 session_id 到文件（用于 CLI 兼容）

    Args:
        session_id: 会话 ID
        file_path: session 文件路径

    Returns:
        bool: 是否成功
    """
    try:
        from datetime import datetime
        data = {
            'session_id': session_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
