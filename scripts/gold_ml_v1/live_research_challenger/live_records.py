from __future__ import annotations

import json
from typing import Any

import pandas as pd

from live_store import json_value


def candidate_record(event: Any, evaluated: dict[str, Any], now_text: str) -> dict[str, Any]:
    decision = pd.Timestamp(event.bar_close_time)
    candidate_key = f"{event.candidate_id}|{decision.strftime('%Y-%m-%d %H:%M:%S')}"
    features = {
        str(key): json_value(value)
        for key, value in dict(event.features_json).items()
    }
    return {
        "candidate_key": candidate_key,
        "candidate_id": event.candidate_id,
        "comp": event.comp,
        "decision_time": decision.strftime("%Y-%m-%d %H:%M:%S"),
        "direction": evaluated["direction"],
        "source_timeframe": event.source_timeframe,
        "higher_timeframe": event.higher_timeframe,
        "atr": json_value(evaluated.get("atr")),
        "target_r": json_value(evaluated.get("target_r")),
        "horizon_hours": int(evaluated["horizon_hours"]),
        "entry_price": json_value(evaluated.get("entry_price")),
        "stop_price": json_value(evaluated.get("stop_price")),
        "target_price": json_value(evaluated.get("target_price")),
        "position_state": evaluated["position_state"],
        "outcome": evaluated["outcome"],
        "exit_time": json_value(evaluated.get("exit_time")),
        "exit_price": json_value(evaluated.get("exit_price")),
        "r": json_value(evaluated.get("r")),
        "current_price": json_value(evaluated.get("current_price")),
        "current_r": json_value(evaluated.get("current_r")),
        "features_json": json.dumps(features, ensure_ascii=False, separators=(",", ":")),
        "first_seen_at": now_text,
        "last_updated_at": now_text,
    }


def dynamic_update(
    candidate_key: str,
    evaluated: dict[str, Any],
    now_text: str,
) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "position_state": evaluated["position_state"],
        "outcome": evaluated["outcome"],
        "exit_time": json_value(evaluated.get("exit_time")),
        "exit_price": json_value(evaluated.get("exit_price")),
        "r": json_value(evaluated.get("r")),
        "current_price": json_value(evaluated.get("current_price")),
        "current_r": json_value(evaluated.get("current_r")),
        "last_updated_at": now_text,
    }
