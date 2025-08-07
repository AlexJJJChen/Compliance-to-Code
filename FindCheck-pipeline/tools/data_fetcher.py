#!/usr/bin/env python3
"""
数据获取工具

从公司数据库中提取特定公司在给定时间范围内的数据。
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)


class DataFetcher:
    """
    数据获取工具类
    
    从公司数据库中提取特定公司在给定时间范围内的数据。
    """
    
    def __init__(self, data_dir: str = "data/company_data"):
        """
        初始化数据获取工具
        
        参数:
            data_dir: 存放公司数据的目录
        """
        self.data_dir = os.path.join(project_root, data_dir)
        self.data_files = self._get_data_files()
        
    def _get_data_files(self) -> Dict[str, str]:
        """
        获取所有可用的数据文件
        
        返回:
            键为法规ID，值为对应数据文件路径的字典
        """
        data_files = {}
        
        # 可以根据文件名匹配法规
        regulation_mapping = {
            "股份回购": "regulation_04",
            "持股管理": "regulation_08",
            "权益分派": "regulation_10"
        }
        
        # 扫描数据目录
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                file_path = os.path.join(self.data_dir, filename)
                if os.path.isfile(file_path) and filename.endswith(".csv"):
                    # 根据文件名判断所属法规
                    for key, value in regulation_mapping.items():
                        if key in filename:
                            data_files[value] = file_path
                            break
        
        return data_files
    
    def get_company_data(self, 
                         company_name: str, 
                         regulation_id: str,
                         start_date: Optional[Union[str, datetime]] = None,
                         end_date: Optional[Union[str, datetime]] = None) -> Tuple[Optional[pd.DataFrame], Tuple[Optional[str], Optional[str]]]:
        """
        获取特定公司在给定时间范围内的数据, 并返回实际使用的数据范围。
        
        参数:
            company_name: 公司名称
            regulation_id: 法规ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        返回:
            一个元组 (公司数据DataFrame, (实际开始日期, 实际结束日期))
        """
        # 获取对应法规的数据文件
        data_file = self.data_files.get(regulation_id)
        if not data_file:
            print(f"未找到法规 {regulation_id} 的数据文件")
            return None, (None, None)
        
        try:
            # 读取数据文件
            print(f"正在读取数据文件: {data_file}")
            df = pd.read_csv(data_file, low_memory=False)
            
            # 过滤出指定公司的数据
            company_df = df[df["公司简称"] == company_name]
            
            if len(company_df) == 0:
                print(f"未找到公司 {company_name} 的数据")
                return None, (None, None)
                
            print(f"找到 {company_name} 的 {len(company_df)} 条记录")
            
            # 初始化实际日期范围
            actual_start, actual_end = None, None

            # 如果有日期列并且指定了日期范围，过滤日期
            if "日期" in company_df.columns:
                # 确保日期列是datetime类型
                company_df["日期"] = pd.to_datetime(company_df["日期"], errors="coerce")
                
                # 获取过滤前的日期范围
                valid_dates = company_df["日期"].dropna()
                if not valid_dates.empty:
                    actual_start = valid_dates.min().strftime('%Y-%m-%d')
                    actual_end = valid_dates.max().strftime('%Y-%m-%d')

                # 过滤日期范围
                if start_date:
                    start_date = pd.to_datetime(start_date)
                    company_df = company_df[company_df["日期"] >= start_date]
                
                if end_date:
                    end_date = pd.to_datetime(end_date)
                    company_df = company_df[company_df["日期"] <= end_date]
                
                # 获取过滤后的日期范围
                final_dates = company_df["日期"].dropna()
                if not final_dates.empty:
                    actual_start = final_dates.min().strftime('%Y-%m-%d')
                    actual_end = final_dates.max().strftime('%Y-%m-%d')

                print(f"筛选后的数据: {len(company_df)} 条记录")
            
            return company_df, (actual_start, actual_end)
        
        except Exception as e:
            print(f"读取数据文件时出错: {e}")
            return None, (None, None)
    
    def get_available_companies(self, regulation_id: str) -> List[str]:
        """
        获取特定法规下的所有可用公司
        
        参数:
            regulation_id: 法规ID
            
        返回:
            可用公司名称列表
        """
        # 获取对应法规的数据文件
        data_file = self.data_files.get(regulation_id)
        if not data_file:
            print(f"未找到法规 {regulation_id} 的数据文件")
            return []
        
        try:
            # 读取数据文件，只取公司简称列
            df = pd.read_csv(data_file, usecols=["公司简称"])
            companies = df["公司简称"].unique().tolist()
            return companies
        
        except Exception as e:
            print(f"获取可用公司列表时出错: {e}")
            return []
    
    def get_available_shareholders(self, regulation_id: str, company_name: str) -> List[str]:
        """
        获取特定法规和公司下的所有可用股东
        目前仅支持regulation_08法规
        
        参数:
            regulation_id: 法规ID
            company_name: 公司名称
            
        返回:
            可用股东名称列表
        """
        if regulation_id != "regulation_08":
            return []
            
        # 获取对应法规的数据文件
        data_file = self.data_files.get(regulation_id)
        if not data_file:
            print(f"未找到法规 {regulation_id} 的数据文件")
            return []
        
        try:
            # 读取数据文件，只取公司简称和股东列
            df = pd.read_csv(data_file, usecols=["公司简称", "股东"])
            # 过滤出特定公司的数据
            company_df = df[df["公司简称"] == company_name]
            
            if len(company_df) == 0:
                print(f"未找到公司 {company_name} 的数据")
                return []
                
            # 获取不重复的股东列表
            shareholders = company_df["股东"].dropna().unique().tolist()
            return shareholders
        
        except Exception as e:
            print(f"获取可用股东列表时出错: {e}")
            return []
    
    def get_date_range(self, regulation_id: str, company_name: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取特定公司数据的日期范围
        
        参数:
            regulation_id: 法规ID
            company_name: 公司名称
            
        返回:
            (最早日期, 最晚日期)元组，如果未找到则返回(None, None)
        """
        company_data = self.get_company_data(company_name, regulation_id)
        if company_data is None or len(company_data) == 0 or "日期" not in company_data.columns:
            return None, None
        
        company_data["日期"] = pd.to_datetime(company_data["日期"], errors="coerce")
        dates = company_data["日期"].dropna()
        
        if len(dates) == 0:
            return None, None
            
        return dates.min(), dates.max()


if __name__ == "__main__":
    # 测试代码
    fetcher = DataFetcher()
    
    # 显示可用的数据文件
    print("可用的数据文件:")
    for reg_id, file_path in fetcher.data_files.items():
        print(f"  - {reg_id}: {os.path.basename(file_path)}")
    
    # 指定法规的可用公司
    regulation_id = "regulation_04"  # 股份回购
    companies = fetcher.get_available_companies(regulation_id)
    print(f"\n法规 {regulation_id} 下的可用公司: {len(companies)}")
    if len(companies) > 5:
        print(f"前5个公司: {companies[:5]}")
    else:
        print(f"所有公司: {companies}")
    
    # 如果可用公司不为空，测试获取第一个公司的数据
    if companies:
        company_name = companies[0]
        start_date = "2022-01-01"
        end_date = "2023-12-31"
        print(f"\n获取公司 {company_name} 在 {start_date} 到 {end_date} 期间的数据")
        
        data = fetcher.get_company_data(company_name, regulation_id, start_date, end_date)
        if data is not None:
            print(f"数据形状: {data.shape}")
            print(f"数据列: {data.columns.tolist()}")
            print(f"第一条记录:\n{data.iloc[0]}")
            
            # 查看日期范围
            min_date, max_date = fetcher.get_date_range(regulation_id, company_name)
            print(f"\n数据日期范围: {min_date} 到 {max_date}") 