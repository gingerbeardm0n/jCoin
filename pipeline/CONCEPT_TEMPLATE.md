# Concept Template — Crypto Educator Setup

**Adapted from jTrader Gap-and-Go concept structure**  
**Last updated:** 2026-06-19

---

## Template Instructions

Use this structure for every distinct trading setup extracted from educator sources (TradingRiot, Trader Mayne, CanteringClark). Aggregate all sources describing the same setup into one concept page.

Sections: Definition → Setup Criteria → Entry Trigger → Add-On Mechanics → Stop Criteria → Profit Targets → Hold Duration → Market Condition Dependency → Red Flags → Example Trades → Decision Rules.

---

# Concept: [SETUP NAME]

**Last updated:** [DATE]  
**Source:** Educator names and videos  
**Sample size:** [N] trades  
**Win rate:** [X]% ([W/L count])

---

## Definition

One-paragraph summary. What is this setup? How does it differ from similar patterns?

Key distinctions:
- **vs. [other setup]:** [what makes this one different]
- **vs. [other setup]:** [differentiator]

---

## Setup Criteria

### Required
| Criterion | Target | Notes |
|-----------|--------|-------|
| Market regime | e.g., "ranging" or "trending" | When is this valid? |
| Funding rate | e.g., "+0.05% to +0.15%" | Extreme or neutral? |
| Price zone | e.g., "VWAP band ±2σ" | Where in the structure? |
| Liquidity condition | e.g., "near support cluster" | Key level or cluster? |
| Pair | e.g., "BTC / ETH preferred, avoid low-vol alts" | Instrument scope? |

### Ideal (increases conviction)
- [condition that improves win rate or reduces draw-down]
- [confirmation signal that educator mentioned]

---

## Entry Trigger

**Primary trigger:** [What breaks or signals entry]  
(Key phrase educator used: "[exact quote or paraphrase]")

**Mechanism:**
1. [Step 1: how to identify the setup]
2. [Step 2: what confirms it]
3. [Step 3: how price action triggers entry]
4. [Step 4: entry execution (maker vs taker)]

**Time of entry:** [When in the session — e.g., "after liquidation cascade" or "funding rate extreme"]
- [Example timing]
- [Another timing pattern]

---

## Add-On Mechanics

Based on educator commentary, most common approaches:

| Mechanic | Frequency | Description |
|----------|-----------|-------------|
| [Approach 1] | [e.g., "most common"] | [What it is] |
| [Approach 2] | [e.g., "common"] | [What it is] |

**Key principle:** [Educator's rule about sizing / adding — e.g., "sizes into momentum, not weakness"] 

---

## Stop Criteria

| Stop Type | When to Use |
|-----------|-------------|
| [Stop type 1] | [Condition that triggers it] |
| [Stop type 2] | [Condition that triggers it] |

**Stop placement:** [How far from entry, relative to what level]

**Critical rule:** [Any hard rule educator stated about stops]

---

## Profit Targets

| Target Type | How Determined | Notes |
|-------------|---|---|
| T1 | e.g., "VWAP +" | [Description] |
| T2 | e.g., "next resistance" | [Description] |

**Observed behavior:** [Examples or patterns in actual trades]

---

## Hold Duration

| Duration | % of trades | Notes |
|----------|---|---|
| [e.g., "Scalp (< 5 min)"] | [X%] | [When/why] |
| [e.g., "Short (5-30 min)"] | [X%] | [When/why] |

**Interpretation:** [What this tells us about the setup]

---

## Market Condition Dependency

Does this setup perform differently based on regime, funding extremes, liquidation context?

- **[Condition 1]:** Educator noted [outcome]
- **[Condition 2]:** Educator noted [outcome]

---

## Red Flags (When to Skip)

- [Red flag 1 — condition that causes failures]
- [Red flag 2 — condition that causes failures]
- [Red flag 3 — condition that causes failures]

---

## Example Trades (from session transcripts)

**ITEM XXXX — [PAIR] ([pattern name]):**  
[1-2 sentence description of the trade: catalyst/signal → entry price/size → add-ons → exit → P&L → key lesson]

**ITEM XXXX — [PAIR] ([pattern name]):**  
[Similar structure]

**ITEM XXXX — [PAIR] (cautionary tale):**  
[Trade that failed or highlighted a red flag — valuable for learning what NOT to do]

---

## jCoin Decision Rules

Based on the above analysis, these are the concrete rules jCoin should apply:

```
[SETUP_NAME] entry conditions:
  - market_regime == [value]
  - funding_rate in range [value] (or extreme-[direction])
  - price in zone [definition]
  - [additional condition]
  
  IF [condition_a]:
    [parameter or action]
  ELSE:
    [alternative parameter or action]

Entry trigger:
  - [precise technical condition]
  - [confirmation signal if any]

Stop:
  - initial stop = [price level or distance]
  - if [condition] = exit [percentage]

Targets:
  - T1 = [price or zone definition]
    scale [%] at T1, hold rest
  - T2 = [price or zone definition]

Hold:
  - default = [scalp|short|extended]
  - extend only if [condition]
  - exit all by [time/condition]

Liquidation handling:
  - [if liquidations are relevant to this setup]

Risk management:
  - position size = [rule, e.g., "0.5% equity per trade"]
  - max loss per session = [if educator stated]
```

---

## Data Coverage & Confidence

| Field | Coverage | Confidence | Notes |
|-------|----------|-----------|-------|
| SETUP_NAME | [N] distinct trades | [High/Medium/Low] | [Coverage note] |
| ENTRY_TRIGGER | [N] with trigger data | [High/Medium/Low] | [Coverage note] |
| HOLD_DURATION | [N] populated | [High/Medium/Low] | [Coverage note] |
| FUNDING_RATE | [N] populated | [High/Medium/Low] | [Coverage note] |
| CVD_SIGNAL | [N] populated | [High/Medium/Low] | [Coverage note] |

**Next pass opportunity:** [What additional research or verification would improve this concept]

---

## Aggregated Educator Consensus

This concept aggregates insights from:
- TradingRiot: [specific observations or trades]
- Trader Mayne: [specific observations or trades]
- CanteringClark: [specific observations or trades]

**Conflicts or variations:** [If educators disagreed on key parameters, note it here]

**Highest confidence elements:** [The rules/parameters that appear consistently across educators]

---

*End of Concept Template*
