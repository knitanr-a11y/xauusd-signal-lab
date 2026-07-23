# NEXT CHAT HANDOFF — MOCHIPOYO ALERT RESEARCH — M9S DONE / M9T NEXT

Date: 2026-07-24

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

This document is the current restart point if the ChatGPT conversation reaches its length limit unexpectedly.

---

## 1. User's actual objective

The final goal is **not exact Mochipoyo reproduction**.

The real objective is:

- trade only where FX/crypto has robust edge,
- high win rate when possible,
- useful portfolio-level trade frequency,
- PF materially above 1 after realistic costs,
- lower drawdown and smaller loss tails,
- improve reward/risk so the system is not dependent on a high win rate to offset oversized losses,
- eventually use several timeframes and both XAUUSD and BTCUSD rather than forcing one timeframe to provide all frequency.

Critical user clarification:

> A single branch does not need to preserve high frequency. If M5/M15/H1/H4 and BTC are all available, each branch can be stricter and quality can be prioritized. Portfolio breadth can supply frequency.

Therefore do **not** protect M15 trade count at the cost of weak trades.

---

## 2. Absolute safety / research contracts

Current project remains **audit-only**.

All remain false/off:

- `discord_send=false`
- `mt5_order=false`
- `live_ready=false`
- `final_signal=false`
- `entry_gate_enabled=false`

Never:

- use future bars, future TP/SL/outcomes, or unresolved future information in candidate construction,
- use open/unconfirmed OHLC where the contract requires closed bars,
- silently change M7C formulas/thresholds,
- reset M7C runtime manifest,
- stop/reset M8C,
- reset/reuse M8C prospective start,
- backfill a new prospective shadow,
- claim commission/swap are modeled when they are not,
- claim historical proxy events are genuine Mochipoyo source truth,
- transplant GOLD rules directly into BTC,
- sum signals from multiple timeframes as independent trades without deduplication,
- pyramid M5/M15/H1/H4 merely because they signal the same direction.

Trading/research time basis is MT5 server time. Do not convert research logic to JST.

The newest CSV row is contractually closed where the project says so.

---

## 3. User operating preferences

- User does not run Python directly. Only numbered BATs when a local run is actually needed.
- Do not ask the user to run a BAT for each exploratory iteration.
- Assistant-side exploration on uploaded history is preferred.
- Ask for a local BAT only at an important deterministic or fresh prospective checkpoint.
- User strongly dislikes guessing. Use exact files, exact rules, exact metrics, exact commit state.
- When a BAT is requested, state whether it is one-time or persistent, whether M7C/M8C/collector remain running, success/error text, output path, and submission file.

Local repo root:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\xauusd-signal-lab-clean\xauusd-signal-lab`

MT5 Files root:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files`

User GOLD history folder:

`MT5 Files\gold_v3_2023_2026\`

Files:

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m5.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`
- `gold_v3_2023_2026_h4.csv`
- `gold_v3_2023_2026_d1.csv`

Period: 2023-01-03 through 2026-06-19.

No comparable BTC 2023-2026 history has been supplied.

---

## 4. M7C frozen source-proxy kernel — DO NOT CHANGE

M15 source-proxy formula:

- PRIMARY_LONG: `IDLE AND rci9_turn_up AND BULLISH_STACK`
- PRIMARY_SHORT: `IDLE AND rci9_turn_down AND BEARISH_STACK`
- LONG_EXIT: `ACTIVE_LONG AND rci9 >= 78.333333333333`
- SHORT_EXIT: `ACTIVE_SHORT AND rci9 <= -75`
- REENTRY: `NOT_MODELED_OR_SCORED`

RCI turn:

- up: current > previous AND previous <= previous2
- down: current < previous AND previous >= previous2

EMA:

- bullish: EMA20 > EMA30 > EMA40
- bearish: EMA20 < EMA30 < EMA40

M7C valid prospective start remains:

`2026-07-20T14:54:15Z`

Do not reset it.

---

## 5. M8C — STILL RUNNING / NEVER RESET

M8C remains a separate BTC-focused forward shadow:

- CONTROL: accept all future proxy PRIMARY candidates
- CHALLENGER: reject BTCUSD PRIMARY_LONG on proxy branch only
- genuine source anchor remains separate and unsuppressed

Keep M8C, M7C, and genuine source collector running unchanged.

Persistent M8C BAT:

`scripts/mochipoyo_alert_research/m8c/bat/02_run_forward_shadow_forever.bat`

Do not reuse M8C start for a new GOLD shadow.

---

## 6. Corrected genuine source evidence

Old M9B PF 2.234 was timing-invalid and is not promotable.

M9I2 corrected source execution timing by +15 minutes and replaces it.

Corrected genuine source outcomes:

- 42 resolved source trades
- WR 69.05%
- PF 1.5147

Important structural finding:

- direct frozen PRIMARY kernel true at corrected genuine source decision: 40/43
- most source misses were state divergence, not failure of the direct PRIMARY kernel

BTC branch source vs extra historically showed a major asymmetry:

- BTC LONG source strong
- BTC LONG extra very weak

This is why M8C BTC LONG challenger continues unchanged.

---

## 7. M9J / M9K — rejected BTC entry threshold mining

M9J showed source-like BTC LONG RCI entry location increased WR but worsened loss tails/PF.

Do not resume historical BTC entry-RCI threshold mining on the same sample.

M9K found a descriptive BTC LONG failed-reset / overextension tail-risk pattern, especially persistent M5 BULLISH_STACK during adverse movement, but it was not temporally stable enough to freeze as a gate.

Decision remains:

`NO_STABLE_PROSPECTIVE_TAIL_GATE_FREEZE_STOP_HISTORICAL_MINING`

Revisit only with new forward BTC evidence.

---

## 8. M9L / M9M — new multi-year GOLD history changed the direction

Unchanged frozen M7C replay on GOLD 2023-2025 was not profitable enough:

- immediate: 3518 trades, WR 60.20%, PF 0.9251
- first-turn: 3118 trades, WR 60.58%, PF 0.9361

LONG first-turn was above PF1 in every available year but thin:

- 2023 PF 1.0246
- 2024 PF 1.1330
- 2025 PF 1.0357
- 2026 to Jun19 PF 1.3142

SHORT was structurally weak in 2023-2025.

M9M froze three strong-looking 2023-2024 static filters before opening 2025. All failed 2025 holdout. This proved that fixed RCI/ATR-style filters were fragile and that high WR could still hide large loss tails.

Do not describe 2025 as untouched holdout for any later M9N+ hypotheses; it has now been opened/research-exposed.

---

## 9. M9N / M9O / M9P — canonical M15 dynamic LONG core

The best reproducible M15 direction uses relative/rolling features rather than fixed thresholds.

Canonical strict M15 N3:

### N1 — quiet M5 pullback
At first-turn decision, latest fully closed M5 `tick_volume_ratio20` <= rolling 50th percentile of latest 200 fully available ratio observations.

### N2 — strong M15 momentum
At first-turn decision, latest fully closed M15 MACD(6,13) line in bps >= rolling 75th percentile of latest 200 fully closed M15 values.

### N3
`N1 OR N2`

M9P local deterministic reproduction PASS matched reference.

Canonical N3:

- 1495 trades
- about 35.6 raw candidates/month across 42 observed months
- WR 62.27%
- PF 1.3659
- average win +17.20 bps
- average loss -20.87 bps
- max DD 510.5 bps
- max losing streak 11

Yearly PF:

- 2023 1.1453
- 2024 1.3575
- 2025 1.2422
- 2026 to Jun19 1.7568

Robustness:

- 72/72 nearby W/q combinations retained PF>1 in every available calendar year
- all 72 aggregate PF>1 after an additional 2 bps/trade stress

This is reproducible historical robustness, **not independent future validation**.

M9P uploaded package SHA256:

`0699d558fef49fa93e8f26c5514bc6129f5bd7fc8170078ab1523f1a8eb5dd4a`

---

## 10. N6 risk observation

Within canonical N3, H4 RCI9 empirical percentile using latest 100 fully closed H4 bars:

Risk-zone descriptive band:

`> 0.25 and <= 0.50`

Historical risk-zone:

- 282 trades
- PF 0.9087
- average loss -33.59 bps
- <= -100 bps tail rate ~2.84%

Complement:

- PF 1.5469
- DD ~364.9 bps

N6 is **not a validated historical gate**. It is a forward risk hypothesis.

---

## 11. M9Q — loss reduction + profit extension

User explicitly wanted both:

- reduce losses,
- extend winners.

Exploratory historical hypotheses:

### Q1 — N6 half-risk accounting
Keep every N3 signal, but use virtual 0.50x exposure in N6, 1.00x otherwise.

Historical exploratory:

- PF 1.4414
- DD 428.5 bps
- signal count unchanged

### Q2 — selective half-runner
At original M7C exit:

- if latest fully closed H1 MACD(6,13) line is rising vs prior closed H1 bar,
- close 50% at original exit,
- keep 50% runner,
- close runner at first subsequent fully closed M15 RCI9 turn-down at next decision open,
- otherwise close 100% at original exit.

Historical exploratory PF 1.4099.

### Q3 — Q1 + Q2

Historical exploratory:

- PF 1.4703
- DD 418.2 bps
- average positive +17.64 bps
- average negative -17.26 bps
- max losing streak 9

This approximately repaired the mildly loss-larger-than-win profile.

All M9Q history is research-exposed. Q1/Q2/Q3 require fresh prospective testing.

---

## 12. M9R — four-arm M15 fresh prospective design (FROZEN DESIGN, NOT STARTED)

Keep this design. Do not start/backfill silently.

Arms:

- R0: N3 base
- R1: N3 + N6 0.50x risk accounting
- R2: N3 + selective half-runner
- R3: combined

Requirements:

- fresh GOLD-specific prospective start
- never reuse M7C or M8C start
- no historical backfill
- no live order / Discord signal

Current decision after user requested multi-timeframe portfolio work:

**M9R remains available as the M15 branch risk/reward prospective design, but is not started yet. Review the multi-timeframe portfolio structure first.**

---

## 13. M9S — GOLD multi-timeframe portfolio exploration

Formal exploratory result:

`config/mochipoyo_alert_research/m9s_gold_multitimeframe_portfolio_exploratory_result_20260724.json`

User's new strategic direction:

> Because M5/M15/H1/H4 and BTC can provide more signals overall, each branch may be stricter. Prioritize quality per branch and use portfolio breadth for frequency.

### Raw first-turn LONG baselines

- M5: 4708, WR 64.02%, PF 1.0278, DD 2329.8 bps
- M15: 2068, WR 62.48%, PF 1.1171, DD 1107.7 bps
- H1: 586, WR 67.24%, PF 1.3444, DD 1327.8 bps
- H4: 125, WR 68.0%, PF 1.4344, DD 1470.9 bps

Raw SHORT baselines were weak:

- M5 PF 0.9070
- M15 PF 0.8870
- H1 PF 0.7585
- H4 PF 0.7785

Do not force GOLD SHORT.

### S1 — exploratory strict M5 LONG

Definition:

- M5 own adaptive core true: M5 quiet-volume relative condition OR M5 strong-MACD relative condition,
- M15 closed MACD bps >= trailing-100 q75,
- H1 closed MACD bps >= trailing-100 median,
- H1 closed RCI9 >= trailing-100 median.

Exploratory results:

- 1256
- ~29.9 raw candidates/month
- WR 65.45%
- PF 1.3337
- avg win +10.63 bps
- avg loss -15.09 bps
- DD 335.3 bps
- streak 6

Yearly PF:

- 2023 1.0646
- 2024 1.4504
- 2025 1.7264
- 2026 to Jun19 1.1614

Promising but 2023/2026 margins are thin. Must stress nearby definitions before any freeze.

### S2 — canonical M15 N3

Use M9P metrics above. This is the strongest reproducible branch today.

### S3 — exploratory H1 higher-timeframe momentum LONG

Definition:

- latest closed H4 MACD bps >= trailing-100 q75
- latest closed D1 MACD bps >= trailing-100 median

Exploratory:

- 191
- ~4.55 raw candidates/month averaged over 42 months
- WR 71.20%
- PF 1.7802
- avg win +35.14 bps
- avg loss -48.80 bps
- DD 532.3 bps
- streak 4

Yearly PF:

- 2023 2.7167
- 2024 2.2658
- 2025 1.2938
- 2026 to Jun19 2.3703

High priority exploratory branch, not validated.

### S4 — exploratory H4 daily-aligned premium LONG

Definition:

- latest closed D1 RCI9 >= trailing-100 median
- D1 EMA20 > EMA30 > EMA40

Exploratory:

- 70
- ~1.67 raw candidates/month over 42 months
- WR 72.86%
- PF 3.2956
- avg win +77.50 bps
- avg loss -63.12 bps
- DD 281.7 bps
- streak 2

Yearly PF:

- 2023 1.5401 (only 6 trades)
- 2024 2.8991
- 2025 3.1337
- 2026 to Jun19 16.51 (only 9 trades; do NOT treat this PF literally)

This is premium exploratory reference only because samples are small.

---

## 14. Multi-timeframe overlap / portfolio implications

Raw selected LONG candidate sum across M5/M15/H1/H4 is about **71.7/month before dedup**.

This is NOT the expected independent trade count.

Observed overlap:

- M5 S1 vs M15 N3 within +/-15m: 96 / 1256 = 7.64%
- M5 S1 vs M15 N3 within +/-60m: 363 / 1256 = 28.90%
- H1 S3 vs M15 N3 within +/-60m: 37 / 191 = 19.37%
- H1 S3 vs M15 N3 within +/-4h: 107 / 191 = 56.02%
- H4 S4 vs H1 S3 within +/-4h: 12 / 70 = 17.14%
- H4 S4 vs M15 N3 within +/-4h: 34 / 70 = 48.57%

Implication:

- other timeframes genuinely add many new opportunities,
- but some represent the same market move,
- first portfolio design should deduplicate overlapping positions,
- multi-timeframe agreement should be stored as **confidence metadata**, not automatic extra lots/pyramiding.

---

## 15. BTC policy

There is no supplied BTC 2023-2026 historical set comparable to GOLD.

Do not use absence of history as justification to fit BTC from GOLD.

BTC remains separate:

- genuine source collector running,
- M7C proxy running,
- M8C CONTROL/CHALLENGER running,
- known BTC LONG extra/tail-loss problem remains important.

When enough new forward BTC data exists, build BTC-specific multi-timeframe branches separately.

---

## 16. Current formal state files

Always read these after this handoff because they may be newer:

1. `config/mochipoyo_alert_research/current_state_20260723.json`
2. `config/mochipoyo_alert_research/next_action_20260723.json`
3. `config/mochipoyo_alert_research/m9s_gold_multitimeframe_portfolio_exploratory_result_20260724.json`
4. `config/mochipoyo_alert_research/m9o_gold_dynamic_core_robustness_result_20260724.json`
5. `config/mochipoyo_alert_research/m9p_local_reproduction_result_20260724.json`
6. `config/mochipoyo_alert_research/m9q_gold_loss_reduction_profit_extension_exploratory_result_20260724.json`

Also preserve M7C/M8C runtime contracts and starts.

---

## 17. Next stage — M9T

`M9T_MULTI_TIMEFRAME_BRANCH_ROBUSTNESS_AND_PORTFOLIO_DEDUP_DESIGN`

Do next:

1. Parameter-neighborhood stress S1 M5, S3 H1, S4 H4. Do not trust the discovered single W/q definitions.
2. For every branch report:
   - yearly PF,
   - quarterly PF,
   - monthly frequency,
   - WR,
   - PF,
   - avg win/loss,
   - DD,
   - losing streak,
   - large-loss tail,
   - added-cost sensitivity.
3. Reject branches that only look good at one threshold/window.
4. Build explicit cross-timeframe dedup/confidence logic.
5. Estimate actual portfolio candidate frequency after dedup, not raw sum.
6. Keep M15 M9R four-arm risk/reward design available; decide after portfolio design whether runner/risk sizing is M15-only or generalizable.
7. Continue M8C/M7C/source collection unchanged.
8. No user BAT is required yet.

---

## 18. Always-ready next-chat start prompt

Paste this into a new chat if the current conversation ends unexpectedly:

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初に、GitHubの次のファイルを順番どおり必ず読んでください。

1.
docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9S_DONE_M9T_MULTI_TIMEFRAME_PORTFOLIO_NEXT_20260724.md

2.
config/mochipoyo_alert_research/current_state_20260723.json

3.
config/mochipoyo_alert_research/next_action_20260723.json

4.
config/mochipoyo_alert_research/m9s_gold_multitimeframe_portfolio_exploratory_result_20260724.json

5.
config/mochipoyo_alert_research/m9o_gold_dynamic_core_robustness_result_20260724.json

6.
config/mochipoyo_alert_research/m9p_local_reproduction_result_20260724.json

7.
config/mochipoyo_alert_research/m9q_gold_loss_reduction_profit_extension_exploratory_result_20260724.json

現在はaudit-onlyです。
M8C / M7C / genuine source collectorは動作継続中なので、停止・reset・prospective start変更・backfillをしないでください。

ユーザーの最新方針は、M15だけで件数を守るのではなく、GOLD M5/M15/H1/H4と将来BTCを別枝として厳選し、portfolio全体で頻度を確保することです。
同一相場の複数時間足シグナルは単純加算・pyramidingせず、まずdedup/confidence stackingしてください。

M9P M15 N3は決定論的再現PASS。
M9QのN6半リスク＋selective half-runnerは履歴探索結果であり未検証。
M9R四本prospective designは保持しているが未開始。
M9SでM5/H1/H4の有望LONG探索枝が出たが全履歴research-exposedなので未検証。

次はM9T:
MULTI_TIMEFRAME_BRANCH_ROBUSTNESS_AND_PORTFOLIO_DEDUP_DESIGN
から続けてください。

わからないことを憶測で実装しないでください。
ただし、既にこのhandoffに答えが書いてあることを再質問しないでください。
```

---

## 19. Handoff maintenance rule

When M9T or later materially changes:

- current state,
- next action,
- branch definitions,
- prospective starts,
- operator BATs,
- accepted/rejected candidates,
- critical metrics,

update this handoff or create the next dated handoff **before** doing fragile long-running work, so a conversation length limit never loses the research state.
