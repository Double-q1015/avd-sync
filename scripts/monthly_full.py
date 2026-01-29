#!/usr/bin/env python3
"""
每月全量爬取和发布脚本
用于服务器 Cron 定时任务
"""
import sys
import os
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
        # 确保环境变量传递给子进程
        env = os.environ.copy()
        project_root = Path(__file__).parent.parent
        main_script = project_root / 'main.py'
        
        result = subprocess.run(
            [sys.executable, '-u', str(main_script), '--mode', 'full', '--optimize'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=14400,  # 4小时超时
            env=env
        )
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            logger.error(f"全量爬取失败 (返回码: {result.returncode})")
            if error_msg:
                logger.error(f"错误信息: {error_msg}")
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
        # 确保环境变量传递给子进程
        env = os.environ.copy()
        
        # 使用当前 Python 解释器和绝对路径
        project_root = Path(__file__).parent.parent
        release_script = project_root / 'scripts' / 'release_database.py'
        
        logger.info(f"执行发布脚本: {release_script}")
        logger.info("注意：上传大文件可能需要 2-3 分钟，请耐心等待...")
        
        # 使用 sys.executable 确保使用相同的 Python 解释器
        # 添加 -u 参数（unbuffered）确保输出实时显示
        result = subprocess.run(
            [
                sys.executable, '-u', str(release_script),
                '--tag', 'latest-full',
                '--name', f'CVE Database - Full Update ({current_month})',
                '--compress',
                '--optimize',
                '--delete-old',
                '--fixed-filename', 'cve_database_full.db.gz'
            ],
            cwd=project_root,
            capture_output=False,  # 不捕获输出，实时显示
            text=True,
            env=env,
            bufsize=0  # 无缓冲，实时输出
        )
        
        if result.returncode != 0:
            logger.error(f"发布失败 (返回码: {result.returncode})")
            return 1
        
        logger.info("✅ 发布成功")
        return 0
        
    except Exception as e:
        logger.error(f"发布失败: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
