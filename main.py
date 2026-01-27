"""
主程序入口
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DATABASE_CONFIG, CRAWLER_CONFIG
from storage import create_storage
from core.crawler import CVECrawler, CrawlMode
from utils.logger import setup_logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AVD Sync - 阿里云CVE漏洞库同步工具')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--db-path', type=str, help='数据库文件路径')
    parser.add_argument('--optimize', action='store_true', help='爬取后优化数据库')
    parser.add_argument('--mode', type=str, choices=['incremental', 'full', 'auto'], 
                       default='auto', help='爬取模式: incremental(增量), full(全量), auto(自动判断)')
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("AVD Sync - 阿里云CVE漏洞库同步工具启动")
    logger.info("=" * 60)
    
    try:
        # 初始化数据库
        if args.db_path:
            # 如果指定了db_path参数，使用SQLite
            db_config = {
                'type': 'sqlite',
                'db_path': Path(args.db_path)
            }
        else:
            # 使用配置文件中的设置
            db_type = DATABASE_CONFIG.get('type', 'sqlite')
            if db_type == 'mysql':
                db_config = {
                    'type': 'mysql',
                    **DATABASE_CONFIG['mysql']
                }
            else:
                db_config = {
                    'type': 'sqlite',
                    'db_path': DATABASE_CONFIG['db_path']
                }
        
        db_storage = create_storage(db_config)
        logger.info(f"数据库类型: {db_config['type']}")
        if db_config['type'] == 'sqlite':
            logger.info(f"数据库路径: {db_config['db_path']}")
        else:
            logger.info(f"数据库: {db_config.get('database')} @ {db_config.get('host')}:{db_config.get('port')}")
        
        # 显示当前数据库统计
        total_count = db_storage.get_cve_count()
        logger.info(f"当前数据库中的CVE数量: {total_count}")
        
        # 确定爬取模式
        if args.mode == 'auto':
            # 自动判断：检查是否需要全量爬取
            interval_days = CRAWLER_CONFIG['full_crawl']['interval_days']
            if db_storage.should_run_full_crawl(interval_days):
                crawl_mode = CrawlMode.FULL
                logger.info(f"自动模式：距离上次全量爬取已超过{interval_days}天，执行全量爬取")
            else:
                crawl_mode = CrawlMode.INCREMENTAL
                logger.info("自动模式：执行增量爬取")
        elif args.mode == 'full':
            crawl_mode = CrawlMode.FULL
            logger.info("手动指定：执行全量爬取")
        else:
            crawl_mode = CrawlMode.INCREMENTAL
            logger.info("手动指定：执行增量爬取")
        
        # 创建爬虫实例
        crawler = CVECrawler(db_storage, crawl_mode)
        
        # 开始爬取
        import time
        start_time = time.time()
        stats = crawler.crawl()
        duration = int(time.time() - start_time)
        
        # 如果是全量爬取，更新耗时
        if crawl_mode == CrawlMode.FULL:
            from utils.date_utils import get_current_date
            db_storage.record_full_crawl(get_current_date(), stats['total_cves'], duration)
        
        # 显示最终统计
        logger.info("=" * 60)
        logger.info("爬取完成！最终统计:")
        logger.info(f"  爬取模式: {crawl_mode}")
        logger.info(f"  总页数: {stats['total_pages']}")
        logger.info(f"  尝试爬取CVE数: {stats['total_cves']}")
        logger.info(f"  成功处理CVE数: {stats.get('processed_cves', stats['total_cves'])}")
        logger.info(f"  新增CVE: {stats['new_cves']}")
        logger.info(f"  更新CVE: {stats['updated_cves']}")
        logger.info(f"  失败CVE: {stats['failed_cves']}")
        if stats.get('skipped_cves', 0) > 0:
            logger.info(f"  跳过CVE: {stats['skipped_cves']}")
        logger.info(f"  耗时: {duration}秒")
        processed = stats.get('processed_cves', stats['total_cves'])
        if processed > 0:
            logger.info(f"  平均速度: {processed/duration:.2f} CVE/秒")
        logger.info("=" * 60)
        
        # 优化数据库
        if args.optimize:
            logger.info("开始优化数据库...")
            db_storage.optimize_database()
            logger.info("数据库优化完成")
        
        # 显示最终数据库统计
        final_count = db_storage.get_cve_count()
        logger.info(f"数据库中的CVE总数: {final_count}")
        
    except KeyboardInterrupt:
        logger.warning("用户中断爬取")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

