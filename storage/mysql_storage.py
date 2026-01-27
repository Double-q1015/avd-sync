"""
MySQL数据库存储模块
使用 mysql-connector-python (官方MySQL连接器)
"""
import logging
from typing import List, Optional, Dict
from contextlib import contextmanager
from datetime import datetime

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import mysql.connector
    from mysql.connector import Error
    from mysql.connector.cursor import MySQLCursorDict
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    mysql = None
    Error = None
    MySQLCursorDict = None

from models.cve import CVEModel
from storage.base_storage import BaseStorage

logger = logging.getLogger(__name__)


class MySQLStorage(BaseStorage):
    """MySQL数据库存储类"""
    
    def __init__(self, host: str, port: int, user: str, password: str, 
                 database: str, charset: str = 'utf8mb4'):
        """
        初始化MySQL数据库存储
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
        """
        if not MYSQL_AVAILABLE:
            raise ImportError(
                "MySQL支持需要安装mysql-connector-python库。请运行: pip install mysql-connector-python"
            )
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            autocommit=False
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn.is_connected():
                conn.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # 创建CVE表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cve_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cve VARCHAR(20) UNIQUE NOT NULL,
                    title TEXT,
                    product TEXT,
                    danger_level VARCHAR(50),
                    description TEXT,
                    impact_range TEXT,
                    security_versions TEXT,
                    solution_advice TEXT,
                    reference_links TEXT,
                    exploitability VARCHAR(50),
                    package VARCHAR(50),
                    publish_date VARCHAR(20),
                    cwe VARCHAR(20),
                    score VARCHAR(20),
                    crawl_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_cve (cve),
                    INDEX idx_publish_date (publish_date),
                    INDEX idx_crawl_date (crawl_date),
                    INDEX idx_danger_level (danger_level)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建爬取统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    crawl_date DATE UNIQUE NOT NULL,
                    total_cves INT DEFAULT 0,
                    new_cves INT DEFAULT 0,
                    updated_cves INT DEFAULT 0,
                    crawl_mode VARCHAR(20) DEFAULT 'incremental',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建全量爬取历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS full_crawl_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    crawl_date DATE UNIQUE NOT NULL,
                    total_cves INT DEFAULT 0,
                    duration_seconds INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_full_crawl_date (crawl_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 数据库迁移：检查并添加缺失的列
            self._migrate_database(cursor)
            
            conn.commit()
            cursor.close()
            logger.info("MySQL数据库初始化完成")
    
    def _migrate_database(self, cursor):
        """
        数据库迁移：检查并添加缺失的列
        
        Args:
            cursor: 数据库游标
        """
        try:
            # 检查 crawl_stats 表是否存在 crawl_mode 列
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'crawl_stats' 
                AND COLUMN_NAME = 'crawl_mode'
            """, (self.database,))
            
            if cursor.fetchone() is None:
                logger.info("检测到旧版数据库，正在添加 crawl_mode 列...")
                cursor.execute('ALTER TABLE crawl_stats ADD COLUMN crawl_mode VARCHAR(20) DEFAULT "incremental"')
                logger.info("成功添加 crawl_mode 列")
            else:
                logger.debug("数据库表结构已是最新版本")
        except Exception as e:
            logger.warning(f"数据库迁移检查失败: {e}")
        finally:
            cursor.close()
    
    def insert_or_update_cve(self, cve_model: CVEModel) -> bool:
        """插入或更新CVE记录"""
        data = cve_model.to_dict()
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            try:
                # 检查CVE是否已存在
                cursor.execute('SELECT cve FROM cve_records WHERE cve = %s', (data['cve'],))
                exists = cursor.fetchone() is not None
                
                if exists:
                    # 更新记录
                    cursor.execute('''
                        UPDATE cve_records SET
                            title = %s, product = %s, danger_level = %s,
                            description = %s, impact_range = %s, security_versions = %s,
                            solution_advice = %s, reference_links = %s,
                            exploitability = %s, package = %s, publish_date = %s,
                            cwe = %s, score = %s, crawl_date = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE cve = %s
                    ''', (
                        data['title'], data['product'], data['danger_level'],
                        data['description'], data['impact_range'], data['security_versions'],
                        data['solution_advice'], data['reference_links'],
                        data['exploitability'], data['package'], data['publish_date'],
                        data['cwe'], data['score'], data['crawl_date'],
                        data['cve']
                    ))
                    return False
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO cve_records (
                            cve, title, product, danger_level, description,
                            impact_range, security_versions, solution_advice,
                            reference_links, exploitability, package, publish_date,
                            cwe, score, crawl_date
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        data['cve'], data['title'], data['product'], data['danger_level'],
                        data['description'], data['impact_range'], data['security_versions'],
                        data['solution_advice'], data['reference_links'],
                        data['exploitability'], data['package'], data['publish_date'],
                        data['cwe'], data['score'], data['crawl_date']
                    ))
                    return True
            finally:
                cursor.close()
    
    def batch_insert_or_update(self, cve_models: List[CVEModel]) -> Dict[str, int]:
        """批量插入或更新CVE记录"""
        stats = {'new': 0, 'updated': 0, 'failed': 0}
        
        for cve_model in cve_models:
            try:
                is_new = self.insert_or_update_cve(cve_model)
                if is_new:
                    stats['new'] += 1
                else:
                    stats['updated'] += 1
            except Exception as e:
                logger.error(f"插入/更新CVE {cve_model.cve} 失败: {e}")
                stats['failed'] += 1
        
        return stats
    
    def get_cve(self, cve_id: str) -> Optional[CVEModel]:
        """根据CVE ID获取记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute('SELECT * FROM cve_records WHERE cve = %s', (cve_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_model(row)
                return None
            finally:
                cursor.close()
    
    def get_all_cves(self, limit: Optional[int] = None, offset: int = 0) -> List[CVEModel]:
        """获取所有CVE记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                if limit:
                    cursor.execute(
                        'SELECT * FROM cve_records ORDER BY publish_date DESC LIMIT %s OFFSET %s',
                        (limit, offset)
                    )
                else:
                    cursor.execute('SELECT * FROM cve_records ORDER BY publish_date DESC')
                
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
            finally:
                cursor.close()
    
    def get_cve_count(self) -> int:
        """获取CVE总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute('SELECT COUNT(*) as count FROM cve_records')
                result = cursor.fetchone()
                return result['count'] if result else 0
            finally:
                cursor.close()
    
    def _row_to_model(self, row: dict) -> CVEModel:
        """将数据库行转换为CVE模型"""
        ref_links = row.get('reference_links', '')
        if ref_links:
            ref_links = [link for link in ref_links.split(',') if link]
        else:
            ref_links = []
        
        data = {
            'cve': row['cve'],
            'title': row.get('title', 'N/A'),
            'product': row.get('product', 'N/A'),
            'danger_level': row.get('danger_level', 'N/A'),
            'description': row.get('description', 'N/A'),
            'impact_range': row.get('impact_range', 'N/A'),
            'security_versions': row.get('security_versions', 'N/A'),
            'solution_advice': row.get('solution_advice'),
            'reference_links': ref_links,
            'exploitability': row.get('exploitability', 'N/A'),
            'package': row.get('package', 'N/A'),
            'publish_date': row.get('publish_date', 'N/A'),
            'cwe': row.get('cwe'),
            'score': row.get('score'),
            'crawl_date': row.get('crawl_date'),
        }
        return CVEModel.from_dict(data)
    
    def update_crawl_stats(self, date: str, new_count: int, updated_count: int, crawl_mode: str = 'incremental'):
        """更新爬取统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                total = new_count + updated_count
                
                cursor.execute('''
                    INSERT INTO crawl_stats (crawl_date, total_cves, new_cves, updated_cves, crawl_mode)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_cves = VALUES(total_cves),
                        new_cves = VALUES(new_cves),
                        updated_cves = VALUES(updated_cves),
                        crawl_mode = VALUES(crawl_mode)
                ''', (date, total, new_count, updated_count, crawl_mode))
            finally:
                cursor.close()
    
    def get_latest_publish_date(self) -> Optional[str]:
        """获取数据库中最新CVE的发布日期"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute('''
                    SELECT MAX(publish_date) as max_date
                    FROM cve_records 
                    WHERE publish_date != "N/A" 
                    AND publish_date REGEXP "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
                ''')
                result = cursor.fetchone()
                return result['max_date'] if result and result['max_date'] else None
            finally:
                cursor.close()
    
    def get_last_full_crawl_date(self) -> Optional[str]:
        """获取最后一次全量爬取的日期"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute('SELECT MAX(crawl_date) as max_date FROM full_crawl_history')
                result = cursor.fetchone()
                return result['max_date'] if result and result['max_date'] else None
            finally:
                cursor.close()
    
    def record_full_crawl(self, date: str, total_cves: int, duration_seconds: int):
        """记录全量爬取历史"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute('''
                    INSERT INTO full_crawl_history (crawl_date, total_cves, duration_seconds)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_cves = VALUES(total_cves),
                        duration_seconds = VALUES(duration_seconds)
                ''', (date, total_cves, duration_seconds))
            finally:
                cursor.close()
    
    def should_run_full_crawl(self, interval_days: int = 30) -> bool:
        """判断是否应该执行全量爬取"""
        from datetime import datetime, timedelta
        
        last_full_crawl = self.get_last_full_crawl_date()
        if not last_full_crawl:
            return True
        
        try:
            if isinstance(last_full_crawl, str):
                last_date = datetime.strptime(last_full_crawl, '%Y-%m-%d')
            else:
                last_date = last_full_crawl
            days_since = (datetime.now() - last_date).days
            return days_since >= interval_days
        except (ValueError, TypeError):
            return True
    
    def optimize_database(self):
        """优化数据库（MySQL使用OPTIMIZE TABLE）"""
        logger.info("开始优化MySQL数据库...")
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute('OPTIMIZE TABLE cve_records, crawl_stats, full_crawl_history')
            finally:
                cursor.close()
        logger.info("MySQL数据库优化完成")

