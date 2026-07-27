# MOCHIPOYO Alert Research handoff — M10W13 PASS / M10W14 directional coverage next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W13_PASS_M10W14_DIRECTIONAL_COVERAGE_MAP_READY_AUDIT_ONLY`

All existing forward monitors remain running unchanged. Immutable starts remain unchanged. M10P/M10P2 BAT01 remain forbidden. M10V remains forbidden until M10P and M10P2 both reach 20 resolved with integrity PASS.

## Why M10W14 exists

M10W13 showed that the current zero-match SHORT period is historically ordinary and did not justify threshold rescue. Existing-family historical threshold rescue research is therefore stopped.

The user raised a separate and important concern: prior attempts to find edge often produced weak or unconvincing performance. M10W14 does **not** try to rescue those candidates. Instead it asks whether the present candidate stack has structural directional/regime blind spots.

## M10W14

Stage:
`M10W14_GOLD_DIRECTIONAL_COVERAGE_AND_BLIND_SPOT_MAP_AUDIT_ONLY`

Contract:
`config/mochipoyo_alert_research/m10w14_gold_directional_coverage_blind_spot_map_contract_20260728.json`

Operator:
`scripts/mochipoyo_alert_research/m10w14/bat/01_run_gold_directional_coverage_blind_spot_map.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W14/LATEST/99_UPLOAD_PACKAGE.zip`

## Exact M10W14 scope

Outcome-blind only. Common M15 server-time windows are classified as:

- LONG_ONLY
- SHORT_ONLY
- BOTH
- NEITHER

Frozen candidate families mapped:

LONG:
- M5_S1
- M15_S2
- H1_S3
- H4_S4

SHORT:
- M10P C056+G013
- M10P2 C0212

Regime axes:
- D1 EMA20/30/40 stack: bullish / bearish / mixed
- H4 EMA20-EMA30 sign
- H1 MACD-line sign
- H1 ATR-percentile tercile

M10W14 must not read or compute trade outcomes, PF, PnL, win rate, future path labels, or threshold rescue. Coverage is not edge.

## Research sequence after M10W14

Only after reviewing the coverage/blind-spot map may a later M10W15 pre-register **independent** blind-spot hypotheses. New candidate formulas must be frozen before their performance is inspected.

Historical results are research-exposed and cannot by themselves overturn the user's prior concern about weak candidates. A genuinely new family must ultimately be validated by a brand-new fresh prospective shadow with frozen rules and no backfill/refit.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- no Discord send
- no MT5 orders
- no live_ready/final_signal
- no threshold refit
- no runtime/start reset
- no historical backfill into forward
- keep all current monitors running unchanged
