# MOCHIPOYO Alert Research — COMPLETE NEXT CHAT HANDOFF

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

Date: 2026-07-28

## 1. Read these files first, in this order

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_COMPLETE_M10W24B_NEITHER_CORRECTION_READY_20260728.md`
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/objective_coverage_plus_value_add_20260722.json`
5. `docs/mochipoyo_alert_research/SCOPE_CLARIFICATION_M10_GOLD_ONLY_M7C_DUAL_SOURCE_BACKGROUND_20260727.md`
6. `config/mochipoyo_alert_research/m10w24b_neither_cohort_scope_correction_contract_20260728.json`
7. `config/mochipoyo_alert_research/m10w23_high_atr_bullish_microstructure_entry_preregistration_20260728.json`
8. `config/mochipoyo_alert_research/m10w24_user_local_broader_cohort_result_scope_mismatch_20260728.json`
9. `config/mochipoyo_alert_research/m10w19_user_local_initial_fresh_start_result_20260728.json`
10. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

Only inspect additional files when needed to execute the frozen next action. Do not wander into unrelated repo projects or silently mix in BTC candidate research.

## 2. Current formal state

`M10W24_SCOPE_MISMATCH_DIAGNOSED_M10W24B_NEITHER_CORRECTION_READY_AUDIT_ONLY`

Next stage:
`M10W24B_NEITHER_COHORT_SCOPE_CORRECTION_AUDIT_ONLY`

Current next action:
- keep all existing monitors unchanged
- keep M10W19 BAT03 running unchanged
- fetch/pull latest `feature/mochipoyo-alert-research`
- run only M10W24B
- upload the resulting `99_UPLOAD_PACKAGE.zip`

Operator:
`scripts/mochipoyo_alert_research/m10w24b/bat/01_run_neither_cohort_scope_correction.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W24B/LATEST/99_UPLOAD_PACKAGE.zip`

## 3. Scope

Active new M10 candidate / expectancy / value research is **GOLD / XAUUSD only**.

Do not silently broaden M10 research to BTCUSD.

M7C is a separate frozen source-fidelity background track and remains dual-symbol BTCUSD + XAUUSD. Do not remove BTC from M7C and do not feed M7C BTC observations into GOLD M10 candidate discovery, thresholds, or portfolio research.

## 4. User objective

Exact Mochipoyo cloning is not the final goal.

Primary priority:
`DO_NOT_MISS_SUPPORTED_MOCHIPOYO_SOURCE_ALERTS`

Additional independent proxy alerts are allowed.

Preferred value-add:
keep useful extra alerts while removing or suppressing losing extra alerts.

Do not suppress matched source alerts by default.

Keep categories separated:
- SOURCE_MATCHED
- MISSED_SOURCE
- EXTRA_CANDIDATE
- EXTRA_ACCEPTED
- EXTRA_REJECTED

Do not tune an extra-signal gate on the same forward sample used to claim its performance.

## 5. Global safety / invariants

Everything remains audit-only.

Forbidden unless explicitly changed by a future formal contract:
- Discord send
- MT5 orders
- live_ready
- final_signal
- automatic live promotion
- historical backfill into forward
- future leakage
- nearest-M1 fallback
- prospective start reset
- runtime reset
- threshold rescue after outcomes
- silently modifying any running monitor

Time basis is MT5 server time.
Newest CSV row is contractually CLOSED.
Exact M1 entry/exit is required where specified.
PC-off raw CSV gaps remain unobserved and are never backfilled from future information.

## 6. Running / preserved monitors

Keep unchanged:
- collector
- M7C
- M8C
- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19

Immutable starts currently recorded:
- M7C UTC: `2026-07-20T14:54:15Z`
- M9V MT5: `2026.07.24 11:04:00`
- M9Y MT5: `2026.07.24 12:45:00`
- M10B MT5: `2026.07.24 20:54:00`
- M10E MT5: `2026.07.24 22:06:00`
- M10P MT5: `2026.07.24 23:56:00`
- M10P2 MT5: `2026.07.27 01:39:00`
- M10W19 MT5: `2026.07.28 02:31:00`

Never change these starts.

## 7. Forced-reboot recovery rule

Recovery operator:
`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

It archives/removes stale loop locks only after verifying loops are not running. It does not reset runtime manifests, starts, SQLite, or forward history.

After M10W19 INIT PASS, never rerun M10W19 BAT01. Restart M10W19 with BAT03 only.

M10P BAT01: permanently forbidden.
M10P2 BAT01: permanently forbidden.
M10W19 BAT01: permanently forbidden after its frozen start.

## 8. SHORT line — M10P / M10P2 / M10V

M10P:
- SHORT family: C056 + G013
- immutable start: `2026.07.24 23:56:00`
- 240-minute horizon

M10P2:
- SHORT family: C0212
- immutable start: `2026.07.27 01:39:00`
- 240-minute horizon

M10W13 historical waiting-time calibration concluded:
- detectors are not dead
- then-current zero runs were not unusually long
- no threshold change was justified
- no further historical threshold drilldown was recommended
- policy: `STOP_HISTORICAL_RESCUE_RESEARCH_AND_WAIT_FOR_PREDECLARED_FRESH_GATES`

Do not resume near-miss / threshold rescue for M10P or M10P2.

M10V is preregistered but **must not execute** until:
- M10P >= 20 resolved
- M10P2 >= 20 resolved
- both integrity checks PASS
- starts and thresholds unchanged

Common direct-comparison window begins at later start `2026.07.27 01:39:00`.
Same-timestamp same-direction events become one SHORT position with dual attribution, no double sizing/PnL.

## 9. BLC1 loss-reduction line — M10W17 / M10W18 / M10W19

M10W17 used M10W14 `coverage_class=NEITHER` exact regime buckets only.
It found two stable LONG directional-opportunity buckets.

Important HIGH-ATR bullish bucket:
`D1_BULLISH | H4_POSITIVE | H1_MACD_POSITIVE | ATR_HIGH_GE_0P67`
LONG opportunity metrics:
- 2023-24: n249, PF 1.2229806473, net +694.1569 bps
- 2025: n207, PF 1.3841527763, net +1017.6094 bps
- 2026: n34, PF 2.2809144068, net +611.5246 bps
- all: n490, PF 1.3723542165, net +2323.2909 bps
- fixed-$0.20 PF 1.3703415800
- +2bps PF 1.2004017818

This is directional opportunity, not an entry signal.

BLC1 itself had been weak/inconsistent, especially in 2026. M10W18 tested one post-hoc loss-reduction gate only:
`h1_atr_pct100 < 0.67`

Exact one-position historical resimulation:
Baseline BLC1 all:
- n965
- PF 1.1901848843
- net +2536.6885 bps
- +2bps PF 1.0423429240
- DD 862.5706 bps

Filtered BLC1 all:
- n682
- PF 1.3591452834
- net +3009.3595 bps
- fixed-$0.20 PF 1.3512883467
- +2bps PF 1.1811482340
- +2bps net +1645.3595 bps
- DD 631.5769 bps

2026 improved from PF 1.0113371406 to 1.8047536670 and DD from 862.5706 to 183.5214 bps.

The excluded HIGH/unavailable arm was poor:
- all PF 0.9298526718
- 2025 PF 0.8554305734
- 2026 PF 0.5167612640

Filtering also freed capacity: 52 newly accepted later low/mid-ATR BLC1 candidates; 49 resolved, PF 1.6692983506, net +368.4263 bps.

But this filter was proposed after inspecting BLC1 outcomes, so M10W18 is not clean validation and cannot be adopted historically.

M10W19 is the clean fresh two-arm test:
- W0 = exact BLC1 baseline
- W1 = exact BLC1 + `h1_atr_pct100 < 0.67`
- immutable fresh start: `2026.07.28 02:31:00`
- review gates by W1 filtered resolved: 20 / 60 / 120
- no automatic promotion
- initial package was clean zero baseline, not performance evidence
- BAT01 may never be rerun
- BAT03 only for continuation/restart

Do not change BLC1, ATR gate, start, 240-minute horizon, or review thresholds from M10W19 outcomes.

## 10. M10W20 / M10W21 — simple HIGH-ATR bullish entries failed

Three preregistered entries were tested inside a broader bullish/high-ATR regime:
- HBR1: M15 1-hour price breakout
- HER1: M15 EMA20 reclaim
- HRC1: M15 RCI9 oversold turn

Result:
- HBR1 REJECT
- HER1 REJECT; train/2025 positive but 2026 PF ~0.742
- HRC1 INSUFFICIENT_DENSITY; validation/cost fragile

Do not tune variants of these failed triggers.

## 11. M10W22 — new causal-information availability

M10W22 was outcome-blind.
It did not read trade outcomes, future returns, PF/PnL, or profit ranking.

It showed that lower-timeframe information is available and variable:
- M5 tick-volume ratio
- M5 body ratio
- M5 close location
- M5 lower/upper wick ratios
- M5 3-bar return/range
- M1 5-bar return/range
- M1 up-close count
- M1 close location
- spread state

`real_volume` is unusable: M1 and M5 nonzero fraction = 0.

Important later-discovered issue:
M10W22 rebuilt the bullish/high-ATR regime but omitted the parent M10W14 `coverage_class=NEITHER` join/filter. Its 8648 rows are therefore a broader cohort than the original M10W17 blind-spot bucket.

## 12. M10W23 — formulas frozen outcome-blind

These three families were frozen before M10W24 outcome evaluation:

MVI1 — M5 volume impulse:
- `m5_tick_volume_ratio20 >= 1.0`
- `m5_body_ratio >= 0.50`
- `m5_close_location >= 2/3`

MWR1 — M5 pullback rejection:
- `m5_ret3_bps <= 0.0`
- `m5_lower_wick_ratio >= 0.40`
- `m5_close_location >= 0.60`

MMO1 — M1 micro momentum:
- `m1_ret5_bps > 0.0`
- `m1_up_close_count5 >= 3`
- `m1_close_location >= 0.60`

Common frozen rules:
- LONG
- exact M1 execution at decision time
- 240-minute horizon
- one position per family
- actual spread primary
- fixed-$0.20 sensitivity
- +1/+2bps sensitivity
- train 2023-24 / validation 2025 / test 2026

Decision tiers remain frozen:
STRONG:
- >=20 each split
- PF >=1.30 each split
- all PF >=1.50
- fixed-$0.20 all PF >=1.40
- +2bps all PF >=1.20
- all split nets positive

ROBUST:
- >=20 each split
- PF >=1.10 each split
- all PF >=1.30
- fixed-$0.20 all PF >=1.20
- +2bps all PF >=1.05
- all split nets positive

REJECT if any adequately populated split PF <=1.0, or all fixed-$0.20 PF <=1.0, or all +2bps PF <=1.0.

Do not alter these formulas, thresholds, horizon, execution, costs, splits, or decision tiers after outcomes.

## 13. M10W24 result — execution PASS, cohort scope mismatch

Uploaded package SHA256:
`167935382d79f780ab1f1d0f01dd8672b3186390a06cfb6d485cfcdba9d36c8a`

Execution integrity passed, with 8648 broader bullish/high-ATR rows and zero entry-data gaps.

Broader-cohort results:
- MVI1 REJECT: resolved 320, all PF 1.0736167150, +2bps PF 0.9596505482
- MWR1 REJECT: resolved 304, all PF 1.0823411942, +2bps PF 0.9580157484
- MMO1 REJECT: resolved 511, train PF 0.9803526694, 2026 PF 2.0933540485, all PF 1.1361539137, +2bps PF 1.0028386354

These results are valid only for the broader cohort.
They **must not** be interpreted as rejection of the original M10W17 NEITHER blind-spot hypotheses.

Cause:
`COHORT_SCOPE_IMPLEMENTATION_DRIFT_NOT_FORMULA_OR_THRESHOLD_FAILURE`

M10W22 omitted the pre-existing NEITHER parent filter.

Do not tune MVI1/MWR1/MMO1 from these outcomes.

## 14. M10W24B — exact next stage

Stage:
`M10W24B_NEITHER_COHORT_SCOPE_CORRECTION_AUDIT_ONLY`

This is a documented cohort-scope correction, not threshold rescue.

Correction only:
1. read M10W22 `02_target_regime_causal_feature_rows.csv`
2. read M10W14 `02_m15_coverage_grid.csv`
3. exact join on `decision_time`
4. retain only `coverage_class=NEITHER`
5. evaluate the exact frozen M10W23 MVI1/MWR1/MMO1 formulas

Absolutely unchanged:
- all three formulas
- all thresholds
- LONG direction
- exact M1 execution
- 240-minute horizon
- one-position-per-family
- actual/fixed/+1/+2bps costs
- train/2025/2026 splits
- STRONG/ROBUST/REJECT tiers

M10W24B historical result will still be research-exposed and is not clean independent validation because the broader M10W24 outcomes are already known.

Only an unchanged ROBUST or STRONG result may justify a brand-new fresh prospective shadow, and even then the historical result is not final support.

## 15. Immediate next action

Do not run any new threshold search or alternate formula before M10W24B.

Keep current monitors running unchanged.
Keep M10W19 BAT03 running.
Never rerun M10W19 BAT01.

Fetch/Pull latest branch, then run only:
`scripts/mochipoyo_alert_research/m10w24b/bat/01_run_neither_cohort_scope_correction.bat`

Then upload only:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W24B/LATEST/99_UPLOAD_PACKAGE.zip`

After upload:
- inspect package contents and SHA256 before claims
- verify exact NEITHER join counts / integrity
- verify formulas and decision tiers unchanged
- report train/2025/2026/all actual/fixed/+1/+2bps
- do not rescue failed families
- if ROBUST/STRONG, design a brand-new independent fresh shadow before claiming support
- if no family advances, do not threshold-tune these same families; move to genuinely new information or another preregistered hypothesis line

## 16. Never do

- Never reset or change a frozen prospective start.
- Never rerun M10P BAT01.
- Never rerun M10P2 BAT01.
- Never rerun M10W19 BAT01 after its start freeze.
- Never run M10V before both M10P and M10P2 have >=20 resolved and integrity PASS.
- Never backfill PC-off raw CSV gaps.
- Never delete loop locks blindly.
- Never treat early fresh zeros or very small n as efficacy evidence.
- Never use M10W24 broader-cohort results to claim the NEITHER hypothesis failed.
- Never change M10W23 formulas or thresholds for M10W24B.
- Never silently broaden active M10 research to BTCUSD.
- Never interpret historical research-exposed support as final live support.
- Never enable Discord send / MT5 orders / live_ready / final_signal / automatic promotion without explicit formal authorization.

## 17. Next-chat start prompt

Paste this into the next chat:

repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

MOCHIPOYO Alert Researchの続きです。

まずGitHub上の以下を順番どおり、最初から最後まで読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_COMPLETE_M10W24B_NEITHER_CORRECTION_READY_20260728.md
2. config/mochipoyo_alert_research/current_state_20260727.json
3. config/mochipoyo_alert_research/next_action_20260727.json
4. config/mochipoyo_alert_research/objective_coverage_plus_value_add_20260722.json
5. docs/mochipoyo_alert_research/SCOPE_CLARIFICATION_M10_GOLD_ONLY_M7C_DUAL_SOURCE_BACKGROUND_20260727.md
6. config/mochipoyo_alert_research/m10w24b_neither_cohort_scope_correction_contract_20260728.json
7. config/mochipoyo_alert_research/m10w23_high_atr_bullish_microstructure_entry_preregistration_20260728.json
8. config/mochipoyo_alert_research/m10w24_user_local_broader_cohort_result_scope_mismatch_20260728.json
9. config/mochipoyo_alert_research/m10w19_user_local_initial_fresh_start_result_20260728.json
10. config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json

現在の正式状態は:
M10W24_SCOPE_MISMATCH_DIAGNOSED_M10W24B_NEITHER_CORRECTION_READY_AUDIT_ONLY

次は:
M10W24B_NEITHER_COHORT_SCOPE_CORRECTION_AUDIT_ONLY

重要:
- 新しいM10研究はGOLD/XAUUSD onlyです。
- M7Cだけは凍結済みのBTCUSD+XAUUSD source-fidelity backgroundです。M7Cを変更しないでください。
- 全体はaudit-onlyです。
- MT5 server time基準です。
- CSV最新行はclosed契約です。
- historical backfill、future leakage、nearest-M1 fallbackは禁止です。
- collector/M7C/M8C/M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19を変更・resetしないでください。
- M10P BAT01、M10P2 BAT01は禁止です。
- M10W19 startは 2026.07.28 02:31:00 で固定済みです。M10W19 BAT01は二度と実行せず、BAT03のみ継続してください。
- M10VはM10PとM10P2が両方20 resolved以上かつintegrity PASSになるまで実行禁止です。
- M10W13以降、M10P/M10P2のhistorical threshold rescueは停止済みです。
- M10W24は実行自体はPASSしましたが、M10W22でcoverage_class=NEITHERが抜けていたため、broader high-ATR bullish cohortの結果です。M10W24のREJECTをNEITHER blind spotの失敗と解釈しないでください。
- M10W24BではM10W22 feature rowsとM10W14 coverage gridをdecision_timeでexact joinし、coverage_class=NEITHERだけに戻します。
- MVI1/MWR1/MMO1のformula、threshold、240分exit、exact M1、one-position、cost条件、split、STRONG/ROBUST/REJECT基準は一切変更禁止です。
- M10W24Bはscope correctionであってthreshold rescueではありません。
- M10W24Bで良くてもhistoricalはresearch-exposedです。fresh prospective shadowなしで最終支持・live採用しないでください。
- Discord send、MT5 order、live_ready、final_signal、automatic promotionは禁止です。

次に実行するBATは:
scripts/mochipoyo_alert_research/m10w24b/bat/01_run_neither_cohort_scope_correction.bat

出力は:
%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W24B/LATEST/99_UPLOAD_PACKAGE.zip

私は憶測での実装を禁止しています。疑問点があれば、勝手に条件を作らず、GitHubの正式契約・実装・結果を確認してから判断してください。

最初に、上記ファイルを実際に読んだうえで、現在地点、絶対禁止事項、M10W24 scope mismatchの意味、M10W24Bで変更するもの／変更しないものを簡潔に確認してから続けてください。
