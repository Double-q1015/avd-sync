#!/usr/bin/env python3
"""
每月全量爬取和发布脚本
用于服务器 Cron 定时任务
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DATABASE_CONFIG
from utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """执行全量爬取并发布到 GitHub"""
    logger.info("=" * 60)
    logger.info("每月全量爬取和发布")
    logger.info("=" * 60)
    
    # 1. 执行全量爬取
    logger.info("开始全量爬取...")
    try:
        result = subprocess.run(
            ['python', 'main.py', '--mode', 'full', '--optimize'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=14400  # 4小时超时
        )
        
        if result.returncode != 0:
            logger.error(f"全量爬取失败: {result.stderr}")
            return 1
        
        logger.info("✅ 全量爬取完成")
    except subprocess.TimeoutExpired:
        logger.error("全量爬取超时（超过4小时）")
        return 1
    except Exception as e:
        logger.error(f"执行爬取失败: {e}")
        return 1
    
    # 2. 检查数据库文件
    db_path = DATABASE_CONFIG['db_path']
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        return 1
    
    # 3. 发布到 GitHub Release
    logger.info("开始发布到 GitHub Release...")
    current_month = datetime.now().strftime('%Y-%m')
    try:
        result = subprocess.run(
            [
                'python', 'scripts/release_database.py',
                '--tag', 'latest-full',
                '--name', f'CVE Database - Full Update ({current_month})',
                '--compress',
                '--optimize',
                '--delete-old',
                '--fixed-filename', 'cve_database_full.db.gz'
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"发布失败: {result.stderr}")
            return 1
        
        logger.info("✅ 发布成功")
        logger.info(result.stdout)
        return 0
        
    except Exception as e:
        logger.error(f"发布失败: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
