"""The ONE allowed sealed-window confirmation look (VALIDATION_RULES.md section 5).

Window: 2026-06-01 00:00 UTC -> 2026-09-30 23:59 UTC. A and B are run once each with their
FIXED configs. This CONFIRMS the already-decided winner; it does not select.

Nothing here writes into the repo's data/ tree. All sealed data lives in SCRATCH.
Dev data is read-only; it supplies warm-up history.

    python -m jcoin.research.sealed_confirmation fetch   # download Jun-Sep 2026 into SCRATCH
    python -m jcoin.research.sealed_confirmation run     # run A (0x/1x/2x), B main, BTC B&H
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import polars as pl

from jcoin.data.config import DATA_DIR
from jcoin.research import splits

UTC = dt.timezone.utc
SCRATCH = Path("C:/Users/joelb/AppData/Local/Temp/claude/C--Repositories/"
               "c097e0c2-3485-4880-b75c-d99c4e6a8eda/scratchpad/sealed")
WIN_LO = splits.SEALED_START                                   # 2026-06-01 00:00 UTC
WIN_HI = dt.datetime(2026, 10, 1, tzinfo=UTC)                  # exclusive
LAST_BAR_OPEN = dt.datetime(2026, 9, 30, 23, 59, tzinfo=UTC)   # inclusive bound for candles
MONTHS = ["2026-06", "2026-07", "2026-08", "2026-09"]
START_EQUITY = 10_000

_KBASE = "https://data.binance.vision/data/futures/um/monthly/klines"


# ----------------------------------------------------------------------------- fetch
def _month_url(sym: str, tf: str, ym: str) -> str:
    return f"{_KBASE}/{sym}/{tf}/{sym}-{tf}-{ym}.zip"


def fetch_all() -> None:
    from jcoin.data import fetch_binance_daily as fd
    from jcoin.data import fetch_binance_vision as fv
    from jcoin.data import fetch_funding_binance as ff

    # --- A: 1m BTC/ETH = dev 1m (< sealed start) + Jun-Sep monthly zips ---------------
    for label, sym in (("BTC", "BTCUSDT"), ("ETH", "ETHUSDT")):
        dev = pl.read_parquet(DATA_DIR / "ohlcv" / "binanceusdm" / label / "1m.parquet")
        dev = dev.filter(pl.col("ts") < int(WIN_LO.timestamp() * 1000))
        frames = [dev]
        for ym in MONTHS:
            blob = fv._download(_month_url(sym, "1m", ym))
            if blob is None:
                raise RuntimeError(f"missing {sym} 1m {ym}")
            f = fv._parse_zip(blob)
            print(f"  {label} 1m {ym}: {f.height} bars", flush=True)
            frames.append(f)
        out = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
        p = SCRATCH / "ohlcv" / "binanceusdm" / label / "1m.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        out.write_parquet(p)
        print(f"{label}: {out.height} bars, last {out['ts'].max()}")

    # --- A: funding (dev cache + sealed months) --------------------------------------
    new_dir = SCRATCH / "funding_new" / "binanceusdm"
    ff.FUNDING_DIR = new_dir                       # fetch_label reads this module global
    for label in ("BTC", "ETH"):
        new = ff.fetch_label(label, "2026-06", "2026-09", allow_sealed=True)
        dev = pl.read_parquet(DATA_DIR / "funding" / "binanceusdm" / label / "funding.parquet")
        dev = dev.filter(pl.col("ts") < int(WIN_LO.timestamp() * 1000))
        comb = pl.concat([dev, new]).unique(subset=["ts"], keep="last").sort("ts")
        p = SCRATCH / "funding" / "binanceusdm" / label / "funding.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        comb.write_parquet(p)
        print(ff.describe(label, comb))

    # --- B: daily klines, every symbol, dev copy + Jun-Sep ------------------------------
    syms = fd.list_usdt_symbols()
    print(f"{len(syms)} USDT symbols in bucket listing", flush=True)
    droot = SCRATCH / "binance_daily"

    def one(sym: str):
        frames = []
        devp = DATA_DIR / "ohlcv" / "binance_daily" / sym / "1d.parquet"
        if devp.exists():
            d = pl.read_parquet(devp)
            frames.append(d.filter(pl.col("ts") < WIN_LO))
        n_new = 0
        for ym in MONTHS:
            blob = fd._get(_month_url(sym, "1d", ym))
            if blob is None:
                continue
            f = fd._parse_zip(blob)
            frames.append(f)
            n_new += f.height
        if not frames:
            return sym, 0, 0
        out = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
        p = droot / sym / "1d.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        out.write_parquet(p)
        return sym, out.height, n_new

    res = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, r in enumerate(ex.map(one, syms), 1):
            res.append(r)
            if i % 100 == 0:
                print(f"  {i}/{len(syms)}", flush=True)
    with_new = sum(1 for _, _, n in res if n)
    print(f"daily: {len(res)} symbols written, {with_new} with Jun-Sep bars, "
          f"{sum(n for _, _, n in res)} new bars")
    (SCRATCH / "fetch_summary.json").write_text(json.dumps(
        {"symbols": len(res), "with_new": with_new, "new_bars": sum(n for _, _, n in res)}))


# ----------------------------------------------------------------------------- run: A
def _patch_for_A():
    """Point the repo's DataFeed at the scratch 1m files (read-only reuse of the harness)."""
    import jcoin.data.feed as feed
    from jcoin.data.config import partition_path as real

    def scratch_path(exchange, label, timeframe):
        p = SCRATCH / "ohlcv" / exchange / label / f"{timeframe}.parquet"
        return p

    feed.partition_path = scratch_path
    return real


def _evaluate_A(trades, lo, hi):
    from jcoin.research.portfolio_backtest import metrics, run_portfolio
    from jcoin.research.phase1_honest_a import (MAX_CONCURRENT, MAX_PER_SYMBOL, RISK_FRAC)
    splits.check_window(lo, hi, allow_sealed=True)
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    taken: list = []
    curve, R = run_portfolio(sub, START_EQUITY, RISK_FRAC, MAX_PER_SYMBOL, MAX_CONCURRENT,
                             taken_trades=taken)
    years = (hi - lo).days / 365.25
    m = metrics(curve, R, START_EQUITY, years)
    m["n_candidates"] = len(sub)
    m["funding_R_total"] = float(sum(t["funding_R"] for t in taken))
    return m, taken, curve


def _open_at_end(taken, label_candles):
    """Count taken trades still open at the final bar (marked to market at its close)."""
    from jcoin.research.backtest_breakout import _atr
    from jcoin.research.phase1_honest_a import ATR_INIT, ATR_PERIOD, ATR_TRAIL, MAX_HOLD
    from jcoin.strategy.breakout import detect_breakout
    out = []
    for t in taken:
        df = label_candles[t["symbol"]]
        ts = df["ts"].to_list()
        n = len(ts)
        if t["exit_time"] != ts[-1]:
            continue
        i = ts.index(t["entry_time"])
        if i + MAX_HOLD <= n - 1:
            continue                       # reached max_hold exactly at the last bar: not open
        # replay stop logic to see whether the last bar stopped it out
        d2, _ = detect_breakout(df, k=2)
        high, low, close = d2["high"].to_numpy(), d2["low"].to_numpy(), d2["close"].to_numpy()
        a = _atr(d2, ATR_PERIOD)[i]
        long = t["side"] == "long"
        entry = close[i]
        stop = entry - ATR_INIT * a if long else entry + ATR_INIT * a
        best = high[i] if long else low[i]
        stopped = False
        for j in range(i + 1, n):
            if long:
                if low[j] <= stop:
                    stopped = (j == n - 1)
                    break
                best = max(best, high[j]); stop = max(stop, best - ATR_TRAIL * a)
            else:
                if high[j] >= stop:
                    stopped = (j == n - 1)
                    break
                best = min(best, low[j]); stop = min(stop, best + ATR_TRAIL * a)
        if not stopped:
            out.append((t["symbol"], t["side"], str(t["entry_time"])))
    return out


def run_A():
    from jcoin.data.feed import DataFeed
    from jcoin.research.phase1_honest_a import (ATR_INIT, ATR_PERIOD, ATR_TRAIL, COST_FRAC,
                                                  LABELS, MAX_HOLD, TF)
    from jcoin.research.portfolio_backtest import build_trades
    _patch_for_A()
    splits.check_window(WIN_LO, WIN_HI, allow_sealed=True)
    fdir = SCRATCH / "funding" / "binanceusdm"
    candles = {l: DataFeed().get_candles(l, TF, end=LAST_BAR_OPEN) for l in LABELS}
    for l, df in candles.items():
        print(f"A candles {l}: {df.height} bars, last open {df['ts'].max()}")
    out = {}
    for mult in (1.0, 0.0, 2.0):
        trades = build_trades(TF, LABELS, ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, COST_FRAC,
                              funding_mult=mult, funding_dir=fdir, end=LAST_BAR_OPEN)
        m, taken, curve = _evaluate_A(trades, WIN_LO, WIN_HI)
        m["open_at_end"] = _open_at_end(taken, candles)
        m["trades_list"] = [(t["symbol"], t["side"], str(t["entry_time"]), str(t["exit_time"]),
                             round(t["R"], 3)) for t in taken]
        out[mult] = m
        print(f"A funding {mult:g}x: n={m['n_trades']} ret={m['total_ret']*100:.2f}% "
              f"maxDD={m['max_dd']*100:.2f}% avgR={m['avg_R']:.3f} win={m['win_pct']:.1f}% "
              f"final={m['final_equity']:.0f} open_at_end={len(m['open_at_end'])} "
              f"fundR={m['funding_R_total']:+.2f}")
    return out


# ----------------------------------------------------------------------------- run: B
def load_panel_scratch(start="2020-01-01"):
    from jcoin.research.basket_trend_backtest import Panel
    t0 = dt.datetime.fromisoformat(start).replace(tzinfo=UTC)
    root = SCRATCH / "binance_daily"
    frames = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f = d / "1d.parquet"
        if f.exists():
            df = pl.read_parquet(f).filter(pl.col("ts") < WIN_HI)
            if df.height:
                frames[d.name] = df
    n_days = (WIN_HI.date() - t0.date()).days
    dates = np.array([np.datetime64(t0.date()) + np.timedelta64(i, "D") for i in range(n_days)])
    syms = sorted(frames)
    o = np.full((n_days, len(syms)), np.nan)
    c, q = o.copy(), o.copy()
    base = np.datetime64(t0.date())
    for j, s in enumerate(syms):
        df = frames[s]
        di = (df["ts"].dt.date().to_numpy().astype("datetime64[D]") - base).astype(int)
        ok = (di >= 0) & (di < n_days)
        o[di[ok], j] = df["open"].to_numpy()[ok]
        c[di[ok], j] = df["close"].to_numpy()[ok]
        q[di[ok], j] = df["quote_volume"].to_numpy()[ok]
    return Panel(dates, syms, o, c, q)


def _curve_stats(equity, flat_days_before):
    curve = np.concatenate([np.ones(flat_days_before + 1), equity])   # 1.0 then daily closes
    peak = np.maximum.accumulate(curve)
    return {"total_ret": float(curve[-1] - 1.0), "max_dd": float(np.max((peak - curve) / peak)),
            "final_equity": float(START_EQUITY * curve[-1])}


def run_B():
    import jcoin.research.basket_trend_backtest as bt
    splits.check_window(WIN_LO, WIN_HI, allow_sealed=True)
    real_check = bt.check_window
    # simulate() calls check_window without opt-in; allow it for this single window only.
    bt.check_window = lambda s, e, allow_sealed=False: real_check(
        s, e, allow_sealed=(allow_sealed or e <= WIN_HI))
    panel = load_panel_scratch()
    print(f"B panel: {len(panel.symbols)} symbols, {panel.dates[0]} -> {panel.dates[-1]}")
    end_i = len(panel.dates)
    i_win = int((np.datetime64(WIN_LO.date()) - panel.dates[0]) / np.timedelta64(1, "D"))
    i_dev0 = int((np.datetime64(splits.DEV_START.date()) - panel.dates[0]) / np.timedelta64(1, "D"))
    # first rebalance >= 2026-06-01 on the dev schedule (every 14 days from 2021-01-01)
    k = -(-(i_win - i_dev0) // bt.REBAL_DAYS)
    i_rebal = i_dev0 + k * bt.REBAL_DAYS
    print(f"B first rebalance on dev 14-day grid >= 2026-06-01: {panel.dates[i_rebal]} "
          f"(flat/cash {i_rebal - i_win} days before)")
    cfg = bt.CONFIGS[0]
    assert cfg.name.startswith("B main")
    res = bt.simulate(panel, cfg, i_rebal, end_i)
    st = _curve_stats(res.equity, i_rebal - i_win)
    n_reb = sum(1 for e in res.log if "universe" in e)
    n_orders = int(res.n_trades.sum())
    costs = float(res.costs.sum())
    st.update(rebalances=n_reb, orders=n_orders, cost=costs,
              avg_held=float(res.n_held.mean()), final_held=int(res.n_held[-1]))
    st["rebal_dates"] = [str(panel.dates[e["i"]]) for e in res.log if "universe" in e]
    st["longs_per_rebal"] = [len(e["longs"]) for e in res.log if "universe" in e]
    print("B main:", {k: v for k, v in st.items() if k not in ("rebal_dates",)})

    bh_cfg = [c for c in bt.CONFIGS if c.name.startswith("BM: BTC")][0]
    bh = bt.simulate(panel, bh_cfg, i_win, end_i)
    bst = _curve_stats(bh.equity, 0)
    bst["bnh_from_rebal_total_ret"] = None
    bh2 = bt.simulate(panel, bh_cfg, i_rebal, end_i)
    bst["from_rebal_date"] = _curve_stats(bh2.equity, 0)["total_ret"]
    print("BTC B&H (06-01, incl 0.5% entry cost):", bst)
    # raw price move for reference
    j = panel.symbols.index("BTCUSDT")
    raw = panel.close[end_i - 1, j] / panel.open[i_win, j] - 1
    bst["raw_price_ret"] = float(raw)
    print(f"BTC raw open(06-01)->close(09-30): {raw*100:.2f}%")
    return st, bst


def main(argv=None) -> int:
    cmd = (argv or sys.argv[1:] or [""])[0]
    if cmd == "fetch":
        fetch_all()
    elif cmd == "run":
        A = run_A()
        B, BH = run_B()
        (SCRATCH / "results.json").write_text(json.dumps(
            {"A": {str(k): v for k, v in A.items()}, "B": B, "BH": BH}, default=str, indent=1))
        print("saved", SCRATCH / "results.json")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
