"""PaperTrader — run the validated engine on live data with a virtual account.

Phase A of going live: self-simulated paper trading. Same Strategy + TradingEngine as
the backtest (parity); only the broker (PaperBroker) and the data clock differ.

Responsibilities beyond the engine:
  - kill-switch wiring: hard halt -> flatten + disable; soft halt -> pause new entries.
  - state persistence: positions/equity/closed/curve saved to JSON so a restart resumes
    exactly where it left off (never lose track of open risk).
  - logging: one human-readable line per processed bar + every fill.

Two modes (same processing path):
  - run_replay(): drive from stored history — used to TEST the whole stack end to end.
  - run_live_once(): fetch the latest CLOSED bar per symbol and process it — call this
    from a scheduler every 4h for an actual paper run.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import polars as pl

from jcoin.data.config import LIVE_MARKETS, Market, market_by_label
from jcoin.data.feed import DataFeed
from jcoin.data.live_source import get_recent_candles
from jcoin.engine.broker import PaperBroker
from jcoin.engine.engine import TradingEngine
from jcoin.engine.features import compute_features
from jcoin.engine.kill_switch import HaltLevel, KillSwitch, KillSwitchConfig
from jcoin.engine.risk import RiskConfig, can_open
from jcoin.engine.strategy import BreakoutStrategy, StrategyConfig
from jcoin.engine.types import ClosedTrade, Position, Side
from jcoin.strategy.cycle import CYCLE_BEAR, CYCLE_UNKNOWN, current_phase

_FEAT_COLS = ["symbol", "ts", "open", "high", "low", "close", "volume",
              "regime", "atr", "brk_long", "brk_short", "conf_sh", "conf_sl"]


class PaperTrader:
    def __init__(self, labels=("BTC", "ETH"), tf="4h", *,
                 strat=StrategyConfig(), risk=RiskConfig(), ks=KillSwitchConfig(),
                 cost_frac=0.0012, start_equity=10_000.0,
                 state_dir="paper_state", live_markets=None, broker=None):
        self.labels = list(labels)
        self.tf = tf
        self.engine = TradingEngine(BreakoutStrategy(strat),
                                    broker if broker is not None else PaperBroker(cost_frac),
                                    risk, start_equity)
        self.ks = KillSwitch(ks, start_equity)
        self.last_ts: dt.datetime | None = None
        self.start_equity = start_equity
        self.persist = True   # live: save every bar; replay sets False (save once at end)
        self.live_markets = {m.label: m for m in (live_markets or LIVE_MARKETS)}

        self._cycle_phase: str = CYCLE_UNKNOWN  # updated each live bar from BTC history
        self._base_risk = risk                  # original config; bear phase scales it down
        self._last_prices: dict[str, float] = {}

        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self._init_log()
        if self.state_path.exists():
            self._load()
            self.log.info("resumed: equity=%.2f open=%d last_ts=%s",
                          self.engine.account.equity, self.engine.account.open_count, self.last_ts)

    # -- core processing (shared by replay + live) ---------------------------
    def process_step(self, ts: dt.datetime, rows: dict[str, dict]) -> None:
        acct = self.engine.account
        # Macro cycle filter: scale risk to 75% in bear phase instead of disabling.
        # Bear shorts still have positive edge (PF ~1.59) but weaker + funding drag.
        # Swap engine.risk each step (RiskConfig is frozen, so replace the instance).
        if self._cycle_phase == CYCLE_BEAR:
            scaled = RiskConfig(
                risk_frac=self._base_risk.risk_frac * 0.75,
                max_per_symbol=self._base_risk.max_per_symbol,
                max_concurrent=self._base_risk.max_concurrent,
            )
            if self.engine.risk is not scaled:
                self.log.info("CYCLE FILTER: bear phase -> risk_frac=%.3f (75%% of base)",
                              scaled.risk_frac)
            self.engine.risk = scaled
        else:
            self.engine.risk = self._base_risk

        decision = self.ks.evaluate(ts, acct.equity)
        if decision.level is HaltLevel.HARD:
            if acct.open_count:
                self.log.warning("HARD HALT (%s) -> flatten all", decision.reason)
                self.engine.flatten_all(ts, rows, f"killswitch:{decision.reason}")
            self.engine.entries_enabled = False
        else:
            self.engine.entries_enabled = decision.level is not HaltLevel.SOFT
            if decision.level is HaltLevel.SOFT:
                self.log.warning("SOFT HALT (%s) -> entries paused", decision.reason)

        n_closed_before = len(acct.closed)
        self.engine.step(ts, rows)

        for tr in acct.closed[n_closed_before:]:
            self.ks.on_trade_closed(tr.pnl)
            self.log.info("EXIT  %s %s @ %.2f  pnl=%.2f R=%.2f (%s)",
                          tr.symbol, tr.side.value, tr.exit_price, tr.pnl, tr.R, tr.exit_reason)
        for sym, pos in acct.positions.items():
            if pos.entry_time == ts:
                self.log.info("ENTER %s %s @ %.2f  size=%.5f stop=%.2f",
                              sym, pos.side.value, pos.entry_price, pos.size, pos.init_stop)

        acct.equity_curve.append((ts, acct.equity))
        self.last_ts = ts
        for sym, row in rows.items():
            if "close" in row:
                self._last_prices[sym] = row["close"]
        if self.persist:
            self._save()
        self.log.info("bar %s | equity=%.2f open=%d trades=%d",
                      ts.isoformat(), acct.equity, acct.open_count, len(acct.closed))

    # -- cycle filter --------------------------------------------------------
    def _refresh_cycle_phase(self, feats: dict) -> None:
        """Compute current macro cycle phase from BTC (market leader) feature data.

        Reads from the feature dataframe already fetched for this bar — no extra
        API call. Needs >= 2190 bars (365 days at 4h) for the SMA to be valid;
        falls back to CYCLE_UNKNOWN (treated as bull = entries allowed) if the
        live exchange returns fewer bars.
        """
        btc_feat = feats.get("BTC")
        if btc_feat is None or btc_feat.height < 2190:
            self.log.info("cycle filter: insufficient BTC history (%d bars), treating as bull",
                          btc_feat.height if btc_feat is not None else 0)
            self._cycle_phase = CYCLE_UNKNOWN
            return
        self._cycle_phase = current_phase(btc_feat)
        self.log.info("cycle filter: BTC phase = %s", self._cycle_phase)

    # -- live mode -----------------------------------------------------------
    def run_live_once(self) -> bool:
        """Fetch latest closed bars, process the newest common timestamp. Returns True
        if a new bar was processed."""
        feats = {}
        for label in self.labels:
            mkt = self.live_markets.get(label) or market_by_label(label)
            # Fetch enough bars for cycle filter (2190 needed for 365-day SMA)
            df = get_recent_candles(mkt, self.tf, limit=2300)
            if df.height < 60:
                self.log.warning("insufficient live data for %s", label)
                return False
            f = compute_features(df, k=2, atr_period=14).with_columns(symbol=pl.lit(label))
            feats[label] = f
        self._refresh_cycle_phase(feats)
        common_ts = min(f["ts"].max() for f in feats.values())
        if self.last_ts is not None and common_ts <= self.last_ts:
            self.log.info("no new closed bar (latest=%s)", common_ts)
            return False
        rows = {}
        for label, f in feats.items():
            r = f.filter(pl.col("ts") == common_ts).select(_FEAT_COLS)
            if r.height:
                rows[label] = r.to_dicts()[0]
        self.process_step(common_ts, rows)
        return True

    # -- replay mode (testing the full stack) --------------------------------
    def run_replay(self, start=None, end=None) -> None:
        feed = DataFeed()
        by_ts: dict = {}
        feats_full: dict[str, pl.DataFrame] = {}
        for label in self.labels:
            f = compute_features(feed.get_candles(label, self.tf, start=start, end=end),
                                 k=2, atr_period=14).with_columns(symbol=pl.lit(label))
            feats_full[label] = f
            for row in f.select(_FEAT_COLS).iter_rows(named=True):
                by_ts.setdefault(row["ts"], {})[label] = row

        # Pre-compute BTC cycle phase timeline for replay (causal: bar i uses rows 0..i)
        from jcoin.strategy.cycle import add_cycle_filter as _acf
        btc_full = feats_full.get("BTC")
        cycle_by_ts: dict = {}
        if btc_full is not None:
            btc_cycle = _acf(btc_full).select(["ts", "cycle_phase"])
            cycle_by_ts = dict(zip(btc_cycle["ts"].to_list(), btc_cycle["cycle_phase"].to_list()))

        # Reset account state — replay always starts from scratch so live positions
        # from a previous run don't get closed at wrong historical prices.
        acct = self.engine.account
        acct.equity = self.start_equity
        acct.positions.clear()
        acct.closed.clear()
        acct.equity_curve.clear()
        self.engine.entries_enabled = True
        self.engine._bars_held.clear()
        self._last_prices.clear()
        self.last_ts = None
        self.ks.reset(self.start_equity)

        self.persist = False
        for ts in sorted(by_ts):
            self._cycle_phase = cycle_by_ts.get(ts, CYCLE_UNKNOWN)
            self.process_step(ts, by_ts[ts])
        self.persist = True
        self._save()

    # -- persistence ---------------------------------------------------------
    def _save(self) -> None:
        acct = self.engine.account
        st = {
            "equity": acct.equity,
            "last_ts": self.last_ts.isoformat() if self.last_ts else None,
            "bars_held": self.engine._bars_held,
            "cycle_phase": self._cycle_phase,
            "last_prices": self._last_prices,
            "positions": [self._pos_d(p) for p in acct.positions.values()],
            "closed": [self._trade_d(t) for t in acct.closed],
            "equity_curve": [[t.isoformat(), e] for t, e in acct.equity_curve],
            "killswitch": self._ks_d(),
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=2))
        tmp.replace(self.state_path)  # atomic

    def _load(self) -> None:
        st = json.loads(self.state_path.read_text())
        acct = self.engine.account
        acct.equity = st["equity"]
        self.last_ts = dt.datetime.fromisoformat(st["last_ts"]) if st["last_ts"] else None
        self.engine._bars_held = dict(st.get("bars_held", {}))
        acct.positions = {p["symbol"]: self._pos_from(p) for p in st["positions"]}
        acct.closed = [self._trade_from(t) for t in st["closed"]]
        acct.equity_curve = [(dt.datetime.fromisoformat(t), e) for t, e in st["equity_curve"]]
        self._ks_from(st["killswitch"])

    @staticmethod
    def _pos_d(p: Position) -> dict:
        return {"symbol": p.symbol, "side": p.side.value, "entry_time": p.entry_time.isoformat(),
                "entry_price": p.entry_price, "size": p.size, "risk_dollars": p.risk_dollars,
                "atr": p.atr, "init_stop": p.init_stop, "trail_stop": p.trail_stop,
                "extreme": p.extreme, "entry_cost": p.entry_cost}

    @staticmethod
    def _pos_from(d: dict) -> Position:
        return Position(d["symbol"], Side(d["side"]), dt.datetime.fromisoformat(d["entry_time"]),
                        d["entry_price"], d["size"], d["risk_dollars"], d["atr"],
                        d["init_stop"], d["trail_stop"], d["extreme"], d["entry_cost"])

    @staticmethod
    def _trade_d(t: ClosedTrade) -> dict:
        return {"symbol": t.symbol, "side": t.side.value, "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat(), "entry_price": t.entry_price,
                "exit_price": t.exit_price, "size": t.size, "pnl": t.pnl, "R": t.R,
                "exit_reason": t.exit_reason}

    @staticmethod
    def _trade_from(d: dict) -> ClosedTrade:
        return ClosedTrade(d["symbol"], Side(d["side"]), dt.datetime.fromisoformat(d["entry_time"]),
                           dt.datetime.fromisoformat(d["exit_time"]), d["entry_price"],
                           d["exit_price"], d["size"], d["pnl"], d["R"], d["exit_reason"])

    def _ks_d(self) -> dict:
        s = self.ks.state
        return {"peak_equity": s.peak_equity, "day": s.day.isoformat() if s.day else None,
                "day_start_equity": s.day_start_equity, "loss_streak": s.loss_streak,
                "cooldown_left": s.cooldown_left,
                "halted_until_day": s.halted_until_day.isoformat() if s.halted_until_day else None,
                "hard_halted": s.hard_halted}

    def _ks_from(self, d: dict) -> None:
        s = self.ks.state
        s.peak_equity = d["peak_equity"]
        s.day = dt.date.fromisoformat(d["day"]) if d["day"] else None
        s.day_start_equity = d["day_start_equity"]
        s.loss_streak = d["loss_streak"]
        s.cooldown_left = d.get("cooldown_left", 0)
        s.halted_until_day = dt.date.fromisoformat(d["halted_until_day"]) if d["halted_until_day"] else None
        s.hard_halted = d["hard_halted"]

    def _init_log(self) -> None:
        self.log = logging.getLogger(f"jcoin.paper.{id(self)}")
        self.log.setLevel(logging.INFO)
        if not self.log.handlers:
            fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            fh = logging.FileHandler(self.dir / "paper.log", encoding="utf-8")
            fh.setFormatter(fmt)
            sh = logging.StreamHandler(__import__("sys").stdout)  # stdout, not stderr
            sh.setFormatter(fmt)
            self.log.addHandler(fh)
            self.log.addHandler(sh)
