# Mochipoyo Alert Research — Objective Clarification

Date: 2026-07-22
Branch: `feature/mochipoyo-alert-research`
Mode: audit-only

## User-confirmed objective

The final objective is **not limited to an exact clone of Mochipoyo alerts**.

The priorities are:

1. Do not miss supported Mochipoyo source alerts.
2. Additional independent proxy alerts are acceptable.
3. The preferred improvement is to keep useful additional alerts while removing or suppressing losing additional alerts.
4. Matched Mochipoyo source alerts must not be silently removed by an outcome gate unless a later, separately approved shadow study explicitly evaluates that possibility.

Canonical machine-readable contract:

`config/mochipoyo_alert_research/objective_coverage_plus_value_add_20260722.json`

## Meaning for current M7C

M7C remains a frozen prospective baseline and must continue unchanged.

Do not:

- refit the M7B/M7C formulas during collection;
- reset or recreate the valid runtime manifest;
- restart the valid sample from zero;
- reinterpret every unmatched proxy signal as an automatic system failure;
- use future outcomes to modify the current M7C formulas.

The current categories must be interpreted as follows:

- `SOURCE_MATCHED`: coverage of a supported Mochipoyo event.
- `MISSED_SOURCE`: a primary coverage defect.
- `EXTRA_CANDIDATE`: an allowed independent candidate, not yet proven profitable.

M7C still needs enough forward events to measure the coverage anchor. Extra signals remain separate and are not automatically accepted for use.

## Required post-M7C sequence

### M8A — Coverage gap audit

Investigate missed supported source events. Candidate extensions must use only information available at the decision time. The priority is recall, not profit fitting.

### M8B — Extra-signal outcome audit

Freeze extra-signal timestamps before outcome evaluation. Then measure future outcomes with costs. Do not tune and claim performance on the same sample.

### M8C — Extra loss-reduction gate shadow

Build a gate for `EXTRA_CANDIDATE` signals only. Its purpose is to reject poor extras while preserving source-alert coverage. Keep it audit-only and forward-test it before any acceptance.

### M8D — Incremental portfolio review

Compare:

- source-anchor signals only;
- source-anchor plus all extras;
- source-anchor plus accepted extras after the loss-reduction gate.

Report at minimum signal count, win rate, PF after costs, net profit, drawdown, and maximum losing streak.

## Handoff requirement

Every future handoff must state clearly:

- exact Mochipoyo cloning is not the final objective;
- source-event coverage is the primary anchor;
- extra alerts are allowed but must be evaluated separately;
- the loss-reduction gate initially applies only to extras;
- current M7C remains frozen until its forward review is complete;
- numbered operator run files and required upload files must be listed upfront.

## Safety state

- audit-only: ON
- formula refit during M7C: OFF
- Discord send: OFF
- MT5 order: OFF
- live-ready: OFF
- final signal: OFF
