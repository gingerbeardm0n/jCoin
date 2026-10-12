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
from jcoin.data.live_source import get_recent_candles_cached
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
                 state_dir="paper_state", live_markets=None, broker=None,
                 allow_stale_entries: bool = True):
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
        # Catch-up backlog bars are hours-old signals by definition. Paper trading is
        # fine simulating entries on them (default True); real-money runners (see
        # run_kraken.py) pass False so they only ever manage/exit stale positions and
        # never OPEN a real position off a stale bar (audit 2026-09-18, item #2).
        self.allow_stale_entries = allow_stale_entries

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
    def process_step(self, ts: dt.datetime, rows: dict[str, dict],
                      allow_entries: bool = True,
                      entry_symbols: set[str] | None = None) -> None:
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
        self.engine.step(ts, rows, allow_entries=allow_entries, entry_symbols=entry_symbols)

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
        """Fetch closed bars and process EVERY bar newer than last_ts, in chronological
        order (audit 2026-09-18, item #2: after any outage the old single-bar logic
        silently skipped every intermediate bar's signals -- 38% of bars were missed
        since July). Returns True if at least one new bar was processed.

        Robust to one symbol lagging: a symbol whose fetch fails or is stale/short is
        logged and excluded from this tick rather than freezing catch-up for everyone
        else (it just gets no rows at any timestamp until its feed recovers).

        Orphan positions (audit 2026-09-18): engine.step() only manages/enters symbols
        present in `rows`, so an open position in a symbol that has since fallen out of
        `self.labels` would otherwise never be fetched, never be managed, and sit stuck
        forever. Any such symbol is added to the fetch list here so its position keeps
        getting managed (stops/trailing/exits), but it is excluded from `entry_symbols`
        so it can never open a NEW position -- only the configured universe can.
        """
        open_syms = set(self.engine.account.positions.keys())
        orphans = sorted(s for s in open_syms if s not in self.labels)
        fetch_labels = list(self.labels) + orphans
        if orphans:
            self.log.warning("managing %d orphan position(s) outside universe: %s",
                             len(orphans), orphans)

        feats = {}
        lagging: list[str] = []
        self.fetch_failures = lagging  # read by run_paper to decide exit code / ping
        for label in fetch_labels:
            mkt = self.live_markets.get(label) or market_by_label(label)
            try:
                # Fetch enough bars for cycle filter (2190 needed for 365-day SMA).
                # Cached on disk (data/live_source.get_recent_candles_cached) so a hot
                # run only fetches the handful of bars newer than the cache.
                df = get_recent_candles_cached(mkt, self.tf, self.dir / "cache", limit=2300)
            except Exception as e:
                self.log.error("fetch FAILED for %s: %s — excluding it this tick", label, e)
                lagging.append(label)
                continue
            if df.height < 60:
                self.log.warning("insufficient live data for %s (%d bars) — excluding it this tick",
                                 label, df.height)
                lagging.append(label)
                continue
            f = compute_features(df, k=2, atr_period=14).with_columns(symbol=pl.lit(label))
            feats[label] = f

        if not feats:
            self.log.error("no usable live data for ANY symbol this tick")
            return False
        if lagging:
            self.log.warning("proceeding without lagging/unavailable symbol(s): %s", lagging)

        self._refresh_cycle_phase(feats)

        # Union of new-bar timestamps across whichever symbols DID return data, so one
        # lagging symbol's shorter history can't block catch-up for the rest.
        new_ts_by_symbol = {
            label: sorted(t for t in f["ts"].to_list() if self.last_ts is None or t > self.last_ts)
            for label, f in feats.items()
        }
        all_new_ts = sorted({t for ts_list in new_ts_by_symbol.values() for t in ts_list})
        if not all_new_ts:
            newest = max(f["ts"].max() for f in feats.values())
            self.log.info("no new closed bar (latest=%s)", newest)
            return False

        # Feed-staleness guard (safety item #2): if the newest bar ANY symbol can offer
        # is much older than one bar-interval, the exchange feed itself looks stale --
        # exclude just that newest bar (don't trade on it) but still catch up everything
        # older, which is legitimate backlog rather than a live-feed problem.
        newest_ts = all_new_ts[-1]
        age_h = (dt.datetime.now(dt.timezone.utc) - newest_ts).total_seconds() / 3600
        if age_h > 9.0:  # 4h bar + 4h tolerance + 1h slack
            self.log.error("FEED STALE: latest available bar %s is %.1fh old — excluding it "
                           "this tick, still catching up older backlog bars", newest_ts, age_h)
            all_new_ts = all_new_ts[:-1]
        if not all_new_ts:
            return False

        if len(all_new_ts) > 1:
            self.log.info("CATCH-UP: %d missed bar(s) to process (%s -> %s)",
                          len(all_new_ts), all_new_ts[0], all_new_ts[-1])

        processed_any = False
        for ts in all_new_ts:
            rows = {}
            for label, f in feats.items():
                r = f.filter(pl.col("ts") == ts).select(_FEAT_COLS)
                if r.height:
                    rows[label] = r.to_dicts()[0]
            if not rows:
                continue
            # Only the newest bar in this batch is "fresh"; anything behind it is a
            # catch-up bar. allow_stale_entries=False (run_kraken.py) means catch-up
            # bars only manage/exit existing positions -- never open a new real
            # position on an hours-old signal.
            is_newest = ts == all_new_ts[-1]
            allow_entries = self.allow_stale_entries or is_newest
            # entry_symbols restricts NEW entries to the configured universe even when
            # orphan positions are being fetched/managed alongside it this tick.
            self.process_step(ts, rows, allow_entries=allow_entries,
                              entry_symbols=set(self.labels))
            processed_any = True

        return processed_any

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

    def reset_equity(self, new_equity: float) -> None:
        """Reset account to new_equity, drop open positions, keep closed trade history."""
        acct = self.engine.account
        self.log.warning(
            "EQUITY RESET: %.2f -> %.2f | dropping %d open position(s)",
            acct.equity, new_equity, acct.open_count,
        )
        acct.equity = new_equity
        acct.positions.clear()
        acct.equity_curve.clear()
        self.engine._bars_held.clear()
        self.engine.entries_enabled = True
        self._last_prices.clear()
        self.ks.reset(new_equity)
        self._save()
        self.log.warning("EQUITY RESET complete — live paper now tracks $%.2f", new_equity)

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
                "extreme": p.extreme, "entry_cost": p.entry_cost,
                "stop_order_id": p.stop_order_id, "stop_order_price": p.stop_order_price}

    @staticmethod
    def _pos_from(d: dict) -> Position:
        return Position(d["symbol"], Side(d["side"]), dt.datetime.fromisoformat(d["entry_time"]),
                        d["entry_price"], d["size"], d["risk_dollars"], d["atr"],
                        d["init_stop"], d["trail_stop"], d["extreme"], d["entry_cost"],
                        d.get("stop_order_id"), d.get("stop_order_price"))

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
