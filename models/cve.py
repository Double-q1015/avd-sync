"""
CVE数据模型
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class CVEModel:
    """CVE漏洞数据模型"""
    cve: str
    title: str
    product: str
    danger_level: str
    description: str
    impact_range: str
    security_versions: str
    solution_advice: Optional[str]
    reference_links: List[str]
    exploitability: str
    package: str  # 修复拼写错误：pcakage -> package
    publish_date: str
    cwe: Optional[str] = None
    score: Optional[str] = None
    crawl_date: Optional[str] = None  # 爬取日期
    
    def __post_init__(self):
        """初始化后处理"""
        if self.crawl_date is None:
            self.crawl_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 确保reference_links是列表
        if isinstance(self.reference_links, str):
            self.reference_links = [self.reference_links] if self.reference_links else []
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'cve': self.cve,
            'title': self.title,
            'product': self.product,
            'danger_level': self.danger_level,
            'description': self.description,
            'impact_range': self.impact_range,
            'security_versions': self.security_versions,
            'solution_advice': self.solution_advice,
            'reference_links': ','.join(self.reference_links) if self.reference_links else '',
            'exploitability': self.exploitability,
            'package': self.package,
            'publish_date': self.publish_date,
            'cwe': self.cwe or '',
            'score': self.score or '',
            'crawl_date': self.crawl_date,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CVEModel':
        """从字典创建对象"""
        # 处理reference_links
        ref_links = data.get('reference_links', [])
        if isinstance(ref_links, str):
            ref_links = [link for link in ref_links.split(',') if link] if ref_links else []
        
        # 兼容旧的拼写错误
        package = data.get('package') or data.get('pcakage', 'N/A')
        
        return cls(
            cve=data.get('cve', ''),
            title=data.get('title', 'N/A'),
            product=data.get('product', 'N/A'),
            danger_level=data.get('danger_level', 'N/A'),
            description=data.get('description', 'N/A'),
            impact_range=data.get('impact_range', 'N/A'),
            security_versions=data.get('security_versions', 'N/A'),
            solution_advice=data.get('solution_advice'),
            reference_links=ref_links,
            exploitability=data.get('exploitability', 'N/A'),
            package=package,
            publish_date=data.get('publish_date', 'N/A'),
            cwe=data.get('cwe'),
            score=data.get('score'),
            crawl_date=data.get('crawl_date'),
        )

