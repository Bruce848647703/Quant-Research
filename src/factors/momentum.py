"""
短期反转因子模块
因子 = 5日收益率 - 1日收益率

逻辑：
- 5日收益率代表短期趋势方向
- 1日收益率代表最近一天的反转信号（过度反应）
- 两者相减，剥离最近一天的扰动，捕捉反转机会
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

from .base import BaseFactor


class ShortTermReversalFactor(BaseFactor):
    """
    短期反转因子：5日收益 - 1日收益
    
    高因子值 = 趋势强但最近一天下跌 → 超跌反弹机会
    低因子值 = 趋势弱但最近一天上涨 → 超涨回调风险
    """
    
    def __init__(self, trend_window: int = 5, reversal_window: int = 1):
        super().__init__(
            name="short_term_reversal",
            params={
                "trend_window": trend_window,
                "reversal_window": reversal_window
            }
        )
        self.trend_window = trend_window
        self.reversal_window = reversal_window
    
    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算短期反转因子
        
        Args:
            data: 面板数据，MultiIndex (date, stock_code)，需包含 'close' 列
            
        Returns:
            包含 factor_value, return_trend, return_reversal 列的DataFrame
        """
        df = data.copy()
        
        # 计算趋势收益率（5日）
        df["return_trend"] = df.groupby(level="stock_code")["close"].pct_change(
            self.trend_window
        )
        
        # 计算反转收益率（1日）
        df["return_reversal"] = df.groupby(level="stock_code")["close"].pct_change(
            self.reversal_window
        )
        
        # 因子值 = 趋势收益 - 反转收益
        df["factor_value"] = df["return_trend"] - df["return_reversal"]
        
        # 删除NaN
        df = df.dropna(subset=["factor_value", "return_trend", "return_reversal"])
        
        return df
    
    def compute_with_groups(self, data: pd.DataFrame, num_groups: int = 5,
                           normalize_method: str = "zscore") -> pd.DataFrame:
        """
        完整计算流程：计算因子 → 标准化 → 分组
        
        Args:
            data: 原始面板数据
            num_groups: 分组数量
            normalize_method: 标准化方法
            
        Returns:
            包含因子值和分组信息的DataFrame
        """
        # 计算因子值
        df = self.compute(data)
        
        # 截面标准化
        df = self.normalize(df, method=normalize_method)
        
        # 五分位分组
        df = self.group_stocks(df, num_groups=num_groups)
        
        return df


class MomentumFactor(BaseFactor):
    """
    经典动量因子（备选）：12-1月动量
    
    计算过去12个月收益率，跳过最近1个月
    """
    
    def __init__(self, lookback: int = 252, skip: int = 21):
        super().__init__(
            name="momentum_12_1",
            params={"lookback": lookback, "skip": skip}
        )
        self.lookback = lookback
        self.skip = skip
    
    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算经典动量因子"""
        df = data.copy()
        
        # 计算过去12个月收益率
        df["return_12m"] = df.groupby(level="stock_code")["close"].pct_change(self.lookback)
        
        # 计算最近1个月收益率
        df["return_1m"] = df.groupby(level="stock_code")["close"].pct_change(self.skip)
        
        # 动量 = 12月收益 - 1月收益（跳过最近1个月）
        df["factor_value"] = df["return_12m"] - df["return_1m"]
        
        df = df.dropna(subset=["factor_value"])
        
        return df
