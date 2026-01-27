# SQLite到MySQL数据迁移指南

## 概述

本迁移脚本可以将SQLite数据库中的所有数据迁移到MySQL数据库，包括：
- CVE记录（cve_records表）
- 爬取统计（crawl_stats表）
- 全量爬取历史（full_crawl_history表）

## 前置要求

### 1. 安装依赖

```bash
# 安装SQLAlchemy（如果还没安装）
pip install sqlalchemy

# 安装MySQL驱动（二选一）
pip install pymysql
# 或
pip install mysql-connector-python
```

### 2. 配置MySQL

在 `config/settings.py` 中配置MySQL连接信息：

```python
'mysql': {
    'host': 'localhost',     # MySQL服务器地址
    'port': 3306,
    'user': 'your_user',     # 用户名
    'password': 'your_password',  # 密码
    'database': 'cve_db',    # 数据库名
    'driver': 'pymysql',     # 驱动：'pymysql' 或 'mysqlconnector'
}
```

或使用环境变量：

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=your_user
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=cve_db
export MYSQL_DRIVER=pymysql
```

### 3. 创建MySQL数据库

```sql
CREATE DATABASE cve_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 使用方法

### 基本用法

```bash
# 使用默认配置迁移
python scripts/migrate_sqlite_to_mysql.py

# 指定SQLite数据库路径
python scripts/migrate_sqlite_to_mysql.py --sqlite-path /path/to/cve_database.db

# 干运行模式（不实际迁移，只显示将要执行的操作）
python scripts/migrate_sqlite_to_mysql.py --dry-run
```

### 高级选项

```bash
# 自定义批量大小（默认100）
python scripts/migrate_sqlite_to_mysql.py --batch-size 200

# 跳过爬取统计迁移
python scripts/migrate_sqlite_to_mysql.py --skip-stats

# 跳过全量爬取历史迁移
python scripts/migrate_sqlite_to_mysql.py --skip-history

# 迁移后验证数据
python scripts/migrate_sqlite_to_mysql.py --verify

# 组合使用
python scripts/migrate_sqlite_to_mysql.py --batch-size 200 --verify
```

## 迁移流程

### 1. 准备阶段

- 检查SQLite数据库是否存在
- 检查MySQL配置是否完整
- 连接MySQL数据库
- 显示数据统计信息

### 2. 迁移阶段

#### CVE记录迁移
- 分批读取SQLite中的CVE记录
- 批量插入/更新到MySQL
- 显示实时进度条
- 记录成功/失败统计

#### 爬取统计迁移
- 读取所有爬取统计记录
- 插入/更新到MySQL

#### 全量爬取历史迁移
- 读取所有全量爬取历史
- 插入/更新到MySQL

### 3. 验证阶段（可选）

- 比较CVE数量
- 比较最新发布日期
- 随机抽样验证数据一致性

## 示例输出

```
============================================================
SQLite到MySQL数据迁移工具
============================================================
SQLite数据库路径: /path/to/cve_database.db
MySQL配置:
  主机: localhost:3306
  数据库: cve_db
  用户: your_user
✅ MySQL连接成功

SQLite数据库统计:
  CVE记录数: 328458

MySQL数据库统计:
  CVE记录数: 0

是否开始迁移 328458 条CVE记录到MySQL? (yes/no): yes

开始迁移CVE记录...
SQLite数据库中共有 328458 条CVE记录
MySQL数据库中已有 0 条CVE记录
迁移CVE记录: 100%|████████████| 328458/328458 [15:30<00:00, 352.5条/s]
CVE记录迁移完成: 总计 328458, 成功 328458, 失败 0

开始迁移爬取统计...
爬取统计迁移完成: 15 条记录

开始迁移全量爬取历史...
全量爬取历史迁移完成: 3 条记录

开始验证迁移结果...
SQLite CVE数量: 328458
MySQL CVE数量: 328458
✅ CVE数量匹配，迁移成功
SQLite最新发布日期: 2026-01-26
MySQL最新发布日期: 2026-01-26
✅ 最新发布日期匹配
随机抽样验证...
抽样验证: 10/10 条记录匹配

============================================================
迁移完成！
============================================================
CVE记录: 总计 328458, 成功 328458, 失败 0
爬取统计: 已迁移
全量爬取历史: 已迁移
```

## 性能优化

### 批量大小调整

根据数据量和网络情况调整批量大小：

```bash
# 小批量（适合网络不稳定）
python scripts/migrate_sqlite_to_mysql.py --batch-size 50

# 大批量（适合网络稳定，数据量大）
python scripts/migrate_sqlite_to_mysql.py --batch-size 500
```

### 迁移时间估算

- **10万条记录**: 约5-10分钟
- **30万条记录**: 约15-30分钟
- **100万条记录**: 约1-2小时

实际时间取决于：
- 网络延迟
- MySQL服务器性能
- 批量大小设置

## 故障处理

### 1. 连接失败

**错误**: `Can't connect to MySQL server`

**解决**:
- 检查MySQL服务是否运行
- 检查主机地址和端口是否正确
- 检查防火墙设置
- 检查用户权限

### 2. 数据库不存在

**错误**: `Unknown database 'cve_db'`

**解决**:
```sql
CREATE DATABASE cve_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 权限不足

**错误**: `Access denied for user`

**解决**:
```sql
GRANT ALL PRIVILEGES ON cve_db.* TO 'your_user'@'%';
FLUSH PRIVILEGES;
```

### 4. 迁移中断

如果迁移过程中断，可以重新运行脚本：
- 已迁移的数据会自动跳过（基于CVE编号唯一性）
- 只会迁移未迁移的数据

## 迁移后操作

### 1. 切换数据库配置

在 `config/settings.py` 中：

```python
DATABASE_CONFIG = {
    'type': 'mysql',  # 改为 'mysql'
    # ... MySQL配置
}
```

或使用环境变量：

```bash
export DB_TYPE=mysql
```

### 2. 测试新数据库

```bash
# 运行一次增量爬取测试
python main.py --mode incremental

# 检查数据
python scripts/check_latest_date.py
```

### 3. 备份SQLite数据库（可选）

迁移完成后，可以备份SQLite数据库作为备份：

```bash
cp data/cve_database.db data/backups/cve_database_backup_$(date +%Y%m%d).db
```

## 注意事项

1. **数据安全**: 迁移前建议备份SQLite数据库
2. **网络稳定**: 确保网络连接稳定，避免迁移中断
3. **磁盘空间**: 确保MySQL服务器有足够的磁盘空间
4. **字符编码**: 确保MySQL数据库使用utf8mb4字符集
5. **索引优化**: 迁移完成后可以优化MySQL数据库

## 回滚方案

如果需要回滚到SQLite：

1. 在 `config/settings.py` 中设置 `'type': 'sqlite'`
2. 或使用环境变量 `export DB_TYPE=sqlite`
3. SQLite数据库文件仍然保留，可以直接使用

## 常见问题

### Q: 迁移会覆盖MySQL中已有的数据吗？

A: 不会。脚本使用 `INSERT OR UPDATE` 机制，如果CVE已存在则更新，不存在则插入。

### Q: 迁移过程中可以中断吗？

A: 可以。重新运行脚本会继续迁移未迁移的数据。

### Q: 迁移后SQLite数据库还会保留吗？

A: 是的。SQLite数据库文件不会删除，可以作为备份保留。

### Q: 如何验证迁移是否成功？

A: 使用 `--verify` 参数，脚本会自动验证数据一致性。

## 技术支持

如果遇到问题，请：
1. 查看日志文件 `logs/crawler.log`
2. 使用 `--dry-run` 模式测试
3. 检查MySQL连接和权限
4. 提交Issue并附上错误信息

