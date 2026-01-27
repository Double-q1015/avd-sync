"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 爬虫配置
CRAWLER_CONFIG = {
    'cve_vuln_url': 'https://avd.aliyun.com/nvd/list?page=',
    'cve_detail_url': 'https://avd.aliyun.com/detail?id=',
    'start_page': 1,  # 起始页码
    'request_delay': 0.1,  # 请求延迟（秒）
    'max_retries': 3,  # 最大重试次数
    'retry_delay': 5,  # 重试延迟（秒）
    # 增量爬取配置
    'incremental': {
        'enabled': True,  # 是否启用增量爬取
        'lookback_days': 7,  # 向前回溯天数（防止遗漏）
    },
    # 全量爬取配置
    'full_crawl': {
        'enabled': True,  # 是否启用全量爬取
        'interval_days': 30,  # 全量爬取间隔（天）
    },
}

# 浏览器配置
BROWSER_CONFIG = {
    'headless': os.getenv('HEADLESS', 'False').lower() == 'true',  # 是否无头模式（Docker中建议True）
    'no_sandbox': True,  # 关闭沙箱模式（Docker中必须）
    'user_agent': None,  # 自定义User-Agent
    'timeout': int(os.getenv('BROWSER_TIMEOUT', '30')),  # 页面加载超时（秒）
}

# 数据库配置
# 支持数据库类型：'sqlite' 或 'mysql'（基于SQLAlchemy）
DATABASE_CONFIG = {
    'type': os.getenv('DB_TYPE', 'sqlite'),  # 'sqlite' 或 'mysql'
    
    # SQLite配置（当type='sqlite'时使用）
    'db_path': BASE_DIR / 'data' / 'cve_database.db',
    'backup_path': BASE_DIR / 'data' / 'backups',
    
    # MySQL配置（当type='mysql'时使用）
    'mysql': {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', 'root'),
        'database': os.getenv('MYSQL_DATABASE', 'cve_db'),
        'driver': os.getenv('MYSQL_DRIVER', 'pymysql'),  # 'pymysql' 或 'mysqlconnector'
    },
    
    # SQLAlchemy配置
    'echo': os.getenv('DB_ECHO', 'False').lower() == 'true',  # 是否打印SQL语句（调试用）
}

# 日志配置
LOG_CONFIG = {
    'log_dir': BASE_DIR / 'logs',
    'log_file': 'crawler.log',
    'log_level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# GitHub Release 配置
GITHUB_CONFIG = {
    'repo_owner': '',  # 需要设置
    'repo_name': '',  # 需要设置
    'release_tag_prefix': 'v',  # release标签前缀
    'db_filename': 'cve_database.db',  # 发布的数据库文件名
}

# 确保必要的目录存在
for path in [DATABASE_CONFIG['db_path'].parent, LOG_CONFIG['log_dir'], DATABASE_CONFIG['backup_path']]:
    path.mkdir(parents=True, exist_ok=True)

