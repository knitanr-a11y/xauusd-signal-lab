from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config/btc_ai_v1/stage55_dual_reverse_short_shadow_contract_20260804.json"
MODEL = ROOT / "config/btc_ai_v1/m1_cp30_logistic_q70_bootstrap_model_202608.json"


class Stage55ShadowContractTest(unittest.TestCase):
    def test_observation_only_flags(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        auth = contract["authorization"]
        self.assertTrue(auth["prospective_shadow"])
        self.assertTrue(auth["observation_only"])
        self.assertFalse(auth["discord"])
        self.assertFalse(auth["mt5_order"])
        self.assertFalse(auth["live_trading"])
        self.assertFalse(auth["automatic_promotion"])

    def test_frozen_model_checksum(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        expected = contract["candidate_families"][0]["detector"]["model_artifact_sha256"]
        self.assertEqual(hashlib.sha256(MODEL.read_bytes()).hexdigest(), expected)

    def test_exact_m1_fail_closed(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["time_contract"]["m1_gap"], "INVALIDATE_CANDIDATE")
        self.assertEqual(contract["activation"]["mode"], "NO_BACKFILL")


if __name__ == "__main__":
    unittest.main()
