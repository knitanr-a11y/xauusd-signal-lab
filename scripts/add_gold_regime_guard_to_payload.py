from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gold_regime_guard import DEFAULT_HISTORY_CSV, evaluate_from_history_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "guarded_payloads"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("payload json must be an object")
    return data


def extract_current_signal(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current_signal_snapshot") or payload.get("current_signal") or payload
    if not isinstance(current, dict):
        raise ValueError("current signal snapshot must be an object")
    return current


def attach_guard(payload: dict[str, Any], guard: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["regime_guard"] = guard
    guardrails = out.get("guardrails")
    if isinstance(guardrails, list):
        guardrails = list(guardrails)
    else:
        guardrails = []
    if guard.get("gold_abc_buy_danger_regime"):
        guardrails.append(
            "GOLD ABC BUY danger regime is active. This is a warning-only regime flag based on recent completed GOLD ABC BUY outcomes, not current-trade outcome leakage. Require stronger chart confirmation and treat caution/strong_caution as a likely no-trade."
        )
    out["guardrails"] = guardrails
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach GOLD ABC BUY warning-only danger regime guard to an AI payload JSON.")
    parser.add_argument("--payload-json", type=Path, required=True)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--last-n", type=int, default=3)
    parser.add_argument("--min-losses", type=int, default=3)
    parser.add_argument("--lookback-days", type=int, default=30)
    args = parser.parse_args()

    payload_json = resolve_path(args.payload_json)
    history_csv = resolve_path(args.history_csv)
    out_json = resolve_path(args.out_json) if args.out_json else DEFAULT_OUT_DIR / f"{payload_json.stem}_with_gold_regime_guard.json"

    payload = read_json(payload_json)
    current = extract_current_signal(payload)
    guard = evaluate_from_history_csv(
        current,
        history_csv=history_csv,
        last_n=args.last_n,
        min_losses=args.min_losses,
        lookback_days=args.lookback_days,
    )
    guarded = attach_guard(payload, guard)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(guarded, f, ensure_ascii=False, indent=2, default=str)

    print("Payload:", payload_json)
    print("History CSV:", history_csv)
    print("Saved guarded payload:", out_json)
    print("gold_abc_buy_danger_regime:", guard.get("gold_abc_buy_danger_regime"))
    print("warning_only:", guard.get("warning_only"))
    print("reason:", guard.get("reason"))
    print("recent_results:", guard.get("recent_results"))
    print("recent_r_values:", guard.get("recent_r_values"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
