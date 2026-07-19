# Stage M7B — Frozen Trigger Kernel Validation Audit Contract

Status: audit-only  
Contract version: `MOCHIPOYO_M7B_FROZEN_TRIGGER_KERNEL_VALIDATION_V1`

## 1. Purpose

M7B freezes a small, interpretable set of independent trigger-proxy kernels before any later genuine Webhook events are used.

It does not continue M7A rule discovery. It does not claim to identify Mochipoyo's proprietary formula. It measures only trigger reproduction behavior on the already verified M15 observation windows:

- genuine event recall and event-by-event misses;
- verified-window no-event false positives;
- false-positive time clusters;
- BTCUSD/XAUUSD separation and unchanged-formula cross-symbol application;
- EMA ordering residuals and near-cross sensitivity;
- exit-threshold sensitivity;
- suitability for prospective M7C shadow comparison.

Trade outcomes, MFE, MAE, source EXIT profit, win rate, PF, and future bars remain outside M7B.

## 2. Frozen source boundary

The frozen manifest is:

```text
config/mochipoyo_alert_research/m7b_frozen_trigger_kernel_manifest_v1.json
```

It is based on the M7A result built at:

```text
2026-07-19T17:45:00Z
```

The manifest must be committed before newly arrived genuine events are used for forward comparison.

After freeze, later events may not be used to alter the same formulas or sensitivity values. They belong to M7C forward validation.

## 3. Causal decision contract

M7B must reuse M7A `build_decision_samples` without changing the decision cutoff.

For every M15 decision boundary:

- decision time is the new M15 bar open;
- the latest usable OHLC bar is the immediately preceding fully closed M15 bar;
- the new M15 open may be used;
- the new M15 high, low, and close are forbidden;
- future bars are forbidden;
- causal pivot proxies remain valid only after right-side confirmation;
- the M4-selected M15 bar for every genuine event must match exactly;
- source event identity remains the Webhook/SQLite event ID.

CSV rows outside the verified first-to-last source-event window for each ticker must not be treated as no-event controls.

## 4. Frozen kernels

### CORE-L0

```text
state_before == IDLE
AND rci9_turn_up == True
```

This is the timing-only PRIMARY LONG baseline.

### KERNEL-L1

```text
state_before == IDLE
AND rci9_turn_up == True
AND ema_alignment == BULLISH_STACK
```

`BULLISH_STACK` means:

```text
EMA20 > EMA30 > EMA40
```

### CORE-S0

```text
state_before == IDLE
AND rci9_turn_down == True
```

This is the timing-only PRIMARY SHORT baseline.

### KERNEL-S1

```text
state_before == IDLE
AND rci9_turn_down == True
AND ema_alignment == BEARISH_STACK
```

`BEARISH_STACK` means:

```text
EMA20 < EMA30 < EMA40
```

### EXIT-L0

```text
state_before == ACTIVE_LONG
AND rci9 >= 78.333333333333
```

### EXIT-S0

```text
state_before == ACTIVE_SHORT
AND rci9 <= -75
```

No PRIMARY EMA rule is copied to EXIT or reentry without separate evidence.

## 5. Reentry policy

No reentry formula is frozen.

- `REENTRY_LONG`: one combined positive and zero XAUUSD positives; reject as a one-sample artifact.
- `REENTRY_SHORT`: four combined positives and one XAUUSD positive; observation only.
- PRIMARY EMA ordering must not be assumed to apply to reentry.

## 6. Required event audit

For every genuine event eligible for each frozen kernel, output one row with:

- source `raw_alert_id`;
- ticker;
- decision time;
- selected MT5 server-open time;
- state before;
- actual transition;
- kernel ID;
- `TRUE_POSITIVE` or `FALSE_NEGATIVE`;
- RCI9 level, delta, and local-turn flags;
- EMA alignment, slopes, spread, and pairwise EMA gaps;
- current-open location relative to EMA20 and EMA40;
- prior source transition and bars since prior source event.

Opposite or other genuine events matched by a kernel must be reported separately as `OTHER_GENUINE_EVENT_COLLISION`. They must not be silently counted as ordinary no-event controls.

## 7. Required no-event false-positive audit

For every matched `NO_EVENT` decision within the verified observation window, output the complete row and diagnostic features.

False positives are clustered separately by:

- strict contiguous M15 boundaries: gap `<= 15` minutes;
- gap-tolerant bursts: gap `<= 30` minutes.

Both cluster definitions are frozen diagnostics. Neither may be selected after looking at which gives the more favorable presentation.

## 8. Cross-symbol audit

Every frozen formula must be evaluated unchanged on BTCUSD and XAUUSD.

The cross-symbol table must explicitly show:

```text
BTCUSD source evidence -> unchanged formula on XAUUSD
XAUUSD source evidence -> unchanged formula on BTCUSD
```

No threshold or condition may be refitted between symbols.

The table must include, for source and validation symbol:

- positive support;
- matched positives;
- event recall;
- verified-window no-event false positives.

## 9. EMA calculation and near-cross audit

M7B derives pairwise EMA gaps from the causal closed-bar distances:

```text
EMA20 - EMA30
EMA30 - EMA40
```

The derived strict ordering must agree with the stored `ema_alignment`. Any disagreement is fail-closed.

Because exported TradingView EMA numeric values are not present, M7B may not claim a direct TradingView-versus-MT5 EMA difference was measured.

Instead, it must identify genuine events and false positives where either EMA pair is close to crossing and report pre-frozen symmetric tolerance diagnostics:

```text
0.00, 0.25, 0.50, 1.00, 2.00 bps
```

These tolerance results are diagnostics only. M7B must not promote the best tolerance into the frozen kernel.

## 10. EXIT threshold sensitivity

M7B reports, without selecting a replacement threshold:

```text
LONG EXIT RCI9: 75.0, 77.5, 78.333333333333, 80.0, 82.5
SHORT EXIT RCI9: -82.5, -80.0, -77.5, -75.0, -72.5
```

The frozen kernels remain `78.333333333333` and `-75.0` regardless of the same-window sensitivity result.

## 11. Jackknife audit

For each frozen kernel, M7B removes one genuine target event at a time and recomputes recall on the remaining target events without refitting any condition.

This is a stability diagnostic only. It does not create leave-one-out thresholds and does not authorize formula selection.

## 12. M7C PASS / BLOCKED contract

`PASS` authorizes only prospective shadow reproduction in M7C.

M7B may return `PASS` only when all of the following hold:

1. stored and derived strict EMA ordering agree on every eligible IDLE decision;
2. `KERNEL-L1` and `KERNEL-S1` each have all-scope event recall of at least `0.70`;
3. each PRIMARY directional kernel matches at least one genuine event in each ticker where that ticker has positive support;
4. neither PRIMARY directional kernel collides with another genuine event class;
5. neither directional kernel increases no-event false positives relative to its RCI9-only core;
6. a directional kernel may miss at most one additional genuine event relative to its core;
7. `EXIT-L0` and `EXIT-S0` each have all-scope event recall of at least `0.70`;
8. all causal, observation-window, source-event, and safety checks pass.

`PASS` does not approve:

- historical full-CSV scanning;
- M5, H1, or other-timeframe extraction;
- an entry gate;
- Discord delivery;
- MT5 orders;
- live-ready status;
- a final signal.

Any failed condition returns `BLOCKED` with explicit reasons.

## 13. Outputs

The runner writes only derived audit files:

```text
latest_frozen_trigger_kernel_validation.json
latest_frozen_trigger_event_audit.csv
latest_frozen_trigger_false_positives.csv
latest_frozen_trigger_event_collisions.csv
latest_frozen_trigger_false_positive_clusters.csv
latest_frozen_trigger_cross_symbol.csv
latest_frozen_trigger_sensitivity.csv
latest_frozen_trigger_ema_residuals.csv
latest_frozen_trigger_jackknife.csv
```

SQLite and MT5 CSV inputs are read-only.

## 14. Runtime implementation

Implementation:

```text
scripts/mochipoyo_alert_research/frozen_trigger_kernel_validation.py
```

The script must import and reuse M7A causal decision construction rather than rebuilding an incompatible all-bar mapper.

## 15. Safety state

The following remain false:

```text
entry_gate_enabled
historical_scan_approved
cross_timeframe_scan_approved
discord_send
mt5_order
live_ready
final_signal
```

The generated proxy remains an independent approximation and must not be named or presented as the original proprietary Mochipoyo condition.
