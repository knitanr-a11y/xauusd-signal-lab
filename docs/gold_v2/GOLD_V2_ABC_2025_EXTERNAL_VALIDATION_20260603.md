# GOLD V2 ABC 2025 external validation

Created: 2026-06-03
Status: audit-only / not runtime approved

## Critical conclusion

The fixed ABC composition does **not** pass 2025 external validation as-is when Candidate A is allowed to use uncapped same-direction stacking.

The reconstructed 2025 universe creates large simultaneous stacks that produce unacceptable tail losses.

This does not necessarily invalidate the 2026 ABC audit, but it reveals that runtime ABC must include a hard stack cap or an explicit 2025-tested universe selection layer before live adoption.

## Method

- Used uploaded 2025 MT5 GOLD# candles.
- Applied the already-selected GOLD V2 TOP2_PER_ORIGIN fixed rule universe to 2025 candles.
- To avoid duplicate overstacking across different 2026 folds, each fold-specific 26-rule universe was evaluated separately.
- Candidate A/B/C thresholds were frozen; no 2025 tuning was applied.
- This is a reconstructed external stress check, not a full original discovery re-run.

## ABC as originally defined: A uncapped stack

| Ruleset | Count | Win rate | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| fold4_rules | 200 | 63.00% | 2.11 | +466.73R | -43.0R | 63.38R |
| fold2_rules | 163 | 58.28% | 1.60 | +195.26R | -38.0R | 104.34R |
| fold3_rules | 227 | 49.78% | 1.53 | +231.95R | -23.0R | 69.56R |
| fold1_rules | 169 | 42.60% | 1.19 | +50.35R | -22.0R | 87.40R |

This is not acceptable for runtime because the worst-loss tail is too large.

## Safety variant: ABC entry gate but all kept signals capped at CAP3

| Ruleset | Count | Win rate | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| fold4_rules | 200 | 66.00% | 2.33 | +176.24R | -3.0R | 13.29R |
| fold2_rules | 163 | 58.28% | 1.91 | +101.26R | -3.0R | 11.88R |
| fold3_rules | 227 | 52.86% | 1.44 | +93.12R | -3.0R | 24.80R |
| fold1_rules | 169 | 44.97% | 1.24 | +31.56R | -3.0R | 23.51R |

This is much safer. The best fold4 version is weaker than the 2026 ABC audit, but it is realistic and does not carry the -40R class tail.

## Current judgement

```text
ABC without stack cap:
  Reject for runtime. 2025 tail risk is too large.

ABC entry gate + hard stack cap/CAP3 sizing:
  Viable candidate for further validation.

Candidate A:
  Still useful as an entry-selection gate, but not as unlimited stacking.

Candidate B/C:
  Promising, but C still needs fixed forward validation.
```

## Required next step

Freeze a risk-controlled variant and rerun 2025 and 2026 side-by-side with identical sizing:

```text
A/B/C entry gate
+ max stack cap
+ no unlimited same-direction stack
+ fixed thresholds
```

Only after that should this move toward demo/runtime integration.
