"""
CompanyDataDB 模块

提供企业数据库接口，用于加载和管理企业合规相关数据。
"""

import os
import pandas as pd
from typing import Dict, List, Any, Optional, Union
import json


class CompanyDataDB:
    """
    企业数据库，提供企业数据的加载和管理功能。
    
    属性:
        data_cache: 存储已加载数据的缓存，键为数据源标识
    """
    
    def __init__(self):
        """初始化企业数据库"""
        self.data_cache: Dict[str, pd.DataFrame] = {}
    
    def load_data(self, data_source: str) -> pd.DataFrame:
        """
        加载企业数据。
        
        参数:
            data_source: 数据源，可以是CSV文件路径或其他标识
            
        返回:
            加载的数据DataFrame
        """
        # 检查缓存
        if data_source in self.data_cache:
            return self.data_cache[data_source]
        
        # 加载新数据
        try:
            if os.path.exists(data_source):
                # 从文件加载
                if data_source.endswith('.csv'):
                    df = pd.read_csv(data_source)
                elif data_source.endswith('.xlsx') or data_source.endswith('.xls'):
                    df = pd.read_excel(data_source)
                else:
                    raise ValueError(f"不支持的文件格式: {data_source}")
            else:
                # 假定是数据库表或其他标识
                # 在实际应用中，这里可以实现数据库连接逻辑
                raise ValueError(f"无法识别的数据源: {data_source}")
            
            # 存入缓存
            self.data_cache[data_source] = df
            
            return df
            
        except Exception as e:
            raise ValueError(f"加载数据失败 ({data_source}): {e}")
    
    def filter_by_company(self, df: pd.DataFrame, company_name: str) -> pd.DataFrame:
        """
        按公司名称过滤数据。
        
        参数:
            df: 原始数据
            company_name: 公司名称
            
        返回:
            过滤后的数据
        """
        # 假设有一个公司名称列
        company_columns = ['公司简称', '公司名称', 'company_name', '企业名称', '企业简称']
        
        for col in company_columns:
            if col in df.columns:
                return df[df[col] == company_name]
        
        # 如果没有找到公司列
        raise ValueError(f"数据中未找到公司名称列，无法按 {company_name} 过滤")
    
    def preprocess_data(self, df: pd.DataFrame, regulation_id: str) -> pd.DataFrame:
        """
        根据特定法规预处理数据。
        
        参数:
            df: 原始数据
            regulation_id: 法规ID
            
        返回:
            预处理后的数据
        """
        # 根据不同的法规进行特定处理
        if regulation_id == "regulation_04":
            return self._preprocess_regulation_04(df)
        elif regulation_id == "regulation_08":
            return self._preprocess_regulation_08(df)
        elif regulation_id == "regulation_10":
            return self._preprocess_regulation_10(df)
        else:
            # 默认处理
            return df
    
    def _preprocess_regulation_04(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理股份回购法规（04号）的数据。
        
        参数:
            df: 原始数据
            
        返回:
            处理后的数据
        """
        # 复制数据以避免修改原始数据
        processed_df = df.copy()
        
        # 1. 日期列转换
        date_columns = [
            '日期', '决议通过日', '实施开始日', '实施截止日', '上市日期', 
            '公告日期', '出售计划披露日', '出售开始日', '出售截止日'
        ]
        
        for col in date_columns:
            if col in processed_df.columns:
                processed_df[col] = pd.to_datetime(processed_df[col], errors='coerce')
        
        # 2. 数值列处理
        numeric_columns = [
            '收盘价', '总股本', '回购数量上限', '回购数量下限', '资金总额上限',
            '资金总额下限', '要约价格', '申报价格', '当日回购数量', '累计回购数量',
            '已使用资金', '日收益率', '前收盘价', '发行价格', '复权因子', '成交量'
        ]
        
        for col in numeric_columns:
            if col in processed_df.columns:
                processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')
        
        # 3. 布尔列处理
        bool_columns = ['存在回购方案', '存在出售计划', '披露出售进展']
        
        for col in bool_columns:
            if col in processed_df.columns:
                # 尝试将各种表示转换为布尔值
                processed_df[col] = processed_df[col].map({
                    True: True, 'True': True, 'true': True, '是': True, '1': True, 1: True,
                    False: False, 'False': False, 'false': False, '否': False, '0': False, 0: False
                }).fillna(False)
        
        return processed_df
    
    def _preprocess_regulation_08(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理股份减持和持股管理法规（08号）的数据。
        
        参数:
            df: 原始数据
            
        返回:
            处理后的数据
        """
        # 此处添加特定于08号法规的处理逻辑
        # 目前仅返回原始数据
        return df
    
    def _preprocess_regulation_10(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理权益分派法规（10号）的数据。
        
        参数:
            df: 原始数据
            
        返回:
            处理后的数据
        """
        # 此处添加特定于10号法规的处理逻辑
        # 目前仅返回原始数据
        return df
    
    def save_data(self, df: pd.DataFrame, output_path: str) -> None:
        """
        保存数据到文件。
        
        参数:
            df: 要保存的数据
            output_path: 输出文件路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 根据文件扩展名保存
        if output_path.endswith('.csv'):
            df.to_csv(output_path, index=False)
        elif output_path.endswith('.xlsx') or output_path.endswith('.xls'):
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"不支持的文件格式: {output_path}")
    
    def get_company_list(self, data_source: str) -> List[str]:
        """
        获取数据源中的公司列表。
        
        参数:
            data_source: 数据源
            
        返回:
            公司名称列表
        """
        try:
            df = self.load_data(data_source)
            
            # 尝试找到公司名称列
            company_columns = ['公司简称', '公司名称', 'company_name', '企业名称', '企业简称']
            
            for col in company_columns:
                if col in df.columns:
                    return df[col].dropna().unique().tolist()
            
            # 如果找不到合适的列
            raise ValueError("数据中未找到公司名称列")
            
        except Exception as e:
            raise ValueError(f"获取公司列表失败: {e}")
    
    def clear_cache(self) -> None:
        """清空数据缓存"""
        self.data_cache.clear() 