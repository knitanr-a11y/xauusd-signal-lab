# NEXT CHAT HANDOFF — M10W2 PASS / M10W3 GOLD LONG portfolio comparison next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w2_user_local_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w3_gold_long_baseline_vs_filtered_h1_portfolio_contract_20260727.json`
6. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

## Scope and running systems
New M10 research remains GOLD/XAUUSD only. M7C remains its frozen BTCUSD+XAUUSD background source-fidelity track.
Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
Never rerun M10P BAT01 or M10P2 BAT01. Never change frozen starts.

## SHORT fresh track remains separate
M10P and M10P2 remain independent fresh SHORT shadows. Latest recorded M10Q checkpoint was 0 resolved for both, next gate 5.
M10V remains forbidden until BOTH M10P >=20 resolved and M10P2 >=20 resolved with integrity PASS.
M10W historical LONG research must not bypass this gate or read SHORT fresh outcomes for selection.

## M10W0 record correction
The M10W0 formal result previously contained a transcription-only typo in `frozen_raw_hashes.M5`.
Correct hash:
`c47c0a136e8a953bf219bfbcb80a79ccac3afb04a0ed6e825843eba143948d`
The record was corrected without changing raw data, logic, thresholds or starts.

## M10W1 result
Baseline LONG portfolio:
- CORE M5_RUNNER75 + H1_RUNNER50 single-capital PF 1.9623457969, net +4790.231951 bps, DD 328.823566 bps
- EXTENDED + H4_ENTRY single-capital PF 2.3542115765, net +6812.558036 bps, DD 377.403475 bps
- H4 remains sensitivity, not automatically promoted to core

## M10W2 result — M10D H1 compound filter
Package SHA256:
`59f728be1ce5c9da495025b50074bfc6bcc09c825bbffdf914ceaef9ac02f0b5`

Frozen filter:
- exclude H1 LONG when M5 MACD bps slope <= -0.1308
- AND H1 EMA30-EMA40 distance >= 17.3333 bps
- features use closed bars at or before actual H1 reclaim entry time

Baseline H1 runner50:
- n 159
- PF 2.8303858343
- net +2802.749225 bps
- payoff 1.3365710884
- DD 271.583160 bps

Filtered H1 runner50:
- n 130
- PF 5.4011538833
- net +2956.129828 bps
- payoff 1.9129086670
- DD 101.743044 bps
- fixed-$0.20 PF 5.3636874915
- additional +2 bps PF 4.6152185532

Yearly PF improves versus baseline in 2023/2024/2025/2026, but 2025 net decreases from +1071.49 to +848.19 bps. The rule is research-exposed historical evidence, not fresh OOS validation.

Excluded forensics:
- 34 candidates excluded before one-position
- 30 baseline accepted trades removed
- removed baseline subset PF 0.85770049, net -122.315329 bps
- filtering freed capacity for 1 new accepted trade, +31.065274 bps

Interpretation:
Keep baseline H1 and filtered H1. Filtered H1 is a strong historical challenger, not an operational replacement. M10E fresh evidence remains required before operational replacement.

## Next stage — M10W3
Stage:
`M10W3_GOLD_LONG_BASELINE_VS_FILTERED_H1_PORTFOLIO_AUDIT_ONLY`

Run:
`scripts/mochipoyo_alert_research/m10w3/bat/01_run_gold_long_baseline_vs_filtered_h1_portfolio_audit.bat`

Upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W3\LATEST\99_UPLOAD_PACKAGE.zip`

Frozen scenarios:
1. CORE_BASELINE = M5_RUNNER75 + H1_BASELINE_RUNNER50
2. CORE_FILTERED = M5_RUNNER75 + H1_FILTERED_RUNNER50
3. EXTENDED_BASELINE = M5_RUNNER75 + H1_BASELINE_RUNNER50 + H4_ENTRY
4. EXTENDED_FILTERED = M5_RUNNER75 + H1_FILTERED_RUNNER50 + H4_ENTRY

Single-capital policy is chronological first-come-first-served, one normalized position, no pyramiding. Exact same entry timestamp across included families is fail-closed. Cost sensitivity is +0.5/+1.0/+1.5/+2.0 bps per accepted trade.

M10W3 must not read SHORT ledgers, M10E fresh outcomes for selection, or M10P/M10P2 fresh outcomes. It must not alter any running monitor, threshold, runtime or start.

## Safety
Audit-only. No backfill, no future leakage, no nearest-M1 fallback, newest CSV row CLOSED, MT5 server time only, no Discord send, no MT5 orders, no live_ready, no final_signal, no automatic promotion.
