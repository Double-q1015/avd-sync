"""
基于SQLAlchemy的数据库存储模块
支持SQLite和MySQL等多种数据库
"""
import logging
from typing import List, Optional, Dict
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    create_engine = None
    sessionmaker = None
    Session = None
    SQLAlchemyError = None
    text = None

from models.cve import CVEModel
from storage.base_storage import BaseStorage
from storage.models import Base, CVERecord, CrawlStats, FullCrawlHistory

logger = logging.getLogger(__name__)


class SQLAlchemyStorage(BaseStorage):
    """基于SQLAlchemy的数据库存储类"""
    
    def __init__(self, database_url: str, echo: bool = False, create_database: bool = True):
        """
        初始化SQLAlchemy数据库存储
        
        Args:
            database_url: 数据库连接URL
                SQLite示例: 'sqlite:///path/to/database.db'
                MySQL示例: 'mysql+pymysql://user:password@host:port/database'
                MySQL示例(官方连接器): 'mysql+mysqlconnector://user:password@host:port/database'
            echo: 是否打印SQL语句（用于调试）
            create_database: 如果数据库不存在，是否自动创建（仅MySQL）
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "SQLAlchemy支持需要安装sqlalchemy库。请运行: pip install sqlalchemy"
            )
        
        self.database_url = database_url
        self.echo = echo
        
        # 如果是MySQL且需要自动创建数据库
        if create_database and 'mysql' in database_url.lower():
            self._ensure_database_exists(database_url)
        
        self.engine = create_engine(database_url, echo=echo, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self._init_database()
    
    def _ensure_database_exists(self, database_url: str):
        """
        确保MySQL数据库存在，如果不存在则创建
        
        Args:
            database_url: 数据库连接URL
        """
        try:
            # 解析数据库URL
            parsed = urlparse(database_url)
            
            # 提取数据库名
            database_name = parsed.path.lstrip('/')
            if not database_name:
                return  # 没有指定数据库名，跳过
            
            # 构建不包含数据库名的URL（连接到MySQL服务器）
            server_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                '',  # 路径为空
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            # 尝试连接服务器（不指定数据库）
            server_engine = create_engine(server_url, echo=False, pool_pre_ping=True)
            
            with server_engine.begin() as conn:
                # 检查数据库是否存在
                result = conn.execute(text(f"SHOW DATABASES LIKE '{database_name}'"))
                if result.fetchone() is None:
                    # 数据库不存在，创建它
                    logger.info(f"数据库 '{database_name}' 不存在，正在创建...")
                    conn.execute(text(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    logger.info(f"✅ 数据库 '{database_name}' 创建成功")
                else:
                    logger.debug(f"数据库 '{database_name}' 已存在")
            
            server_engine.dispose()
            
        except Exception as e:
            logger.warning(f"自动创建数据库失败: {e}")
            logger.info("请手动创建数据库或检查连接权限")
            # 不抛出异常，让后续连接尝试继续
    
    @contextmanager
    def _get_session(self) -> Session:
        """获取数据库会话的上下文管理器"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def _get_connection(self):
        """兼容接口：获取数据库连接（实际返回session）"""
        with self._get_session() as session:
            yield session
    
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            Base.metadata.create_all(bind=self.engine)
            
            # 执行数据库迁移
            with self._get_session() as session:
                self._migrate_database(session)
            
            logger.info("数据库表结构初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _migrate_database(self, session: Session):
        """
        数据库迁移：检查并添加缺失的列
        
        Args:
            session: 数据库会话
        """
        try:
            # 检查 crawl_stats 表是否存在 crawl_mode 列
            if 'mysql' in self.database_url.lower():
                # MySQL
                result = session.execute(text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'crawl_stats' 
                    AND COLUMN_NAME = 'crawl_mode'
                """))
            else:
                # SQLite
                result = session.execute(text("""
                    SELECT name FROM pragma_table_info('crawl_stats') 
                    WHERE name = 'crawl_mode'
                """))
            
            if result.fetchone() is None:
                logger.info("检测到旧版数据库，正在添加 crawl_mode 列...")
                if 'mysql' in self.database_url.lower():
                    session.execute(text('ALTER TABLE crawl_stats ADD COLUMN crawl_mode VARCHAR(20) DEFAULT "incremental"'))
                else:
                    session.execute(text('ALTER TABLE crawl_stats ADD COLUMN crawl_mode TEXT DEFAULT "incremental"'))
                logger.info("成功添加 crawl_mode 列")
            else:
                logger.debug("数据库表结构已是最新版本")
        except Exception as e:
            logger.warning(f"数据库迁移检查失败: {e}")
    
    def insert_or_update_cve(self, cve_model: CVEModel) -> bool:
        """插入或更新CVE记录"""
        data = cve_model.to_dict()
        
        with self._get_session() as session:
            # 检查CVE是否已存在
            existing = session.query(CVERecord).filter(CVERecord.cve == data['cve']).first()
            
            if existing:
                # 更新记录
                for key, value in data.items():
                    if key != 'cve':  # 不更新主键
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
                return False
            else:
                # 插入新记录
                record = CVERecord(**data)
                session.add(record)
                return True
    
    def batch_insert_or_update(self, cve_models: List[CVEModel]) -> Dict[str, int]:
        """批量插入或更新CVE记录"""
        stats = {'new': 0, 'updated': 0, 'failed': 0}
        
        with self._get_session() as session:
            for cve_model in cve_models:
                try:
                    data = cve_model.to_dict()
                    
                    # 检查CVE是否已存在
                    existing = session.query(CVERecord).filter(CVERecord.cve == data['cve']).first()
                    
                    if existing:
                        # 更新记录
                        for key, value in data.items():
                            if key != 'cve':  # 不更新主键
                                setattr(existing, key, value)
                        existing.updated_at = datetime.now()
                        stats['updated'] += 1
                    else:
                        # 插入新记录
                        record = CVERecord(**data)
                        session.add(record)
                        stats['new'] += 1
                except Exception as e:
                    logger.error(f"插入/更新CVE {cve_model.cve} 失败: {e}")
                    stats['failed'] += 1
        
        return stats
    
    def get_cve(self, cve_id: str) -> Optional[CVEModel]:
        """根据CVE ID获取记录"""
        with self._get_session() as session:
            record = session.query(CVERecord).filter(CVERecord.cve == cve_id).first()
            
            if record:
                return self._record_to_model(record)
            return None
    
    def get_all_cves(self, limit: Optional[int] = None, offset: int = 0) -> List[CVEModel]:
        """获取所有CVE记录"""
        with self._get_session() as session:
            query = session.query(CVERecord).order_by(CVERecord.publish_date.desc())
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            records = query.all()
            return [self._record_to_model(record) for record in records]
    
    def get_cve_count(self) -> int:
        """获取CVE总数"""
        with self._get_session() as session:
            return session.query(CVERecord).count()
    
    def _record_to_model(self, record: CVERecord) -> CVEModel:
        """将数据库记录转换为CVE模型"""
        ref_links = record.reference_links or ''
        if ref_links:
            ref_links = [link for link in ref_links.split(',') if link]
        else:
            ref_links = []
        
        data = {
            'cve': record.cve,
            'title': record.title or 'N/A',
            'product': record.product or 'N/A',
            'danger_level': record.danger_level or 'N/A',
            'description': record.description or 'N/A',
            'impact_range': record.impact_range or 'N/A',
            'security_versions': record.security_versions or 'N/A',
            'solution_advice': record.solution_advice,
            'reference_links': ref_links,
            'exploitability': record.exploitability or 'N/A',
            'package': record.package or 'N/A',
            'publish_date': record.publish_date or 'N/A',
            'cwe': record.cwe,
            'score': record.score,
            'crawl_date': record.crawl_date,
        }
        return CVEModel.from_dict(data)
    
    def update_crawl_stats(self, date_str: str, new_count: int, updated_count: int, crawl_mode: str = 'incremental'):
        """更新爬取统计"""
        with self._get_session() as session:
            crawl_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            total = new_count + updated_count
            
            stats = session.query(CrawlStats).filter(CrawlStats.crawl_date == crawl_date).first()
            
            if stats:
                stats.total_cves = total
                stats.new_cves = new_count
                stats.updated_cves = updated_count
                stats.crawl_mode = crawl_mode
            else:
                stats = CrawlStats(
                    crawl_date=crawl_date,
                    total_cves=total,
                    new_cves=new_count,
                    updated_cves=updated_count,
                    crawl_mode=crawl_mode
                )
                session.add(stats)
    
    def get_latest_publish_date(self) -> Optional[str]:
        """获取数据库中最新CVE的发布日期"""
        with self._get_session() as session:
            # 根据数据库类型使用不同的查询
            if 'sqlite' in self.database_url.lower():
                # SQLite使用GLOB
                result = session.execute(text("""
                    SELECT MAX(publish_date) as max_date
                    FROM cve_records 
                    WHERE publish_date != 'N/A' 
                    AND publish_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                """))
            else:
                # MySQL使用REGEXP
                result = session.execute(text("""
                    SELECT MAX(publish_date) as max_date
                    FROM cve_records 
                    WHERE publish_date != 'N/A' 
                    AND publish_date REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                """))
            row = result.fetchone()
            return row[0] if row and row[0] else None
    
    def get_last_full_crawl_date(self) -> Optional[str]:
        """获取最后一次全量爬取的日期"""
        with self._get_session() as session:
            result = session.query(FullCrawlHistory.crawl_date).order_by(
                FullCrawlHistory.crawl_date.desc()
            ).first()
            
            if result:
                return result[0].strftime('%Y-%m-%d') if isinstance(result[0], date) else str(result[0])
            return None
    
    def record_full_crawl(self, date_str: str, total_cves: int, duration_seconds: int):
        """记录全量爬取历史"""
        with self._get_session() as session:
            crawl_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            history = session.query(FullCrawlHistory).filter(
                FullCrawlHistory.crawl_date == crawl_date
            ).first()
            
            if history:
                history.total_cves = total_cves
                history.duration_seconds = duration_seconds
            else:
                history = FullCrawlHistory(
                    crawl_date=crawl_date,
                    total_cves=total_cves,
                    duration_seconds=duration_seconds
                )
                session.add(history)
    
    def should_run_full_crawl(self, interval_days: int = 30) -> bool:
        """判断是否应该执行全量爬取"""
        from datetime import datetime, timedelta
        
        last_full_crawl = self.get_last_full_crawl_date()
        if not last_full_crawl:
            return True
        
        try:
            last_date = datetime.strptime(last_full_crawl, '%Y-%m-%d')
            days_since = (datetime.now() - last_date).days
            return days_since >= interval_days
        except (ValueError, TypeError):
            return True
    
    def optimize_database(self):
        """优化数据库"""
        logger.info("开始优化数据库...")
        try:
            if 'sqlite' in self.database_url.lower():
                # SQLite优化
                with self._get_session() as session:
                    session.execute(text('VACUUM'))
                    session.execute(text('ANALYZE'))
            elif 'mysql' in self.database_url.lower():
                # MySQL优化
                with self._get_session() as session:
                    session.execute(text('OPTIMIZE TABLE cve_records, crawl_stats, full_crawl_history'))
            logger.info("数据库优化完成")
        except Exception as e:
            logger.warning(f"数据库优化失败: {e}")

