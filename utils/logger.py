"""
日志工具模块
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from config.settings import LOG_CONFIG


def setup_logger(name: str = 'avd_sync', log_level: str = None) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别，如果为None则使用配置中的级别
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    level = log_level or LOG_CONFIG['log_level']
    logger.setLevel(getattr(logging, level.upper()))
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（带轮转）
    log_file = LOG_CONFIG['log_dir'] / LOG_CONFIG['log_file']
    # 确保日志目录存在且有写权限
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_CONFIG['max_bytes'],
            backupCount=LOG_CONFIG['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # 如果无法写入日志文件，只使用控制台输出
        logger.warning(f"无法创建日志文件 {log_file}: {e}，将只使用控制台输出")
    
    return logger

