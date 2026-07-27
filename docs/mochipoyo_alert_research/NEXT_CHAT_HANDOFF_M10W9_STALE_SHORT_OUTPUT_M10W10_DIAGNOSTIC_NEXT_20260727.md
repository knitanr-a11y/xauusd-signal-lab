# NEXT CHAT HANDOFF — M10W9 stale SHORT output / M10W10 diagnostic next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w9_m10q_refresh_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w10_m10p_m10p2_runtime_freshness_diagnostic_contract_20260727.json`

## Scope
Current new M10 research remains GOLD/XAUUSD only. M7C remains its frozen BTCUSD+XAUUSD background source-fidelity track unchanged.

## Preserved monitors / starts
Keep collector, M7C, M8C, M9V, M9Y, M10B and M10E unchanged.

Immutable starts:
- M9V `2026.07.24 11:04:00`
- M9Y `2026.07.24 12:45:00`
- M10B `2026.07.24 20:54:00`
- M10E `2026.07.24 22:06:00`
- M10P `2026.07.24 23:56:00`
- M10P2 `2026.07.27 01:39:00`

Never rerun M10P BAT01 or M10P2 BAT01.

## M10W9 finding
User uploaded M10Q refresh package SHA256:
`d8d83d038bebc0e32bfdda87f7800d70a50a09eedfb0ad8e90fcbcd9c27bc662`

M10Q itself PASSed read-only at `2026-07-27T18:04:05Z`.
It reported:
- M10P candidate/accepted/resolved/open = 0/0/0/0, latest M1 `2026.07.27 03:45:00`
- M10P2 candidate/accepted/resolved/open = 0/0/0/0, latest M1 `2026.07.27 03:45:00`

But M9Y had already reported raw M1 through `2026.07.27 20:50:00` shortly before. Difference = 1025 minutes.

Therefore the M10Q zero counts are NOT accepted as current market evidence. The M10P/M10P2 LATEST outputs are stale relative to the live GOLD feed. Runtime status must be diagnosed before saying the SHORT conditions did or did not occur.

Do not restart, reset, reinitialize, delete locks, change starts or change thresholds based on this finding.

## Existing BAT03 contracts
M10P BAT03 uses:
`scripts/mochipoyo_alert_research/m10p/python/m10p_guarded_runtime.py forever`

M10P2 BAT03 uses:
`scripts/mochipoyo_alert_research/m10p2/python/m10p2_guarded_runtime.py forever`

Both guarded wrappers use observed-M1 trading-bar feed freshness rather than consuming weekend wall-clock time.

## Next: M10W10
Stage:
`M10W10_M10P_M10P2_RUNTIME_FRESHNESS_DIAGNOSTIC_AUDIT_ONLY`

Run only:
`scripts/mochipoyo_alert_research/m10w10/bat/01_run_m10p_m10p2_runtime_freshness_diagnostic.bat`

Upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W10\LATEST\99_UPLOAD_PACKAGE.zip`

M10W10 is read-only with respect to monitored research state. It checks:
- current raw six-file GOLD tails
- M10P/M10P2 LATEST summary age
- runtime state cycle count / last cycle
- immutable runtime and frozen-prefix integrity
- lock existence and PID from lock
- best-effort Windows PID existence
- current observed-M1 feed guard
- raw M1 vs output M1 staleness

It writes only its own M10W10 diagnostic output package.

## After M10W10
Do not take action before reviewing the package.

Possible outcomes:
- loop exited + lock absent + current guard PASS -> BAT03-only restart may be authorized after review, preserving immutable start/runtime/state
- stale lock + no live PID -> handle lock only after explicit review
- current guard/integrity BLOCK -> diagnose that failure; do not force restart
- live PID present but output stale -> inspect process/console state before action

## Fresh LONG context
Latest fresh LONG evidence remains early/descriptive only:
- M9V S1_M5=3, S2_M15=5, S3_H1=0, S4_H4=0
- M9Y Y0 resolved=3, N6 flagged=0; formal gates not reached
- M10B M5 resolved=1, H1/H4=0
- M10E H1=0

No LONG efficacy/rule change is authorized from these small counts.

## SHORT comparison gate
M10V remains forbidden before BOTH M10P and M10P2 have >=20 valid fresh resolved trades with integrity PASS. The stale M10Q zero counts do not advance or reset that gate.

## Safety
Audit-only. No historical backfill, no threshold refit, no start reset, no lock deletion before review, no Discord send, no MT5 order, no live_ready, no final_signal, no automatic promotion. Project time basis remains MT5 server time and newest CSV row remains CLOSED by contract.
