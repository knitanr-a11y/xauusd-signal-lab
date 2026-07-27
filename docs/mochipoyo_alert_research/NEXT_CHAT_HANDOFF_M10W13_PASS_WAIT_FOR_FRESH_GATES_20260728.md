# MOCHIPOYO Alert Research — M10W13 PASS / Wait for predeclared fresh gates

repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## Current formal status

`M10W13_PASS_WAIT_FOR_PREDECLARED_FRESH_GATES_AUDIT_ONLY`

Active NEW M10 research remains **GOLD / XAUUSD only**. M7C remains the older frozen dual-symbol source-fidelity background track.

All monitors stay unchanged:
- collector
- M7C
- M8C
- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2

Immutable starts remain:
- M7C UTC `2026-07-20T14:54:15Z`
- M9V `2026.07.24 11:04:00`
- M9Y `2026.07.24 12:45:00`
- M10B `2026.07.24 20:54:00`
- M10E `2026.07.24 22:06:00`
- M10P `2026.07.24 23:56:00`
- M10P2 `2026.07.27 01:39:00`

M10P/M10P2 BAT01 remain permanently forbidden. BAT03 restart only, preserving starts/runtime.

## M10W13 result

Result file:
`config/mochipoyo_alert_research/m10w13_user_local_historical_activation_interval_result_20260728.json`

Uploaded package SHA256:
`3b42b91c7466d50fece292ea0d38a0b751503256c23cb753a372c922f6ec89bd`

Stage status:
`PASS_FROZEN_HISTORICAL_WAITING_TIME_WITHIN_NORMAL_RANGE_NO_THRESHOLD_ACTION`

This stage used frozen research-exposed GOLD history only for activation/no-match waiting-time calibration.
It did **not** read trade outcomes and did **not** calculate PF/PnL/WR.
It is not fresh support.

### M10P C056+G013 historical activation context

- eligible H1 decisions: 20,436
- exact activations: 164
- activation rate: 0.8025%
- historical zero-run count: 98
- zero-run median: 111.5 decisions
- p75: 249.5
- p90: 529.7
- p95: 689.2
- p99: 1096.13
- max: 2038
- current prospective zero-match decisions from M10W12: 21
- current zero-run empirical percentile: 28.57%
- 72.45% of historical zero-runs were at least as long as current 21

Current 21-decision wait is therefore ordinary and below the historical median.

Historical bottleneck leg was not dead:
- `h1_macd_line_bps <= -7.667425443` passed 4,779 / 20,436 decisions = 23.39%

M10W12 current interval had line-leg pass count 0, but historical evidence shows that leg is intermittent rather than permanently inactive.

### M10P2 C0212 historical activation context

- eligible M15 decisions: 81,329
- exact activations: 4,422
- activation rate: 5.437%
- historical zero-run count: 127
- zero-run median: 56 decisions
- p75: 288
- p90: 1875.6
- p95: 3307.7
- p99: 7045.84
- max: 12,460
- current prospective zero-match decisions from M10W12: 81
- current zero-run empirical percentile: 59.84%
- 40.16% of historical zero-runs were at least as long as current 81

Current 81-decision wait is above the historical median but still well inside the historical p90 range.

C0212 activations are highly clustered:
- inter-activation median = 1 decision
- p90 = 1
- p95 = 1
- max spacing = 12,461

So the unconditional 5.44% activation rate must **not** be interpreted as a simple independent Bernoulli arrival rate. Long no-match regimes historically occurred despite activation clusters.

Historical bottleneck leg was not dead:
- `h4_ema20_30_bps >= 37.61355979` passed 12,254 / 81,329 decisions = 15.07%

## Interpretation frozen after M10W13

- detectors dead: **false**
- current zero-match runs unusually long: **false**
- threshold rescue/refit: **forbidden**
- performance inference from waiting-time history: **forbidden**
- historical activation density as fresh support: **false**
- further historical threshold drilling: **stop**

Do not use M10W12 near-misses or M10W13 waiting-time distributions to lower thresholds.

## Next policy

There is no immediate new historical research BAT to run.
Keep all forward monitors running unchanged and wait for predeclared fresh gates.

Fresh review triggers:

### M9Y
- Y0 accepted 20: operational review
- N6 flagged 10: risk-sizing review
- Y0 accepted 60: interim
- Y0 accepted 120: formal

### M10E
- resolved 5: health/first review
- resolved 10: interim
- resolved 20: formal baseline-vs-filtered review

### M10P
- resolved 5: operational
- resolved 10: interim
- resolved 20: formal

### M10P2
- resolved 5: operational
- resolved 10: interim
- resolved 20: formal

### M10V
Execution remains **FORBIDDEN** until:
- M10P >= 20 resolved
- M10P2 >= 20 resolved
- both integrity PASS
- starts/thresholds unchanged
- no unresolved runtime/prefix violation

## Safety

- audit-only
- no Discord send
- no MT5 order
- no live_ready
- no final_signal
- no automatic promotion
- no historical backfill
- no threshold refit
- no start reset
- no runtime reset
- CSV newest row contract remains CLOSED
- project times remain MT5 server time
- M10P BAT01 NEVER
- M10P2 BAT01 NEVER

## Next chat start

Read first:
1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M10W13_PASS_WAIT_FOR_FRESH_GATES_20260728.md`
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w13_user_local_historical_activation_interval_result_20260728.json`

Then continue only from the actual fresh monitor state. Do not invent a new threshold rescue stage merely because current candidate counts remain low or zero.
