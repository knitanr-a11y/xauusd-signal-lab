# GOLD V3 Stage116 Spec — EXACT_LEDGER_BRIDGE

Created JST: `2026-06-14`

Stage116 writes `FX_OUTPUTS/gold_v3/115a/inbox/latest_signal.json` from an exact frozen ledger match only.

It does not reconstruct the 107Q detector.

Inputs:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/112c/gold_v3_112_selected_policy_freeze_manifest.json
goldsharp_m15.csv or gold#_m15.csv
```

Rule:

```text
latest closed M15 time exactly equals selected ledger entry_dt -> write LONG/SHORT latest_signal.json
otherwise -> write NO_SIGNAL latest_signal.json
```

Reason:

```text
Stage112 freezes KEEP_107Q_BASE but does not freeze a full live predicate implementation.
This bridge prevents approximate reconstruction.
```

Outputs:

```text
FX_OUTPUTS/gold_v3/116c/current/latest_bridge_status.json
FX_OUTPUTS/gold_v3/116c/journal/YYYY-MM/gold_v3_116_bridge_YYYY-MM-DD.jsonl
FX_OUTPUTS/gold_v3/116c/gold_v3_116_summary.json
FX_OUTPUTS/gold_v3/116c/paste_me.txt
FX_OUTPUTS/gold_v3/115a/inbox/latest_signal.json
```

Safety flags:

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
