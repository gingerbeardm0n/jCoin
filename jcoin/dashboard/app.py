"""jCoin dashboard — live paper trading monitor.

Reads paper_state/state.json and pushes updates to the browser via SSE
whenever the file changes (i.e. every time a new bar is processed).

Usage:
    python -m jcoin.dashboard
    python -m jcoin.dashboard --state-dir paper_state --port 8765
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI(title="jCoin Dashboard")

# Set by __main__ before uvicorn starts
STATE_FILE: Path = Path("paper_state/state.json")

VALIDATED   = {"BTC", "ETH", "EGLD", "SAND", "IMX"}
WATCH_LIST  = {"ADA", "XRP", "AVAX", "HBAR", "NEAR", "SUI"}


# ── API ──────────────────────────────────────────────────────────────────────

@app.get("/api/state")
def get_state():
    if not STATE_FILE.exists():
        return {"error": "state file not found", "path": str(STATE_FILE)}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


@app.get("/api/events")
async def sse_events():
    """Server-Sent Events: sends 'update' whenever state.json changes."""
    async def _stream():
        last_mtime = 0.0
        while True:
            try:
                mtime = STATE_FILE.stat().st_mtime if STATE_FILE.exists() else 0.0
                if mtime != last_mtime:
                    last_mtime = mtime
                    yield "data: update\n\n"
            except Exception:
                pass
            await asyncio.sleep(2)
    return StreamingResponse(_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Dashboard HTML ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_HTML)


_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>jCoin Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d0d0d; color: #e0e0e0; font-family: 'Courier New', monospace; font-size: 13px; }
  a { color: inherit; text-decoration: none; }

  header { background: #111; border-bottom: 1px solid #222; padding: 14px 24px;
           display: flex; align-items: center; gap: 24px; }
  header h1 { font-size: 18px; color: #fff; letter-spacing: 2px; }
  #last-update { color: #555; font-size: 11px; margin-left: auto; }

  .metrics { display: flex; gap: 12px; padding: 16px 24px; flex-wrap: wrap; }
  .card { background: #141414; border: 1px solid #222; border-radius: 6px;
          padding: 14px 20px; min-width: 140px; }
  .card .label { color: #666; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
  .card .value { font-size: 22px; font-weight: bold; margin-top: 4px; color: #fff; }
  .card .sub   { font-size: 11px; color: #888; margin-top: 2px; }

  .green  { color: #00c853 !important; }
  .red    { color: #ff3d3d !important; }
  .yellow { color: #ffb300 !important; }
  .gray   { color: #666    !important; }
  .blue   { color: #42a5f5 !important; }

  section { padding: 0 24px 24px; }
  h2 { font-size: 11px; text-transform: uppercase; letter-spacing: 2px;
       color: #555; margin: 20px 0 10px; border-bottom: 1px solid #1e1e1e; padding-bottom: 6px; }

  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; color: #555; font-size: 10px; text-transform: uppercase;
       letter-spacing: 1px; padding: 6px 10px; border-bottom: 1px solid #1e1e1e; }
  td { padding: 8px 10px; border-bottom: 1px solid #181818; vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #161616; }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 3px;
           font-size: 10px; font-weight: bold; letter-spacing: 1px; }
  .badge-long  { background: #003319; color: #00c853; border: 1px solid #00c853; }
  .badge-short { background: #2a0000; color: #ff3d3d; border: 1px solid #ff3d3d; }
  .badge-bear  { background: #2a0000; color: #ff3d3d; border: 1px solid #ff3d3d; }
  .badge-bull  { background: #003319; color: #00c853; border: 1px solid #00c853; }
  .badge-unknown { background: #222; color: #888; border: 1px solid #444; }
  .badge-validated { background: #002b14; color: #69f0ae; border: 1px solid #69f0ae; }
  .badge-active { background: #00234a; color: #42a5f5; border: 1px solid #42a5f5; }
  .badge-watch  { background: #1a1a00; color: #ffb300; border: 1px solid #ffb300; }
  .badge-idle   { background: #141414; color: #555; border: 1px solid #2a2a2a; }

  .coin-grid { display: flex; flex-wrap: wrap; gap: 10px; }
  .coin-card { background: #141414; border: 1px solid #222; border-radius: 6px;
               padding: 12px 16px; min-width: 130px; }
  .coin-card .name { font-size: 14px; font-weight: bold; color: #fff; }
  .coin-card .status { font-size: 10px; margin-top: 6px; }
  .coin-card .pos-detail { font-size: 10px; color: #888; margin-top: 4px; line-height: 1.6; }

  #no-state { color: #555; padding: 40px; text-align: center; }
  .pulse { animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
</style>
</head>
<body>

<header>
  <h1>⬡ jCOIN</h1>
  <span id="cycle-badge" class="badge badge-unknown">CYCLE: —</span>
  <span id="ks-badge" class="badge badge-idle">KS: OK</span>
  <span id="last-update">waiting for data…</span>
</header>

<div class="metrics" id="metrics"></div>

<section>
  <h2>Coin Universe</h2>
  <div class="coin-grid" id="coin-grid"></div>

  <h2>Open Positions</h2>
  <table id="pos-table">
    <thead><tr>
      <th>Symbol</th><th>Side</th><th>Entry Time</th><th>Entry $</th>
      <th>Current $</th><th>Unreal. P&amp;L</th>
      <th>Init Stop</th><th>Trail Stop</th><th>Extreme</th><th>Bars Held</th><th>Risk $</th>
    </tr></thead>
    <tbody id="pos-body"><tr><td colspan="11" class="gray">No open positions</td></tr></tbody>
  </table>

  <h2>Recent Closed Trades</h2>
  <table id="trades-table">
    <thead><tr>
      <th>Symbol</th><th>Side</th><th>Entry</th><th>Exit</th>
      <th>Entry $</th><th>Exit $</th><th>P&amp;L</th><th>R</th><th>Reason</th>
    </tr></thead>
    <tbody id="trades-body"><tr><td colspan="9" class="gray">No trades yet</td></tr></tbody>
  </table>
</section>

<script>
const VALIDATED  = new Set(["BTC","ETH","EGLD","SAND","IMX"]);
const MONITORING = new Set(["ADA","XRP","AVAX","HBAR"]);  // in paper runner, no sealed test yet
const WATCH_LIST = new Set(["NEAR","SUI"]);                // not in runner
const ALL_COINS  = ["BTC","ETH","EGLD","SAND","IMX","ADA","XRP","AVAX","HBAR","NEAR","SUI"];

function fmt$(n)   { return n == null ? '—' : '$' + n.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}); }
function fmtPct(n) { return n == null ? '—' : (n >= 0 ? '+' : '') + (n*100).toFixed(1) + '%'; }
function fmtR(n)   { return n == null ? '—' : (n >= 0 ? '+' : '') + n.toFixed(2) + 'R'; }
function fmtDate(s){ if(!s) return '—'; const d = new Date(s); return d.toISOString().replace('T',' ').slice(0,16) + ' UTC'; }
function clr(n)    { return n >= 0 ? 'green' : 'red'; }

function render(st) {
  if (!st || st.error) {
    document.getElementById('metrics').innerHTML = '<p id="no-state">'+  (st?.error || 'No state file yet') +'</p>';
    return;
  }

  const start = 10000;
  const equity = st.equity;
  const ret = (equity - start) / start;
  const nOpen = (st.positions || []).length;
  const nClosed = (st.closed || []).length;
  const lastTs = st.last_ts || '—';
  const ks = st.killswitch || {};
  // Header badges
  const cyclePhase = st.cycle_phase || 'unknown';
  const cbadge = document.getElementById('cycle-badge');
  cbadge.textContent = 'CYCLE: ' + cyclePhase.toUpperCase();
  cbadge.className = 'badge badge-' + (cyclePhase === 'bear' ? 'bear' : cyclePhase === 'bull' ? 'bull' : 'unknown');

  const ksBadge = document.getElementById('ks-badge');
  if (ks.hard_halted) {
    ksBadge.textContent = 'KS: HARD HALT'; ksBadge.className = 'badge badge-short';
  } else {
    ksBadge.textContent = 'KS: OK'; ksBadge.className = 'badge badge-idle';
  }

  // Metric cards
  document.getElementById('metrics').innerHTML = `
    <div class="card">
      <div class="label">Equity</div>
      <div class="value">${fmt$(equity)}</div>
      <div class="sub ${clr(ret)}">${fmtPct(ret)} from $${start.toLocaleString()}</div>
    </div>
    <div class="card">
      <div class="label">Open Positions</div>
      <div class="value ${nOpen > 0 ? 'blue' : 'gray'}">${nOpen}</div>
      <div class="sub">max 2 concurrent</div>
    </div>
    <div class="card">
      <div class="label">Closed Trades</div>
      <div class="value">${nClosed}</div>
      <div class="sub">since 2021 replay</div>
    </div>
    <div class="card">
      <div class="label">Last Bar</div>
      <div class="value" style="font-size:13px;margin-top:6px">${fmtDate(lastTs)}</div>
      <div class="sub">4h bars, live from krakenfutures</div>
    </div>
    <div class="card">
      <div class="label">Peak Equity</div>
      <div class="value">${fmt$(ks.peak_equity)}</div>
      <div class="sub ${clr(equity - (ks.peak_equity||equity))}">${fmtPct((equity-(ks.peak_equity||equity))/(ks.peak_equity||equity))} from peak</div>
    </div>
  `;

  // Coin grid
  const positions = st.positions || [];
  const posMap = {};
  positions.forEach(p => posMap[p.symbol] = p);
  const barsHeld = st.bars_held || {};

  document.getElementById('coin-grid').innerHTML = ALL_COINS.map(coin => {
    const pos = posMap[coin];
    const bars = barsHeld[coin] || 0;
    let statusHtml, cardBorder = '';
    if (pos) {
      const side = pos.side.toUpperCase();
      statusHtml = `<div class="status"><span class="badge badge-${pos.side}">${side}</span></div>
        <div class="pos-detail">
          Entry: ${fmt$(pos.entry_price)}<br>
          Trail: ${fmt$(pos.trail_stop)}<br>
          Bars: ${bars}
        </div>`;
      cardBorder = `border-color: ${pos.side === 'long' ? '#00c853' : '#ff3d3d'}`;
    } else if (VALIDATED.has(coin)) {
      statusHtml = `<div class="status"><span class="badge badge-validated">VALIDATED</span></div><div class="pos-detail" style="color:#555">sealed test ✓</div>`;
    } else if (MONITORING.has(coin)) {
      statusHtml = `<div class="status"><span class="badge badge-active">MONITORING</span></div><div class="pos-detail" style="color:#555">in paper runner</div>`;
    } else if (WATCH_LIST.has(coin)) {
      statusHtml = `<div class="status"><span class="badge badge-watch">WATCH LIST</span></div><div class="pos-detail" style="color:#555">not in runner</div>`;
    } else {
      statusHtml = `<div class="status"><span class="badge badge-idle">INACTIVE</span></div>`;
    }
    return `<div class="coin-card" style="${cardBorder}">
      <div class="name">${coin}</div>
      ${statusHtml}
    </div>`;
  }).join('');

  // Open positions table
  const posBody = document.getElementById('pos-body');
  const lastPrices = st.last_prices || {};
  if (positions.length === 0) {
    posBody.innerHTML = '<tr><td colspan="11" class="gray">No open positions</td></tr>';
  } else {
    posBody.innerHTML = positions.map(p => {
      const bars = barsHeld[p.symbol] || 0;
      const sc = p.side === 'long' ? 'green' : 'red';
      const cur = lastPrices[p.symbol];
      let upnl = null, upnlR = null, upnlClass = 'gray';
      if (cur != null && p.size != null) {
        const dir = p.side === 'long' ? 1 : -1;
        upnl = dir * (cur - p.entry_price) * p.size;
        upnlR = upnl / (p.risk_dollars || 1);
        upnlClass = upnl >= 0 ? 'green' : 'red';
      }
      return `<tr>
        <td><b>${p.symbol}</b></td>
        <td><span class="badge badge-${p.side}">${p.side.toUpperCase()}</span></td>
        <td>${fmtDate(p.entry_time)}</td>
        <td class="${sc}">${fmt$(p.entry_price)}</td>
        <td>${cur != null ? fmt$(cur) : '<span class="gray">—</span>'}</td>
        <td class="${upnlClass}">${upnl != null ? fmt$(upnl) + ' <span style="color:#666;font-size:10px">(' + fmtR(upnlR) + ')</span>' : '<span class="gray">—</span>'}</td>
        <td>${fmt$(p.init_stop)}</td>
        <td class="yellow">${fmt$(p.trail_stop)}</td>
        <td>${fmt$(p.extreme)}</td>
        <td>${bars}</td>
        <td>${fmt$(p.risk_dollars)}</td>
      </tr>`;
    }).join('');
  }

  // Recent trades (last 25, reversed)
  const closed = (st.closed || []).slice(-25).reverse();
  const tradesBody = document.getElementById('trades-body');
  if (closed.length === 0) {
    tradesBody.innerHTML = '<tr><td colspan="9" class="gray">No trades yet</td></tr>';
  } else {
    tradesBody.innerHTML = closed.map(t => {
      const pnlClass = t.pnl >= 0 ? 'green' : 'red';
      const rClass   = t.R   >= 0 ? 'green' : 'red';
      return `<tr>
        <td><b>${t.symbol}</b></td>
        <td><span class="badge badge-${t.side}">${t.side.toUpperCase()}</span></td>
        <td style="color:#666">${fmtDate(t.entry_time)}</td>
        <td style="color:#666">${fmtDate(t.exit_time)}</td>
        <td>${fmt$(t.entry_price)}</td>
        <td>${fmt$(t.exit_price)}</td>
        <td class="${pnlClass}">${fmt$(t.pnl)}</td>
        <td class="${rClass}">${fmtR(t.R)}</td>
        <td style="color:#555">${t.exit_reason}</td>
      </tr>`;
    }).join('');
  }

  document.getElementById('last-update').textContent =
    'Updated ' + new Date().toLocaleTimeString();
}

async function fetchAndRender() {
  try {
    const r = await fetch('/api/state');
    const st = await r.json();
    render(st);
  } catch(e) {
    console.error(e);
  }
}

// Initial load
fetchAndRender();

// Listen for file-change events via SSE
const evtSource = new EventSource('/api/events');
evtSource.onmessage = () => fetchAndRender();
evtSource.onerror   = () => console.warn('SSE disconnected, will retry');
</script>
</body>
</html>
"""
