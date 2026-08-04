from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "btc_ai_v1"))

from stage55_discord_notifier import entry_message, initialize_state, target_price  # noqa: E402


class Stage55DiscordTest(unittest.TestCase):
    def test_addendum_authorizes_delivery_only(self):
        contract = json.loads(
            (ROOT / "config" / "btc_ai_v1" / "stage55_discord_entry_alert_addendum_20260804.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(contract["authorization"]["discord_entry_notification"])
        self.assertFalse(contract["authorization"]["mt5_order"])
        self.assertFalse(contract["relationship_to_frozen_shadow_contract"]["candidate_rules_changed"])

    def test_entry_message_contains_manual_review_levels(self):
        event = {
            "family": "M1_FALSE_LONG_REVERSAL_SHORT",
            "source_decision_time": "2026-08-04 10:00:00",
            "alert_time": "2026-08-04 10:30:00",
            "confirmation_time": "2026-08-04 10:35:00",
            "entry_time": "2026-08-04 10:35:00",
            "entry_price": 100.0,
            "stop_price": 110.0,
            "max_minutes": 240,
            "detector_score": 0.8,
            "detector_threshold": 0.7,
        }
        self.assertEqual(target_price(event), 80.0)
        message = entry_message(event)
        self.assertIn("SHORT", message)
        self.assertIn("Entry", message)
        self.assertIn("SL", message)
        self.assertIn("TP 2R", message)
        self.assertIn("実注文なし", message)

    def test_first_notifier_start_baselines_existing_entries(self):
        ledger = pd.DataFrame({"candidate_key": ["M1|a", "M5|b"]})
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state = initialize_state(state_path, ledger, pd.Timestamp("2026-08-04 12:00:00"))
            self.assertEqual(state["baseline_candidate_keys"], ["M1|a", "M5|b"])
            self.assertEqual(state["sent_candidate_keys"], [])


if __name__ == "__main__":
    unittest.main()
