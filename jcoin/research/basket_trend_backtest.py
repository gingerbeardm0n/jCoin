"""Strategy B: daily basket trend, long-only spot proxy (VALIDATION_RULES.md §5).

FIXED definition, no tuning:
  - Point-in-time universe: on each rebalance date d, eligible = USDT symbols with >= 100 daily
    bars before d (and a bar on d-1); rank by trailing 90-day mean quote volume using ONLY bars
    strictly before d; take the top 30. Stablecoins / fiat-like / wrapped / index / TradFi-underlying
    contracts excluded (EXCLUDED_BASES). Delisted coins are in the panel.
  - Signal per coin: long if EMA(20) > EMA(100) of closes up to d-1, else flat.
  - Main weighting: every long coin gets 1/30 of equity (cash for the rest, exposure <= 1x).
    Alternative (reported only): 1/N_long (fully invested across longs).
  - Rebalance every 14 days at the OPEN of day d. Positions drift in between.
  - Costs: 0.40% taker + 0.10% slippage = 0.50% per side on every traded notional
    (buys, sells, trims; also the forced exit of a delisted coin).
  - Delisting: a held coin is sold at its last available close.
  - Benchmarks: BTC buy-and-hold; equal-weight top-30 buy-and-hold with the same universe,
    14-day rebalance and costs (strategy B without the EMA filter).

Sealed window: nothing at or after 2026-06-01 is loaded or evaluated (splits.check_window).

Usage:
    python -m jcoin.research.basket_trend_backtest
"""

from __future__ import annotations

import datetime as dt
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from jcoin.research.splits import DEV_SLICES, SEALED_START, check_window, dev_window

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "ohlcv" / "binance_daily"

TOP_N = 30
MIN_HISTORY = 100
VOL_WINDOW = 90
REBAL_DAYS = 14
FEE = 0.0040
SLIPPAGE = 0.0010
COST_RATE = FEE + SLIPPAGE          # per side, on traded notional

# Base asset names (symbol minus the USDT suffix) that are NOT investable crypto "coins".
STABLE_FIAT = {
    "USDC", "BUSD", "TUSD", "FDUSD", "USDP", "DAI", "PAX", "EUR", "GBP", "AEUR", "USDE", "USDS",
    "USD1", "USDD", "RLUSD", "BFUSD", "XUSD", "UST", "SUSD", "GUSD", "USDBRL", "FRAX",
}
WRAPPED_LEVERAGED_INDEX = {
    "WBTC", "WBETH", "BETH", "STETH", "WSTETH", "CBETH", "RETH",     # wrapped / staking derivatives
    "PAXG", "XAUT",                                                  # tokenized gold
    "BTCDOM", "DEFI", "FOOTBALL", "BLUEBIRD", "ANTHROPIC", "OPENAI",  # index / pre-IPO style contracts
}
# TradFi-underlying perps (listed 2025+); not crypto coins. Filled from an audit of the data
# (see TRADFI_BASES audit in the results file).
TRADFI = {
    "AAOI", "AAPL", "ACN", "ADBE", "ALAB", "AMAT", "AMC", "AMD", "AMZN", "ANET", "APLD", "ASML",
    "ASTS", "AVGO", "AXTI", "BABA", "BMNR", "BRKB", "BX", "CIEN", "COHR", "COIN", "COPPER", "COST",
    "CRCL", "CRDO", "CRM", "CRML", "CRWD", "CRWV", "CSCO", "CVNA", "CVX", "DDOG", "DELL", "DIS",
    "DJT", "DKNG", "DRAM", "EBAY", "EWJ", "EWT", "EWY", "EWZ", "FLNC", "GDX", "GEV", "GLW", "GME",
    "GOOGL", "GPRO", "GS", "GTLB", "HD", "HIMS", "HOOD", "HPE", "HUT", "IBM", "INTC", "IONQ", "IREN",
    "IWM", "JPM", "KLAC", "KO", "KORU", "LLY", "LRCX", "MARA", "MDB", "META", "MRK", "MRNA", "MRVL",
    "MSFT", "MSTR", "MU", "MUU", "NATGAS", "NBIS", "NET", "NFLX", "NKE", "NOK", "NOW", "NVDA", "NVDL",
    "NVO", "OKLO", "ONDS", "ORCL", "PANW", "PDD", "PLTR", "PYPL", "QCOM", "QQQ", "RDDT", "RIVN",
    "RKLB", "SMCI", "SMH", "SNDK", "SNOW", "SOFI", "SONY", "SOXL", "SOXS", "SPY", "SQQQ", "TEAM",
    "TER", "TMF", "TQQQ", "TSLA", "TSLL", "TSM", "TTWO", "TXN", "TZA", "UBER", "UNH", "URNM",
    "USAR", "UVXY", "V", "VRT", "VST", "WDC", "WMT", "XAG", "XAU", "XBI", "XLE", "XOM", "XPD", "XPT",
    "MP", "SHOP", "RVV", "BYD", "NAVER", "MEITUAN", "TENCENT", "KUAISHOU", "SAMSUNG", "SAMSUNGEM",
    "SKHYNIX", "SKHY", "HYUNDAI", "LGELECTRONICS", "KODEX200", "CSOPSAMSUNG2L", "CSOPSKHYNIX2L",
    "HK0625", "HK0700", "HK0992", "HK1810", "HANMI", "ZHIPU", "ZHONGJI", "BITO", "CL", "BILL", "ALL",
}
EXCLUDED_BASES: set[str] = STABLE_FIAT | WRAPPED_LEVERAGED_INDEX | TRADFI
# (Binance leveraged tokens such as BTCUP/BTCDOWN are spot-only; none exist as USD-M perps.)


def base_of(sym: str) -> str:
    return sym[:-4] if sym.endswith("USDT") else sym


def is_excluded(sym: str) -> bool:
    return base_of(sym) in EXCLUDED_BASES


# --------------------------------------------------------------------------- data

@dataclass
class Panel:
    dates: np.ndarray            # datetime64[D], length T, consecutive days
    symbols: list[str]
    open: np.ndarray             # (T, N) NaN where no bar
    close: np.ndarray
    qvol: np.ndarray
    excluded: np.ndarray = field(default=None)   # (N,) bool

    def __post_init__(self):
        if self.excluded is None:
            self.excluded = np.array([is_excluded(s) for s in self.symbols])
        T, N = self.close.shape
        self.has_bar = ~np.isnan(self.close)
        self.cum_bars = np.cumsum(self.has_bar, axis=0)                 # bars up to and incl. t
        idx = np.arange(T)[:, None]
        last = np.where(self.has_bar, idx, -1).max(axis=0)
        first = np.where(self.has_bar, idx, T).min(axis=0)
        self.last_idx = last        # -1 if none
        self.first_idx = first
        # forward-filled closes (within life only) for marking
        cf = self.close.copy()
        for j in range(N):
            col = cf[:, j]
            valid = ~np.isnan(col)
            if valid.any():
                ii = np.where(valid, np.arange(T), 0)
                np.maximum.accumulate(ii, out=ii)
                filled = col[ii]
                filled[: first[j]] = np.nan
                cf[:, j] = filled
        self.close_ff = cf


def load_panel(root: Path = DATA_ROOT, start: str = "2020-01-01") -> Panel:
    """Load every symbol parquet into aligned (T, N) matrices. Hard-stops before SEALED_START."""
    t0 = dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc)
    check_window(t0, SEALED_START)
    frames = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f = d / "1d.parquet"
        if not f.exists():
            continue
        df = pl.read_parquet(f).filter(pl.col("ts") < SEALED_START)   # never even load sealed rows
        if df.height:
            frames[d.name] = df
    n_days = (SEALED_START.date() - t0.date()).days
    dates = np.array([np.datetime64(t0.date()) + np.timedelta64(i, "D") for i in range(n_days)])
    syms = sorted(frames)
    o = np.full((n_days, len(syms)), np.nan)
    c = o.copy()
    q = o.copy()
    base = np.datetime64(t0.date())
    for j, s in enumerate(syms):
        df = frames[s]
        di = (df["ts"].dt.date().to_numpy().astype("datetime64[D]") - base).astype(int)
        ok = (di >= 0) & (di < n_days)
        o[di[ok], j] = df["open"].to_numpy()[ok]
        c[di[ok], j] = df["close"].to_numpy()[ok]
        q[di[ok], j] = df["quote_volume"].to_numpy()[ok]
    return Panel(dates, syms, o, c, q)


# --------------------------------------------------------------------------- signals / universe

def ema_matrix(close: np.ndarray, span: int) -> np.ndarray:
    """EMA per column, seeded at each coin's first close; carries through gaps, NaN outside life."""
    T, N = close.shape
    alpha = 2.0 / (span + 1.0)
    out = np.full((T, N), np.nan)
    cur = np.full(N, np.nan)
    for t in range(T):
        x = close[t]
        has = ~np.isnan(x)
        new = np.isnan(cur) & has
        cur = np.where(new, x, cur)
        upd = has & ~new
        cur = np.where(upd, alpha * x + (1 - alpha) * cur, cur)
        out[t] = np.where(np.isnan(cur), np.nan, cur)
    return out


def select_universe(panel: Panel, i: int, top_n: int = TOP_N, min_history: int = MIN_HISTORY,
                    vol_window: int = VOL_WINDOW) -> list[int]:
    """Column indices of the top-N coins on rebalance day index i. Uses bars with index < i ONLY."""
    if i < 1:
        return []
    n_hist = panel.cum_bars[i - 1]                       # bars strictly before i
    elig = (n_hist >= min_history) & panel.has_bar[i - 1] & ~panel.excluded
    lo = max(0, i - vol_window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # all-NaN columns (not yet listed)
        dv = np.nanmean(panel.qvol[lo:i], axis=0)         # trailing mean dollar volume, bars < i
    dv = np.where(elig & ~np.isnan(dv), dv, -np.inf)
    order = np.argsort(-dv, kind="stable")
    return [int(j) for j in order[:top_n] if np.isfinite(dv[j])]


def long_signal(ema_fast: np.ndarray, ema_slow: np.ndarray, i: int) -> np.ndarray:
    """Boolean per coin: EMA fast > EMA slow using closes up to day i-1 (not i)."""
    f, s = ema_fast[i - 1], ema_slow[i - 1]
    with np.errstate(invalid="ignore"):
        return (f > s) & ~np.isnan(f) & ~np.isnan(s)


# --------------------------------------------------------------------------- simulation

@dataclass
class Config:
    name: str
    ema: tuple[int, int] | None = (20, 100)     # None -> no filter (equal-weight B&H)
    weighting: str = "slot"                     # "slot": 1/top_n per coin; "n_long": 1/N_long
    fixed_symbols: tuple[str, ...] | None = None  # e.g. ("BTCUSDT",) for buy-and-hold
    rebal_days: int = REBAL_DAYS
    top_n: int = TOP_N
    cost_rate: float = COST_RATE
    min_history: int = MIN_HISTORY


@dataclass
class SimResult:
    name: str
    dates: np.ndarray
    equity: np.ndarray            # close-of-day equity, starting equity 1.0 before day 0
    traded: np.ndarray            # traded notional (buys+sells) per day
    n_trades: np.ndarray          # individual orders per day
    n_held: np.ndarray            # positions held at close
    cash_frac: np.ndarray         # cash / equity at close
    costs: np.ndarray             # cost paid per day (currency)
    log: list = field(default_factory=list)   # rebalance log (for tests/inspection)


def _rebalance(i, panel, cfg, cash, units, ema_f, ema_s, sym_idx, log):
    """Rebalance at the OPEN of day i. Returns (cash, traded, n_orders, cost)."""
    N = panel.close.shape[1]
    px = np.where(np.isnan(panel.open[i]), panel.close_ff[i - 1] if i > 0 else np.nan, panel.open[i])
    px = np.where(np.isnan(px), panel.close_ff[i], px)
    tradable = ~np.isnan(panel.open[i])                   # need an actual bar to trade
    held_val = np.nansum(units * px)
    equity = cash + held_val

    if cfg.fixed_symbols is not None:
        uni = [sym_idx[s] for s in cfg.fixed_symbols if s in sym_idx]
        sel = uni
        longs = uni
    else:
        uni = select_universe(panel, i, cfg.top_n, cfg.min_history)
        if ema_f is not None:
            sig = long_signal(ema_f, ema_s, i)
            longs = [j for j in uni if sig[j]]
        else:
            longs = list(uni)
        sel = uni
    longs = [j for j in longs if tradable[j]]

    w = np.zeros(N)
    if cfg.fixed_symbols is not None:
        for j in longs:
            w[j] = 1.0 / len(cfg.fixed_symbols)
    elif cfg.weighting == "slot":
        for j in longs:
            w[j] = 1.0 / cfg.top_n
    elif cfg.weighting == "n_long":
        for j in longs:
            w[j] = 1.0 / len(longs)
    else:
        raise ValueError(cfg.weighting)

    cur_val = units * px
    cur_val = np.where(np.isnan(cur_val), 0.0, cur_val)
    # coins we hold but cannot trade today (no bar) keep their units; their target = current value
    stuck = (units > 0) & ~tradable
    # fixed point: targets are a fraction of equity NET of the costs this rebalance incurs
    e_eff = equity
    for _ in range(50):
        tgt = w * e_eff
        tgt = np.where(stuck, cur_val, tgt)
        trade = tgt - cur_val
        cost = cfg.cost_rate * np.abs(trade).sum()
        e_new = equity - cost
        if abs(e_new - e_eff) < 1e-14:
            break
        e_eff = e_new
    tgt = np.where(stuck, cur_val, w * e_eff)
    trade = tgt - cur_val
    traded = float(np.abs(trade).sum())
    cost = cfg.cost_rate * traded
    n_orders = int((np.abs(trade) > 1e-12).sum())
    new_units = np.where(stuck, units, np.where(np.isnan(px), 0.0, tgt / np.where(np.isnan(px), 1, px)))
    cash_new = cash - float(trade.sum()) - cost
    log.append({"i": i, "universe": list(uni), "longs": list(longs), "traded": traded, "cost": cost,
                "n_orders": n_orders, "equity_before": equity})
    return cash_new, new_units, traded, n_orders, cost


def simulate(panel: Panel, cfg: Config, start_i: int, end_i: int) -> SimResult:
    """Day-by-day simulation over index range [start_i, end_i). Equity starts at 1.0 in cash."""
    check_window(_to_dt(panel.dates[start_i]), _to_dt(panel.dates[end_i - 1]) + dt.timedelta(days=1))
    T, N = panel.close.shape
    sym_idx = {s: j for j, s in enumerate(panel.symbols)}
    if cfg.ema is not None:
        ema_f, ema_s = ema_matrix(panel.close, cfg.ema[0]), ema_matrix(panel.close, cfg.ema[1])
    else:
        ema_f = ema_s = None
    n = end_i - start_i
    equity = np.zeros(n)
    traded_a = np.zeros(n)
    ntr = np.zeros(n, dtype=int)
    nheld = np.zeros(n, dtype=int)
    cashf = np.zeros(n)
    costs = np.zeros(n)
    cash = 1.0
    units = np.zeros(N)
    log: list = []
    for k, t in enumerate(range(start_i, end_i)):
        if cfg.fixed_symbols is not None:
            is_rebal = (k == 0)
        else:
            is_rebal = (k % cfg.rebal_days == 0)
        if is_rebal:
            cash, units, tr, no, cst = _rebalance(t, panel, cfg, cash, units, ema_f, ema_s, sym_idx, log)
            traded_a[k] += tr
            ntr[k] += no
            costs[k] += cst
        # delisting: sell at the last available close of the coin
        dl = (units > 0) & (panel.last_idx == t) & (t < T - 1)
        if dl.any():
            for j in np.where(dl)[0]:
                val = units[j] * panel.close[t, j]
                cst = cfg.cost_rate * val
                cash += val - cst
                traded_a[k] += val
                ntr[k] += 1
                costs[k] += cst
                units[j] = 0.0
                log.append({"i": t, "delist_exit": panel.symbols[j], "price": float(panel.close[t, j]),
                            "value": float(val), "cost": float(cst)})
        mv = np.nansum(units * panel.close_ff[t])
        eq = cash + mv
        equity[k] = eq
        nheld[k] = int((units > 0).sum())
        cashf[k] = cash / eq if eq > 0 else 1.0
    return SimResult(cfg.name, panel.dates[start_i:end_i], equity, traded_a, ntr, nheld, cashf, costs, log)


def _to_dt(d64) -> dt.datetime:
    return dt.datetime.combine(d64.astype("datetime64[D]").astype(dt.date), dt.time(), tzinfo=dt.timezone.utc)


# --------------------------------------------------------------------------- metrics

def metrics(res: SimResult, lo: int = 0, hi: int | None = None) -> dict:
    """Metrics on the sub-curve res[lo:hi]; the sub-curve starts from the prior day's close equity."""
    hi = len(res.equity) if hi is None else hi
    eq = res.equity[lo:hi]
    prev = res.equity[lo - 1] if lo > 0 else 1.0
    curve = np.concatenate([[prev], eq])
    rets = curve[1:] / curve[:-1] - 1.0
    n = len(rets)
    years = n / 365.0
    growth = curve[-1] / curve[0]
    cagr = growth ** (1 / years) - 1 if growth > 0 else -1.0
    peak = np.maximum.accumulate(curve)
    mdd = float(np.max((peak - curve) / peak))
    sd = rets.std(ddof=1)
    sharpe = float(rets.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0
    traded = res.traded[lo:hi].sum()
    avg_eq = float(curve[1:].mean())
    return {
        "days": n, "total_ret": growth - 1, "cagr": cagr, "max_dd": mdd,
        "mar": cagr / mdd if mdd > 0 else float("nan"), "sharpe": sharpe,
        "n_trades": int(res.n_trades[lo:hi].sum()),
        "turnover": float(traded / avg_eq / years) if avg_eq > 0 else 0.0,   # (buys+sells)/avg equity per year
        "cost_drag": float(res.costs[lo:hi].sum() / avg_eq / years),
        "avg_held": float(res.n_held[lo:hi].mean()),
        "pct_flat_days": float((res.n_held[lo:hi] == 0).mean()),
        "avg_cash": float(res.cash_frac[lo:hi].mean()),
    }


def slice_bounds(panel: Panel, start_i: int) -> list[tuple[str, int, int]]:
    """DEV_SLICES as (name, lo, hi) offsets within a result that starts at panel index start_i."""
    out = []
    for name, s, e in DEV_SLICES:
        lo = int((np.datetime64(s.date()) - panel.dates[start_i]) / np.timedelta64(1, "D"))
        hi = int((np.datetime64(e.date()) - panel.dates[start_i]) / np.timedelta64(1, "D"))
        out.append((name, lo, hi))
    return out


CONFIGS = [
    Config("B main (EMA 20/100, 1/30 slots)", ema=(20, 100), weighting="slot"),
    Config("B sens (EMA 50/200)", ema=(50, 200), weighting="slot", min_history=200),
    Config("B alt weighting (1/N_long)", ema=(20, 100), weighting="n_long"),
    Config("BM: BTC buy-and-hold", ema=None, fixed_symbols=("BTCUSDT",)),
    Config("BM: EW top-30 B&H (no filter)", ema=None, weighting="slot"),
]


def run_all(panel: Panel):
    d0, d1 = dev_window()
    check_window(d0, d1)
    start_i = int((np.datetime64(d0.date()) - panel.dates[0]) / np.timedelta64(1, "D"))
    end_i = int((np.datetime64(d1.date()) - panel.dates[0]) / np.timedelta64(1, "D"))
    results = {c.name: simulate(panel, c, start_i, end_i) for c in CONFIGS}
    return results, start_i, end_i


def _fmt_row(name, m):
    return (f"| {name} | {m['cagr']*100:.1f}% | {m['max_dd']*100:.1f}% | {m['mar']:.2f} | {m['sharpe']:.2f} | "
            f"{m['turnover']:.1f}x | {m['n_trades']} | {m['avg_held']:.1f} | {m['pct_flat_days']*100:.0f}% | "
            f"{abs(m['avg_cash'])*100:.0f}% |")


def main() -> int:
    panel = load_panel()
    results, start_i, _ = run_all(panel)
    print(f"panel: {len(panel.symbols)} symbols, {panel.dates[0]} -> {panel.dates[-1]}")
    hdr = "| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg held | Flat days | Avg cash |"
    print("\nFULL DEV 2021-01-01 -> 2026-05-31\n" + hdr + "\n|" + "---|" * 10)
    for name, r in results.items():
        print(_fmt_row(name, metrics(r)))
    for sname, lo, hi in slice_bounds(panel, start_i):
        print(f"\nSLICE {sname}\n" + hdr + "\n|" + "---|" * 10)
        for name, r in results.items():
            print(_fmt_row(name, metrics(r, lo, hi)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
