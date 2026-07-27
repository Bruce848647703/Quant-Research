"""
Backtrader回测引擎封装
"""
import os
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from .strategy import ShortTermReversalStrategy, FactorDataFeed
from .analyzers import SharpeRatioAnalyzer, DrawdownAnalyzer, TradeAnalyzer, generate_report


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.cerebro = bt.Cerebro()
        self._setup_broker()
        self._setup_analyzers()
    
    def _setup_broker(self):
        """配置交易参数"""
        bt_config = self.config.get("backtest", {})
        
        # 初始资金
        self.cerebro.broker.setcash(bt_config.get("initial_cash", 1000000))
        
        # 手续费
        commission = bt_config.get("commission", 0.0003)
        self.cerebro.broker.setcommission(commission=commission)
        
        # 默认滑点
        self.cerebro.broker.set_slippage_perc(perc=0.001)
    
    def _setup_analyzers(self):
        """添加分析器"""
        self.cerebro.addanalyzer(SharpeRatioAnalyzer, _name="sharpe")
        self.cerebro.addanalyzer(DrawdownAnalyzer, _name="drawdown")
        self.cerebro.addanalyzer(TradeAnalyzer, _name="trades")
    
    def add_data(self, data: pd.DataFrame, name: str):
        """
        添加股票数据
        
        Args:
            data: 包含OHLCV和factor_value的DataFrame
            name: 数据名称（股票代码）
        """
        # 确保索引正确
        if isinstance(data.index, pd.MultiIndex):
            data = data.reset_index()
        
        data["date"] = pd.to_datetime(data["date"])
        data = data.set_index("date").sort_index()
        
        # 确保必需列存在
        required_cols = ["open", "high", "low", "close", "volume", "factor_value"]
        for col in required_cols:
            if col not in data.columns:
                data[col] = 0
        
        # 创建Backtrader数据源
        bt_data = FactorDataFeed(
            dataname=data,
            datetime=None,
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            openinterest=-1,
            factor_value="factor_value",
        )
        
        self.cerebro.adddata(bt_data, name=name)
    
    def run(self, **kwargs) -> Dict:
        """
        运行回测
        
        Returns:
            回测结果字典
        """
        # 添加策略
        bt_config = self.config.get("backtest", {})
        self.cerebro.addstrategy(
            ShortTermReversalStrategy,
            stocks_per_group=bt_config.get("stocks_per_group", 20),
            num_groups=bt_config.get("num_groups", 5),
            long_group=bt_config.get("long_group", 1),
        )
        
        print("开始回测...")
        print(f"初始资金: {self.cerebro.broker.getvalue():,.2f}")
        print()
        
        # 运行
        results = self.cerebro.run(**kwargs)
        strat = results[0]
        
        # 收集结果
        final_value = self.cerebro.broker.getvalue()
        print(f"\n期末资金: {final_value:,.2f}")
        
        analysis = {
            "sharpe": strat.analyzers.sharpe.get_analysis(),
            "drawdown": strat.analyzers.drawdown.get_analysis(),
            "trades": strat.analyzers.trades.get_analysis(),
        }
        
        return analysis
    
    def plot(self, save_path: str = None):
        """绘制回测结果"""
        try:
            self.cerebro.plot(
                style="candle",
                barup="red",
                bardown="green",
                savefig=save_path,
            )
        except Exception as e:
            print(f"绘图失败: {e}")
    
    def save_report(self, analysis: Dict, output_dir: str = "results/reports"):
        """保存回测报告"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"backtest_report_{timestamp}.txt")
        
        report_text = generate_report(analysis, report_path)
        print(report_text)
        
        return report_path
