"""§8 test: A vs A_SR (spot-referenced stops, nano fills). VALIDATION_RULES.md §8.

A_SR runs A's signals, ATR, trailing stop and stop trigger on Coinbase SPOT 4h bars and
fills on Coinbase nano perp bars, with a resting nano disaster stop 2 ATR beyond the stop.

Usage:
    python -m jcoin.research.spot_stop_test
Writes pipeline/SPOT_STOP_TEST_2026-10.md. Spot candles are cached under
data/ohlcv/coinbase_spot/<coin>/4h.parquet.
"""

from __future__ import annotations

import datetime as dt
import sys

import polars as pl

from jcoin.data.config import DATA_DIR, ROOT
from jcoin.research import splits
from jcoin.research.backtest_breakout import _atr
from jcoin.research.close_stop_test import CB_HI, CB_LO, row, trades
from jcoin.research.coinbase_parity import PRODUCTS, fetch_coinbase_4h
from jcoin.research.phase1_honest_a import (
    ATR_INIT, ATR_PERIOD, ATR_TRAIL, COST_FRAC, LABELS, MAX_HOLD, _END, evaluate,
)
from jcoin.strategy.breakout import detect_breakout
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND

UTC = dt.timezone.utc
SPOT_PRODUCTS = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
SPOT_START = dt.datetime(2020, 9, 1, tzinfo=UTC)  # warm-up before the 2021 dev start
DISASTER_ATR = 2.0
REPORT_PATH = ROOT / "pipeline" / "SPOT_STOP_TEST_2026-10.md"


def spot_4h(coin: str) -> pl.DataFrame:
    path = DATA_DIR / "ohlcv" / "coinbase_spot" / coin / "4h.parquet"
    if path.exists():
        df = pl.read_parquet(path)
        if df["ts"].max() >= _END - dt.timedelta(hours=4):
            return df.filter(pl.col("ts") <= _END)
    df = fetch_coinbase_4h(SPOT_PRODUCTS[coin], SPOT_START, _END)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return df.filter(pl.col("ts") <= _END)


def ref_trades(ref: dict, fill: dict, disaster_atr: float | None = DISASTER_ATR,
               atr_init=ATR_INIT, atr_trail=ATR_TRAIL, max_hold=MAX_HOLD, cost_frac=COST_FRAC):
    """A's intrabar logic on `ref` bars, filled on `fill` bars (both {label: 4h frame}).

    With ref is fill and disaster_atr=None this reproduces build_trades(stop_mode="intrabar").
    Each trade also records `exit_kind` in {"stop", "disaster", "time"}.
    """
    out = []
    for label in ref:
        df2, sigs = detect_breakout(ref[label], k=2)
        hi, lo, cl = (df2[c].to_numpy() for c in ("high", "low", "close"))
        ts = df2["ts"].to_list()
        atr = _atr(df2, ATR_PERIOD)
        fb = {r["ts"]: r for r in fill[label].select("ts", "open", "high", "low", "close").to_dicts()}
        n = len(cl)
        for s in sigs:
            if s["side"] == "long" and s["regime"] != REGIME_UPTREND:
                continue
            if s["side"] == "short" and s["regime"] != REGIME_DOWNTREND:
                continue
            i = s["idx"]
            if i + 1 >= n or atr[i] <= 0 or ts[i] not in fb:
                continue
            long = s["side"] == "long"
            a = atr[i]
            entry_ref, entry_fill = cl[i], fb[ts[i]]["close"]
            stop = entry_ref - atr_init * a if long else entry_ref + atr_init * a
            stop_dist = abs(entry_ref - stop) / entry_ref
            best = hi[i] if long else lo[i]
            basis = entry_fill / entry_ref
            exit_fill, exit_idx, kind = None, min(i + max_hold, n - 1), "time"
            for j in range(i + 1, min(i + 1 + max_hold, n)):
                f = fb.get(ts[j])
                hit_ref = lo[j] <= stop if long else hi[j] >= stop
                d_fill = None
                if disaster_atr is not None and f is not None:
                    d_level = (stop - disaster_atr * a if long else stop + disaster_atr * a) * basis
                    if long and f["low"] <= d_level:
                        d_fill = min(d_level, f["open"])
                    elif not long and f["high"] >= d_level:
                        d_fill = max(d_level, f["open"])
                if f is not None:
                    basis_j = f["close"] / cl[j]
                else:
                    basis_j = basis
                s_fill = stop * basis_j if hit_ref else None
                if d_fill is not None and s_fill is not None:
                    worse = min(d_fill, s_fill) if long else max(d_fill, s_fill)
                    exit_fill, exit_idx, kind = worse, j, "disaster" if worse == d_fill else "stop"
                    break
                if d_fill is not None:
                    exit_fill, exit_idx, kind = d_fill, j, "disaster"
                    break
                if s_fill is not None:
                    exit_fill, exit_idx, kind = s_fill, j, "stop"
                    break
                if f is not None:
                    basis = basis_j
                best = max(best, hi[j]) if long else min(best, lo[j])
                stop = max(stop, best - atr_trail * a) if long else min(stop, best + atr_trail * a)
            if exit_fill is None:
                f = fb.get(ts[exit_idx])
                exit_fill = f["close"] if f is not None else cl[exit_idx] * basis
            gross = (exit_fill - entry_fill) / entry_fill if long else (entry_fill - exit_fill) / entry_fill
            out.append({"symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
                        "side": s["side"], "R": (gross - cost_frac) / stop_dist, "funding_R": 0.0,
                        "exit_kind": kind})
    return sorted(out, key=lambda t: t["entry_time"])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    splits.check_window(CB_LO, CB_HI)

    spot = {c: spot_4h(c) for c in LABELS}
    nano = {c: fetch_coinbase_4h(p, dt.datetime(2025, 6, 1, tzinfo=UTC), _END) for c, p in PRODUCTS.items()}
    # A_SR signals need spot warm-up before nano starts; trades are then limited to the window.
    a_nano = trades("intrabar", 0.0, nano)
    a_sr = ref_trades(spot, nano)
    a_bin = trades("intrabar", 0.0)
    a_spot = trades("intrabar", 0.0, spot)

    cb = {"A on nano": evaluate(a_nano, CB_LO, CB_HI), "A_SR (spot stops, nano fills)": evaluate(a_sr, CB_LO, CB_HI),
          "A on Binance (report only)": evaluate(a_bin, CB_LO, CB_HI),
          "A on Coinbase spot (report only)": evaluate(a_spot, CB_LO, CB_HI)}
    dev = {"A on Binance (0x funding)": evaluate(a_bin, lo, hi), "A on Coinbase spot": evaluate(a_spot, lo, hi)}

    hdr = ["| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |", "|---|---|---|---|---|---|---|---|---|"]
    a_pf, sr = cb["A on nano"]["pf"], cb["A_SR (spot stops, nano fills)"]
    b, sp = dev["A on Binance (0x funding)"], dev["A on Coinbase spot"]
    c1 = sr["pf"] >= 1.0 and sr["pf"] > a_pf
    c2 = sp["sharpe"] >= 0.9 * b["sharpe"] and sp["mar"] >= 0.9 * b["mar"]

    win = [t for t in a_sr if CB_LO <= t["entry_time"] < CB_HI]
    kinds = {k: sum(1 for t in win if t["exit_kind"] == k) for k in ("stop", "disaster", "time")}
    key = lambda t: (t["symbol"], t["entry_time"], t["side"])
    nano_by = {key(t): t for t in a_nano if CB_LO <= t["entry_time"] < CB_HI}
    common = [(t, nano_by[key(t)]) for t in win if key(t) in nano_by]
    common.sort(key=lambda p: -abs(p[0]["R"] - p[1]["R"]))

    out = ["# §8: A vs A_SR (spot-referenced stops, nano fills)", "",
           "Protocol: `VALIDATION_RULES.md` §8, committed in `228de57` before this script existed.", "",
           f"## 1. Coinbase window {CB_LO:%Y-%m-%d} → 2026-05-31 (12bp, no funding)", ""] + hdr
    out += [row(k, v) for k, v in cb.items()]
    out += ["", f"A_SR candidate trades in window (before the portfolio's 1/symbol, 2-concurrent caps): "
                f"{kinds['stop']} spot stops, {kinds['disaster']} nano disaster stops, {kinds['time']} time exits. "
                f"Candidates common to A-on-nano and A_SR (same entry bar/side): {len(common)}.",
            "", "Largest per-trade differences (report only):", "",
            "| Symbol | Entry | Side | A on nano R | A_SR R | A_SR exit |", "|---|---|---|---|---|---|"]
    out += [f"| {s['symbol']} | {s['entry_time']:%Y-%m-%d %H:%M} | {s['side']} | {n['R']:+.2f} | {s['R']:+.2f} | {s['exit_kind']} |"
            for s, n in common[:10]]
    out += ["", "## 2. Dev period 2021-01-01 → 2026-05-31 (12bp, no funding)", ""] + hdr + [row(k, v) for k, v in dev.items()]
    out += ["", "## Decision (§8, both required)", "",
            f"1. A_SR Coinbase PF {sr['pf']:.2f} ≥ 1.00 and > A on nano {a_pf:.2f} → {'yes' if c1 else 'no'}",
            f"2. Spot dev Sharpe {sp['sharpe']:.2f} ≥ 0.90×{b['sharpe']:.2f}={0.9*b['sharpe']:.2f} and "
            f"MAR {sp['mar']:.2f} ≥ 0.90×{b['mar']:.2f}={0.9*b['mar']:.2f} → {'yes' if c2 else 'no'}",
            "", f"**Verdict: {'ADOPT A_SR for paper' if (c1 and c2) else 'DO NOT ADOPT A_SR'}**"]
    REPORT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
