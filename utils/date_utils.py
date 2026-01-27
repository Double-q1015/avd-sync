"""
日期工具模块
"""
import time
from datetime import datetime
from typing import Optional


def is_date_before(date1: str, date2: str) -> bool:
    """
    判断date1是否早于date2
    
    Args:
        date1: 日期字符串，格式为 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
        date2: 日期字符串，格式为 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
        
    Returns:
        如果date1早于date2返回True，否则返回False
    """
    try:
        # 提取日期部分（去掉时间部分）
        date1_clean = date1.split(' ')[0]
        date2_clean = date2.split(' ')[0]
        
        date1_obj = time.strptime(date1_clean, "%Y-%m-%d")
        date2_obj = time.strptime(date2_clean, "%Y-%m-%d")
        
        return date1_obj < date2_obj
    except ValueError as e:
        raise ValueError(f"日期格式错误: {e}")


def parse_date(date_str: str) -> Optional[datetime]:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
        
    Returns:
        datetime对象，如果解析失败返回None
    """
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def format_date(date: datetime, format_str: str = "%Y-%m-%d") -> str:
    """
    格式化日期
    
    Args:
        date: datetime对象
        format_str: 格式字符串
        
    Returns:
        格式化后的日期字符串
    """
    return date.strftime(format_str)


def get_current_date() -> str:
    """获取当前日期字符串（YYYY-MM-DD）"""
    return datetime.now().strftime("%Y-%m-%d")

