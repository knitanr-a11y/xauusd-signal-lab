#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch GOLD strict-7 AI tag builder to include positive tags and win/loss audit levels.

Run from repository root after pulling:
  python scripts\gold_strict_7_signals\apply_ai_tag_positive_balance_patch.py
  python scripts\build_gold_strict_7_ai_tag_numeric_rules.bat

Why this patcher exists:
- The builder is a large file and has already been customized several times.
- This patch keeps the edit small and idempotent.
- It does not change signal conditions, MT5, Discord, order sending, or ledgers.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "build_gold_strict_7_ai_tag_numeric_rules.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"[SKIP] {label}: already patched")
        return text
    if old not in text:
        raise SystemExit(f"[ERROR] pattern not found for {label}")
    print(f"[PATCH] {label}")
    return text.replace(old, new, 1)


def main() -> int:
    text = read(TARGET)
    original = text

    text = replace_once(
        text,
        'SCHEMA_VERSION = "gold_strict_7_ai_tag_numeric_rules_v2_strict7_source_guard"\n',
        'SCHEMA_VERSION = "gold_strict_7_ai_tag_numeric_rules_v3_positive_balance_audit"\nDEFAULT_TAG_BALANCE_AUDIT_CSV = Path("data/runtime_state/gold/strict_7/ai_tag_win_loss_balance_audit.csv")\n',
        "schema version and audit csv default",
    )

    text = replace_once(
        text,
        '''NON_INFORMATIVE_TAGS = {\n    "", "-", "none", "null", "n/a", "na", "unknown", "unclear",\n    "no_clear_positive_tag", "no_positive_tag", "no_risk_tag", "no_clear_risk_tag",\n}\n''',
        '''NON_INFORMATIVE_TAGS = {\n    "", "-", "none", "null", "n/a", "na", "unknown", "unclear",\n    "no_clear_positive_tag", "no_positive_tag", "no_risk_tag", "no_clear_risk_tag",\n}\n\nPOSITIVE_TAG_KEYS = [\n    "positive_tags",\n    "possible_positive_tags",\n    "good_tags",\n    "strength_tags",\n    "favorable_tags",\n    "winning_reason_tags",\n    "success_tags",\n    "supporting_tags",\n]\n''',
        "positive tag key list",
    )

    old_explode = '''def explode_review_tags(rows: list[dict[str, Any]]) -> pd.DataFrame:\n    out: list[dict[str, Any]] = []\n    for row in rows:\n        seen: set[tuple[str, str]] = set()\n        for json_key, tag_group in [\n            ("possible_risk_tags", "risk"),\n            ("execution_issue_tags", "execution"),\n            ("system_issue_tags", "system"),\n        ]:\n            tags = row.get(json_key, [])\n            if isinstance(tags, str):\n                tags = [x.strip() for x in tags.replace(";", ",").split(",") if x.strip()]\n            if not isinstance(tags, list):\n                tags = []\n            for tag in tags:\n                tag_name = canonical_tag(tag)\n                if not is_informative_tag(tag_name):\n                    continue\n                key = (tag_name, tag_group)\n                if key in seen:\n                    continue\n                seen.add(key)\n                out.append({\n                    "trade_id": clean_str(row.get("trade_id")),\n                    "order_key": clean_str(row.get("order_key")),\n                    "payload_key": clean_str(row.get("payload_key")),\n                    "strategy_id": clean_str(row.get("strategy_id")),\n                    "symbol": clean_str(row.get("symbol")),\n                    "tag_name": tag_name,\n                    "tag_group": tag_group,\n                })\n    return pd.DataFrame(out)\n'''
    new_explode = '''def normalize_tag_list(value: Any) -> list[str]:\n    if value is None:\n        return []\n    if isinstance(value, str):\n        text = value.strip()\n        if not text:\n            return []\n        if text.startswith("[") and text.endswith("]"):\n            try:\n                parsed = json.loads(text)\n                if isinstance(parsed, list):\n                    return [canonical_tag(x) for x in parsed if is_informative_tag(canonical_tag(x))]\n            except Exception:\n                pass\n        return [canonical_tag(x) for x in text.replace(";", ",").split(",") if is_informative_tag(canonical_tag(x))]\n    if isinstance(value, list):\n        return [canonical_tag(x) for x in value if is_informative_tag(canonical_tag(x))]\n    return []\n\n\ndef explode_review_tags(rows: list[dict[str, Any]]) -> pd.DataFrame:\n    out: list[dict[str, Any]] = []\n    for row in rows:\n        seen: set[tuple[str, str, str]] = set()\n        for json_key, tag_group, tag_role in [\n            ("possible_risk_tags", "risk", "risk"),\n            ("risk_tags", "risk", "risk"),\n            ("execution_issue_tags", "execution", "risk"),\n            ("system_issue_tags", "system", "risk"),\n        ]:\n            for tag_name in normalize_tag_list(row.get(json_key, [])):\n                key = (tag_name, tag_group, tag_role)\n                if key in seen:\n                    continue\n                seen.add(key)\n                out.append({\n                    "trade_id": clean_str(row.get("trade_id")),\n                    "order_key": clean_str(row.get("order_key")),\n                    "payload_key": clean_str(row.get("payload_key")),\n                    "strategy_id": clean_str(row.get("strategy_id")),\n                    "symbol": clean_str(row.get("symbol")),\n                    "tag_name": tag_name,\n                    "tag_group": tag_group,\n                    "tag_role": tag_role,\n                })\n        for json_key in POSITIVE_TAG_KEYS:\n            for tag_name in normalize_tag_list(row.get(json_key, [])):\n                key = (tag_name, "positive", "positive")\n                if key in seen:\n                    continue\n                seen.add(key)\n                out.append({\n                    "trade_id": clean_str(row.get("trade_id")),\n                    "order_key": clean_str(row.get("order_key")),\n                    "payload_key": clean_str(row.get("payload_key")),\n                    "strategy_id": clean_str(row.get("strategy_id")),\n                    "symbol": clean_str(row.get("symbol")),\n                    "tag_name": tag_name,\n                    "tag_group": "positive",\n                    "tag_role": "positive",\n                })\n    return pd.DataFrame(out)\n'''
    text = replace_once(text, old_explode, new_explode, "explode positive and risk tags")

    text = replace_once(
        text,
        '''            if not tag_name or tag_group not in {"risk", "execution", "system"}:\n                continue\n''',
        '''            if not tag_name or tag_group not in {"risk", "execution", "system", "positive"}:\n                continue\n''',
        "allow positive tag group in candidate builder",
    )

    text = replace_once(
        text,
        '''        rule = {\n            "rule_id": f"GOLD_STRICT7_TAG_RULE_{i:04d}",\n''',
        '''        tag_role = clean_str(row.get("tag_role"), "positive" if clean_str(row.get("tag_group")) == "positive" else "risk")\n        rule = {\n            "rule_id": f"GOLD_STRICT7_TAG_RULE_{i:04d}",\n''',
        "define tag_role in build_rules",
    )

    text = replace_once(
        text,
        '''            "tag_group": clean_str(row.get("tag_group")),\n            "severity": "WATCH",\n            "action": "WARN",\n''',
        '''            "tag_group": clean_str(row.get("tag_group")),\n            "tag_role": tag_role,\n            "severity": "WATCH",\n            "action": "INFO" if tag_role == "positive" else "WARN",\n''',
        "write tag_role and action",
    )

    text = replace_once(
        text,
        '''            "kept_trades": safe_float(row.get("kept_trades")),\n            "source": "gold_strict_7_ai_review_feature_snapshot_tags",\n''',
        '''            "kept_trades": safe_float(row.get("kept_trades")),\n            "verdict": clean_str(row.get("verdict")),\n            "display_level_suggestion": clean_str(row.get("display_level_suggestion")),\n            "tag_hit_count": safe_float(row.get("tag_hit_count")),\n            "tag_win_count": safe_float(row.get("tag_win_count")),\n            "tag_loss_count": safe_float(row.get("tag_loss_count")),\n            "tag_win_rate": safe_float(row.get("tag_win_rate")),\n            "tag_avg_r": safe_float(row.get("tag_avg_r")),\n            "tag_pf": safe_float(row.get("tag_pf")),\n            "wins_with_tag_rate": safe_float(row.get("wins_with_tag_rate")),\n            "losses_with_tag_rate": safe_float(row.get("losses_with_tag_rate")),\n            "source": "gold_strict_7_ai_review_feature_snapshot_tags",\n''',
        "write audit fields into rules",
    )

    text = replace_once(
        text,
        '''    p.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)\n''',
        '''    p.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)\n    p.add_argument("--tag-balance-audit-csv", type=Path, default=DEFAULT_TAG_BALANCE_AUDIT_CSV)\n    p.add_argument("--auto-run-tag-balance-audit", action="store_true", help="Run audit_gold_strict_7_ai_tag_win_loss_balance.py first when audit CSV is missing.")\n''',
        "args for tag balance audit",
    )

    helper = '''\n\ndef load_tag_balance_audit(path: Path) -> pd.DataFrame:\n    if not path.exists():\n        return pd.DataFrame()\n    df = read_csv(path)\n    for col in ["strategy_id", "tag_group", "tag_name", "tag_role"]:\n        if col not in df.columns:\n            df[col] = ""\n        df[col] = df[col].fillna("").astype(str)\n    return df\n\n\ndef enrich_candidates_with_tag_balance(candidates: pd.DataFrame, audit_df: pd.DataFrame) -> pd.DataFrame:\n    if candidates.empty or audit_df.empty:\n        return candidates\n    work = candidates.copy()\n    if "tag_role" not in work.columns:\n        work["tag_role"] = work["tag_group"].apply(lambda x: "positive" if clean_str(x) == "positive" else "risk")\n    join_cols = ["strategy_id", "tag_group", "tag_name", "tag_role"]\n    keep_cols = join_cols + [\n        "tag_hit_count", "tag_win_count", "tag_loss_count", "tag_win_rate", "tag_avg_r", "tag_pf",\n        "wins_with_tag_rate", "losses_with_tag_rate", "verdict", "display_level_suggestion",\n    ]\n    available = [c for c in keep_cols if c in audit_df.columns]\n    return work.merge(audit_df[available].drop_duplicates(join_cols), on=join_cols, how="left")\n'''
    text = replace_once(text, "\ndef parse_args() -> argparse.Namespace:\n", helper + "\ndef parse_args() -> argparse.Namespace:\n", "audit enrich helper functions")

    text = replace_once(
        text,
        '''    output_json = resolve(args.output_json)\n    output_csv = resolve(args.output_csv)\n''',
        '''    output_json = resolve(args.output_json)\n    output_csv = resolve(args.output_csv)\n    tag_balance_audit_csv = resolve(args.tag_balance_audit_csv)\n''',
        "resolve audit csv",
    )

    text = replace_once(
        text,
        '''    review_rows = read_jsonl(review_jsonl)\n    tag_df = explode_review_tags(review_rows)\n''',
        '''    review_rows = read_jsonl(review_jsonl)\n    tag_df = explode_review_tags(review_rows)\n    if args.auto_run_tag_balance_audit and not tag_balance_audit_csv.exists():\n        import subprocess\n        audit_script = Path(__file__).resolve().parent / "audit_gold_strict_7_ai_tag_win_loss_balance.py"\n        subprocess.run([os.sys.executable, str(audit_script)], cwd=str(REPO_ROOT), check=False)\n    tag_balance_audit_df = load_tag_balance_audit(tag_balance_audit_csv)\n''',
        "load audit csv",
    )

    text = replace_once(
        text,
        '''    candidates = build_candidate_rows(feature_df, tag_df, args)\n    rules, summary_df = build_rules(candidates, args)\n''',
        '''    candidates = build_candidate_rows(feature_df, tag_df, args)\n    candidates = enrich_candidates_with_tag_balance(candidates, tag_balance_audit_df)\n    rules, summary_df = build_rules(candidates, args)\n''',
        "enrich candidates with audit",
    )

    text = replace_once(
        text,
        '''            "rules_count": int(len(rules)),\n        },\n''',
        '''            "rules_count": int(len(rules)),\n            "tag_balance_audit_rows": int(len(tag_balance_audit_df)),\n        },\n''',
        "json audit row count",
    )

    if text != original:
        write(TARGET, text)
        print(f"[OK] patched {TARGET}")
    else:
        print(f"[OK] already patched {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
