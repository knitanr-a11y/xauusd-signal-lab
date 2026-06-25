from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/gold_ml_v1/cost_stress"))

from cost_stress_contract import BRIDGE
from cost_stress_engine import recover_risk
from cost_stress_reports import bridge_candidate_summary, bridge_trade_audit


class CoreRegistryFixTests(unittest.TestCase):
    def test_risk_fallback(self) -> None:
        row = pd.Series({"r_value": 0.25, "candidate_id": "T", "entry_time": "2026-01-01"})
        self.assertEqual(recover_risk(row, 2.5), 2.5)

    def test_bridge_core_report(self) -> None:
        frame = pd.DataFrame({
            "candidate_id": ["GML1-PROV-010", "GML1-PROV-010"],
            "lineage_id": ["H1_D1_BREAKOUT_FILTER_LINEAGE", "H1_D1_BREAKOUT_FILTER_LINEAGE"],
            "decision_close_time": pd.to_datetime(["2023-01-04 01:00:00", "2023-01-05 01:00:00"]),
            "entry_time": pd.to_datetime(["2023-01-04 01:00:00", "2023-01-05 01:00:00"]),
            "exit_time": pd.to_datetime(["2023-01-04 02:00:00", "2023-01-05 02:00:00"]),
            "r_value": [1.0, -1.0],
            "direction": ["LONG", "LONG"],
            "trade_core_source": [BRIDGE, BRIDGE],
        })
        audit = bridge_trade_audit(frame)
        summary = bridge_candidate_summary(audit)
        self.assertEqual(summary.iloc[0]["stress_gate_status"], "NOT_ELIGIBLE_AUDIT_ONLY")
        self.assertEqual(summary.iloc[0]["trade_count"], 2)

    def test_bat_folder(self) -> None:
        action = json.loads((ROOT / "config/gold_ml_v1/next_local_action.json").read_text(encoding="utf-8"))
        self.assertIn("/windows/", action["runner"])


if __name__ == "__main__":
    unittest.main()
