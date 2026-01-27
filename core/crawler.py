"""
爬虫核心模块
"""
import time
import logging
from typing import List, Optional
from tqdm import tqdm

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.browser import BrowserManager
from core.parser import HTMLParser
from storage.db_storage import DatabaseStorage
from models.cve import CVEModel
from utils.date_utils import is_date_before, get_current_date, parse_date
from utils.retry import retry
from config.settings import CRAWLER_CONFIG, BROWSER_CONFIG
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CrawlMode:
    """爬取模式枚举"""
    INCREMENTAL = 'incremental'  # 增量爬取
    FULL = 'full'  # 全量爬取


class CVECrawler:
    """CVE爬虫主类"""
    
    def __init__(self, db_storage: DatabaseStorage, crawl_mode: str = CrawlMode.INCREMENTAL):
        """
        初始化爬虫
        
        Args:
            db_storage: 数据库存储实例
            crawl_mode: 爬取模式 ('incremental' 或 'full')
        """
        self.db_storage = db_storage
        self.browser_manager = BrowserManager()
        self.cve_vuln_url = CRAWLER_CONFIG['cve_vuln_url']
        self.cve_detail_url = CRAWLER_CONFIG['cve_detail_url']
        self.request_delay = CRAWLER_CONFIG['request_delay']
        self.crawl_mode = crawl_mode
        
        # 根据爬取模式设置停止日期
        if crawl_mode == CrawlMode.INCREMENTAL:
            # 增量爬取：从数据库最新日期开始，向前回溯几天防止遗漏
            latest_date = self.db_storage.get_latest_publish_date()
            if latest_date:
                latest_dt = parse_date(latest_date)
                if latest_dt:
                    lookback_days = CRAWLER_CONFIG['incremental']['lookback_days']
                    start_date = latest_dt - timedelta(days=lookback_days)
                    self.stop_date = start_date.strftime('%Y-%m-%d')
                    logger.info(f"增量爬取模式：从 {self.stop_date} 开始（向前回溯{lookback_days}天）")
                else:
                    # 日期解析失败，提示使用全量爬取
                    logger.error(f"无法解析数据库中的最新日期: {latest_date}")
                    logger.error("建议使用全量爬取模式初始化数据库")
                    raise ValueError(f"日期解析失败: {latest_date}")
            else:
                # 数据库为空，提示使用全量爬取
                logger.error("数据库为空，无法执行增量爬取")
                logger.error("请先使用全量爬取模式初始化数据库: python main.py --mode full")
                raise ValueError("数据库为空，无法执行增量爬取。请先使用全量爬取模式初始化数据库")
        else:
            # 全量爬取：不设置日期限制，爬取所有数据
            self.stop_date = None
            logger.info("全量爬取模式：将爬取所有可用数据（无日期限制）")
    
    def crawl(self) -> dict:
        """
        爬取所有CVE数据
        
        Returns:
            包含统计信息的字典
        """
        stats = {
            'total_pages': 0,
            'total_cves': 0,  # 总尝试爬取的CVE数
            'processed_cves': 0,  # 成功处理的CVE数
            'new_cves': 0,
            'updated_cves': 0,
            'failed_cves': 0,
            'skipped_cves': 0
        }
        
        try:
            page_num = CRAWLER_CONFIG['start_page']
            
            with self.browser_manager:
                while True:
                    logger.info(f"开始爬取第 {page_num} 页...")
                    
                    # 获取列表页
                    cve_info_list = self._fetch_vuln_list(page_num)
                    
                    if not cve_info_list:
                        logger.warning(f"第 {page_num} 页没有数据，停止爬取")
                        break
                    
                    stats['total_pages'] += 1
                    
                    # 爬取每个CVE的详细信息
                    page_stats = self._crawl_cve_details(cve_info_list)
                    stats['total_cves'] += page_stats.get('total', 0)
                    stats['processed_cves'] += page_stats.get('processed', 0)
                    stats['new_cves'] += page_stats['new']
                    stats['updated_cves'] += page_stats['updated']
                    stats['failed_cves'] += page_stats['failed']
                    stats['skipped_cves'] += page_stats.get('skipped', 0)
                    
                    # 检查是否应该停止
                    if self._should_stop(cve_info_list):
                        if self.crawl_mode == CrawlMode.FULL:
                            logger.info("全量爬取：已爬取完所有可用数据，停止爬取")
                        else:
                            logger.info(f"增量爬取：达到停止条件（日期阈值: {self.stop_date}），停止爬取")
                        break
                    
                    page_num += 1
                    # 列表页之间的延迟可以减少
                    if self.request_delay > 0:
                        time.sleep(self.request_delay * 0.5)  # 列表页延迟减半
        
        except Exception as e:
            logger.error(f"爬取过程中出错: {e}", exc_info=True)
            raise
        
        finally:
            # 更新爬取统计
            self.db_storage.update_crawl_stats(
                get_current_date(),
                stats['new_cves'],
                stats['updated_cves'],
                self.crawl_mode
            )
            
            # 如果是全量爬取，记录历史
            if self.crawl_mode == CrawlMode.FULL:
                # 计算耗时（这里简化处理，实际应该在开始时记录）
                self.db_storage.record_full_crawl(
                    get_current_date(),
                    stats['total_cves'],
                    0  # 耗时需要在实际实现中计算
                )
            
            logger.info(f"爬取完成！模式: {self.crawl_mode}, 统计信息: {stats}")
        
        return stats
    
    def crawl_all(self) -> dict:
        """
        兼容旧接口，默认使用增量爬取
        """
        return self.crawl()
    
    @retry(max_retries=CRAWLER_CONFIG['max_retries'], delay=CRAWLER_CONFIG['retry_delay'])
    def _fetch_vuln_list(self, page_num: int) -> List[dict]:
        """
        获取漏洞列表页
        
        Args:
            page_num: 页码
            
        Returns:
            漏洞信息列表
        """
        url = self.cve_vuln_url + str(page_num)
        page = self.browser_manager.get_page()
        
        logger.debug(f"访问列表页: {url}")
        page.get(url, timeout=BROWSER_CONFIG.get('timeout', 10))
        
        # 智能等待：等待表格加载完成（最多等待0.5秒）
        try:
            page.wait.ele_loaded('table', timeout=0.5)
        except:
            # 如果等待超时，使用更短的固定等待
            time.sleep(0.2)
        
        html = page.html
        cve_info_list = HTMLParser.parse_vuln_page(html)
        
        logger.info(f"第 {page_num} 页解析到 {len(cve_info_list)} 个CVE")
        return cve_info_list
    
    def _crawl_cve_details(self, cve_info_list: List[dict]) -> dict:
        """
        爬取CVE详细信息
        
        Args:
            cve_info_list: CVE信息列表
            
        Returns:
            统计信息字典
        """
        cve_models = []
        skipped_count = 0
        failed_count = 0
        total_attempted = 0
        
        for cve_info in tqdm(cve_info_list, desc="爬取CVE详情"):
            cve_id = cve_info.get('cve_id')
            if not cve_id:
                logger.warning(f"跳过无效的CVE信息: {cve_info}")
                failed_count += 1
                continue
            
            total_attempted += 1
            
            # 优化：检查CVE是否已存在（增量爬取时可以跳过已存在的）
            if self.crawl_mode == CrawlMode.INCREMENTAL:
                existing = self.db_storage.get_cve(cve_id)
                if existing:
                    # 检查是否需要更新（比较发布日期）
                    cve_date = cve_info.get('date', '')
                    if existing.publish_date != 'N/A' and cve_date:
                        # 如果日期相同，可能不需要更新，跳过
                        if existing.publish_date == cve_date.split(' ')[0]:
                            skipped_count += 1
                            continue
            
            try:
                cve_model = self._fetch_cve_detail(cve_id, cve_info)
                if cve_model:
                    cve_models.append(cve_model)
                else:
                    # 解析返回None，计入失败
                    logger.warning(f"CVE {cve_id} 解析返回空结果")
                    failed_count += 1
                # 减少延迟，只在必要时等待
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
            except Exception as e:
                logger.error(f"爬取CVE {cve_id} 详情失败: {e}")
                failed_count += 1
                continue
        
        if skipped_count > 0:
            logger.info(f"跳过了 {skipped_count} 个已存在的CVE（无需更新）")
        
        # 批量保存到数据库
        db_failed = 0
        if cve_models:
            stats = self.db_storage.batch_insert_or_update(cve_models)
            db_failed = stats['failed']
            return {
                'total': total_attempted,  # 总尝试数
                'processed': len(cve_models),  # 成功处理数
                'new': stats['new'],
                'updated': stats['updated'],
                'failed': failed_count + db_failed,  # 解析失败 + 数据库失败
                'skipped': skipped_count
            }
        
        return {
            'total': total_attempted,
            'processed': 0,
            'new': 0,
            'updated': 0,
            'failed': failed_count,
            'skipped': skipped_count
        }
    
    @retry(max_retries=CRAWLER_CONFIG['max_retries'], delay=CRAWLER_CONFIG['retry_delay'])
    def _fetch_cve_detail(self, cve_id: str, cve_info: dict) -> Optional[CVEModel]:
        """
        获取CVE详细信息
        
        Args:
            cve_id: CVE编号
            cve_info: CVE基本信息
            
        Returns:
            CVE数据模型
        """
        url = self.cve_detail_url + cve_id
        page = self.browser_manager.get_page()
        
        logger.debug(f"访问详情页: {url}")
        page.get(url, timeout=BROWSER_CONFIG.get('timeout', 10))
        
        # 智能等待：等待主要内容加载（最多等待0.3秒）
        try:
            # 等待标题或主要内容区域加载
            page.wait.ele_loaded('span.header__title__text', timeout=0.3)
        except:
            # 如果等待超时，使用更短的固定等待
            time.sleep(0.15)
        
        html = page.html
        cve_model = HTMLParser.parse_vuln_detail(cve_id, html)
        
        # 补充列表页的信息
        if cve_info.get('cwe'):
            cve_model.cwe = cve_info['cwe']
        if cve_info.get('score'):
            cve_model.score = cve_info['score']
        
        return cve_model
    
    def _should_stop(self, cve_info_list: List[dict]) -> bool:
        """
        检查是否应该停止爬取
        
        Args:
            cve_info_list: 当前页的CVE信息列表
            
        Returns:
            如果应该停止返回True
        """
        # 全量爬取：不设置日期限制，只有当页面为空时才停止
        if self.crawl_mode == CrawlMode.FULL or self.stop_date is None:
            return False
        
        # 增量爬取：检查是否所有CVE都早于停止日期
        # 只有当所有CVE都早于停止日期时才停止（避免因单页混合新旧日期而提前停止）
        all_before_stop = True
        for cve_info in cve_info_list:
            date = cve_info.get('date', '')
            if date:
                try:
                    if not is_date_before(date, self.stop_date):
                        # 如果有一个CVE不早于停止日期，继续爬取
                        all_before_stop = False
                        break
                except ValueError:
                    # 日期解析失败，继续爬取
                    all_before_stop = False
                    break
        
        return all_before_stop

