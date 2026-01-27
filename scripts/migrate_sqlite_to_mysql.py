#!/usr/bin/env python3
"""
SQLite到MySQL数据迁移脚本
"""
import sys
import argparse
from pathlib import Path
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db_storage import SQLiteStorage
from storage import create_storage
from models.cve import CVEModel
from utils.logger import setup_logger
from config.settings import DATABASE_CONFIG

logger = setup_logger()


def migrate_cve_records(sqlite_storage, mysql_storage, batch_size=100):
    """
    迁移CVE记录
    
    Args:
        sqlite_storage: SQLite存储实例
        mysql_storage: MySQL存储实例
        batch_size: 批量处理大小
    """
    logger.info("开始迁移CVE记录...")
    
    # 获取SQLite中的CVE总数
    total_count = sqlite_storage.get_cve_count()
    logger.info(f"SQLite数据库中共有 {total_count} 条CVE记录")
    
    if total_count == 0:
        logger.warning("SQLite数据库为空，无需迁移")
        return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
    
    # 获取MySQL中已有的CVE数量
    mysql_count = mysql_storage.get_cve_count()
    logger.info(f"MySQL数据库中已有 {mysql_count} 条CVE记录")
    
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
    
    # 分批读取和迁移
    offset = 0
    batch_num = 0
    
    with tqdm(total=total_count, desc="迁移CVE记录", unit="条") as pbar:
        while True:
            # 从SQLite读取一批数据
            cve_list = sqlite_storage.get_all_cves(limit=batch_size, offset=offset)
            
            if not cve_list:
                break
            
            batch_num += 1
            batch_cves = []
            
            for cve_model in cve_list:
                stats['total'] += 1
                batch_cves.append(cve_model)
            
            # 批量插入/更新到MySQL
            if batch_cves:
                try:
                    batch_stats = mysql_storage.batch_insert_or_update(batch_cves)
                    stats['success'] += batch_stats['new'] + batch_stats['updated']
                    stats['failed'] += batch_stats['failed']
                except Exception as e:
                    logger.error(f"批量插入失败（批次 {batch_num}）: {e}")
                    stats['failed'] += len(batch_cves)
            
            offset += batch_size
            pbar.update(len(cve_list))
            
            # 每1000条记录显示一次进度
            if stats['total'] % 1000 == 0:
                logger.info(f"已处理 {stats['total']}/{total_count} 条记录... (成功: {stats['success']}, 失败: {stats['failed']})")
    
    logger.info(f"CVE记录迁移完成: 总计 {stats['total']}, 成功 {stats['success']}, 失败 {stats['failed']}")
    return stats


def migrate_crawl_stats(sqlite_storage, mysql_storage):
    """
    迁移爬取统计
    
    Args:
        sqlite_storage: SQLite存储实例
        mysql_storage: MySQL存储实例
    """
    logger.info("开始迁移爬取统计...")
    
    try:
        with sqlite_storage._get_connection() as sqlite_conn:
            cursor = sqlite_conn.cursor()
            cursor.execute('SELECT * FROM crawl_stats ORDER BY crawl_date')
            rows = cursor.fetchall()
            
            stats_count = 0
            for row in rows:
                row_dict = dict(row)
                date = row_dict['crawl_date']
                new_count = row_dict.get('new_cves', 0)
                updated_count = row_dict.get('updated_cves', 0)
                crawl_mode = row_dict.get('crawl_mode', 'incremental')
                
                mysql_storage.update_crawl_stats(date, new_count, updated_count, crawl_mode)
                stats_count += 1
            
            logger.info(f"爬取统计迁移完成: {stats_count} 条记录")
            return stats_count
    except Exception as e:
        logger.error(f"迁移爬取统计失败: {e}")
        return 0


def migrate_full_crawl_history(sqlite_storage, mysql_storage):
    """
    迁移全量爬取历史
    
    Args:
        sqlite_storage: SQLite存储实例
        mysql_storage: MySQL存储实例
    """
    logger.info("开始迁移全量爬取历史...")
    
    try:
        with sqlite_storage._get_connection() as sqlite_conn:
            cursor = sqlite_conn.cursor()
            cursor.execute('SELECT * FROM full_crawl_history ORDER BY crawl_date')
            rows = cursor.fetchall()
            
            history_count = 0
            for row in rows:
                row_dict = dict(row)
                date = row_dict['crawl_date']
                total_cves = row_dict.get('total_cves', 0)
                duration_seconds = row_dict.get('duration_seconds', 0)
                
                mysql_storage.record_full_crawl(date, total_cves, duration_seconds)
                history_count += 1
            
            logger.info(f"全量爬取历史迁移完成: {history_count} 条记录")
            return history_count
    except Exception as e:
        logger.error(f"迁移全量爬取历史失败: {e}")
        return 0


def verify_migration(sqlite_storage, mysql_storage):
    """
    验证迁移结果
    
    Args:
        sqlite_storage: SQLite存储实例
        mysql_storage: MySQL存储实例
    """
    logger.info("开始验证迁移结果...")
    
    # 比较CVE数量
    sqlite_count = sqlite_storage.get_cve_count()
    mysql_count = mysql_storage.get_cve_count()
    
    logger.info(f"SQLite CVE数量: {sqlite_count}")
    logger.info(f"MySQL CVE数量: {mysql_count}")
    
    if sqlite_count == mysql_count:
        logger.info("✅ CVE数量匹配，迁移成功")
    else:
        logger.warning(f"⚠️  CVE数量不匹配，差异: {abs(sqlite_count - mysql_count)}")
    
    # 比较最新发布日期
    sqlite_latest = sqlite_storage.get_latest_publish_date()
    mysql_latest = mysql_storage.get_latest_publish_date()
    
    logger.info(f"SQLite最新发布日期: {sqlite_latest}")
    logger.info(f"MySQL最新发布日期: {mysql_latest}")
    
    if sqlite_latest == mysql_latest:
        logger.info("✅ 最新发布日期匹配")
    else:
        logger.warning(f"⚠️  最新发布日期不匹配")
    
    # 随机抽样验证
    logger.info("随机抽样验证...")
    sample_cves = sqlite_storage.get_all_cves(limit=10)
    match_count = 0
    
    for cve_model in sample_cves:
        mysql_cve = mysql_storage.get_cve(cve_model.cve)
        if mysql_cve and mysql_cve.cve == cve_model.cve:
            match_count += 1
    
    logger.info(f"抽样验证: {match_count}/{len(sample_cves)} 条记录匹配")
    
    return {
        'cve_count_match': sqlite_count == mysql_count,
        'latest_date_match': sqlite_latest == mysql_latest,
        'sample_match_rate': match_count / len(sample_cves) if sample_cves else 0
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SQLite到MySQL数据迁移工具')
    parser.add_argument('--sqlite-path', type=str, help='SQLite数据库路径（默认使用配置中的路径）')
    parser.add_argument('--mysql-config', type=str, help='MySQL配置JSON文件路径（可选）')
    parser.add_argument('--batch-size', type=int, default=100, help='批量处理大小（默认100）')
    parser.add_argument('--skip-stats', action='store_true', help='跳过爬取统计迁移')
    parser.add_argument('--skip-history', action='store_true', help='跳过全量爬取历史迁移')
    parser.add_argument('--verify', action='store_true', help='迁移后验证数据')
    parser.add_argument('--dry-run', action='store_true', help='干运行模式（不实际迁移）')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("SQLite到MySQL数据迁移工具")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("⚠️  干运行模式：不会实际执行迁移")
    
    try:
        # 初始化SQLite存储
        sqlite_path = Path(args.sqlite_path) if args.sqlite_path else DATABASE_CONFIG['db_path']
        if not sqlite_path.exists():
            logger.error(f"SQLite数据库文件不存在: {sqlite_path}")
            return 1
        
        logger.info(f"SQLite数据库路径: {sqlite_path}")
        sqlite_storage = SQLiteStorage(sqlite_path)
        
        # 初始化MySQL存储
        mysql_config = DATABASE_CONFIG.get('mysql', {})
        if not mysql_config or not mysql_config.get('host'):
            logger.error("MySQL配置未设置，请先配置MySQL连接信息")
            logger.info("可以通过以下方式配置:")
            logger.info("1. 在 config/settings.py 中配置 DATABASE_CONFIG['mysql']")
            logger.info("2. 或使用环境变量: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
            return 1
        
        mysql_storage_config = {
            'type': 'mysql',
            **mysql_config
        }
        
        logger.info(f"MySQL配置:")
        logger.info(f"  主机: {mysql_config['host']}:{mysql_config.get('port', 3306)}")
        logger.info(f"  数据库: {mysql_config['database']}")
        logger.info(f"  用户: {mysql_config['user']}")
        
        if args.dry_run:
            logger.info("干运行模式：跳过MySQL连接")
        else:
            try:
                mysql_storage = create_storage(mysql_storage_config)
                logger.info("✅ MySQL连接成功")
            except Exception as e:
                logger.error(f"MySQL连接失败: {e}")
                logger.info("\n提示:")
                logger.info("  1. 检查MySQL服务是否运行")
                logger.info("  2. 检查网络连接")
                logger.info("  3. 检查用户名和密码是否正确")
                logger.info("  4. 检查用户是否有创建数据库的权限")
                return 1
        
        # 显示统计信息
        sqlite_count = sqlite_storage.get_cve_count()
        logger.info(f"\nSQLite数据库统计:")
        logger.info(f"  CVE记录数: {sqlite_count}")
        
        if not args.dry_run:
            mysql_count = mysql_storage.get_cve_count()
            logger.info(f"\nMySQL数据库统计:")
            logger.info(f"  CVE记录数: {mysql_count}")
        
        # 确认迁移
        if not args.dry_run:
            response = input(f"\n是否开始迁移 {sqlite_count} 条CVE记录到MySQL? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("迁移已取消")
                return 0
        
        # 开始迁移
        if args.dry_run:
            logger.info("\n[干运行] 将执行以下操作:")
            logger.info(f"  1. 迁移 {sqlite_count} 条CVE记录")
            if not args.skip_stats:
                logger.info("  2. 迁移爬取统计")
            if not args.skip_history:
                logger.info("  3. 迁移全量爬取历史")
            return 0
        
        # 迁移CVE记录
        cve_stats = migrate_cve_records(sqlite_storage, mysql_storage, args.batch_size)
        
        # 迁移爬取统计
        if not args.skip_stats:
            migrate_crawl_stats(sqlite_storage, mysql_storage)
        
        # 迁移全量爬取历史
        if not args.skip_history:
            migrate_full_crawl_history(sqlite_storage, mysql_storage)
        
        # 验证迁移结果
        if args.verify:
            verify_result = verify_migration(sqlite_storage, mysql_storage)
            
            if verify_result['cve_count_match'] and verify_result['latest_date_match']:
                logger.info("\n🎉 迁移验证通过！")
            else:
                logger.warning("\n⚠️  迁移验证发现问题，请检查日志")
        
        # 显示最终统计
        logger.info("\n" + "=" * 60)
        logger.info("迁移完成！")
        logger.info("=" * 60)
        logger.info(f"CVE记录: 总计 {cve_stats['total']}, 成功 {cve_stats['success']}, 失败 {cve_stats['failed']}")
        
        if not args.skip_stats:
            logger.info("爬取统计: 已迁移")
        if not args.skip_history:
            logger.info("全量爬取历史: 已迁移")
        
        logger.info("\n提示: 迁移完成后，可以:")
        logger.info("  1. 在 config/settings.py 中设置 DATABASE_CONFIG['type'] = 'mysql'")
        logger.info("  2. 或使用环境变量: export DB_TYPE=mysql")
        logger.info("  3. 然后使用新的MySQL数据库运行爬虫")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断迁移")
        return 1
    except Exception as e:
        logger.error(f"迁移过程出错: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

