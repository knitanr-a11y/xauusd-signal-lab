# GOLD V3 Stage107L Spec — REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY
```

## Purpose

Stage107K2 produced a valid regime frontier and a balanced-60 policy, but it stopped at final summary writing because of a column prefix bug.

Stage107L must continue from the generated 107K2 artifacts without treating 107K2 as a strategy failure.

The purpose is to:

1. Reconstruct the 107K2 balanced policy summary from the generated frontier when the summary CSV is missing.
2. Rehydrate the best balanced policy ledger from `gold_v3_107k2_all_regime_ledgers.csv`.
3. Verify that rehydrated metrics match the 107K2 frontier rows.
4. Check whether the ledger has `exit_dt`.
5. Run rolling health-gate simulation only if `exit_dt` is present and each history row satisfies `exit_dt <= current entry_dt`.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107k2c/gold_v3_107k2_regime_frontier.csv
FX_OUTPUTS/gold_v3/107k2c/gold_v3_107k2_all_regime_ledgers.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107k2c/gold_v3_107k2_balanced_policy_summary.csv
FX_OUTPUTS/gold_v3/107k2c/gold_v3_107k2_best_policy_regime_rows.csv
```

If optional files are missing, Stage107L must reconstruct them from the frontier.

## Selected 107K2 result to rehydrate

The current attached 107K2 frontier review selected:

```text
best_policy_key: density_safe||100||Q0.6
decision: REGIME_BALANCED_60_READY_FOR_REVIEW
```

Stage107L must not hard-code this as the only possible policy. It must calculate the best balanced policy from the available frontier. A CLI override may be used only for audit review.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime
- Stage69 runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5 execution
- AI API

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
csv_open_bar_exclusion_required=false
```

Health / rolling gate rule:

```text
Only resolved outcomes with exit_dt <= current entry_dt may enter history.
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Required output directory

```text
FX_OUTPUTS/gold_v3/107lc/
```

## Mandatory outputs

```text
gold_v3_107l_balanced_policy_summary.csv
gold_v3_107l_best_policy_regime_rows.csv
gold_v3_107l_rehydrated_best_policy_ledger.csv
gold_v3_107l_rehydration_metric_parity.csv
gold_v3_107l_exit_dt_precondition_matrix.csv
gold_v3_107l_blocker_matrix.csv
gold_v3_107l_validation_matrix.csv
gold_v3_107l_summary.json
GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY_REPORT.md
paste_me.txt
```

If `exit_dt` exists and is complete enough to run health gates, also output:

```text
gold_v3_107l_health_gate_frontier.csv
gold_v3_107l_best_health_gate_ledger.csv
gold_v3_107l_health_gate_state_ledger.csv
gold_v3_107l_health_gate_quality_gate_matrix.csv
gold_v3_107l_next_action_decision.csv
```

## Success and blocker conditions

### READY

Stage107L may be READY only when:

- 107K2 frontier exists.
- 107K2 all-regime ledger exists.
- A balanced policy can be selected.
- Rehydrated per-regime metrics match the frontier rows within tolerance.
- If health gates run, all health-gate history rows use only `exit_dt <= current entry_dt`.

### BLOCKED_INPUT_INCOMPLETE

Stage107L must be BLOCKED, not failed, when:

- `exit_dt` is missing from the selected ledger.
- `exit_dt` is present but unresolved or null for selected rows.
- Rehydration metric parity fails.
- Required 107K2 artifacts are missing.

The expected near-term blocker is:

```text
missing_exit_dt_for_resolved_only_health_gate
```

This means the balanced policy exists, but live-faithful health gating cannot proceed until a resolved-only ledger with `exit_dt` is available.

## Acceptance lens

Stage107L is not allowed to declare the system live-ready.

It may only decide one of:

```text
REGIME_REHYDRATION_READY_HEALTH_GATE_BLOCKED_EXIT_DT_REQUIRED
REGIME_REHYDRATION_AND_HEALTH_GATE_READY_FOR_107M
REGIME_REHYDRATION_METRIC_MISMATCH_BLOCKED
NO_BALANCED_POLICY_FOUND_IN_107K2_FRONTIER
```
