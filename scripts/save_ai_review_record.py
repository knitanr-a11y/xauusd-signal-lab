from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PAYLOAD_JSON = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_signal_review_payload_row_0.json"
DEFAULT_AI_RESPONSE_JSON = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "sample_ai_response.json"
DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_ledger.csv"

LEDGER_COLUMNS = [
    "recorded_at",
    "signal_id",
    "payload_sha256",
    "ai_response_sha256",
    "broker_profile",
    "symbol",
    "preset",
    "source_row",
    "signal_model",
    "side",
    "jst_entry_time",
    "jst_entry_hour",
    "entry_price",
    "sl",
    "tp",
    "risk",
    "entry_risk_atr_ratio",
    "entry_spread_price_atr_ratio",
    "h1_ema_alignment",
    "m15_ema_alignment",
    "side_matches_h1_ema",
    "side_matches_m15_ema",
    "macd_hist_supports_side",
    "macd_hist_delta_supports_side",
    "winning_pattern_match",
    "losing_pattern_similarity",
    "final_risk_label",
    "evidence_for_entry",
    "evidence_against_entry",
    "human_checkpoints",
    "actual_result",
    "actual_r",
    "actual_exit_reason",
    "notes",
]

REQUIRED_AI_RESPONSE_KEYS = [
    "winning_pattern_match",
    "losing_pattern_similarity",
    "final_risk_label",
    "evidence_for_entry",
    "evidence_against_entry",
    "human_checkpoints",
    "do_not_use_as_final_trade_decision",
]

ALLOWED_WIN_MATCH = {"high", "medium", "low"}
ALLOWED_LOSS_SIM = {"high", "medium", "low"}
ALLOWED_RISK_LABEL = {"normal", "caution", "strong_caution", "skip_candidate"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def normalize_list(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(str(x) for x in value)
    return str(value)


def normalize_optional(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def validate_ai_response(response: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_AI_RESPONSE_KEYS if key not in response]
    if missing:
        raise ValueError(f"AI response missing required keys: {missing}")

    if response["winning_pattern_match"] not in ALLOWED_WIN_MATCH:
        raise ValueError(f"Invalid winning_pattern_match: {response['winning_pattern_match']}")
    if response["losing_pattern_similarity"] not in ALLOWED_LOSS_SIM:
        raise ValueError(f"Invalid losing_pattern_similarity: {response['losing_pattern_similarity']}")
    if response["final_risk_label"] not in ALLOWED_RISK_LABEL:
        raise ValueError(f"Invalid final_risk_label: {response['final_risk_label']}")
    if response["do_not_use_as_final_trade_decision"] is not True:
        raise ValueError("AI response must set do_not_use_as_final_trade_decision=true")

    for key in ["evidence_for_entry", "evidence_against_entry", "human_checkpoints"]:
        if not isinstance(response[key], list):
            raise ValueError(f"AI response key must be a list: {key}")


def build_signal_id(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata", {})
    signal = payload.get("current_signal_snapshot", {})
    parts = [
        str(metadata.get("preset", "")),
        str(signal.get("combined_signal_source", "")),
        str(signal.get("side", "")),
        str(signal.get("jst_entry_time", "")),
        str(signal.get("entry_price", "")),
    ]
    raw = "|".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"sig_{digest}"


def infer_actual_outcome_from_payload(
    payload: dict[str, Any],
    *,
    actual_result_arg: str,
    actual_r_arg: str,
    actual_exit_reason_arg: str,
) -> tuple[str, str, str, str]:
    """Resolve actual outcome fields for the ledger.

    Live/shadow-forward payloads usually do not know the outcome yet, so CLI args stay empty.
    Historical case-db replay payloads can include `current_row_label_audit_not_sent_as_features`.
    That audit block is not part of `current_signal_snapshot` and is not used as an AI input feature,
    but it is safe and useful for post-review ledger analysis.
    """
    audit = payload.get("current_row_label_audit_not_sent_as_features", {})
    if not isinstance(audit, dict):
        audit = {}

    actual_result = actual_result_arg or normalize_optional(audit.get("result"))
    actual_r = actual_r_arg or normalize_optional(audit.get("r"))
    actual_exit_reason = actual_exit_reason_arg or normalize_optional(audit.get("exit_reason"))

    source = "cli_args"
    if not any([actual_result_arg, actual_r_arg, actual_exit_reason_arg]) and any([actual_result, actual_r, actual_exit_reason]):
        source = "payload_current_row_label_audit"
    elif not any([actual_result, actual_r, actual_exit_reason]):
        source = "empty_unknown_outcome"

    return actual_result, actual_r, actual_exit_reason, source


def build_ledger_row(
    *,
    payload: dict[str, Any],
    response: dict[str, Any],
    payload_path: Path,
    response_path: Path,
    actual_result: str,
    actual_r: str,
    actual_exit_reason: str,
    notes: str,
) -> dict[str, Any]:
    metadata = payload.get("metadata", {})
    signal = payload.get("current_signal_snapshot", {})

    row = {
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "signal_id": build_signal_id(payload),
        "payload_sha256": sha256_file(payload_path),
        "ai_response_sha256": sha256_file(response_path),
        "broker_profile": metadata.get("broker_profile", ""),
        "symbol": metadata.get("symbol", ""),
        "preset": metadata.get("preset", ""),
        "source_row": metadata.get("current_case_source_row", ""),
        "signal_model": signal.get("combined_signal_source", ""),
        "side": signal.get("side", ""),
        "jst_entry_time": signal.get("jst_entry_time", ""),
        "jst_entry_hour": signal.get("jst_entry_hour", ""),
        "entry_price": signal.get("entry_price", ""),
        "sl": signal.get("sl", ""),
        "tp": signal.get("tp", ""),
        "risk": signal.get("risk", ""),
        "entry_risk_atr_ratio": signal.get("entry_risk_atr_ratio", ""),
        "entry_spread_price_atr_ratio": signal.get("entry_spread_price_atr_ratio", ""),
        "h1_ema_alignment": signal.get("h1_ema_alignment", ""),
        "m15_ema_alignment": signal.get("m15_ema_alignment", ""),
        "side_matches_h1_ema": signal.get("side_matches_h1_ema", ""),
        "side_matches_m15_ema": signal.get("side_matches_m15_ema", ""),
        "macd_hist_supports_side": signal.get("macd_hist_supports_side", ""),
        "macd_hist_delta_supports_side": signal.get("macd_hist_delta_supports_side", ""),
        "winning_pattern_match": response.get("winning_pattern_match", ""),
        "losing_pattern_similarity": response.get("losing_pattern_similarity", ""),
        "final_risk_label": response.get("final_risk_label", ""),
        "evidence_for_entry": normalize_list(response.get("evidence_for_entry")),
        "evidence_against_entry": normalize_list(response.get("evidence_against_entry")),
        "human_checkpoints": normalize_list(response.get("human_checkpoints")),
        "actual_result": actual_result,
        "actual_r": actual_r,
        "actual_exit_reason": actual_exit_reason,
        "notes": notes,
    }
    return row


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})


def write_sample_ai_response(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = {
        "winning_pattern_match": "medium",
        "losing_pattern_similarity": "medium",
        "final_risk_label": "caution",
        "evidence_for_entry": [
            "Rule-based signal is already selected by the tested preset.",
            "M15 direction and MACD support are present in the sample snapshot."
        ],
        "evidence_against_entry": [
            "H1 alignment is not clearly supportive.",
            "Risk/ATR is relatively large, so the trade may need more room."
        ],
        "closest_win_case_notes": [
            "Compare with same model and side winning cases first."
        ],
        "closest_loss_case_notes": [
            "Do not mark skip_candidate based on one shared loss feature only."
        ],
        "human_checkpoints": [
            "Check whether the next M15 candle maintains the breakout area.",
            "Check whether spread remains normal before entry."
        ],
        "do_not_use_as_final_trade_decision": True
    }
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Save one AI review response into a CSV ledger for shadow-mode verification.")
    parser.add_argument("--payload-json", type=Path, default=DEFAULT_PAYLOAD_JSON)
    parser.add_argument("--ai-response-json", type=Path, default=DEFAULT_AI_RESPONSE_JSON)
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--write-sample-response", action="store_true", help="Create a sample AI response JSON and exit.")
    parser.add_argument("--actual-result", type=str, default="", help="Optional after outcome is known: win/loss/timeout/etc.")
    parser.add_argument("--actual-r", type=str, default="", help="Optional after outcome is known.")
    parser.add_argument("--actual-exit-reason", type=str, default="", help="Optional after outcome is known.")
    parser.add_argument("--notes", type=str, default="")
    args = parser.parse_args()

    payload_path = args.payload_json if args.payload_json.is_absolute() else PROJECT_ROOT / args.payload_json
    response_path = args.ai_response_json if args.ai_response_json.is_absolute() else PROJECT_ROOT / args.ai_response_json
    ledger_path = args.ledger_csv if args.ledger_csv.is_absolute() else PROJECT_ROOT / args.ledger_csv

    if args.write_sample_response:
        write_sample_ai_response(response_path)
        print("Wrote sample AI response:", response_path)
        return 0

    payload = load_json(payload_path)
    response = load_json(response_path)
    validate_ai_response(response)

    actual_result, actual_r, actual_exit_reason, actual_source = infer_actual_outcome_from_payload(
        payload,
        actual_result_arg=args.actual_result,
        actual_r_arg=args.actual_r,
        actual_exit_reason_arg=args.actual_exit_reason,
    )
    notes = args.notes
    if actual_source == "payload_current_row_label_audit":
        notes = (notes + " | " if notes else "") + "actual_outcome_from_payload_audit"

    row = build_ledger_row(
        payload=payload,
        response=response,
        payload_path=payload_path,
        response_path=response_path,
        actual_result=actual_result,
        actual_r=actual_r,
        actual_exit_reason=actual_exit_reason,
        notes=notes,
    )
    append_ledger(ledger_path, row)

    print("Saved AI review ledger row:", ledger_path)
    print("signal_id:", row["signal_id"])
    print("model/side/time:", row["signal_model"], row["side"], row["jst_entry_time"])
    print("AI labels:", row["winning_pattern_match"], row["losing_pattern_similarity"], row["final_risk_label"])
    print("actual outcome:", row["actual_result"], row["actual_r"], row["actual_exit_reason"], f"source={actual_source}")
    if not args.actual_result and actual_source == "empty_unknown_outcome":
        print("actual_result is empty. This is OK for live/shadow-forward mode before outcome is known.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
