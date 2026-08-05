# BTC AI V1 — Source Acceptance and Fixed Cost Contract

Date: 2026-08-03  
Research: `BTC_AI_CANDIDATE_RESEARCH_V1`  
Branch: `feature/btc-ai-v1-data-acquisition`

## Formal status

`BTC_AI_V1_SOURCE_ACCEPTED_FIXED_COST_FROZEN_RESEARCH_DESIGN_NEXT`

## Accepted source snapshot

Symbol: `BTCUSD#`

Broker metadata:

- company: `Tradexfin Limited`
- server: `XMTrading-MT5 3`
- description: `Bitcoin vs US Dollar`
- digits: `2`
- point/tick size: `0.01`
- tick value: `0.01 USD`
- contract size: `1 BTC per 1.0 lot`
- time: MT5 broker-server naive time
- bars: fully closed only

| TF | Rows | First | Last | SHA256 |
|---|---:|---|---|---|
| M1 | 1,879,776 | 2023-01-01 00:00 | 2026-08-03 03:02 | `c33e9ecc258f01ee8959f9d6b219ba1c5047a0c1f2ab99683054398400e87135` |
| M5 | 376,123 | 2023-01-01 00:00 | 2026-08-03 02:55 | `325c8a39776415b5abf59dca940d1d36733f8726f6c6d7e3171fdce8c6aa8bb0` |
| M15 | 125,567 | 2023-01-01 00:00 | 2026-08-03 02:45 | `8df8d24f2dd14df71545324b30784f8fcd00dd82ee90caf7e5c389c58b9751b6` |
| H1 | 31,443 | 2023-01-01 00:00 | 2026-08-03 02:00 | `7c04ec467399f00d89c19a59491aef91a4ce54ac834c3edc0c122501ed2306e4` |
| H4 | 7,860 | 2023-01-01 00:00 | 2026-08-02 20:00 | `94c2013dc175e340b3d22e229383863ba699aad224ea14d3e6fda90bc857a7d0` |
| D1 | 1,310 | 2023-01-01 00:00 | 2026-08-02 00:00 | `8485e0249e6320c66cc43efd1ad90f86913eee6ea98e177fc684b4d0f4760c73` |

Supporting files:

- `export_manifest.csv`: `a1177b058477fe0157879d7fd9793ad83ed679dc01efc2c268b29ff071073a58`
- `symbol_metadata.csv`: `47bc080d821e6e525415a4ccc3108aaab10c96dc5541838cd8df43468f9a3ce7`

## Source audit

The following checks passed:

- all manifest and metadata symbol fields are `BTCUSD#`;
- no timestamp duplicates or reversal;
- no null cells or OHLC invariant violations;
- BTC price range: 16,453.03 through 126,178.45 USD;
- no row in the earlier GOLD price band;
- M1 reaggregation reproduces every provided M5, M15, H1, H4 and D1 row exactly for OHLC, tick volume, minimum spread and real volume;
- the one additional M1-derived bar for each higher timeframe is an unfinished final bucket and is correctly absent from the closed-bar export.

The earlier GOLD exports are not part of this source manifest and are not authorized BTC inputs.

## Gap policy

The broker source contains absent minute intervals.

- no interpolation;
- no fabricated bars;
- no forward fill;
- a future exact-M1 execution contract must fail closed when a required interval is unavailable;
- gap handling cannot be changed after candidate results are seen.

## Frozen research cost

User-authorized primary spread cost:

`22.50 USD per BTC, once per completed 1.0-lot trade`

Equivalent: `2,250 points` at `0.01 USD` per point.

Primary execution representation:

- LONG adjusted entry = raw executable M1 open + 22.50 USD;
- SHORT adjusted entry = raw executable M1 open - 22.50 USD.

For realized one-lot PnL this is equivalent to subtracting 22.50 USD once from gross directional price PnL.

The CSV spread column remains available for audit, but it is not used for candidate selection or the primary performance result.

Not modeled:

- economic-event spread expansion;
- commission;
- slippage;
- swap.

All conclusions must explicitly state that they apply to this fixed-cost contract. A different cost requires a new dated preregistration before rerunning affected evaluations.

## Research boundary

No candidate discovery has started.

Next stage: `BTC_AI_V1_01_RESEARCH_DESIGN_PREREGISTRATION`

Before outcome inspection, the next stage must freeze the research objective, period split, causal features, exact-M1 execution, gap handling, multiple-testing control, robustness gates and reporting outputs.

## Safety

- old BTC BCR is audit history only;
- no GOLD V19, Challenger C1 or P75 modification;
- no Discord or MT5 orders;
- no live-ready or final signal;
- no candidate promotion.
