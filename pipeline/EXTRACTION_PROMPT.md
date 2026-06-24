# Crypto Educator Transcript Extraction Instructions

---

## 1. OUTPUT FILE STRUCTURE

Extractions are written to **chunk files**. Each chunk covers ~100 videos and is named:

```
EDUCATOR_SUMMARIES_XXXX-XXXX.md
```

**Examples:**
- ITEMS 0001–0100 → `EDUCATOR_SUMMARIES_0001-0100.md`
- ITEMS 0101–0200 → `EDUCATOR_SUMMARIES_0101-0200.md`

When appending an ITEM, determine which chunk covers that range and write to that file only. If the chunk file does not exist, create it with no header — just start appending entries.

`EDUCATOR_SUMMARIES_MASTER.md` is frozen. **Never write to it.**

---

## 2. BATCH WORKFLOW

Extractions run in **batches of 10 files, sequentially**. A Haiku agent handles extraction for each batch of 10. A Sonnet agent reviews and corrects after each batch.

**Rules:**
- Never run two extraction batches concurrently against the same chunk file
- Always complete one batch (extract → append → Sonnet review → corrections) before starting the next
- Append each ITEM to the chunk file immediately after extraction
- Every entry must end with `---` on its own line

**Haiku agent chat reporting (one line per file, nothing else):**
- Success: `ITEM XXXX: ✓`
- Failure: `ITEM XXXX FAILED — [one sentence reason]`

Do not paste the extraction into chat. Do not narrate steps.

---

## 3. DETERMINING SOURCE TYPE

Read the filename/context first:

- Contains video title, "tutorial", "strategy", "breakdown" → likely `Educational`
- Contains "trade recap", "live session", "session results" → likely `Live Trading`
- Presents rules/system without personal execution → `Educational`
- Shows specific entry/exit fills with real P&L → `Live Trading`

**Decision rule:** If educator executed at least one real-money perpetual trade in the video → use `Live Trading`. If they did not execute any trades → use `Educational`.

---

## 4. CONTROLLED VOCABULARY

All allowed values for every field. Use **only** the values listed here.

**TYPE:**
`Live Trading` | `Educational`

**Fields for FORMAT: Live Trading:**

| Field | Allowed Values |
|-------|----------------|
| PAIR | BTC, ETH, ALT (alt/alts for altcoin) |
| STRATEGY | `maker-mean-reversion` `taker-breakout` `liquidation-sweep` `funding-carry` `grid` `unknown` |
| DIRECTION | `long` `short` `long+short` |
| LEVERAGE | `1x` `2x` `3x` `5x` `10x+` |
| NEWS | `yes` `no` |
| OUTCOME | `WIN` `LOSS` `BE` |
| market_regime | `trending` `ranging` `post-liq-sweep` `funding-extreme` `neutral` |
| funding_condition | `extreme-long` `extreme-short` `neutral` |
| cvd_signal | `bullish-div` `bearish-div` `none` `unknown` |
| liquidation_context | `cluster-above` `cluster-below` `cascade-observed` `none` `unknown` |

**Shared fields (all formats):**

| Field | Allowed Values |
|-------|----------------|
| market | `"hot"` `"cold"` `"neutral"` |
| acct_state | `"building-cushion"` `"in-drawdown"` `"at-goal"` `"exceeded-goal"` `"normal"` `null` |

---

## 5. SHARED METADATA FIELDS

These fields appear in both FORMAT sections. Definitions are authoritative.

---

**market**
Overall market environment. Use educator's own commentary as the signal.

| Value | Signals |
|-------|---------|
| `"hot"` | High volatility, frequent liquidation cascades, funding rates extreme, many tradeable setups |
| `"cold"` | Low volatility, few clear setups, tight ranges, slow fills |
| `"neutral"` | Neither clearly hot nor cold, or cannot be determined |

---

**acct_state**
Educator's account state relative to goals.

| Value | Use When |
|-------|----------|
| `"building-cushion"` | Conservative, accumulating profit gradually |
| `"in-drawdown"` | Recovering from recent losses |
| `"at-goal"` | Hit session goal, considering stopping |
| `"exceeded-goal"` | Significantly surpassed session goal |
| `"normal"` | No specific goal-related state mentioned |
| `null` | Educational format only |

---

## 6. FORMAT: Live Trading

### What to Extract

Read the full transcript. Identify all trades the educator personally made. Produce output in the exact format below.

**Extract only trades executed by the educator. Do NOT include:**
- Trades by viewers or chat members
- Simulator/paper trades
- Setups mentioned but not entered
- "Should have" or "missed" trades

---

### Output Template

```
ITEM [NUMBER] | TYPE: Live Trading
---

TRADES:
| #  | PAIR | ENTRY PRICE | POSITION SIZE | STRATEGY | DIRECTION | LEVERAGE | ENTRY SETUP | EXIT | RESULT | OUTCOME |
|----|------|-------------|---------------|----------|-----------|----------|-------------|------|--------|---------|
| 1  | [PR]  | [PRICE]     | [SIZE]        | [STRAT]  | [DIR]     | [LEV]    | [SETUP]     | [EX] | [+/-$] | [W/L/BE]|

SUMMARY:
[150-200 words of prose, third person, no bullet points]

METADATA:
{"p&l": "[VALUE]", "record": "[VALUE]",
 "market": "[VALUE]",
 "market_regime": "[VALUE]",
 "funding_condition": "[VALUE]",
 "cvd_signal": "[VALUE]",
 "liquidation_context": "[VALUE]",
 "acct_state": "[VALUE]",
 "size_context": "[VALUE]",
 "session_end": "[VALUE]",
 "behavioral_deviation": VALUE}

---
```

---

### File Header

**Format:** `ITEM [NUMBER] | TYPE: Live Trading`

[NUMBER]: Use the file identifier.  
[TYPE]: `Live Trading` or `Educational`

---

### Trades Table

Exactly **11 columns** in this order:

`# | PAIR | ENTRY PRICE | POSITION SIZE | STRATEGY | DIRECTION | LEVERAGE | ENTRY SETUP | EXIT | RESULT | OUTCOME`

Always include the header row and the `|---|` separator.

---

**Column 1: #**  
Sequential integer starting at 1.

**Column 2: PAIR**  
BTC, ETH, ALT (alt coin), or specific symbol (e.g., SOLUSDT).

**Column 3: ENTRY PRICE**  
Price where position was opened. Format: `$45,200` or `$45,200-$45,350` for multi-entry.

**Column 4: POSITION SIZE**  
Contracts or quote units. Format: `1 BTC` or `50 contracts` or `$10K`.

**Column 5: STRATEGY**  
How they traded: `maker-mean-reversion` | `taker-breakout` | `liquidation-sweep` | `funding-carry` | `grid` | `unknown`

**Column 6: DIRECTION**  
`long` | `short` | `long+short` (if both in same session)

**Column 7: LEVERAGE**  
`1x` | `2x` | `3x` | `5x` | `10x+`

**Column 8: ENTRY SETUP**  
Short description (under 10 words). Examples:
- `CVD divergence / mean reversion at VWAP`
- `Liquidation cluster above, maker bid at level`
- `Funding rate extreme short, scalp long`
- `Breakout above resistance on volume`

**Column 9: EXIT**  
Always begins with `PROF:` or `STOP:`.

- `PROF: [reason]` — for profitable or breakeven exits
- `STOP: [reason]` — for losing exits

Examples:
- `PROF: took target at VWAP + 0.5%`
- `STOP: failed breakout below support`
- `STOP: liquidation cascade reversed`

**EXIT prefix must match OUTCOME:**
- `PROF:` → OUTCOME must be `WIN` or `BE`
- `STOP:` → OUTCOME must be `LOSS`

**Column 10: RESULT**  
Dollar profit or loss. Format: `+$500` | `-$1,200` | `$0` | `unknown`

Always include +/- sign, $, commas for thousands.

**Column 11: OUTCOME**  
`WIN` | `LOSS` | `BE`

---

### Summary

Write **150-200 words** of flowing prose. Always **third person** — use "The educator" or their name, not "I."

Must address:
1. **Entry reasoning** — What gave them conviction? CVD state? OI behavior? Funding extreme?
2. **Exit reasoning** — Planned (target hit) or reactive (reversal, liquidation, time stop)?
3. **Risk management** — Position sizing, leverage choice, stop placement
4. **Market context** — Regime, funding condition, liquidation clusters observed
5. **Behavioral observations** — Did they follow their rules? Hesitation? FOMO?
6. **Key lesson** — If stated explicitly, include it

Do NOT restate the trade table. Add context and reasoning.

---

### Metadata — Live Trading

**11 fields** in **this exact order**. Never reorder or add fields.

```json
{"p&l": "VALUE", "record": "VALUE",
 "market": "VALUE", 
 "market_regime": "VALUE",
 "funding_condition": "VALUE",
 "cvd_signal": "VALUE",
 "liquidation_context": "VALUE",
 "acct_state": "VALUE",
 "size_context": "VALUE",
 "session_end": "VALUE",
 "behavioral_deviation": VALUE}
```

---

**p&l**  
Total for the session. Format: `"+$1,839"` or `"-$4,500"`. Must equal sum of RESULT column.

**record**  
Win-loss record. Format: `"XW-XL"` or `"XW-XL-XBE"` if breakeven occurred.

**market**  
`"hot"` | `"cold"` | `"neutral"` — see Section 5.

**market_regime**  
`"trending"` | `"ranging"` | `"post-liq-sweep"` | `"funding-extreme"` | `"neutral"`

**funding_condition**  
What was the funding rate environment? `"extreme-long"` | `"extreme-short"` | `"neutral"`

**cvd_signal**  
Cumulative volume delta state: `"bullish-div"` | `"bearish-div"` | `"none"` | `"unknown"`

**liquidation_context**  
Were liquidation cascades a factor? `"cluster-above"` | `"cluster-below"` | `"cascade-observed"` | `"none"` | `"unknown"`

**acct_state**  
`"building-cushion"` | `"in-drawdown"` | `"at-goal"` | `"exceeded-goal"` | `"normal"` | `null`

**size_context**  
Position sizing: `"full"` | `"reduced"` | `"oversized"`

**session_end**  
When/why did they stop? Format: `"14:30 - hit target"` or `"unknown"`

**behavioral_deviation**  
Any clear deviation from stated rules? `"fomo-entry"` | `"revenge-trade"` | `"oversize"` | `"broke-rules"` | `null`

---

### Critical Rules — Live Trading

1. **FORMAT IS FIXED.** Every output: FILE HEADER → `---` → TRADES TABLE → SUMMARY → METADATA → `---`. Never omit. Never reorder.

2. **ONLY EDUCATOR'S TRADES.** Never include trades by viewers or mentioned but not executed.

3. **P&L MUST EQUAL SUM OF RESULT VALUES.** Calculate the sum before writing metadata. They must match exactly.

4. **EXIT PREFIX MUST MATCH OUTCOME.** `PROF:` pairs with WIN/BE. `STOP:` pairs with LOSS.

5. **NULL IS JSON NULL.** No quotes: `"behavioral_deviation": null` NOT `"behavioral_deviation": "null"`. Booleans also have no quotes.

6. **ONE ROW = ONE COMPLETE TRADE.** Adds and partial exits belong in the same row. Only create a new row if they fully exited and re-entered.

7. **NEVER REJECT A FILE.** Every item must produce output. If unusual or complex, adapt using edge cases. Rejection is unacceptable.

---

### Edge Cases — Live Trading

**No trades taken:**  
Replace TRADES table with: `TRADES: NO TRADES TAKEN`  
Set `"p&l": "$0"` and `"record": "0W-0L"`.

**Multiple entries at different prices:**  
`ENTRY PRICE` shows range: `$45,200-$45,350`. Capture price range and note adds in ENTRY SETUP.

**Same pair traded multiple times (full exit and re-entry):**  
Create separate numbered row for each complete cycle.

---

## 7. FORMAT: Educational

Use this format when educator did not execute real-money trades.

### Output Template

```
ITEM [NUMBER] | TYPE: Educational
---

TRADES: NO TRADES TAKEN

SUMMARY:
[150-200 words of prose, third person, no bullet points]

METADATA:
{"p&l": null, "record": null,
 "market": null,
 "market_regime": VALUE,
 "funding_condition": VALUE,
 "cvd_signal": VALUE,
 "liquidation_context": VALUE,
 "acct_state": VALUE,
 "size_context": null,
 "session_end": null,
 "behavioral_deviation": null}

---
```

### Summary — Educational

Write **150-200 words** of prose. Third person. Cover the topic, specific trading lessons, market observations, and actionable insights.

### Metadata — Educational

These fields are **always null** for Educational:
- `p&l` → `null`
- `record` → `null`
- `market` → `null`
- `size_context` → `null`
- `session_end` → `null`
- `behavioral_deviation` → `null`

These may be non-null if educator mentions them:
- `market_regime`, `funding_condition`, `cvd_signal`, `liquidation_context`, `acct_state`

---

## 8. OVERALL CONTEXT

This extraction project builds a structured dataset from educator videos (TradingRiot, Trader Mayne, CanteringClark) that informs jCoin's perpetual futures momentum algorithm.

**Format consistency is the single most important requirement.** Every output must look identical in structure within its format type. A reviewer should see the exact same structure every time.

---

*End of Instructions*
