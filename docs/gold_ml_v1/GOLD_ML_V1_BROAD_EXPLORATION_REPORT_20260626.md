# GOLD_ML_V1 broad exploration audit — 2026-06-26

Status: `AUDIT_COMPLETE_ZERO_60WR_PF2_EXTERNAL_SURVIVORS`

## Causal/time contract

- CSV `time` was treated as MT5 server bar-open time.
- Decisions were made only at the relevant bar close.
- H1/H4/D1 features were joined only when their `bar_close_time <= decision_time`.
- M5 confirmation entries occurred at the confirming M5 close / exact M1 open.
- Same-M1 TP/SL collision used SL priority.
- No open-bar, future high/low/close, future ATR or future higher-timeframe state was used.

## Search scale

- Seven independent families: STP, RPB, BREAK, MOM, SWEEP, EMA and SQUEEZE.
- Event parameter cells: 7,296; unique 2023 event masks: 5,920.
- Stage-2 execution variants passing the lenient 2023 gate: 14,358.
- Five entry modes, three risk definitions and seven exit profiles were tested.
- 55 candidates were frozen using 2023 only. Frozen SHA256: `11294c59d0d6fb13592749e835d445c07114144b7857b1c6a6c0a1933999c0d8`.

## Target result

| Period | Frozen candidates with >=20 resolved, WR >=60%, PF >=2 |
|---|---:|
| 2023 | 33 |
| 2024 | 0 |
| 2025 | 0 |
| 2026 diagnostic | 0 |

No candidate passed the target in both 2024 validation and 2025 final test.

## Loss-feature pruning

- Pairwise losing zones were derived from live-known entry features only.
- Rules were fitted on 2023 H1 and required non-degrading confirmation on 2023 H2.
- 21 filtered candidates were frozen. Only 1 improved both WR and PF in both 2024 and 2025.
- That one generalized filter remained far below the target: 2024 WR 51.4% / PF 1.059; 2025 WR 50.9% / PF 1.037.
- Therefore loss pruning substantially improved 2023 but mostly failed external generalization.

## Best external diagnostics — not candidates

| ID | Family | 2024 n/WR/PF | 2025 n/WR/PF | 2026 n/WR/PF | Negative months 2024/25/26 |
|---|---|---|---|---|---|
| GML1-BROAD-C-054 | SWEEP LONG | 83 / 33.7% / 1.806 | 106 / 30.2% / 1.641 | 40 / 12.5% / 0.588 | 5 / 5 / 5 |
| GML1-BROAD-C-046 | SQUEEZE LONG | 103 / 21.4% / 1.410 | 114 / 27.2% / 1.462 | 39 / 15.4% / 0.714 | 4 / 3 / 3 |
| GML1-BROAD-F-031 | SWEEP LONG | 114 / 48.2% / 1.165 | 135 / 47.4% / 1.127 | 44 / 50.0% / 1.297 | 5 / 6 / 2 |
| GML1-BROAD-F-029 | SWEEP LONG | 73 / 50.7% / 1.280 | 99 / 48.5% / 1.176 | 37 / 51.4% / 1.319 | 6 / 4 / 2 |
| GML1-BROAD-F-018 | RPB LONG | 90 / 56.7% / 1.640 | 87 / 48.3% / 1.144 | 40 / 45.0% / 0.998 | 2 / 5 / 3 |
| GML1-BROAD-U-007 | BREAK LONG | 56 / 55.4% / 1.743 | 77 / 45.5% / 1.250 | 15 / 46.7% / 1.312 | 2 / 4 / 3 |
| GML1-BROAD-C-040 | MOM LONG | 226 / 35.0% / 1.064 | 321 / 38.6% / 1.262 | 62 / 35.5% / 1.100 | 5 / 1 / 2 |
| GML1-BROAD-C-041 | MOM LONG | 259 / 34.0% / 1.023 | 364 / 38.5% / 1.246 | 74 / 31.1% / 0.902 | 6 / 2 / 2 |

The best PF-oriented diagnostic was a LONG sweep/reclaim family, but its WR was only 33.7% in 2024 and 30.2% in 2025. The best WR in 2024 was 56.7%; the best WR in 2025 was 54.8%.

## Volatility and direction findings

- High-volatility segments often outperformed low-volatility segments in the high-count momentum families, but not enough to reach the target.
- SHORT families did not generalize: the best sufficiently populated SHORT candidate had PF 0.958 in 2024 and 1.000 in 2025.
- The external diagnostic leaders were all LONG, but none met the required WR/PF combination.

## Cost stress

- Six scenarios were evaluated with exact path replay, including added spread up to 0.20 and adverse slippage up to 0.05.
- Because no candidate met the base external target, cost stress did not create an eligible candidate.
- The best PF-oriented sweep family remained above PF 1.40 in its worst 2024/2025 stress year, but its WR remained around 29%, so it is not suitable for the requested objective.

## Decision

- Existing nine candidates remain unchanged.
- Active new candidate count remains zero.
- No health gate was applied; health-gate columns equal dedup results and are explicitly marked OFF.
- `live_ready`, `final_signal`, MT5 orders, Discord, AI API and automatic promotion remain OFF.
- No further threshold or feature changes are made after viewing 2024/2025/2026. Doing so would violate the frozen-period contract.
