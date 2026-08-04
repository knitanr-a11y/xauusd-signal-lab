# BTC AI V1 — H4 day-open causal loss-cooldown audit

Date: 2026-08-05  
branch: `feature/btc-day-open-loss-cooldown-audit`  
preregistration commit: `8a7fe42ce8a8bd308b511647054394fc5c3f3a48`

## Formal conclusion

`BTC_AI_V1_DAY_OPEN_LOSS_COOLDOWN_NO_VARIANT_PASSED_ALL_FROZEN_GATES`

The frozen +0.25ATR-lock parent was not modified. Five causal cooldown rules based only on already resolved strategy outcomes were run once. No rule passed every frozen gate because none improved win rate by the required 2 points. One rule passed every other economic, temporal, robustness, direction, concentration, retention, and loss-selectivity gate.

## Formal period 2024–2026 July

| Configuration | Trades | Retained | Win rate | PF | Net USD | Max DD | Net/DD | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Skip next two episodes after full stop | 1,018 | 75.0% | 56.58% | 1.328 | +88,877.90 | 19,595.14 | 4.536 | REJECT |
| Skip next episode after full 4ATR stop | 1,155 | 85.1% | 56.62% | 1.304 | +96,324.73 | 18,014.22 | 5.347 | REJECT |
| Wait next broker day after full stop | 1,113 | 82.0% | 56.60% | 1.288 | +88,545.88 | 15,671.79 | 5.650 | REJECT |
| Control +0.25ATR lock | 1,357 | 100.0% | 56.67% | 1.225 | +85,951.14 | 18,996.77 | 4.525 | CONTROL |
| Skip next episode after any net loss | 948 | 69.9% | 56.75% | 1.207 | +57,158.62 | 21,328.84 | 2.680 | REJECT |
| Skip next after two consecutive net losses | 1,195 | 88.1% | 56.82% | 1.182 | +62,345.03 | 24,741.27 | 2.520 | REJECT |

## Strong near-pass: skip one episode after a full 4ATR stop

- Trigger only after `INITIAL_SL` or `INITIAL_SL_GAP_OPEN`.
- Skip exactly the next desired-state episode; remain flat until the following state flip.
- Uses no price-pattern, direction, month, year, session, or volatility filter.

- Trades: 1,155 (85.1% retained)
- Win rate: 56.62% (-0.05 points versus parent)
- PF: 1.304
- Net: +96,324.73 USD
- Max DD: 18,014.22 USD
- Net/DD: 5.347
- Largest-winner-removed PF: 1.264
- Double-cost PF: 1.214
- LONG PF: 1.218; SHORT PF: 1.416

### Year results

| Period | PF | Net USD |
|---|---:|---:|
| 2024 | 1.187 | +22,970.40 |
| 2025 | 1.287 | +37,599.56 |
| 2026 Jan–Jul | 1.570 | +35,754.77 |

It passed every frozen gate except the required +2 percentage-point win-rate improvement. Win rate was essentially unchanged, but loss severity and drawdown improved materially.

## Matched skipped-episode selectivity

| Rule | Formal loss capture | Formal profit sacrificed | Edge | 2025 edge | 2026 edge |
|---|---:|---:|---:|---:|---:|
| Skip next episode after full 4ATR stop | 17.11% | 11.75% | +5.36pt | +0.87pt | +4.40pt |
| Skip next episode after any net loss | 27.73% | 28.79% | -1.06pt | -0.71pt | -14.62pt |
| Skip next after two consecutive net losses | 10.08% | 13.27% | -3.19pt | -1.05pt | +2.16pt |
| Wait next broker day after full stop | 19.61% | 15.45% | +4.16pt | -3.34pt | +9.71pt |
| Skip next two episodes after full stop | 29.04% | 23.08% | +5.96pt | -6.38pt | +24.21pt |

The one-episode cooldown after a full stop captured 17.11% of control loss dollars while sacrificing 11.75% of control profit dollars. The selectivity advantage was positive in both 2025 and 2026. This is stronger and more temporally stable than the static entry flags, but it does not improve the percentage win rate.

## Other cooldown findings

- Skipping after every net loss overreacted and removed too much profitable recovery.
- Waiting until the next broker day improved DD but had inconsistent loss selectivity between 2025 and 2026.
- Skipping two episodes after a full stop produced PF 1.328 but failed the frozen DD limit and had negative selectivity in 2025.
- Waiting for two consecutive losses failed 2024 and reduced total economics.

## Causality and parity audit

- Raw H4 events: 7,647
- Completed trades across six configs: 9,270
- Unresolved: 0
- Parent control parity: 1,885 versus 1,885 trades, exact match
- Independent Python/Numba parity all pass
- Synthetic tests all pass
- Cooldown uses only already resolved prior trades.
- At a state flip, old trade close and net result are finalized before the new episode decision.
- Skipped episodes have no synthetic outcomes and no same-state delayed re-entry.
- Future/open/as-of use: 0; exact M1 no fallback.
- Parent candidate and Stage55 were not modified.

## Boundary and recommendation

- No cooldown replaces the frozen parent on retrospective data alone.
- No Fresh Shadow was created.
- The one-episode-after-full-stop rule is retained as a strong post-hoc economic lead, not a formal win-rate improvement.
- For prospective work, avoid adding both static filters and cooldown simultaneously. A clean matched-pair should compare the frozen +0.25ATR-lock parent against exactly this one cooldown rule.
