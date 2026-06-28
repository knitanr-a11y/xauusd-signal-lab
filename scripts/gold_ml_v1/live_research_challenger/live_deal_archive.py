from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd

from live_store import atomic_write_csv, atomic_write_text

DEAL_COLUMNS = [
    "candidate_key",
    "candidate_id",
    "comp",
    "direction",
    "position_ticket",
    "deal_ticket",
    "order_ticket",
    "time",
    "time_msc",
    "deal_type",
    "entry",
    "reason",
    "magic",
    "symbol",
    "volume",
    "price",
    "commission",
    "swap",
    "profit",
    "fee",
    "comment",
    "external_id",
    "captured_at",
    "row_hash",
]

POSITION_INDEX_COLUMNS = [
    "position_ticket",
    "candidate_key",
    "candidate_id",
    "comp",
    "direction",
    "deal_count",
    "entry_deal_count",
    "exit_deal_count",
    "first_deal_time",
    "last_deal_time",
    "deal_net_profit",
    "ledger_net_profit",
    "net_difference",
    "archive_files",
    "position_digest",
    "completed_at",
]


@dataclass(frozen=True)
class DealCapture:
    position_ticket: int
    deals: tuple[dict[str, Any], ...]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value).strip()


def _number(value: Any) -> float:
    if value is None or _text(value) == "":
        return 0.0
    converted = float(value)
    return converted if np.isfinite(converted) else 0.0


def _integer(value: Any) -> int:
    if value is None or _text(value) == "":
        return 0
    return int(value)


def _asdict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if isinstance(value, dict):
        return dict(value)
    return {
        name: getattr(value, name)
        for name in (
            "ticket",
            "order",
            "time",
            "time_msc",
            "type",
            "entry",
            "magic",
            "position_id",
            "reason",
            "volume",
            "price",
            "commission",
            "swap",
            "profit",
            "fee",
            "symbol",
            "comment",
            "external_id",
        )
        if hasattr(value, name)
    }


def _deal_time(payload: dict[str, Any]) -> str:
    seconds = _integer(payload.get("time"))
    if seconds <= 0:
        milliseconds = _integer(payload.get("time_msc"))
        seconds = milliseconds // 1000
    if seconds <= 0:
        return ""
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")


def normalize_deals(raw_deals: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for raw in raw_deals:
        payload = _asdict(raw)
        position_ticket = _integer(payload.get("position_id"))
        deal_ticket = _integer(payload.get("ticket"))
        if position_ticket <= 0 or deal_ticket <= 0:
            continue
        records.append(
            {
                "position_ticket": position_ticket,
                "deal_ticket": deal_ticket,
                "order_ticket": _integer(payload.get("order")),
                "time": _deal_time(payload),
                "time_msc": _integer(payload.get("time_msc")),
                "deal_type": _integer(payload.get("type")),
                "entry": _integer(payload.get("entry")),
                "reason": _integer(payload.get("reason")),
                "magic": _integer(payload.get("magic")),
                "symbol": _text(payload.get("symbol")),
                "volume": _number(payload.get("volume")),
                "price": _number(payload.get("price")),
                "commission": _number(payload.get("commission")),
                "swap": _number(payload.get("swap")),
                "profit": _number(payload.get("profit")),
                "fee": _number(payload.get("fee")),
                "comment": _text(payload.get("comment")),
                "external_id": _text(payload.get("external_id")),
            }
        )
    records.sort(key=lambda item: (item["time_msc"], item["deal_ticket"]))
    return tuple(records)


def read_position_deals(client: Any, position_ticket: int) -> tuple[dict[str, Any], ...]:
    custom = getattr(client, "position_deal_records", None)
    if callable(custom):
        return normalize_deals(custom(int(position_ticket)))
    mt5 = getattr(client, "mt5", None)
    if mt5 is None:
        return ()
    deals = mt5.history_deals_get(position=int(position_ticket)) or ()
    return normalize_deals(deals)


class DealCapturingClient:
    """Proxy an MT5 client and retain complete deal snapshots before shutdown."""

    def __init__(self, delegate: Any, sink: list[DealCapture]):
        self._delegate = delegate
        self._sink = sink

    def __enter__(self) -> "DealCapturingClient":
        self._delegate.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
        return self._delegate.__exit__(exc_type, exc, tb)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def capture_position(self, position_ticket: int) -> tuple[dict[str, Any], ...]:
        deals = read_position_deals(self._delegate, int(position_ticket))
        if deals:
            self._sink.append(DealCapture(int(position_ticket), deals))
        return deals

    def closed_position_profit(self, position_ticket: int):
        result = self._delegate.closed_position_profit(int(position_ticket))
        if result is not None:
            self.capture_position(int(position_ticket))
        return result


def capturing_factory(
    base_factory: Callable[[Any], Any],
    sink: list[DealCapture],
) -> Callable[[Any], DealCapturingClient]:
    return lambda settings: DealCapturingClient(base_factory(settings), sink)


def _deal_hash(record: dict[str, Any]) -> str:
    payload = {
        key: record[key]
        for key in DEAL_COLUMNS
        if key not in {"captured_at", "row_hash"}
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _position_digest(frame: pd.DataFrame) -> str:
    hashes = sorted(frame["row_hash"].astype(str).tolist())
    return hashlib.sha256("\n".join(hashes).encode("utf-8")).hexdigest()


def _read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path, dtype=object)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame[columns].copy()


def load_position_index(output_dir: Path) -> pd.DataFrame:
    return _read_csv(
        output_dir / "trades" / "deal_position_index.csv",
        POSITION_INDEX_COLUMNS,
    )


def completed_position_tickets(output_dir: Path) -> set[int]:
    frame = load_position_index(output_dir)
    if frame.empty:
        return set()
    values = pd.to_numeric(frame["position_ticket"], errors="coerce").dropna()
    return {int(value) for value in values if int(value) > 0}


def _matching_ledger_row(ledger: pd.DataFrame, position_ticket: int) -> pd.Series | None:
    if ledger.empty or "position_ticket" not in ledger.columns:
        return None
    tickets = pd.to_numeric(ledger["position_ticket"], errors="coerce")
    matches = ledger[tickets.eq(int(position_ticket))]
    if len(matches) != 1:
        return None
    return matches.iloc[0]


def _enrich_deals(
    deals: tuple[dict[str, Any], ...],
    ledger_row: pd.Series,
    captured_at: str,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for deal in deals:
        record = {
            "candidate_key": _text(ledger_row.get("candidate_key")),
            "candidate_id": _text(ledger_row.get("candidate_id")),
            "comp": _text(ledger_row.get("comp")),
            "direction": _text(ledger_row.get("direction")),
            **deal,
            "captured_at": captured_at,
        }
        record["row_hash"] = _deal_hash(record)
        records.append(record)
    return pd.DataFrame(records, columns=DEAL_COLUMNS)


def _merge_immutable(existing: pd.DataFrame, addition: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return addition.sort_values(["time_msc", "deal_ticket"], kind="mergesort").reset_index(drop=True)
    by_ticket = existing.set_index("deal_ticket", drop=False)
    for record in addition.to_dict(orient="records"):
        key = str(record["deal_ticket"])
        if key in by_ticket.index.astype(str):
            existing_row = existing[existing["deal_ticket"].astype(str).eq(key)].iloc[0]
            if _text(existing_row["row_hash"]) != _text(record["row_hash"]):
                raise ValueError(f"immutable MT5 deal collision for ticket {key}")
            continue
        existing = pd.concat([existing, pd.DataFrame([record], columns=DEAL_COLUMNS)], ignore_index=True)
    return existing[DEAL_COLUMNS].sort_values(["time_msc", "deal_ticket"], kind="mergesort").reset_index(drop=True)


def archive_captures(
    output_dir: Path,
    ledger: pd.DataFrame,
    captures: Iterable[DealCapture],
    captured_at: str,
    *,
    net_tolerance: float = 0.01,
) -> dict[str, Any]:
    latest_by_position: dict[int, DealCapture] = {}
    for capture in captures:
        latest_by_position[int(capture.position_ticket)] = capture

    completed = 0
    incomplete: list[str] = []
    archived_deals = 0
    position_index = load_position_index(output_dir)

    for position_ticket, capture in sorted(latest_by_position.items()):
        ledger_row = _matching_ledger_row(ledger, position_ticket)
        if ledger_row is None:
            incomplete.append(f"position {position_ticket}: ledger row unavailable or ambiguous")
            continue
        if _text(ledger_row.get("trade_state")) != "CLOSED":
            continue
        enriched = _enrich_deals(capture.deals, ledger_row, captured_at)
        if enriched.empty:
            incomplete.append(f"position {position_ticket}: no MT5 deals returned")
            continue

        position_ids = pd.to_numeric(enriched["position_ticket"], errors="coerce")
        if not position_ids.eq(position_ticket).all():
            incomplete.append(f"position {position_ticket}: mixed position ids in deal snapshot")
            continue
        if enriched["deal_ticket"].astype(str).duplicated().any():
            incomplete.append(f"position {position_ticket}: duplicate deal tickets")
            continue

        deal_net = float(
            enriched[["profit", "commission", "swap", "fee"]]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
            .sum(axis=1)
            .sum()
        )
        ledger_net = float(ledger_row.get("net_profit"))
        difference = deal_net - ledger_net
        if abs(difference) > net_tolerance:
            incomplete.append(
                f"position {position_ticket}: deal net {deal_net:.8f} != ledger net {ledger_net:.8f}"
            )
            continue

        times = pd.to_datetime(enriched["time"], errors="coerce")
        if times.isna().any():
            incomplete.append(f"position {position_ticket}: deal time unavailable")
            continue
        enriched = enriched.assign(_month=times.dt.strftime("%Y-%m"))
        archive_files: list[str] = []
        for month, group in enriched.groupby("_month", sort=True):
            path = output_dir / "trades" / "deals" / str(month)[:4] / f"mt5_deals_{month}.csv"
            existing = _read_csv(path, DEAL_COLUMNS)
            monthly = _merge_immutable(existing, group.drop(columns=["_month"])[DEAL_COLUMNS])
            atomic_write_csv(path, monthly)
            archive_files.append(str(path.relative_to(output_dir)).replace("\\", "/"))
            archived_deals += len(group)

        complete_frame = enriched.drop(columns=["_month"])[DEAL_COLUMNS]
        entry_values = pd.to_numeric(complete_frame["entry"], errors="coerce").fillna(-1).astype(int)
        row = {
            "position_ticket": position_ticket,
            "candidate_key": _text(ledger_row.get("candidate_key")),
            "candidate_id": _text(ledger_row.get("candidate_id")),
            "comp": _text(ledger_row.get("comp")),
            "direction": _text(ledger_row.get("direction")),
            "deal_count": int(len(complete_frame)),
            "entry_deal_count": int(entry_values.eq(0).sum()),
            "exit_deal_count": int(entry_values.isin([1, 2, 3]).sum()),
            "first_deal_time": str(times.min()),
            "last_deal_time": str(times.max()),
            "deal_net_profit": deal_net,
            "ledger_net_profit": ledger_net,
            "net_difference": difference,
            "archive_files": "|".join(sorted(set(archive_files))),
            "position_digest": _position_digest(complete_frame),
            "completed_at": captured_at,
        }
        addition = pd.DataFrame([row], columns=POSITION_INDEX_COLUMNS)
        if position_index.empty:
            position_index = addition
        else:
            old = position_index[
                position_index["position_ticket"].astype(str).eq(str(position_ticket))
            ]
            if not old.empty and _text(old.iloc[0]["position_digest"]) != row["position_digest"]:
                raise ValueError(f"immutable MT5 position digest collision for {position_ticket}")
            position_index = pd.concat(
                [
                    position_index[
                        ~position_index["position_ticket"].astype(str).eq(str(position_ticket))
                    ],
                    addition,
                ],
                ignore_index=True,
            )
        completed += 1

    if not position_index.empty:
        position_index = position_index[POSITION_INDEX_COLUMNS].sort_values(
            ["last_deal_time", "position_ticket"], kind="mergesort"
        ).reset_index(drop=True)
        atomic_write_csv(output_dir / "trades" / "deal_position_index.csv", position_index)

    status = {
        "captured_positions": int(len(latest_by_position)),
        "completed_positions": completed,
        "archived_deal_rows": archived_deals,
        "incomplete": incomplete,
    }
    atomic_write_text(
        output_dir / "trades" / "deal_archive_status.json",
        json.dumps({"updated_at": captured_at, **status}, ensure_ascii=False, indent=2),
    )
    return status
