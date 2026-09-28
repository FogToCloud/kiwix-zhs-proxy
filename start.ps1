# -*- coding: utf-8 -*-
# kiwix-zhs-proxy 一键启动
# 1) 确保 kiwix-serve 在 8090
# 2) 确保简体代理在 8080
# 3) 打开「访问入口页」（/lan）：列出本机所有可用地址 + 二维码，手机扫码即开

# ==================== 按你的环境修改（或设环境变量覆盖，AI/脚本更友好） ====================
# 优先级：环境变量 KIWIX_DIR / ZIM_FILE / KIWIX_PYTHON > 下方默认值
$KIWIX_DIR   = if ($env:KIWIX_DIR)  { $env:KIWIX_DIR }  else { "C:\Users\cong\Kiwix" }
$ZIM_FILE    = if ($env:ZIM_FILE)   { $env:ZIM_FILE }   else { "$KIWIX_DIR\zim\wikipedia_zh_all_maxi_2026-08.zim" }
$PYTHON_EXE  = if ($env:KIWIX_PYTHON) { $env:KIWIX_PYTHON } else { "$KIWIX_DIR\python\python.exe" }
$PROXY_PY    = Join-Path $PSScriptRoot "kiwix_zhs_proxy.py"  # 代理脚本在本项目目录
$SERVE_EXE   = "$KIWIX_DIR\kiwix-serve\kiwix-serve.exe"
# 监听地址：默认 0.0.0.0 让手机能访问（代理启动时会提示"仅限内网"）；
# 只想本机访问就设 $env:KIWIX_HOST = "127.0.0.1"
$HOST_BIND   = if ($env:KIWIX_HOST) { $env:KIWIX_HOST } else { "0.0.0.0" }
# ====================================================================================

function Test-Port([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# ---------- 1. 确保 8090 ----------
if (Test-Port 8090) {
    Write-Host "[1/3] 8090 already running" -ForegroundColor Green
} else {
    Write-Host "[1/3] starting kiwix-serve on 8090 ..." -ForegroundColor Cyan
    if (-not (Test-Path $SERVE_EXE)) { Write-Host "ERROR: missing $SERVE_EXE" -ForegroundColor Red; exit 1 }
    if (-not (Test-Path $ZIM_FILE))  { Write-Host "ERROR: missing $ZIM_FILE"  -ForegroundColor Red; exit 1 }
    Start-Process -FilePath $SERVE_EXE -ArgumentList "--port=8090","--daemon","`"$ZIM_FILE`"" -WindowStyle Minimized
    $tries = 0
    while (-not (Test-Port 8090) -and $tries -lt 30) { Start-Sleep -Seconds 2; $tries++ }
    if (-not (Test-Port 8090)) { Write-Host "ERROR: 8090 not ready in 60s" -ForegroundColor Red; exit 1 }
    Write-Host "[1/3] 8090 ready" -ForegroundColor Green
}

# ---------- 2. 确保代理 8080 ----------
if (Test-Port 8080) {
    Write-Host "[2/3] 8080 proxy already running" -ForegroundColor Green
} else {
    Write-Host "[2/3] starting simplified proxy on 8080 ..." -ForegroundColor Cyan
    if (-not (Test-Path $PYTHON_EXE)) { Write-Host "ERROR: python not found at $PYTHON_EXE" -ForegroundColor Red; exit 1 }
    $env:KIWIX_HOST = $HOST_BIND
    Start-Process -FilePath $PYTHON_EXE -ArgumentList "`"$PROXY_PY`"" -WindowStyle Minimized
    $tries2 = 0
    while (-not (Test-Port 8080) -and $tries2 -lt 15) { Start-Sleep -Seconds 2; $tries2++ }
    if (-not (Test-Port 8080)) { Write-Host "ERROR: 8080 not ready in 30s" -ForegroundColor Red; exit 1 }
    Write-Host "[2/3] 8080 proxy ready" -ForegroundColor Green
}

# ---------- 3. 打开浏览器 ----------
Write-Host "[3/3] opening access page ..." -ForegroundColor Cyan
# 打开「访问入口页」（/lan）：自动列出本机所有可用地址 + 二维码，手机扫码即开。
# 任何网络环境（家里 WiFi / 手机热点 / 无外网）都适用：手机连哪个网络，就扫那张卡的码。
Start-Process "http://127.0.0.1:8080/lan"
Write-Host ""
Write-Host "Launched. Browser should show the access page (IP list + QR codes)."
Write-Host "Phone (same Wi-Fi or phone hotspot): scan the QR code on the page,"
Write-Host "or open http://<PC-IP>:8080 (find the IP on the page)."
Write-Host "To stop: run stop.ps1"
Read-Host "Press Enter to close"
