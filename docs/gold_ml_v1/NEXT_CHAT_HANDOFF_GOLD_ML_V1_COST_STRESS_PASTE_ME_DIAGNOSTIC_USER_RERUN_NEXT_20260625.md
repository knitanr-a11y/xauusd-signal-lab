# GOLD_ML_V1 diagnostic handoff

Status: `GOLD_ML_V1_019_COST_STRESS_PASTE_ME_DIAGNOSTIC_USER_RERUN_READY_AUDIT_ONLY`

The one-click launcher now records console output, removes stale diagnostics before each run, keeps the window open, and opens `PASTE_ME_GOLD_ML_V1.txt` in Notepad after the run.

Launcher revision: `PASTE_ME_V2_20260625`

Generated files:

- `PASTE_ME_GOLD_ML_V1.txt`
- `outputs/gold_ml_v1/next_action/PASTE_ME_GOLD_ML_V1.txt`
- `outputs/gold_ml_v1/next_action/FULL_CONSOLE_LOG.txt`
- `outputs/gold_ml_v1/next_action/LATEST_NEXT_ACTION.txt`
- `outputs/gold_ml_v1/next_action/DISPATCHER_BOOTSTRAP_ERROR.txt`
- `outputs/gold_ml_v1/cost_stress_raw_reconstructed/LATEST_RUN_SUMMARY.txt`
- `outputs/gold_ml_v1/cost_stress_raw_reconstructed/COST_STRESS_RUN_ERROR.txt`

If Python or the dispatcher cannot start, the root BAT creates a minimal paste-me file and includes the dispatcher bootstrap error. No stale paste-me file may be reused.

No candidate, grid, gate, period, or execution switch changed.

Next: Pull in GitHub Desktop, double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`, then paste the full Notepad contents.
