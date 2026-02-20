# KiCad AI 自动测试启动脚本
# 后台启动服务并运行测试

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "KiCad AI RF PCB 自动测试" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# 检查并安装依赖
Write-Host "`n[1/4] 检查依赖..." -ForegroundColor Yellow

# 检查 Playwright
python -c "from playwright.async_api import async_playwright" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "安装 Playwright..." -ForegroundColor Yellow
    pip install playwright
    playwright install chromium
}

# 启动后端
Write-Host "`n[2/4] 启动后端服务..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location "E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\agent"
    python main.py
} -Name "BackendServer"

Start-Sleep -Seconds 3

# 启动前端
Write-Host "[3/4] 启动前端服务..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location "E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-ai-auto\web"
    npm run dev
} -Name "FrontendServer"

Start-Sleep -Seconds 8

# 检查服务状态
Write-Host "`n[4/4] 检查服务状态..." -ForegroundColor Yellow
$backendRunning = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$frontendRunning = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue

if ($backendRunning) {
    Write-Host "  后端 (8000): OK" -ForegroundColor Green
} else {
    Write-Host "  后端 (8000): FAIL" -ForegroundColor Red
}

if ($frontendRunning) {
    Write-Host "  前端 (3000): OK" -ForegroundColor Green
} else {
    Write-Host "  前端 (3000): FAIL" -ForegroundColor Red
}

# 运行测试
Write-Host "`n开始运行测试..." -ForegroundColor Cyan
python E:\0-007-MyAIOS\projects\1-kicad-for-chrome\rf_pcb_test.py

# 清理
Write-Host "`n清理服务..." -ForegroundColor Yellow
Stop-Job -Name "BackendServer" -ErrorAction SilentlyContinue
Stop-Job -Name "FrontendServer" -ErrorAction SilentlyContinue
Remove-Job -Name "BackendServer" -Force -ErrorAction SilentlyContinue
Remove-Job -Name "FrontendServer" -Force -ErrorAction SilentlyContinue

Write-Host "测试完成!" -ForegroundColor Green
