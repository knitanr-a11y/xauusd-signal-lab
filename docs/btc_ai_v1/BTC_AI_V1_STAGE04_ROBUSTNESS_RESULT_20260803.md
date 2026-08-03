# BTC AI V1 Stage 04 — Robustness Controls Result

Date: 2026-08-03  
Status: `COMPLETE_NO_ROBUST_FINALIST_FINAL_TEST_REMAINS_LOCKED`

## Input

Nine frozen development survivors from Stage 03. No candidate definition, direction, fixed spread, stop, target, horizon, month, or session rule was changed.

The exact control construction was frozen in `config/btc_ai_v1/robustness_control_protocol_20260803.json` before control outputs were computed.

## Formal controls

- 2,000 calendar-month block bootstrap iterations
- 2,000 matched-random iterations preserving month, direction and event count
- 2,000 monthly cyclic pseudo-state shifts preserving monthly count and event clustering
- one-step parameter-neighborhood test
- +1 and +5 minute entry delays as diagnostics only

## Result

- development shortlist: 9
- all robustness gates passed: 0
- frozen finalists: 0
- 2026 untouched final test opened: no

| Candidate | Dev PF | Bootstrap net+ prob | Bootstrap PF p05 | Random net pct | Random PF pct | Pseudo net pct | Pseudo PF pct | Neighbor positive share | Failed controls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `BRE_SHORT_041` | 1.3301 | 0.9765 | 1.0659 | 0.9475 | 0.9785 | 0.9625 | 0.9515 | 0.75 | matched-random |
| `BRE_SHORT_051` | 1.1519 | 0.8900 | 0.9591 | 0.9855 | 0.9910 | 0.9870 | 0.9845 | 0.75 | bootstrap |
| `BRE_SHORT_047` | 1.3435 | 0.9505 | 1.0009 | 0.9480 | 0.9690 | 0.9630 | 0.9520 | 0.75 | matched-random |
| `BRE_SHORT_033` | 1.2570 | 0.9240 | 0.9598 | 0.9720 | 0.9845 | 0.9660 | 0.9735 | 0.50 | bootstrap |
| `BRE_SHORT_052` | 1.2790 | 0.9370 | 0.9823 | 0.9715 | 0.9800 | 0.9715 | 0.9640 | 0.75 | bootstrap |
| `BRE_SHORT_046` | 1.1692 | 0.8160 | 0.8819 | 0.9350 | 0.9560 | 0.9440 | 0.9400 | 0.50 | bootstrap, matched-random, pseudo-state |
| `BRE_SHORT_030` | 1.1573 | 0.8595 | 0.9269 | 0.9520 | 0.9740 | 0.9430 | 0.9550 | 0.50 | bootstrap, pseudo-state |
| `BRE_SHORT_044` | 1.2231 | 0.9325 | 0.9826 | 0.9040 | 0.9530 | 0.9205 | 0.9120 | 0.50 | bootstrap, matched-random, pseudo-state |
| `BRE_SHORT_049` | 1.2445 | 0.9300 | 0.9747 | 0.9595 | 0.9775 | 0.9665 | 0.9590 | 0.75 | bootstrap |

## Gate-level findings

- parameter-neighborhood: 9/9 passed
- matched-random: 5/9 passed
- pseudo-state: 6/9 passed
- month bootstrap: 2/9 passed
- all four simultaneously: 0/9

The top development candidate `BRE_SHORT_041` passed bootstrap, pseudo-state and neighborhood, but missed the preregistered matched-random net percentile: 0.9475 versus required 0.95. The threshold is not relaxed.

`BRE_SHORT_047` similarly missed matched-random net percentile at 0.9480. It is not rescued.

## Delay diagnostics

Entry-delay tests were not formal selection gates. They show that several candidates remained positive at +1 and +5 minutes, while `BRE_SHORT_030` became negative at both delays and `BRE_SHORT_033` became negative at +5 minutes. These diagnostics do not authorize changing entry timing.

## Formal classification

The first candidate search cycle is classified:

`PROMISING_NOT_ROBUST_NO_FINALIST`

No candidate is opened on the untouched 2026 test. No prospective Shadow, Discord, MT5 order, live-ready status, or portfolio construction is authorized.

## Output hashes

- robustness results: `7fc368c2c30366fde7952e705414b173c808ac5bd97f8f3a4329f1026475a754`
- finalist registry: `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`
