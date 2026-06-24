"""Sealed train/validate/test for XRP, HBAR, AVAX using their grid-optimal configs.

Each coin uses the config from its broad plateau zone, not the shared default.
Gate same as before: TEST split PF>=1.15 AND MAR>=0.40.
BTC+ETH included as control sanity check.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from jcoin.data.config import partition_path
from jcoin.data.fetch_binance_vision import _BASE, _download, _month_range, _parse_zip
from jcoin.engine.features import compute_features
from jcoin.research.portfolio_backtest import metrics, run_portfolio

UTC = dt.timezone.utc
TF = "4h"
START = "2021-01"
K, ATRP = 2, 14
COST_FRAC, RISK = 0.0012, 0.01
HOLD = 120

SPLITS = [
    ("train(21-23)",  dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
    ("valid(23-25)",  dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    ("TEST(25-26)*",  dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
]

# (label, symbol, init, trail, note)
COINS = [
    ("BTC",  "BTCUSDT",  1.0, 6.0,  "shared config [CONTROL]"),
    ("ETH",  "ETHUSDT",  1.0, 6.0,  "shared config [CONTROL]"),
    ("XRP",  "XRPUSDT",  1.0, 5.0,  "plateau best (17/28 PF>=1.2) [CAND]"),
    ("HBAR", "HBARUSDT", 1.5, 10.0, "plateau best (19/28 PF>=1.2) [CAND]"),
    ("AVAX", "AVAXUSDT", 2.0, 8.0,  "plateau best (12/28 PF>=1.2) [CAND]"),
]

GATE_PF  = 1.15
GATE_MAR = 0.40


def _fetch_4h(symbol: str, label: str) -> pl.DataFrame:
    path = partition_path("binanceusdm", label, TF)
    if path.exists():
        return pl.read_parquet(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    start_date = dt.datetime.strptime(START, "%Y-%m").date().replace(day=1)
    today = dt.datetime.now(dt.timezone.utc).date()
    last_complete = today.replace(day=1) - dt.timedelta(days=1)
    frames = []
    for y, m in _month_range(start_date, last_complete):
        blob = _download(f"{_BASE}/monthly/klines/{symbol}/{TF}/{symbol}-{TF}-{y}-{m:02d}.zip")
        if blob:
            frames.append(_parse_zip(blob))
    if not frames:
        raise RuntimeError(f"no 4h data for {symbol}")
    df = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
    df.write_parquet(path)
    return df


def _load(symbol: str, label: str) -> pl.DataFrame:
    df = _fetch_4h(symbol, label)
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    ).sort("ts")
    return compute_features(df, k=K, atr_period=ATRP)


def _sim(feat: pl.DataFrame, label: str, init: float, trail: float):
    high = feat["high"].to_numpy(); low = feat["low"].to_numpy()
    close = feat["close"].to_numpy(); atr = feat["atr"].to_numpy()
    regime = feat["regime"].to_numpy()
    bl = feat["brk_long"].to_numpy(); bs = feat["brk_short"].to_numpy()
    ts = feat["ts"].to_list()
    n = len(close); trades = []
    for i in range(n):
        if bl[i] and regime[i] == "uptrend":
            long = True
        elif bs[i] and regime[i] == "downtrend":
            long = False
        else:
            continue
        if i + 1 >= n or atr[i] <= 0:
            continue
        entry, a = close[i], atr[i]
        stop = entry - init * a if long else entry + init * a
        sd = abs(entry - stop) / entry
        if sd <= 0:
            continue
        best = high[i] if long else low[i]
        exit_price, exit_idx = None, min(i + HOLD, n - 1)
        for j in range(i + 1, min(i + 1 + HOLD, n)):
            if long:
                if low[j] <= stop:
                    exit_price, exit_idx = stop, j; break
                best = max(best, high[j]); stop = max(stop, best - trail * a)
            else:
                if high[j] >= stop:
                    exit_price, exit_idx = stop, j; break
                best = min(best, low[j]); stop = min(stop, best + trail * a)
        if exit_price is None:
            exit_price = close[exit_idx]
        gross = (exit_price - entry) / entry if long else (entry - exit_price) / entry
        trades.append({"symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
                       "side": "long" if long else "short", "R": (gross - COST_FRAC) / sd})
    return sorted(trades, key=lambda t: t["entry_time"])


def _eval(trades, lo, hi):
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 8:
        return None
    curve, R = run_portfolio(sub, 10_000, RISK, 1, 1)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def main() -> int:
    print(f"SEALED VALIDATION | gate PF>={GATE_PF} AND MAR>={GATE_MAR} on TEST split\n")
    print(f"{'coin':<6} {'config':<22} {'split':<14} {'CAGR':>6} {'maxDD':>6} "
          f"{'MAR':>5} {'PF':>5} {'n':>4}  result")
    print("-" * 85)

    verdicts = {}
    for label, sym, init, trail, note in COINS:
        try:
            feat = _load(sym, label)
        except Exception as e:
            print(f"{label:<6}  ERROR: {e}")
            continue
        trades = _sim(feat, label, init, trail)
        cfg_str = f"i={init}/t={trail}"
        test_m = None
        for sname, lo, hi in SPLITS:
            m = _eval(trades, lo, hi)
            is_test = "TEST" in sname
            if is_test:
                test_m = m
            if m:
                flag = ""
                if is_test:
                    ok = m["pf"] >= GATE_PF and m["mar"] >= GATE_MAR
                    flag = "  PASS" if ok else "  FAIL"
                print(f"{label:<6} {cfg_str:<22} {sname:<14} {m['cagr']*100:>5.0f}% "
                      f"{m['max_dd']*100:>5.0f}% {m['mar']:>5.2f} {m['pf']:>5.2f} "
                      f"{m['n_trades']:>4}  {flag}")
            else:
                print(f"{label:<6} {cfg_str:<22} {sname:<14}  (too few trades)")
        verdicts[label] = (test_m, init, trail, note)
        print()

    print("=" * 85)
    print(f"\nSUMMARY — gate PF>={GATE_PF} AND MAR>={GATE_MAR}\n")
    passed = []
    for label, (test_m, init, trail, note) in verdicts.items():
        if test_m:
            ok = test_m["pf"] >= GATE_PF and test_m["mar"] >= GATE_MAR
            status = "PASS -> add to universe" if ok else "FAIL -> skip"
            if ok:
                passed.append(label)
            print(f"  {label:<5} PF={test_m['pf']:.2f}  MAR={test_m['mar']:.2f}  "
                  f"config i={init}/t={trail}  {status}")
            print(f"        {note}")
        else:
            print(f"  {label:<5} insufficient TEST data")
        print()
    print(f"Coins passing gate: {passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
