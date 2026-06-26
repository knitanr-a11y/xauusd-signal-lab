# GOLD_ML_V1 overextension pruning audit — 2026-06-26

Status: `AUDIT_COMPLETE_NO_PROMOTION`

## Contract

- CSV time was treated as MT5 server bar-open time.
- M15 decisions used `time + 15 minutes`.
- Higher-timeframe data was available only after bar close.
- Entry used the exact M1 open at decision close.
- Same-M1 collision used SL priority.
- 2023 was used for model, gate and two-feature exclusion selection.
- 2024 and 2025 were fixed external evaluation; 2026 was diagnostic.
- The existing nine were unchanged.

## LONG

The selected 2023 OOF gate produced 41 trades, 61.0% win rate and PF 1.563. A two-feature exclusion increased the retained 2023 OOF result to 31 trades, 74.2% win rate and PF 2.875.

The exclusion failed externally. The rows it removed were profitable in 2024 and 2026. After pruning:

- 2024: 130 trades, 51.5%, PF 1.027
- 2025: 98 trades, 50.0%, PF 0.995
- 2026 diagnostic: 39 trades, 35.9%, PF 0.560

Verdict: reject the LONG pruning rule.

## SHORT

The selected 2023 OOF gate produced 84 trades, 53.6% win rate and PF 1.180. The two-feature exclusion removed 20 rows with an 80% non-win rate and improved the retained 2023 OOF result to 64 trades, 64.1% win rate and PF 1.852.

The excluded subset remained negative in the fixed external periods: -2R in 2024, -6R in 2025 and 0R in the 2026 diagnostic. However, the retained strategy remained weak:

- 2024: 95 trades, 47.4%, PF 0.890
- 2025: 126 trades, 42.9%, PF 0.761
- 2026 diagnostic: 25 trades, 52.0%, PF 1.083

Verdict: the SHORT loss pattern generalized weakly, but it cannot rescue the parent strategy and is not activated.

## Decision

- Existing nine unchanged.
- Active new candidates remain zero.
- No pruning rule activated.
- Health gate, live-ready, MT5 and Discord remain OFF.
