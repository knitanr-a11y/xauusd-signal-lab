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


def gold_rule_profiles() -> dict[str, Any]:
    return {
        "GOLD_ABC_V3": {
            "description": "GOLD本命ABC v3。A=Hidden Divergence、B=EMA20反発+MACD再加速。",
            "adoption_status": "adopted_candidate",
            "trades": 216,
            "win_rate": 0.5926,
            "total_r": 104.0,
            "pf": 2.18,
            "risk_note": "GOLD ABC BUY danger regime が true のときだけ警戒強化。",
        },
        "GOLD_EXTRA_HIGH_RSI_STOCH": {
            "description": "GOLD EXTRA HIGH。RSI/STOCH反発を使う高PF補助候補。",
            "adoption_status": "adopted_candidate",
            "trades": 44,
            "win_rate": 0.7045,
            "total_r": 28.1,
            "pf": 3.16,
            "max_consecutive_losses": 2,
        },
        "GOLD_EXTRA_BB_BALANCE": {
            "description": "GOLD EXTRA STANDARD。BBバランス系の補助候補。",
            "adoption_status": "adopted_candidate",
            "trades": 17,
            "win_rate": 0.5294,
            "total_r": 5.5,
            "pf": 1.69,
            "risk_note": "補助候補なので、ABCやEXTRA HIGHより慎重寄りで扱う。",
        },
    }


def btc_rule_profiles() -> dict[str, Any]:
    return {
        "BTC_RUNNER_RR2_RISK1": {
            "description": "BTCの低頻度RUNNER。スプレッド込みでも採用候補。",
            "adoption_status": "adopted_candidate",
            "net_trades": 77,
            "net_win_rate": 0.6104,
            "net_total_r": 64.0,
            "net_pf": 3.13,
            "avg_effective_rr_after_spread": 1.68,
        },
        "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8": {
            "description": "BTC M5追加ルール。CSV最頻スプレッド+値幅フィルタ通過時のみ通知・採用候補。",
            "adoption_status": "filtered_adopted_candidate",
            "value_filters": {
                "net_tp_after_spread_pips_min": 5.0,
                "spread_to_sl_ratio_max": 0.50,
                "effective_rr_after_spread_min": 1.0,
            },
            "after_filter_trades": 109,
            "after_filter_win_rate": 0.6422,
            "after_filter_total_r": 101.0,
            "after_filter_pf": 3.59,
        },
    }


def compact_payload_for_ai(payload: dict[str, Any]) -> dict[str, Any]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    symbol_group = str(payload.get("symbol_group") or cur.get("symbol_group") or "")
    strategy_label = str(cur.get("strategy_label") or "")

    if symbol_group == "BTC":
        rule_profiles: dict[str, Any] = btc_rule_profiles()
    elif symbol_group == "GOLD":
        rule_profiles = gold_rule_profiles()
    else:
        rule_profiles = {}

    regime_guard = payload.get("regime_guard", {}) or {}
    guards: dict[str, Any] = {
        "overlap_detected": payload.get("overlap_detected"),
        "overlap_labels": payload.get("overlap_labels", []),
        "confidence_hint": payload.get("confidence_hint"),
    }
    if symbol_group == "GOLD" or strategy_label.startswith("GOLD"):
        guards["regime_guard"] = regime_guard
        guards["regime_guard_instruction"] = "GOLD ABC BUY danger regime は GOLD_ABC_V3 の BUY のときだけ重要。GOLD EXTRAやSELLでは対象外として扱う。"

    return {
        "symbol_group": symbol_group,
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
            "trade_plan": cur.get("trade_plan"),
        },
        "guards": guards,
        "rule_profiles": rule_profiles,
        "important_instruction": (
            f"これは {symbol_group} のシグナルです。payload内のrule_profilesを既知の検証結果として扱い、"
            "根拠なく『履歴がない』『検証不足』とは言わないでください。別銘柄のルールや警戒条件を理由に含めないでください。"
        ),
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
    symbol_group = str(compact.get("symbol_group") or "")
    system_prompt = (
        "あなたはトレードシグナルのリスク確認係です。売買を断定せず、"
        "与えられたpayloadだけを根拠に、運用上の注意度をJSONで返します。"
        "評価は normal/cautious/avoid の3段階。"
        "payloadに含まれない外部ニュース、別銘柄、別ルールの話を理由に入れてはいけません。"
        "rule_profiles は検証済みの戦略実績として扱い、根拠なく履歴不足と言わないでください。"
        "BTC M5追加ルールは高頻度なので、問題がなくても通常〜慎重の範囲で保守的に扱います。"
        "GOLDのdanger regimeはGOLD_ABC_V3 BUYのときだけ考慮してください。"
    )
    user_prompt = (
        f"次の {symbol_group} トレードシグナルpayloadを評価してください。"
        "別銘柄の注意点は含めないでください。"
        "rule_profilesに実績がある場合、履歴不足とは言わず、その実績を前提に慎重度を判断してください。"
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
