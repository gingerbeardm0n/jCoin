# Enrichment Prompt — Crypto Educator Trade Mechanics (Haiku Pass 1)

**Last updated:** 2026-06-19  
**Purpose:** Extract structured trade mechanics from educator summaries  
**Pass type:** Summary-only (no re-reading transcripts)  
**Batch size:** 25 ITEM entries per agent call

---

## How to Use This Prompt

1. Split the chunk file into batches of 25 ITEM entries
2. Send this prompt + batch content to a Haiku agent
3. Collect all batch outputs into a single file (e.g. `haiku_enrichment_0001-0100.txt`)
4. Run `enrichment_inserter.py` to insert mechanics tables into chunk file

---

## The Prompt (send this verbatim to Haiku, followed by the batch content)

---

You are processing crypto educator perpetual trading video transcript summaries to extract structured trade mechanics data. This is a **strict summary-only pass** — extract only from the SUMMARY text and TRADES table. Do NOT infer, fabricate, or use outside knowledge.

### Input Format

Each ITEM entry has this structure:
```
ITEM XXXX | TYPE: ...
---

TRADES:
| # | PAIR | ENTRY PRICE | POSITION SIZE | STRATEGY | DIRECTION | LEVERAGE | ENTRY SETUP | EXIT | RESULT | OUTCOME |

SUMMARY:
[narrative text]

METADATA:
{json}

---
```

Some entries have `TRADES: NO TRADES TAKEN` — skip those entirely, output nothing for them.

### Your Task

For each ITEM entry that has trades: produce a `TRADE_MECHANICS` table with one row per trade, extracting mechanics from the SUMMARY and TRADES table.

### TRADE_MECHANICS Table Schema

```
| # | PAIR | FUNDING_RATE | OI_BEHAVIOR | CVD_SIGNAL | PATTERN_TYPE | ENTRY_TRIGGER | ADD_ON_MECHANIC | STOP_CRITERIA | TARGET | TIME_OF_ENTRY | HOLD_DURATION | LIQUIDATION_CONTEXT |
```

### Column Definitions

| Column | What to extract | Example values |
|--------|-----------------|-----------------|
| `#` | Trade row number — matches TRADES table | `1`, `2`, `3` |
| `PAIR` | BTC, ETH, ALT | `BTC`, `ETH` |
| `FUNDING_RATE` | Funding rate at entry, extreme conditions | `+0.08%`, `−0.12%`, `extreme`, `neutral` |
| `OI_BEHAVIOR` | Open interest state/change | `spiking`, `declining`, `trapped-longs`, `trapped-shorts`, `neutral` |
| `CVD_SIGNAL` | Cumulative volume delta state | `bullish-div`, `bearish-div`, `absorption`, `exhaustion`, `unknown` |
| `PATTERN_TYPE` | Setup type — use controlled vocab | see vocab below |
| `ENTRY_TRIGGER` | Specific price level or signal that triggered entry | `break $46K resistance`, `CVD div at VWAP`, `liquidation cluster bounce` |
| `ADD_ON_MECHANIC` | How they added after initial entry | `added on dip to support`, `scaled in $5K→$10K`, `grid entries` |
| `STOP_CRITERIA` | Stop conditions being watched | `below support $45K`, `CVD neg cross`, `below liquidation cluster` |
| `TARGET` | First profit target | `VWAP`, `$46K resistance`, `+0.5% from entry` |
| `TIME_OF_ENTRY` | Time of entry if mentioned | `14:32 UTC`, `post-lunch`, `unknown` |
| `HOLD_DURATION` | How long position was held | `scalp`, `short`, `extended`, `unknown` |
| `LIQUIDATION_CONTEXT` | Were liquidations a factor? | `cluster-above`, `cluster-below`, `cascade`, `none`, `unknown` |

### Controlled Vocabulary

**PATTERN_TYPE** (pick closest match):
`maker-mean-reversion` | `taker-breakout` | `liquidation-sweep` | `funding-carry` | `funding-pop` | `vwap-reclaim` | `range-extremity` | `grid` | `unknown`

**HOLD_DURATION:**
- `scalp` = seconds to ~5 minutes
- `short` = 5–30 minutes
- `extended` = 30 minutes+
- `unknown` = cannot determine

### Fill Rules

- Use `-` when the data is not found anywhere in the summary
- Use `n/a` when the field is genuinely not applicable to this trade
- Keep cell values SHORT — brief phrases only, not full sentences
- FUNDING_RATE and OI_BEHAVIOR often apply to all trades in the same session — carry them across rows if consistent
- PATTERN_TYPE should match the STRATEGY column in the TRADES table where possible, mapped to controlled vocab

### Output Format

For each ITEM entry with trades, output:

```
=== ITEM 0042 ===
TRADE_MECHANICS:
| # | PAIR | FUNDING_RATE | OI_BEHAVIOR | CVD_SIGNAL | PATTERN_TYPE | ENTRY_TRIGGER | ADD_ON_MECHANIC | STOP_CRITERIA | TARGET | TIME_OF_ENTRY | HOLD_DURATION | LIQUIDATION_CONTEXT |
|---|------|--------------|-------------|------------|--------------|----------------|-----------------|---------------|--------|---------------|----------------|--------------------|
| 1 | BTC  | extreme-long | spiking     | bullish-div| maker-mean-reversion | CVD div at VWAP, maker bid at support | none | below support $45K | VWAP | 14:32 | short | cluster-above |
```

After ALL file entries, output the TSV audit block:

```
=== TSV_AUDIT ===
item	trade	pair	FUNDING_RATE	OI_BEHAVIOR	CVD_SIGNAL	PATTERN_TYPE	ENTRY_TRIGGER	ADD_ON_MECHANIC	STOP_CRITERIA	TARGET	TIME_OF_ENTRY	HOLD_DURATION	LIQUIDATION_CONTEXT
0042	1	BTC	S	S	S	S	S	N	S	S	S	S	S
```

**TSV audit values:**
- `S` = value was found and extracted from summary
- `-` = not found in summary (cell contains `-` in mechanics table)
- `N` = not applicable (cell contains `n/a` in mechanics table)

### Rules

- Output ONLY the `=== ITEM XXXX ===` blocks and the `=== TSV_AUDIT ===` block
- No commentary, no explanations, no preamble
- Do not rewrite or repeat the original TRADES table or SUMMARY
- Do not skip any ITEM entry that has trades
- ITEM entries with `TRADES: NO TRADES TAKEN` — output nothing
- **CRITICAL — TSV column count:** Every TSV data row MUST have exactly 13 data values after the pair column (15 tab-separated values total: item, trade, pair + 13 data columns). Never output fewer. Column order is fixed: FUNDING_RATE, OI_BEHAVIOR, CVD_SIGNAL, PATTERN_TYPE, ENTRY_TRIGGER, ADD_ON_MECHANIC, STOP_CRITERIA, TARGET, TIME_OF_ENTRY, HOLD_DURATION, LIQUIDATION_CONTEXT.

---

## Now process the following ITEM entries (batch of 25):

[INSERT BATCH CONTENT HERE]
