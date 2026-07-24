# NEXT CHAT HANDOFF — M9V/M9Y RUNNING / M9Z MULTI-TIMEFRAME PAYOFF RESEARCH NEXT

Date: 2026-07-24  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

This is the authoritative restart point for the next chat.

---

## 1. Actual objective

The goal is NOT strict Mochipoyo reproduction for its own sake.

The actual objective is:

- trade where FX/crypto has robust edge,
- useful portfolio-level frequency,
- preferably high win rate but not at the expense of payoff,
- positive reward/risk (損小利大),
- smaller DD and loss tails,
- multi-timeframe and eventually multi-asset breadth,
- audit/research parity before any operational promotion.

The user explicitly wants:

- better entry location,
- avoid entering while a pullback is still unresolved,
- smaller losses without arbitrary tight stops,
- alert/native EXIT treated as a profit-management event rather than mandatory 100% full exit,
- allow winners to continue when higher-timeframe momentum remains favorable,
- maintain enough total frequency by combining multiple timeframes/assets.

---

## 2. Hard safety/research contracts

Everything remains audit-only.

All remain OFF/FALSE:

- Discord send
- MT5 orders
- live ready
- final signal
- real entry gate

Never:

- reset/reinitialize M7C,
- reset/reinitialize M8C,
- rerun M9V BAT00/BAT01,
- rerun M9Y BAT01,
- change any frozen prospective start,
- backfill by moving a start,
- use future bars/features/outcomes in candidate logic,
- silently treat missing MT5 bars during PC downtime as observed forward evidence,
- pyramid M5/M15/H1/H4 simply because multiple branches say LONG,
- transplant GOLD payoff rules into BTC without BTC-specific evidence.

Research time basis remains MT5 server time for market data/forward accounting.

Newest CSV row contract remains CLOSED.

Historical spread is modeled where stated. Commission and swap remain NOT MODELED unless explicitly added later.

---

## 3. Current persistent monitors — KEEP RUNNING

These are currently intended to remain running in parallel:

1. Genuine source Cloudflare collector
2. M7C prospective shadow
3. M8C forward shadow
4. M9V v2 GOLD multi-timeframe breadth shadow
5. M9Y GOLD payoff / 損小利大 shadow

Do not stop any of them merely because historical research continues.

### Immutable starts

- M7C valid prospective start UTC: `2026-07-20T14:54:15Z`
- M9V start MT5 server time: `2026.07.24 11:04:00`
- M9Y start MT5 server time: `2026.07.24 12:45:00`

Never reset/re-freeze/recreate these starts.

---

## 4. M7C / M8C state

M7C frozen proxy remains unchanged:

- PRIMARY_LONG = IDLE AND RCI9 causal turn-up AND EMA20>EMA30>EMA40
- PRIMARY_SHORT = IDLE AND RCI9 causal turn-down AND EMA20<EMA30<EMA40
- LONG_EXIT = ACTIVE_LONG AND RCI9 >= 78.333333333333
- SHORT_EXIT = ACTIVE_SHORT AND RCI9 <= -75
- reentry = NOT_MODELED_OR_SCORED

M8C remains a separate forward comparison:

- CONTROL accepts all future proxy PRIMARY candidates
- CHALLENGER rejects BTCUSD PRIMARY_LONG on the proxy branch only
- genuine source anchor remains separate and unsuppressed

M8C review gates:

- total future proxy PRIMARY >=30
- BTCUSD PRIMARY_LONG >=8
- challenger accepted >=15

M7C/M8C must not be reset while M9Z historical research proceeds.

---

## 5. M9V — GOLD multi-timeframe breadth forward

M9V runtime:

`M9V_RUNTIME_V2_APPEND_SAFE_PREFIX`

Fresh start:

`2026.07.24 11:04:00` MT5 server time

Arms:

- V0 = M15 N3 only
- V1 = M15 + H1
- V2 = M5 + M15 + H1 + H4

One-position dedup is enforced. Later overlapping timeframe candidates are confirmation metadata rather than automatic extra positions.

Review gates:

- operational >=20 accepted arm events
- interim >=60
- H1 S3 branch review needs >=10 H1 candidates
- formal >=120

M9V is a base breadth experiment. Do not retrofit M9X/M9Y payoff rules into it.

---

## 6. M9X — historical payoff-decoupling exact reproduction PASS

Formal result:

`config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json`

One-position addendum:

`config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json`

User-local deterministic reproduction PASS:

- canonical M15 N3 = 1495
- W1 reclaim reference = 1054
- W1 entry-only PF = 1.5875291007284058

### W1 reclaim reference

`W1_RECLAIM_0P10_ATR5_WITHIN_10M`

At canonical M15 N3 first-turn:

1. use latest fully closed M5 Wilder ATR14,
2. reclaim level = original PRIMARY bid/open - 0.10 * ATR5,
3. if first-turn M1 open is already >= level, enter normally,
4. otherwise wait at most 10 fully closed M1 bars,
5. after first M1 close >= level, enter exact next M1 open ask,
6. skip if reclaim does not occur before timeout/native exit.

This is a central reference cell, not a claimed historical optimum.

Neighborhood tested:

- ATR offsets: 0.00 / 0.05 / 0.10 / 0.15 / 0.20
- waits: 5 / 10 / 15 / 20 / 30m
- 25 total combinations
- count range 872–1206
- aggregate PF range 1.5043–1.6576
- +2bps PF range 1.1944–1.3149
- all 25 had PF>1 in every available calendar year
- all still had at least one weak quarter; minimum quarter PF roughly 0.620–0.907

Therefore the concept is broad but not complete/forward validated.

### One-position runner correction

M9X independent scoring found 46 cases where the next W1 candidate arrived while a previous runner was still active.

Prospective runner arms must therefore enforce one-position accounting.

Corrected historical reference:

#### 50% runner + N6

- n = 1008
- PF = 1.66289170174128
- avg win = +17.4043 bps
- avg loss = -15.0786 bps
- payoff ratio ≈ 1.154:1
- DD = 291.53 bps
- +2bps PF = 1.32774

#### 75% runner + N6

- n = 1008
- PF = 1.6483266594682453
- avg win = +18.9514 bps
- avg loss = -15.2679 bps
- payoff ratio ≈ 1.241:1
- DD = 296.28 bps
- +2bps PF = 1.33026

These remain historical/research-exposed references only.

---

## 7. M9Y — fresh payoff shadow RUNNING

M9Y runtime:

`M9Y_RUNTIME_V1_APPEND_SAFE_PREFIX`

Fresh start:

`2026.07.24 12:45:00` MT5 server time

M9Y is independent from M9V start. It reads M9V v2 S2_M15 candidate output READ-ONLY and only allows:

`proxy_primary_time > M9Y prospective_start_server_time`

M9Y does not modify/reset M9V.

Arms:

- Y0 = W1 reclaim + normal 1.0x risk + native exit
- Y1 = W1 reclaim + N6 0.5x risk when flagged + native exit
- Y2 = Y1 + 50% selective runner
- Y3 = Y1 + 75% selective runner

N6 at ACTUAL reclaim entry time:

- latest fully closed H4 RCI9 percentile over trailing100 closed H4 bars
- risk zone >25% and <=50%
- 0.5x size only
- never suppress candidate

Selective runner:

- at native M7C LONG_EXIT, latest fully closed H1 MACD(6,13) line > previous closed H1 MACD line
- runner exit = first M15 decision at or after native exit whose latest fully closed M15 RCI9 turns down
- if native EXIT itself already satisfies turn-down, runner exits immediately with no extension

M9Y first local bootstrap PASS was clean. Initial counts were zero because the first one-shot was ~1 M1 minute after start; that is not a performance result.

Review gates:

- Y0 accepted >=20 operational
- >=60 interim
- N6 flagged actual entries >=10 for risk review
- Y0 accepted >=120 formal

At 20 entries, manually review before blindly collecting to 120.

---

## 8. Forced reboot recovery — IMPORTANT

Windows forced reboot/power loss can leave stale exclusive lock files for:

- collector
- M7C
- M9V
- M9Y

Formal contract:

`config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json`

Recovery BAT:

`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

Use ONLY after an actual forced reboot/power-loss situation, when protected loops are no longer running.

Recovery BAT:

- verifies no protected process is running,
- archives confirmed stale locks,
- removes only stale locks,
- does not change runtime manifests,
- does not change prospective starts,
- does not reset SQLite DB,
- does not reset M8C state.

Restart order after recovery PASS:

1. MT5 / CSV export must be running/updating
2. collector
3. M7C
4. M8C
5. M9V
6. M9Y

Never rerun any initializer after reboot.

If the raw MT5 CSV never restores bars from the PC-off interval, that missing interval is unobserved forward time and must not be silently counted.

---

## 9. How long monitors run

No fixed calendar stop date.

Use review checkpoints:

### M7C

- 5 supported events operational
- 15 interim
- formal >=30 plus per-ticker/direction/exit minimums

### M8C

- total >=30
- BTC LONG >=8
- challenger accepted >=15

### M9V

- 20 / 60 / 120 accepted events
- H1 S3 >=10 for branch review

### M9Y

- Y0 20 / 60 / 120
- N6 flagged entries >=10

At the first operational checkpoint, inspect:

- implementation integrity
- count/frequency
- PF
- WR
- average win / loss
- payoff ratio
- DD
- loss tails
- overlap behavior
- regime/subperiod weakness

A checkpoint is NOT an automatic promotion threshold.

---

## 10. NEXT STAGE — M9Z

Stage:

`M9Z_GOLD_MULTI_TIMEFRAME_PAYOFF_EXTENSION_ASSISTANT_SIDE_AUDIT_ONLY`

M9Z is historical assistant-side research while all forward monitors continue unchanged.

No user BAT is required at the start of M9Z.

### Research order

1. M5
2. H1
3. H4

Do NOT copy M15 W1 `0.10 ATR / 10m` directly into other timeframes and call it valid.

Each timeframe gets its own entry/exit study.

### M9Z-M5 first

Base candidate family:

Use the frozen M9S S1 M5 branch population without redefining the branch first.

Study:

- entry-to-native-M5-exit MAE/MFE
- holding time
- large-loss tails
- winners versus losers path profile
- post-native-exit MFE at causal horizons appropriate to M5
- whether deep unresolved pullback is weaker than reclaim/confirmation entry
- M1-based reclaim normalized to M5 volatility
- small predefined threshold neighborhood, looking for a stable family, not a historical best cell
- M15/H1 momentum/structure as a separate profit-management vector
- transaction-cost sensitivity
- monthly/quarterly/yearly density and PF
- overlap with M15/M9Y candidates

M5 historically had high frequency but thin cost margin, so entry quality and cost robustness are critical.

### M9Z-H1 second

Base candidate family:

Frozen M9S S3 H1 branch.

Study:

- M5/M15 pullback/reclaim for more precise entry
- H1 MAE/MFE and large-loss structure
- native H1 exit versus later continuation
- H4/D1 momentum/structure for selective runner
- positive payoff while preserving enough H1 frequency
- cost/tail/subperiod robustness

H1 previously showed the strongest parameter-neighborhood robustness among non-M15 branches, so it is high priority.

### M9Z-H4 third

Base candidate family:

Frozen M9S S4 H4 branch.

Main risk = very small sample size.

Study conservatively:

- H1/M15 entry refinement
- H4 MAE/MFE
- post-native-exit continuation
- D1 trend/momentum profit management
- very small predefined variant family only
- stability/count more important than headline PF

Never present H4 historical PF as a reliable live expectation because yearly counts are small.

---

## 11. After M9Z branch research

Only branches with broad robustness should enter a new portfolio reconstruction.

Next portfolio questions:

- how many distinct opportunities/month remain after one-position dedup?
- does M5 add genuinely independent timing opportunities after M15/H1?
- does ordered confirmation improve payoff/runner decisions?
- should later higher-timeframe confirmation increase runner fraction, tighten stop, or merely annotate confidence?
- what is the incremental PF/net/DD contribution of each branch?
- what is day/week P&L correlation between branches?
- does portfolio frequency stay useful after removing weak/overlapping entries?

Do not automatically open multiple positions because M5/M15/H1/H4 all align LONG.

Historical M9Z findings must NOT alter M9V or M9Y until:

1. deterministic reproduction passes,
2. a new explicit future prospective contract is frozen,
3. fresh start is independent and no backfill is used.

---

## 12. BTC policy

BTC remains separate.

Current BTC evidence includes genuine-source/M7C/M8C forward collection and the prior warning that BTC LONG extra proxy trades had large tail-loss problems.

Do not transplant GOLD M9X/M9Y/M9Z entry or runner rules into BTC.

BTC-specific multi-timeframe/payoff work requires BTC-specific evidence/data.

---

## 13. User/operator preferences

- Japanese responses.
- Evidence-first and quantified.
- Do not guess implementation details.
- User does not want to run Python manually; user-facing operations should be numbered BAT files.
- Do not ask the user to run a BAT until it is actually needed.
- Current forward timestamps/accounting use MT5 server time, not JST conversion.
- Keep handoff updated whenever material state changes.

---

## 14. Files to read first in the next chat

Read in this exact order:

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_M9Y_RUNNING_M9Z_PAYOFF_RESEARCH_NEXT_20260724.md`
2. `config/mochipoyo_alert_research/current_state_20260723.json`
3. `config/mochipoyo_alert_research/next_action_20260723.json`
4. `config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json`
5. `config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json`
6. `config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json`
7. `config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json`
8. `config/mochipoyo_alert_research/m9y_initial_local_pass_20260724.json`
9. M9S/M9T/M9U files only as needed for frozen M5/H1/H4 branch definitions and historical reference; do not redefine them ad hoc.

---

## 15. Exact next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート研究の続きです。

最初に次を順番どおり必ず読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_M9Y_RUNNING_M9Z_PAYOFF_RESEARCH_NEXT_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json
5. config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json
6. config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json
7. config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json
8. config/mochipoyo_alert_research/m9y_initial_local_pass_20260724.json

現在、genuine source collector / M7C / M8C / M9V / M9Y はfresh forward継続中です。
停止・reset・backfill・initializer再実行は禁止です。

M9V start = 2026.07.24 11:04:00 MT5 server time
M9Y start = 2026.07.24 12:45:00 MT5 server time

強制再起動時だけ専用recovery BATでstale lockを回復し、initializerは再実行しません。

次は M9Z_GOLD_MULTI_TIMEFRAME_PAYOFF_EXTENSION_ASSISTANT_SIDE_AUDIT_ONLY です。
まずGOLD M5の frozen M9S S1 branch を基準に、MAE/MFE、entry location、deep unresolved pullback vs reclaim、native EXIT後の伸び、M15/H1を使う別profit vector、cost/tail/subperiod robustnessを調べてください。

M15の0.10ATR/10分をそのままM5/H1/H4へ移植しないでください。
M5の次はH1、その次はH4です。
historical M9Z結果はM9V/M9Yへretrofitしないでください。

ユーザーに新しいBATを求めるのは、deterministic reproductionまたは新fresh prospective stageで本当に必要になった時だけにしてください。
```
