import http.server
import socketserver
import threading
import time
import os

PORT = 8888
DIRECTORY = r"E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\web\dist"


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


# 启动服务器
def start_server():
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        httpd.serve_forever()


# 在后台线程启动服务器
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

print(f"Local server started on http://localhost:{PORT}/")
print("Waiting for server to be ready...")
time.sleep(2)

# 保持运行
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nServer stopped")
