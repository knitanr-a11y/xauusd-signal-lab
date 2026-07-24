# NEXT CHAT HANDOFF — MOCHIPOYO ALERT RESEARCH — M9T DONE / M9U NEXT

Date: 2026-07-24

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

This is the current restart point if the conversation reaches its length limit.

---

## 1. User objective

The goal is not exact Mochipoyo reproduction.

The goal is a robust multi-timeframe / multi-asset trading portfolio with:

- high win rate where possible,
- PF materially above 1 after realistic costs,
- useful portfolio-level frequency,
- lower DD and smaller loss tails,
- better reward/risk,
- GOLD M5/M15/H1/H4 and later BTC as separate branches,
- strict branches are allowed because frequency can come from portfolio breadth.

Do not protect M15 trade count at the cost of weak trades.

---

## 2. Absolute contracts

Project remains audit-only.

Keep false/off:

- `discord_send=false`
- `mt5_order=false`
- `live_ready=false`
- `final_signal=false`
- `entry_gate_enabled=false`

Never:

- use future bars/outcomes in candidate construction,
- use open/unconfirmed OHLC where closed bars are required,
- change M7C formulas/thresholds silently,
- reset M7C runtime manifest,
- stop/reset M8C,
- reset/reuse M8C prospective start,
- backfill a new prospective shadow,
- claim commission/swap are modeled,
- claim historical proxy events are genuine Mochipoyo source truth,
- transplant GOLD rules into BTC,
- sum multi-timeframe signals as independent trades without dedup,
- pyramid overlapping M5/M15/H1/H4 signals by default.

Trading/research time basis = MT5 server time.

---

## 3. User operating preferences

- User does not run Python directly.
- Use numbered BATs only when a local run is genuinely needed.
- Do not ask for BAT execution for each exploratory iteration.
- Assistant-side exploration on uploaded history is preferred.
- Exact filenames/rules/metrics/commits matter; do not guess.
- Maintain a current handoff before long/fragile work.

Local repo root:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\xauusd-signal-lab-clean\xauusd-signal-lab`

GOLD history folder:

`MT5 Files\gold_v3_2023_2026\`

Files: M1/M5/M15/H1/H4/D1, period 2023-01-03 through 2026-06-19.

No comparable BTC 2023-2026 history has been supplied.

---

## 4. M7C frozen source-proxy kernel — DO NOT CHANGE

M15:

- PRIMARY_LONG: `IDLE AND rci9_turn_up AND BULLISH_STACK`
- PRIMARY_SHORT: `IDLE AND rci9_turn_down AND BEARISH_STACK`
- LONG_EXIT: `ACTIVE_LONG AND rci9 >= 78.333333333333`
- SHORT_EXIT: `ACTIVE_SHORT AND rci9 <= -75`
- REENTRY: `NOT_MODELED_OR_SCORED`

RCI turn:

- up: current > previous AND previous <= previous2
- down: current < previous AND previous >= previous2

EMA bullish = EMA20 > EMA30 > EMA40.

M7C prospective start remains:

`2026-07-20T14:54:15Z`

Do not reset it.

---

## 5. M8C — STILL RUNNING / NEVER RESET

M8C remains separate BTC forward evidence:

- CONTROL accepts all future proxy PRIMARY
- CHALLENGER rejects BTCUSD PRIMARY_LONG on proxy branch only
- genuine source anchor remains separate/unsuppressed

Keep M8C, M7C and collector running unchanged.

Persistent M8C BAT:

`scripts/mochipoyo_alert_research/m8c/bat/02_run_forward_shadow_forever.bat`

Do not reuse M8C start for GOLD.

---

## 6. Corrected genuine source / BTC state

Old M9B PF2.234 is timing-invalid and non-promotable.

M9I2 corrected source:

- 42 resolved genuine source trades
- WR ~69.05%
- PF ~1.5147
- direct frozen PRIMARY kernel true 40/43
- most misses were state divergence

BTC LONG source vs proxy extra historically showed strong asymmetry; M8C BTC LONG rejection challenger therefore remains.

M9J entry-RCI mining failed.
M9K BTC LONG tail-state pattern was descriptive but not stable enough for historical promotion.

Do not restart historical BTC threshold mining; wait for new forward evidence.

---

## 7. Multi-year GOLD baseline changed research direction

Frozen M7C replay 2023-2025 was weak overall.

LONG first-turn was PF>1 each year but thin.
SHORT was structurally weak 2023-2025.

M9M froze three strong-looking 2023-2024 static filters before opening 2025; all failed 2025 holdout.

2025 is now research-exposed and must never be described as untouched for M9N+ hypotheses.

This shifted research from fixed RCI/ATR thresholds toward rolling/relative market-state features.

---

## 8. M9P canonical M15 N3 — deterministic local PASS

N1 = quiet M5 pullback:

latest fully closed M5 `tick_volume_ratio20` <= rolling q50 of latest 200 full observations.

N2 = strong M15 momentum:

latest fully closed M15 MACD(6,13) line bps >= rolling q75 of latest 200 closed M15 values.

N3 = `N1 OR N2`.

M9P deterministic local reproduction PASS:

- 1495 trades
- ~35.6/month over 42 months
- WR 62.27%
- PF 1.3659
- avg win +17.20 bps
- avg loss -20.87 bps
- DD 510.5 bps
- streak 11

Year PF:

- 2023 1.1453
- 2024 1.3575
- 2025 1.2422
- 2026-to-Jun19 1.7568

Robustness: 72/72 nearby W/q combinations retained PF>1 in every available year and aggregate PF>1 after extra 2bps/trade stress.

M9P uploaded package SHA256:

`0699d558fef49fa93e8f26c5514bc6129f5bd7fc8170078ab1523f1a8eb5dd4a`

---

## 9. M9Q / M9R — M15 loss reduction + profit extension

N6 descriptive risk zone inside N3:

H4 RCI9 percentile >0.25 and <=0.50 using latest 100 fully closed H4 bars.

N6 historical:

- 282
- PF 0.9087
- avg loss -33.59 bps
- <=-100bps tail ~2.84%

N6 complement PF ~1.5469.

N6 is not a validated gate.

M9Q exploratory overlays:

Q1: all N3 signals retained; N6 virtual size 0.50x, others 1.00x.

- exploratory PF 1.4414
- DD 428.5 bps

Q2: at original M7C exit, if latest fully closed H1 MACD line is rising, close 50%, run 50% until first subsequent fully closed M15 RCI9 turn-down; otherwise close all.

- exploratory PF 1.4099

Q3 = Q1 + Q2:

- PF 1.4703
- DD 418.2 bps
- avg positive +17.64 bps
- avg negative -17.26 bps
- streak 9

All historical periods are exposed. No promotion.

M9R four-arm fresh prospective design remains frozen but NOT started:

- R0 N3 base
- R1 N6 half-risk
- R2 selective half-runner
- R3 combined

Fresh GOLD start required; no M7C/M8C start reuse/backfill.

Keep M9R available as the M15 branch risk/reward layer until portfolio accounting is deterministic.

---

## 10. M9S raw multi-timeframe branch exploration

Formal result:

`config/mochipoyo_alert_research/m9s_gold_multitimeframe_portfolio_exploratory_result_20260724.json`

Raw LONG first-turn baselines:

- M5: 4708, PF 1.0278
- M15: 2068, PF 1.1171
- H1: 586, PF 1.3444
- H4: 125, PF 1.4344

Raw SHORT PF was below 1 on M5/M15/H1/H4. Do not force GOLD SHORT.

Exploratory selected branches:

S1 M5 strict multi-timeframe LONG:

- own M5 relative core
- M15 MACD >= trailing100 q75
- H1 MACD >= trailing100 median
- H1 RCI9 >= trailing100 median

Canonical S1:

- 1256
- ~29.9/month
- WR 65.45%
- PF 1.3337
- DD 335.3 bps

S2 = canonical M15 N3 above.

S3 H1 higher-timeframe momentum LONG:

- closed H4 MACD bps >= trailing100 q75
- closed D1 MACD bps >= trailing100 median

Canonical:

- 191
- ~4.55/month
- WR 71.20%
- PF 1.7802
- DD 532.3 bps

S4 H4 premium:

- closed D1 RCI9 >= trailing100 median
- D1 EMA20 > EMA30 > EMA40

Canonical:

- 70
- ~1.67/month
- WR 72.86%
- PF 3.2956
- DD 281.7 bps

S4 sample is very small; do not treat PF literally.

---

## 11. M9T — branch robustness result (DONE)

Formal result:

`config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json`

### S1 M5

Stress 729 nearby combinations.

- 729/729 aggregate PF>1
- 408/729 PF>1 in every calendar year
- only 4/729 aggregate PF>1 after extra 2bps/trade
- canonical extra-2bps PF ~0.9568

Decision:

`AUXILIARY_ONLY_COST_SENSITIVE_NOT_READY_AS_PRIMARY_BRANCH`

Do not use M5 frequency as an excuse for weak/cost-sensitive trades.

### S2 M15

M9O/P remains strongest reproducible branch:

- 72/72 nearby definitions all-year PF>1
- 72/72 aggregate survives extra 2bps

Decision: primary reproducible research core, not live.

### S3 H1

Stress 81 nearby combinations:

H4 W80/100/120 x H4 MACD q70/q75/q80 x D1 W80/100/120 x D1 MACD q45/q50/q55.

Result:

- 81/81 PF>1 in every available calendar year
- 81/81 aggregate PF>1 after extra 2bps
- aggregate PF range ~1.57 to 2.63
- extra-2bps PF range ~1.43 to 2.34
- minimum calendar-year PF across grid ~1.09

Decision:

`HIGHEST_PRIORITY_NEW_MULTI_TIMEFRAME_BRANCH_FOR_DETERMINISTIC_REPRODUCTION_AND_FRESH_PROSPECTIVE_TEST`

### S4 H4

Stress 9 nearby D1 W/q definitions:

- 9/9 aggregate survives extra 2bps
- only 4/9 PF>1 in every calendar year

Decision:

`PREMIUM_REFERENCE_ONLY_SMALL_SAMPLE_AND_2023_SENSITIVITY`

---

## 12. Regime diversification

Weak quarters are mostly different by branch:

- S1 weak: 2023Q2 PF0.731, 2024Q1 PF0.960
- S2 weak: 2024Q4 PF0.976, 2025Q3 PF0.798
- S3 weak: 2025Q4 PF0.702
- S4 weak: 2024Q4 only one losing trade

Monthly branch net-return correlations were low:

- M5/M15 -0.073
- M5/H1 0.055
- M5/H4 0.318
- M15/H1 0.154
- M15/H4 0.215
- H1/H4 0.196

This supports diversification across timeframes, not just frequency expansion.

---

## 13. Dedup frequency

Raw branch sum is ~71.7 candidate events/month and is NOT independent trades.

Fixed-window descriptive clustering:

- 15m: ~68.7 clusters/month; ~4.2% multi-branch
- 60m: ~58.1/month; ~14.7% multi-branch
- 120m: ~47.3/month; ~26.3% multi-branch
- 240m: ~35.7/month; ~40.8% multi-branch

Cluster composition uses later events and is descriptive only; do not use it as a first-event entry filter.

---

## 14. Causal one-position GOLD portfolio reference

First causal portfolio accounting reference:

- LONG only
- sort S1/S2/S3/S4 chronologically
- while flat, first qualifying branch opens one virtual position using that branch's own first-turn entry and own frozen proxy exit
- while position active, later LONG branch events do not open another position; they are metadata/confirmation only
- simultaneous timestamps priority H4 > H1 > M15 > M5
- no future event used to decide initial entry

Historical exposed result:

- 2241 accepted trades
- ~53.36 trades/month
- median monthly count 53
- monthly range 27-75
- WR 63.23%
- PF 1.4447
- net 7515.3 bps
- avg win +17.23 bps
- avg loss -20.54 bps
- DD 535.4 bps
- streak 8
- <=-100bps tail ~1.16%

Year PF:

- 2023 1.3191
- 2024 1.5245
- 2025 1.3616
- 2026-to-Jun19 1.5965

13/14 quarters PF>1.

Remaining weak quarter:

- 2025Q3: 175 trades, WR59.43%, PF~0.804, net about -317.8bps

Extra-cost stress:

- +0.5bps PF 1.3691
- +1.0bps PF 1.2967
- +1.5bps PF 1.2276
- +2.0bps PF 1.1617
- +2.5bps PF 1.0992
- +3.0bps PF 1.0400

Accepted contribution:

- M15 S2: 1104
- M5 S1: 952
- H1 S3: 139
- H4 S4: 46

This is promising but research-exposed and not live.

---

## 15. Multi-timeframe agreement is NOT a generic positive score

M9T checked only causal prior confirmations.

Examples:

- M15 target with prior M5 <=60m: n198, PF~1.84
- M15 target with prior H1 <=60m: n21, PF~3.09
- H1 target with prior M5 <=4h: n40, PF~4.21
- H1 target with prior M15 <=4h: n59, PF~0.90
- H4 target with prior M15 <=60m: n12, PF~8.16 (tiny sample)
- M5 target with prior H1 <=4h: n58, PF~2.32
- M5 target with prior H4 <=4h: n23, PF~0.65

Therefore:

- do not say "more timeframes agree = always better",
- order/sequence matters,
- likely reflects market phase: e.g. H1 appearing after a prior M15 signal may be later/more mature than an H1 signal preceded by M5 structure,
- store ordered branch sequence as causal metadata first,
- no historical generic confidence threshold promotion.

---

## 16. BTC policy

No comparable multi-year BTC history is currently available.

BTC stays separate:

- genuine source collector running
- M7C running
- M8C control/challenger running
- known BTC LONG extra tail-loss issue remains

Do not transplant GOLD M5/M15/H1/H4 branch rules into BTC.

When enough new BTC forward data exists, create BTC-specific branches.

---

## 17. Current state files

Read these after this handoff because they may be newer:

1. `config/mochipoyo_alert_research/current_state_20260723.json`
2. `config/mochipoyo_alert_research/next_action_20260723.json`
3. `config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json`
4. `config/mochipoyo_alert_research/m9s_gold_multitimeframe_portfolio_exploratory_result_20260724.json`
5. `config/mochipoyo_alert_research/m9o_gold_dynamic_core_robustness_result_20260724.json`
6. `config/mochipoyo_alert_research/m9p_local_reproduction_result_20260724.json`
7. `config/mochipoyo_alert_research/m9q_gold_loss_reduction_profit_extension_exploratory_result_20260724.json`

Preserve all M7C/M8C starts/contracts.

---

## 18. Next stage — M9U

`M9U_MULTI_TIMEFRAME_PORTFOLIO_DETERMINISTIC_REPRODUCTION_AND_PROSPECTIVE_DESIGN`

Do next:

1. Build one deterministic repository implementation for S1 M5, S2 M15 N3, S3 H1, S4 H4.
2. Closed bars only; exact first-turn execution; historical spread treatment identical to research references.
3. Self-verify exact branch counts/metrics against M9T.
4. Reproduce the causal one-position portfolio exactly.
5. Output branch contributions, monthly/quarter/year PF, DD, streak, tails and extra-cost stress.
6. Preserve ordered confirmation sequence metadata.
7. Do not use generic agreement count as a confidence score.
8. H1 S3 is highest-priority new branch for future fresh prospective evidence.
9. M5 S1 remains auxiliary/cost-sensitive.
10. H4 S4 remains premium/reference because of small sample.
11. Keep M9R M15 risk/reward design separate until M9U accounting is deterministic.
12. After self-verification, design a NEW GOLD prospective portfolio shadow with a fresh start; no backfill and no M7C/M8C start reuse.
13. Continue BTC source/M7C/M8C collection unchanged.
14. No user BAT is required yet.

---

## 19. Always-ready next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初にGitHubの次を順番どおり必ず読んでください。

1.
docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9T_DONE_M9U_DETERMINISTIC_PORTFOLIO_NEXT_20260724.md

2.
config/mochipoyo_alert_research/current_state_20260723.json

3.
config/mochipoyo_alert_research/next_action_20260723.json

4.
config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json

5.
config/mochipoyo_alert_research/m9s_gold_multitimeframe_portfolio_exploratory_result_20260724.json

6.
config/mochipoyo_alert_research/m9p_local_reproduction_result_20260724.json

7.
config/mochipoyo_alert_research/m9q_gold_loss_reduction_profit_extension_exploratory_result_20260724.json

現在audit-onlyです。
M8C / M7C / genuine source collectorは継続中です。停止・reset・prospective start変更・backfillは禁止です。

最新方針は、GOLD M5/M15/H1/H4を別枝として厳選し、portfolio全体で頻度を確保することです。
同一相場の複数時間足LONGはpyramidingせず、まず1ポジションdedupとordered confirmation metadataを使います。

M9TではH1 S3が81/81近傍条件で全4年PF>1かつ追加2bps耐性を持ち、最高優先の新枝になりました。
M5 S1は件数は多いがコスト感度が高いので補助扱いです。
M15 N3は決定論的再現済みの主軸です。
H4 S4はpremium小標本です。

因果的1ポジションportfolioの履歴参考は2241件、約53.36件/月、WR63.23%、PF1.4447、DD535.4bps、全4年PF>1、追加2bpsでPF1.1617でした。ただし2025Q3 PF0.804が残ります。

単純な「複数時間足一致数=高confidence」は禁止です。時間足の順序で成績が逆転したため、ordered causal sequenceとして扱ってください。

M9RのN6半リスク＋selective half-runner四本比較設計はM15枝用として保持中ですが未開始です。

次はM9U:
MULTI_TIMEFRAME_PORTFOLIO_DETERMINISTIC_REPRODUCTION_AND_PROSPECTIVE_DESIGN
から続けてください。

ユーザーはPythonを直接実行しません。探索ごとにBATを要求せず、重要な決定論的/forward checkpointだけ番号付きBATにしてください。
わからないことを憶測で実装しないでください。ただしhandoffに答えがあることを再質問しないでください。
```

---

## 20. Handoff maintenance rule

If M9U or later materially changes state, branch definitions, prospective starts, operator BATs, accepted/rejected candidates, critical metrics or next action, update/create the next dated handoff before fragile long-running work.
