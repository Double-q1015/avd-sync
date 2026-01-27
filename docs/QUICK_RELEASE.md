# 快速发布数据库到 GitHub Release

本指南将帮助你快速将当前数据库推送到 GitHub Release。

## 📋 前置要求

1. **已安装依赖**
   ```bash
   pip install PyGithub requests
   ```

2. **已配置 GitHub Token**
   
   **方法一：使用环境变量（最简单，推荐）**
   ```bash
   # 1. 获取 GitHub Token
   #    访问 https://github.com/settings/tokens
   #    点击 "Generate new token (classic)"
   #    选择权限：`repo`（完整仓库权限）
   #    生成并复制 Token
   
   # 2. 设置环境变量
   export GITHUB_TOKEN=your_github_token_here
   
   # 3. 验证（可选）
   echo $GITHUB_TOKEN
   ```
   
   **方法二：使用 GitHub CLI（可选）**
   ```bash
   # 安装 GitHub CLI（如果未安装）
   brew install gh  # macOS
   # 或访问 https://cli.github.com/
   
   # 登录
   gh auth login
   ```
   
   **如何获取 Token：**
   1. 访问 https://github.com/settings/tokens
   2. 点击 "Generate new token (classic)"
   3. 选择权限：`repo`（完整仓库权限）
   4. 生成并复制 Token
   5. 设置环境变量：`export GITHUB_TOKEN=你的token`

## 🚀 快速开始

### 步骤 1: 确认配置

检查 `config/settings.py` 中的配置：

```python
GITHUB_CONFIG = {
    'repo_owner': 'Double-q1015',  # 你的 GitHub 用户名
    'repo_name': 'avd-sync',       # 仓库名
    ...
}
```

### 步骤 2: 运行发布脚本

#### 基本发布（最简单）

```bash
# 使用默认设置发布（标签自动生成：v2025.01.27）
python scripts/release_database.py
```

#### 指定版本标签

```bash
# 使用自定义标签
python scripts/release_database.py --tag v1.0.0
```

#### 压缩后发布（推荐）

```bash
# 使用 gzip 压缩（文件更小，下载更快）
python scripts/release_database.py --compress

# 或使用 7z 压缩（压缩率更高）
python scripts/release_database.py --compress --compress-method 7z
```

#### 优化数据库后发布

```bash
# 先优化数据库（VACUUM），再发布
python scripts/release_database.py --optimize --compress
```

#### 完整示例

```bash
# 优化 + 压缩 + 自定义标签
python scripts/release_database.py \
    --tag v2025.01.27 \
    --name "CVE Database - 2025-01-27" \
    --optimize \
    --compress \
    --compress-method gzip
```

## 📝 脚本参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--tag` | Release 标签 | `--tag v1.0.0` |
| `--name` | Release 名称 | `--name "CVE Database Release"` |
| `--db-path` | 数据库文件路径 | `--db-path /path/to/database.db` |
| `--platform` | 发布平台 | `--platform github` 或 `--platform gitee` |
| `--compress` | 压缩数据库 | `--compress` |
| `--compress-method` | 压缩方法 | `--compress-method gzip` (gzip/7z/xz) |
| `--optimize` | 优化数据库 | `--optimize` |
| `--token` | GitHub Token | `--token your_token` |

## ✅ 发布成功示例

```
============================================================
数据库发布工具
============================================================
开始优化数据库...
✅ 数据库优化完成
开始压缩数据库文件: data/cve_database.db
✅ 压缩完成: data/cve_database.db.gz

发布信息:
  平台: github
  标签: v2025.01.27
  名称: CVE Database Release - 2025-01-27
  文件: cve_database.db.gz
  大小: 240.50 MB
  CVE 数量: 328,458

创建 Release: v2025.01.27
上传文件: cve_database.db.gz
上传校验和文件: cve_database.db.gz.sha256
✅ Release 创建成功: https://github.com/Double-q1015/avd-sync/releases/tag/v2025.01.27
✅ 发布成功！
```

## 🔍 验证发布

1. **访问 Release 页面**
   ```
   https://github.com/Double-q1015/avd-sync/releases
   ```

2. **检查文件**
   - 数据库文件（或压缩文件）
   - SHA256 校验和文件

3. **下载测试**
   ```bash
   # 下载数据库
   wget https://github.com/Double-q1015/avd-sync/releases/download/v2025.01.27/cve_database.db.gz
   
   # 解压
   gunzip cve_database.db.gz
   
   # 验证校验和
   sha256sum -c cve_database.db.gz.sha256
   ```

## ⚠️ 常见问题

### 1. Token 未找到

**错误**：
```
未找到 GitHub token，请设置 GITHUB_TOKEN 环境变量或使用 gh auth login
```

**解决**：
```bash
# 方法一：使用 GitHub CLI
gh auth login

# 方法二：设置环境变量
export GITHUB_TOKEN=your_token_here
```

### 2. 仓库不存在或无权访问

**错误**：
```
404 {"message":"Not Found"}
```

**解决**：
- 确认 `repo_owner` 和 `repo_name` 配置正确
- 确认 Token 有 `repo` 权限
- 确认仓库已创建

### 3. 文件过大

**错误**：
```
文件大小超过 2GB，GitHub/Gitee 不支持
```

**解决**：
- 使用 `--compress` 压缩文件
- 或使用 `--optimize` 优化数据库
- 考虑分片上传（需要修改脚本）

### 4. Release 已存在

脚本会自动处理：
- 如果标签已存在，会删除旧 Release 后重新创建
- 或使用新的标签创建 Release

## 📊 发布统计

发布后，Release 说明会自动包含：
- 发布日期和时间
- 数据库文件大小
- CVE 数量
- 最新发布日期
- 统计记录数
- SHA256 校验和
- 使用说明和查询示例

## 🔄 更新已存在的 Release

如果需要更新已存在的 Release：

1. **删除旧 Release**（在 GitHub 网页上）
2. **重新运行脚本**（使用相同标签）

或使用新标签创建新 Release。

## 💡 最佳实践

1. **使用压缩**：减少下载时间
   ```bash
   python scripts/release_database.py --compress
   ```

2. **优化数据库**：减少文件大小
   ```bash
   python scripts/release_database.py --optimize --compress
   ```

3. **语义化版本**：使用清晰的标签
   ```bash
   python scripts/release_database.py --tag v2025.01.27
   ```

4. **定期发布**：建议每天或每周发布一次

## 📚 更多信息

- 详细文档：查看 [docs/RELEASE.md](RELEASE.md)
- 脚本源码：`scripts/release_database.py`
- GitHub Releases API：https://docs.github.com/en/rest/releases
