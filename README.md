# AVD Sync

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

一个用于同步阿里云漏洞库（avd.aliyun.com）CVE漏洞信息的Python工具，数据存储在SQLite数据库中，并支持每日自动同步和发布到GitHub Releases。

## 📋 目录

- [特性](#-特性)
- [快速开始](#-快速开始)
- [使用说明](#-使用说明)
- [数据库结构](#-数据库结构)
- [GitHub Actions](#-github-actions-自动化)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

## ✨ 特性

- 🕷️ **自动化爬取**: 自动爬取阿里云漏洞库的CVE信息
- 💾 **SQLite存储**: 使用SQLite数据库存储，支持高效查询
- 🔄 **智能更新策略**: 
  - **每日增量爬取**: 只爬取新数据，高效快速
  - **每月全量爬取**: 重新爬取所有数据，确保历史数据更新
- 📊 **数据统计**: 记录爬取统计信息和全量爬取历史
- 🔍 **去重处理**: 自动处理重复数据，支持增量更新
- 📝 **完整日志**: 详细的日志记录，便于调试和监控

## 📁 项目结构

```
avd-sync/
├── config/              # 配置文件
│   └── settings.py
├── core/                # 核心模块
│   ├── browser.py      # 浏览器管理
│   ├── parser.py       # HTML解析
│   └── crawler.py      # 爬虫逻辑
├── models/             # 数据模型
│   └── cve.py
├── storage/             # 存储模块
│   └── db_storage.py   # SQLite存储
├── utils/              # 工具模块
│   ├── logger.py       # 日志工具
│   ├── retry.py        # 重试装饰器
│   └── date_utils.py   # 日期工具
├── .github/
│   └── workflows/
│       └── daily-release.yml  # GitHub Actions工作流
├── main.py             # 主程序入口
├── requirements.txt    # 依赖列表
└── README.md          # 项目文档
```

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `config/settings.py` 文件，根据需要修改配置：

```python
# 爬虫配置
CRAWLER_CONFIG = {
    'start_page': 1,
    'request_delay': 0.1,  # 请求延迟（秒）
    'incremental': {
        'lookback_days': 7,  # 增量爬取回溯天数
    },
}

# 浏览器配置
BROWSER_CONFIG = {
    'headless': False,  # 是否无头模式
    'no_sandbox': True,
}
```

### 运行爬虫

```bash
# 自动模式（推荐）：自动判断执行增量或全量爬取
python main.py --mode auto

# 增量爬取：只爬取新数据（从数据库最新日期开始）
python main.py --mode incremental

# 全量爬取：重新爬取所有数据
python main.py --mode full

# 爬取后优化数据库
python main.py --mode incremental --optimize

# 指定数据库路径
python main.py --mode incremental --db-path /path/to/database.db
```

### 爬取模式说明

#### 增量爬取（Incremental）
- **用途**: 日常更新，快速获取最新CVE
- **策略**: 从数据库最新CVE发布日期开始，向前回溯7天（可配置）防止遗漏
- **优势**: 速度快，资源消耗少
- **适用场景**: 每日自动更新

#### 全量爬取（Full）
- **用途**: 确保历史数据完整性，更新已存在的CVE信息
- **策略**: 从第一页开始爬取所有数据，覆盖到配置的日期阈值
- **优势**: 数据完整，可更新历史CVE信息
- **适用场景**: 每月执行一次

#### 自动模式（Auto）
- **用途**: 智能判断执行增量还是全量
- **策略**: 检查距离上次全量爬取的时间，超过30天（可配置）则执行全量，否则执行增量
- **优势**: 无需手动判断，自动选择最优策略

## 📊 数据库结构

### cve_records 表

存储CVE详细信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| cve | TEXT | CVE编号（唯一） |
| title | TEXT | 漏洞标题 |
| product | TEXT | 受影响产品 |
| danger_level | TEXT | 危险级别 |
| description | TEXT | 漏洞描述 |
| impact_range | TEXT | 影响范围 |
| security_versions | TEXT | 安全版本 |
| solution_advice | TEXT | 解决建议 |
| reference_links | TEXT | 参考链接（逗号分隔） |
| exploitability | TEXT | 利用情况 |
| package | TEXT | 补丁情况 |
| publish_date | TEXT | 披露时间 |
| cwe | TEXT | CWE编号 |
| score | TEXT | 评分 |
| crawl_date | TEXT | 爬取日期 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### crawl_stats 表

存储爬取统计信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| crawl_date | DATE | 爬取日期（唯一） |
| total_cves | INTEGER | 总CVE数 |
| new_cves | INTEGER | 新增CVE数 |
| updated_cves | INTEGER | 更新CVE数 |
| crawl_mode | TEXT | 爬取模式（incremental/full） |

### full_crawl_history 表

存储全量爬取历史：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| crawl_date | DATE | 爬取日期（唯一） |
| total_cves | INTEGER | 总CVE数 |
| duration_seconds | INTEGER | 爬取耗时（秒） |
| created_at | TIMESTAMP | 创建时间 |

## 🔍 数据库查询示例

```sql
-- 查询最新的10个CVE
SELECT cve, title, danger_level, publish_date 
FROM cve_records 
ORDER BY publish_date DESC 
LIMIT 10;

-- 查询高危漏洞
SELECT cve, title, danger_level, publish_date 
FROM cve_records 
WHERE danger_level LIKE '%高%' 
ORDER BY publish_date DESC;

-- 查询特定CVE
SELECT * FROM cve_records WHERE cve = 'CVE-2024-XXXX';

-- 查询统计信息
SELECT * FROM crawl_stats ORDER BY crawl_date DESC;

-- 查看全量爬取历史
SELECT * FROM full_crawl_history ORDER BY crawl_date DESC;

-- 查看增量爬取记录
SELECT * FROM crawl_stats WHERE crawl_mode = 'incremental' ORDER BY crawl_date DESC;
```

### 使用发布的数据库

1. 访问 [Releases](https://github.com/Double-q1015/avd-sync/releases)
2. 选择需要的版本：
   - **增量更新**: 标签以 `incremental-` 开头，适合日常使用
   - **全量更新**: 标签以 `full-` 开头，数据最完整
3. 下载 `cve_database.db` 文件
4. 使用SQLite工具打开数据库进行查询

## 📝 日志

日志文件保存在 `logs/crawler.log`，支持自动轮转（最大10MB，保留5个备份）。

## ⚙️ 配置说明

### 爬虫配置

- `start_page`: 起始页码
- `request_delay`: 请求之间的延迟时间（秒）
- `max_retries`: 最大重试次数
- `retry_delay`: 重试延迟时间（秒）
- `incremental.lookback_days`: 增量爬取时向前回溯的天数（默认7天，防止遗漏）
- `full_crawl.interval_days`: 全量爬取间隔天数（默认30天）

### 浏览器配置

- `headless`: 是否使用无头模式（不显示浏览器窗口）
- `no_sandbox`: 是否关闭沙箱模式（解决某些环境下的问题）
- `timeout`: 页面加载超时时间（秒）

## 🛠️ 开发

### 添加新功能

项目采用模块化设计，易于扩展：

- **添加新的解析器**: 在 `core/parser.py` 中添加新的解析方法
- **添加新的存储方式**: 在 `storage/` 目录下创建新的存储类
- **添加新的工具**: 在 `utils/` 目录下添加工具函数

### 代码规范

- 使用类型提示
- 遵循PEP 8代码风格
- 添加适当的文档字符串
- 使用日志而不是print

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🤝 贡献

我们欢迎所有形式的贡献！请查看我们的 [贡献指南](CONTRIBUTING.md) 了解如何参与项目。

### 贡献方式

- 🐛 [报告 Bug](https://github.com/Double-q1015/avd-sync/issues/new?template=bug_report.md)
- 💡 [提出功能建议](https://github.com/Double-q1015/avd-sync/issues/new?template=feature_request.md)
- 📝 [改进文档](CONTRIBUTING.md#文档改进)
- 🔧 [提交代码](CONTRIBUTING.md#提交代码)

### 行为准则

请阅读并遵守我们的 [行为准则](CODE_OF_CONDUCT.md)。

## ⚠️ 注意事项

1. 请遵守网站的robots.txt和使用条款
2. 合理设置请求延迟，避免对服务器造成压力
3. 数据库文件可能较大，GitHub Release有文件大小限制（建议<100MB）
4. 定期备份数据库文件

## 📧 联系方式

- 📮 提交 [Issue](https://github.com/Double-q1015/avd-sync/issues)
- 📖 查看 [文档](docs/)
- 🤝 查看 [贡献指南](CONTRIBUTING.md)

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

## 📊 项目统计

- ⭐ 如果这个项目对你有帮助，请给个 Star！
- 🍴 Fork 本项目
- 📢 分享给其他开发者

---

**注意**: 请遵守网站的 robots.txt 和使用条款，合理使用爬虫工具。

