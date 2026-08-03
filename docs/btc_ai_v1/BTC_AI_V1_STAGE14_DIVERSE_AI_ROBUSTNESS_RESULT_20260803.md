# BTC AI V1 Stage 14 — Diverse AI Robustness Result

Date: 2026-08-03  
Status: `COMPLETE_EXPLORATORY_SURVIVORS_FROZEN`

All controls used the same **24-calendar-month** development trades.

- Shortlist: 4.
- Month-bootstrap pass: 2/4.
- Matched-random pass: 4/4.
- Pseudo-state pass: 4/4.
- Parameter-neighborhood pass: 4/4.
- All controls pass: 2/4.

| Candidate | AI | Trades/24m | Trades/month | Dev PF | Bootstrap net+ | PF p05 | All gates |
|---|---|---:|---:|---:|---:|---:|---|
| `ML3_070` | EXTRA_D8 | 240 | 10.00 | 1.4819 | 0.9970 | 1.1640 | PASS |
| `ML3_011` | XGB_D3 | 349 | 14.54 | 1.2982 | 0.9880 | 1.0644 | PASS |
| `ML3_068` | EXTRA_D8 | 356 | 14.83 | 1.1524 | 0.8850 | 0.9460 | FAIL |
| `ML3_107` | RANK_ENSEMBLE | 387 | 16.12 | 1.1817 | 0.9305 | 0.9852 | FAIL |

Frozen exploratory survivors: `ML3_070` and `ML3_011`. Classification ceiling: `EXPLORATORY_PROSPECTIVE_ONLY`; no untouched support remains.
