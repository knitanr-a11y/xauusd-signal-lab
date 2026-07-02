#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

BTC4_TP1_MAGIC = 26070441
BTC4_TP2_MAGIC = 26070442
DEFAULT_STATE_JSON = Path("data/runtime_state/btc/youtube_candidates/btc4_split_position_state.json")
DEFAULT_REPORT_JSON = Path("data/runtime_state/btc/youtube_candidates/latest_position_manager_report.json")


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def plan_pair_action(*, pair_status: str, tp1_open: bool, tp2_open: bool, tp1_profitably_closed: bool, tp2_sl_at_be: bool) -> str:
    if pair_status not in {"ARMED", "PARTIAL_SEND_ANOMALY", "BE_MOVED"}:
        return "NO_ACTIVE_PAIR"
    if not tp1_open and not tp2_open:
        return "PAIR_CLOSED"
    if tp1_open and not tp2_open:
        return "ANOMALY_TP2_MISSING"
    if tp1_open and tp2_open:
        return "WAIT_TP1"
    if not tp1_open and tp2_open:
        if tp2_sl_at_be:
            return "BE_ALREADY_SET"
        if tp1_profitably_closed:
            return "MOVE_TP2_TO_BE"
        return "WAIT_TP1_CLOSE_CONFIRMATION"
    return "NO_ACTION"


def _load_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"MetaTrader5 import failed: {exc}") from exc
    return mt5


def _position_dict(position: Any) -> dict[str, Any]:
    if hasattr(position, "_asdict"):
        return dict(position._asdict())
    return {name: getattr(position, name) for name in dir(position) if not name.startswith("_")}


def _deal_dict(deal: Any) -> dict[str, Any]:
    if hasattr(deal, "_asdict"):
        return dict(deal._asdict())
    return {name: getattr(deal, name) for name in dir(deal) if not name.startswith("_")}


def inspect_account(mt5: Any, *, expected_login: int, require_demo: bool, require_hedging: bool) -> dict[str, Any]:
    if not mt5.initialize():
        return {"ok": False, "reason": f"MT5_INITIALIZE_FAILED: {mt5.last_error()}"}
    account = mt5.account_info()
    if account is None:
        return {"ok": False, "reason": f"ACCOUNT_INFO_FAILED: {mt5.last_error()}"}
    login = int(getattr(account, "login", 0))
    trade_mode = int(getattr(account, "trade_mode", -1))
    margin_mode = int(getattr(account, "margin_mode", -1))
    demo_mode = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
    hedging_mode = int(getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", 2))
    errors: list[str] = []
    if expected_login and login != int(expected_login):
        errors.append(f"login mismatch actual={login} expected={expected_login}")
    if require_demo and trade_mode != demo_mode:
        errors.append(f"account is not demo trade_mode={trade_mode}")
    if require_hedging and margin_mode != hedging_mode:
        errors.append(f"account is not hedging margin_mode={margin_mode}")
    return {
        "ok": not errors,
        "reason": "PASS" if not errors else "; ".join(errors),
        "login": login,
        "trade_mode": trade_mode,
        "margin_mode": margin_mode,
        "demo": trade_mode == demo_mode,
        "hedging": margin_mode == hedging_mode,
    }


def _positions_by_magic(mt5: Any, symbol: str) -> dict[int, list[dict[str, Any]]]:
    positions = mt5.positions_get(symbol=symbol) or []
    output: dict[int, list[dict[str, Any]]] = {}
    for position in positions:
        item = _position_dict(position)
        output.setdefault(int(item.get("magic", 0) or 0), []).append(item)
    return output


def _tp1_profitably_closed(mt5: Any, *, magic: int, armed_at_utc: str) -> bool:
    try:
        start = datetime.fromisoformat(armed_at_utc.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
    except Exception:
        start = datetime.now(UTC) - timedelta(days=30)
    deals = mt5.history_deals_get(start, datetime.now(UTC) + timedelta(minutes=1)) or []
    entry_out = {
        int(getattr(mt5, "DEAL_ENTRY_OUT", 1)),
        int(getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)),
    }
    for deal in deals:
        item = _deal_dict(deal)
        if int(item.get("magic", 0) or 0) != int(magic):
            continue
        if int(item.get("entry", -1)) not in entry_out:
            continue
        net = float(item.get("profit", 0.0) or 0.0) + float(item.get("swap", 0.0) or 0.0) + float(item.get("commission", 0.0) or 0.0)
        if net > 0.0:
            return True
    return False


def _sl_is_be(position: dict[str, Any]) -> bool:
    open_price = float(position.get("price_open", 0.0) or 0.0)
    sl = float(position.get("sl", 0.0) or 0.0)
    return open_price > 0 and sl > 0 and abs(open_price - sl) <= max(1e-8, open_price * 1e-8)


def manage(args: argparse.Namespace) -> dict[str, Any]:
    mt5 = _load_mt5()
    account = inspect_account(
        mt5,
        expected_login=int(args.expected_login),
        require_demo=bool(args.require_demo_account),
        require_hedging=bool(args.require_hedging),
    )
    report: dict[str, Any] = {
        "schema_version": "btc_youtube_position_manager_v1",
        "managed_at_utc": utc_text(),
        "account": account,
        "send_requested": bool(args.send),
        "actions": [],
        "errors": [],
        "cycle_ok": bool(account.get("ok", False)),
    }
    if not account.get("ok"):
        write_json(args.report_json, report)
        mt5.shutdown()
        return report

    state = read_json(args.state_json, {"pairs": []})
    pairs = state.get("pairs", []) if isinstance(state, dict) else []
    positions = _positions_by_magic(mt5, args.symbol)
    changed = False
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        status = str(pair.get("status", ""))
        tp1_positions = positions.get(int(pair.get("tp1_magic", BTC4_TP1_MAGIC)), [])
        tp2_positions = positions.get(int(pair.get("tp2_magic", BTC4_TP2_MAGIC)), [])
        tp1_open = bool(tp1_positions)
        tp2_open = bool(tp2_positions)
        tp2_position = tp2_positions[0] if tp2_positions else {}
        profitable_close = _tp1_profitably_closed(
            mt5,
            magic=int(pair.get("tp1_magic", BTC4_TP1_MAGIC)),
            armed_at_utc=str(pair.get("armed_at_utc", utc_text())),
        ) if (not tp1_open and tp2_open) else False
        action = plan_pair_action(
            pair_status=status,
            tp1_open=tp1_open,
            tp2_open=tp2_open,
            tp1_profitably_closed=profitable_close,
            tp2_sl_at_be=_sl_is_be(tp2_position) if tp2_open else False,
        )
        action_report: dict[str, Any] = {
            "signal_key": pair.get("signal_key", ""),
            "status_before": status,
            "planned_action": action,
            "tp1_open": tp1_open,
            "tp2_open": tp2_open,
            "tp1_profitably_closed": profitable_close,
            "sent": False,
        }
        if action == "MOVE_TP2_TO_BE":
            if not args.send:
                action_report["result"] = "DRY_RUN_WOULD_MOVE_TP2_TO_BE"
            else:
                ticket = int(tp2_position.get("ticket", 0) or 0)
                price_open = float(tp2_position.get("price_open", 0.0) or 0.0)
                tp = float(tp2_position.get("tp", 0.0) or 0.0)
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "symbol": args.symbol,
                    "sl": price_open,
                    "tp": tp,
                    "magic": int(pair.get("tp2_magic", BTC4_TP2_MAGIC)),
                    "comment": "BTC4 TP1 hit -> TP2 BE",
                }
                result = mt5.order_send(request)
                action_report["order_result"] = None if result is None else _position_dict(result)
                retcode = None if result is None else int(getattr(result, "retcode", -1))
                success_codes = {
                    int(getattr(mt5, "TRADE_RETCODE_DONE", 10009)),
                    int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
                }
                if retcode in success_codes:
                    pair["status"] = "BE_MOVED"
                    pair["be_moved_at_utc"] = utc_text()
                    action_report["sent"] = True
                    action_report["result"] = "TP2_BE_MOVED"
                    changed = True
                else:
                    action_report["result"] = f"TP2_BE_MOVE_FAILED retcode={retcode}"
                    report["errors"].append(action_report["result"])
        elif action == "PAIR_CLOSED":
            pair["status"] = "CLOSED"
            pair["closed_at_utc"] = utc_text()
            changed = True
            action_report["result"] = "PAIR_MARKED_CLOSED"
        elif action.startswith("ANOMALY"):
            pair["status"] = action
            changed = True
            report["errors"].append(action)
            action_report["result"] = action
        else:
            action_report["result"] = action
        report["actions"].append(action_report)

    if changed:
        state["updated_at_utc"] = utc_text()
        write_json(args.state_json, state)
    report["cycle_ok"] = bool(account.get("ok") and not report["errors"])
    report["state_json"] = str(args.state_json)
    write_json(args.report_json, report)
    mt5.shutdown()
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage BTC4 split-position break-even state on MT5 demo account.")
    parser.add_argument("--state-json", type=Path, default=DEFAULT_STATE_JSON)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--symbol", default="BTCUSD#")
    parser.add_argument("--expected-login", type=int, default=75539039)
    parser.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--require-hedging", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--send", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = manage(args)
    except Exception as exc:
        report = {
            "schema_version": "btc_youtube_position_manager_v1",
            "managed_at_utc": utc_text(),
            "cycle_ok": False,
            "errors": [repr(exc)],
        }
        write_json(args.report_json, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if report.get("cycle_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
