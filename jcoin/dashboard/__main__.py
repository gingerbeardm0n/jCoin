"""python -m jcoin.dashboard [--state-dir paper_state] [--port 8765]"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

import uvicorn

import jcoin.dashboard.app as dashboard_app


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin live dashboard")
    p.add_argument("--state-dir", default="paper_state")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args(argv)

    dashboard_app.STATE_FILE = Path(args.state_dir) / "state.json"

    url = f"http://localhost:{args.port}"
    if not args.no_browser:
        webbrowser.open(url)

    print(f"jCoin dashboard → {url}")
    print(f"State file     → {dashboard_app.STATE_FILE}")
    uvicorn.run(dashboard_app.app, host="0.0.0.0", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
