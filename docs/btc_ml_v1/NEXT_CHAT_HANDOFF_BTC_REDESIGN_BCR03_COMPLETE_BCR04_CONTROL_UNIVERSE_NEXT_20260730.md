# NEXT CHAT HANDOFF — BTC redesign BCR03 complete, BCR04 control universe next

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:12:00+09:00`
- current status: `BTC_REDESIGN_BCR03_COMPLETE_BCR04_CONTROL_UNIVERSE_CONTRACT_FROZEN_IMPLEMENTATION_NEXT`

## 1. Startup hard gate

Read only branch `feature/btc-fresh-forward-research`.

Do not use `main`, the default branch, a similar filename, or an older handoff as current authority. Start from `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md` and follow its exact read order.

Do not start with `AGENTS.md`; it is GOLD-specific in this repository.

Do not broadly search or read GOLD V2, old GOLD, GOLD V3, GOLD_ML_V1, DISC8, Stage41, old BTC stacking/YouTube handoffs, or FF05 recovery V3–V11.

## 2. Research objective

Two separated tracks remain active:

- Track A: source-anchored BTC research using genuine M7C/Collector BTC alerts as primary evidence.
- Track B: independent-vector BTC research based on market mechanisms not dependent on the Mochipoyo RCI/state formula.

The objective is not perfect alert copying or one attractive backtest. It is a traceable candidate system covering causal design, value testing, loss control, portfolio complementarity, prospective shadow, drift monitoring and fail-closed stopping.

## 3. Runtime protection

M7C and Collector are read-only evidence sources.

Do not stop, restart, reset or modify Collector, M7C, M8C, M9, M10 or any GOLD/MOCHIPOYO runtime. Do not write BTC results back to MOCHIPOYO paths.

## 4. Completed evidence

### D1 / Collector and M7C

M7C and Collector provenance, cursor behavior, event classes and time semantics were audited. No outcome interpretation was performed.

### BCR01

Accepted outcome-blind source snapshot:

- package SHA256: `bc562948ee8baefba32d0e291a54341243da4684bdbf43d652676d5fcdab5611`
- raw IDs: `1–194`
- cursor: `194`
- outcome tables read: false

The invalid v1.0.0 schema-order error package is audit history only.

### BCR02

Canonical source event ledger:

- package SHA256: `5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`
- research rows: `131`
- BTCUSD rows: `76`
- M7C state reconstruction parity: `125 / 125`
- outcomes opened: false

### BCR02A

Outcome-blind fidelity decomposition:

- BTC primary alerts: `25`
- correct RCI turn direction: `25 / 25`
- correct EMA stack: `22 / 25`
- M7C missed primary alerts: `11`
- missed primary with prior state divergence: `9`
- primary RCI turn mismatches: `0`

This suggests path-dependent state divergence, especially exit delay/miss, must be separated from entry-trigger fidelity. It does not prove profitability.

## 5. BCR03 completed

Authoritative M15 source tuple:

- exact original path: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- path authority: user-attested exact original path
- content SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- server-open range: `2025-09-13 08:00:00` through `2026-07-30 06:15:00`
- duplicate opens: `0`
- explicit gap transitions: `47`
- implied missing M15 bars: `53`

BCR02 BTC source event mapping:

- current server-open found: `76 / 76`
- immediately previous fully closed bar found: `76 / 76`
- accepted mapping for inspected interval: MT5 server time = UTC + 3 hours

M7C feature parity from this CSV:

- RCI9: `890 / 890`
- EMA20-minus-EMA30 bps: `890 / 890`
- EMA30-minus-EMA40 bps: `890 / 890`

Causal boundary:

- fully closed M15 history allowed;
- current M15 open only allowed;
- current high/low/close forbidden;
- future bars and gap interpolation forbidden;
- HTF features forbidden until a separate as-of contract is proven.

## 6. Current next stage

`BCR04_OUTCOME_BLIND_DECISION_UNIVERSE_AND_CONTROL_WINDOWS`

The contract is frozen in:

- `docs/btc_ml_v1/BTC_BCR04_OUTCOME_BLIND_DECISION_UNIVERSE_AND_CONTROL_WINDOWS_CONTRACT_20260730.md`
- `configs/btc_ml_v1/btc_bcr04_outcome_blind_decision_universe_contract_20260730.json`

BCR04 must create a complete M15 decision universe, propagate source state, retain every source event, create non-event control classes, freeze a causal feature registry and assess label-free data capability for Track B.

BCR04 is necessary because positive source events alone cannot identify a trigger signature. Controls must be formed without any future result.

## 7. BCR04 prohibitions

Do not open outcomes or calculate WR, PF, DD, MFE, MAE, TP/SL performance.

Do not select thresholds because of later profitability. Do not promote or reject a candidate. Do not create FF06, prospective shadow, Discord, MT5 order or lot design.

## 8. User action

No additional user file or BAT is required at this moment.

The next implementation task is to build and test BCR04 against the frozen BCR02 package and exact BCR03 M15 source tuple, then return the outcome-blind control-universe package for audit.

## 9. Handoff maintenance

After BCR04 implementation or result audit, update in the same work unit:

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. this dated handoff pointer
3. `btc_candidate_research_current_state_20260730.json`
4. `btc_candidate_research_next_action_20260730.json`
5. handoff policy if allowlists or prohibitions change

Fail closed on any contradiction.
