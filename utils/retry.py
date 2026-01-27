"""
重试装饰器
"""
import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间倍数
        exceptions: 需要重试的异常类型
        
    Example:
        @retry(max_retries=3, delay=2.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}. "
                            f"{current_delay}秒后重试..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 在 {max_retries + 1} 次尝试后仍然失败")
            
            raise last_exception
        return wrapper
    return decorator

