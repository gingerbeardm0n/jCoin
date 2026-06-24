# Compression Pipeline — Crypto Educator Transcripts
# Adapted from jTrader Stock-Picker pipeline
# Last updated: 2026-06-19

---

## SECTION 1 — PROCESS OVERVIEW

Read this section to get fully up to speed at the start of any new session.

### Project Context

Project: **jCoin** — autonomous perpetual futures momentum scalping algorithm.  
Educator sources: TradingRiot, Trader Mayne, CanteringClark  
Goal of this pipeline: compress raw video transcripts/articles into lossless caveman-prose files for downstream analysis and algorithm training.

### File Locations

| Resource | Path |
|----------|------|
| Raw transcripts/articles (source) | `C:\Repositories\jCoin\educator_library\raw\` |
| Compressed output | `C:\Repositories\jCoin\educator_library\compressed\` |
| This file | `C:\Repositories\jCoin\pipeline\COMPRESSION_PROMPT.md` |

Source filenames follow pattern: `EDUCATOR_[Name]_[Title].txt` or `.md`  
Output filenames follow pattern: `EDUCATOR_[Name]_[Title]_compressed.md`

### Batch Workflow

Process in **batches of 20 items**, sequentially. Complete one batch fully before starting the next.

**Per-batch steps:**

1. **Identify items** — determine next 20 source files
2. **Spawn agent** — use `subagent_type: caveman:cavecrew-builder`. Give it the abbreviated prompt (see Section 2).
3. **No QA by default** — skip QA unless the agent's report looks suspicious (vague, missing trades, no R:R numbers).
4. **Report back** — one line per file (success/failure).

### Orchestrator Rules (Critical)

- **Only the orchestrator spawns agents.** Haiku sub-agents never spawn additional agents.
- **Haiku agents report back if stuck.** If a Haiku agent cannot read a file, encounters an error, it must stop and report.
- **Orchestrator reads source only when needed.** Only read the full source if the agent's report is insufficient.
- **No parallel agents — ever.** Sequential execution only.

---

## SECTION 2 — AGENT PROMPT (Copy-Paste Verbatim)

> **Orchestrator note**: Use `subagent_type: caveman:cavecrew-builder`. Send the abbreviated prompt below. Replace `[START]` and `[END]` with actual file numbers or educator names. The abbreviated prompt is sufficient.

### Abbreviated Prompt (preferred — lower token overhead)

```
You are a transcript compression agent. Compress each raw transcript into caveman-prose format.

**OUTPUT DIR**: `C:\Repositories\jCoin\educator_library\compressed\`
**SOURCE DIR**: `C:\Repositories\jCoin\educator_library\raw\`

**FILES TO COMPRESS**: [START] through [END] (20 items)

**OUTPUT FILENAME FORMAT**: `EDUCATOR_[Name]_[Title]_compressed.md`

**COMPRESSION RULES**:
- Caveman prose: drop articles, filler words, pleasantries
- Fragments OK. Short punchy sentences. → for cause/effect
- Abbreviations: K=thousand, ETH=Ethereum, BTC=Bitcoin, CVD=cumulative volume delta, OI=open interest, perp=perpetual, VWAP, EMA, ATH, POC, HVN=high volume node
- Keep ALL numbers exact (P&L, position sizes, prices, funding rates, liquidation levels, %)
- Keep ALL tickers and pair names (BTCUSDT, ETHUSDT, ALT symbols, etc.)
- Keep trade mechanics, entry/exit reasons, mistakes, rules stated
- Keep crypto-specific signals: funding rate extremes, open interest behavior, CVD divergence, liquidation cascades, perpetual vs spot distinction
- Target: ~1,500-2,000 chars per file
- Do NOT invent details. Do NOT add meta-commentary.

**PROCESS**: For each file: read source → write compressed output → next file.
Skip missing files with a note. Do not spawn sub-agents. Report all 20 when done.
```

---

## SECTION 3 — WHAT TO DELETE

- Filler words: "alright guys", "you know", "actually", "basically", "like", "so", "right", "I mean", "let me just", "real quick", "honestly", "literally"
- Pleasantries: "hey everyone", "welcome back", "thanks for watching", "smash the like button", "hit subscribe"
- Emotional commentary with zero trading info: "I was so frustrated", "that felt amazing", "I couldn't believe it"
- Personal stories/anecdotes with NO price/time/decision facts embedded
- Repeated restatements of the same fact
- Off-topic tangents (family, weather, equipment) UNLESS a price or time is embedded
- Platform/setup tutorial segments (exchange walkthroughs, terminal demos)
- Outro/housekeeping: subscribe prompts, course mentions, social media, website plugs
- General crypto trading education that restates known rules without session-specific context

---

## SECTION 4 — WHAT TO PRESERVE (NEVER DELETE)

- Personal stories that CONTAIN a price level, time, or trade outcome: strip the story, keep the fact. Example: "I was monitoring it at 3pm and when I checked back at 3:47pm the funding rate had swung to -0.15%" → "3:47pm: funding -0.15%"
- Price sequences — preserve order AND direction. "ETH flushed to $2,400 then I entered the bounce at $2,380" → "flush $2,400 → bounce entry $2,380" NOT "entry $2,380, flush $2,400" (reversed = wrong meaning)
- Every pair mentioned
- Every price level (entry, exit, liquidation line, resistance, support, VWAP, round number)
- Every position size (contracts, leverage)
- Every specific time mentioned
- Every pattern name (range-extremity, liquidation sweep, CVD divergence, funding pop, etc.)
- Every trading rule stated or invoked during this session
- Every P&L number (per trade AND session total)
- Every scanner/signal detail (funding rate, OI extreme, CVD state, liquidation cluster, vol spike)
- Every "should have / mistake / regret" — CRITICAL for learning
- Every add-on entry or partial exit step with prices and sizes
- Every reason given for entering or exiting
- Every reason given for PASSING on a trade (skips are as important as entries)
- Funding rate observations (extreme long/short bias, reversal tells, carry income calculations)
- Open interest behavior (spikes, concentration, traps, liquidation risk)
- CVD/order-flow signals (divergence, exhaustion, absorption, buying/selling pressure)
- Liquidation signals (cascade, local bottom/top, trap indicators)
- Perpetual vs spot distinction when mentioned
- Time-of-day or market regime commentary

---

## SECTION 5 — OUTPUT FORMAT

- Caveman prose: drop articles (a/an/the), filler, pleasantries
- Abbreviate: K=thousand, ETH, BTC, CVD, OI, perp, VWAP, EMA, ATH, POC, HVN
- Fragments OK. Use → for cause/effect or price sequences
- Group by pair/trade when logical
- **First line**: date (if stated), total P&L, session type (daily recap / live / educational / strategy guide)
- **Per trade**: PAIR: catalyst/signal → entry price/contracts → add-ons → exit price → P&L → reason
- **Per skip/pass**: PAIR (PASS): reason
- **Signals section** at end: funded-rate observations, OI behavior, CVD state, liquidation signals
- **Rules section** at end: numbered list of rules explicitly stated this session
- **Regrets section** at end: what they said they should have done differently

Target length: ~1,500–2,000 characters from a typical 15–20KB transcript (10x compression)

Output: ONLY the compressed text. No preamble, no "here is the compressed version", no commentary.

---

## SECTION 6 — CRYPTO-SPECIFIC SIGNALS TO CAPTURE

- **Funding rate**: rate at entry, rate at exit, whether they mentioned funding avoidance, carry trade income
- **Open interest**: spiking at highs/lows, concentration zones, used to identify traps
- **CVD divergence**: bullish vs bearish divergence between price and cumulative volume delta
- **Liquidation signals**: liquidation cascades observed, wick patterns suggesting liquidation cluster, recovery tells
- **Perpetual vs spot**: when they note trading perp (leverage/carry) vs spot (no funding), distinction matters for rules
- **Market regime**: trending, ranging, liquidation sweep aftermath, funding spike into session

---

## SECTION 7 — ERROR HANDLING

If you cannot read a file, encounter a file that is empty, or are unsure how to handle it: **stop and report back immediately**. Do not guess. Do not skip silently. Report:
- The filename
- What you attempted
- What went wrong or why you are unsure

Do not attempt to infer or fabricate content for any file you cannot fully read.
