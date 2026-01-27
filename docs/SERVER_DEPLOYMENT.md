# 服务器部署指南

本指南介绍如何在服务器上使用 Cron 定时任务自动执行爬取和发布。

## 📋 目录

- [架构说明](#架构说明)
- [前置要求](#前置要求)
- [配置步骤](#配置步骤)
- [Cron 任务配置](#cron-任务配置)
- [监控和日志](#监控和日志)
- [故障排查](#故障排查)

## 架构说明

```
服务器 Cron → 爬取脚本 → 发布脚本 → GitHub API → Release
```

### 工作流程

1. **每日增量任务** (`daily_incremental.py`)
   - 执行增量爬取
   - 优化数据库
   - 压缩数据库
   - 删除旧的 `latest-incremental` Release
   - 创建新的 `latest-incremental` Release
   - 上传：`cve_database_incremental.db.gz` + SHA256

2. **每月全量任务** (`monthly_full.py`)
   - 执行全量爬取
   - 优化数据库
   - 压缩数据库
   - 删除旧的 `latest-full` Release
   - 创建新的 `latest-full` Release
   - 上传：`cve_database_full.db.gz` + SHA256

## 前置要求

### 1. 服务器环境

- Python 3.9+
- 已安装项目依赖（`pip install -r requirements.txt`）
- 足够的磁盘空间（建议至少 5GB）
- 稳定的网络连接

### 2. GitHub Token

获取 GitHub Personal Access Token：

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：`repo`（完整仓库权限）
4. 生成并复制 Token

### 3. 配置 GitHub 仓库信息

在 `config/settings.py` 中设置：

```python
GITHUB_CONFIG = {
    'repo_owner': 'your-username',  # 你的 GitHub 用户名
    'repo_name': 'avd-sync',        # 仓库名
    ...
}
```

或使用环境变量：

```bash
export GITHUB_REPO_OWNER=your-username
export GITHUB_REPO_NAME=avd-sync
```

## 配置步骤

### 步骤 1: 设置环境变量

在服务器上设置 GitHub Token：

```bash
# 临时设置（当前会话）
export GITHUB_TOKEN=your_github_token_here

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export GITHUB_TOKEN=your_github_token_here' >> ~/.bashrc
source ~/.bashrc
```

### 步骤 2: 测试脚本

手动测试脚本是否正常工作：

```bash
# 测试增量脚本
cd /path/to/avd-sync
python3 scripts/daily_incremental.py

# 测试全量脚本（需要较长时间）
python3 scripts/monthly_full.py
```

### 步骤 3: 配置 Cron 任务

#### 方法一：使用 crontab（推荐）

```bash
# 编辑 Cron 任务
crontab -e

# 添加以下内容（修改路径为你的实际路径）
```

参考 `scripts/crontab.example` 文件，或使用以下配置：

```cron
# 设置环境变量
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
GITHUB_TOKEN=your_github_token_here

# 每日增量爬取和发布（每天 08:00 执行，北京时间）
0 8 * * * cd /path/to/avd-sync && /usr/bin/python3 scripts/daily_incremental.py >> logs/cron_incremental.log 2>&1

# 每月全量爬取和发布（每月1号 10:00 执行，北京时间）
0 10 1 * * cd /path/to/avd-sync && /usr/bin/python3 scripts/monthly_full.py >> logs/cron_full.log 2>&1
```

#### 方法二：使用 systemd timer（可选）

创建 systemd 服务文件：

```ini
# /etc/systemd/system/avd-sync-incremental.service
[Unit]
Description=AVD Sync Daily Incremental Crawl
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/avd-sync
Environment="GITHUB_TOKEN=your_token"
ExecStart=/usr/bin/python3 /path/to/avd-sync/scripts/daily_incremental.py
StandardOutput=append:/path/to/avd-sync/logs/cron_incremental.log
StandardError=append:/path/to/avd-sync/logs/cron_incremental.log
```

创建 timer 文件：

```ini
# /etc/systemd/system/avd-sync-incremental.timer
[Unit]
Description=Run AVD Sync Incremental Daily

[Timer]
OnCalendar=daily
OnCalendar=08:00
Timezone=Asia/Shanghai

[Install]
WantedBy=timers.target
```

启用 timer：

```bash
sudo systemctl enable avd-sync-incremental.timer
sudo systemctl start avd-sync-incremental.timer
```

## Cron 任务配置

### 时间设置

| 任务 | Cron 表达式 | 说明 |
|------|------------|------|
| 每日增量 | `0 8 * * *` | 每天 08:00（北京时间） |
| 每月全量 | `0 10 1 * *` | 每月1号 10:00（北京时间） |

### 时区说明

Cron 使用系统时区。如果服务器使用 UTC，需要调整时间：

- 北京时间 08:00 = UTC 00:00
- 北京时间 10:00 = UTC 02:00

### 路径配置

确保以下路径正确：

1. **项目路径**：`/path/to/avd-sync`（修改为实际路径）
2. **Python 路径**：`/usr/bin/python3`（使用 `which python3` 查看）
3. **日志路径**：`logs/cron_*.log`（会自动创建）

## 监控和日志

### 查看日志

```bash
# 增量任务日志
tail -f logs/cron_incremental.log

# 全量任务日志
tail -f logs/cron_full.log

# 爬虫日志
tail -f logs/crawler.log
```

### 检查 Cron 任务

```bash
# 查看当前 Cron 任务
crontab -l

# 查看 Cron 执行日志（Linux）
grep CRON /var/log/syslog

# 查看 Cron 执行日志（macOS）
grep cron /var/log/system.log
```

### 验证 Release

访问 GitHub Release 页面，检查：

- `latest-incremental` Release 是否每天更新
- `latest-full` Release 是否每月更新
- 文件是否正确上传（数据库文件 + SHA256）

## 故障排查

### 问题 1: Cron 任务未执行

**检查**：
```bash
# 检查 Cron 服务是否运行
sudo systemctl status cron  # Linux
sudo launchctl list | grep cron  # macOS

# 检查 Cron 任务语法
crontab -l
```

**解决**：
- 确保 Cron 服务正在运行
- 检查 Cron 任务语法是否正确
- 检查文件路径和权限

### 问题 2: 脚本执行失败

**检查日志**：
```bash
tail -n 100 logs/cron_incremental.log
```

**常见原因**：
- GitHub Token 未设置或无效
- Python 路径不正确
- 项目路径不正确
- 依赖未安装

### 问题 3: GitHub API 错误

**错误信息**：
```
未找到 GitHub token，请设置 GITHUB_TOKEN 环境变量
```

**解决**：
- 确保 `GITHUB_TOKEN` 环境变量已设置
- 在 Cron 任务中显式设置环境变量
- 检查 Token 是否有 `repo` 权限

### 问题 4: 数据库文件不存在

**错误信息**：
```
数据库文件不存在: /path/to/cve_database.db
```

**解决**：
- 确保先执行一次爬取（手动或通过 Cron）
- 检查数据库路径配置
- 检查文件权限

### 问题 5: 发布失败

**检查**：
- GitHub Token 是否有效
- 仓库配置是否正确（`repo_owner`, `repo_name`）
- 网络连接是否正常
- GitHub API 速率限制

## 最佳实践

1. **测试优先**：在配置 Cron 前，先手动测试脚本
2. **日志监控**：定期检查日志，及时发现问题
3. **备份数据**：定期备份数据库文件
4. **资源监控**：监控服务器 CPU、内存、磁盘使用情况
5. **错误通知**：可以配置邮件或 Webhook 通知（可选）

## 相关文件

- `scripts/daily_incremental.py` - 每日增量脚本
- `scripts/monthly_full.py` - 每月全量脚本
- `scripts/release_database.py` - 发布脚本
- `scripts/crontab.example` - Cron 配置示例
- `config/settings.py` - 配置文件

## 参考链接

- [Cron 语法说明](https://crontab.guru/)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitHub Releases API](https://docs.github.com/en/rest/releases)
