"""
时区处理工具函数模块

用于统一项目中的时区处理，避免timezone-aware和timezone-naive datetime混用导致的错误。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """
    获取当前UTC时间，返回timezone-aware对象
    
    替代 datetime.utcnow() 使用，确保返回timezone-aware的datetime对象
    
    Returns:
        datetime: 当前UTC时间，包含时区信息
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    确保datetime对象是UTC时区的timezone-aware对象
    
    Args:
        dt: 可能为None的datetime对象
        
    Returns:
        Optional[datetime]: UTC时区的timezone-aware对象，如果输入为None则返回None
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # 假设naive datetime是UTC时间，添加时区信息
        logger.debug(f"Converting naive datetime {dt} to UTC timezone-aware")
        return dt.replace(tzinfo=timezone.utc)
    
    # 如果已经是timezone-aware，转换到UTC
    if dt.tzinfo != timezone.utc:
        logger.debug(f"Converting timezone-aware datetime {dt} to UTC")
        return dt.astimezone(timezone.utc)
    
    return dt


def safe_datetime_diff(dt1: Optional[datetime], dt2: Optional[datetime]) -> Optional[timedelta]:
    """
    安全计算两个datetime的差值
    
    确保两个datetime都是timezone-aware对象后再进行运算，避免时区混用错误
    
    Args:
        dt1: 第一个datetime对象
        dt2: 第二个datetime对象
        
    Returns:
        Optional[timedelta]: 时间差，如果任一输入为None则返回None
    """
    if dt1 is None or dt2 is None:
        return None
    
    utc_dt1 = ensure_utc(dt1)
    utc_dt2 = ensure_utc(dt2)
    
    if utc_dt1 is None or utc_dt2 is None:
        return None
    
    try:
        diff = utc_dt1 - utc_dt2
        logger.debug(f"Calculated time difference: {diff} between {utc_dt1} and {utc_dt2}")
        return diff
    except Exception as e:
        logger.error(f"Error calculating datetime difference: {e}")
        logger.error(f"dt1: {utc_dt1} (type: {type(utc_dt1)}, tzinfo: {utc_dt1.tzinfo})")
        logger.error(f"dt2: {utc_dt2} (type: {type(utc_dt2)}, tzinfo: {utc_dt2.tzinfo})")
        raise


def is_timezone_aware(dt: Optional[datetime]) -> bool:
    """
    检查datetime对象是否包含时区信息
    
    Args:
        dt: datetime对象
        
    Returns:
        bool: 如果包含时区信息返回True，否则返回False
    """
    if dt is None:
        return False
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def format_datetime_for_api(dt: Optional[datetime]) -> Optional[str]:
    """
    将datetime对象格式化为API返回格式
    
    确保返回标准的ISO格式字符串
    
    Args:
        dt: datetime对象
        
    Returns:
        Optional[str]: ISO格式的时间字符串，如果输入为None则返回None
    """
    if dt is None:
        return None
    
    # 确保是timezone-aware
    utc_dt = ensure_utc(dt)
    if utc_dt is None:
        return None
    
    return utc_dt.isoformat()