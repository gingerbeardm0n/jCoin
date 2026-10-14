"""Windowless launcher for the jCoin scheduled tasks.

Task Scheduler runs this with pythonw.exe (no console), so nothing pops up on
screen. It runs the real job with python.exe under CREATE_NO_WINDOW and appends
all output to the same log files the old PowerShell wrappers used.

Usage: pythonw.exe scripts\task_runner.pyw paper|watchdog
"""
import os
import subprocess
import sys

REPO = r"C:\Repositories\jCoin"
PYTHON = r"C:\Python310\python.exe"

JOBS = {
    "paper": (["-m", "jcoin.live.run_paper", "--mode", "live", "--max-dd-pct", "0.398"],
              os.path.join(REPO, "paper_state", "scheduler.log")),
    "watchdog": (["-m", "jcoin.live.watchdog"],
                 os.path.join(REPO, "paper_state", "watchdog.log")),
}


def main() -> int:
    job = sys.argv[1] if len(sys.argv) > 1 else ""
    if job not in JOBS:
        return 2
    args, log_path = JOBS[job]
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    with open(log_path, "a", encoding="utf-8") as log:
        proc = subprocess.run([PYTHON, *args], cwd=REPO, env=env,
                              stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
