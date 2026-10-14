# jCoin paper-trader wrapper for Windows Task Scheduler.
# Runs the live paper step (processes the newest closed 4h bar; idempotent — safe to
# run hourly, it skips if no new bar). Paper uses public data only, no API keys.
# Note: do NOT set ErrorActionPreference=Stop — Python logging on stderr would be
# misread as a fatal error. We merge all output to the log and exit on Python's code.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$repo = "C:\Repositories\jCoin"
Set-Location $repo
New-Item -ItemType Directory -Force -Path "$repo\paper_state" | Out-Null
& "C:\Python310\python.exe" -m jcoin.live.run_paper --mode live --max-dd-pct 0.398 2>&1 |
    Out-File -Append -Encoding utf8 "$repo\paper_state\scheduler.log"
exit $LASTEXITCODE
