from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from stage260_e7_detector import detect_e7_batch, detect_e7_streaming, E7StreamingDetector
from stage260_live_replay_contract import assert_batch_streaming_parity


def synthetic_context() -> pd.DataFrame:
    times = pd.date_range('2025-01-01', periods=1200, freq='5min')
    rows = []
    prev = 100.0
    for i, t in enumerate(times):
        o = prev
        c = o + 0.02 * np.sin(i / 10)
        h = max(o, c) + 0.1
        l = min(o, c) - 0.1
        tv = 100.0
        if i == 1150:
            o, c, h, l, tv = 100, 102, 102.05, 99.95, 300
        if i == 1151:
            o, c, h, l, tv = 102, 102.5, 102.55, 101.95, 110
        rows.append({
            'time': t,
            'source_close_time': t + pd.Timedelta(minutes=5),
            'decision_time': t + pd.Timedelta(minutes=5),
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'tick_volume': tv,
            'h1_atr14': 10.0,
            'h1_atr_band': 'P40_60',
            'h4_atr_band': 'P40_60',
        })
        prev = c
    raw = pd.DataFrame(rows)
    detector = E7StreamingDetector()
    enriched = []
    for row in raw.to_dict('records'):
        features = detector._features(row)
        enriched.append({**row, **features})
        detector._insert_histories(row, features)
        detector.prev_close = float(row['close'])
        detector.prev_bar_close = float(row['close'])
        detector.last_time = pd.Timestamp(row['time'])
        detector.bar_index += 1
    return pd.DataFrame(enriched)


class TestE7Detector(unittest.TestCase):
    NUMERIC = [
        'anchor_open', 'anchor_close', 'anchor_h1_atr14', 'tick_volume',
        'slot_median_volume', 'slot_volume_ratio', 'slot_volume_percentile',
        'global_volume_percentile', 'body_ratio', 'tr_ratio',
    ]

    def test_batch_streaming_parity(self):
        context = synthetic_context()
        raw = context.drop(columns=[
            'server_slot', 'm5_tr', 'tr_median_288', 'slot_median_volume',
            'slot_volume_percentile', 'global_volume_percentile', 'slot_volume_ratio',
        ])
        _, batch = detect_e7_batch(context)
        _, stream, _ = detect_e7_streaming(raw)
        result = assert_batch_streaming_parity(batch, stream, numeric_columns=self.NUMERIC)
        self.assertEqual(result['status'], 'PASS')

    def test_restart_invariance(self):
        raw = synthetic_context().drop(columns=[
            'server_slot', 'm5_tr', 'tr_median_288', 'slot_median_volume',
            'slot_volume_percentile', 'global_volume_percentile', 'slot_volume_ratio',
        ])
        detector = E7StreamingDetector()
        for row in raw.iloc[:1151].to_dict('records'):
            detector.on_bar(row)
        restored = E7StreamingDetector.from_snapshot(detector.snapshot())
        for row in raw.iloc[1151:].to_dict('records'):
            restored.on_bar(row)
        _, full, _ = detect_e7_streaming(raw)
        result = assert_batch_streaming_parity(
            full, restored.event_frame(), numeric_columns=self.NUMERIC,
        )
        self.assertEqual(result['status'], 'PASS')

    def test_invalid_before_acceptance_emits_nothing(self):
        context = synthetic_context()
        raw = context.drop(columns=[
            'server_slot', 'm5_tr', 'tr_median_288', 'slot_median_volume',
            'slot_volume_percentile', 'global_volume_percentile', 'slot_volume_ratio',
        ]).copy()
        raw.loc[1151, ['open', 'close', 'high', 'low']] = [102, 100.5, 102.1, 100.4]
        _, events, _ = detect_e7_streaming(raw)
        self.assertEqual(len(events), 0)


if __name__ == '__main__':
    unittest.main()
