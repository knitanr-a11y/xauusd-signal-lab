# GOLD SCALP EVENT-SEQUENCE GRAMMAR V1

Date: 2026-08-02

Formal status:

`RETROSPECTIVE_EVENT_SEQUENCE_MULTI_VECTOR_COMPLETE_NO_FORMAL_CANDIDATE`

Read in order:

1. `docs/gold_scalp_event_sequence_grammar_v1/GOLD_SCALP_EVENT_SEQUENCE_GRAMMAR_V1_AUDIT_20260802.md`
2. `config/gold_scalp_event_sequence_grammar_v1/formal_status_20260802.json`
3. `config/gold_scalp_event_sequence_grammar_v1/candidate_observation_catalog_20260802.csv`
4. `docs/gold_scalp_event_sequence_grammar_v1/REPRODUCTION_NOTE_20260802.md`

Boundaries:

- existing GOLD candle data only;
- MT5 broker-server naive time;
- spread 0.30 USD once;
- initial SL <= 5 USD;
- TP >= 5 USD;
- breakeven allowed;
- exact M1 resolution;
- one-position non-overlap;
- research only;
- no Shadow, Discord, MT5 order, live trading, promotion or merge authorization;
- frozen V19 and Challenger C1 were not modified or used as candidate inputs.

Main result:

Five event-sequence and candle-grammar vectors were completed. No profile passed the multi-block pseudo-forward candidate gate. Candidate promotion produced 22 paper observations, but no grammar both produced a positive target block and later re-qualified under the same causal calibration contract.
