from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import pandas as pd

FORCED_EXIT_BUFFER_MIN = 5
STATE_VERSION = "STAGE262_EXIT_V1"


class ExitContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class CandidateTrade:
    candidate_id: str
    candidate_key: str
    entry_time: pd.Timestamp
    direction: str
    horizon_min: int
    tp: float
    sl: float


@dataclass(frozen=True)
class TradePlan:
    candidate_id: str
    candidate_key: str
    entry_time: pd.Timestamp
    direction: str
    horizon_min: int
    tp: float
    sl: float
    eligibility_status: str
    calendar_id: str | None = None
    calendar_source_version: str | None = None
    calendar_published_at: pd.Timestamp | None = None
    session_close_time: pd.Timestamp | None = None
    nominal_exit_time: pd.Timestamp | None = None
    planned_exit_time: pd.Timestamp | None = None
    state_version: str = STATE_VERSION

    @property
    def trade_opened(self) -> bool:
        return self.eligibility_status == "TRADE_OPENED"


@dataclass
class OpenTradeState:
    plan: TradePlan
    entry_price: float
    state: str = "OPEN"
    last_processed_m1_time: pd.Timestamp | None = None
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    gross_pnl: float | None = None
    cost2_pnl: float | None = None

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> "OpenTradeState":
        data = dict(value)
        plan_data = dict(data.pop("plan"))
        for col in (
            "entry_time", "calendar_published_at", "session_close_time",
            "nominal_exit_time", "planned_exit_time",
        ):
            if plan_data.get(col) is not None:
                plan_data[col] = pd.Timestamp(plan_data[col])
        for col in ("last_processed_m1_time", "exit_time"):
            if data.get(col) is not None:
                data[col] = pd.Timestamp(data[col])
        return cls(plan=TradePlan(**plan_data), **data)


def normalize_calendar(calendar: pd.DataFrame) -> pd.DataFrame:
    required = [
        "calendar_id", "broker_or_server_id", "symbol_group", "server_timezone",
        "session_date", "session_open_time", "session_close_time",
        "is_holiday_closed", "is_short_session", "published_at",
        "source_name", "source_version",
    ]
    missing = [c for c in required if c not in calendar.columns]
    if missing:
        raise ExitContractError(f"calendar columns missing: {missing}")
    out = calendar.copy()
    for c in ("session_open_time", "session_close_time", "published_at"):
        out[c] = pd.to_datetime(out[c], errors="raise")
    out["is_holiday_closed"] = out["is_holiday_closed"].astype(bool)
    out["is_short_session"] = out["is_short_session"].astype(bool)
    if (out["session_close_time"] <= out["session_open_time"]).any():
        raise ExitContractError("session_close_time must be after session_open_time")
    if out["calendar_id"].duplicated().any():
        raise ExitContractError("calendar_id must be unique")
    return out.sort_values(["session_open_time", "published_at"]).reset_index(drop=True)


def plan_trade(candidate: CandidateTrade, calendar: pd.DataFrame) -> TradePlan:
    cal = normalize_calendar(calendar)
    entry = pd.Timestamp(candidate.entry_time)
    matched = cal[(cal["session_open_time"] <= entry) & (entry < cal["session_close_time"])]
    if matched.empty:
        return TradePlan(
            candidate_id=candidate.candidate_id,
            candidate_key=candidate.candidate_key,
            entry_time=entry,
            direction=candidate.direction,
            horizon_min=int(candidate.horizon_min),
            tp=float(candidate.tp),
            sl=float(candidate.sl),
            eligibility_status="CALENDAR_MISSING_NO_ENTRY",
        )
    preknown = matched[matched["published_at"] <= entry]
    if preknown.empty:
        row = matched.sort_values("published_at").iloc[0]
        return TradePlan(
            candidate_id=candidate.candidate_id,
            candidate_key=candidate.candidate_key,
            entry_time=entry,
            direction=candidate.direction,
            horizon_min=int(candidate.horizon_min),
            tp=float(candidate.tp),
            sl=float(candidate.sl),
            eligibility_status="CALENDAR_NOT_PREKNOWN_NO_ENTRY",
            calendar_id=str(row.calendar_id),
            calendar_source_version=str(row.source_version),
            calendar_published_at=pd.Timestamp(row.published_at),
            session_close_time=pd.Timestamp(row.session_close_time),
        )
    row = preknown.sort_values("published_at").iloc[-1]
    common = dict(
        candidate_id=candidate.candidate_id,
        candidate_key=candidate.candidate_key,
        entry_time=entry,
        direction=candidate.direction,
        horizon_min=int(candidate.horizon_min),
        tp=float(candidate.tp),
        sl=float(candidate.sl),
        calendar_id=str(row.calendar_id),
        calendar_source_version=str(row.source_version),
        calendar_published_at=pd.Timestamp(row.published_at),
        session_close_time=pd.Timestamp(row.session_close_time),
    )
    if bool(row.is_holiday_closed):
        return TradePlan(**common, eligibility_status="HOLIDAY_CLOSED_NO_ENTRY")
    nominal = entry + pd.Timedelta(minutes=int(candidate.horizon_min))
    forced = pd.Timestamp(row.session_close_time) - pd.Timedelta(minutes=FORCED_EXIT_BUFFER_MIN)
    planned = min(nominal, forced)
    if planned <= entry:
        return TradePlan(
            **common,
            eligibility_status="TOO_CLOSE_TO_SESSION_END_NO_ENTRY",
            nominal_exit_time=nominal,
            planned_exit_time=planned,
        )
    return TradePlan(
        **common,
        eligibility_status="TRADE_OPENED",
        nominal_exit_time=nominal,
        planned_exit_time=planned,
    )


def _levels(direction: str, entry: float, tp: float, sl: float) -> tuple[float, float]:
    if direction == "LONG":
        return entry + tp, entry - sl
    if direction == "SHORT":
        return entry - tp, entry + sl
    raise ExitContractError(f"unknown direction: {direction}")


def _finish(state: OpenTradeState, time: pd.Timestamp, price: float, reason: str) -> None:
    state.state = reason
    state.exit_time = pd.Timestamp(time)
    state.exit_price = float(price)
    state.exit_reason = reason
    gross = price - state.entry_price if state.plan.direction == "LONG" else state.entry_price - price
    state.gross_pnl = float(gross)
    state.cost2_pnl = float(gross - 2.0)


def process_m1_bar(state: OpenTradeState, bar: dict[str, Any] | pd.Series) -> None:
    if state.state != "OPEN":
        return
    t = pd.Timestamp(bar["time"])
    if state.last_processed_m1_time is not None and t <= state.last_processed_m1_time:
        raise ExitContractError("M1 bars must be strictly increasing")
    planned = pd.Timestamp(state.plan.planned_exit_time)
    if t < state.plan.entry_time:
        return
    if t > planned:
        state.state = "DATA_MISSING_BLOCKED"
        state.exit_reason = "DATA_MISSING_BLOCKED"
        return
    if t == planned:
        _finish(state, t, float(bar["open"]), "FORCED_EXIT")
        state.last_processed_m1_time = t
        return
    tp_price, sl_price = _levels(state.plan.direction, state.entry_price, state.plan.tp, state.plan.sl)
    high, low = float(bar["high"]), float(bar["low"])
    if state.plan.direction == "LONG":
        hit_sl, hit_tp = low <= sl_price, high >= tp_price
    else:
        hit_sl, hit_tp = high >= sl_price, low <= tp_price
    if hit_sl:
        _finish(state, t, sl_price, "SL_EXIT")
    elif hit_tp:
        _finish(state, t, tp_price, "TP_EXIT")
    state.last_processed_m1_time = t


def evaluate_trade_batch(plan: TradePlan, m1: pd.DataFrame) -> dict[str, Any]:
    base = asdict(plan)
    if not plan.trade_opened:
        return {**base, "state": "NO_ENTRY_CALENDAR", "exit_reason": plan.eligibility_status}
    x = m1.copy()
    x["time"] = pd.to_datetime(x["time"], errors="raise")
    x = x.sort_values("time").drop_duplicates("time", keep="first")
    indexed = x.set_index("time")
    if plan.entry_time not in indexed.index:
        return {**base, "state": "DATA_MISSING_BLOCKED", "exit_reason": "ENTRY_M1_MISSING"}
    if plan.planned_exit_time not in indexed.index:
        return {**base, "state": "DATA_MISSING_BLOCKED", "exit_reason": "FORCED_EXIT_M1_MISSING"}
    entry_price = float(indexed.loc[plan.entry_time, "open"])
    state = OpenTradeState(plan=plan, entry_price=entry_price)
    path = x[(x["time"] >= plan.entry_time) & (x["time"] <= plan.planned_exit_time)]
    for bar in path.to_dict(orient="records"):
        process_m1_bar(state, bar)
        if state.state != "OPEN":
            break
    if state.state == "OPEN":
        state.state = "DATA_MISSING_BLOCKED"
        state.exit_reason = "PLANNED_EXIT_NOT_PROCESSED"
    return asdict(state)


class StreamingExitEngine:
    def __init__(self, states: Iterable[OpenTradeState] = ()) -> None:
        self.states: dict[str, OpenTradeState] = {s.plan.candidate_key: s for s in states}

    def add_plan(self, plan: TradePlan, entry_bar: dict[str, Any] | pd.Series | None) -> None:
        if not plan.trade_opened:
            return
        if entry_bar is None or pd.Timestamp(entry_bar["time"]) != plan.entry_time:
            raise ExitContractError("exact entry M1 is required")
        self.states[plan.candidate_key] = OpenTradeState(plan=plan, entry_price=float(entry_bar["open"]))

    def on_bar(self, bar: dict[str, Any] | pd.Series) -> None:
        for state in self.states.values():
            if state.state == "OPEN" and pd.Timestamp(bar["time"]) >= state.plan.entry_time:
                process_m1_bar(state, bar)

    def snapshot(self) -> dict[str, Any]:
        return {key: state.snapshot() for key, state in self.states.items()}

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> "StreamingExitEngine":
        return cls(OpenTradeState.from_snapshot(v) for v in value.values())

    def result_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(s) for s in self.states.values()])
