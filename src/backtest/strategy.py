"""
Backtrader回测策略模块
实现短期反转因子的周度轮动策略
"""
import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List


class ShortTermReversalStrategy(bt.Strategy):
    """
    短期反转因子轮动策略
    
    每周调仓一次，按因子值排序：
    - 买入Top组（因子值最高，反转信号最强）
    - 卖出Bottom组（因子值最低）
    """
    
    params = dict(
        rebalance_weekday=0,  # 0=周一
        stocks_per_group=20,  # 每组持仓数量
        num_groups=5,         # 分组数量
        long_group=1,         # 做多组别（1=最高分）
        printlog=True,
    )
    
    def __init__(self):
        self.order_dict = {}  # 存储各股票的挂单
        self.rebalance_dates = []  # 调仓日期列表
        self.current_rebalance_idx = 0
        
        # 预计算调仓日期（每周一）
        self._calc_rebalance_dates()
    
    def _calc_rebalance_dates(self):
        """计算所有调仓日期"""
        # 获取所有交易日期
        trading_days = set()
        for d in self.datas:
            for session in d.p.sessionstart, d.p.sessionend:
                pass
        
        # 简化：在next中判断是否为周一
        pass
    
    def log(self, txt, dt=None):
        """日志输出"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"[{dt.isoformat()}] {txt}")
    
    def notify_order(self, order):
        """订单状态回调"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"买入成交: {order.data._name}, 价格: {order.executed.price:.2f}, "
                        f"数量: {order.executed.size:.0f}, 手续费: {order.executed.comm:.2f}")
            else:
                self.log(f"卖出成交: {order.data._name}, 价格: {order.executed.price:.2f}, "
                        f"数量: {order.executed.size:.0f}, 手续费: {order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单取消/拒绝: {order.data._name}")
        
        # 清理订单记录
        if order.data in self.order_dict:
            del self.order_dict[order.data]
    
    def notify_trade(self, trade):
        """交易完成回调"""
        if trade.isclosed:
            self.log(f"交易平仓: {trade.data._name}, 毛利: {trade.pnl:.2f}, "
                    f"净利: {trade.pnlcomm:.2f}")
    
    def next(self):
        """每个交易日执行"""
        # 检查是否有未完成的订单
        pending_orders = [o for o in self.order_dict.values() if o is not None]
        if pending_orders:
            return
        
        # 判断是否为调仓日（周一）
        current_date = self.datas[0].datetime.date(0)
        if current_date.weekday() != self.params.rebalance_weekday:
            return
        
        # 执行调仓
        self._rebalance(current_date)
    
    def _rebalance(self, current_date):
        """执行调仓逻辑"""
        # 获取所有股票的因子值
        factor_scores = {}
        for d in self.datas:
            if hasattr(d, 'factor_value') and len(d) > 0:
                try:
                    fv = d.factor_value[0]
                    if not np.isnan(fv):
                        factor_scores[d] = fv
                except (IndexError, AttributeError):
                    continue
        
        if len(factor_scores) < self.params.stocks_per_group * 2:
            return
        
        # 按因子值排序
        sorted_stocks = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 确定目标持仓（Top组）
        target_stocks = [d for d, _ in sorted_stocks[:self.params.stocks_per_group]]
        
        # 获取当前持仓
        current_positions = {d: self.getposition(d).size for d in self.datas 
                           if self.getposition(d).size > 0}
        
        # 卖出不在目标中的持仓
        for d, size in current_positions.items():
            if d not in target_stocks:
                if d not in self.order_dict or self.order_dict[d] is None:
                    self.log(f"调仓卖出: {d._name}")
                    self.order_dict[d] = self.sell(data=d, size=size)
        
        # 计算每只股票的目标仓位（等权）
        if target_stocks:
            # 可用资金
            available_cash = self.broker.getcash() * 0.95  # 保留5%现金
            cash_per_stock = available_cash / len(target_stocks)
            
            for d in target_stocks:
                current_size = self.getposition(d).size
                target_price = d.close[0]
                
                if target_price <= 0:
                    continue
                
                # 计算目标股数（向下取整到100的倍数）
                target_size = int(cash_per_stock / target_price / 100) * 100
                
                if target_size <= 0:
                    continue
                
                # 需要调整的仓位
                size_diff = target_size - current_size
                
                if size_diff > 0 and abs(size_diff) >= 100:
                    # 需要加仓
                    if d not in self.order_dict or self.order_dict[d] is None:
                        self.log(f"调仓买入: {d._name}, 目标: {target_size}")
                        self.order_dict[d] = self.buy(data=d, size=size_diff)
                elif size_diff < 0 and abs(size_diff) >= 100:
                    # 需要减仓
                    if d not in self.order_dict or self.order_dict[d] is None:
                        self.log(f"调仓减仓: {d._name}, 目标: {target_size}")
                        self.order_dict[d] = self.sell(data=d, size=abs(size_diff))
        
        self.log(f"调仓完成, 持仓股票数: {len(target_stocks)}")


class FactorDataFeed(bt.PandasData):
    """
    自定义数据源，包含因子值字段
    """
    lines = ('factor_value',)
    
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', -1),
        ('factor_value', 'factor_value'),
    )
