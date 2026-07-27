"""
因子基类模块
定义因子计算的抽象接口
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseFactor(ABC):
    """因子抽象基类"""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}
    
    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子值
        
        Args:
            data: 包含OHLCV的面板数据，MultiIndex (date, stock_code)
            
        Returns:
            包含 'factor_value' 列的DataFrame
        """
        pass
    
    def normalize(self, data: pd.DataFrame, column: str = "factor_value",
                  method: str = "zscore") -> pd.DataFrame:
        """
        截面标准化
        
        Args:
            data: 包含因子值的DataFrame
            column: 需要标准化的列名
            method: 标准化方法，'zscore' 或 'rank'
            
        Returns:
            标准化后的DataFrame
        """
        df = data.copy()
        
        if method == "zscore":
            # Z-score标准化（去极值后标准化）
            # MAD去极值
            median = df.groupby(level="date")[column].transform("median")
            mad = df.groupby(level="date")[column].transform(
                lambda x: np.median(np.abs(x - x.median()))
            )
            upper = median + 3 * 1.4826 * mad
            lower = median - 3 * 1.4826 * mad
            df[column] = df[column].clip(lower, upper)
            
            # Z-score
            mean = df.groupby(level="date")[column].transform("mean")
            std = df.groupby(level="date")[column].transform("std")
            df[column] = (df[column] - mean) / std
            
        elif method == "rank":
            # 排名标准化（0-1之间）
            df[column] = df.groupby(level="date")[column].rank(pct=True)
        
        return df
    
    def group_stocks(self, data: pd.DataFrame, column: str = "factor_value",
                     num_groups: int = 5) -> pd.DataFrame:
        """
        五分位分组
        
        Args:
            data: 包含因子值的DataFrame
            column: 分组依据的列名
            num_groups: 分组数量
            
        Returns:
            包含 'group' 列的DataFrame（1=最高分，num_groups=最低分）
        """
        df = data.copy()
        df["group"] = df.groupby(level="date")[column].transform(
            lambda x: pd.qcut(x, q=num_groups, labels=range(num_groups, 0, -1),
                             duplicates="drop")
        )
        return df
