# KiCad AI 自动化控制系统 - 部署文档

## 概述

本文档介绍如何部署 KiCad AI 自动化控制系统，包括开发环境搭建、生产环境配置和常见问题解决。

---

## 系统要求

### 硬件要求

| 环境 | CPU | 内存 | 存储 | 网络 |
|------|-----|------|------|------|
| 开发环境 | 4 核 | 8GB | 50GB SSD | 10Mbps |
| 测试环境 | 4 核 | 8GB | 100GB SSD | 100Mbps |
| 生产环境 | 8 核 | 16GB+ | 200GB SSD | 1Gbps |

### 软件要求

- **操作系统**: Ubuntu 22.04 LTS (推荐) / Windows 10/11 / macOS 12+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **KiCad**: 8.0+
- **Node.js**: 20+ (前端开发)
- **Python**: 3.11+ (后端开发)

---

## 快速部署 (Docker)

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/kicad-for-chrome.git
cd kicad-for-chrome
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置以下参数：
# - API_KEY: API 认证密钥
# - ALLOWED_ORIGINS: 允许的跨域来源
# - PROJECTS_DIR: 项目文件目录
# - OUTPUT_DIR: 输出文件目录
```

### 3. 启动服务

```bash
cd kicad-ai-auto
docker-compose up -d
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f control-agent

# 测试 API
curl http://localhost:8000/api/health
```

### 5. 访问系统

- **Web UI**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **noVNC** (可选): http://localhost:6080

---

## 手动部署

### 前端部署

#### 1. 安装依赖

```bash
cd kicad-ai-auto/web
npm install
```

#### 2. 配置环境

```bash
# 创建 .env 文件
cat > .env << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/control
EOF
```

#### 3. 构建生产版本

```bash
npm run build
```

#### 4. 部署

```bash
# 使用 nginx 部署
sudo cp -r dist/* /var/www/html/

# 或使用 serve
npm install -g serve
serve -s dist -l 3000
```

### 后端部署

#### 1. 安装依赖

```bash
cd kicad-ai-auto/agent
pip install -r ../docker/requirements.txt
```

#### 2. 配置环境

```bash
export API_KEY="your-secret-key"
export ALLOWED_ORIGINS="http://localhost:3000,http://your-domain.com"
export PROJECTS_DIR="/projects"
export OUTPUT_DIR="/output"
export DISPLAY=":99"
```

#### 3. 启动服务

```bash
# 开发模式
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 生产环境配置

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # 前端
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd 服务

创建 `/etc/systemd/system/kicad-agent.service`:

```ini
[Unit]
Description=KiCad AI Control Agent
After=network.target

[Service]
Type=simple
User=kicad
WorkingDirectory=/opt/kicad-ai-auto/agent
Environment="API_KEY=your-secret-key"
Environment="ALLOWED_ORIGINS=https://your-domain.com"
Environment="PROJECTS_DIR=/opt/projects"
Environment="OUTPUT_DIR=/opt/output"
Environment="DISPLAY=:99"
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable kicad-agent
sudo systemctl start kicad-agent
```

---

## 安全配置

### 1. API 密钥配置

```bash
# 生成强密码
openssl rand -base64 32

# 设置环境变量
export API_KEY="your-generated-key"
```

### 2. CORS 配置

只允许特定域名访问：

```bash
export ALLOWED_ORIGINS="https://your-domain.com,https://admin.your-domain.com"
```

### 3. 文件上传限制

```python
# 在 agent/main.py 中配置
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.kicad_pro', '.kicad_sch', '.kicad_pcb', '.zip'}
```

### 4. 速率限制

```python
# 在 agent/main.py 中配置
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
)
```

---

## 监控和日志

### 查看日志

```bash
# Docker 部署
docker-compose logs -f [service-name]

# Systemd 部署
sudo journalctl -u kicad-agent -f
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/api/health

# 完整状态检查
curl http://localhost:8000/api/state/full
```

### Prometheus 监控 (可选)

添加 Prometheus 指标端点：

```python
# 在 main.py 中添加
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 备份和恢复

### 备份项目文件

```bash
# 创建备份
sudo tar -czf backup-$(date +%Y%m%d).tar.gz /opt/projects /opt/output

# 定时备份 (crontab)
0 2 * * * /opt/kicad-ai-auto/scripts/backup.sh
```

### 恢复备份

```bash
# 停止服务
docker-compose down

# 恢复数据
sudo tar -xzf backup-20240201.tar.gz -C /

# 重启服务
docker-compose up -d
```

---

## 故障排除

### 常见问题

#### 1. KiCad 无法启动

```bash
# 检查 Xvfb
echo $DISPLAY
ps aux | grep Xvfb

# 手动启动 Xvfb
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
```

#### 2. WebSocket 连接失败

```bash
# 检查防火墙
sudo ufw status
sudo ufw allow 8000

# 检查 nginx 配置
sudo nginx -t
sudo systemctl restart nginx
```

#### 3. 截图失败

```bash
# 检查依赖
python -c "import pyautogui; print('OK')"
python -c "from Xlib import display; print('OK')"

# 安装缺失依赖
pip install pyautogui python-xlib
```

#### 4. 权限问题

```bash
# 修复文件权限
sudo chown -R kicad:kicad /opt/projects /opt/output
sudo chmod -R 755 /opt/projects /opt/output
```

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 前端调试
npm run dev

# 后端调试
uvicorn main:app --reload --log-level debug
```

---

## 性能优化

### 1. 截图性能

- 降低截图频率 (默认 10 FPS)
- 使用 WebP 格式压缩
- 降低截图分辨率

### 2. 数据库优化 (如果使用)

```python
# 连接池配置
DATABASE_URL="postgresql://user:pass@localhost/kicad?pool_size=20"
```

### 3. 缓存配置

```python
# Redis 缓存
REDIS_URL="redis://localhost:6379/0"
```

---

## 升级指南

### 升级到新版本

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取更新
git pull origin main

# 3. 更新 Docker 镜像
docker-compose pull
docker-compose up -d

# 4. 验证升级
curl http://localhost:8000/api/health
```

### 回滚

```bash
# 1. 停止服务
docker-compose down

# 2. 恢复数据
./scripts/restore.sh

# 3. 使用旧版本镜像
docker-compose -f docker-compose.yml -f docker-compose.old.yml up -d
```

---

## 开发环境搭建

### 1. 安装开发工具

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# 安装 pyenv
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0
```

### 2. 安装依赖

```bash
# 前端
cd kicad-ai-auto/web
npm install

# 后端
cd ../agent
pip install -r ../docker/requirements.txt
pip install -r requirements-dev.txt
```

### 3. 启动开发服务器

```bash
# 终端 1 - 前端
cd kicad-ai-auto/web
npm run dev

# 终端 2 - 后端
cd kicad-ai-auto/agent
python main.py
```

---

## API 使用示例

### 1. 启动 KiCad

```bash
curl -X POST http://localhost:8000/api/project/start \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json"
```

### 2. 打开项目

```bash
curl -X POST http://localhost:8000/api/project/open \
  -H "X-API-Key: your-key" \
  -F "file=@/path/to/project.kicad_pro"
```

### 3. 导出 Gerber

```bash
curl -X POST http://localhost:8000/api/export \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "gerber",
    "output_dir": "/output/gerber",
    "options": {"layers": ["F.Cu", "B.Cu"]}
  }'
```

---

## 贡献指南

1. Fork 仓库
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

---

## 许可证

GPL-3.0

---

## 支持和联系

- 问题报告: GitHub Issues
- 文档: https://docs.kicad-ai.example.com
- 邮件: support@kicad-ai.example.com

---

**最后更新**: 2025-02-11
**版本**: 1.0.0
