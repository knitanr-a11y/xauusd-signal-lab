# MOCHIPOYO Alert Research handoff — M10W10 diagnostic PASS, M10W11 BAT03 restart next

## Read first
1. `config/mochipoyo_alert_research/current_state_20260727.json`
2. `config/mochipoyo_alert_research/next_action_20260727.json`
3. `config/mochipoyo_alert_research/m10w10_user_local_runtime_freshness_diagnostic_result_20260728.json`
4. `config/mochipoyo_alert_research/m10w11_m10p_m10p2_bat03_restart_verification_contract_20260728.json`
5. `config/mochipoyo_alert_research/m10p_c056_g013_fresh_prospective_shadow_contract_20260725.json`
6. `config/mochipoyo_alert_research/m10p2_c0212_fresh_prospective_shadow_contract_20260725.json`

## Scope / safety
- New M10 research is GOLD / XAUUSD only.
- audit-only.
- no Discord send, MT5 order, live_ready, final_signal, automatic promotion.
- do not change frozen thresholds or starts.
- M10P BAT01 and M10P2 BAT01 are permanently forbidden.
- M10V remains forbidden until both SHORT families have at least 20 resolved and integrity PASS.

## M10W10 finding
Uploaded package SHA256:
`c5af5b33a6a97f594b625e602668a8e2f6d0c6ebd3b2e6b18d255e4819b071e9`

Raw feed at diagnostic:
- M1 `2026.07.27 21:15:00`
- M5 `2026.07.27 21:10:00`
- M15 `2026.07.27 21:00:00`
- H1 `2026.07.27 20:00:00`
- H4 `2026.07.27 16:00:00`
- D1 `2026.07.24 00:00:00`

M10P:
- immutable start `2026.07.24 23:56:00`
- last cycle UTC `2026-07-27T00:46:08Z`
- cycle count 2380
- last summary M1 `2026.07.27 03:45:00`
- lock absent
- runtime integrity PASS
- current observed-feed guard PASS

M10P2:
- immutable start `2026.07.27 01:39:00`
- last cycle UTC `2026-07-27T00:46:21Z`
- cycle count 101
- last summary M1 `2026.07.27 03:45:00`
- lock absent
- runtime integrity PASS
- current observed-feed guard PASS

Conclusion: both persistent SHORT loops are not currently running, but their frozen runtime/state/start remain valid.

## Important restart semantics clarification
Do not add a gap-quarantine rule. Both frozen contracts explicitly declare:
- `restart_safe: true`
- `rebuild_post_start_deterministically_each_cycle: true`

Therefore BAT03 restart is the intended recovery path. Rebuilding already-collected post-start raw data under the already-frozen formula/start is not pre-start historical backfill and does not authorize threshold tuning. Exact missing M1 timestamps still remain data gaps per the frozen contracts.

## M10W11 operator sequence
Keep collector/M7C/M8C/M9V/M9Y/M10B/M10E unchanged.

1. Run existing M10P BAT03 only:
   `scripts\mochipoyo_alert_research\m10p\bat\03_run_shadow_forever.bat`
   Confirm first console cycle prints PASS.

2. Then run existing M10P2 BAT03 only:
   `scripts\mochipoyo_alert_research\m10p2\bat\03_run_shadow_forever.bat`
   Confirm first console cycle prints PASS.

3. After both first PASS cycles, run existing read-only M10Q once:
   `scripts\mochipoyo_alert_research\m10q\bat\01_run_dual_fresh_checkpoint_audit.bat`

4. Upload only:
   `%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10Q\LATEST\99_UPLOAD_PACKAGE.zip`

## What to verify next
- M10P and M10P2 summary M1 should advance beyond the stale `2026.07.27 03:45:00` frontier.
- Starts must remain exactly unchanged.
- Integrity must remain PASS.
- Record current candidate / accepted / resolved / open / gap / overlap counts from refreshed M10Q.
- Do not interpret PF before declared gates.
- Do not execute M10V before both families reach 20 resolved.
