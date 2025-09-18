import pandas as pd
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseDataPreprocessor(ABC):
    """
    数据预处理器的抽象基类。

    所有针对特定法规的预处理器都应继承此类，并实现`preprocess`方法。
    """

    @abstractmethod
    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对原始DataFrame进行预处理。

        参数:
            df: 从数据源加载的原始DataFrame。

        返回:
            经过预处理的DataFrame。
        """
        pass

class Regulation04Preprocessor(BaseDataPreprocessor):
    """针对 'regulation_04' 法规的预处理器。"""

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为'regulation_04'法规转换日期列。

        - 将指定的列转换为不带时区的datetime对象。
        - 对无法转换的日期值，会将其设置为NaT（Not a Time）。
        """
        logger.debug("应用Regulation04Preprocessor：开始转换日期列。")
        df_processed = df.copy()

        date_columns = [
            '日期', '决议通过日', '实施开始日', '实施截止日', 
            '上市日期', '公告日期', '出售开始日', '出售截止日',
            '出售计划披露日' # 根据日志中的错误补充此列
        ]

        for col in date_columns:
            if col in df_processed.columns:
                try:
                    df_processed[col] = pd.to_datetime(df_processed[col], errors='coerce')
                    logger.debug(f"已将列 '{col}' 转换为datetime类型。")
                except Exception as e:
                    logger.error(f"在转换列 '{col}' 时发生错误: {e}")
            else:
                logger.warning(f"预期的日期列 '{col}' 在数据中未找到，跳过处理。")

        return df_processed

# --- 预处理器注册表 ---
# 将法规ID映射到其对应的预处理器类。
# 如需为新法规添加预处理器，只需在此处注册即可。
PREPROCESSOR_REGISTRY = {
    'regulation_04': Regulation04Preprocessor,
}

def get_preprocessor(regulation_id: str) -> BaseDataPreprocessor | None:
    """
    预处理器工厂函数。

    根据给定的法规ID，查找并返回一个预处理器实例。

    参数:
        regulation_id: 法规的唯一标识符。

    返回:
        如果找到，则返回一个BaseDataPreprocessor的实例；否则返回None。
    """
    preprocessor_class = PREPROCESSOR_REGISTRY.get(regulation_id)
    if preprocessor_class:
        logger.info(f"已为法规 '{regulation_id}' 找到数据预处理器: {preprocessor_class.__name__}")
        return preprocessor_class()
    
    logger.warning(f"未找到法规 '{regulation_id}' 的特定数据预处理器。将使用原始数据。")
    return None 