from __future__ import annotations

from bisect import bisect_left, bisect_right, insort
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from stage260_live_replay_contract import candidate_key
from stage260_event_audit_utils import causal_percentile

STATE_VERSION = 'E7_V1'
EVENT_TYPE = 'E7_TICK_VOLUME_IMPULSE_ACCEPTANCE'


@dataclass
class ImpulseSetup:
    direction: str
    anchor_time: pd.Timestamp
    anchor_bar_index: int
    anchor_open: float
    anchor_high: float
    anchor_low: float
    anchor_close: float
    anchor_h1_atr14: float
    tick_volume: float
    slot_median_volume: float
    slot_volume_ratio: float
    slot_volume_percentile: float
    global_volume_percentile: float
    body_ratio: float
    tr_ratio: float
    state: str = 'IMPULSE_ACTIVE'

    @property
    def midpoint(self) -> float:
        return (self.anchor_open + self.anchor_close) / 2.0

    @property
    def accept_level(self) -> float:
        s = 1.0 if self.direction == 'LONG' else -1.0
        return self.anchor_close + s * 0.03 * self.anchor_h1_atr14

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> 'ImpulseSetup':
        v = dict(value)
        v['anchor_time'] = pd.Timestamp(v['anchor_time'])
        return cls(**v)


def _slot(time: pd.Timestamp) -> int:
    t = pd.Timestamp(time)
    return t.hour * 12 + t.minute // 5


def _true_range(o: float, h: float, l: float, c: float, prev_close: float | None) -> float:
    if prev_close is None or not np.isfinite(prev_close):
        return h - l
    return max(h - l, abs(h - prev_close), abs(l - prev_close))


def _rank_percentile(sorted_values: list[float], value: float) -> float:
    return bisect_right(sorted_values, float(value)) / len(sorted_values)


def prepare_e7_context_batch(m5: pd.DataFrame, h1_context: pd.DataFrame, h4_context: pd.DataFrame) -> pd.DataFrame:
    """Batch-only causal feature builder. Current row is excluded from every baseline."""
    x = m5.sort_values('time').copy().reset_index(drop=True)
    x['time'] = pd.to_datetime(x['time'], errors='raise')
    x['source_close_time'] = pd.to_datetime(x['source_close_time'], errors='raise')
    x['decision_time'] = x['source_close_time']
    x['server_slot'] = x['time'].dt.hour * 12 + x['time'].dt.minute // 5
    pc = x['close'].shift(1)
    x['m5_tr'] = pd.concat([
        x['high'] - x['low'],
        (x['high'] - pc).abs(),
        (x['low'] - pc).abs(),
    ], axis=1).max(axis=1)
    x['tr_median_288'] = x['m5_tr'].shift(1).rolling(288, min_periods=100).median()
    x['global_volume_percentile'] = causal_percentile(x['tick_volume'].to_numpy(float), 2880, 1000)

    x['slot_median_volume'] = np.nan
    x['slot_volume_percentile'] = np.nan
    for _, idx in x.groupby('server_slot', sort=False).groups.items():
        ids = np.asarray(list(idx), dtype=int)
        vals = x.loc[ids, 'tick_volume'].to_numpy(float)
        med = pd.Series(vals).shift(1).rolling(60, min_periods=20).median().to_numpy()
        pct = causal_percentile(vals, 60, 20)
        x.loc[ids, 'slot_median_volume'] = med
        x.loc[ids, 'slot_volume_percentile'] = pct
    x['slot_volume_ratio'] = x['tick_volume'] / x['slot_median_volume']

    x = pd.merge_asof(
        x.sort_values('decision_time'), h1_context.sort_values('source_close_time'),
        left_on='decision_time', right_on='source_close_time', direction='backward',
        allow_exact_matches=True, suffixes=('', '_h1src'),
    )
    x = pd.merge_asof(
        x.sort_values('decision_time'), h4_context.sort_values('source_close_time'),
        left_on='decision_time', right_on='source_close_time', direction='backward',
        allow_exact_matches=True, suffixes=('', '_h4src'),
    )
    if (x['source_close_time_h1src'] > x['decision_time']).fillna(False).any():
        raise AssertionError('H1 lookahead')
    if (x['source_close_time_h4src'] > x['decision_time']).fillna(False).any():
        raise AssertionError('H4 lookahead')
    return x.reset_index(drop=True)


def _anchor_from_bar(bar: dict[str, Any] | pd.Series, bar_index: int) -> dict[str, Any] | None:
    get = bar.get if isinstance(bar, dict) else bar.get
    atr = float(get('h1_atr14', np.nan))
    slot_med = float(get('slot_median_volume', np.nan))
    slot_pct = float(get('slot_volume_percentile', np.nan))
    global_pct = float(get('global_volume_percentile', np.nan))
    tr_med = float(get('tr_median_288', np.nan))
    tv = float(get('tick_volume', np.nan))
    o, h, l, c = map(float, [get('open'), get('high'), get('low'), get('close')])
    tr = float(get('m5_tr', np.nan))
    if not all(np.isfinite(v) for v in [atr, slot_med, slot_pct, global_pct, tr_med, tv, o, h, l, c, tr]):
        return None
    if atr <= 0 or slot_med <= 0 or tr_med <= 0 or h <= l:
        return None
    slot_ratio = tv / slot_med
    body = abs(c - o)
    body_ratio = body / (h - l)
    tr_ratio = tr / tr_med
    if slot_ratio < 1.80 or slot_pct < 0.90 or global_pct < 0.85:
        return None
    if body < 0.12 * atr or body_ratio < 0.65 or tr_ratio < 1.50:
        return None
    if c > o and c >= h - 0.15 * (h - l):
        direction = 'LONG'
    elif c < o and c <= l + 0.15 * (h - l):
        direction = 'SHORT'
    else:
        return None
    return {
        'direction': direction,
        'anchor_time': pd.Timestamp(get('decision_time')),
        'anchor_bar_index': int(bar_index),
        'anchor_open': o,
        'anchor_high': h,
        'anchor_low': l,
        'anchor_close': c,
        'anchor_h1_atr14': atr,
        'tick_volume': tv,
        'slot_median_volume': slot_med,
        'slot_volume_ratio': slot_ratio,
        'slot_volume_percentile': slot_pct,
        'global_volume_percentile': global_pct,
        'body_ratio': body_ratio,
        'tr_ratio': tr_ratio,
        'h1_atr_band': str(get('h1_atr_band', '')),
        'h4_atr_band': str(get('h4_atr_band', '')),
    }


def _invalid(setup: ImpulseSetup, bar: dict[str, Any] | pd.Series) -> bool:
    c = float(bar['close'])
    return c <= setup.midpoint if setup.direction == 'LONG' else c >= setup.midpoint


def _accepted(setup: ImpulseSetup, bar: dict[str, Any] | pd.Series, prev_close: float) -> bool:
    o, c = float(bar['open']), float(bar['close'])
    if setup.direction == 'LONG':
        return c >= setup.accept_level and c > prev_close and c > o
    return c <= setup.accept_level and c < prev_close and c < o


def _event(setup: ImpulseSetup, bar: dict[str, Any] | pd.Series) -> dict[str, Any]:
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
        'anchor_h1_atr14': setup.anchor_h1_atr14,
        'tick_volume': setup.tick_volume,
        'slot_median_volume': setup.slot_median_volume,
        'slot_volume_ratio': setup.slot_volume_ratio,
        'slot_volume_percentile': setup.slot_volume_percentile,
        'global_volume_percentile': setup.global_volume_percentile,
        'body_ratio': setup.body_ratio,
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


class E7StreamingDetector:
    """Live-style detector. Volume baselines are updated only after current bar decisions."""
    def __init__(self) -> None:
        self.slot_values = {i: deque() for i in range(288)}
        self.slot_sorted = {i: [] for i in range(288)}
        self.global_values: deque[float] = deque()
        self.global_sorted: list[float] = []
        self.tr_values: deque[float] = deque()
        self.active: dict[str, ImpulseSetup | None] = {'LONG': None, 'SHORT': None}
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
        i = bisect_left(sorted_values, value)
        if i >= len(sorted_values) or sorted_values[i] != value:
            raise AssertionError('sorted history mismatch')
        sorted_values.pop(i)

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
    def from_snapshot(cls, value: dict[str, Any]) -> 'E7StreamingDetector':
        o = cls()
        for k, vals in value.get('slot_values', {}).items():
            o.slot_values[int(k)] = deque(float(v) for v in vals)
        for k, vals in value.get('slot_sorted', {}).items():
            o.slot_sorted[int(k)] = [float(v) for v in vals]
        o.global_values = deque(float(v) for v in value.get('global_values', []))
        o.global_sorted = [float(v) for v in value.get('global_sorted', [])]
        o.tr_values = deque(float(v) for v in value.get('tr_values', []))
        o.active = {
            k: None if value['active'].get(k) is None else ImpulseSetup.from_snapshot(value['active'][k])
            for k in ('LONG', 'SHORT')
        }
        o.events = list(value.get('events', []))
        o.raw_anchors = list(value.get('raw_anchors', []))
        o.resolutions = list(value.get('resolutions', []))
        o.last_time = None if value.get('last_time') is None else pd.Timestamp(value['last_time'])
        o.prev_close = value.get('prev_close')
        o.prev_bar_close = value.get('prev_bar_close')
        o.bar_index = int(value.get('bar_index', -1))
        o.global_trade_active_until = pd.Timestamp(value.get('global_trade_active_until', pd.Timestamp.min))
        return o

    def _resolve(self, d: str, reason: str, bar: dict[str, Any]) -> None:
        s = self.active[d]
        if s is None:
            return
        self.resolutions.append({
            'direction': d,
            'anchor_time': s.anchor_time,
            'resolution_time': pd.Timestamp(bar['decision_time']),
            'resolution': reason,
        })
        self.active[d] = None

    def _update_state(self, d: str, bar: dict[str, Any], gap: bool) -> bool:
        s = self.active[d]
        if s is None:
            return False
        if gap:
            self._resolve(d, 'GAP', bar)
            return True
        age = self.bar_index - s.anchor_bar_index
        if age > 2:
            self._resolve(d, 'EXPIRED', bar)
            return True
        if _invalid(s, bar):
            self._resolve(d, 'INVALID', bar)
            return True
        prev = self.prev_bar_close
        if prev is not None and _accepted(s, bar, float(prev)):
            e = _event(s, bar)
            if e['decision_time'] >= self.global_trade_active_until:
                self.events.append(e)
                self.global_trade_active_until = e['entry_time'] + pd.Timedelta(minutes=120)
                self._resolve(d, 'ACCEPTED_EMITTED', bar)
            else:
                self._resolve(d, 'ACCEPTED_DEDUP_SUPPRESSED', bar)
            return True
        return False

    def _features(self, b: dict[str, Any]) -> dict[str, float]:
        tv = float(b['tick_volume'])
        slot = _slot(pd.Timestamp(b['time']))
        slot_hist = self.slot_values[slot]
        slot_sorted = self.slot_sorted[slot]
        slot_med = float(np.median(slot_hist)) if len(slot_hist) >= 20 else np.nan
        slot_pct = _rank_percentile(slot_sorted, tv) if len(slot_sorted) >= 20 else np.nan
        global_pct = _rank_percentile(self.global_sorted, tv) if len(self.global_sorted) >= 1000 else np.nan
        o, h, l, c = map(float, [b['open'], b['high'], b['low'], b['close']])
        tr = _true_range(o, h, l, c, self.prev_close)
        tr_med = float(np.median(self.tr_values)) if len(self.tr_values) >= 100 else np.nan
        return {
            'server_slot': slot,
            'm5_tr': tr,
            'tr_median_288': tr_med,
            'slot_median_volume': slot_med,
            'slot_volume_percentile': slot_pct,
            'global_volume_percentile': global_pct,
            'slot_volume_ratio': tv / slot_med if np.isfinite(slot_med) and slot_med > 0 else np.nan,
        }

    def _insert_histories(self, b: dict[str, Any], f: dict[str, float]) -> None:
        tv = float(b['tick_volume'])
        slot = int(f['server_slot'])
        tr = float(f['m5_tr'])
        sv, ss = self.slot_values[slot], self.slot_sorted[slot]
        sv.append(tv)
        insort(ss, tv)
        if len(sv) > 60:
            old = sv.popleft()
            self._remove_sorted(ss, old)
        self.global_values.append(tv)
        insort(self.global_sorted, tv)
        if len(self.global_values) > 2880:
            old = self.global_values.popleft()
            self._remove_sorted(self.global_sorted, old)
        self.tr_values.append(tr)
        if len(self.tr_values) > 288:
            self.tr_values.popleft()

    def on_bar(self, bar: pd.Series | dict[str, Any]) -> None:
        b = bar.to_dict() if isinstance(bar, pd.Series) else dict(bar)
        t = pd.Timestamp(b['time'])
        if pd.Timestamp(b['decision_time']) != pd.Timestamp(b['source_close_time']):
            raise ValueError('decision_time must equal source_close_time')
        if self.last_time is not None and t <= self.last_time:
            raise ValueError('bars not increasing')
        self.bar_index += 1
        gap = self.last_time is not None and t - self.last_time != pd.Timedelta(minutes=5)
        resolved = {d: self._update_state(d, b, gap) for d in ('LONG', 'SHORT')}
        f = self._features(b)
        enriched = {**b, **f}
        a = _anchor_from_bar(enriched, self.bar_index)
        if a is not None:
            d = a['direction']
            a['suppressed_active'] = self.active[d] is not None
            a['suppressed_resolution_bar'] = resolved[d]
            self.raw_anchors.append(a.copy())
            if self.active[d] is None and not resolved[d]:
                self.active[d] = ImpulseSetup(**{
                    k: a[k] for k in ImpulseSetup.__dataclass_fields__ if k in a
                })
        self._insert_histories(b, f)
        self.prev_close = float(b['close'])
        self.prev_bar_close = float(b['close'])
        self.last_time = t

    def event_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.events)


def detect_e7_streaming(context: pd.DataFrame):
    d = E7StreamingDetector()
    for bar in context.to_dict(orient='records'):
        d.on_bar(bar)
    return pd.DataFrame(d.raw_anchors), d.event_frame(), d


def detect_e7_batch(context: pd.DataFrame):
    records = context.to_dict(orient='records')
    raw = []
    for i, b in enumerate(records):
        a = _anchor_from_bar(b, i)
        if a is not None:
            raw.append(a)
    candidates = []
    active = {'LONG': None, 'SHORT': None}
    trade_until = pd.Timestamp.min
    raw_by_index = {int(a['anchor_bar_index']): a for a in raw}
    last_time = None
    for i, b in enumerate(records):
        t = pd.Timestamp(b['time'])
        gap = last_time is not None and t - last_time != pd.Timedelta(minutes=5)
        resolved = {'LONG': False, 'SHORT': False}
        for d in ('LONG', 'SHORT'):
            s = active[d]
            if s is None:
                continue
            if gap or i - s.anchor_bar_index > 2 or _invalid(s, b):
                active[d] = None
                resolved[d] = True
                continue
            prev_close = float(records[i - 1]['close']) if i > 0 else np.nan
            if np.isfinite(prev_close) and _accepted(s, b, prev_close):
                e = _event(s, b)
                if e['decision_time'] >= trade_until:
                    candidates.append(e)
                    trade_until = e['entry_time'] + pd.Timedelta(minutes=120)
                active[d] = None
                resolved[d] = True
        a = raw_by_index.get(i)
        if a is not None:
            d = a['direction']
            if active[d] is None and not resolved[d]:
                active[d] = ImpulseSetup(**{
                    k: a[k] for k in ImpulseSetup.__dataclass_fields__ if k in a
                })
        last_time = t
    return pd.DataFrame(raw), pd.DataFrame(candidates)
