from __future__ import annotations

from bisect import bisect_left, bisect_right, insort
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from stage260_live_replay_contract import candidate_key
from stage260_e7_detector import prepare_e7_context_batch

STATE_VERSION = 'E8_V1'
EVENT_TYPE = 'E8_TICK_VOLUME_ABSORPTION_REJECTION'


@dataclass
class AbsorptionSetup:
    direction: str
    anchor_time: pd.Timestamp
    anchor_bar_index: int
    anchor_open: float
    anchor_high: float
    anchor_low: float
    anchor_close: float
    anchor_range: float
    anchor_h1_atr14: float
    tick_volume: float
    slot_median_volume: float
    slot_volume_ratio: float
    slot_volume_percentile: float
    global_volume_percentile: float
    body_ratio: float
    upper_wick_ratio: float
    lower_wick_ratio: float
    tr_ratio: float
    state: str = 'ABSORPTION_ACTIVE'

    @property
    def accept_level(self) -> float:
        sign = 1.0 if self.direction == 'LONG' else -1.0
        return self.anchor_close + sign * 0.03 * self.anchor_h1_atr14

    @property
    def invalid_level(self) -> float:
        if self.direction == 'SHORT':
            return self.anchor_high - 0.15 * self.anchor_range
        return self.anchor_low + 0.15 * self.anchor_range

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> 'AbsorptionSetup':
        item = dict(value)
        item['anchor_time'] = pd.Timestamp(item['anchor_time'])
        return cls(**item)


def _slot(time: pd.Timestamp) -> int:
    t = pd.Timestamp(time)
    return t.hour * 12 + t.minute // 5


def _true_range(o: float, h: float, l: float, c: float, prev_close: float | None) -> float:
    if prev_close is None or not np.isfinite(prev_close):
        return h - l
    return max(h - l, abs(h - prev_close), abs(l - prev_close))


def _rank_percentile(sorted_values: list[float], value: float) -> float:
    return bisect_right(sorted_values, float(value)) / len(sorted_values)


def _anchor_from_bar(bar: dict[str, Any] | pd.Series, bar_index: int) -> dict[str, Any] | None:
    atr = float(bar.get('h1_atr14', np.nan))
    slot_med = float(bar.get('slot_median_volume', np.nan))
    slot_pct = float(bar.get('slot_volume_percentile', np.nan))
    global_pct = float(bar.get('global_volume_percentile', np.nan))
    tr_med = float(bar.get('tr_median_288', np.nan))
    tv = float(bar.get('tick_volume', np.nan))
    o, h, l, c = map(float, [bar.get('open'), bar.get('high'), bar.get('low'), bar.get('close')])
    tr = float(bar.get('m5_tr', np.nan))
    if not all(np.isfinite(v) for v in [atr, slot_med, slot_pct, global_pct, tr_med, tv, o, h, l, c, tr]):
        return None
    bar_range = h - l
    if atr <= 0 or slot_med <= 0 or tr_med <= 0 or bar_range <= 0:
        return None
    slot_ratio = tv / slot_med
    body_ratio = abs(c - o) / bar_range
    upper = h - max(o, c)
    lower = min(o, c) - l
    upper_ratio = upper / bar_range
    lower_ratio = lower / bar_range
    tr_ratio = tr / tr_med
    if slot_ratio < 1.80 or slot_pct < 0.90 or global_pct < 0.85:
        return None
    if bar_range < 0.10 * atr or tr_ratio < 1.25 or body_ratio > 0.30:
        return None
    upper_ok = upper_ratio >= 0.55 and upper >= 1.50 * max(lower, 1e-12) and (h - c) / bar_range >= 0.45
    lower_ok = lower_ratio >= 0.55 and lower >= 1.50 * max(upper, 1e-12) and (c - l) / bar_range >= 0.45
    if upper_ok == lower_ok:
        return None
    direction = 'SHORT' if upper_ok else 'LONG'
    return {
        'direction': direction,
        'anchor_time': pd.Timestamp(bar.get('decision_time')),
        'anchor_bar_index': int(bar_index),
        'anchor_open': o,
        'anchor_high': h,
        'anchor_low': l,
        'anchor_close': c,
        'anchor_range': bar_range,
        'anchor_h1_atr14': atr,
        'tick_volume': tv,
        'slot_median_volume': slot_med,
        'slot_volume_ratio': slot_ratio,
        'slot_volume_percentile': slot_pct,
        'global_volume_percentile': global_pct,
        'body_ratio': body_ratio,
        'upper_wick_ratio': upper_ratio,
        'lower_wick_ratio': lower_ratio,
        'tr_ratio': tr_ratio,
        'h1_atr_band': str(bar.get('h1_atr_band', '')),
        'h4_atr_band': str(bar.get('h4_atr_band', '')),
    }


def _invalid(setup: AbsorptionSetup, bar: dict[str, Any] | pd.Series) -> bool:
    close = float(bar['close'])
    return close >= setup.invalid_level if setup.direction == 'SHORT' else close <= setup.invalid_level


def _accepted(setup: AbsorptionSetup, bar: dict[str, Any] | pd.Series, prev_close: float) -> bool:
    open_price, close = float(bar['open']), float(bar['close'])
    if setup.direction == 'SHORT':
        return close <= setup.accept_level and close < prev_close and close < open_price
    return close >= setup.accept_level and close > prev_close and close > open_price


def _event(setup: AbsorptionSetup, bar: dict[str, Any] | pd.Series) -> dict[str, Any]:
    t = pd.Timestamp(bar['decision_time'])
    return {
        'candidate_key': candidate_key(EVENT_TYPE, setup.direction, setup.anchor_time, t),
        'event_type': EVENT_TYPE,
        'direction': setup.direction,
        'anchor_time': setup.anchor_time,
        'decision_time': t,
        'entry_time': t,
        'entry_price_source_time': t,
        'state_version': STATE_VERSION,
        'anchor_open': setup.anchor_open,
        'anchor_high': setup.anchor_high,
        'anchor_low': setup.anchor_low,
        'anchor_close': setup.anchor_close,
        'anchor_range': setup.anchor_range,
        'anchor_h1_atr14': setup.anchor_h1_atr14,
        'tick_volume': setup.tick_volume,
        'slot_median_volume': setup.slot_median_volume,
        'slot_volume_ratio': setup.slot_volume_ratio,
        'slot_volume_percentile': setup.slot_volume_percentile,
        'global_volume_percentile': setup.global_volume_percentile,
        'body_ratio': setup.body_ratio,
        'upper_wick_ratio': setup.upper_wick_ratio,
        'lower_wick_ratio': setup.lower_wick_ratio,
        'tr_ratio': setup.tr_ratio,
        'accept_close': float(bar['close']),
        'h1_atr_band': str(bar.get('h1_atr_band', '')),
        'h4_atr_band': str(bar.get('h4_atr_band', '')),
        'weekday': int(t.weekday()),
        'server_hour': int(t.hour),
        'month': t.strftime('%Y-%m'),
        'quarter': f'{t.year}Q{t.quarter}',
        'half': f'{t.year}H{1 if t.month <= 6 else 2}',
    }


class E8StreamingDetector:
    def __init__(self) -> None:
        self.slot_values = {i: deque() for i in range(288)}
        self.slot_sorted = {i: [] for i in range(288)}
        self.global_values: deque[float] = deque()
        self.global_sorted: list[float] = []
        self.tr_values: deque[float] = deque()
        self.active: dict[str, AbsorptionSetup | None] = {'LONG': None, 'SHORT': None}
        self.events: list[dict[str, Any]] = []
        self.raw_anchors: list[dict[str, Any]] = []
        self.resolutions: list[dict[str, Any]] = []
        self.last_time: pd.Timestamp | None = None
        self.prev_close: float | None = None
        self.prev_bar_close: float | None = None
        self.bar_index = -1
        self.global_trade_active_until = pd.Timestamp.min

    @staticmethod
    def _remove_sorted(sorted_values: list[float], value: float) -> None:
        index = bisect_left(sorted_values, value)
        if index >= len(sorted_values) or sorted_values[index] != value:
            raise AssertionError('sorted history mismatch')
        sorted_values.pop(index)

    def snapshot(self) -> dict[str, Any]:
        return {
            'slot_values': {str(k): list(v) for k, v in self.slot_values.items() if v},
            'slot_sorted': {str(k): list(v) for k, v in self.slot_sorted.items() if v},
            'global_values': list(self.global_values),
            'global_sorted': list(self.global_sorted),
            'tr_values': list(self.tr_values),
            'active': {k: None if v is None else v.snapshot() for k, v in self.active.items()},
            'events': list(self.events),
            'raw_anchors': list(self.raw_anchors),
            'resolutions': list(self.resolutions),
            'last_time': self.last_time,
            'prev_close': self.prev_close,
            'prev_bar_close': self.prev_bar_close,
            'bar_index': self.bar_index,
            'global_trade_active_until': self.global_trade_active_until,
        }

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> 'E8StreamingDetector':
        detector = cls()
        for key, values in value.get('slot_values', {}).items():
            detector.slot_values[int(key)] = deque(float(v) for v in values)
        for key, values in value.get('slot_sorted', {}).items():
            detector.slot_sorted[int(key)] = [float(v) for v in values]
        detector.global_values = deque(float(v) for v in value.get('global_values', []))
        detector.global_sorted = [float(v) for v in value.get('global_sorted', [])]
        detector.tr_values = deque(float(v) for v in value.get('tr_values', []))
        detector.active = {
            key: None if value['active'].get(key) is None else AbsorptionSetup.from_snapshot(value['active'][key])
            for key in ('LONG', 'SHORT')
        }
        detector.events = list(value.get('events', []))
        detector.raw_anchors = list(value.get('raw_anchors', []))
        detector.resolutions = list(value.get('resolutions', []))
        detector.last_time = None if value.get('last_time') is None else pd.Timestamp(value['last_time'])
        detector.prev_close = value.get('prev_close')
        detector.prev_bar_close = value.get('prev_bar_close')
        detector.bar_index = int(value.get('bar_index', -1))
        detector.global_trade_active_until = pd.Timestamp(value.get('global_trade_active_until', pd.Timestamp.min))
        return detector

    def _resolve(self, direction: str, reason: str, bar: dict[str, Any]) -> None:
        setup = self.active[direction]
        if setup is None:
            return
        self.resolutions.append({
            'direction': direction,
            'anchor_time': setup.anchor_time,
            'resolution_time': pd.Timestamp(bar['decision_time']),
            'resolution': reason,
        })
        self.active[direction] = None

    def _update_state(self, direction: str, bar: dict[str, Any], gap: bool) -> bool:
        setup = self.active[direction]
        if setup is None:
            return False
        if gap:
            self._resolve(direction, 'GAP', bar)
            return True
        age = self.bar_index - setup.anchor_bar_index
        if age > 2:
            self._resolve(direction, 'EXPIRED', bar)
            return True
        if _invalid(setup, bar):
            self._resolve(direction, 'INVALID', bar)
            return True
        prev = self.prev_bar_close
        if prev is not None and _accepted(setup, bar, float(prev)):
            event = _event(setup, bar)
            if event['decision_time'] >= self.global_trade_active_until:
                self.events.append(event)
                self.global_trade_active_until = event['entry_time'] + pd.Timedelta(minutes=120)
                self._resolve(direction, 'ACCEPTED_EMITTED', bar)
            else:
                self._resolve(direction, 'ACCEPTED_DEDUP_SUPPRESSED', bar)
            return True
        return False

    def _features(self, bar: dict[str, Any]) -> dict[str, float]:
        tick_volume = float(bar['tick_volume'])
        server_slot = _slot(pd.Timestamp(bar['time']))
        slot_history = self.slot_values[server_slot]
        slot_sorted = self.slot_sorted[server_slot]
        slot_median = float(np.median(slot_history)) if len(slot_history) >= 20 else np.nan
        slot_percentile = _rank_percentile(slot_sorted, tick_volume) if len(slot_sorted) >= 20 else np.nan
        global_percentile = _rank_percentile(self.global_sorted, tick_volume) if len(self.global_sorted) >= 1000 else np.nan
        o, h, l, c = map(float, [bar['open'], bar['high'], bar['low'], bar['close']])
        true_range = _true_range(o, h, l, c, self.prev_close)
        tr_median = float(np.median(self.tr_values)) if len(self.tr_values) >= 100 else np.nan
        return {
            'server_slot': server_slot,
            'm5_tr': true_range,
            'tr_median_288': tr_median,
            'slot_median_volume': slot_median,
            'slot_volume_percentile': slot_percentile,
            'global_volume_percentile': global_percentile,
            'slot_volume_ratio': tick_volume / slot_median if np.isfinite(slot_median) and slot_median > 0 else np.nan,
        }

    def _insert_histories(self, bar: dict[str, Any], features: dict[str, float]) -> None:
        tick_volume = float(bar['tick_volume'])
        server_slot = int(features['server_slot'])
        true_range = float(features['m5_tr'])
        slot_values, slot_sorted = self.slot_values[server_slot], self.slot_sorted[server_slot]
        slot_values.append(tick_volume)
        insort(slot_sorted, tick_volume)
        if len(slot_values) > 60:
            old = slot_values.popleft()
            self._remove_sorted(slot_sorted, old)
        self.global_values.append(tick_volume)
        insort(self.global_sorted, tick_volume)
        if len(self.global_values) > 2880:
            old = self.global_values.popleft()
            self._remove_sorted(self.global_sorted, old)
        self.tr_values.append(true_range)
        if len(self.tr_values) > 288:
            self.tr_values.popleft()

    def on_bar(self, bar: pd.Series | dict[str, Any]) -> None:
        item = bar.to_dict() if isinstance(bar, pd.Series) else dict(bar)
        time = pd.Timestamp(item['time'])
        if pd.Timestamp(item['decision_time']) != pd.Timestamp(item['source_close_time']):
            raise ValueError('decision_time must equal source_close_time')
        if self.last_time is not None and time <= self.last_time:
            raise ValueError('bars not increasing')
        self.bar_index += 1
        gap = self.last_time is not None and time - self.last_time != pd.Timedelta(minutes=5)
        resolved = {direction: self._update_state(direction, item, gap) for direction in ('LONG', 'SHORT')}
        features = self._features(item)
        anchor = _anchor_from_bar({**item, **features}, self.bar_index)
        if anchor is not None:
            direction = anchor['direction']
            anchor['suppressed_active'] = self.active[direction] is not None
            anchor['suppressed_resolution_bar'] = resolved[direction]
            self.raw_anchors.append(anchor.copy())
            if self.active[direction] is None and not resolved[direction]:
                self.active[direction] = AbsorptionSetup(**{
                    key: anchor[key] for key in AbsorptionSetup.__dataclass_fields__ if key in anchor
                })
        self._insert_histories(item, features)
        self.prev_close = float(item['close'])
        self.prev_bar_close = float(item['close'])
        self.last_time = time

    def event_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.events)


def detect_e8_streaming(context: pd.DataFrame):
    detector = E8StreamingDetector()
    for bar in context.to_dict(orient='records'):
        detector.on_bar(bar)
    return pd.DataFrame(detector.raw_anchors), detector.event_frame(), detector


def detect_e8_batch(context: pd.DataFrame):
    records = context.to_dict(orient='records')
    raw = []
    for index, bar in enumerate(records):
        anchor = _anchor_from_bar(bar, index)
        if anchor is not None:
            raw.append(anchor)
    candidates = []
    active = {'LONG': None, 'SHORT': None}
    trade_until = pd.Timestamp.min
    raw_by_index = {int(anchor['anchor_bar_index']): anchor for anchor in raw}
    last_time = None
    for index, bar in enumerate(records):
        time = pd.Timestamp(bar['time'])
        gap = last_time is not None and time - last_time != pd.Timedelta(minutes=5)
        resolved = {'LONG': False, 'SHORT': False}
        for direction in ('LONG', 'SHORT'):
            setup = active[direction]
            if setup is None:
                continue
            if gap or index - setup.anchor_bar_index > 2 or _invalid(setup, bar):
                active[direction] = None
                resolved[direction] = True
                continue
            prev_close = float(records[index - 1]['close']) if index > 0 else np.nan
            if np.isfinite(prev_close) and _accepted(setup, bar, prev_close):
                event = _event(setup, bar)
                if event['decision_time'] >= trade_until:
                    candidates.append(event)
                    trade_until = event['entry_time'] + pd.Timedelta(minutes=120)
                active[direction] = None
                resolved[direction] = True
        anchor = raw_by_index.get(index)
        if anchor is not None:
            direction = anchor['direction']
            if active[direction] is None and not resolved[direction]:
                active[direction] = AbsorptionSetup(**{
                    key: anchor[key] for key in AbsorptionSetup.__dataclass_fields__ if key in anchor
                })
        last_time = time
    return pd.DataFrame(raw), pd.DataFrame(candidates)
