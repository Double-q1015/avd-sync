# 数据库支持说明

## 支持的数据库

AVD Sync 目前支持以下数据库：

1. **SQLite**（默认）- 轻量级，适合单机使用
2. **MySQL** - 适合生产环境，支持高并发

## 配置方式

### SQLite配置（默认）

在 `config/settings.py` 中：

```python
DATABASE_CONFIG = {
    'type': 'sqlite',
    'db_path': BASE_DIR / 'data' / 'cve_database.db',
}
```

或通过环境变量：

```bash
export DB_TYPE=sqlite
python main.py
```

### MySQL配置

#### 方式1：配置文件

在 `config/settings.py` 中：

```python
DATABASE_CONFIG = {
    'type': 'mysql',
    'mysql': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'your_password',
        'database': 'cve_db',
        'charset': 'utf8mb4',
    },
}
```

#### 方式2：环境变量（推荐）

```bash
export DB_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=cve_db
export MYSQL_CHARSET=utf8mb4

python main.py
```

## 安装MySQL支持

如果需要使用MySQL，需要安装mysql-connector-python（MySQL官方连接器）：

```bash
pip install mysql-connector-python
```

或添加到 `requirements.txt`：

```bash
pip install -r requirements.txt
```

## 数据库初始化

### SQLite

SQLite数据库会在首次运行时自动创建，无需手动初始化。

### MySQL

需要先创建数据库：

```sql
CREATE DATABASE cve_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

然后运行程序，表结构会自动创建。

## 使用示例

### 使用SQLite（默认）

```bash
# 使用默认配置
python main.py --mode incremental

# 指定数据库路径
python main.py --mode incremental --db-path /path/to/custom.db
```

### 使用MySQL

```bash
# 通过环境变量配置
export DB_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=password
export MYSQL_DATABASE=cve_db

python main.py --mode incremental
```

## 性能对比

| 特性 | SQLite | MySQL |
|------|--------|-------|
| 适用场景 | 单机、小规模 | 生产、高并发 |
| 安装复杂度 | 无需安装 | 需要MySQL服务器 |
| 性能 | 中等 | 高 |
| 并发支持 | 有限 | 优秀 |
| 数据量 | 适合中小型 | 适合大型 |
| 备份 | 文件复制 | 需要mysqldump |

## 迁移数据

### 从SQLite迁移到MySQL

1. **导出SQLite数据**（使用脚本或工具）

2. **创建MySQL数据库和表**（运行程序自动创建）

3. **导入数据**（可以使用数据迁移脚本）

### 从MySQL迁移到SQLite

1. **导出MySQL数据**

2. **使用SQLite数据库**

3. **导入数据**

## 注意事项

### SQLite

- ✅ 无需安装，开箱即用
- ✅ 适合单机使用
- ⚠️ 并发写入性能有限
- ⚠️ 不适合高并发场景

### MySQL

- ✅ 适合生产环境
- ✅ 支持高并发
- ✅ 性能优秀
- ⚠️ 需要MySQL服务器
- ⚠️ 需要安装mysql-connector-python库

## 故障排查

### MySQL连接失败

1. **检查MySQL服务是否运行**
   ```bash
   # Linux/Mac
   sudo systemctl status mysql
   
   # 或
   mysqladmin -u root -p ping
   ```

2. **检查网络连接**
   ```bash
   telnet localhost 3306
   ```

3. **检查用户权限**
   ```sql
   GRANT ALL PRIVILEGES ON cve_db.* TO 'user'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. **检查防火墙设置**

### 字符编码问题

确保MySQL数据库使用utf8mb4字符集：

```sql
CREATE DATABASE cve_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 最佳实践

### 开发环境

使用SQLite，简单快速：

```python
DATABASE_CONFIG = {
    'type': 'sqlite',
    'db_path': 'data/cve_database.db',
}
```

### 生产环境

使用MySQL，性能更好：

```python
DATABASE_CONFIG = {
    'type': 'mysql',
    'mysql': {
        'host': 'db.example.com',
        'port': 3306,
        'user': 'cve_user',
        'password': 'secure_password',
        'database': 'cve_production',
        'charset': 'utf8mb4',
    },
}
```

### 使用环境变量

生产环境建议使用环境变量，避免在代码中硬编码密码：

```bash
export DB_TYPE=mysql
export MYSQL_HOST=db.example.com
export MYSQL_USER=cve_user
export MYSQL_PASSWORD=$(cat /path/to/password.txt)
export MYSQL_DATABASE=cve_production
```

## 未来计划

计划支持更多数据库：

- PostgreSQL
- MongoDB
- Redis（缓存）

欢迎贡献代码！

