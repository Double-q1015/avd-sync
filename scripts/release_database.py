#!/usr/bin/env python3
"""
数据库发布脚本
支持发布到 GitHub 或 Gitee Release
"""
import argparse
import logging
import sys
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# 类型检查忽略（PyGithub 可能未安装）
try:
    from github import Github  # type: ignore
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    Github = None  # type: ignore

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DATABASE_CONFIG, GITHUB_CONFIG
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_file_size(file_path: Path) -> Tuple[int, str]:
    """获取文件大小"""
    size = file_path.stat().st_size
    # 转换为人类可读格式
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return size, f"{size:.2f} {unit}"
        size /= 1024.0
    return size, f"{size:.2f} TB"


def calculate_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 校验和"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compress_database(db_path: Path, method: str = 'gzip') -> Optional[Path]:
    """
    压缩数据库文件
    
    Args:
        db_path: 数据库文件路径
        method: 压缩方法 ('gzip', '7z', 'xz')
    
    Returns:
        压缩后的文件路径，如果失败返回 None
    """
    logger.info(f"开始压缩数据库文件: {db_path}")
    
    if method == 'gzip':
        compressed_path = db_path.with_suffix('.db.gz')
        try:
            subprocess.run(
                ['gzip', '-k', '-9', str(db_path)],
                check=True,
                capture_output=True
            )
            logger.info(f"✅ 压缩完成: {compressed_path}")
            return compressed_path
        except subprocess.CalledProcessError as e:
            logger.error(f"gzip 压缩失败: {e}")
            return None
        except FileNotFoundError:
            logger.error("gzip 未安装，请先安装 gzip")
            return None
    
    elif method == '7z':
        compressed_path = db_path.with_suffix('.db.7z')
        try:
            subprocess.run(
                ['7z', 'a', '-mx=9', '-mmt=4', str(compressed_path), str(db_path)],
                check=True,
                capture_output=True
            )
            logger.info(f"✅ 压缩完成: {compressed_path}")
            return compressed_path
        except subprocess.CalledProcessError as e:
            logger.error(f"7z 压缩失败: {e}")
            return None
        except FileNotFoundError:
            logger.error("7z 未安装，请先安装 p7zip")
            return None
    
    elif method == 'xz':
        compressed_path = db_path.with_suffix('.db.xz')
        try:
            subprocess.run(
                ['xz', '-k', '-9', str(db_path)],
                check=True,
                capture_output=True
            )
            logger.info(f"✅ 压缩完成: {compressed_path}")
            return compressed_path
        except subprocess.CalledProcessError as e:
            logger.error(f"xz 压缩失败: {e}")
            return None
        except FileNotFoundError:
            logger.error("xz 未安装，请先安装 xz")
            return None
    
    else:
        logger.error(f"不支持的压缩方法: {method}")
        return None


def optimize_database(db_path: Path) -> bool:
    """优化数据库（VACUUM）"""
    logger.info("开始优化数据库...")
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("VACUUM")
        conn.close()
        logger.info("✅ 数据库优化完成")
        return True
    except Exception as e:
        logger.warning(f"数据库优化失败: {e}")
        return False


def get_database_stats(db_path: Path) -> dict:
    """获取数据库统计信息"""
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 获取 CVE 数量
        cursor.execute("SELECT COUNT(*) FROM cve_records")
        cve_count = cursor.fetchone()[0]
        
        # 获取最新发布日期
        cursor.execute("SELECT MAX(publish_date) FROM cve_records")
        latest_date = cursor.fetchone()[0]
        
        # 获取爬取统计
        cursor.execute("SELECT COUNT(*) FROM crawl_stats")
        stats_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'cve_count': cve_count,
            'latest_date': latest_date,
            'stats_count': stats_count
        }
    except Exception as e:
        logger.warning(f"获取数据库统计信息失败: {e}")
        return {}


def generate_release_body(db_path: Path, stats: dict, tag: str, compressed: bool = False) -> str:
    """生成 Release 说明"""
    file_size, size_str = get_file_size(db_path)
    
    body = f"""## CVE数据库发布

**发布日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 数据库信息
- **文件**: `{db_path.name}`
- **大小**: {size_str}
- **CVE 数量**: {stats.get('cve_count', 'N/A'):,}
- **最新发布日期**: {stats.get('latest_date', 'N/A')}
- **统计记录数**: {stats.get('stats_count', 'N/A')}

### 文件完整性
SHA256 校验和: `{calculate_sha256(db_path)}`

### 使用方法

1. **下载数据库文件**
   ```bash
   wget https://github.com/{GITHUB_CONFIG['repo_owner']}/{GITHUB_CONFIG['repo_name']}/releases/download/{tag}/{db_path.name}
   ```

2. **如果是压缩文件，先解压**
   ```bash
   gunzip {db_path.name}  # gzip
   # 或
   7z x {db_path.name}    # 7z
   ```

3. **验证文件完整性**
   ```bash
   sha256sum {db_path.name} > {db_path.name}.sha256
   sha256sum -c {db_path.name}.sha256
   ```

4. **使用 SQLite 工具打开**
   ```bash
   sqlite3 {db_path.stem}.db
   ```

### 查询示例

```sql
-- 查询所有CVE
SELECT * FROM cve_records ORDER BY publish_date DESC LIMIT 10;

-- 查询高危漏洞
SELECT * FROM cve_records WHERE danger_level LIKE '%高%' ORDER BY publish_date DESC;

-- 查询特定CVE
SELECT * FROM cve_records WHERE cve = 'CVE-2024-XXXX';

-- 查看统计信息
SELECT * FROM crawl_stats ORDER BY date DESC LIMIT 10;
```

### 注意事项

- 数据库使用 SQLite 3 格式
- 字符编码: UTF-8
- 建议使用 SQLite 3.30+ 版本打开
"""
    
    if compressed:
        body += "\n- ⚠️ 此文件已压缩，请先解压后使用\n"
    
    return body


def release_to_github(
    db_path: Path,
    tag: str,
    name: str,
    body: str,
    token: Optional[str] = None
) -> bool:
    """发布到 GitHub Release"""
    if not GITHUB_AVAILABLE:
        logger.error("PyGithub 未安装，请运行: pip install PyGithub")
        return False
    
    # 获取 token
    if not token:
        token = subprocess.run(
            ['gh', 'auth', 'token'],
            capture_output=True,
            text=True
        ).stdout.strip()
        
        if not token:
            token = subprocess.getenv('GITHUB_TOKEN')
    
    if not token:
        logger.error("未找到 GitHub token，请设置 GITHUB_TOKEN 环境变量或使用 gh auth login")
        return False
    
    try:
        if Github is None:
            logger.error("PyGithub 未正确导入")
            return False
        g = Github(token)
        repo = g.get_repo(f"{GITHUB_CONFIG['repo_owner']}/{GITHUB_CONFIG['repo_name']}")
        
        # 检查 Release 是否已存在
        try:
            release = repo.get_release(tag)
            logger.warning(f"Release {tag} 已存在，将更新...")
            # GitHub API 不支持更新 Release，需要删除后重新创建
            logger.info("删除旧 Release...")
            release.delete_release()
        except Exception:
            pass  # Release 不存在，继续创建
        
        # 创建 Release
        logger.info(f"创建 Release: {tag}")
        release = repo.create_git_release(
            tag=tag,
            name=name,
            message=body,
            draft=False,
            prerelease=False
        )
        
        # 上传文件
        logger.info(f"上传文件: {db_path.name}")
        release.upload_asset(
            path=str(db_path),
            label=db_path.name,
            content_type='application/octet-stream'
        )
        
        # 上传校验和文件
        sha256 = calculate_sha256(db_path)
        checksum_path = db_path.with_suffix('.sha256')
        checksum_path.write_text(f"{sha256}  {db_path.name}\n")
        
        logger.info(f"上传校验和文件: {checksum_path.name}")
        release.upload_asset(
            path=str(checksum_path),
            label=checksum_path.name,
            content_type='text/plain'
        )
        
        logger.info(f"✅ Release 创建成功: {release.html_url}")
        return True
        
    except Exception as e:
        logger.error(f"发布到 GitHub 失败: {e}")
        return False


def release_to_gitee(
    db_path: Path,
    tag: str,
    name: str,
    body: str,
    token: Optional[str] = None
) -> bool:
    """发布到 Gitee Release"""
    try:
        import requests
    except ImportError:
        logger.error("requests 未安装，请运行: pip install requests")
        return False
    
    if not token:
        token = subprocess.getenv('GITEE_TOKEN')
    
    if not token:
        logger.error("未找到 Gitee token，请设置 GITEE_TOKEN 环境变量")
        return False
    
    owner = GITHUB_CONFIG['repo_owner']
    repo = GITHUB_CONFIG['repo_name']
    base_url = f"https://gitee.com/api/v5/repos/{owner}/{repo}"
    headers = {
        'Authorization': f'token {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # 检查 Release 是否已存在
        response = requests.get(f"{base_url}/releases/tags/{tag}", headers=headers)
        if response.status_code == 200:
            logger.warning(f"Release {tag} 已存在，将删除后重新创建...")
            release_id = response.json()['id']
            requests.delete(f"{base_url}/releases/{release_id}", headers=headers)
        
        # 创建 Release
        logger.info(f"创建 Release: {tag}")
        data = {
            'tag_name': tag,
            'name': name,
            'body': body,
            'draft': False,
            'prerelease': False
        }
        response = requests.post(f"{base_url}/releases", headers=headers, json=data)
        response.raise_for_status()
        release = response.json()
        
        # 上传文件（Gitee 需要先获取上传 URL）
        logger.info(f"上传文件: {db_path.name}")
        # Gitee 上传文件需要分两步：先获取上传 URL，再上传文件
        upload_url = f"{base_url}/releases/{release['id']}/attach_files"
        
        with open(db_path, 'rb') as f:
            files = {'file': (db_path.name, f, 'application/octet-stream')}
            upload_response = requests.post(upload_url, headers={'Authorization': f'token {token}'}, files=files)
            upload_response.raise_for_status()
        
        logger.info(f"✅ Release 创建成功: {release['html_url']}")
        return True
        
    except Exception as e:
        logger.error(f"发布到 Gitee 失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='发布数据库到 GitHub/Gitee Release')
    parser.add_argument('--tag', type=str, help='Release 标签（如 v2025.01.26）')
    parser.add_argument('--name', type=str, help='Release 名称')
    parser.add_argument('--db-path', type=str, help='数据库文件路径')
    parser.add_argument('--platform', choices=['github', 'gitee'], default='github', help='发布平台')
    parser.add_argument('--compress', action='store_true', help='压缩数据库文件')
    parser.add_argument('--compress-method', choices=['gzip', '7z', 'xz'], default='gzip', help='压缩方法')
    parser.add_argument('--optimize', action='store_true', help='优化数据库（VACUUM）')
    parser.add_argument('--token', type=str, help='GitHub/Gitee Token（可选，优先使用环境变量）')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("数据库发布工具")
    logger.info("=" * 60)
    
    # 确定数据库路径
    if args.db_path:
        db_path = Path(args.db_path)
    else:
        db_path = DATABASE_CONFIG['db_path']
    
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        return 1
    
    # 优化数据库（可选）
    if args.optimize:
        optimize_database(db_path)
    
    # 压缩数据库（可选）
    release_file = db_path
    if args.compress:
        compressed_path = compress_database(db_path, args.compress_method)
        if compressed_path:
            release_file = compressed_path
        else:
            logger.warning("压缩失败，使用原始文件")
    
    # 获取数据库统计信息
    stats = get_database_stats(db_path)
    
    # 确定标签和名称
    if not args.tag:
        args.tag = f"v{datetime.now().strftime('%Y.%m.%d')}"
    
    if not args.name:
        args.name = f"CVE Database Release - {datetime.now().strftime('%Y-%m-%d')}"
    
    # 生成发布说明
    body = generate_release_body(release_file, stats, args.tag, args.compress)
    
    # 显示信息
    file_size, size_str = get_file_size(release_file)
    logger.info(f"\n发布信息:")
    logger.info(f"  平台: {args.platform}")
    logger.info(f"  标签: {args.tag}")
    logger.info(f"  名称: {args.name}")
    logger.info(f"  文件: {release_file.name}")
    logger.info(f"  大小: {size_str}")
    logger.info(f"  CVE 数量: {stats.get('cve_count', 'N/A'):,}")
    
    # 检查文件大小限制
    if file_size > 2 * 1024 * 1024 * 1024:  # 2GB
        logger.error("文件大小超过 2GB，GitHub/Gitee 不支持")
        return 1
    
    # 发布
    if args.platform == 'github':
        success = release_to_github(release_file, args.tag, args.name, body, args.token)
    else:
        success = release_to_gitee(release_file, args.tag, args.name, body, args.token)
    
    if success:
        logger.info("✅ 发布成功！")
        return 0
    else:
        logger.error("❌ 发布失败！")
        return 1


if __name__ == '__main__':
    sys.exit(main())

