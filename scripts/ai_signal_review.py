from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_USER_AGENT = "xauusd-signal-lab/1.0 (+https://github.com/knitanr-a11y/xauusd-signal-lab)"

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["normal", "cautious", "avoid"]},
        "decision_jp": {"type": "string", "enum": ["通常", "慎重", "見送り候補"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "lot_multiplier_hint": {"type": "number"},
        "summary_jp": {"type": "string"},
        "reasons_jp": {"type": "array", "items": {"type": "string"}},
        "warnings_jp": {"type": "array", "items": {"type": "string"}},
        "checklist_jp": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "decision",
        "decision_jp",
        "confidence",
        "lot_multiplier_hint",
        "summary_jp",
        "reasons_jp",
        "warnings_jp",
        "checklist_jp",
    ],
    "additionalProperties": False,
}


def load_env_file(path: Path = DEFAULT_ENV_FILE) -> None:
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


def compact_payload_for_ai(payload: dict[str, Any]) -> dict[str, Any]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    regime_guard = payload.get("regime_guard", {}) or {}
    return {
        "symbol_group": payload.get("symbol_group"),
        "time": payload.get("time"),
        "source_tf": payload.get("source_tf") or cur.get("source_tf"),
        "signal": {
            "strategy_label": cur.get("strategy_label"),
            "signal_model": cur.get("signal_model"),
            "portfolio_rank": cur.get("portfolio_rank"),
            "side": cur.get("side"),
            "rr": cur.get("rr"),
            "risk_atr": cur.get("risk_atr"),
            "lot_hint": cur.get("lot_hint"),
            "entry_hour": cur.get("entry_hour"),
            "entry_time_proxy": cur.get("entry_time_proxy"),
            "abc_source": cur.get("abc_source"),
        },
        "price_context": {
            "close": cur.get("close"),
            "atr14": cur.get("atr14"),
        },
        "guards": {
            "regime_guard": regime_guard,
            "overlap_detected": payload.get("overlap_detected"),
            "overlap_labels": payload.get("overlap_labels", []),
            "confidence_hint": payload.get("confidence_hint"),
        },
        "rule_profiles": {
            "BTC_RUNNER_RR2_RISK1": "BTCの低頻度RUNNER。通常候補。",
            "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8": "BTCのM5追加ルール。検証成績は良いが高頻度なのでロット小さめ候補。",
            "GOLD_ABC_V3": "GOLD本命ABC。danger regimeがtrueなら慎重確認。",
            "GOLD_EXTRA_HIGH_RSI_STOCH": "GOLD EXTRA HIGH。補助候補。",
            "GOLD_EXTRA_BB_BALANCE": "GOLD EXTRA STANDARD。補助候補。",
        },
    }


def fallback_review(reason: str) -> dict[str, Any]:
    return {
        "provider": "fallback",
        "model": "none",
        "ok": False,
        "error": reason,
        "decision": "cautious",
        "decision_jp": "慎重",
        "confidence": "low",
        "lot_multiplier_hint": 0.5,
        "summary_jp": "AI評価に失敗したため、機械判定のみで慎重扱いにしています。",
        "reasons_jp": ["AI評価が利用できませんでした。", "通知シグナル自体は検出済みです。"],
        "warnings_jp": [reason],
        "checklist_jp": ["チャート形状を手動確認", "スプレッドと直近急変動を確認", "必要ならロットを落とす"],
    }


def extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts: list[str] = []
    for item in response.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def evaluate_signal_payload(
    payload: dict[str, Any],
    *,
    env_file: Path = DEFAULT_ENV_FILE,
    model: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    load_env_file(env_file)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback_review("OPENAI_API_KEY が .env または環境変数にありません。")

    model_name = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    compact = compact_payload_for_ai(payload)
    system_prompt = (
        "あなたはトレードシグナルのリスク確認係です。売買を断定せず、"
        "与えられたpayloadだけを根拠に、運用上の注意度をJSONで返します。"
        "評価は normal/cautious/avoid の3段階。"
        "BTC M5追加ルールは高頻度なので、問題がなくても通常〜慎重の範囲で保守的に扱います。"
        "danger regimeや不明点がある場合は慎重または見送り候補にします。"
    )
    user_prompt = (
        "次のトレードシグナルpayloadを評価してください。"
        "出力は必ず指定JSON Schemaに従ってください。\n\n"
        + json.dumps(compact, ensure_ascii=False, indent=2, default=str)
    )
    body = {
        "model": model_name,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "trade_signal_review",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": OPENAI_USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return fallback_review(f"OpenAI HTTPError status={exc.code}: {err_body[:500]}")
    except Exception as exc:
        return fallback_review(f"OpenAI評価エラー: {exc}")

    text = extract_output_text(data)
    if not text:
        return fallback_review("OpenAI応答からJSONテキストを取得できませんでした。")
    try:
        review = json.loads(text)
    except json.JSONDecodeError as exc:
        return fallback_review(f"OpenAI応答JSONの解析に失敗しました: {exc}")

    review["provider"] = "openai"
    review["model"] = model_name
    review["ok"] = True
    review["error"] = ""
    return review


def apply_ai_review(payload: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["ai_review"] = review
    out["ai_review_required"] = True
    out["ai_review_status"] = review.get("decision_jp", "評価済み") if review.get("ok") else "評価エラー"
    return out
