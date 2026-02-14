FROM ubuntu:22.04

# 避免交互式配置提示
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # X11 和显示
    xvfb \
    x11vnc \
    fluxbox \
    # KiCad 依赖
    software-properties-common \
    # 基础工具
    wget \
    curl \
    git \
    python3 \
    python3-pip \
    python3-dev \
    # 编译工具
    build-essential \
    cmake \
    pkg-config \
    # X11 开发库
    libx11-dev \
    libxext-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxrandr-dev \
    libxi-dev \
    # OpenGL
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    # 字体
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    # 其他依赖
    libgtk-3-0 \
    libgtk-3-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 添加 KiCad PPA 并安装 KiCad
RUN add-apt-repository -y ppa:kicad/kicad-8.0-releases && \
    apt-get update && \
    apt-get install -y \
    kicad \
    kicad-libraries \
    kicad-templates \
    kicad-symbols \
    kicad-footprints \
    kicad-packages3d \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# 创建必要目录
RUN mkdir -p /projects /output /config /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

# 配置 KiCad 环境变量
ENV KICAD_CONFIG_HOME=/config
ENV KICAD_SYMBOL_DIR=/usr/share/kicad/symbols
ENV KICAD_FOOTPRINT_DIR=/usr/share/kicad/footprints
ENV KICAD_3DMODEL_DIR=/usr/share/kicad/3dmodels
ENV KICAD_TEMPLATE_DIR=/usr/share/kicad/template

# 暴露端口
# 6080 - noVNC
# 5900 - VNC
EXPOSE 6080 5900

# 启动脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["kicad"]
