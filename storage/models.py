"""
SQLAlchemy 数据库模型
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class CVERecord(Base):
    """CVE记录表"""
    __tablename__ = 'cve_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cve = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text)
    product = Column(Text)
    danger_level = Column(String(50), index=True)
    description = Column(Text)
    impact_range = Column(Text)
    security_versions = Column(Text)
    solution_advice = Column(Text)
    reference_links = Column(Text)
    exploitability = Column(String(50))
    package = Column(String(50))
    publish_date = Column(String(20), index=True)
    cwe = Column(String(20))
    score = Column(String(20))
    crawl_date = Column(Text, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_cve', 'cve'),
        Index('idx_publish_date', 'publish_date'),
        Index('idx_crawl_date', 'crawl_date'),
        Index('idx_danger_level', 'danger_level'),
    )


class CrawlStats(Base):
    """爬取统计表"""
    __tablename__ = 'crawl_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    crawl_date = Column(Date, unique=True, nullable=False)
    total_cves = Column(Integer, default=0)
    new_cves = Column(Integer, default=0)
    updated_cves = Column(Integer, default=0)
    crawl_mode = Column(String(20), default='incremental')
    created_at = Column(DateTime, default=func.now())


class FullCrawlHistory(Base):
    """全量爬取历史表"""
    __tablename__ = 'full_crawl_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    crawl_date = Column(Date, unique=True, nullable=False, index=True)
    total_cves = Column(Integer, default=0)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_full_crawl_date', 'crawl_date'),
    )

