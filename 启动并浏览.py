import subprocess
import time
import webbrowser
import os

# 启动前端服务器
print("正在启动前端开发服务器...")
web_dir = r"E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\web"

# 使用npm run dev启动服务器
server_process = subprocess.Popen(
    ["cmd", "/c", "npm run dev"],
    cwd=web_dir,
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

print("等待服务器启动...")
time.sleep(8)  # 等待服务器启动

# 打开浏览器
print("正在打开浏览器...")
webbrowser.open("http://localhost:5173")

print("服务器已启动在 http://localhost:5173")
print("按 Ctrl+C 停止服务器")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n正在停止服务器...")
    server_process.terminate()
    print("服务器已停止")
