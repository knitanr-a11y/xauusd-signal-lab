# NEXT CHAT HANDOFF — M9X EXACT PASS / M9Y IMPLEMENTED / FRESH START NEXT

Date: 2026-07-24  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## 1. Current operating state

Keep all existing forward collectors running unchanged:

- M7C unchanged, audit-only.
- M8C running; never reset.
- Genuine source collector running.
- M9V v2 fresh multi-timeframe GOLD forward running.
- M9V immutable start = MT5 server time `2026.07.24 11:04:00`.
- M9V runtime contract = `M9V_RUNTIME_V2_APPEND_SAFE_PREFIX`.
- Never rerun M9V BAT00/BAT01 and never reset/backfill M9V.
- Discord send / MT5 order / live-ready / final signal / real entry gate remain OFF.

## 2. Objective

The final objective is robust multi-timeframe / multi-asset trading edge with useful portfolio frequency and preferably positive reward/risk (損小利大), not merely high win rate.

User explicitly wants:

- entry at more favorable locations,
- avoid blindly buying the deepest unresolved pullback,
- smaller losses without arbitrary tight stops,
- native alert EXIT treated as a profit-management event rather than mandatory 100% full exit,
- allow winners to run when higher-timeframe momentum remains favorable.

## 3. M9X user local deterministic reproduction — EXACT PASS

Formal result:

`config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json`

Uploaded ZIP SHA256:

`bafa3102b2d4d4a1e7e92f23781b1202ce84edb14a1820618fc02bff9be157da`

M9X reproduced exactly:

- canonical N3 = 1495
- W1 reclaim reference = 1054
- W1 entry-only PF = 1.5875291007284058
- historical spread included
- commission NOT modeled
- swap NOT modeled
- research-exposed history, not independent validation

### W1 reclaim reference

`W1_RECLAIM_0P10_ATR5_WITHIN_10M`

At canonical M15 N3 first-turn:

1. latest fully closed M5 Wilder ATR14,
2. reclaim level = original PRIMARY bid/open - 0.10 * ATR5,
3. if first-turn M1 open already >= level, enter normally,
4. otherwise wait at most 10 fully closed M1 bars,
5. after first M1 close >= level, enter exact next M1 open ask,
6. skip if no reclaim by timeout/native exit.

M9X neighborhood test:

- ATR offsets 0.00 / 0.05 / 0.10 / 0.15 / 0.20
- waits 5 / 10 / 15 / 20 / 30m
- 25 combinations
- count range 872–1206
- aggregate PF range 1.5043–1.6576
- +2bps PF range 1.1944–1.3149
- all 25 had PF>1 in every available calendar year
- weak quarters still exist; minimum quarter PF range ~0.620–0.907

Do not claim the historical sample is complete or forward validated.

## 4. Runner overlap operational correction

Formal addendum:

`config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json`

Important discovery:

- among 1054 independent M9X W1 trades, 46 next entries occurred while the previous runner was still open.
- prospective runner arms must therefore enforce one-position accounting.
- later candidates while runner is active are skipped/confirmation metadata, not a new position.

Corrected one-position historical reference:

### 50% runner + N6

- count 1008
- WR 59.03%
- PF 1.66289170174128
- avg win +17.4043 bps
- avg loss -15.0786 bps
- payoff ratio ~1.154:1
- DD 291.53 bps
- +2bps PF 1.32774
- yearly PF 2023 1.424 / 2024 1.496 / 2025 1.420 / 2026-through-0619 2.491

### 75% runner + N6

- count 1008
- WR 57.04%
- PF 1.6483266594682453
- avg win +18.9514 bps
- avg loss -15.2679 bps
- payoff ratio ~1.241:1
- DD 296.28 bps
- +2bps PF 1.33026
- yearly PF 2023 1.479 / 2024 1.466 / 2025 1.367 / 2026-through-0619 2.497

This remains historical/research-exposed evidence only.

## 5. M9Y fresh payoff prospective shadow

Contract:

`config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json`

Implementation self-test:

`config/mochipoyo_alert_research/m9y_implementation_self_test_result_20260724.json`

Status:

`IMPLEMENTED_SELF_TEST_PASS_READY_FOR_ONE_TIME_LOCAL_FRESH_START`

M9Y has NOT been started yet.

### M9Y architecture

M9Y is a separate runtime and does not modify/backfill M9V.

To avoid duplicate M15-N3 implementations and parity drift, M9Y consumes the existing M9V v2 `S2_M15` branch-candidate ledger READ-ONLY.

M9Y eligibility is fail-closed:

`proxy_primary_time > M9Y prospective_start_server_time`

Therefore a first-turn after M9Y start that belongs to a pre-M9Y PRIMARY is forbidden.

M9V start is NOT reused as M9Y start.

M9Y freezes its own new start, raw CSV immutable prefixes, and the SHA256/start of the M9V runtime manifest.

If M9V runtime manifest changes/reset occurs, M9Y blocks.

### M9Y arms

`Y0_W1_NATIVE_EXIT`
- W1 reclaim entry
- 1.0x risk
- native M7C exit

`Y1_W1_N6_NATIVE_EXIT`
- W1 reclaim
- N6 = 0.5x risk, otherwise 1.0x
- native exit

`Y2_W1_N6_RUNNER50`
- W1 reclaim
- N6 sizing
- 50% selective runner

`Y3_W1_N6_RUNNER75`
- W1 reclaim
- N6 sizing
- 75% selective runner

N6:

- at ACTUAL reclaim entry time,
- latest fully closed H4 RCI9 percentile in trailing100 closed H4 bars,
- risk zone >25% and <=50%,
- 0.5x size only,
- never suppress candidate.

Selective runner:

- at native M7C LONG_EXIT, latest fully closed H1 MACD(6,13) line > previous closed H1 MACD line,
- runner exit = first M15 decision at or after native exit whose latest fully closed M15 RCI9 turns down (`current < previous && previous >= previous2`),
- if native EXIT itself is already that turn-down decision, runner exits immediately at same time and gets no extension.

Each M9Y arm has one-position accounting independently. Cross-arm positions are virtual comparisons only.

## 6. M9Y self-tests

Passed:

- M9V S2 read-only feed versus independent M15 N3 recomputation produced exact same candidates/metrics in test window.
- test window S2 = 476, W1 = 348.
- Y0 PF 1.9096771524763991 exact parity.
- Y1 PF 2.050800724761162 exact parity.
- Y2 count331 / PF2.069775123045078 exact parity.
- Y3 count331 / PF2.034581162873279 exact parity.
- fresh-start simulation start `2025.06.03 11:59:00`.
- pre-start PRIMARY candidate count = 0.
- later raw CSV append accepted.
- frozen M5 row tamper => BLOCK.
- M9V runtime manifest tamper => BLOCK.
- one-position runner overlap enforced.

## 7. Current user action — exact order

Keep M8C / M7C / genuine source collector / M9V 03 running.

Pull latest `feature/mochipoyo-alert-research`.

### Step 1

Run exactly once:

`scripts/mochipoyo_alert_research/m9y/bat/01_initialize_fresh_runtime_once.bat`

Expected:

`[M9Y INIT PASS]`

After PASS:

- never rerun M9Y 01,
- never delete/reset M9Y runtime manifest/start receipt.

If BLOCKED, do not delete anything; send full screen output.

### Step 2

After INIT PASS, run once:

`scripts/mochipoyo_alert_research/m9y/bat/02_run_shadow_once.bat`

Expected:

`[M9Y PASS] ...`

Then run:

`scripts/mochipoyo_alert_research/m9y/bat/05_open_latest_results.bat`

Submit:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9Y\LATEST\99_UPLOAD_PACKAGE.zip`

### Step 3 — NOT YET

Do NOT start:

`scripts/mochipoyo_alert_research/m9y/bat/03_run_shadow_forever.bat`

until the initial M9Y ZIP is reviewed by ChatGPT.

## 8. Never do

- do not reset M8C,
- do not change M7C formulas/thresholds,
- do not reset/backfill M9V,
- do not rerun M9V BAT00/BAT01,
- do not reuse M9V start as M9Y start,
- do not admit M9V S2 with PRIMARY <= M9Y start,
- do not rerun M9Y initializer after PASS,
- do not start M9R,
- do not transplant GOLD payoff rules into BTC without BTC-specific evidence,
- do not enable Discord, MT5 orders, live-ready, final signal, or real trading gate.

## 9. Files to read first in next chat

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9X_PASS_M9Y_IMPLEMENTED_FRESH_START_NEXT_20260724.md`
2. `config/mochipoyo_alert_research/current_state_20260723.json`
3. `config/mochipoyo_alert_research/next_action_20260723.json`
4. `config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json`
5. `config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json`
6. `config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json`
7. `config/mochipoyo_alert_research/m9y_implementation_self_test_result_20260724.json`
8. `config/mochipoyo_alert_research/m9v_v2_initial_local_pass_20260724.json`

## 10. Next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初に次を順番どおり必ず読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9X_PASS_M9Y_IMPLEMENTED_FRESH_START_NEXT_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json
5. config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json
6. config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json
7. config/mochipoyo_alert_research/m9y_implementation_self_test_result_20260724.json

M8C / M7C / genuine source collector / M9V v2 fresh forwardは変更・停止・resetしないでください。
M9V startはMT5 server time 2026.07.24 11:04:00でimmutableです。M9V BAT00/01は再実行禁止です。

M9Xはユーザー環境でexact PASS済みです。
runner重複46件を補正しても50%/75% runnerは損小利大方向を維持しました。

M9YはM9V S2をread-only upstreamとして使う別fresh payoff shadowです。M9V startは再利用せず、新しいM9Y startを切ります。
現在はM9Y 01 fresh init → 02 initial one-shot → ZIPレビューの順です。03 persistent loopはinitial ZIPレビューまで開始しないでください。
```
