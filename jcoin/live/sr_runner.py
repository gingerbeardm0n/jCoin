"""A_SR paper trader: spot-referenced stops, Coinbase nano fills (VALIDATION_RULES.md §9).

Runs alongside A (run_paper) with its own state in paper_state_sr/. Each hourly tick:
  1. For every newly closed 4h bar (Coinbase SPOT BTC-USD / ETH-USD):
     a. replay that bar's 1-minute candles for open positions: spot 1m high/low vs the
        stop, nano 1m high/low vs the resting disaster stop (2 ATR beyond the stop);
     b. at the bar close: time exit after 120 bars, else trail the stop from the spot
        bar's high/low;
     c. on the newest bar only: A's breakout entry, sized in whole nano contracts,
        filled at the nano 4h close.
  2. Replay 1-minute candles from the last closed bar up to now.
Exits: spot stop -> stop x (nano/spot close of that minute); disaster -> the resting
level (or the nano open if gapped); same minute -> the worse fill; time -> nano close.

Usage (VM, once):   python -m jcoin.live.sr_runner --init
Hourly (daemon):    python -m jcoin.live.sr_runner
Exit codes: 0 ok, 1 error, 5 hard-halt latch, 6 stale spot feed, 7 no state (use --init).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path

import polars as pl

from jcoin.data import coinbase_public as cb
from jcoin.data.config import COINBASE_MARKETS, CONTRACT_SIZES
from jcoin.engine.risk import RiskConfig, size_position
from jcoin.engine.types import EnterIntent, Side
from jcoin.live.ping import ping
from jcoin.research.backtest_breakout import _atr
from jcoin.strategy.breakout import detect_breakout
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND

log = logging.getLogger("jcoin.sr")

SPOT = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
NANO = {m.label: m.symbol for m in COINBASE_MARKETS}
LABELS = ["BTC", "ETH"]
BAR_MS, MIN_MS = 4 * 3600 * 1000, 60 * 1000
ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, DISASTER_ATR = 14, 1.0, 6.0, 120, 2.0
COST_FRAC = 0.0012
MAX_DD, MAX_STREAK = 0.398, 33
STALE_MS = 9 * 3600 * 1000
SPOT_BARS = 600


class CoinbaseData:
    """Network seam (public Coinbase endpoints only). Tests substitute a fake."""

    def bars_4h(self, pid: str, limit: int) -> list[list]:
        return cb.fetch_candles(pid, "4h", limit=limit)

    def minutes(self, pid: str, start_ms: int, end_ms: int) -> list[list]:
        n = (end_ms - start_ms) // MIN_MS + 5
        return [r for r in cb.fetch_candles(pid, "1m", since_ms=start_ms, limit=n) if r[0] < end_ms]

    def funding_rate(self, pid: str) -> float:
        return cb.current_funding_rate(pid)


def _closed(rows, bar_ms, now_ms):
    return [r for r in rows if r[0] + bar_ms <= now_ms]


class SRTrader:
    def __init__(self, state_dir="paper_state_sr", data=None, now_ms=None,
                 risk=RiskConfig(0.01, 1, 2, lot_sizes=dict(CONTRACT_SIZES))):
        self.dir = Path(state_dir)
        self.path = self.dir / "state.json"
        self.data = data or CoinbaseData()
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.risk = risk
        self.s: dict = {}
        self._min_cache: dict = {}

    # -- state ---------------------------------------------------------------
    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> None:
        self.s = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def init(self, equity: float) -> None:
        """Fresh paper clock: mark the latest closed spot bar as processed, no backfill."""
        now = self.now_ms()
        last = max(_closed(self.data.bars_4h(SPOT[l], 10), BAR_MS, now)[-1][0] for l in LABELS)
        self.s = {"equity": equity, "start_equity": equity, "peak": equity,
                  "clock_start_ms": now, "last_bar_ms": last, "positions": {}, "closed": [],
                  "nonwin_streak": 0, "hard_halted": False, "halt_reason": ""}
        self.save()
        log.info("A_SR paper clock started: equity %.2f, last bar %s", equity, _iso(last))

    # -- one tick ----------------------------------------------------------
    def tick(self) -> None:
        now = self.now_ms()
        self._min_cache = {}
        spot = {l: _closed(self.data.bars_4h(SPOT[l], SPOT_BARS), BAR_MS, now) for l in LABELS}
        newest = min(rows[-1][0] for rows in spot.values())
        if now - newest > STALE_MS:
            raise StaleFeed(f"newest closed spot 4h bar {_iso(newest)} is "
                            f"{(now - newest) / 3.6e6:.1f}h old")
        nano = {l: {r[0]: r for r in _closed(self.data.bars_4h(NANO[l], 200), BAR_MS, now)}
                for l in LABELS}
        new_bars = sorted({r[0] for rows in spot.values() for r in rows if r[0] > self.s["last_bar_ms"]})
        for b in new_bars:
            close_ms = b + BAR_MS
            for l in list(self.s["positions"]):
                self._replay_minutes(l, close_ms)
            for l in list(self.s["positions"]):
                self._bar_close(l, b, spot[l], nano[l])
            if b == new_bars[-1] and not self.s["hard_halted"]:
                for l in LABELS:
                    self._maybe_enter(l, b, spot[l], nano[l])
            self.s["last_bar_ms"] = b
        for l in list(self.s["positions"]):
            self._replay_minutes(l, now - now % MIN_MS)
        self.save()

    # -- internals -----------------------------------------------------------
    def _minutes(self, label, start_ms, end_ms):
        key = label
        cached = self._min_cache.get(key)
        if not cached or cached[0] > start_ms or cached[1] < end_ms:
            sp = {r[0]: r for r in self.data.minutes(SPOT[label], start_ms, end_ms)}
            na = {r[0]: r for r in self.data.minutes(NANO[label], start_ms, end_ms)}
            cached = self._min_cache[key] = (start_ms, end_ms, sp, na)
        _, _, sp, na = cached
        for m in sorted(set(sp) | set(na)):
            if start_ms <= m < end_ms:
                yield m, sp.get(m), na.get(m)

    def _replay_minutes(self, label, upto_ms):
        p = self.s["positions"][label]
        if upto_ms <= p["checked_ms"]:
            return
        long = p["side"] == "long"
        for m, s, f in self._minutes(label, p["checked_ms"], upto_ms):
            stop = p["stop"]
            d_fill = None
            if f is not None:
                d_level = (stop - DISASTER_ATR * p["atr"] if long else stop + DISASTER_ATR * p["atr"]) * p["basis"]
                if long and f[3] <= d_level:
                    d_fill = min(d_level, f[1])
                elif not long and f[2] >= d_level:
                    d_fill = max(d_level, f[1])
            basis_m = f[4] / s[4] if (f is not None and s is not None) else p["basis"]
            s_fill = None
            if s is not None and ((long and s[3] <= stop) or (not long and s[2] >= stop)):
                s_fill = stop * basis_m
            if d_fill is not None and s_fill is not None:
                worse = min(d_fill, s_fill) if long else max(d_fill, s_fill)
                return self._close(label, worse, m, "disaster" if worse == d_fill else "stop")
            if d_fill is not None:
                return self._close(label, d_fill, m, "disaster")
            if s_fill is not None:
                return self._close(label, s_fill, m, "stop")
            p["basis"] = basis_m
            if f is not None:
                p["last_price"] = f[4]
        p["checked_ms"] = upto_ms

    def _bar_close(self, label, b, spot_rows, nano_by_ts):
        p = self.s["positions"].get(label)
        if p is None or b <= p["entry_ms"]:
            return
        bar = next((r for r in spot_rows if r[0] == b), None)
        if bar is None:
            log.warning("A_SR %s: no spot bar at %s; trail not updated this bar", label, _iso(b))
            return
        n = nano_by_ts.get(b)
        if n is not None:
            p["last_price"] = n[4]
        p["bars_held"] += 1
        if p["bars_held"] >= MAX_HOLD:
            return self._close(label, n[4] if n else bar[4] * p["basis"], b + BAR_MS, "time")
        if p["side"] == "long":
            p["best"] = max(p["best"], bar[2])
            p["stop"] = max(p["stop"], p["best"] - ATR_TRAIL * p["atr"])
        else:
            p["best"] = min(p["best"], bar[3])
            p["stop"] = min(p["stop"], p["best"] + ATR_TRAIL * p["atr"])

    def _maybe_enter(self, label, b, spot_rows, nano_by_ts):
        if label in self.s["positions"] or len(self.s["positions"]) >= self.risk.max_concurrent:
            return
        rows = [r for r in spot_rows if r[0] <= b]
        if not rows or rows[-1][0] != b:
            return
        df = pl.DataFrame(rows, schema=["ts", "open", "high", "low", "close", "volume"], orient="row")
        df = df.with_columns(pl.from_epoch("ts", time_unit="ms").dt.replace_time_zone("UTC"))
        df2, sigs = detect_breakout(df, k=2)
        last = df2.height - 1
        sig = next((s for s in sigs if s["idx"] == last), None)
        if sig is None:
            return
        if (sig["side"] == "long" and sig["regime"] != REGIME_UPTREND) or \
           (sig["side"] == "short" and sig["regime"] != REGIME_DOWNTREND):
            return
        a = float(_atr(df2, ATR_PERIOD)[last])
        n = nano_by_ts.get(b)
        if a <= 0 or n is None:
            log.warning("A_SR %s signal at %s skipped: atr=%.4f nano bar %s", label, _iso(b), a,
                        "present" if n else "MISSING")
            return
        long = sig["side"] == "long"
        entry_ref, entry_fill = float(df2["close"][last]), float(n[4])
        basis = entry_fill / entry_ref
        stop = entry_ref - ATR_INIT * a if long else entry_ref + ATR_INIT * a
        intent = EnterIntent(label, Side.LONG if long else Side.SHORT, stop * basis, a, "A_SR")
        size, risk_dollars = size_position(self.s["equity"], intent, entry_fill, self.risk)
        if size <= 0:
            log.warning("A_SR %s %s signal at %s skipped by sizing (equity %.2f, 1 contract too big)",
                        label, sig["side"], _iso(b), self.s["equity"])
            return
        self.s["positions"][label] = {
            "side": sig["side"], "entry_ms": b, "entry_fill": entry_fill, "entry_ref": entry_ref,
            "stop": stop, "best": float(df2["high"][last] if long else df2["low"][last]),
            "atr": a, "size": size, "risk_dollars": risk_dollars, "basis": basis,
            "bars_held": 0, "checked_ms": b + BAR_MS, "last_price": entry_fill,
        }
        log.info("A_SR ENTER %s %s size=%g @ nano %.2f (spot %.2f, stop %.2f spot, risk $%.2f)",
                 label, sig["side"], size, entry_fill, entry_ref, stop, risk_dollars)

    def _close(self, label, exit_fill, exit_ms, kind):
        p = self.s["positions"].pop(label)
        d = 1 if p["side"] == "long" else -1
        notional = p["size"] * p["entry_fill"]
        hours = max(0.0, (exit_ms - (p["entry_ms"] + BAR_MS)) / 3.6e6)
        try:
            rate = self.data.funding_rate(NANO[label])
        except Exception as e:
            log.warning("A_SR funding rate unavailable for %s (%s); charging 0", label, e)
            rate = 0.0
        funding = d * rate * hours * notional  # + = paid
        pnl = d * p["size"] * (exit_fill - p["entry_fill"]) - COST_FRAC * notional - funding
        R = pnl / p["risk_dollars"]
        s = self.s
        s["equity"] += pnl
        s["peak"] = max(s["peak"], s["equity"])
        s["nonwin_streak"] = s["nonwin_streak"] + 1 if R <= 0 else 0
        s["closed"].append({"symbol": label, "side": p["side"], "entry_time": _iso(p["entry_ms"] + BAR_MS),
                            "exit_time": _iso(exit_ms), "entry_fill": p["entry_fill"], "exit_fill": exit_fill,
                            "size": p["size"], "pnl": pnl, "R": R, "funding": funding, "exit_kind": kind})
        log.info("A_SR EXIT %s %s %s @ %.2f R=%+.3f pnl=%+.2f equity=%.2f",
                 label, p["side"], kind, exit_fill, R, pnl, s["equity"])
        dd = 1 - s["equity"] / s["peak"]
        if not s["hard_halted"] and (dd > MAX_DD or s["nonwin_streak"] > MAX_STREAK):
            s["hard_halted"] = True
            s["halt_reason"] = f"drawdown {dd:.1%}" if dd > MAX_DD else f"{s['nonwin_streak']} non-winners"
            log.error("A_SR HARD HALT: %s -- flattening; human review required (KILL_RULE.md)",
                      s["halt_reason"])
            for other in list(s["positions"]):
                o = s["positions"][other]
                self._close(other, o["last_price"], exit_ms, "halt")


class StaleFeed(RuntimeError):
    pass


def _iso(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).isoformat(timespec="minutes")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A_SR paper trader (VALIDATION_RULES.md §9)")
    ap.add_argument("--state-dir", default="paper_state_sr")
    ap.add_argument("--init", action="store_true", help="start a fresh A_SR paper clock")
    ap.add_argument("--start-equity", type=float, default=1000.0)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    t = SRTrader(args.state_dir)
    if not t.exists():
        if not args.init:
            print(f"NO STATE: {t.path} missing -- restore a backup or run once with --init")
            ping(suffix="/fail")
            return 7
        t.init(args.start_equity)
        return 0
    t.load()
    if t.s["hard_halted"]:
        print(f"A_SR HALTED ({t.s['halt_reason']}) -- see KILL_RULE.md restart procedure")
        return 5
    try:
        t.tick()
    except StaleFeed as e:
        log.error("A_SR FEED STALE: %s", e)
        ping(suffix="/fail")
        return 6
    except Exception:
        log.exception("A_SR tick failed")
        ping(suffix="/fail")
        return 1
    s = t.s
    since = s["clock_start_ms"]
    rs = [c["R"] for c in s["closed"]]
    stats = (f"avgR={sum(rs) / len(rs):+.3f} over {len(rs)} trades" if rs else "0 trades")
    print(f"SUMMARY A_SR | equity=${s['equity']:,.2f} | open={len(s['positions'])} | {stats} "
          f"since {_iso(since)[:10]} | nonwin_streak={s['nonwin_streak']} | last_bar={_iso(s['last_bar_ms'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
