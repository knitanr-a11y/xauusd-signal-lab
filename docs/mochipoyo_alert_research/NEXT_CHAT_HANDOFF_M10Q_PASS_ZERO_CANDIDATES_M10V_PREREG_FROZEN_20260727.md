# NEXT CHAT HANDOFF — M10Q PASS, dual fresh zero candidates, M10V comparison preregistered

Date: 2026-07-27
Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`

## Read first in the next chat
1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M10Q_PASS_ZERO_CANDIDATES_M10V_PREREG_FROZEN_20260727.md`
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10q_user_local_checkpoint_result_20260727.json`
5. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`
6. `docs/mochipoyo_alert_research/M10P_AND_AFTER_SHORT_ADOPTION_ROADMAP_20260725.md`

## Current operating state
Audit-only. Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.

Immutable starts:
- M7C UTC: `2026-07-20T14:54:15Z`
- M9V MT5 server: `2026.07.24 11:04:00`
- M9Y MT5 server: `2026.07.24 12:45:00`
- M10B MT5 server: `2026.07.24 20:54:00`
- M10E MT5 server: `2026.07.24 22:06:00`
- M10P MT5 server: `2026.07.24 23:56:00`
- M10P2 MT5 server: `2026.07.27 01:39:00`

Never rerun M10P BAT01 or M10P2 BAT01.

## M10P
Candidate: `M10L_H240_C056 + M10N_G013`
- h1_macd_hist_bps >= 3.637199446
- h1_macd_line_bps <= -7.667425443
- h1_ret3_bps >= 18.70087437
- d1_macd_hist_bps >= -14.25480242
- SHORT / 240 minutes / one-position

Historical deterministic reference:
- n=84
- PF=2.540715351740206
- fixed-$0.20 PF=2.538476073441831

Fresh review gates: 5 / 10 / 20 / 40 / 60 resolved.

## M10P2
Candidate: `M10J_C0212`
- h4_ema20_30_bps >= 37.61355979
- h1_atr_pct100 >= 0.8
- M15 decision
- SHORT / 240 minutes / one-position

Deterministic reproduction reference:
- n=318
- 2023-2024 PF=1.5689385901535529
- 2025 PF=1.3904778450159343
- 2026 PF=1.5465266111892766
- all PF=1.4839437156621065
- fixed-$0.20 all PF=1.4816933419152243
- max reference diff=0.0

Fresh review gates: 5 / 10 / 20 resolved.

## Latest M10Q result
Uploaded package: `99_UPLOAD_PACKAGE(39).zip`
SHA256: `f68789868c25b1994c4eb0421f975db1a3dadaa9b4404be39bfb04288ff40815`
Formal result: `config/mochipoyo_alert_research/m10q_user_local_checkpoint_result_20260727.json`

M10P at M10Q snapshot:
- start `2026.07.24 23:56:00`
- candidate 0
- accepted 0
- resolved 0
- open 0
- entry gap 0
- exit gap 0
- overlap 0
- next gate 5

M10P2 at M10Q snapshot:
- start `2026.07.27 01:39:00`
- candidate 0
- accepted 0
- resolved 0
- open 0
- entry gap 0
- exit gap 0
- overlap 0
- next gate 5

Latest common feed snapshot in M10Q:
- M1 `2026.07.27 03:45:00`
- M5 `2026.07.27 03:35:00`
- M15 `2026.07.27 03:30:00`
- H1 `2026.07.27 02:00:00`
- H4 `2026.07.24 20:00:00`
- D1 `2026.07.24 00:00:00`

Interpretation: no fresh condition has occurred yet. This is not candidate failure and is not a reason to loosen thresholds.

## M10V preregistration
File: `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`
Status: preregistration only; M10V must NOT execute yet.

Frozen execution gate:
- M10P >= 20 resolved
- M10P2 >= 20 resolved
- both integrity checks PASS
- starts unchanged
- thresholds unchanged
- no historical backfill

Direct comparison common window begins at the later immutable start: `2026.07.27 01:39:00` MT5 server time.

Single-capital future comparison is frozen as chronological first-come-first-served. While one 240-minute trade is active, later entries from either family are skipped in the single-capital view. Exact-same-timestamp same-direction qualification becomes one SHORT position, attributed to both for overlap accounting, with no double sizing or double PnL.

No threshold optimization, rescue filters, or outcome-driven sizing are allowed in M10V.

## Feed freshness correction
M10P and M10P2 use session-gap-aware observed-M1-bar freshness rather than wall-clock weekend elapsed time.
Preserved limits:
- M1 0
- M5 10
- M15 30
- H1 120
- H4 480
- D1 2880 observed M1 bars

This correction changed no candidate formula, threshold, start, or historical result.

## Forced reboot recovery
Use only:
`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

Restart order:
1. MT5 / CSV export
2. collector
3. M7C
4. M8C
5. M9V
6. M9Y
7. M10B
8. M10E
9. M10P BAT03 only
10. M10P2 BAT03 only

Recovery may recover stale locks only. It must not reset starts/runtimes/history. PC-off raw-data gaps remain unobserved and are never backfilled.

## Absolute prohibitions
- no M10P BAT01
- no M10P2 BAT01
- no start reset/change
- no historical backfill
- no nearest M1 fallback
- latest CSV row is CLOSED
- MT5 server time only
- no prospective threshold refit
- no Discord send
- no MT5 order
- no live_ready
- no final_signal
- no automatic promotion
- do not merge M10P and M10P2 before the preregistered M10V execution gate

## Next action
Continue both fresh shadows unchanged. Run M10Q read-only audit when a checkpoint review is desired and specifically when either family approaches/reaches a predeclared review gate. If neither reaches a gate, keep accumulating fresh evidence without tuning.

Do not execute M10V until both M10P and M10P2 have at least 20 resolved and all frozen integrity conditions pass.
