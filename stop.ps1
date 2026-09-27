# -*- coding: utf-8 -*-
# 停止 kiwix-zhs-proxy：结束 kiwix-serve 与简体代理进程

$targets = @()
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*kiwix_zhs_proxy*" } |
    ForEach-Object { $targets += $_.ProcessId }

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "kiwix-serve*" } |
    ForEach-Object { $targets += $_.ProcessId }

if ($targets.Count -eq 0) {
    Write-Host "Nothing to stop (no proxy / kiwix-serve process found)." -ForegroundColor Yellow
} else {
    $targets | Select-Object -Unique | ForEach-Object {
        Write-Host "Stopping PID $_ ..." -ForegroundColor Cyan
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
    Write-Host "Stopped." -ForegroundColor Green
}
