"""
ComplianceUnit类

合规单元是系统的基本组件，代表一个最小的可验证的法规单元。
每个ComplianceUnit包含subject、condition、constraint和可选的contextual_info。
"""

from typing import Dict, List, Any, Optional, Callable, Union
import inspect
import importlib.util
import sys
import json
from dataclasses import dataclass, field
import pandas as pd
from datetime import datetime


@dataclass
class ComplianceUnit:
    """
    合规单元（Compliance Unit）的数据类表示。
    
    每个CU代表一个独立的、可验证的合规要求。
    使用@dataclass可以自动生成__init__, __repr__, __eq__等方法。
    """
    cu_id: str
    regulation_id: str
    category: str
    source: str
    subject: Optional[str] = None
    condition: Optional[str] = None
    constraint: Optional[str] = None
    code: Optional[str] = None
    contextual_info: Optional[str] = None
    relation: Optional[str] = None
    target: Optional[str] = None
    
    # 注意: 旧的 execute, to_json, from_json, 和手写的 __init__ 方法已被移除，
    # 因为 @dataclass 和新的执行流程使其变得多余。

    def to_dict(self) -> Dict[str, Any]:
        """将数据类的实例转换为字典。"""
        # dataclasses.asdict(self) 也可以实现，但自定义可以确保顺序和格式
        return {
            "cu_id": self.cu_id,
            "regulation_id": self.regulation_id,
            "category": self.category,
            "source": self.source,
            "subject": self.subject,
            "condition": self.condition,
            "constraint": self.constraint,
            "code": self.code,
            "contextual_info": self.contextual_info,
            "relation": self.relation,
            "target": self.target,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceUnit":
        """从字典创建合规单元实例，对缺失的键提供默认值。"""
        # 获取dataclass所有已定义的字段
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        
        # 为确保兼容性，为新字段提供默认值
        data.setdefault("regulation_id", data.get("reg_id", "")) # 兼容旧的reg_id
        data.setdefault("category", "")
        data.setdefault("source", "")
        
        # 只使用字典中存在的、且为dataclass字段的键值对来创建实例
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)

    def __repr__(self):
        return f"ComplianceUnit(cu_id='{self.cu_id}')"

    # The `execute` method has been removed as it is obsolete.
    # The new sandbox execution is handled by RuleExecutor. 