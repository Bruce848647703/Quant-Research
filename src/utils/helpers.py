"""
工具函数模块
"""
import os
import yaml
from typing import Dict


def load_config(config_path: str = None) -> Dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为 config/config.yaml
        
    Returns:
        配置字典
    """
    if config_path is None:
        # 默认路径
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "config.yaml")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def ensure_dir(dir_path: str):
    """确保目录存在"""
    os.makedirs(dir_path, exist_ok=True)


def format_pct(value: float, decimals: int = 2) -> str:
    """格式化百分比"""
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """格式化数字（千分位）"""
    return f"{value:,.{decimals}f}"
