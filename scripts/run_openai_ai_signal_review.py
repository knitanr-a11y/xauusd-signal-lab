from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PAYLOAD_JSON = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_signal_review_payload_row_0.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews"
DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_ledger.csv"
DEFAULT_MODEL = "gpt-5-mini"

REQUIRED_RESPONSE_KEYS = [
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


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_dotenv_if_exists(path: Path) -> None:
    """Small .env loader to avoid requiring python-dotenv."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object")
    return data


def validate_ai_response(response: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_RESPONSE_KEYS if key not in response]
    if missing:
        raise ValueError(f"AI response missing required keys: {missing}")

    if response["winning_pattern_match"] not in ALLOWED_WIN_MATCH:
        raise ValueError(f"Invalid winning_pattern_match: {response['winning_pattern_match']}")
    if response["losing_pattern_similarity"] not in ALLOWED_LOSS_SIM:
        raise ValueError(f"Invalid losing_pattern_similarity: {response['losing_pattern_similarity']}")
    if response["final_risk_label"] not in ALLOWED_RISK_LABEL:
        raise ValueError(f"Invalid final_risk_label: {response['final_risk_label']}")
    if response["do_not_use_as_final_trade_decision"] is not True:
        raise ValueError("do_not_use_as_final_trade_decision must be true")

    for key in ["evidence_for_entry", "evidence_against_entry", "human_checkpoints"]:
        if not isinstance(response[key], list):
            raise ValueError(f"AI response key must be a list: {key}")


def build_input_text(payload: dict[str, Any]) -> str:
    return (
        "Evaluate this trading signal review payload.\n"
        "Return JSON only using the exact schema requested inside ai_task.\n\n"
        "PAYLOAD_JSON:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    )


def response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "to_dict"):
        return response.to_dict()
    return json.loads(response.model_dump_json())


def extract_output_text_from_response(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    data = response_to_dict(response)
    texts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(str(content["text"]))

    return "\n".join(texts).strip()


def write_debug_response(response: Any, debug_path: Path) -> None:
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    data = response_to_dict(response)
    debug_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def call_openai_responses_api(
    payload: dict[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    debug_response_path: Path,
) -> tuple[dict[str, Any], str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Python SDK is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in your environment or create a local .env file. "
            "Do not commit .env to GitHub."
        )

    client = OpenAI(api_key=api_key)

    instructions = (
        "You are a cautious but not overly defensive trading signal risk reviewer. "
        "The rule-based signal already has baseline backtested expectancy. "
        "You must compare current_signal_snapshot against similar_winning_cases and similar_losing_cases. "
        "Return JSON only. Do not include markdown. Do not make final trading decisions."
    )

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=build_input_text(payload),
        max_output_tokens=max_output_tokens,
    )

    write_debug_response(response, debug_response_path)

    data = response_to_dict(response)
    status = data.get("status")
    incomplete_details = data.get("incomplete_details")
    usage = data.get("usage", {})

    output_text = extract_output_text_from_response(response)
    if not output_text:
        raise RuntimeError(
            "OpenAI response did not include visible output text. "
            f"status={status}, incomplete_details={incomplete_details}, usage={usage}. "
            f"Debug response saved to: {debug_response_path}. "
            "Try increasing --max-output-tokens, e.g. --max-output-tokens 3000."
        )

    parsed = extract_json_object(output_text)
    validate_ai_response(parsed)
    return parsed, output_text


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run_save_ledger(payload_json: Path, ai_response_json: Path, ledger_csv: Path) -> None:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "save_ai_review_record.py"),
        "--payload-json",
        str(payload_json),
        "--ai-response-json",
        str(ai_response_json),
        "--ledger-csv",
        str(ledger_csv),
        "--notes",
        "openai_api_shadow_review",
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Call OpenAI API for one AI signal review payload and save the response.")
    parser.add_argument("--payload-json", type=Path, default=DEFAULT_PAYLOAD_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--max-output-tokens", type=int, default=3000)
    parser.add_argument("--save-ledger", action="store_true", help="Append the AI response to the selected ledger CSV after validation.")
    parser.add_argument("--dry-run", action="store_true", help="Validate payload and print output paths without calling OpenAI.")
    args = parser.parse_args()

    load_dotenv_if_exists(PROJECT_ROOT / ".env")

    payload_json = resolve_path(args.payload_json)
    out_dir = resolve_path(args.out_dir)
    ledger_csv = resolve_path(args.ledger_csv)
    payload = load_json(payload_json)

    source_row = payload.get("metadata", {}).get("current_case_source_row", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_response = out_dir / f"openai_ai_response_row_{source_row}_{timestamp}.json"
    out_raw = out_dir / f"openai_ai_response_row_{source_row}_{timestamp}.txt"
    out_debug = out_dir / f"openai_ai_response_row_{source_row}_{timestamp}_debug.json"

    print("Payload:", payload_json)
    print("Model:", args.model)
    print("Max output tokens:", args.max_output_tokens)
    print("Output JSON:", out_response)
    print("Output raw:", out_raw)
    print("Output debug:", out_debug)
    if args.save_ledger:
        print("Ledger CSV:", ledger_csv)

    if args.dry_run:
        print("Dry run only. No OpenAI API call was made.")
        return 0

    parsed, raw_text = call_openai_responses_api(
        payload,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
        debug_response_path=out_debug,
    )

    write_json(out_response, parsed)
    out_raw.parent.mkdir(parents=True, exist_ok=True)
    out_raw.write_text(raw_text, encoding="utf-8")

    print("Saved AI response:", out_response)
    print("Saved raw response:", out_raw)
    print("Saved debug response:", out_debug)
    print("AI labels:", parsed["winning_pattern_match"], parsed["losing_pattern_similarity"], parsed["final_risk_label"])

    if args.save_ledger:
        run_save_ledger(payload_json, out_response, ledger_csv)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
