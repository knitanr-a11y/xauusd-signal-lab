# BTC AI V1 — Broad-entry / exit-first research result

Date: 2026-08-05  
Branch: `feature/btc-broad-entry-exit-first-research`  
Preregistration commit: `c4e1015baad6e7577907911c9911c4df4e6bdeed`

## Formal conclusion

`BTC_AI_V1_BROAD_ENTRY_EXIT_FIRST_ALL_FOUR_FAMILIES_REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE`

Entry confirmation, EMA, ATR-regime and session filters were removed. Four broad entry families were evaluated with three fixed exits each:

- every H1 body-sign continuation
- every H1 body-sign fade
- every H4 close versus broker-day open continuation
- every H4 close versus broker-day open fade
- 60 existing-M1 time exit with 2 ATR hard stop
- 240 existing-M1 time exit with 2 ATR hard stop
- 1 ATR stop / 2 ATR target / 720 existing-M1 maximum hold

All 12 configurations failed the preregistered cost-adjusted gates.

## Formal period 2024–2026 July

| Family | Exit | Trades | PF | Net USD |
|---|---|---:|---:|---:|
| H1 continuation | 60-minute | 22,318 | 0.832 | -534,955.89 |
| H1 continuation | 240-minute | 6,869 | 0.939 | -104,616.17 |
| H1 continuation | bracket | 11,306 | 0.843 | -346,856.43 |
| H1 fade | 60-minute | 22,327 | 0.873 | -393,009.12 |
| H1 fade | 240-minute | 6,973 | 0.965 | -59,912.58 |
| H1 fade | bracket | 10,644 | 0.910 | -184,032.41 |
| H4 day-open continuation | 60-minute | 5,655 | 0.851 | -122,162.62 |
| H4 day-open continuation | 240-minute | 5,473 | 0.948 | -70,186.78 |
| H4 day-open continuation | bracket | 5,087 | 0.889 | -105,798.72 |
| H4 day-open fade | 60-minute | 5,655 | 0.844 | -126,594.77 |
| H4 day-open fade | 240-minute | 5,490 | 0.904 | -131,498.69 |
| H4 day-open fade | bracket | 4,970 | 0.873 | -119,199.73 |

## Cost-before diagnostic

The strongest gross result was H1 body fade with a 240-minute hold:

- 6,973 trades
- gross PF 1.059
- gross average +13.91 USD per trade
- gross net +96,979.92 USD
- after the frozen 22.50 USD completed-trade cost: PF 0.965 and net -59,912.58 USD

This indicates that broad directional information was not entirely absent, but repeated event entry created too much turnover for the observed gross edge.

## Pipeline and causality

- raw configuration candidates: 233,016
- deduplicated candidates: 233,016
- one-position trades: 153,458
- resolved trades: 153,458
- unresolved trades: 0
- exact-entry M1 missing: 66 configuration rows
- exact-entry fallback: none
- same-M1 collision: SL-first
- future/open/as-of feature use: 0
- Stage55 modified: false

## Next research boundary

Do not rescue directions, hours, months, years or volatility slices. The next separate cycle retains broad state coverage but removes repeated same-direction entries: hold the desired H1/H4 state and trade only when the state flips.

No prospective Shadow is authorized. MT5 orders, live trading, live-ready, final signal, Discord and automatic promotion remain OFF.
