# BTC BCR05A — label-derived event-distance incident and correction

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `PRE_ACCEPTANCE_OUTPUT_INVALIDATED_CORRECTION_REQUIRED`
- outcomes opened: false

## 1. Incident

The first local BCR05A comparison output included:

`distance_to_nearest_source_event_bin=EVENT`

as an inferential feature in family E.

Every primary source event is definitionally in the `EVENT` bin, while every non-event control is not. The variable therefore separated event and control rows perfectly without describing a market trigger.

This is label-derived self-identification. It is not an outcome leak, but it is invalid as source-trigger evidence and invalid as a future candidate feature.

The pre-acceptance local package SHA256 was:

`838dc8cacdcb086302cfa48f3a5818fdbc7e2ac61c041337381be57df996dcdb`

It is rejected and must not be cited as a BCR05A result.

## 2. Broader availability distinction

BCR04 contains variables with different roles:

### Candidate-causal market variables

- closed-bar indicators and price context;
- current open;
- broker-server hour and day;
- explicit data-gap flags known at the boundary.

### Source-fidelity context

- source state;
- source-state age;
- distance to a previous genuine source event;
- distance to a next source event;
- nearest source-event distance.

Source-fidelity context is useful for explaining M7C/source state paths, but it is not automatically available to an independent future BTC candidate. A later candidate may use its own proxy-state age only after that state machine is frozen and parity-tested.

### Label-derived or future source-event variables

- current row's `EVENT` membership;
- distance to the next source event;
- nearest-event distance when it depends on a future event.

These may be used to construct descriptive strata, but never as trigger-signature predictors or shortlist evidence.

## 3. Correction

BCR05A v1.0.1 must:

1. remove nearest-event-distance levels from inferential feature tests;
2. exclude source-event-derived state-age variables from candidate-feature shortlist ranking;
3. retain those variables only in a clearly labeled fidelity-context descriptive output;
4. permit family E shortlist evidence only from broker hour/day and boundary-known gap flags;
5. rerun FDR because the family-E test set changed;
6. preserve the prior RCI9 anchor and all other frozen tests;
7. continue to prohibit outcomes, profitability, threshold search and final formula construction.

## 4. Impact

No profitability data was opened. No candidate was promoted. No FF06 or runtime was created.

The incident was detected before the first BCR05A output was accepted into current state or handoff. The corrected output alone may become authoritative.
