from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from mochipoyo_alert_research.collect_events_once import build_events_url, fetch_json  # noqa: E402
from mochipoyo_alert_research.config import load_config  # noqa: E402


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def dict_shape(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "keys": sorted(str(key) for key in value.keys()),
        "key_types": {str(key): value_type(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))},
    }


def list_shape(value: list[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "count": len(value),
        "first_item_type": value_type(value[0]) if value else "empty",
    }
    if not value:
        return result
    first = value[0]
    if isinstance(first, dict):
        result["first_item"] = dict_shape(first)
        nested: dict[str, Any] = {}
        for key, item in sorted(first.items(), key=lambda pair: str(pair[0])):
            if isinstance(item, list):
                nested[str(key)] = list_shape(item)
            elif isinstance(item, dict):
                nested[str(key)] = dict_shape(item)
        if nested:
            result["first_item_nested_containers"] = nested
    return result


def contract_shape(payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "PASS_SCHEMA_ONLY",
        "values_included": False,
        "secrets_included": False,
        "payload_type": value_type(payload),
    }
    if isinstance(payload, dict):
        result["top_level"] = dict_shape(payload)
        containers: dict[str, Any] = {}
        for key, item in sorted(payload.items(), key=lambda pair: str(pair[0])):
            if isinstance(item, list):
                containers[str(key)] = list_shape(item)
            elif isinstance(item, dict):
                containers[str(key)] = dict_shape(item)
        result["top_level_containers"] = containers
    elif isinstance(payload, list):
        result["top_level_list"] = list_shape(payload)
    return result


def main() -> int:
    try:
        config = load_config()
        url = build_events_url(config.events_url, after_id=0, limit=5)
        payload = fetch_json(url, config.read_token, timeout_seconds=30.0)
        result = contract_shape(payload)
        diagnostic_path = config.logs_dir / "latest_contract_shape.json"
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result["diagnostic_path"] = str(diagnostic_path)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"[ERROR] Contract inspection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
