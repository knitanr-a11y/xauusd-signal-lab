# GML1 live Discord and MT5 execution v1

Date: 2026-06-29  
Scope: the four existing live-capable sleeves only

- `A_CORE / GML1-WATCH-022-C`
- `B_STATE / GML1-H1D1-STATEFUL-REENTRY24-C`
- `P18 / GML1-PROV-018-APPROX`
- `W024A / GML1-WATCH-024-A`

P16 and P19 remain historical-only. Their frozen historical exclusion times are never used for new decisions.

## What this stage adds

The existing closed-bar candidate runtime is unchanged. The one-shot runner now attaches a separate delivery/execution cycle after the candidate registry has been written.

For each newly accepted candidate, the adapter can:

1. send one Discord entry message;
2. display the candidate sleeve's historical automatic-execution win rate and sample count;
3. display the candidate sleeve's realized live-MT5 win rate and closed-order count;
4. send one current-market MT5 order with ATR-derived server-side SL and TP;
5. enforce one position per sleeve and a total GML1 position limit;
6. force a market close at the sleeve's wall-clock horizon if SL or TP has not already closed the order;
7. send a Discord exit message after the actual MT5 position is confirmed closed.

The adapter never sends an order at the old historical M1 entry price. If a candidate is observed after the configured entry-lag limit, it is recorded as `SKIPPED_STALE`.

## Win-rate definitions

### Historical automatic-execution win rate

Source files:

```text
outputs/gold_ml_v1/research_challenger_local_runtime/
  research_challenger_local_2024.csv
  research_challenger_local_2025.csv
  research_challenger_local_2026.csv
```

Rows are grouped by `comp`, so A_CORE, B_STATE, P18 and W024A each receive a separate value. A historical trade is a win when its resolved `r` is greater than zero. The displayed period is 2024 through the available 2026 partial snapshot.

The value is calculated from the local frozen replay output rather than copied into notification code. By default, a missing or invalid historical output blocks an MT5 order with `SKIPPED_WIN_RATE_UNAVAILABLE`; the notification reports `N/A`.

### Realized live-MT5 win rate

Source:

```text
outputs/gold_ml_v1/live_research_challenger/live_execution_ledger.csv
```

The result is candidate-sleeve specific. A closed actual MT5 position is a win when:

```text
profit + commission + swap + fee > 0
```

Dry-run rows and signal-only rows are not counted as live trades.

## Files/.env

The adapter reads only:

```text
MT5 MQL5\Files\.env
```

A webhook is detected through any of these names:

- `GML1_DISCORD_WEBHOOK_URL`
- `GML1_DISCORD_WEBHOOK`
- `DISCORD_WEBHOOK_URL`
- `DISCORD_WEBHOOK`
- `WEBHOOK_URL`
- `WEBHOOK`

No webhook, password, login or other secret is written to logs or committed to the repository.

The repository example is:

```text
scripts/gold_ml_v1/live_research_challenger/live_execution.env.example
```

## Safe activation order

### 1. Discord only

A webhook in `Files\.env` enables Discord automatically unless `GML1_DISCORD_ENABLED=false` is set. Keep:

```text
GML1_MT5_ORDER_ENABLED=false
```

The first adapter run registers existing candidate rows as `INITIALIZED_NO_BACKFILL`; it sends no old notification and no old order.

### 2. MT5 dry-run

Add the symbol and positive volume for every sleeve, then use:

```text
GML1_MT5_ORDER_ENABLED=true
GML1_MT5_DRY_RUN=true
```

A new candidate is recorded as `DRY_RUN`. No `order_send` call occurs.

### 3. Real orders

Real orders require all of the following:

```text
GML1_MT5_ORDER_ENABLED=true
GML1_MT5_DRY_RUN=false
GML1_MT5_LIVE_CONFIRM=I_UNDERSTAND_THIS_SENDS_REAL_MT5_ORDERS
GML1_MT5_SYMBOL=<the broker's exact gold symbol>
```

A positive global volume or positive sleeve-specific volumes must also exist. Missing or invalid values produce `CONFIG_ERROR`; no order is sent.

The default total GML1 position limit is one. A hedging account is required by default so the four sleeves remain independently traceable. This can be changed only through the explicit `.env` controls.

## Duplicate and recovery controls

- Candidate identity is frozen as `candidate_key`.
- Every candidate is written once to `live_execution_ledger.csv`.
- MT5 magic numbers are deterministic per sleeve.
- MT5 comments contain a deterministic candidate-key digest.
- Before a new order, the adapter checks the ledger, open MT5 positions and recent MT5 deal history.
- A pipeline lock prevents two one-shot runners from advancing candidate state or entering the delivery/order section simultaneously.
- If the terminal changes an order comment, a unique open position with the sleeve magic is recovered rather than duplicated.

## Outputs

```text
outputs/gold_ml_v1/live_research_challenger/
  live_execution_state.json
  live_execution_ledger.csv
  live_execution_audit.jsonl
  live_pipeline.lock               # transient only
  latest_status.json
```

The existing `live_candidates.csv`, `live_state.json` and candidate-audit outputs remain authoritative for candidate detection. Execution records do not rewrite candidate history.

## Current validation boundary

Code-level tests cover fail-closed settings, candidate-specific historical win rates, no-backfill initialization, stale-candidate rejection, Discord idempotency, order idempotency, horizon close, live win-rate update, partial time-exit tracking and management of an already-open position after new entries are disabled.

This stage is not considered production-verified until the user's Windows/MT5 environment has completed:

1. Discord-only delivery;
2. MT5 dry-run on a fresh market-open candidate;
3. broker symbol, lot-step, stop-distance and filling-mode verification;
4. a deliberately small separately authorized real-order test;
5. entry, SL/TP or time-exit, deal-history and Discord-exit reconciliation.

Do not claim that market-open real-order verification has passed before those observations exist.
