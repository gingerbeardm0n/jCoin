# jCoin daemon setup + launch
# Run from the PS session where KRAKEN_FUTURES_KEY and KRAKEN_FUTURES_SECRET are set.

Set-Location C:\Repositories\jCoin

# --- 1. Promote env vars to User level (survives reboot, inherited by all processes) ---
$key    = $env:KRAKEN_FUTURES_KEY
$secret = $env:KRAKEN_FUTURES_SECRET

if (-not $key -or -not $secret) {
    Write-Host "ERROR: KRAKEN_FUTURES_KEY or KRAKEN_FUTURES_SECRET not set in this session." -ForegroundColor Red
    Write-Host "Set them first:  `$env:KRAKEN_FUTURES_KEY = 'your-key'" -ForegroundColor Yellow
    exit 1
}

[System.Environment]::SetEnvironmentVariable("KRAKEN_FUTURES_KEY",    $key,    "User")
[System.Environment]::SetEnvironmentVariable("KRAKEN_FUTURES_SECRET", $secret, "User")
Write-Host "Keys stored permanently (User environment)." -ForegroundColor Green

# --- 2. Kill any existing daemon instance ---
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

# --- 3. Launch daemon hidden in background ---
New-Item -ItemType Directory -Path logs -Force | Out-Null
Start-Process pythonw `
    -ArgumentList "-m jcoin.live.daemon --mode both" `
    -WorkingDirectory C:\Repositories\jCoin `
    -WindowStyle Hidden

Write-Host "Daemon launched (mode=both: Kraken demo + paper simulation)." -ForegroundColor Green

# --- 4. Wait for log to appear and show first lines ---
Write-Host "Waiting for daemon log..." -ForegroundColor Cyan
$waited = 0
while (-not (Test-Path logs\daemon.log) -and $waited -lt 15) {
    Start-Sleep -Seconds 1
    $waited++
}

if (Test-Path logs\daemon.log) {
    Write-Host ""
    Write-Host "=== daemon.log ===" -ForegroundColor Cyan
    Get-Content logs\daemon.log
    Write-Host ""
    Write-Host "Daemon is running. Tail log anytime:" -ForegroundColor Green
    Write-Host "  Get-Content C:\Repositories\jCoin\logs\daemon.log -Wait" -ForegroundColor Yellow
} else {
    Write-Host "Log not created after 15s — daemon may have crashed." -ForegroundColor Red
    Write-Host "Run visibly to debug:  python -m jcoin.live.daemon" -ForegroundColor Yellow
}
