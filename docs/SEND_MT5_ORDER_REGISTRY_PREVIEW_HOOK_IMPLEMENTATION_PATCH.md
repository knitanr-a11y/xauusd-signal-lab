# SEND MT5 ORDER registry preview hook implementation patch

Last updated: 2026-05-10

## Purpose

This patch folds the disabled-by-default registry preview hook into:

```text
scripts/send_mt5_order_from_payload.py
```

It keeps sender execution behavior unchanged unless one of these output flags is explicitly provided:

```text
--registry-preview-out-csv
--registry-preview-out-json
```

No production registry write is introduced.

## Safety invariants

```text
No preview output flags => no registry preview work.
Preview export runs only after sender result rows are already determined.
Preview export does not affect local validation, position policy, order_check, order_send, ledger writing, or exit code.
DRY_RUN_ORDER_CHECK_OK rows are eligible by default.
SENT rows are included only with --registry-preview-include-sent.
Blocked/error rows never create preview rows.
```

## Patch

Apply the following edits to `scripts/send_mt5_order_from_payload.py`.

### 1. Add import

Change:

```python
import time
from pathlib import Path
from typing import Any
```

To:

```python
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
```

### 2. Add constants after position policy constants

```python
REGISTRY_PREVIEW_SCHEMA_VERSION = "gold_multi_strategy_sender_registry_preview_from_sender_v1"
REGISTRY_PREVIEW_DEFAULT_POSITION_STATUS = "ACTIVE"
REGISTRY_PREVIEW_DEFAULT_POSITION_TICKET_START = 990001
REGISTRY_PREVIEW_DEFAULT_ORDER_TICKET_START = 880001
REGISTRY_PREVIEW_DEFAULT_DEAL_TICKET_START = 770001

REGISTRY_PREVIEW_COLUMNS = [
    "schema_version",
    "created_at_utc",
    "updated_at_utc",
    "account_login",
    "account_server",
    "broker_symbol",
    "symbol",
    "position_ticket",
    "order_ticket",
    "deal_ticket",
    "ticket_source",
    "magic_number",
    "direction",
    "lot",
    "entry_price",
    "sl_price",
    "tp_price",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "signal_key",
    "order_key",
    "payload_key",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "source_payload_csv",
    "sender_report_json",
    "position_status",
    "last_seen_utc",
    "close_status",
    "close_reason",
    "source_sender_status",
    "source_sender_row_index",
    "source_payload_row_index",
    "source_order_send_ok",
    "notes",
]
```

### 3. Add helper functions before `parse_args()`

```python
def clean_int(x: Any, default: int = 0) -> int:
    try:
        if x is None or x == "":
            return int(default)
        if pd.isna(x):
            return int(default)
    except Exception:
        pass
    try:
        return int(float(x))
    except Exception:
        return int(default)


def clean_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    text = clean_str(x).strip().lower()
    return text in {"true", "1", "yes", "y"}


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def normalize_symbol_from_broker(broker_symbol: str) -> str:
    text = broker_symbol.strip()
    if not text:
        return ""
    for sep in ["#", ".", "_"]:
        if sep in text:
            text = text.split(sep)[0]
    return text.upper()


def registry_preview_enabled(args: argparse.Namespace) -> bool:
    return bool(args.registry_preview_out_csv or args.registry_preview_out_json)


def infer_registry_strategy_key(payload_row: pd.Series, strategy_id: str = "") -> str:
    for col in ["router_strategy_slot", "strategy_key", "pair_name"]:
        value = clean_str(payload_row.get(col))
        if value:
            return value
    text = clean_str(strategy_id, clean_str(payload_row.get("strategy_id"), clean_str(payload_row.get("router_strategy_id"))))
    upper = text.upper()
    if "C_ENV" in upper or "BUY_C" in upper:
        return "BUY_C_ENV_RR2_72H"
    if "H1H4_BEAR" in upper or "BEAR_AB" in upper or "SELL_H1H4_BEAR_AB" in upper:
        return "SELL_H1H4_BEAR_AB"
    return text


def infer_registry_strategy_id(payload_row: pd.Series) -> str:
    return clean_str(payload_row.get("strategy_id"), clean_str(payload_row.get("router_strategy_id")))


def infer_registry_strategy_alias(strategy_key: str, strategy_id: str, direction: str) -> str:
    text = f"{strategy_key} {strategy_id}".upper()
    if "BUY_C" in text or "C_ENV" in text:
        return "BUY_C"
    if "SELL_H1H4_BEAR_AB" in text or "BEAR_AB" in text or "H1H4_BEAR" in text:
        return "SELL_AB"
    if "BTC" in text:
        return "BTC"
    return f"{direction.upper()}_UNK"


def build_registry_payload_lookup(payload_df: pd.DataFrame) -> dict[tuple[str, str, int], pd.Series]:
    lookup: dict[tuple[str, str, int], pd.Series] = {}
    if payload_df.empty:
        return lookup
    for idx, row in payload_df.iterrows():
        source_row_index = int(idx) + 1
        order_key = clean_str(row.get("order_key"), clean_str(row.get("payload_key")))
        payload_key = clean_str(row.get("payload_key"), order_key)
        if order_key:
            lookup[("order_key", order_key, 0)] = row
        if payload_key:
            lookup[("payload_key", payload_key, 0)] = row
        lookup[("row_index", "", source_row_index)] = row
    return lookup


def find_registry_payload_row(sender_row: pd.Series, lookup: dict[tuple[str, str, int], pd.Series]) -> tuple[pd.Series | None, int]:
    order_key = clean_str(sender_row.get("order_key"))
    payload_key = clean_str(sender_row.get("payload_key"))
    row_index = clean_int(sender_row.get("row_index"), 0)
    if order_key and ("order_key", order_key, 0) in lookup:
        row = lookup[("order_key", order_key, 0)]
        return row, clean_int(row.name, -1) + 1
    if payload_key and ("payload_key", payload_key, 0) in lookup:
        row = lookup[("payload_key", payload_key, 0)]
        return row, clean_int(row.name, -1) + 1
    if row_index and ("row_index", "", row_index) in lookup:
        row = lookup[("row_index", "", row_index)]
        return row, row_index
    return None, 0


def is_registry_preview_eligible(sender_row: pd.Series, *, include_dry_run_check_ok: bool, include_sent: bool) -> bool:
    status = clean_str(sender_row.get("order_status"))
    if include_dry_run_check_ok and status == "DRY_RUN_ORDER_CHECK_OK":
        return True
    if include_sent and status == "SENT" and clean_bool(sender_row.get("order_send_ok")):
        return True
    return False


def sender_ticket_or_fallback(sender_row: pd.Series, keys: list[str], fallback: int) -> tuple[int, str]:
    for key in keys:
        value = clean_int(sender_row.get(key), 0)
        if value != 0:
            return value, "mt5_report"
    return int(fallback), "fallback_preview"


def build_registry_preview_rows(
    *,
    results_df: pd.DataFrame,
    payload_df: pd.DataFrame,
    args: argparse.Namespace,
    account_info: dict[str, Any],
    out_dir: Path,
) -> list[dict[str, Any]]:
    if results_df.empty:
        return []

    now = utc_now_text()
    lookup = build_registry_payload_lookup(payload_df)
    rows: list[dict[str, Any]] = []

    for eligible_offset, (_, sender_row) in enumerate(results_df.iterrows()):
        if not is_registry_preview_eligible(
            sender_row,
            include_dry_run_check_ok=bool(args.registry_preview_include_dry_run_check_ok),
            include_sent=bool(args.registry_preview_include_sent),
        ):
            continue

        payload_row, source_payload_row_index = find_registry_payload_row(sender_row, lookup)
        pr = payload_row if payload_row is not None else sender_row

        source_status = clean_str(sender_row.get("order_status"))
        direction = clean_str(sender_row.get("direction"), clean_str(pr.get("direction"))).upper()
        broker_symbol = clean_str(sender_row.get("broker_symbol"), clean_str(pr.get("broker_symbol"), clean_str(pr.get("symbol"))))
        symbol = clean_str(pr.get("symbol"), normalize_symbol_from_broker(broker_symbol))
        strategy_id = infer_registry_strategy_id(pr)
        strategy_key = infer_registry_strategy_key(pr, strategy_id)
        strategy_alias = infer_registry_strategy_alias(strategy_key, strategy_id, direction)

        payload_key = clean_str(pr.get("payload_key"), clean_str(sender_row.get("payload_key"), clean_str(pr.get("order_key"), clean_str(sender_row.get("order_key")))))
        order_key = clean_str(pr.get("order_key"), clean_str(sender_row.get("order_key"), payload_key))
        signal_key = clean_str(pr.get("signal_key"), clean_str(sender_row.get("signal_key")))

        lot = clean_float(sender_row.get("lot"))
        if lot is None:
            lot = clean_float(pr.get("lot")) or 0.0

        entry_price = clean_float(sender_row.get("current_execution_price"))
        if entry_price is None:
            entry_price = clean_float(pr.get("entry_price"))
        if entry_price is None:
            entry_price = clean_float(pr.get("entry_price_reference"))
        if entry_price is None:
            entry_price = 0.0

        sl_price = clean_float(sender_row.get("sl_price"))
        if sl_price is None:
            sl_price = clean_float(pr.get("sl_price")) or 0.0

        tp_price = clean_float(sender_row.get("tp_price"))
        if tp_price is None:
            tp_price = clean_float(pr.get("tp_price")) or 0.0

        if source_status == "SENT" and clean_bool(sender_row.get("order_send_ok")):
            order_ticket, order_ticket_source = sender_ticket_or_fallback(
                sender_row,
                ["order_ticket", "order", "order_id"],
                int(args.registry_preview_order_ticket_start) + eligible_offset,
            )
            deal_ticket, deal_ticket_source = sender_ticket_or_fallback(
                sender_row,
                ["deal_ticket", "deal", "deal_id"],
                int(args.registry_preview_deal_ticket_start) + eligible_offset,
            )
            position_ticket, position_ticket_source = sender_ticket_or_fallback(
                sender_row,
                ["position_ticket", "position", "ticket"],
                int(args.registry_preview_position_ticket_start) + eligible_offset,
            )
            ticket_source = "mt5_report" if "mt5_report" in {order_ticket_source, deal_ticket_source, position_ticket_source} else "fallback_preview"
        else:
            position_ticket = int(args.registry_preview_position_ticket_start) + eligible_offset
            order_ticket = int(args.registry_preview_order_ticket_start) + eligible_offset
            deal_ticket = int(args.registry_preview_deal_ticket_start) + eligible_offset
            ticket_source = "fallback_preview"

        row = {
            "schema_version": REGISTRY_PREVIEW_SCHEMA_VERSION,
            "created_at_utc": now,
            "updated_at_utc": now,
            "account_login": clean_int(account_info.get("login"), 0),
            "account_server": clean_str(account_info.get("server")),
            "broker_symbol": broker_symbol,
            "symbol": symbol,
            "position_ticket": position_ticket,
            "order_ticket": order_ticket,
            "deal_ticket": deal_ticket,
            "ticket_source": ticket_source,
            "magic_number": clean_int(pr.get("magic_number"), clean_int(sender_row.get("magic"), 26050601)),
            "direction": direction,
            "lot": float(lot),
            "entry_price": float(entry_price),
            "sl_price": float(sl_price),
            "tp_price": float(tp_price),
            "strategy_key": strategy_key,
            "strategy_alias": strategy_alias,
            "strategy_id": strategy_id,
            "condition_id": clean_str(pr.get("condition_id"), strategy_id),
            "signal_key": signal_key,
            "order_key": order_key,
            "payload_key": payload_key,
            "router_strategy_slot": clean_str(pr.get("router_strategy_slot"), strategy_key),
            "router_strategy_id": clean_str(pr.get("router_strategy_id"), strategy_id),
            "candidate_rank": clean_str(pr.get("candidate_rank")),
            "source_payload_csv": str(args.input_csv),
            "sender_report_json": str(out_dir / "mt5_order_send_report.json"),
            "position_status": clean_str(args.registry_preview_position_status, REGISTRY_PREVIEW_DEFAULT_POSITION_STATUS).upper(),
            "last_seen_utc": now,
            "close_status": "",
            "close_reason": "",
            "source_sender_status": source_status,
            "source_sender_row_index": clean_int(sender_row.get("row_index"), eligible_offset + 1),
            "source_payload_row_index": int(source_payload_row_index),
            "source_order_send_ok": clean_bool(sender_row.get("order_send_ok")),
            "notes": "sender-native disabled-by-default registry preview; no production registry mutation",
        }
        rows.append(row)

    return rows


def write_registry_preview_outputs(
    *,
    preview_rows: list[dict[str, Any]],
    args: argparse.Namespace,
    out_dir: Path,
    results_df: pd.DataFrame,
) -> dict[str, Any]:
    out_df = pd.DataFrame([{col: row.get(col, "") for col in REGISTRY_PREVIEW_COLUMNS} for row in preview_rows], columns=REGISTRY_PREVIEW_COLUMNS)

    if args.registry_preview_out_csv:
        write_csv(out_df, args.registry_preview_out_csv)
    if args.registry_preview_out_json:
        summary = {
            "schema_version": REGISTRY_PREVIEW_SCHEMA_VERSION,
            "preview_ok": True,
            "reason": "REGISTRY_PREVIEW_ROWS_BUILT" if preview_rows else "NO_ELIGIBLE_SENDER_ROWS",
            "output_csv": str(args.registry_preview_out_csv or ""),
            "output_json": str(args.registry_preview_out_json or ""),
            "sender_rows_in": int(len(results_df)),
            "registry_preview_rows": int(len(out_df)),
            "include_dry_run_check_ok": bool(args.registry_preview_include_dry_run_check_ok),
            "include_sent": bool(args.registry_preview_include_sent),
            "position_status": clean_str(args.registry_preview_position_status, REGISTRY_PREVIEW_DEFAULT_POSITION_STATUS).upper(),
            "position_ticket_start": int(args.registry_preview_position_ticket_start),
            "order_ticket_start": int(args.registry_preview_order_ticket_start),
            "deal_ticket_start": int(args.registry_preview_deal_ticket_start),
            "safety": {
                "production_registry_mutated": False,
                "order_ledger_mutated_by_preview": False,
                "trigger_state_mutated": False,
                "order_check_called_by_preview": False,
                "order_send_called_by_preview": False,
            },
            "records": out_df.to_dict(orient="records"),
        }
        write_text(args.registry_preview_out_json, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))

    return {
        "schema_version": REGISTRY_PREVIEW_SCHEMA_VERSION,
        "preview_enabled": True,
        "preview_ok": True,
        "reason": "REGISTRY_PREVIEW_ROWS_BUILT" if preview_rows else "NO_ELIGIBLE_SENDER_ROWS",
        "output_csv": str(args.registry_preview_out_csv or ""),
        "output_json": str(args.registry_preview_out_json or ""),
        "registry_preview_rows": int(len(out_df)),
        "include_dry_run_check_ok": bool(args.registry_preview_include_dry_run_check_ok),
        "include_sent": bool(args.registry_preview_include_sent),
    }
```

### 4. Add CLI arguments in `parse_args()` before `args = p.parse_args()`

```python
    p.add_argument("--registry-preview-out-csv", default=None, help="Optional disabled-by-default registry preview CSV output path. Never writes production registry.")
    p.add_argument("--registry-preview-out-json", default=None, help="Optional disabled-by-default registry preview JSON summary output path. Never writes production registry.")
    p.add_argument("--registry-preview-position-status", default=REGISTRY_PREVIEW_DEFAULT_POSITION_STATUS)
    p.add_argument("--registry-preview-position-ticket-start", type=int, default=REGISTRY_PREVIEW_DEFAULT_POSITION_TICKET_START)
    p.add_argument("--registry-preview-order-ticket-start", type=int, default=REGISTRY_PREVIEW_DEFAULT_ORDER_TICKET_START)
    p.add_argument("--registry-preview-deal-ticket-start", type=int, default=REGISTRY_PREVIEW_DEFAULT_DEAL_TICKET_START)
    p.add_argument("--registry-preview-include-dry-run-check-ok", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--registry-preview-include-sent", action="store_true")
```

### 5. Insert optional export before `mt5_order_send_report.json` is written

Find this block near the end of `main()`:

```python
        report.update({
            "rows_in": int(len(df)),
            "rows_out": int(len(out)),
            "dry_run_check_ok_rows": int((out.get("order_status", pd.Series(dtype=str)) == "DRY_RUN_ORDER_CHECK_OK").sum()) if not out.empty else 0,
            "sent_rows": int((out.get("order_status", pd.Series(dtype=str)) == "SENT").sum()) if not out.empty else 0,
            "blocked_position_policy_rows": int((out.get("order_status", pd.Series(dtype=str)) == "BLOCKED_POSITION_POLICY").sum()) if not out.empty else 0,
            "blocked_existing_symbol_position_rows": int((out.get("order_status", pd.Series(dtype=str)).isin(["BLOCKED_EXISTING_SYMBOL_POSITION", "BLOCKED_POSITION_POLICY"])).sum()) if not out.empty else 0,
            "error_rows": int(out["order_status"].astype(str).str.startswith(("ERROR", "BLOCKED")).sum()) if "order_status" in out.columns and not out.empty else 0,
            "results": rows,
        })
        write_text(out_dir / "mt5_order_send_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))
```

Replace it with:

```python
        report.update({
            "rows_in": int(len(df)),
            "rows_out": int(len(out)),
            "dry_run_check_ok_rows": int((out.get("order_status", pd.Series(dtype=str)) == "DRY_RUN_ORDER_CHECK_OK").sum()) if not out.empty else 0,
            "sent_rows": int((out.get("order_status", pd.Series(dtype=str)) == "SENT").sum()) if not out.empty else 0,
            "blocked_position_policy_rows": int((out.get("order_status", pd.Series(dtype=str)) == "BLOCKED_POSITION_POLICY").sum()) if not out.empty else 0,
            "blocked_existing_symbol_position_rows": int((out.get("order_status", pd.Series(dtype=str)).isin(["BLOCKED_EXISTING_SYMBOL_POSITION", "BLOCKED_POSITION_POLICY"])).sum()) if not out.empty else 0,
            "error_rows": int(out["order_status"].astype(str).str.startswith(("ERROR", "BLOCKED")).sum()) if "order_status" in out.columns and not out.empty else 0,
            "results": rows,
        })

        if registry_preview_enabled(args):
            preview_rows = build_registry_preview_rows(
                results_df=out,
                payload_df=df,
                args=args,
                account_info=account_info,
                out_dir=out_dir,
            )
            report["registry_preview"] = write_registry_preview_outputs(
                preview_rows=preview_rows,
                args=args,
                out_dir=out_dir,
                results_df=out,
            )
        else:
            report["registry_preview"] = {
                "schema_version": REGISTRY_PREVIEW_SCHEMA_VERSION,
                "preview_enabled": False,
                "preview_ok": True,
                "reason": "REGISTRY_PREVIEW_DISABLED_NO_OUTPUT_FLAGS",
                "registry_preview_rows": 0,
            }

        write_text(out_dir / "mt5_order_send_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))
```

### 6. Add console lines after existing `error_rows` print

Find:

```python
        print(f"error_rows: {report['error_rows']}")
```

Add immediately after:

```python
        registry_preview_report = report.get("registry_preview", {})
        if isinstance(registry_preview_report, dict):
            print(f"registry_preview_enabled: {registry_preview_report.get('preview_enabled')}")
            print(f"registry_preview_rows: {registry_preview_report.get('registry_preview_rows')}")
            if registry_preview_report.get("output_csv"):
                print(f"registry_preview_out_csv: {registry_preview_report.get('output_csv')}")
            if registry_preview_report.get("output_json"):
                print(f"registry_preview_out_json: {registry_preview_report.get('output_json')}")
```

## Post-implementation commands

### A. Existing canonical BAT should still pass

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run_with_verify.bat
```

### B. Sender-native preview dry-run example

```cmd
python scripts\send_mt5_order_from_payload.py --input-csv data\r\ff\f\order_payloads.csv --order-ledger-csv data\r\sender_hook\dry_run_order_ledger.csv --out-dir data\r\sender_hook\sender --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --require-demo-account --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05 --registry-preview-out-csv data\r\sender_hook\registry_preview.csv --registry-preview-out-json data\r\sender_hook\registry_preview.json
```

Expected:

```text
send_requested: False
order_send_called_count: 0
dry_run_check_ok_rows: 1
sent_rows: 0
error_rows: 0
registry_preview_enabled: True
registry_preview_rows: 1
```

### C. Reconcile sender-native preview

```cmd
python scripts\build_gold_multi_strategy_mock_positions_from_registry.py --registry-csv data\r\sender_hook\registry_preview.csv --output-csv data\r\sender_hook\mp.csv
```

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\r\sender_hook\registry_preview.csv --positions-csv data\r\sender_hook\mp.csv --out-dir data\r\sender_hook\r --symbol GOLD#
```

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py --input-csv data\r\ff\f\order_payloads.csv --positions-csv data\r\sender_hook\mp.csv --registry-csv data\r\sender_hook\registry_preview.csv --order-ledger-csv data\r\sender_hook\dry_run_order_ledger.csv --out-dir data\r\sender_hook\p --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02
```

Expected:

```text
REGISTRY_ACTIVE_MATCHED=1
same_strategy_blocked_rows=1
registry_inconsistency_blocked_rows=0
```
