"""
因子单元测试
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.factors.momentum import ShortTermReversalFactor, MomentumFactor


def create_mock_data(n_stocks: int = 10, n_days: int = 30) -> pd.DataFrame:
    """创建模拟数据用于测试"""
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    stock_codes = [f"{str(i).zfill(6)}" for i in range(n_stocks)]
    
    data = []
    for code in stock_codes:
        # 生成随机价格序列
        base_price = np.random.uniform(10, 100)
        returns = np.random.normal(0.001, 0.02, n_days)
        prices = base_price * np.cumprod(1 + returns)
        
        for i, date in enumerate(dates):
            data.append({
                "date": date,
                "stock_code": code,
                "open": prices[i] * 0.99,
                "high": prices[i] * 1.02,
                "low": prices[i] * 0.98,
                "close": prices[i],
                "volume": np.random.randint(100000, 1000000),
            })
    
    df = pd.DataFrame(data)
    df = df.set_index(["date", "stock_code"]).sort_index()
    return df


class TestShortTermReversalFactor:
    """短期反转因子测试"""
    
    def test_compute(self):
        """测试因子计算"""
        data = create_mock_data(n_stocks=5, n_days=20)
        factor = ShortTermReversalFactor(trend_window=5, reversal_window=1)
        
        result = factor.compute(data)
        
        # 检查输出列
        assert "factor_value" in result.columns
        assert "return_trend" in result.columns
        assert "return_reversal" in result.columns
        
        # 检查无NaN
        assert not result["factor_value"].isna().any()
        
        # 检查因子值 = 趋势收益 - 反转收益
        np.testing.assert_array_almost_equal(
            result["factor_value"].values,
            (result["return_trend"] - result["return_reversal"]).values
        )
    
    def test_compute_with_groups(self):
        """测试分组功能"""
        data = create_mock_data(n_stocks=10, n_days=20)
        factor = ShortTermReversalFactor()
        
        result = factor.compute_with_groups(data, num_groups=5)
        
        # 检查分组列
        assert "group" in result.columns
        
        # 检查分组数量
        unique_groups = result["group"].unique()
        assert len(unique_groups) <= 5
    
    def test_normalize_zscore(self):
        """测试Z-score标准化"""
        data = create_mock_data(n_stocks=10, n_days=20)
        factor = ShortTermReversalFactor()
        
        result = factor.compute(data)
        normalized = factor.normalize(result, method="zscore")
        
        # 每个截面的均值应接近0，标准差接近1
        daily_mean = normalized.groupby(level="date")["factor_value"].mean()
        daily_std = normalized.groupby(level="date")["factor_value"].std()
        
        assert daily_mean.abs().max() < 0.1  # 均值接近0
        assert (daily_std - 1).abs().max() < 0.1  # 标准差接近1


class TestMomentumFactor:
    """经典动量因子测试"""
    
    def test_compute(self):
        """测试经典动量因子计算"""
        data = create_mock_data(n_stocks=5, n_days=300)
        factor = MomentumFactor(lookback=252, skip=21)
        
        result = factor.compute(data)
        
        assert "factor_value" in result.columns
        assert not result["factor_value"].isna().any()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
