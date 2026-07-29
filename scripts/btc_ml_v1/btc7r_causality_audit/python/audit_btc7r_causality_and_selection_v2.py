from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ORIGINAL = Path(__file__).with_name("audit_btc7r_causality_and_selection.py")

spec = importlib.util.spec_from_file_location("_btc_ff03_original_v1", ORIGINAL)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load FF03 original implementation: {ORIGINAL}")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

_original_calculate_metrics = module.calculate_metrics


def _calculate_metrics_with_candidate(reproduction, frame):
    metric_input = frame.copy()
    if not metric_input.empty and "candidate" not in metric_input.columns:
        metric_input["candidate"] = module.CANDIDATE_ID
    return _original_calculate_metrics(reproduction, metric_input)


module.calculate_metrics = _calculate_metrics_with_candidate

if __name__ == "__main__":
    raise SystemExit(module.main())
