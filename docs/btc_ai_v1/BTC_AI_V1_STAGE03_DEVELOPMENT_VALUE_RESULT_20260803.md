# BTC AI V1 Stage 03 — Development Value Result

Date: 2026-08-03  
Status: `COMPLETE_DEVELOPMENT_VALUE_RESULT_FINAL_TEST_STILL_LOCKED`

## Evaluation contract

- development only: 2024-01-01 through 2025-12-31
- fixed spread: 22.50 USD per completed 1 BTC trade
- M15 closed-bar decision; exact M1 next-open entry and exact M1 exit
- same-M1 TP/SL collision: SL first
- missing/gapped M1 before resolution or horizon: invalid and excluded
- one open position per candidate
- execution grid: 4 stop multipliers × 4 R targets × 4 horizons
- untouched final test beginning 2026-01-01: not opened

## Result

- capability survivors evaluated: 300
- execution configurations evaluated: 19,200
- configurations passing all development gates: 20
- base candidates with at least one passing configuration: 9
- shortlist count: 9

All nine development survivors belong to `BREAKOUT_COMPRESSION_EXPANSION` and are SHORT definitions. This is a development result, not permission to delete LONG globally or to declare a deployable SHORT-only strategy.

## Frozen development shortlist

| Rank | Candidate | Side | Structural parameters | Stop ATR | Target R | Horizon min | Trades | PF | Net USD | DD USD | Positive folds | Worst fold PF |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `BRE_SHORT_041` | SHORT | {"body": 0.6, "compression": 1.0, "expansion": 1.1, "htf": "H1_H4", "window": 20} | 1.50 | 3.0 | 480 | 151 | 1.3301 | +12156.04 | 6337.05 | 4 | 1.1528 |
| 2 | `BRE_SHORT_051` | SHORT | {"body": 0.6, "compression": 1.0, "expansion": 1.7, "htf": "ANY", "window": 20} | 1.50 | 3.0 | 720 | 406 | 1.1519 | +16473.13 | 9085.09 | 4 | 1.0061 |
| 3 | `BRE_SHORT_047` | SHORT | {"body": 0.6, "compression": 1.0, "expansion": 1.35, "htf": "H1_H4", "window": 20} | 1.50 | 3.0 | 480 | 132 | 1.3435 | +11451.16 | 5536.99 | 3 | 0.9938 |
| 4 | `BRE_SHORT_033` | SHORT | {"body": 0.6, "compression": 0.8, "expansion": 1.7, "htf": "ANY", "window": 20} | 1.50 | 3.0 | 720 | 202 | 1.2570 | +12067.91 | 5993.43 | 3 | 0.9414 |
| 5 | `BRE_SHORT_052` | SHORT | {"body": 0.6, "compression": 1.0, "expansion": 1.7, "htf": "H1", "window": 20} | 1.50 | 3.0 | 480 | 170 | 1.2790 | +12159.61 | 3912.64 | 3 | 0.9340 |
| 6 | `BRE_SHORT_046` | SHORT | {"body": 0.6, "compression": 1.0, "expansion": 1.35, "htf": "H1", "window": 20} | 1.50 | 3.0 | 480 | 216 | 1.1692 | +9204.30 | 7825.03 | 3 | 0.9055 |
| 7 | `BRE_SHORT_030` | SHORT | {"body": 0.35, "compression": 0.8, "expansion": 1.7, "htf": "ANY", "window": 20} | 1.50 | 3.0 | 720 | 253 | 1.1573 | +9081.34 | 8848.77 | 3 | 0.8813 |
| 8 | `BRE_SHORT_044` | SHORT | {"body": 0.35, "compression": 1.0, "expansion": 1.35, "htf": "H1_H4", "window": 20} | 1.50 | 3.0 | 480 | 160 | 1.2231 | +9104.38 | 6712.44 | 3 | 0.8236 |
| 9 | `BRE_SHORT_049` | SHORT | {"body": 0.35, "compression": 1.0, "expansion": 1.7, "htf": "H1", "window": 20} | 1.50 | 3.0 | 480 | 204 | 1.2445 | +12592.58 | 4556.49 | 3 | 0.8201 |

## Interpretation

The first development signal is concentrated in a narrow mechanism:

- downside break of the prior 20-M15-bar low;
- preceding ATR compression threshold;
- current range expansion and bearish body threshold;
- optional H1/H4 bearish alignment;
- 1.5 ATR stop and 3R target;
- 480 or 720 minute maximum holding.

This concentration raises a material overfitting/redundancy concern. No 2026 result will be inspected until the robustness controls and finalist registry are frozen.

## Output hashes

- full development grid: `825c69c0d433be531aebec20f3d49a0c65db1e9b0ad6406c2a3a430e5af7919a`
- shortlist: `95e2117517be524e647595d3d6a6cf7334218c1bad8b9893d09e0a1ef6609365`
