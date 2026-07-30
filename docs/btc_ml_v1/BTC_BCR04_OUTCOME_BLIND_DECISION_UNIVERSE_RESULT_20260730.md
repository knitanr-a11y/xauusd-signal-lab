# BTC BCR04 — outcome-blind decision universe and control windows result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `READY_OUTCOME_BLIND_DECISION_UNIVERSE_AND_CONTROL_WINDOWS`
- outcome interpretation: not performed
- candidate formula: not designed

## 1. Frozen inputs

- BCR02 package SHA256: `5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`
- accepted M7C package SHA256: `870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`
- BTC M15 path: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- preregistration commit: `3c08b558c3a3067d89e72a96c320120cb013cbb9`

The distance bins, age bins, quantile probabilities, rolling horizons, gap policy and Track B capability probes were committed before the actual feature-comparison output was inspected.

## 2. Decision universe

The theoretical BTC M15 decision grid is:

- start: `2026-07-20T15:00:00Z`
- end: `2026-07-30T01:30:00Z`
- frequency: 15 minutes
- rows: `907`
- unique decision times: `907`

Every BCR02 BTC source event maps once:

- source event rows: `76`
- non-event control rows: `831`
- state-before replay parity: exact
- event rows at a gap boundary: `0`

## 3. Event and control classes

| class | rows |
|---|---:|
| `PRIMARY_LONG_EVENT` | 16 |
| `PRIMARY_SHORT_EVENT` | 10 |
| `VALID_LONG_EXIT_EVENT` | 17 |
| `VALID_SHORT_EXIT_EVENT` | 10 |
| `REENTRY_EVENT` | 11 |
| `OPPOSITE_EVENT_IGNORED` | 12 |
| `IDLE_NON_EVENT_CONTROL` | 440 |
| `ACTIVE_LONG_NON_EVENT_CONTROL` | 223 |
| `ACTIVE_SHORT_NON_EVENT_CONTROL` | 168 |

Primary entry events are therefore compared against IDLE controls, not against controls from incompatible source states.

## 4. Gap handling

The theoretical grid contains two explicit gap-adjacent rows:

1. `2026-07-25T07:15:00Z`: current server-open `10:15` is missing.
2. `2026-07-25T07:30:00Z`: current `10:30` exists, but exact previous `10:15` is missing.

Both rows are retained. Neither is a source event. Neither is core-feature eligible.

- current-bar missing rows: `1`
- exact previous-bar missing rows: `1`
- core-feature-eligible rows: `905`
- interpolation: none
- nearest/last-observed fallback: none

M7C itself selected `10:00` for the `10:30` decision. That selected-bar behavior is recorded separately in the BCR03 gap addendum; BCR04 does not copy it into the exact-boundary research universe.

## 5. M7C feature parity

Two parity statements are intentionally separated:

### M7C selected-bar content parity

Using each M7C row's recorded `selected_server_open`:

- RCI9: `890 / 890`
- EMA20-minus-EMA30 bps: `890 / 890`
- EMA30-minus-EMA40 bps: `890 / 890`

### Exact previous-boundary parity

For rows where the exact previous M15 boundary exists:

- eligible proxy rows: `889`
- RCI9: `889 / 889`
- EMA20-minus-EMA30 bps: `889 / 889`
- EMA30-minus-EMA40 bps: `889 / 889`

The one excluded proxy row is the documented 30-minute gap bridge. This distinction does not weaken content provenance; it prevents a hidden gap fallback from entering the BTC research contract.

## 6. Causal feature universe

BCR04 contains features computed only from fully closed M15 bars and current M15 open:

- RCI9, RCI14, RCI18 and turn flags;
- EMA20, EMA30, EMA40, alignment, separation and slopes;
- fixed-horizon closed returns;
- ATR14, ATR50 and ratio;
- fixed-horizon realized volatility;
- Bollinger width;
- previous closed candle body/range/wicks;
- current-open gap from previous close;
- rolling high/low location;
- source state, state age and event distance;
- broker-server hour/day;
- explicit gap flags.

Current M15 high, low and close are not used.

## 7. Preregistered quantile boundaries

Population: all `905` core-feature-eligible rows.

### ATR14

- Q20: `85.1057142857142`
- Q40: `119.29928571428577`
- Q60: `138.01571428571407`
- Q80: `179.80571428571432`

### Bollinger width 20, bps

- Q20: `45.19366026664046`
- Q40: `70.2417849976455`
- Q60: `88.25279598722646`
- Q80: `131.35765669735275`

### Realized volatility 32, bps

- Q20: `9.385502139897904`
- Q40: `12.576403193622218`
- Q60: `15.047986159792703`
- Q80: `18.75867952339954`

These are outcome-blind strata boundaries, not profitability thresholds.

## 8. Track B capability probes

Counts within the 907-row source interval:

- bullish trend-pullback probe: `56`
- bearish trend-pullback probe: `64`
- lowest-quintile compression probe: `181`
- 20-bar current-open breakout up: `2`
- 20-bar current-open breakout down: `1`
- absolute EMA20 distance at least 1.5 ATR14: `220`

These counts show data density only. No Track B family is selected. In particular, the three breakout rows are too sparse in this short source interval to support a candidate conclusion.

## 9. Reproduction assets

Extended package:

- file: `BCR04_OUTCOME_BLIND_DECISION_UNIVERSE_20260730.zip`
- SHA256: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- generator script SHA256: `f22c5fb0e5c1a7421d2f54342d2961f7ba9b4bd16f29d0f30b52c9f6c466a51d`

GitHub core reproducer:

- `scripts/btc_ml_v1/BCR04_outcome_blind_decision_universe/python/run_bcr04_core_reproduction.py`
- commit: `4f6140752f44815cf30132a99a56b79c5bae7e80`
- local verified SHA256: `ceb6f974e42516e7328688cd4e7a2e0c4fc2b7e7955b295690320aaf2170e65b`

Tests:

- `tests/btc_ml_v1/test_bcr04_outcome_blind_decision_universe_core.py`
- commit: `2821c94bec0e83af26b15dbc09214c3cdc9e04fa`
- result: `2 passed`, plus an actual frozen-input core run.

## 10. Decision

BCR04 passes.

It establishes a valid denominator for source-fidelity research. It does not establish profitability and does not authorize WR, PF, DD, MFE, MAE, TP/SL optimization, FF06, shadow, Discord or MT5 order actions.

The next Track A stage may compare primary source events with compatible IDLE controls under a frozen outcome-blind analysis contract. Formula selection and outcome evaluation remain separate later gates.
