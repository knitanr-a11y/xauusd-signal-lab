# MOCHIPOYO Alert Research — M10W33 PASS / M10W34 next

repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## Current state

`M10W33_ONE_ROBUST_SNDX1_M10W34_IMPLEMENTED_INITIALIZE_ONCE_NEXT_AUDIT_ONLY`

Keep collector, M7C, M8C and the eight existing private-snapshot loops running unchanged:
M9V, M9Y, M10B, M10E, M10P, M10P2, M10W19 and M10W26.

M10W26 immutable MT5-server start remains `2026.07.28 15:58:00`. M10W26 BAT01 is permanently forbidden.

## M10W33 result

Uploaded package SHA256:
`fa41d4717e32e5f02cade9043928e27d2d023b13148f7d80b53cdd84edb33a13`

Formal result:
`config/mochipoyo_alert_research/m10w33_user_local_result_20260728.json`

- SNRI1: REJECT; test PF 0.8606475952
- SNRC1: REJECT; test PF 0.7208763323
- SNDX1: ROBUST_CANDIDATE
  - train PF 1.6040678268
  - validation PF 1.7746476467
  - test count 32, PF 1.1872049166, net +106.2531 bps
  - all PF 1.6253362465
  - fixed $0.20 PF 1.6144854774
  - +2bps PF 1.4346749771

Trade ledger and overlap ledger were independently recalculated and matched the package summary.
Historical support is not fresh support. No automatic promotion is allowed.

## M10W34

Contract:
`config/mochipoyo_alert_research/m10w34_sndx1_fresh_prospective_shadow_contract_20260728.json`

Implementation audit:
`config/mochipoyo_alert_research/m10w34_prestart_implementation_audit_20260728.json`

Frozen formula:

- `m5_range3_over_h1_atr14 >= 0.40`
- `m1_range5_over_h1_atr14 >= 0.20`
- `m1_ret5_over_h1_atr14 > 0.0`
- `m1_close_location >= 0.60`

Target:
D1 bullish + H4 EMA20>EMA30 + H1 MACD line>0 + H1 ATR percentile100<0.33 + prefix-causal NEITHER.

Execution:
exact M1 entry, exact +240m M1 exit, actual spread, one position, no nearest-M1 fallback.

## First launch

1. Fetch/Pull the branch.
2. Run exactly once:
   `scripts/mochipoyo_alert_research/m10w34/bat/01_initialize_fresh_start_once.bat`
3. Require PRESTART ENGINE PASS and INIT PASS.
4. Never rerun BAT01 after INIT PASS.
5. Start and keep open:
   `scripts/mochipoyo_alert_research/m10w34/bat/03_run_shadow_forever.bat`
6. After first M10W34 PASS, run:
   `scripts/mochipoyo_alert_research/m10w34/bat/05_audit_initial_health.bat`
7. Upload:
   `%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W34_INITIAL_HEALTH\LATEST\99_UPLOAD_PACKAGE.zip`

## Permanent prohibitions

Do not run BAT01/init/reset for existing loops or M10W26. Do not stop or taskkill healthy loops. Do not delete locks, runtime, state, snapshot, adapter or journal files. Do not change prospective starts. Do not backfill before starts. Do not tune M10W33/M10W34 formulas, thresholds, sessions, ATR boundary, horizon, exit or runner. No Discord, MT5 order, live-ready, final-signal or automatic promotion.
