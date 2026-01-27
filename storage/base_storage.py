"""
数据库存储抽象基类
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from contextlib import contextmanager

from models.cve import CVEModel


class BaseStorage(ABC):
    """数据库存储抽象基类"""
    
    @abstractmethod
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        pass
    
    @abstractmethod
    def _init_database(self):
        """初始化数据库表结构"""
        pass
    
    @abstractmethod
    def insert_or_update_cve(self, cve_model: CVEModel) -> bool:
        """
        插入或更新CVE记录
        
        Args:
            cve_model: CVE数据模型
            
        Returns:
            True表示新插入，False表示更新
        """
        pass
    
    @abstractmethod
    def batch_insert_or_update(self, cve_models: List[CVEModel]) -> Dict[str, int]:
        """
        批量插入或更新CVE记录
        
        Args:
            cve_models: CVE数据模型列表
            
        Returns:
            包含统计信息的字典
        """
        pass
    
    @abstractmethod
    def get_cve(self, cve_id: str) -> Optional[CVEModel]:
        """
        根据CVE ID获取记录
        
        Args:
            cve_id: CVE编号
            
        Returns:
            CVE数据模型，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def get_all_cves(self, limit: Optional[int] = None, offset: int = 0) -> List[CVEModel]:
        """
        获取所有CVE记录
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            CVE数据模型列表
        """
        pass
    
    @abstractmethod
    def get_cve_count(self) -> int:
        """获取CVE总数"""
        pass
    
    @abstractmethod
    def update_crawl_stats(self, date: str, new_count: int, updated_count: int, crawl_mode: str = 'incremental'):
        """
        更新爬取统计
        
        Args:
            date: 爬取日期
            new_count: 新增CVE数量
            updated_count: 更新CVE数量
            crawl_mode: 爬取模式 ('incremental' 或 'full')
        """
        pass
    
    @abstractmethod
    def get_latest_publish_date(self) -> Optional[str]:
        """
        获取数据库中最新CVE的发布日期
        
        Returns:
            最新的发布日期字符串，格式为 YYYY-MM-DD
        """
        pass
    
    @abstractmethod
    def get_last_full_crawl_date(self) -> Optional[str]:
        """
        获取最后一次全量爬取的日期
        
        Returns:
            最后一次全量爬取的日期，格式为 YYYY-MM-DD
        """
        pass
    
    @abstractmethod
    def record_full_crawl(self, date: str, total_cves: int, duration_seconds: int):
        """
        记录全量爬取历史
        
        Args:
            date: 爬取日期
            total_cves: 总CVE数量
            duration_seconds: 爬取耗时（秒）
        """
        pass
    
    @abstractmethod
    def should_run_full_crawl(self, interval_days: int = 30) -> bool:
        """
        判断是否应该执行全量爬取
        
        Args:
            interval_days: 全量爬取间隔天数
            
        Returns:
            如果应该执行全量爬取返回True
        """
        pass
    
    @abstractmethod
    def optimize_database(self):
        """优化数据库"""
        pass
