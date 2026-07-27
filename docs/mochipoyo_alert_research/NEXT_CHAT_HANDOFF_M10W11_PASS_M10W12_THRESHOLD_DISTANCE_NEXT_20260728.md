# MOCHIPOYO Alert Research handoff — M10W11 PASS / M10W12 next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Read first

1. `config/mochipoyo_alert_research/current_state_20260727.json`
2. `config/mochipoyo_alert_research/next_action_20260727.json`
3. `config/mochipoyo_alert_research/m10w11_user_local_bat03_restart_verification_result_20260728.json`
4. `config/mochipoyo_alert_research/m10w12_dual_short_threshold_activation_distance_contract_20260728.json`
5. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`
6. `docs/mochipoyo_alert_research/M10P_AND_AFTER_SHORT_ADOPTION_ROADMAP_20260725.md`

## Scope and safety

- New M10 research is GOLD / XAUUSD only.
- M7C remains the separate frozen BTCUSD+XAUUSD source-fidelity background track and must not be altered.
- audit-only.
- no Discord send.
- no MT5 order.
- no live_ready/final_signal/automatic promotion.
- CSV newest row is CLOSED.
- MT5 server time only.
- no historical backfill.
- no threshold refit from prospective outcomes.
- M10P BAT01 and M10P2 BAT01 are permanently forbidden.
- M10V is forbidden until BOTH M10P and M10P2 have at least 20 resolved fresh trades with integrity PASS.

## Immutable prospective starts

- M9V: `2026.07.24 11:04:00`
- M9Y: `2026.07.24 12:45:00`
- M10B: `2026.07.24 20:54:00`
- M10E: `2026.07.24 22:06:00`
- M10P: `2026.07.24 23:56:00`
- M10P2: `2026.07.27 01:39:00`

## M10W9 / M10W10 incident and resolution

M10Q initially showed both SHORT shadows at M1 `2026.07.27 03:45:00` while other GOLD monitors had advanced beyond `20:50`. M10W10 diagnosed both loops as not running, with no lock, runtime integrity PASS, current feed guard PASS, and preserved immutable starts.

M10P and M10P2 frozen contracts explicitly declare:

- `restart_safe = true`
- `rebuild_post_start_deterministically_each_cycle = true`

Therefore BAT03-only restart was authorized; no gap-quarantine threshold/start modification was required.

M10W10 result:
`config/mochipoyo_alert_research/m10w10_user_local_runtime_freshness_diagnostic_result_20260728.json`

## M10W11 actual user-local result — PASS

Uploaded package:
- filename: `99_UPLOAD_PACKAGE(51).zip`
- SHA256: `038d35f9348ac5988b56c325a05ed04d086992cd1d28feadc00e96e8d3f4f3d4`
- built: `2026-07-27T18:30:42Z`

Formal result:
`config/mochipoyo_alert_research/m10w11_user_local_bat03_restart_verification_result_20260728.json`

M10P after BAT03 restart:
- start unchanged: `2026.07.24 23:56:00`
- latest M1: `2026.07.27 21:28:00`
- candidate=0
- accepted=0
- resolved=0
- open=0
- entry gap=0
- exit gap=0
- overlap=0
- next gate=5

M10P2 after BAT03 restart:
- start unchanged: `2026.07.27 01:39:00`
- latest M1: `2026.07.27 21:29:00`
- candidate=0
- accepted=0
- resolved=0
- open=0
- entry gap=0
- exit gap=0
- overlap=0
- next gate=5

Interpretation:
- stale-output anomaly is resolved.
- current zero-match state is now valid current prospective market evidence.
- zero trades provide NO efficacy/performance inference.
- do not change thresholds because of zero counts or near misses.

## M10W12 — next

Stage:
`M10W12_DUAL_SHORT_THRESHOLD_ACTIVATION_DISTANCE_AUDIT_ONLY`

Contract:
`config/mochipoyo_alert_research/m10w12_dual_short_threshold_activation_distance_contract_20260728.json`

Script:
`scripts/mochipoyo_alert_research/m10w12/python/run_m10w12_dual_short_threshold_activation_distance_audit.py`

Operator:
`scripts\mochipoyo_alert_research\m10w12\bat\01_run_dual_short_threshold_activation_distance_audit.bat`

Output to upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W12\LATEST\99_UPLOAD_PACKAGE.zip`

M10W12 is strictly read-only. Keep all monitors running unchanged.

It must report, separately for the two frozen SHORT families:

### M10P C056+G013
Frozen conditions:
- `h1_macd_hist_bps >= 3.637199446`
- `h1_macd_line_bps <= -7.667425443`
- `h1_ret3_bps >= 18.70087437`
- `d1_macd_hist_bps >= -14.25480242`

Required descriptive checks:
- total post-start causal H1 decisions in the current M10P summary window
- per-condition pass counts
- seed pair pass count
- regime pair pass count
- all-four pass count
- latest raw values and signed margins
- closest near misses with raw margins only
- exact cross-check: all-four pass count must equal running M10P `candidate_match_count`

### M10P2 C0212
Frozen conditions:
- `h4_ema20_30_bps >= 37.61355979`
- `h1_atr_pct100 >= 0.8`

Required descriptive checks:
- total post-start causal M15 decisions in the current M10P2 summary window
- per-condition pass counts
- joint pass count
- latest raw values and signed margins
- closest near misses with raw margins only
- exact cross-check: joint pass count must equal running M10P2 `candidate_match_count`

## Critical M10W12 interpretation rule

Near-miss distance is descriptive only. Never use prospective near-miss output to lower, rescue, tune, or refit a frozen threshold.

If individual legs activate but the full conjunction does not, the detector is not dead; the current conjunction simply has not occurred.

If a frozen leg never activates in the observed interval, record that fact only. Do not weaken it from this prospective sample.

## Existing LONG state to preserve

Historical LONG work M10W0–M10W4 is complete. Filtered H1 remains a strong historical challenger, not an operational replacement before M10E fresh evidence.

Current fresh LONG observations remain early/descriptive:
- M9V: S1_M5=3, S2_M15=5, S3_H1=0, S4_H4=0
- M9Y: Y0 resolved=3, N6 flagged=0, operational gate=20
- M10B: M5 resolved=1, H1=0, H4=0
- M10E: H1 resolved=0

Do not refit any LONG rule from these small fresh counts.

## Recovery

Forced reboot operator only:
`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

M10P/M10P2 restart after a valid recovery remains BAT03 only, never BAT01.
