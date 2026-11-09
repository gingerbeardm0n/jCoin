"""§10 breadth test: strategy A on every other Coinbase US perp coin. VALIDATION_RULES.md §10.

Usage:
    python -m jcoin.research.breadth_coinbase
Writes pipeline/BREADTH_COINBASE_2026-11.md. Binance USD-M 4h data is cached under
data/ohlcv/binanceusdm/<coin>/4h.parquet (fetched via breadth_study._fetch_4h).
"""

from __future__ import annotations

import datetime as dt
import sys

import polars as pl

from jcoin.data.config import ROOT
from jcoin.data.feed import DataFeed
from jcoin.research import splits
from jcoin.research.breadth_study import _fetch_4h
from jcoin.research.phase1_honest_a import ATR_INIT, ATR_PERIOD, ATR_TRAIL, COST_FRAC, MAX_HOLD, TF, _END
from jcoin.research.portfolio_backtest import build_trades, metrics, run_portfolio

UTC = dt.timezone.utc
REPORT_PATH = ROOT / "pipeline" / "BREADTH_COINBASE_2026-11.md"
CANDIDATES = {  # label -> Binance USD-M symbol
    "ADA": "ADAUSDT", "AAVE": "AAVEUSDT", "AVAX": "AVAXUSDT", "BCH": "BCHUSDT", "BNB": "BNBUSDT",
    "DOGE": "DOGEUSDT", "ENA": "ENAUSDT", "HBAR": "HBARUSDT", "HYPE": "HYPEUSDT", "LTC": "LTCUSDT",
    "LINK": "LINKUSDT", "NEAR": "NEARUSDT", "ONDO": "ONDOUSDT", "PEPE": "1000PEPEUSDT", "DOT": "DOTUSDT",
    "SHIB": "1000SHIBUSDT", "SOL": "SOLUSDT", "SUI": "SUIUSDT", "XLM": "XLMUSDT", "XRP": "XRPUSDT",
    "ZEC": "ZECUSDT",
}
UNSEEN = {"ENA", "HYPE", "ONDO", "PEPE", "SHIB", "ZEC"}
BASE = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
WARMUP = dt.timedelta(days=60)
MIN_YEARS = 1.5
START_EQUITY, RISK = 10_000.0, 0.01


def load(label: str, symbol: str) -> pl.DataFrame | None:
    try:
        df = _fetch_4h(symbol, label)
    except RuntimeError:
        return None
    df = df.with_columns(pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts"))
    return df.sort("ts").filter(pl.col("ts") <= _END)


def trades_for(frames: dict) -> list[dict]:
    orig = DataFeed.get_candles
    DataFeed.get_candles = lambda self, label, tf, start=None, end=None, **kw: frames[label]
    try:
        return build_trades(TF, list(frames), ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, COST_FRAC,
                            funding_mult=0.0, end=_END)
    finally:
        DataFeed.get_candles = orig


def portfolio(trades, lo, hi, max_concurrent):
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 2:
        return None, []
    taken: list = []
    curve, R = run_portfolio(sub, START_EQUITY, RISK, 1, max_concurrent, taken_trades=taken)
    m = metrics(curve, R, START_EQUITY, (hi - lo).days / 365.25)
    if m:
        m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else float("nan")
    return m, taken


def slice_record(taken):
    good = total = 0
    for _, a, b in splits.DEV_SLICES:
        rs = [t["R"] for t in taken if a <= t["entry_time"] < b]
        if len(rs) >= 5:
            total += 1
            good += sum(rs) > 0
    return good, total


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)

    rows, passers, frames_all = [], [], {}
    for label, sym in CANDIDATES.items():
        df = load(label, sym)
        if df is None or df.height == 0:
            rows.append((label, "no Binance data", None, None, None, False))
            continue
        start = max(lo, df["ts"].min() + WARMUP)
        years = (hi - start).days / 365.25
        if years < MIN_YEARS:
            rows.append((label, f"insufficient data ({years:.1f}y from {start:%Y-%m})", None, None, None, False))
            continue
        frames_all[label] = df
        m, taken = portfolio(trades_for({label: df}), start, hi, 2)
        if m is None:
            rows.append((label, "no trades", None, None, None, False))
            continue
        good, total = slice_record(taken)
        ok = m["n_trades"] >= 30 and m["pf"] >= 1.20 and m["avg_R"] > 0 and total > 0 and good * 2 >= total
        rows.append((label, f"{years:.1f}y from {start:%Y-%m}", m, (good, total), None, ok))
        if ok:
            passers.append(label)

    base_frames = {l: load(l, s) for l, s in BASE.items()}
    base_m, base_taken = portfolio(trades_for(base_frames), lo, hi, 2)
    comb_m = None
    if passers:
        comb_m, _ = portfolio(trades_for({**base_frames, **{l: frames_all[l] for l in passers}}), lo, hi, 4)

    c1 = len(passers) >= 3
    c2 = comb_m is not None and comb_m["sharpe"] >= base_m["sharpe"] and comb_m["mar"] >= base_m["mar"]

    out = ["# §10 breadth: A on other Coinbase US perp coins", "",
           "Protocol: `VALIDATION_RULES.md` §10, committed in `a5f8698` before this script existed. Binance USD-M 4h,",
           "dev window 2021-01-01 → 2026-05-31, 12bp, funding 0x, A's fixed config. "
           "**Unseen coins are marked \\***; the rest were evaluated before (see §10 disclosure).", "",
           "| Coin | Data | Trades | PF | avg R | Win % | CAGR | Max DD | MAR | +R slices | Pass |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for label, data, m, sl, _, ok in rows:
        name = label + (" \\*" if label in UNSEEN else "")
        if m is None:
            out.append(f"| {name} | {data} | — | — | — | — | — | — | — | — | no |")
        else:
            out.append(f"| {name} | {data} | {m['n_trades']} | {m['pf']:.2f} | {m['avg_R']:+.3f} | {m['win_pct']:.1f}% | "
                       f"{m['cagr']:.1%} | {m['max_dd']:.1%} | {m['mar']:.2f} | {sl[0]}/{sl[1]} | {'**yes**' if ok else 'no'} |")
    hdr = ["| Portfolio | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R |", "|---|---|---|---|---|---|---|---|"]
    fmt = lambda n, m: (f"| {n} | {m['cagr']:.1%} | {m['max_dd']:.1%} | {m['mar']:.2f} | {m['sharpe']:.2f} | "
                        f"{m['pf']:.2f} | {m['n_trades']} | {m['avg_R']:+.3f} |")
    out += ["", "## Portfolio (dev window)", ""] + hdr + [fmt("BTC+ETH (max 2 concurrent)", base_m)]
    if comb_m:
        out.append(fmt(f"BTC+ETH+{'+'.join(passers)} (max 4 concurrent)", comb_m))
    out += ["", "## Decision (§10, both required)", "",
            f"1. Coins passing: {len(passers)} ({', '.join(passers) or 'none'}) ≥ 3 → {'yes' if c1 else 'no'}",
            ("2. Combined Sharpe {:.2f} ≥ {:.2f} and MAR {:.2f} ≥ {:.2f} → {}".format(
                comb_m["sharpe"], base_m["sharpe"], comb_m["mar"], base_m["mar"], "yes" if c2 else "no")
             if comb_m else "2. No combined portfolio (no passers) → no"),
            "", f"**Verdict: {'BREADTH ADOPTED (paper decision next)' if (c1 and c2) else 'BREADTH NOT ADOPTED'}**"]
    REPORT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
