# 数据库发布到 GitHub/Gitee Release 指南

本文档介绍如何将打包的数据库推送到 GitHub 或 Gitee 的 Release 中。

## 📋 目录

- [方案概述](#方案概述)
- [方案一：使用脚本手动发布](#方案一使用脚本手动发布)
- [方案二：GitHub Actions 自动发布](#方案二github-actions-自动发布)
- [方案三：Gitee 发布](#方案三gitee-发布)
- [数据库压缩优化](#数据库压缩优化)
- [常见问题](#常见问题)

## 方案概述

### 当前数据库信息
- **数据库文件**: `data/cve_database.db`
- **文件大小**: 约 342MB（未压缩）
- **数据库类型**: SQLite

### 发布方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **脚本手动发布** | 灵活、可控、支持压缩 | 需要手动执行 | 一次性发布、测试 |
| **GitHub Actions** | 自动化、定时发布 | 需要先运行爬虫 | 持续集成、自动更新 |
| **Gitee 发布** | 国内访问快 | 需要单独配置 | 国内用户 |

## 方案一：使用脚本手动发布

### 1. 安装依赖

```bash
# GitHub CLI（推荐）
brew install gh  # macOS
# 或访问 https://cli.github.com/

# 或使用 Python 库
pip install PyGithub requests
```

### 2. 配置 GitHub Token

```bash
# 使用 GitHub CLI 登录
gh auth login

# 或设置环境变量
export GITHUB_TOKEN=your_github_token_here
```

### 3. 运行发布脚本

```bash
# 基本发布
python scripts/release_database.py

# 指定版本标签
python scripts/release_database.py --tag v2025.01.26

# 压缩后发布（推荐，文件更小）
python scripts/release_database.py --compress

# 发布到 Gitee
python scripts/release_database.py --platform gitee
```

### 脚本功能

- ✅ 自动压缩数据库（可选）
- ✅ 生成发布说明
- ✅ 检查文件大小
- ✅ 支持 GitHub 和 Gitee
- ✅ 错误处理和重试

## 方案二：GitHub Actions 自动发布

### 工作流程

项目已包含以下 GitHub Actions 工作流：

1. **`daily-release.yml`** - 每日发布
   - 定时：每天 UTC 00:00（北京时间 08:00）
   - 流程：运行爬虫 → 优化数据库 → 创建 Release

2. **`monthly-full.yml`** - 每月全量发布
   - 定时：每月1号 UTC 02:00（北京时间 10:00）
   - 流程：全量爬取 → 优化数据库 → 创建 Release

3. **`daily-incremental.yml`** - 每日增量发布
   - 定时：每天 UTC 00:00
   - 流程：增量爬取 → 创建 Release

### 配置说明

#### 1. 设置仓库信息

在 `config/settings.py` 中配置：

```python
GITHUB_CONFIG = {
    'repo_owner': 'your-username',  # GitHub 用户名或组织名
    'repo_name': 'avd-sync',       # 仓库名
    'release_tag_prefix': 'v',     # 标签前缀
    'db_filename': 'cve_database.db',
}
```

#### 2. 启用 GitHub Actions

- 确保 `.github/workflows/` 目录下的工作流文件存在
- 在 GitHub 仓库设置中启用 Actions
- 确保有足够的 Actions 配额（免费账户每月 2000 分钟）

#### 3. 手动触发

在 GitHub 仓库页面：
1. 进入 **Actions** 标签
2. 选择对应的工作流
3. 点击 **Run workflow** 按钮

### 优化建议

#### 压缩数据库

GitHub Release 单个文件限制为 2GB，但建议压缩以减少下载时间：

```yaml
- name: Compress database
  run: |
    gzip -k data/cve_database.db
    # 或使用 7z（压缩率更高）
    # 7z a -mx=9 cve_database.db.7z data/cve_database.db
```

#### 分片上传（如果文件过大）

如果数据库文件超过 100MB，考虑分片：

```yaml
- name: Split database
  run: |
    split -b 50M data/cve_database.db cve_database.db.part
```

## 方案三：Gitee 发布

### 1. 安装 Gitee CLI（可选）

```bash
# 使用 pip 安装
pip install gitee-cli
```

### 2. 配置 Gitee Token

```bash
export GITEE_TOKEN=your_gitee_token_here
```

在 Gitee 设置中创建 Personal Access Token：
- 访问：https://gitee.com/profile/personal_access_tokens
- 权限：需要 `projects` 和 `releases` 权限

### 3. 使用脚本发布

```bash
python scripts/release_database.py --platform gitee --tag v2025.01.26
```

### 4. Gitee Actions（如果支持）

Gitee 也支持类似 GitHub Actions 的 CI/CD，但配置方式略有不同。

## 数据库压缩优化

### 压缩方案对比

| 方法 | 压缩率 | 速度 | 工具 |
|------|--------|------|------|
| **gzip** | ~30% | 快 | 系统自带 |
| **7z** | ~40% | 中 | 需安装 |
| **xz** | ~45% | 慢 | 需安装 |
| **SQLite VACUUM** | ~20% | 快 | SQLite 内置 |

### 推荐方案

```bash
# 1. 先优化数据库（VACUUM）
sqlite3 data/cve_database.db "VACUUM;"

# 2. 使用 gzip 压缩（平衡压缩率和速度）
gzip -k -9 data/cve_database.db

# 3. 或使用 7z（更高压缩率）
7z a -mx=9 -mmt=4 cve_database.db.7z data/cve_database.db
```

### 压缩效果预估

- **原始大小**: ~342MB
- **gzip 压缩后**: ~240MB（约 30% 压缩率）
- **7z 压缩后**: ~205MB（约 40% 压缩率）

## 常见问题

### Q1: GitHub Release 文件大小限制？

**A**: 
- 单个文件最大：**2GB**
- 单个 Release 总大小：**无限制**（但建议不超过 10GB）
- 推荐：压缩后保持在 500MB 以内

### Q2: 如何更新已存在的 Release？

**A**: 
- GitHub/Gitee 不支持直接更新 Release
- 需要创建新的 Release（使用新的标签）
- 或删除旧 Release 后重新创建

### Q3: 如何自动生成发布说明？

**A**: 
脚本会自动生成，包含：
- 发布日期
- 数据库统计信息（CVE 数量等）
- 文件大小
- 使用说明

### Q4: 如何验证发布的文件完整性？

**A**: 
```bash
# 生成校验和
sha256sum cve_database.db > cve_database.db.sha256

# 验证
sha256sum -c cve_database.db.sha256
```

### Q5: 如何下载和使用发布的数据库？

**A**: 
```bash
# 1. 从 Release 下载
wget https://github.com/your-username/avd-sync/releases/download/v2025.01.26/cve_database.db

# 2. 如果是压缩文件，先解压
gunzip cve_database.db.gz

# 3. 使用 SQLite 工具打开
sqlite3 cve_database.db

# 4. 查询数据
sqlite3 cve_database.db "SELECT COUNT(*) FROM cve_records;"
```

### Q6: 如何设置自动发布频率？

**A**: 
修改 `.github/workflows/daily-release.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # 每天
  - cron: '0 0 * * 0'  # 每周日
  - cron: '0 0 1 * *'  # 每月1号
```

## 最佳实践

1. **定期发布**: 建议每天或每周发布一次
2. **压缩文件**: 使用 gzip 或 7z 压缩，减少下载时间
3. **版本标签**: 使用语义化版本（如 `v2025.01.26`）
4. **发布说明**: 包含详细的更新内容和统计信息
5. **校验和**: 提供 SHA256 校验和文件，确保文件完整性
6. **保留历史**: 保留最近 30 天的 Release，方便回滚

## 相关文件

- `scripts/release_database.py` - 发布脚本
- `.github/workflows/daily-release.yml` - 每日发布工作流
- `.github/workflows/monthly-full.yml` - 每月全量发布工作流
- `config/settings.py` - 配置文件

## 参考链接

- [GitHub Releases API](https://docs.github.com/en/rest/releases)
- [Gitee Releases API](https://gitee.com/api/v5/swagger#/postV5ReposOwnerRepoReleases)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [SQLite VACUUM](https://www.sqlite.org/lang_vacuum.html)

