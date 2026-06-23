from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
RUNTIME=Path(__file__).resolve().parents[2]/"scripts"/"gold_v3_runtime"
sys.path.insert(0,str(RUNTIME))
from gold_v3_290_base_health import health_for

def test_base_health_uses_exit_time_not_entry_order():
    history=pd.DataFrame([{"candidate_key":"A","exit_dt":pd.Timestamp("2026-01-02"),"pnl":1.0},{"candidate_key":"A","exit_dt":pd.Timestamp("2026-01-10"),"pnl":-5.0}])
    before=health_for("A",pd.Timestamp("2026-01-05"),history)
    after=health_for("A",pd.Timestamp("2026-01-11"),history)
    assert before[2]==1
    assert after[2]==2
