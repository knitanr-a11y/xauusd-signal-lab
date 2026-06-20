from __future__ import annotations

import unittest
import pandas as pd

from stage260_e6_detector import (
    E6StreamingDetector,
    detect_e6_batch,
    detect_e6_streaming,
)
from stage260_live_replay_contract import assert_batch_streaming_parity


def context_from_bars(bars):
    times = pd.date_range('2025-01-01 00:00', periods=len(bars), freq='15min')
    rows = []
    prev = None
    for i, (o, h, l, c) in enumerate(bars):
        tr = max(h - l, abs(h - prev) if prev is not None else h - l, abs(l - prev) if prev is not None else h - l)
        rows.append({
            'time': times[i],
            'source_close_time': times[i] + pd.Timedelta(minutes=15),
            'decision_time': times[i] + pd.Timedelta(minutes=15),
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'm15_tr': tr,
            'h1_atr14': 10.0,
            'h1_atr_band': 'P40_60',
            'h4_atr_band': 'P40_60',
        })
        prev = c
    return pd.DataFrame(rows)


class TestE6(unittest.TestCase):
    def test_long_anchor_failed_to_short_same_bar(self):
        bars = [
            (100, 103, 99, 103), (103, 106, 102, 106), (106, 110, 105, 110),
            (110, 111, 101, 101),
        ]
        ctx = context_from_bars(bars)
        _, failures, events, _ = detect_e6_streaming(ctx)
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events.iloc[0].direction, 'SHORT')
        self.assertEqual(events.iloc[0].failure_type, 'INVALID_CLOSE_65')

    def test_no_entry_before_failure(self):
        bars = [
            (100, 103, 99, 103), (103, 106, 102, 106), (106, 110, 105, 110),
            (110, 111, 108, 109), (109, 110, 107, 108), (108, 109, 106, 107),
        ]
        ctx = context_from_bars(bars)
        _, failures, events, _ = detect_e6_streaming(ctx)
        self.assertEqual(len(failures), 0)
        self.assertEqual(len(events), 0)

    def test_failure_then_acceptance_next_bar(self):
        bars = [
            (100, 103, 99, 103), (103, 106, 102, 106), (106, 110, 105, 110),
            (110, 111, 104, 105), (105, 106, 101, 101),
        ]
        ctx = context_from_bars(bars)
        _, failures, events, _ = detect_e6_streaming(ctx)
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(pd.Timestamp(events.iloc[0].decision_time), ctx.iloc[4].decision_time)

    def test_original_reclaim_cancels(self):
        bars = [
            (100, 103, 99, 103), (103, 106, 102, 106), (106, 110, 105, 110),
            (110, 111, 104, 105), (105, 109, 104, 109),
        ]
        ctx = context_from_bars(bars)
        _, _, events, det = detect_e6_streaming(ctx)
        self.assertEqual(len(events), 0)
        self.assertTrue(any(r['resolution'] == 'ORIGINAL_DIRECTION_RECLAIMED' for r in det.resolutions))

    def test_batch_streaming_parity(self):
        bars = [
            (100, 103, 99, 103), (103, 106, 102, 106), (106, 110, 105, 110),
            (110, 111, 104, 105), (105, 106, 101, 101),
            (101, 103, 100, 102), (102, 104, 101, 103),
        ]
        ctx = context_from_bars(bars)
        _, _, batch = detect_e6_batch(ctx)
        _, _, stream, _ = detect_e6_streaming(ctx)
        result = assert_batch_streaming_parity(
            batch,
            stream,
            numeric_columns=['anchor_start_price', 'anchor_end_price', 'anchor_move', 'anchor_atr14', 'efficiency'],
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(batch.iloc[0].failure_type, stream.iloc[0].failure_type)
        self.assertEqual(batch.iloc[0].original_direction, stream.iloc[0].original_direction)

    def test_restart_invariance(self):
        bars = [
            (100, 103, 99, 103), (103, 106, 102, 106), (106, 110, 105, 110),
            (110, 111, 104, 105), (105, 106, 101, 101),
        ]
        ctx = context_from_bars(bars)
        detector = E6StreamingDetector()
        for _, bar in ctx.iloc[:4].iterrows():
            detector.on_bar(bar)
        restored = E6StreamingDetector.from_snapshot(detector.snapshot())
        for _, bar in ctx.iloc[4:].iterrows():
            restored.on_bar(bar)
        _, _, full, _ = detect_e6_streaming(ctx)
        result = assert_batch_streaming_parity(
            full,
            restored.event_frame(),
            numeric_columns=['anchor_start_price', 'anchor_end_price', 'anchor_move', 'anchor_atr14', 'efficiency'],
        )
        self.assertEqual(result['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
