"""
存储模块
支持多种数据库后端（基于SQLAlchemy）
"""
from pathlib import Path
from storage.sqlalchemy_storage import SQLAlchemyStorage, SQLALCHEMY_AVAILABLE
from storage.db_storage import SQLiteStorage  # 保留向后兼容

# 为了向后兼容，保留DatabaseStorage别名
DatabaseStorage = SQLiteStorage

__all__ = [
    'SQLAlchemyStorage',
    'SQLiteStorage',  # 向后兼容
    'DatabaseStorage',  # 向后兼容
    'SQLALCHEMY_AVAILABLE',
    'create_storage',
]


def create_storage(config: dict):
    """
    根据配置创建数据库存储实例（使用SQLAlchemy）
    
    Args:
        config: 数据库配置字典
        
    Returns:
        数据库存储实例
        
    Example:
        # SQLite配置
        config = {
            'type': 'sqlite',
            'db_path': '/path/to/database.db'
        }
        
        # MySQL配置（使用pymysql驱动）
        config = {
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'password',
            'database': 'cve_db',
            'driver': 'pymysql'  # 可选：'pymysql' 或 'mysqlconnector'
        }
        
        # 直接使用数据库URL
        config = {
            'type': 'sqlalchemy',
            'url': 'mysql+pymysql://user:password@localhost:3306/cve_db'
        }
    """
    if not SQLALCHEMY_AVAILABLE:
        raise ImportError(
            "SQLAlchemy支持需要安装sqlalchemy库。请运行: pip install sqlalchemy"
        )
    
    db_type = config.get('type', 'sqlite').lower()
    
    if db_type == 'sqlalchemy':
        # 直接使用数据库URL
        database_url = config.get('url')
        if not database_url:
            raise ValueError("SQLAlchemy配置需要提供 'url'")
        return SQLAlchemyStorage(database_url, echo=config.get('echo', False))
    
    elif db_type == 'sqlite':
        # SQLite配置
        db_path = config.get('db_path')
        if not db_path:
            raise ValueError("SQLite配置需要提供 'db_path'")
        
        # 转换为SQLAlchemy URL
        if isinstance(db_path, Path):
            db_path = str(db_path)
        database_url = f'sqlite:///{db_path}'
        return SQLAlchemyStorage(database_url, echo=config.get('echo', False))
    
    elif db_type == 'mysql':
        # MySQL配置
        required_keys = ['host', 'user', 'password', 'database']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"MySQL配置需要提供 '{key}'")
        
        host = config['host']
        port = config.get('port', 3306)
        user = config['user']
        password = config['password']
        database = config['database']
        driver = config.get('driver', 'pymysql')  # 默认使用pymysql
        
        # 构建SQLAlchemy URL
        if driver == 'mysqlconnector':
            database_url = f'mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}'
        else:  # pymysql
            database_url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'
        
        create_db = config.get('create_database', True)  # 默认自动创建数据库
        return SQLAlchemyStorage(database_url, echo=config.get('echo', False), create_database=create_db)
    
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")
