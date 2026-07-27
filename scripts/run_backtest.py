#!/usr/bin/env python3
"""
回测运行脚本
一键运行短期反转因子回测
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
import pandas as pd
import numpy as np

from src.data.data_loader import DataLoader
from src.factors.momentum import ShortTermReversalFactor
from src.backtest.engine import BacktestEngine
from src.utils.helpers import load_config, ensure_dir


def prepare_backtest_data(config: Dict) -> pd.DataFrame:
    """
    准备回测数据：加载数据 → 计算因子 → 分组
    
    Args:
        config: 配置字典
        
    Returns:
        包含因子值的面板数据
    """
    data_config = config["data"]
    factor_config = config["factor"]
    
    print("=" * 60)
    print("数据准备阶段")
    print("=" * 60)
    
    # 加载数据
    loader = DataLoader(
        raw_dir=data_config["raw_dir"],
        processed_dir=data_config["processed_dir"]
    )
    
    data = loader.load_data(
        start_date=data_config["start_date"],
        end_date=data_config["end_date"]
    )
    
    print(f"数据加载完成: {data.shape}")
    
    # 计算因子
    print("\n计算短期反转因子...")
    factor = ShortTermReversalFactor(
        trend_window=factor_config["trend_window"],
        reversal_window=factor_config["reversal_window"]
    )
    
    factor_data = factor.compute_with_groups(
        data,
        num_groups=config["backtest"]["num_groups"],
        normalize_method="zscore"
    )
    
    print(f"因子计算完成: {factor_data.shape}")
    print(f"因子值统计:")
    print(factor_data["factor_value"].describe())
    
    return factor_data


def run_backtest(config: Dict, factor_data: pd.DataFrame):
    """
    运行回测
    
    Args:
        config: 配置字典
        factor_data: 包含因子值的面板数据
    """
    bt_config = config["backtest"]
    results_config = config["results"]
    
    print("\n" + "=" * 60)
    print("回测阶段")
    print("=" * 60)
    
    # 初始化引擎
    engine = BacktestEngine(config)
    
    # 为每只股票添加数据
    stock_codes = factor_data.index.get_level_values("stock_code").unique()
    print(f"添加 {len(stock_codes)} 只股票数据...")
    
    for code in stock_codes:
        stock_data = factor_data.xs(code, level="stock_code").reset_index()
        if len(stock_data) > 10:  # 至少需要10个交易日
            engine.add_data(stock_data, name=code)
    
    # 运行回测
    analysis = engine.run()
    
    # 保存报告
    ensure_dir(results_config["report_dir"])
    report_path = engine.save_report(analysis, results_config["report_dir"])
    
    # 保存分析结果
    results_path = os.path.join(results_config["report_dir"], "analysis_results.yaml")
    with open(results_path, "w", encoding="utf-8") as f:
        yaml.dump(analysis, f, allow_unicode=True, default_flow_style=False)
    print(f"\n分析结果已保存至: {results_path}")
    
    return analysis


def main():
    """主函数"""
    print("短期反转因子回测系统")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    print(f"配置加载完成")
    print(f"  股票池: {config['data']['universe']}")
    print(f"  时间范围: {config['data']['start_date']} ~ {config['data']['end_date']}")
    print(f"  因子: {config['factor']['name']}")
    print(f"  调仓频率: {config['backtest']['rebalance_freq']}")
    print()
    
    # 准备数据
    factor_data = prepare_backtest_data(config)
    
    # 运行回测
    analysis = run_backtest(config, factor_data)
    
    print("\n回测完成!")


if __name__ == "__main__":
    main()
