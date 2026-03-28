FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    xvfb \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libnotify4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    libasound2 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY ../agent/requirements.txt /app/requirements.txt

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY ../agent /app

# 创建必要的目录
RUN mkdir -p /projects /output /data

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
