# jCoin heartbeat watchdog wrapper for Windows Task Scheduler.
# Independent of the trading runner by design — if jCoin-Paper-Trader dies silently,
# this task is what notices (ALERT files + event log + non-zero exit in task history).
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$repo = "C:\Repositories\jCoin"
Set-Location $repo
& "C:\Python310\python.exe" -m jcoin.live.watchdog 2>&1 |
    Out-File -Append -Encoding utf8 "$repo\paper_state\watchdog.log"
exit $LASTEXITCODE
