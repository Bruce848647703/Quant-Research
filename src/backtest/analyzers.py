"""
自定义分析器模块
提供回测结果的统计分析
"""
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Any


class SharpeRatioAnalyzer(bt.Analyzer):
    """夏普比率分析器"""
    
    params = dict(
        riskfreerate=0.02,  # 无风险利率（年化）
        timeframe=bt.TimeFrame.Days,
    )
    
    def __init__(self):
        self.daily_returns = []
        self.dates = []
    
    def next(self):
        self.daily_returns.append(self.strategy.broker.getvalue())
        self.dates.append(self.datas[0].datetime.date(0))
    
    def get_analysis(self):
        """计算夏普比率"""
        values = np.array(self.daily_returns)
        if len(values) < 2:
            return {"sharpe": 0.0, "annual_return": 0.0, "volatility": 0.0}
        
        # 日收益率
        daily_ret = np.diff(values) / values[:-1]
        
        # 年化
        n_days = len(daily_ret)
        annual_return = (1 + np.mean(daily_ret)) ** 252 - 1
        annual_vol = np.std(daily_ret) * np.sqrt(252)
        
        # 夏普比率
        sharpe = (annual_return - self.params.riskfreerate) / annual_vol if annual_vol > 0 else 0
        
        return {
            "sharpe": sharpe,
            "annual_return": annual_return,
            "volatility": annual_vol,
            "total_return": (values[-1] / values[0]) - 1,
            "final_value": values[-1],
        }


class DrawdownAnalyzer(bt.Analyzer):
    """最大回撤分析器"""
    
    def __init__(self):
        self.peak = 0
        self.max_drawdown = 0
        self.current_drawdown = 0
        self.values = []
    
    def next(self):
        value = self.strategy.broker.getvalue()
        self.values.append(value)
        
        if value > self.peak:
            self.peak = value
        
        if self.peak > 0:
            self.current_drawdown = (self.peak - value) / self.peak
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
    
    def get_analysis(self):
        return {
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "peak_value": self.peak,
            "final_value": self.values[-1] if self.values else 0,
        }


class TradeAnalyzer(bt.Analyzer):
    """交易统计分析器"""
    
    def __init__(self):
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.total_trades += 1
            pnl = trade.pnlcomm
            
            if pnl > 0:
                self.winning_trades += 1
                self.total_profit += pnl
            else:
                self.losing_trades += 1
                self.total_loss += abs(pnl)
    
    def get_analysis(self):
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        profit_factor = self.total_profit / self.total_loss if self.total_loss > 0 else float('inf')
        avg_profit = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = self.total_loss / self.losing_trades if self.losing_trades > 0 else 0
        
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "net_profit": self.total_profit - self.total_loss,
        }


def generate_report(results: Dict[str, Any], output_path: str = None) -> str:
    """
    生成回测报告
    
    Args:
        results: 各分析器的结果字典
        output_path: 报告保存路径（可选）
        
    Returns:
        格式化报告文本
    """
    report = []
    report.append("=" * 60)
    report.append("回测报告 - 短期反转因子策略")
    report.append("=" * 60)
    report.append("")
    
    # 收益指标
    if "sharpe" in results:
        sharpe_data = results["sharpe"]
        report.append("【收益指标】")
        report.append(f"  年化收益率: {sharpe_data.get('annual_return', 0):.2%}")
        report.append(f"  年化波动率: {sharpe_data.get('volatility', 0):.2%}")
        report.append(f"  夏普比率:   {sharpe_data.get('sharpe', 0):.3f}")
        report.append(f"  总收益率:   {sharpe_data.get('total_return', 0):.2%}")
        report.append(f"  期末净值:   {sharpe_data.get('final_value', 0):,.2f}")
        report.append("")
    
    # 风险指标
    if "drawdown" in results:
        dd_data = results["drawdown"]
        report.append("【风险指标】")
        report.append(f"  最大回撤:   {dd_data.get('max_drawdown', 0):.2%}")
        report.append(f"  当前回撤:   {dd_data.get('current_drawdown', 0):.2%}")
        report.append(f"  历史最高:   {dd_data.get('peak_value', 0):,.2f}")
        report.append("")
    
    # 交易统计
    if "trades" in results:
        trade_data = results["trades"]
        report.append("【交易统计】")
        report.append(f"  总交易次数: {trade_data.get('total_trades', 0)}")
        report.append(f"  盈利次数:   {trade_data.get('winning_trades', 0)}")
        report.append(f"  亏损次数:   {trade_data.get('losing_trades', 0)}")
        report.append(f"  胜率:       {trade_data.get('win_rate', 0):.2%}")
        report.append(f"  盈亏比:     {trade_data.get('profit_factor', 0):.2f}")
        report.append(f"  平均盈利:   {trade_data.get('avg_profit', 0):,.2f}")
        report.append(f"  平均亏损:   {trade_data.get('avg_loss', 0):,.2f}")
        report.append(f"  净收益:     {trade_data.get('net_profit', 0):,.2f}")
        report.append("")
    
    report.append("=" * 60)
    
    report_text = "\n".join(report)
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"报告已保存至: {output_path}")
    
    return report_text
