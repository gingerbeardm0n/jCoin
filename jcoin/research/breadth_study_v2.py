"""Breadth study v2 — top ~50 coins by market cap.

Extends v1 (17 coins) with ~35 additional liquid USDT-perp markets.
Same shared config, same KEEP rule (PF>=1.2 AND MAR>=0.5).
Reuses existing 4h parquets where available; downloads new ones.

Usage:
    python -m jcoin.research.breadth_study_v2
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from jcoin.data.config import partition_path
from jcoin.data.fetch_binance_vision import _BASE, _download, _month_range, _parse_zip
from jcoin.engine.features import compute_features
from jcoin.research.portfolio_backtest import metrics, run_portfolio

TF = "4h"
START = "2019-01"   # fetch as far back as available; coins launched later get partial history
K, ATRP, INIT, TRAIL, HOLD = 2, 14, 1.0, 6.0, 120
COST_FRAC, RISK = 0.0012, 0.01
MIN_TRADES = 15
MIN_YEARS = 2.0     # require at least 2 years of history to be meaningful

# Full universe: original 17 + ~35 new = ~52 total
# Grouped roughly by market-cap tier
UNIVERSE = [
    # --- original 17 (parquets likely cached from 2021) ---
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "LTCUSDT", "BCHUSDT", "ATOMUSDT", "NEARUSDT", "UNIUSDT",
    "FILUSDT", "ETCUSDT",
    # --- new: large-cap with long history ---
    "TRXUSDT",    # Tron
    "XLMUSDT",    # Stellar
    "VETUSDT",    # VeChain
    "ALGOUSDT",   # Algorand
    "XTZUSDT",    # Tezos
    "EOSUSDT",    # EOS
    "KSMUSDT",    # Kusama
    "WAVESUSDT",  # Waves
    "ZILUSDT",    # Zilliqa
    "ONEUSDT",    # Harmony
    "THETAUSDT",  # Theta
    "EGLDUSDT",   # MultiversX (Elrond)
    "ICPUSDT",    # Internet Computer
    "FLOWUSDT",   # Flow
    # --- DeFi blue chips ---
    "AAVEUSDT",   # Aave
    "MKRUSDT",    # Maker
    "SNXUSDT",    # Synthetix
    "CRVUSDT",    # Curve
    "COMPUSDT",   # Compound
    "GRTUSDT",    # The Graph
    "RUNEUSDT",   # THORChain
    "INJUSDT",    # Injective
    "LDOUSDT",    # Lido
    # --- Gaming/Metaverse ---
    "AXSUSDT",    # Axie Infinity
    "SANDUSDT",   # The Sandbox
    "MANAUSDT",   # Decentraland
    "ENJUSDT",    # Enjin
    # --- Layer 2 / newer L1 ---
    "MATICUSDT",  # Polygon
    "STXUSDT",    # Stacks
    "IMXUSDT",    # Immutable X
    "APTUSDT",    # Aptos (2022)
    "ARBUSDT",    # Arbitrum (2023)
    "OPUSDT",     # Optimism (2022)
    "SUIUSDT",    # Sui (2023)
    # --- Other ---
    "HBARUSDT",   # Hedera (user owns)
    "STXUSDT",    # already above, dedupe handled
]

# Deduplicate preserving order
seen = set()
UNIVERSE = [x for x in UNIVERSE if not (x in seen or seen.add(x))]


def _fetch_4h(symbol: str, label: str) -> pl.DataFrame:
    path = partition_path("binanceusdm", label, TF)
    if path.exists():
        df = pl.read_parquet(path)
        # Check if we have pre-2021 history; if not and start is earlier, try to extend
        ts_min = df["ts"].min()
        # ts is in ms; 2021-01-01 = 1609459200000
        if ts_min is not None and ts_min > 1609459200000 + 86400000 * 7:
            # Existing parquet starts after Jan 2021 — try to prepend earlier months
            start_date = dt.datetime.strptime(START, "%Y-%m").date().replace(day=1)
            first_month_in_parquet = dt.datetime.utcfromtimestamp(ts_min / 1000).date().replace(day=1)
            if start_date < first_month_in_parquet:
                frames = []
                last_before = first_month_in_parquet - dt.timedelta(days=1)
                for y, m in _month_range(start_date, last_before):
                    blob = _download(
                        f"{_BASE}/monthly/klines/{symbol}/{TF}/{symbol}-{TF}-{y}-{m:02d}.zip"
                    )
                    if blob:
                        frames.append(_parse_zip(blob))
                if frames:
                    prepend = pl.concat(frames)
                    df = pl.concat([prepend, df]).unique(subset=["ts"], keep="last").sort("ts")
                    df.write_parquet(path)
        return df

    path.parent.mkdir(parents=True, exist_ok=True)
    start_date = dt.datetime.strptime(START, "%Y-%m").date().replace(day=1)
    today = dt.datetime.now(dt.timezone.utc).date()
    last_complete = today.replace(day=1) - dt.timedelta(days=1)
    frames = []
    for y, m in _month_range(start_date, last_complete):
        blob = _download(
            f"{_BASE}/monthly/klines/{symbol}/{TF}/{symbol}-{TF}-{y}-{m:02d}.zip"
        )
        if blob:
            frames.append(_parse_zip(blob))
    if not frames:
        raise RuntimeError(f"no 4h data for {symbol}")
    df = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
    df.write_parquet(path)
    return df


def _load_features(symbol: str, label: str) -> pl.DataFrame:
    df = _fetch_4h(symbol, label)
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    ).sort("ts")
    return compute_features(df, k=K, atr_period=ATRP)


def _sim(feat: pl.DataFrame, label: str):
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
        stop = entry - INIT * a if long else entry + INIT * a
        sd = abs(entry - stop) / entry
        if sd <= 0:
            continue
        best = high[i] if long else low[i]
        exit_price, exit_idx = None, min(i + HOLD, n - 1)
        for j in range(i + 1, min(i + 1 + HOLD, n)):
            if long:
                if low[j] <= stop:
                    exit_price, exit_idx = stop, j; break
                best = max(best, high[j]); stop = max(stop, best - TRAIL * a)
            else:
                if high[j] >= stop:
                    exit_price, exit_idx = stop, j; break
                best = min(best, low[j]); stop = min(stop, best + TRAIL * a)
        if exit_price is None:
            exit_price = close[exit_idx]
        gross = (exit_price - entry) / entry if long else (entry - exit_price) / entry
        trades.append({"symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
                       "side": "long" if long else "short", "R": (gross - COST_FRAC) / sd})
    return sorted(trades, key=lambda t: t["entry_time"])


def _metrics(trades):
    if len(trades) < MIN_TRADES:
        return None
    curve, R = run_portfolio(trades, 10_000, RISK, 1, 1)
    span = (trades[-1]["exit_time"] - trades[0]["entry_time"]).days / 365.25
    if span < MIN_YEARS:
        return None
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    pos = 0; total = 0
    for yr in range(2019, 2027):
        lo = dt.datetime(yr, 1, 1, tzinfo=dt.timezone.utc)
        hi = dt.datetime(yr + 1, 1, 1, tzinfo=dt.timezone.utc)
        sub = [t for t in trades if lo <= t["entry_time"] < hi]
        if len(sub) >= 8:
            total += 1
            c2, R2 = run_portfolio(sub, 10_000, RISK, 1, 1)
            if c2 and c2[-1][1] > 10_000:
                pos += 1
    m["yrs_pos"] = f"{pos}/{total}"
    return m


def main() -> int:
    print(f"BREADTH STUDY v2 — {len(UNIVERSE)} coins | shared config "
          f"init={INIT}/trail={TRAIL} k={K} atrp={ATRP} | 4h | cost=12bp\n")
    rows = []
    errors = []
    for sym in UNIVERSE:
        label = sym.replace("USDT", "")
        try:
            feat = _load_features(sym, label)
            m = _metrics(_sim(feat, label))
            if m:
                rows.append((label, m))
                keep = m["pf"] >= 1.2 and m["mar"] >= 0.5
                print(f"  {label:<6} PF={m['pf']:.2f} MAR={m['mar']:.2f} "
                      f"{'<- KEEP' if keep else ''}", flush=True)
            else:
                print(f"  {label:<6} (insufficient history / trades)", flush=True)
        except Exception as e:
            errors.append((label, str(e)))
            print(f"  {label:<6} ERROR: {e}", flush=True)

    rows.sort(key=lambda r: r[1]["mar"], reverse=True)

    print(f"\n{'coin':<6} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} "
          f"{'Sharpe':>6} {'win%':>5} {'n':>4} {'yrs+':>5}")
    print("-" * 65)
    keepers = []
    for label, m in rows:
        flag = "  <- KEEP" if (m["pf"] >= 1.2 and m["mar"] >= 0.5) else (
               "  x weak" if m["pf"] < 1.05 else "")
        if m["pf"] >= 1.2 and m["mar"] >= 0.5:
            keepers.append(label)
        print(f"{label:<6} {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
              f"{m['mar']:>5.2f} {m['pf']:>5.2f} {m['sharpe']:>6.2f} "
              f"{m['win_pct']:>4.0f}% {m['n_trades']:>4} {m['yrs_pos']:>5}{flag}")

    print(f"\nKEEPERS (PF>=1.2 AND MAR>=0.5): {keepers}")
    if errors:
        print(f"\nErrors ({len(errors)}): {[e[0] for e in errors]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
