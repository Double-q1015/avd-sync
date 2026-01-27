"""
SQLite数据库存储模块
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from contextlib import contextmanager
from datetime import datetime

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.cve import CVEModel
from storage.base_storage import BaseStorage

logger = logging.getLogger(__name__)


class SQLiteStorage(BaseStorage):
    """SQLite数据库存储类（向后兼容：DatabaseStorage别名）"""
    
    def __init__(self, db_path: Path):
        """
        初始化数据库存储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建CVE表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cve_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cve TEXT UNIQUE NOT NULL,
                    title TEXT,
                    product TEXT,
                    danger_level TEXT,
                    description TEXT,
                    impact_range TEXT,
                    security_versions TEXT,
                    solution_advice TEXT,
                    reference_links TEXT,
                    exploitability TEXT,
                    package TEXT,
                    publish_date TEXT,
                    cwe TEXT,
                    score TEXT,
                    crawl_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cve ON cve_records(cve)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_date ON cve_records(publish_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_crawl_date ON cve_records(crawl_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_danger_level ON cve_records(danger_level)')
            
            # 创建爬取统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_date DATE UNIQUE NOT NULL,
                    total_cves INTEGER DEFAULT 0,
                    new_cves INTEGER DEFAULT 0,
                    updated_cves INTEGER DEFAULT 0,
                    crawl_mode TEXT DEFAULT 'incremental',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建全量爬取历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS full_crawl_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_date DATE UNIQUE NOT NULL,
                    total_cves INTEGER DEFAULT 0,
                    duration_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_full_crawl_date ON full_crawl_history(crawl_date)')
            
            # 数据库迁移：检查并添加缺失的列
            self._migrate_database(cursor)
            
            conn.commit()
            logger.info("数据库初始化完成")
    
    def insert_or_update_cve(self, cve_model: CVEModel) -> bool:
        """
        插入或更新CVE记录
        
        Args:
            cve_model: CVE数据模型
            
        Returns:
            True表示新插入，False表示更新
        """
        data = cve_model.to_dict()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查CVE是否已存在
            cursor.execute('SELECT cve FROM cve_records WHERE cve = ?', (data['cve'],))
            exists = cursor.fetchone() is not None
            
            if exists:
                # 更新记录
                cursor.execute('''
                    UPDATE cve_records SET
                        title = ?, product = ?, danger_level = ?,
                        description = ?, impact_range = ?, security_versions = ?,
                        solution_advice = ?, reference_links = ?,
                        exploitability = ?, package = ?, publish_date = ?,
                        cwe = ?, score = ?, crawl_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE cve = ?
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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['cve'], data['title'], data['product'], data['danger_level'],
                    data['description'], data['impact_range'], data['security_versions'],
                    data['solution_advice'], data['reference_links'],
                    data['exploitability'], data['package'], data['publish_date'],
                    data['cwe'], data['score'], data['crawl_date']
                ))
                return True
    
    def batch_insert_or_update(self, cve_models: List[CVEModel]) -> Dict[str, int]:
        """
        批量插入或更新CVE记录
        
        Args:
            cve_models: CVE数据模型列表
            
        Returns:
            包含统计信息的字典
        """
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
        """
        根据CVE ID获取记录
        
        Args:
            cve_id: CVE编号
            
        Returns:
            CVE数据模型，如果不存在则返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cve_records WHERE cve = ?', (cve_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(dict(row))
            return None
    
    def get_all_cves(self, limit: Optional[int] = None, offset: int = 0) -> List[CVEModel]:
        """
        获取所有CVE记录
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            CVE数据模型列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if limit:
                cursor.execute('SELECT * FROM cve_records ORDER BY publish_date DESC LIMIT ? OFFSET ?', 
                             (limit, offset))
            else:
                cursor.execute('SELECT * FROM cve_records ORDER BY publish_date DESC')
            
            rows = cursor.fetchall()
            return [self._row_to_model(dict(row)) for row in rows]
    
    def get_cve_count(self) -> int:
        """获取CVE总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM cve_records')
            return cursor.fetchone()[0]
    
    def _row_to_model(self, row: dict) -> CVEModel:
        """将数据库行转换为CVE模型"""
        # 处理reference_links
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
        """
        更新爬取统计
        
        Args:
            date: 爬取日期
            new_count: 新增CVE数量
            updated_count: 更新CVE数量
            crawl_mode: 爬取模式 ('incremental' 或 'full')
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            total = new_count + updated_count
            
            cursor.execute('''
                INSERT OR REPLACE INTO crawl_stats (crawl_date, total_cves, new_cves, updated_cves, crawl_mode)
                VALUES (?, ?, ?, ?, ?)
            ''', (date, total, new_count, updated_count, crawl_mode))
    
    def get_latest_crawl_date(self) -> Optional[str]:
        """获取最新的爬取日期"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(publish_date) FROM cve_records WHERE publish_date != "N/A"')
            result = cursor.fetchone()[0]
            return result
    
    def get_latest_publish_date(self) -> Optional[str]:
        """
        获取数据库中最新CVE的发布日期
        
        Returns:
            最新的发布日期字符串，格式为 YYYY-MM-DD
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(publish_date) 
                FROM cve_records 
                WHERE publish_date != "N/A" 
                AND publish_date GLOB "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
            ''')
            result = cursor.fetchone()[0]
            return result
    
    def get_last_full_crawl_date(self) -> Optional[str]:
        """
        获取最后一次全量爬取的日期
        
        Returns:
            最后一次全量爬取的日期，格式为 YYYY-MM-DD
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(crawl_date) FROM full_crawl_history')
            result = cursor.fetchone()[0]
            return result
    
    def record_full_crawl(self, date: str, total_cves: int, duration_seconds: int):
        """
        记录全量爬取历史
        
        Args:
            date: 爬取日期
            total_cves: 总CVE数量
            duration_seconds: 爬取耗时（秒）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO full_crawl_history (crawl_date, total_cves, duration_seconds)
                VALUES (?, ?, ?)
            ''', (date, total_cves, duration_seconds))
    
    def should_run_full_crawl(self, interval_days: int = 30) -> bool:
        """
        判断是否应该执行全量爬取
        
        Args:
            interval_days: 全量爬取间隔天数
            
        Returns:
            如果应该执行全量爬取返回True
        """
        from datetime import datetime, timedelta
        
        last_full_crawl = self.get_last_full_crawl_date()
        if not last_full_crawl:
            # 如果从未执行过全量爬取，则执行
            return True
        
        try:
            last_date = datetime.strptime(last_full_crawl, '%Y-%m-%d')
            days_since = (datetime.now() - last_date).days
            return days_since >= interval_days
        except ValueError:
            # 日期格式错误，执行全量爬取
            return True
    
    def _migrate_database(self, cursor):
        """
        数据库迁移：检查并添加缺失的列
        
        Args:
            cursor: 数据库游标
        """
        try:
            # 检查 crawl_stats 表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='crawl_stats'
            """)
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # 检查 crawl_stats 表是否存在 crawl_mode 列
                cursor.execute("PRAGMA table_info(crawl_stats)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'crawl_mode' not in columns:
                    logger.info("检测到旧版数据库，正在添加 crawl_mode 列...")
                    cursor.execute('ALTER TABLE crawl_stats ADD COLUMN crawl_mode TEXT DEFAULT "incremental"')
                    logger.info("成功添加 crawl_mode 列")
                else:
                    logger.debug("数据库表结构已是最新版本")
        except Exception as e:
            logger.warning(f"数据库迁移检查失败: {e}")
            # 如果迁移失败，不影响正常使用，新表会在创建时自动包含该列
    
    def optimize_database(self):
        """优化数据库（VACUUM和ANALYZE）"""
        logger.info("开始优化数据库...")
        with self._get_connection() as conn:
            conn.execute('VACUUM')
            conn.execute('ANALYZE')
        logger.info("数据库优化完成")


# 向后兼容别名
DatabaseStorage = SQLiteStorage

