# GOLD V3 Stage297 — future-valid pooled REV parity correction

## Evidence

The audited Stage280 metrics describe one REV classifier, not a LONG-only classifier.
For the 2026 walk-forward row, REV base rate is about 4.05%; earlier unseen years are about 4.8-4.9%.

With the exact future-valid population:

- fit_n = 4974
- cal_n = 1809

The LONG-only target produced only 75 fit positives (1.51%), which cannot represent the audited REV model.
The previously observed pooled REV target produced 245 fit positives, giving 4.93%, consistent with the audit metrics.

## Authoritative Stage280 training contract

- retain H4 non-neutral rows only;
- require a valid complete 240-minute future M1 adjudication window;
- predicted REV direction is `-h4_trend`;
- positive target is event onset in that predicted REV direction;
- normalize signed returns, slopes, EMA distances, candle bodies and price positions into predicted REV direction;
- swap upper/lower wick sides for SHORT normalization;
- fit 2024-01-01 through 2025-06-30;
- calibrate 2025-07-01 through 2025-12-31;
- require fit_n=4974, cal_n=1809 and positive_fit=245 before threshold/fixture parity can pass.

Stage281 remains unchanged because its threshold and fixture score already match exactly.

## Local-version marker

The current training report `expected` section includes:

`"stage280_positive_fit": 245`

If this field is absent, the local checkout is running an older Stage280 implementation.
