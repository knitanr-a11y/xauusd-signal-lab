GOLD V2 Core/Tier2 audit-only evaluator requires two intermediate cluster-ledger CSV files:

  abc_stack_cap_2025_fold4_cluster_ledger.csv
  abc_stack_cap_2026_cluster_ledger.csv

These files are not stored in GitHub because they are generated audit outputs.

Preparation:

1. Download this archive from the ChatGPT answer:

   gold_v2_ABC_stack_cap_2025_2026_validation_outputs.zip

2. Extract it to:

   Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs\

3. Confirm these two files exist inside that folder:

   Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs\abc_stack_cap_2025_fold4_cluster_ledger.csv
   Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs\abc_stack_cap_2026_cluster_ledger.csv

4. Then run:

   scripts\gold_v2_runtime\bat\01_RUN_CORE_TIER2_AUDIT_ONLY.bat

This workflow is audit-only. It does not call AI, Discord, MT5 order APIs, or live hooks.
