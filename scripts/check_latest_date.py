#!/usr/bin/env python3
"""
查询数据库中最新CVE的发布日期
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db_storage import DatabaseStorage
from config.settings import DATABASE_CONFIG
from utils.logger import setup_logger

logger = setup_logger()


def main():
    """主函数"""
    # 初始化数据库
    db_path = DATABASE_CONFIG['db_path']
    db_storage = DatabaseStorage(db_path)
    
    # 获取最新发布日期
    latest_date = db_storage.get_latest_publish_date()
    
    # 获取CVE总数
    total_count = db_storage.get_cve_count()
    
    # 显示结果
    print("=" * 60)
    print("数据库信息查询")
    print("=" * 60)
    print(f"数据库路径: {db_path}")
    print(f"CVE总数: {total_count}")
    
    if latest_date:
        print(f"最新CVE发布日期: {latest_date}")
        
        # 计算增量爬取的停止日期
        from datetime import datetime, timedelta
        from utils.date_utils import parse_date
        from config.settings import CRAWLER_CONFIG
        
        latest_dt = parse_date(latest_date)
        if latest_dt:
            lookback_days = CRAWLER_CONFIG['incremental']['lookback_days']
            stop_date = latest_dt - timedelta(days=lookback_days)
            print(f"回溯天数: {lookback_days}天")
            print(f"增量爬取停止日期: {stop_date.strftime('%Y-%m-%d')}")
            print(f"  (将爬取所有 >= {stop_date.strftime('%Y-%m-%d')} 的CVE)")
    else:
        print("最新CVE发布日期: 无（数据库为空）")
        print("提示: 数据库为空时，请使用全量爬取模式初始化数据库")
        print("     运行: python main.py --mode full")
    
    # 查询最近10个CVE的日期分布
    print("\n" + "=" * 60)
    print("最近10个CVE的发布日期:")
    print("=" * 60)
    
    with db_storage._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT cve, publish_date, title
            FROM cve_records
            WHERE publish_date != "N/A"
            AND publish_date GLOB "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
            ORDER BY publish_date DESC
            LIMIT 10
        ''')
        
        rows = cursor.fetchall()
        if rows:
            print(f"{'CVE编号':<20} {'发布日期':<12} {'标题'}")
            print("-" * 80)
            for row in rows:
                cve = row[0]
                date = row[1]
                title = row[2][:50] + "..." if len(row[2]) > 50 else row[2]
                print(f"{cve:<20} {date:<12} {title}")
        else:
            print("没有找到有效的CVE记录")
    
    # 查询日期分布统计
    print("\n" + "=" * 60)
    print("日期分布统计（按年份）:")
    print("=" * 60)
    
    with db_storage._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                substr(publish_date, 1, 4) as year,
                COUNT(*) as count
            FROM cve_records
            WHERE publish_date != "N/A"
            AND publish_date GLOB "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
            GROUP BY year
            ORDER BY year DESC
        ''')
        
        rows = cursor.fetchall()
        if rows:
            print(f"{'年份':<10} {'CVE数量':<10} {'占比'}")
            print("-" * 40)
            total = sum(row[1] for row in rows)
            for row in rows:
                year = row[0]
                count = row[1]
                percentage = (count / total * 100) if total > 0 else 0
                print(f"{year:<10} {count:<10} {percentage:.1f}%")
        else:
            print("没有找到有效的CVE记录")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

