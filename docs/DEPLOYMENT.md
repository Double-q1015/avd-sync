# 部署指南

本文档介绍如何在服务器上部署 AVD Sync，包括 Docker 和 Conda 两种方式。

## 部署方式选择

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Docker** | 环境隔离、易于管理、一键部署 | 性能略低、资源占用稍高 | 生产环境、快速部署 |
| **Conda** | 性能更好、资源占用低 | 需要手动管理依赖 | 开发环境、性能敏感场景 |

---

## 方式一：Docker 部署（推荐）

### 资源需求

#### 最低配置（增量爬取）
- **CPU**: 1核
- **内存**: 1GB
- **磁盘**: 5GB
- **适用场景**: 日常增量更新

#### 推荐配置（全量爬取）
- **CPU**: 2核
- **内存**: 2GB
- **磁盘**: 10GB
- **适用场景**: 全量爬取，数据量大

### 快速开始

#### 使用 Docker Compose（推荐）

```bash
# 构建镜像
docker-compose build

# 运行增量爬取
docker-compose run --rm avd-sync python main.py --mode incremental

# 运行全量爬取
docker-compose run --rm avd-sync python main.py --mode full

# 后台运行
docker-compose up -d
```

#### 使用 Docker 命令

```bash
# 构建镜像
docker build -t avd-sync .

# 运行容器（增量爬取）
docker run --rm \
  --shm-size=2g \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  avd-sync python main.py --mode incremental

# 运行容器（全量爬取）
docker run --rm \
  --shm-size=2g \
  --memory=2g \
  --cpus=2 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  avd-sync python main.py --mode full
```

### 性能优化

1. **使用 Headless 模式**（必须）
   - Docker 中已默认启用
   - 在 `config/settings.py` 中确认：`'headless': True`

2. **调整共享内存大小**
   - 在 `docker-compose.yml` 中设置：`shm_size: 2gb`

3. **资源限制**
   - 在 `docker-compose.yml` 中设置合理的资源限制

### 性能指标参考

**增量爬取**（每天一次）：
- 运行时间：5-15分钟
- 内存峰值：500MB-1GB
- CPU使用：10-30%

**全量爬取**（每月一次）：
- 运行时间：1-2小时
- 内存峰值：1-2GB
- CPU使用：30-60%

### 监控和日志

```bash
# 查看容器资源使用
docker stats avd-sync

# 查看容器日志
docker-compose logs -f avd-sync
```

### 常见问题

1. **浏览器启动失败**
   - 确保设置了 `--no-sandbox` 和足够的共享内存

2. **内存不足**
   - 增加 Docker 内存限制
   - 减少并发数（如果支持）

3. **数据库权限问题**
   ```bash
   chmod -R 755 data/
   ```

### 生产环境建议

#### 定时任务

结合 `docker-compose` 和系统 cron：

```bash
# 每天凌晨执行增量爬取
0 2 * * * cd /path/to/avd-sync && docker-compose run --rm avd-sync python main.py --mode incremental
```

#### 备份策略

定期备份数据库：

```bash
docker-compose exec avd-sync cp /app/data/cve_database.db /app/data/backups/cve_$(date +%Y%m%d).db
```

---

## 方式二：Conda 部署

### Python 版本推荐

**最佳选择：Python 3.10 或 3.11**

- ✅ **Python 3.10**：稳定、成熟，所有依赖完全支持
- ✅ **Python 3.11**：性能提升 10-60%，向后兼容性好
- ⚠️ **Python 3.9**：满足最低要求，但性能较新版本略差

### 环境创建

#### 方式一：使用 conda（推荐）

```bash
# 创建 Python 3.10 环境
conda create -n avd-sync python=3.10 -y

# 激活环境
conda activate avd-sync

# 安装依赖
pip install -r requirements.txt
```

#### 方式二：使用 conda-forge（更稳定）

```bash
# 创建环境并安装基础包
conda create -n avd-sync python=3.10 -c conda-forge -y

# 激活环境
conda activate avd-sync

# 安装依赖
conda install -c conda-forge beautifulsoup4 tqdm lxml -y
pip install -r requirements.txt
```

### 完整部署步骤

#### 1. 创建 Conda 环境

```bash
conda create -n avd-sync python=3.10 -y
conda activate avd-sync
```

#### 2. 安装系统依赖（如果需要浏览器）

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    chromium-browser \
    chromium-chromedriver \
    fonts-wqy-zenhei \
    fonts-wqy-microhei

# CentOS/RHEL
sudo yum install -y \
    chromium \
    chromium-headless \
    wqy-zenhei-fonts \
    wqy-microhei-fonts
```

#### 3. 安装 Python 依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 如果使用 MySQL，还需要安装驱动
pip install pymysql
# 或
pip install mysql-connector-python
```

#### 4. 测试安装

```bash
# 检查 Python 版本
python --version  # 应该显示 Python 3.10.x

# 检查依赖
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
python -c "from DrissionPage import ChromiumPage; print('DrissionPage OK')"

# 运行测试
python main.py --help
```

### 环境管理

#### 导出环境配置

```bash
# 导出 conda 环境
conda env export > environment.yml

# 导出 pip 依赖
pip freeze > requirements-lock.txt
```

#### 在其他机器上恢复环境

```bash
# 从 environment.yml 创建环境
conda env create -f environment.yml

# 或手动创建
conda create -n avd-sync python=3.10 -y
conda activate avd-sync
pip install -r requirements.txt
```

### 常见问题

#### Q1: 应该选择哪个 Python 版本？

**A**: 
- **生产环境**：推荐 Python 3.10（最稳定）
- **开发环境**：可以使用 Python 3.11（性能更好）
- **保守选择**：Python 3.9（满足最低要求）

#### Q2: conda 中找不到 Python 3.10？

**A**: 
```bash
# 更新 conda
conda update conda

# 使用 conda-forge 频道
conda create -n avd-sync python=3.10 -c conda-forge -y
```

#### Q3: 依赖安装失败？

**A**: 
```bash
# 先升级 pip 和 setuptools
pip install --upgrade pip setuptools wheel

# 使用国内镜像（如果网络慢）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 云服务器推荐配置

### 经济型（适合增量爬取）
- **阿里云**: ecs.t6-c1m1.large (1核1GB) - 约30元/月
- **腾讯云**: S2.SMALL1 (1核1GB) - 约30元/月
- **AWS**: t3.micro (1 vCPU, 1GB) - 约$10/月

### 标准型（推荐，适合全量爬取）
- **阿里云**: ecs.t6-c1m2.large (1核2GB) - 约50元/月
- **腾讯云**: S2.MEDIUM4 (2核4GB) - 约100元/月
- **AWS**: t3.small (2 vCPU, 2GB) - 约$15/月

### 高性能型（适合并发场景）
- **阿里云**: ecs.c6.large (2核4GB) - 约150元/月
- **腾讯云**: S5.MEDIUM8 (2核8GB) - 约200元/月
- **AWS**: t3.medium (2 vCPU, 4GB) - 约$30/月

---

## 性能对比

| 场景 | 本地运行 | Docker运行 | Conda运行 | 性能差异 |
|------|---------|-----------|-----------|---------|
| 增量爬取 | 5分钟 | 6-8分钟 | 5分钟 | Docker +20-60% |
| 全量爬取 | 90分钟 | 100-120分钟 | 90分钟 | Docker +10-30% |
| 内存占用 | 400MB | 500-800MB | 400MB | Docker +25-100% |

**结论**: Docker 运行会有一定性能损失，但在可接受范围内。Conda 部署性能与本地运行相当。
