"""Per-trade parity ledger for the paper bots (AUDIT_2026-10-23 item 4; VALIDATION_RULES §9 gate 2).

For every closed paper trade, replay the tested harness on the SAME Coinbase price data
and compare:
  - A    (paper_state/): harness A on nano 4h (execution parity), plus A_SR-style
           spot-referenced replay as a clipping detector (big gap = nano spike clipped a winner).
  - A_SR (paper_state_sr/): §8 harness (`spot_stop_test.ref_trades`) on spot + nano.
A trade is FLAGGED if the replay has no trade with the same symbol/side/entry bar, or
|paper R - replay R| > 0.25. Flags exit 1 and send a /fail ping (the paper bot and the
tested code disagree: something is broken). Only A trades from the Coinbase switch
(2026-10-19) on are checked; earlier A paper trades ran on Kraken prices.

Usage (VM, daily via jcoin-backup.service):
    python -m jcoin.research.parity_ledger
Writes paper_state/parity_ledger.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from jcoin.data.config import COINBASE_MARKETS
from jcoin.live.ping import ping
from jcoin.research.close_stop_test import trades as harness_trades
from jcoin.research.coinbase_parity import fetch_coinbase_4h
from jcoin.research.spot_stop_test import SPOT_PRODUCTS, ref_trades

UTC = dt.timezone.utc
H4 = dt.timedelta(hours=4)
A_VENUE_SWITCH = dt.datetime(2026, 10, 19, tzinfo=UTC)
TOL_R = 0.25
NANO = {m.label: m.symbol for m in COINBASE_MARKETS}


def _ts(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _closed(state_path: Path) -> list[dict]:
    if not state_path.exists():
        return []
    return json.loads(state_path.read_text(encoding="utf-8")).get("closed", [])


def _frames(start: dt.datetime, end: dt.datetime):
    spot = {c: fetch_coinbase_4h(p, start, end) for c, p in SPOT_PRODUCTS.items()}
    nano = {c: fetch_coinbase_4h(p, start, end) for c, p in NANO.items()}
    cut = lambda d: {k: v.filter(v["ts"] + H4 <= end) for k, v in d.items()}   # closed bars only
    return cut(spot), cut(nano)


def _index(trades):
    return {(t["symbol"], t["side"], t["entry_time"]): t for t in trades}


def build(a_trades: list[dict], sr_trades: list[dict], spot, nano):
    """Return (rows, n_flags). Paper trade dicts: symbol, side, entry_time (bar OPEN for A,
    bar CLOSE for A_SR), R."""
    rep_a = _index(harness_trades("intrabar", 0.0, nano))
    rep_sr = _index(ref_trades(spot, nano))
    rows, flags = [], 0
    for bot, paper, replay, shift in (("A", a_trades, rep_a, dt.timedelta(0)),
                                     ("A_SR", sr_trades, rep_sr, H4)):
        for t in paper:
            key = (t["symbol"], t["side"], _ts(t["entry_time"]) - shift)
            r = replay.get(key)
            clip = rep_sr.get(key) if bot == "A" else None
            if r is None:
                status, d = "FLAG: no matching replay trade", None
            else:
                d = t["R"] - r["R"]
                status = "ok" if abs(d) <= TOL_R else f"FLAG: |dR| {abs(d):.2f} > {TOL_R}"
            if status != "ok":
                flags += 1
            note = ""
            if clip is not None and r is not None and clip["R"] - r["R"] > 2.0:
                note = f"spot-ref replay {clip['R']:+.2f}R: nano likely clipped this trade"
            rows.append((bot, t["symbol"], t["side"], key[2], t["R"],
                         None if r is None else r["R"], d, status, note))
    return rows, flags


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Paper-vs-harness parity ledger")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.root)
    a = [t for t in _closed(root / "paper_state" / "state.json")
         if _ts(t["entry_time"]) >= A_VENUE_SWITCH and t.get("exit_reason") != "halt"]
    sr = [t for t in _closed(root / "paper_state_sr" / "state.json") if t.get("exit_kind") != "halt"]
    now = dt.datetime.now(UTC)
    out = ["# Paper parity ledger", "", f"Generated {now:%Y-%m-%d %H:%M} UTC. Tolerance ±{TOL_R}R. "
           f"A checked from {A_VENUE_SWITCH:%Y-%m-%d} (Coinbase prices).", ""]
    flags = 0
    if a or sr:
        earliest = min(_ts(t["entry_time"]) for t in a + sr)
        spot, nano = _frames(min(earliest - dt.timedelta(days=150), now), now)
        rows, flags = build(a, sr, spot, nano)
        out += ["| Bot | Symbol | Side | Entry bar | Paper R | Replay R | dR | Status | Note |",
                "|---|---|---|---|---|---|---|---|---|"]
        f = lambda v: "—" if v is None else f"{v:+.3f}"
        out += [f"| {b} | {s} | {sd} | {e:%Y-%m-%d %H:%M} | {f(p)} | {f(r)} | {f(d)} | {st} | {n} |"
                for b, s, sd, e, p, r, d, st, n in rows]
    else:
        out.append("No closed paper trades to check yet.")
    out += ["", f"**{flags} flagged trade(s).**"]
    (root / "paper_state").mkdir(exist_ok=True)
    (root / "paper_state" / "parity_ledger.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    if flags:
        ping(suffix="/fail")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
