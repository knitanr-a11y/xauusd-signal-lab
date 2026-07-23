# MOCHIPOYO Alert Research — M8B Result / M8C Minimal Forward Hypothesis

## M8B status

`PASS_EXPLORATORY_ONLY`

The frozen M8B population remained unchanged:

- finalized extra signals: 36
- extra-entry trades used for WR/PF: 18
- extra exit actions: 18, not double-counted as trades
- pending source-arrival-grace: excluded
- frozen skeleton SHA256: `f42ce896f00b717320662ff1b64991718bf3e1ce7dfe0d671c62f362731f7acc`

Exact M1 server-time rows were required. No nearest-bar fallback or intrabar high/low/close was used. Candidate creation remained future-free; future prices were used only after the population was frozen for outcome evaluation.

## Aggregate extra-entry result

Historical spread x1.0:

- trades: 18
- wins / losses: 11 / 7
- win rate: 61.11%
- PF: 1.1233
- net: +20.27 bps
- max DD: 109.44 bps
- max losing streak: 2
- observed frequency: 6.52 trades/calendar day over this short sample

Cost sensitivity:

- spread x1.5: PF 1.0198, +3.40 bps
- spread x2.0: PF 0.9251, -13.47 bps

Therefore the all-extra branch is not yet robust enough for promotion. Commission and swap are not modeled in M8B V1, so the aggregate result must not be overstated.

## Main split

### XAUUSD extras

10 trades, WR 70%, PF 3.9251, +97.49 bps at spread x1.0.

The XAU subgroup stayed strongly positive in an exploratory spread x2 reconstruction as well. This is promising but still a small sample.

### BTCUSD extras

8 trades, WR 50%, PF 0.4107, -77.22 bps at spread x1.0.

The concentration is BTCUSD LONG:

- 6 trades
- WR 33.33%
- PF 0.1818
- -107.21 bps at spread x1.0

BTCUSD SHORT had only 2 trades and both won, so no strong claim is allowed from that tiny subgroup.

## Why M8C is deliberately minimal

The user clarified that exact Mochipoyo replication is not the final objective. The final objective is robust after-cost edge with high win rate and useful trade frequency. Therefore M8C must not stack many RCI/EMA/time filters merely to improve in-sample win rate.

M8B's 18 outcomes may generate a hypothesis but may not validate it.

Exploratory same-sample counterfactual, **not validation**:

- remove BTCUSD LONG proxy trades only
- remaining 12 trades
- WR 75%
- PF 4.8247 at spread x1.0
- +127.47 bps
- observed frequency 4.35 trades/calendar day
- spread x2.0 PF 4.2467, +114.11 bps

This large difference is sufficient to justify a narrow forward hypothesis, but it is not evidence that the rule will hold out of sample.

## M8C live-causal correction

`EXTRA_CANDIDATE` is finalized only after source-arrival grace. Therefore future EXTRA classification is forbidden as an entry-time gate input.

M8C V2 uses three conceptual branches:

1. `SOURCE_ANCHOR`: source alerts remain separate and are not suppressed by the proxy gate.
2. `CONTROL_PROXY`: accept all future proxy PRIMARY candidates.
3. `CHALLENGER_PROXY_BLOCK_BTCUSD_LONG`: at proxy decision time, reject only `BTCUSD + PRIMARY_LONG`; accept all others.

The gate uses only ticker and transition available at decision time. Later source-match/extra attribution is analysis-only and cannot change the original gate decision.

The gate is an execution-shadow overlay. It does not change the frozen M7C proxy generator's internal state or formulas.

## M8C forward review gate

Do not reuse the M8B 18 trades as validation.

Collect a new forward sample until all are present:

- total future proxy PRIMARY candidates >= 30
- future BTCUSD PRIMARY_LONG proxy candidates >= 8
- future challenger-accepted proxy candidates >= 15

Review WR, after-spread PF, net bps, DD, losing streak, frequency, accepted fraction, ticker/direction balance, and incremental value versus the separate source-anchor branch.

## Safety

Audit-only continues. Discord send, MT5 order, live-ready, final-signal and real trading entry-gate activation remain OFF. M7C formulas, thresholds, runtime manifest and prospective start remain unchanged.
