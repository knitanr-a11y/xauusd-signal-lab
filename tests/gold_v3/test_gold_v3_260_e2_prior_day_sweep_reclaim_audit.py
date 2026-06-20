from __future__ import annotations

import importlib.util
import tempfile
import unittest
import sys
from pathlib import Path

import pandas as pd

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "gold_v3" / "gold_v3_260_e2_prior_day_sweep_reclaim_audit.py"
spec = importlib.util.spec_from_file_location("stage260_e2", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


class Stage260E2ContractTests(unittest.TestCase):
    def _event_frame(self, single_wick: bool = False) -> pd.DataFrame:
        start = pd.Timestamp("2025-03-03 10:00:00")
        times = pd.date_range("2025-03-03 11:00:00", periods=4, freq="min")
        lows = [99.4, 99.7, 100.1, 100.2]
        closes = [100.3 if single_wick else 99.8, 100.3, 100.2, 100.4]
        rows = []
        for i, t in enumerate(times):
            rows.append(
                {
                    "time": t,
                    "source_close_time": t + pd.Timedelta(minutes=1),
                    "decision_time": t + pd.Timedelta(minutes=1),
                    "open": 100.2,
                    "high": 100.5,
                    "low": lows[i],
                    "close": closes[i],
                    "session_id": 2,
                    "session_start": start,
                    "session_end_close": pd.Timestamp("2025-03-03 23:00:00"),
                    "duration_minutes": 780.0,
                    "expected_duration_from_prior_sessions": 780.0,
                    "observed_shortened_session": False,
                    "previous_session_id": 1,
                    "previous_session_high": 110.0,
                    "previous_session_low": 100.0,
                    "previous_session_start": pd.Timestamp("2025-03-02 10:00:00"),
                    "previous_session_end_close": pd.Timestamp("2025-03-02 23:00:00"),
                    "previous_session_shortened": False,
                    "h1_atr14": 10.0,
                    "h1_atr50": 9.0,
                    "h1_atr_ratio": 10 / 9,
                    "h1_atr_percentile": 0.6,
                    "atr_band": "P60_80",
                    "regime": "NORMAL",
                }
            )
        return pd.DataFrame(rows)

    def test_latest_csv_row_is_kept_and_time_is_open(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m1.csv"
            p.write_text(
                "time,open,high,low,close\n"
                "2025-01-01 00:00:00,1,2,0,1.5\n"
                "2025-01-01 00:01:00,1.5,2,1,1.8\n"
                "2025-01-01 00:02:00,1.8,2.1,1.7,2.0\n",
                encoding="utf-8",
            )
            df = mod.read_mt5_csv(p, "m1")
            self.assertEqual(len(df), 3)
            self.assertEqual(df.iloc[-1]["time"], pd.Timestamp("2025-01-01 00:02:00"))
            self.assertEqual(df.iloc[-1]["source_close_time"], pd.Timestamp("2025-01-01 00:03:00"))
            self.assertEqual(df.attrs["latest_row_contract"], "closed")

    def test_single_wick_is_not_base_event(self):
        df = self._event_frame(single_wick=True)
        events = mod.detect_e2_events(df, mod.E2Config())
        self.assertTrue(events.empty)

    def test_persistent_sweep_and_reclaim_creates_long_event(self):
        df = self._event_frame(single_wick=False)
        events = mod.detect_e2_events(df, mod.E2Config())
        self.assertEqual(len(events), 1)
        self.assertEqual(events.iloc[0]["direction"], "LONG")
        self.assertEqual(events.iloc[0]["decision_time"], pd.Timestamp("2025-03-03 11:02:00"))
        self.assertTrue(bool(events.iloc[0]["outside_close_seen"]))

    def test_mfe_mae_continue_after_sl_touch(self):
        times = pd.date_range("2025-01-02 12:00:00", periods=3, freq="min")
        m1 = pd.DataFrame(
            {
                "time": times,
                "open": [100, 95, 105],
                "high": [101, 106, 112],
                "low": [94, 93, 104],
                "close": [95, 105, 111],
            }
        )
        events = pd.DataFrame(
            [{"entry_time": times[0], "entry_price": 100.0, "direction": "LONG", "population": "EVENT"}]
        )
        paths = mod.evaluate_anchor_paths(events, m1, 3)
        self.assertEqual(paths.iloc[0]["mfe"], 12.0)
        self.assertEqual(paths.iloc[0]["mae"], 7.0)
        ft = mod.simulate_first_touch(events, m1, 3, tp=10.0, sl=5.0)
        self.assertEqual(ft.iloc[0]["result"], "SL")
        self.assertEqual(ft.iloc[0]["gross_pnl"], -5.0)

    def test_same_m1_tp_sl_is_sl_priority(self):
        t = pd.Timestamp("2025-01-02 12:00:00")
        m1 = pd.DataFrame({"time": [t], "open": [100], "high": [111], "low": [94], "close": [105]})
        events = pd.DataFrame([{"entry_time": t, "entry_price": 100.0, "direction": "LONG", "population": "EVENT"}])
        ft = mod.simulate_first_touch(events, m1, 1, tp=10.0, sl=5.0)
        self.assertEqual(ft.iloc[0]["result"], "SL")

    def test_session_boundary_uses_gap_over_15_minutes(self):
        times = [
            pd.Timestamp("2025-01-01 10:00"),
            pd.Timestamp("2025-01-01 10:01"),
            pd.Timestamp("2025-01-01 10:20"),
        ]
        m1 = pd.DataFrame(
            {
                "time": times,
                "source_close_time": [t + pd.Timedelta(minutes=1) for t in times],
                "open": [1, 1, 1],
                "high": [2, 2, 2],
                "low": [0, 0, 0],
                "close": [1, 1, 1],
            }
        )
        marked, cal = mod.build_session_calendar(m1, 15)
        self.assertEqual(marked["session_id"].nunique(), 2)
        self.assertEqual(len(cal), 2)

    def test_htf_merge_uses_only_closed_source(self):
        m1 = pd.DataFrame(
            {
                "time": [pd.Timestamp("2025-01-01 10:29")],
                "source_close_time": [pd.Timestamp("2025-01-01 10:30")],
                "open": [1], "high": [1], "low": [1], "close": [1],
                "session_id": [1],
            }
        )
        h1 = pd.DataFrame(
            {
                "source_close_time": [pd.Timestamp("2025-01-01 10:00"), pd.Timestamp("2025-01-01 11:00")],
                "h1_atr14": [8.0, 99.0],
                "h1_atr50": [8.0, 99.0],
                "h1_atr_ratio": [1.0, 1.0],
                "h1_atr_percentile": [0.5, 1.0],
                "atr_band": ["P40_60", "P80_100"],
            }
        )
        regime = pd.DataFrame(
            {
                "regime_time": [pd.Timestamp("2025-01-01 10:00")],
                "regime": ["NORMAL"],
                "regime_source_close_time": [pd.Timestamp("2025-01-01 10:00")],
            }
        )
        out = mod.causal_merge_context(m1, h1, regime)
        self.assertEqual(out.iloc[0]["h1_atr14"], 8.0)

    def test_source_parity_joins_by_timestamp_not_row_number(self):
        times = pd.date_range("2025-01-01", periods=3, freq="min")
        a = pd.DataFrame({"time": times, "open": [1, 2, 3], "high": [2, 3, 4], "low": [0, 1, 2], "close": [1.5, 2.5, 3.5]})
        b = a.iloc[::-1].reset_index(drop=True)
        result = mod.source_parity(a, b, "m1")
        self.assertTrue(result["pass"])
        self.assertEqual(result["exact_timestamp_overlap"], 3)

    def test_fixed_horizon_dedup_enforces_one_active_setup(self):
        events = pd.DataFrame(
            {
                "entry_time": [
                    pd.Timestamp("2025-01-01 10:00"),
                    pd.Timestamp("2025-01-01 10:30"),
                    pd.Timestamp("2025-01-01 12:00"),
                ]
            }
        )
        out = mod.dedup_fixed_horizon(events, 120)
        self.assertEqual(len(out), 2)

    def test_matched_control_requires_locked_exact_strata(self):
        event_time = pd.Timestamp("2025-01-08 10:00")
        events = pd.DataFrame([
            {
                "pair_id": 7, "entry_time": event_time, "weekday": event_time.weekday(),
                "server_hour": 10, "atr_band": "P40_60", "regime": "NORMAL",
                "direction": "LONG", "quarter": "2025Q1",
                "h1_atr_percentile": 0.5, "penetration_atr": 0.1
            }
        ])
        pool = pd.DataFrame([
            {
                "entry_time": pd.Timestamp("2025-01-15 10:00"), "weekday": event_time.weekday(),
                "server_hour": 10, "atr_band": "P40_60", "regime": "NORMAL",
                "direction": "LONG", "quarter": "2025Q1",
                "h1_atr_percentile": 0.52, "distance_to_level_atr": 0.12,
                "population": "MATCHED_CONTROL_POOL"
            },
            {
                "entry_time": pd.Timestamp("2025-01-15 11:00"), "weekday": event_time.weekday(),
                "server_hour": 11, "atr_band": "P40_60", "regime": "NORMAL",
                "direction": "LONG", "quarter": "2025Q1",
                "h1_atr_percentile": 0.5, "distance_to_level_atr": 0.1,
                "population": "MATCHED_CONTROL_POOL"
            }
        ])
        matched, unmatched = mod.match_controls(events, pool)
        self.assertEqual(len(matched), 1)
        self.assertEqual(len(unmatched), 0)
        self.assertEqual(matched.iloc[0]["server_hour"], 10)
        self.assertEqual(matched.iloc[0]["pair_id"], 7)

    def test_empty_placebo_population_is_safe(self):
        empty = pd.DataFrame()
        out = mod.add_live_safe_flags(empty, mod.E2Config(), 120)
        self.assertTrue(out.empty)


if __name__ == "__main__":
    unittest.main()
