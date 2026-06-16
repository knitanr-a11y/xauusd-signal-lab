# GOLD V3 Stage176-177 Chat Record: OHLC-only Rebuild and Reproduction Incident

Date: 2026-06-16  
Scope: GOLD V3 audit-only, Stage176C through Stage177  
Repository: `knitanr-a11y/xauusd-signal-lab`

## 0. Non-negotiable constraints

- GOLD V3 remains audit-only.
- GOLD V2 / old GOLD / DISC8 / Stage41 must not be read, used, referenced, or used as fallback.
- CSV latest row is contractually closed. Open/as-of/latest-open interpretation is prohibited.
- Candidate pool must not be silently removed.
- F002 exclusion must not be bypassed.
- Discord notification, MT5 order execution, AI API, live hook, final signal, payload autotrade remain OFF until explicit permission.
- NO_SIGNAL must not notify Discord.
- Historical ledger PF must not be treated as live-deployable unless OHLC-to-feature-to-rule reproduction is proven.

## 1. Root issue identified in this chat

The prior workflow incorrectly treated historical ledger feature columns as if they were already live-reproducible.

The user had required from the beginning that only information available at live entry time be used. The correct implementation path should have been:

1. Start from closed OHLC candles only.
2. Compute all features from OHLC using live-reproducible formulas.
3. Verify historical and live feature parity.
4. Search candidates only on those reproducible features.
5. Backtest with M5 TP/SL judgement.
6. Only then consider live signal plumbing.

Instead, the workflow used existing `107k2` ledger feature columns and result columns for candidate search and performance aggregation before proving that those columns could be reproduced from OHLC. This caused the old/current PF and later candidate PF to be downgraded to reference-only.

This was a process/implementation error in the assistant workflow, not a problem caused by future information.

## 2. Clarification about “entry-available information”

The issue is not that the old feature values required future information.

The issue is:

- The values existed in the historical ledger.
- The original formulas/asof rules/score generation were not fully recovered.
- Therefore the same values could not yet be generated from live closed OHLC.

So the correct distinction is:

- Entry-available information: yes, it should exist at entry time.
- Reproducible feature pipeline: not fully proven.

## 3. Stage176C result

Stage176C replayed later candidates P1-P5 using the best recovered/live-safe formula set from Stage176B:

- `m15_rsi_sma14_shift0`
- `h1_up_ema20_gt_ema50_shift0`
- `h1_range_atr_ewm14_shift0`
- `d1_low_atr_sma50_shift2`

Result:

- Original later union:
  - events: 1008
  - entry_dt: 792
  - sum: 3852.958899
  - PF: 2.147422
  - win rate: 0.518849
  - after_events: 103
  - after_sum: 849.750060
  - after_pf: 4.269224
- Recovered later union:
  - events: 595
  - entry_dt: 528
  - sum: 808.603631
  - PF: 1.377671
  - win rate: 0.430252
  - after_events: 16
  - after_sum: 176.205357
  - after_pf: 5.023445

Candidate-level outcome:

- P1_D1: original PF 2.134; recovered PF 0.625
- P2_DEN: original PF 2.321; recovered PF 1.100
- P3_RSI: original PF 2.907; recovered PF 2.907, exact match
- P4_H1_D1_STRICT: original PF 3.060; recovered PF 2.151
- P5_H1UP_CUR: original PF 1.551; recovered PF 1.477

Interpretation:

- P3_RSI was reproducible.
- P1/P2/P4/P5 were not sufficiently reproduced.
- Later candidate PF could not be treated as live-deployable.

## 4. Stage176D result

Stage176D broadened formula reconstruction and audited both later feature formulas and old/current policy inventory.

Recovered exactly:

- `m15_rsi14 = m15_rsi_sma14_shift0`
  - exact: true
- `h1_up = h1_ema20_gt_ema50_shift0`
  - exact: true
- `h1_range_atr = h1_high_low / h1_atr_sma28 shift0`
  - exact: true

Not recovered exactly:

- `d1_dist_atr`
  - best full candidate: `m15_low_minus_d1_ema20_over_d1_atr_sma28_shift1`
  - MAE: 0.3584482526541423
  - max_abs: 3.5062914674726304
  - corr: 0.961317
  - exact: false

Current policy inventory:

- policy: `density_safe||100||Q0.6`
- rows: 8565
- entry_dt: 881
- score columns found:
  - `feature_score`
  - `score`
  - `ledger_score`
  - `score_threshold`
- current_score_formula_recovered: false

Interpretation:

- Old current policy exists in the ledger.
- Its score/policy formula is not recovered from OHLC.
- Old current best must remain reference-only until score generation is reproduced or replaced.

## 5. Consequence of Stage176C/176D

All old candidate results depending on unrecovered historical feature columns or unrecovered score generation are demoted to reference-only.

This includes:

- Stage172 selected portfolio result.
- Later P1/P2/P4/P5 candidate PF.
- Old current best `density_safe||100||Q0.6` live-readiness.

The only safe route is either:

1. Fully recover all feature and score formulas from OHLC; or
2. Rebuild from OHLC-only features and ignore old PF as deployable evidence.

The current decision in this chat moved to option 2: OHLC-only rebuild.

## 6. Uploaded OHLC data for rebuild

The user uploaded two sets of candle data:

Historical 2025 data:

- `gold#_m1.csv`
- `gold#_m5.csv`
- `gold#_m15.csv`
- `gold#_h1.csv`
- `gold#_h4.csv`
- `gold#_d1.csv`

Live/continuation data:

- `goldsharp_m1.csv`
- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

Live feature snapshot:

- `gold_v3_live_feature_snapshot.csv`

Data usage rule established in this chat:

- Use `gold#_*` for 2025.
- Use `goldsharp_*` for 2026 onward.
- Use pre-2025 `goldsharp_*` only as indicator warm-up for HTF features.
- Do not mix `gold_v3_live_feature_snapshot.csv` into search/backtest.
- Use `gold_v3_live_feature_snapshot.csv` only as parity audit against Python-computed OHLC features.

## 7. Stage177 implementation

Stage177 was created as an OHLC-only rebuild search audit.

Files:

- `scripts/gold_v3_runtime/gold_v3_177_ohlc_only_rebuild_search_audit.py`
- `scripts/gold_v3_runtime/bat/run_gold_v3_177_ohlc_only_rebuild_search_audit.bat`

Commits:

- `56a9870fcd9da89897de895c957f99902600683d`
- `3addb24542852b3c2de522a5e63bb172a13833e7`
- `64c118b05d5906fef951cabf447967421650c2d7`

Stage177 design:

- Build features from OHLC only.
- Use M15 as entry time frame.
- Use H1/H4/D1 closed/asof features.
- Use M5 for TP/SL outcome judgement.
- Split:
  - train: 2025
  - test: 2026 onward
  - full: 2025 onward
- Old PF benchmark: 2.237.
- Search long/short profiles with several TP/SL/horizon settings.
- Output TOP rules and month stability data.
- Use `gold_v3_live_feature_snapshot.csv` only for `LIVE_SNAPSHOT_PARITY`.

## 8. Stage177 runtime errors and fixes

Two runtime issues occurred while adding snapshot parity.

### 8.1 First snapshot parity error

Error:

- `row.dt` was interpreted as pandas `.dt` accessor, not the `dt` column value.
- This caused an AttributeError in snapshot parity before the search body started.

Fix:

- Replace `row.dt` with `row['dt']`.

### 8.2 Additional robustness fix

The code was also corrected to:

- Avoid `errors='ignore'` FutureWarning.
- Make snapshot parity non-blocking.
- If snapshot parity raises an exception, write a non-blocking row and continue OHLC-only search.

Latest relevant commit:

- `64c118b05d5906fef951cabf447967421650c2d7`

Current expected behavior:

- Stage177 should no longer stop at snapshot parity.
- If snapshot parity fails, it should continue into candidate search.

## 9. Stage177 output expected next

The user will run:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_177_ohlc_only_rebuild_search_audit.bat
```

Expected output:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\177\paste_me.txt
```

The next chat should read the Stage177 paste and inspect:

- `status`
- `ready`
- `decision`
- `LIVE_SNAPSHOT_PARITY`
- `TOP30_RULES`
- `best_full_pf`
- `best_rule`
- `old_pf_benchmark`
- `train_pf`
- `test_pf`
- `full_pf`
- `full_n`
- `full_neg_months`
- `beats_old_pf_2_237`

## 10. How to evaluate Stage177 output

Do not accept a candidate just because full PF is high.

Required checks:

- test PF must not collapse.
- train/test gap must be reasonable.
- full trade count must not be too small.
- monthly negative count must be acceptable.
- snapshot parity must be inspected but must not be mixed into backtest/search.
- spread/slippage/cost must be audited in a later stage.
- no live payload or autotrade until further gates pass.

If Stage177 finds candidates above old PF 2.237:

- Treat them as OHLC-only candidate candidates, not deployable signals.
- Proceed to Stage178: cost/spread/slippage/monthly/robustness audit.

If Stage177 does not find candidates above old PF 2.237:

- Extend OHLC-only feature/rule search.
- Do not return to old ledger-dependent PF as deployable proof.

## 11. Required communication style for continuation

The continuation should include progress markers such as:

```text
進行度: Stage177結果確認中
進行度: TOP30評価中
進行度: Stage178設計中
```

This is a workflow requirement to make progress visible. It should not include emotional labels or statements about the user.

## 12. Current status at handoff

Current status:

```text
GOLD_V3_STAGE177_OHLC_ONLY_REBUILD_SEARCH_READY_FOR_LOCAL_RUN_AUDIT_ONLY
```

Meaning:

- Stage176C/176D exposed that old ledger candidates are not fully live-reproducible.
- Stage177 was created to rebuild candidate search from OHLC-only data.
- Stage177 code has been patched for snapshot parity errors.
- User is expected to paste Stage177 `paste_me.txt` in the next chat.

## 13. Next chat start prompt

Use this prompt in the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

Read this handoff first:
docs/gold_v3/GOLD_V3_STAGE176_177_CHAT_RECORD_OHLC_ONLY_REBUILD_AND_REPRODUCTION_INCIDENT_20260616.md

GOLD V3 remains audit-only.
Do not read/use/fallback to GOLD V2 / old GOLD / DISC8 / Stage41.
CSV latest row is closed. Open/as-of/latest-open is prohibited.
No Discord, MT5 order, AI API, live hook, final signal, payload, or autotrade.
NO_SIGNAL must not notify Discord.

We are continuing after Stage176C/176D found that old ledger PF and old current best are not fully live-reproducible.
Stage177 OHLC-only rebuild search was created and patched.
I will paste Stage177 paste_me.txt next.

Please evaluate Stage177 results, especially LIVE_SNAPSHOT_PARITY and TOP30_RULES, and decide whether Stage178 cost/spread/slippage/monthly robustness audit should be created or whether Stage177 search must be expanded.
```
