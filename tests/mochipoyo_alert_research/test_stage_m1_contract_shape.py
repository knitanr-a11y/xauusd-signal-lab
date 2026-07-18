from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mochipoyo_alert_research" / "inspect_cloudflare_contract.py"
spec = importlib.util.spec_from_file_location("inspect_cloudflare_contract", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_contract_shape_contains_keys_and_types_but_not_values() -> None:
    secret = "must-not-appear"
    payload = {
        "ok": True,
        "rows": [
            {
                "results": [
                    {
                        "id": 2,
                        "event_key": secret,
                        "event": "LONG",
                    }
                ],
                "success": True,
            }
        ],
    }
    result = module.contract_shape(payload)
    encoded = json.dumps(result, sort_keys=True)
    assert secret not in encoded
    assert "event_key" in encoded
    assert result["values_included"] is False
    assert result["secrets_included"] is False
    assert result["top_level_containers"]["rows"]["first_item_nested_containers"]["results"]["count"] == 1
