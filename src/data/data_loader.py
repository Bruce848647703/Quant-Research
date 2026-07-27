"""
数据获取与预处理模块
使用 akshare 获取A股日线数据
"""
import os
import time
import pandas as pd
import akshare as ak
from typing import List, Optional
from datetime import datetime


class DataLoader:
    """A股数据加载器"""
    
    def __init__(self, raw_dir: str = "data/raw", processed_dir: str = "data/processed"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
    
    def get_hs300_stocks(self) -> pd.DataFrame:
        """获取沪深300成分股列表"""
        try:
            df = ak.index_stock_cons(symbol="000300")
            return df
        except Exception as e:
            print(f"获取沪深300成分股失败: {e}")
            return pd.DataFrame()
    
    def fetch_stock_daily(self, stock_code: str, start_date: str, end_date: str,
                         max_retries: int = 3, retry_delay: float = 2.0) -> pd.DataFrame:
        """
        获取单只股票日线数据（含重试机制）
        
        Args:
            stock_code: 股票代码，如 '000001'
            start_date: 开始日期，格式 'YYYYMMDD'
            end_date: 结束日期，格式 'YYYYMMDD'
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"  # 前复权
                )
                if df.empty:
                    return df
                
                # 标准化列名
                df = df.rename(columns={
                    "日期": "date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "amount",
                    "涨跌幅": "pct_change",
                })
                df["date"] = pd.to_datetime(df["date"])
                df["stock_code"] = stock_code
                df = df.set_index(["date", "stock_code"]).sort_index()
                return df
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    print(f"\n获取 {stock_code} 数据失败(重试{max_retries}次): {e}")
                    return pd.DataFrame()
    
    def fetch_all_stocks(self, stock_codes: List[str], start_date: str, end_date: str,
                         save: bool = True) -> pd.DataFrame:
        """
        批量获取多只股票日线数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            save: 是否保存到文件
            
        Returns:
            合并后的DataFrame
        """
        all_data = []
        failed = []
        total = len(stock_codes)
        
        for i, code in enumerate(stock_codes):
            print(f"\r下载进度: {i+1}/{total} - {code}", end="", flush=True)
            df = self.fetch_stock_daily(code, start_date, end_date)
            if not df.empty:
                all_data.append(df)
            else:
                failed.append(code)
            # 限速：每次请求后暂停，避免被数据源封禁
            time.sleep(0.5)
        
        print()  # 换行
        print(f"成功: {len(all_data)}, 失败: {len(failed)}")
        if failed:
            print(f"失败股票: {failed[:10]}{'...' if len(failed) > 10 else ''}")
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.concat(all_data)
        
        if save:
            filepath = os.path.join(self.raw_dir, f"stock_daily_{start_date}_{end_date}.parquet")
            result.to_parquet(filepath)
            print(f"数据已保存至: {filepath}")
        
        return result
    
    def load_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        加载已存储的数据，若不存在则从网络获取
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame
        """
        filepath = os.path.join(self.raw_dir, f"stock_daily_{start_date}_{end_date}.parquet")
        
        if os.path.exists(filepath):
            print(f"从本地加载数据: {filepath}")
            return pd.read_parquet(filepath)
        
        print("本地数据不存在，开始从网络获取...")
        stocks_df = self.get_hs300_stocks()
        if stocks_df.empty:
            raise ValueError("无法获取沪深300成分股列表")
        
        stock_codes = stocks_df["品种代码"].tolist()
        return self.fetch_all_stocks(stock_codes, start_date, end_date, save=True)
    
    def prepare_panel_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备面板数据：计算收益率等基础字段
        
        Args:
            df: 原始日线数据
            
        Returns:
            包含收益率的面板数据
        """
        df = df.copy()
        
        # 计算日收益率
        df["daily_return"] = df.groupby(level="stock_code")["close"].pct_change()
        
        # 计算5日收益率（趋势）
        df["return_5d"] = df.groupby(level="stock_code")["close"].pct_change(5)
        
        # 计算1日收益率（反转）
        df["return_1d"] = df["daily_return"]
        
        # 计算因子值 = 5日收益 - 1日收益
        df["factor_value"] = df["return_5d"] - df["return_1d"]
        
        # 删除NaN行
        df = df.dropna(subset=["factor_value"])
        
        return df
