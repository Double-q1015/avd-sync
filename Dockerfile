# 使用官方Python镜像作为基础（推荐使用 3.10 更稳定）
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（Chromium和必要的库）
RUN apt-get update && apt-get install -y \
    # Chromium浏览器
    chromium \
    chromium-driver \
    # 字体支持（避免中文显示问题）
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    # 系统库
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/* \
    # 创建 chromium-browser 符号链接（兼容性）
    && ln -s /usr/bin/chromium /usr/bin/chromium-browser || true

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    # 设置Chromium路径
    CHROMIUM_PATH=/usr/bin/chromium \
    # 禁用GPU加速（Docker中不需要）
    DISPLAY=:99 \
    # 设置共享内存大小（Chromium需要）
    SHM_SIZE=2gb \
    # Docker环境必须使用无头模式
    HEADLESS=true \
    # 时区设置
    TZ=Asia/Shanghai \
    # Chromium 无头模式环境变量
    CHROME_BIN=/usr/bin/chromium \
    CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu"

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 创建非 root 用户（安全最佳实践）
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -d /app -s /bin/bash appuser && \
    # 创建必要的目录
    mkdir -p /app/data /app/logs /app/data/backups && \
    # 设置目录权限
    chown -R appuser:appuser /app

# 复制项目代码
COPY --chown=appuser:appuser . .

# 切换到非 root 用户
USER appuser

# 默认命令
CMD ["python", "main.py", "--mode", "auto"]

