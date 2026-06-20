from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from stage260_e8_detector import E8StreamingDetector, detect_e8_batch, detect_e8_streaming
from stage260_live_replay_contract import assert_batch_streaming_parity

NUMERIC = [
    'anchor_open', 'anchor_high', 'anchor_low', 'anchor_close', 'anchor_range',
    'anchor_h1_atr14', 'tick_volume', 'slot_median_volume', 'slot_volume_ratio',
    'slot_volume_percentile', 'global_volume_percentile', 'body_ratio',
    'upper_wick_ratio', 'lower_wick_ratio', 'tr_ratio',
]


def make_raw(invalid: bool = False) -> pd.DataFrame:
    count = 7000
    times = pd.date_range('2025-01-01', periods=count, freq='5min')
    rows = []
    previous = 100.0
    special = 6500
    for index, time in enumerate(times):
        open_price = previous
        close = open_price + 0.01 * np.sin(index / 17)
        high = max(open_price, close) + 0.1
        low = min(open_price, close) - 0.1
        tick_volume = 100.0
        if index == special:
            open_price, close, high, low, tick_volume = 100.0, 100.2, 102.4, 99.9, 300.0
        if index == special + 1:
            if invalid:
                open_price, close, high, low, tick_volume = 100.2, 102.2, 102.3, 100.1, 110.0
            else:
                open_price, close, high, low, tick_volume = 100.2, 99.7, 100.3, 99.6, 110.0
        rows.append({
            'time': time,
            'source_close_time': time + pd.Timedelta(minutes=5),
            'decision_time': time + pd.Timedelta(minutes=5),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'tick_volume': tick_volume,
            'h1_atr14': 10.0,
            'h1_atr_band': 'P40_60',
            'h4_atr_band': 'P40_60',
        })
        previous = close
    return pd.DataFrame(rows)


def enrich_batch(raw: pd.DataFrame) -> pd.DataFrame:
    detector = E8StreamingDetector()
    rows = []
    for bar in raw.to_dict('records'):
        features = detector._features(bar)
        rows.append({**bar, **features})
        detector._insert_histories(bar, features)
        detector.prev_close = float(bar['close'])
        detector.prev_bar_close = float(bar['close'])
        detector.last_time = pd.Timestamp(bar['time'])
        detector.bar_index += 1
    return pd.DataFrame(rows)


class TestE8Detector(unittest.TestCase):
    def test_batch_streaming_parity_and_short(self) -> None:
        raw = make_raw(False)
        batch_context = enrich_batch(raw)
        _, batch = detect_e8_batch(batch_context)
        _, stream, _ = detect_e8_streaming(raw)
        result = assert_batch_streaming_parity(batch, stream, numeric_columns=NUMERIC)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(stream), 1)
        self.assertEqual(stream.iloc[0].direction, 'SHORT')

    def test_invalid_before_acceptance(self) -> None:
        raw = make_raw(True)
        _, stream, _ = detect_e8_streaming(raw)
        self.assertEqual(len(stream), 0)

    def test_restart_invariance(self) -> None:
        raw = make_raw(False)
        split = 6501
        detector = E8StreamingDetector()
        for bar in raw.iloc[:split].to_dict('records'):
            detector.on_bar(bar)
        restored = E8StreamingDetector.from_snapshot(detector.snapshot())
        for bar in raw.iloc[split:].to_dict('records'):
            restored.on_bar(bar)
        _, full, _ = detect_e8_streaming(raw)
        result = assert_batch_streaming_parity(full, restored.event_frame(), numeric_columns=NUMERIC)
        self.assertEqual(result['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
