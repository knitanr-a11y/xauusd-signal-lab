from __future__ import annotations

import csv
import json
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
EXPECTED_CHECKPOINT_ROWS = 3039
EXPECTED_TURN_ROWS = 852
EXPECTED_EVENT_ROWS = 145560
CUTS = (2, 3, 5, 10)
TF_MINUTES = {"M1": 1.0, "M5": 5.0, "M15": 15.0, "H1": 60.0, "H4": 240.0}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def pf(values: list[float]) -> float | None:
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
    return None if losses == 0 else wins / losses


def metrics(rows: list[dict[str, Any]], return_key: str, recovery_key: str | None = None) -> dict[str, Any]:
    vals = [as_float(row.get(return_key)) for row in rows]
    vals = [v for v in vals if v is not None]
    out: dict[str, Any] = {
        "count": len(vals),
        "win_rate": (sum(v > 0 for v in vals) / len(vals)) if vals else None,
        "profit_factor_bps": pf(vals) if vals else None,
        "net_bps": sum(vals),
        "mean_bps": statistics.fmean(vals) if vals else None,
        "median_bps": statistics.median(vals) if vals else None,
    }
    if recovery_key:
        rec = [row.get(recovery_key) for row in rows if row.get(recovery_key) not in (None, "")]
        out["recovery_fraction"] = (sum(as_bool(v) for v in rec) / len(rec)) if rec else None
    return out


def ratio_key(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def event_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["panel_kind"]),
        str(row["proxy_trade_id"]),
        str(row["decision_time"]),
        ratio_key(row.get("checkpoint_atr_ratio")) if str(row["panel_kind"]) == "CHECKPOINT" else "",
    )


def recency_bucket(age_bars: float) -> str:
    if age_bars <= 2:
        return "LE_2"
    if age_bars <= 5:
        return "GT_2_LE_5"
    if age_bars <= 10:
        return "GT_5_LE_10"
    return "GT_10"


def locality(first_pivot: datetime, second_pivot: datetime, entry: datetime) -> str:
    if first_pivot >= entry:
        return "BOTH_PIVOTS_AFTER_SIGNAL"
    if second_pivot >= entry:
        return "SECOND_PIVOT_AFTER_SIGNAL"
    return "PRE_SIGNAL_PAIR"


def signature(events: list[dict[str, Any]]) -> str:
    supportive = any(str(row.get("directional_role")) == "SUPPORTIVE" for row in events)
    opposing = any(str(row.get("directional_role")) == "OPPOSING" for row in events)
    if supportive and opposing:
        return "BOTH"
    if supportive:
        return "SUPPORTIVE_ONLY"
    if opposing:
        return "OPPOSING_ONLY"
    return "NEITHER"


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    latest = local_root / "outputs" / "M9E" / "LATEST"
    summary_path = latest / "01_summary.json"
    checkpoint_path = latest / "02_checkpoint_divergence_panel.csv"
    turn_path = latest / "03_first_turn_divergence_panel.csv"
    event_path = latest / "04_divergence_event_detail.csv"
    required = [summary_path, checkpoint_path, turn_path, event_path]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        print(f"[M9F BLOCKED] required M9E file missing: {missing}")
        return 2

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or summary.get("contract") != "MOCHIPOYO_M9E_CAUSAL_DIVERGENCE_CONTEXT_V1"
        or int(summary.get("checkpoint_rows", -1)) != EXPECTED_CHECKPOINT_ROWS
        or int(summary.get("first_turn_rows", -1)) != EXPECTED_TURN_ROWS
        or int(summary.get("divergence_event_rows", -1)) != EXPECTED_EVENT_ROWS
    ):
        print("[M9F BLOCKED] M9E LATEST does not match reviewed population")
        return 2

    checkpoints = read_csv(checkpoint_path)
    turns = read_csv(turn_path)
    events_raw = read_csv(event_path)
    if len(checkpoints) != EXPECTED_CHECKPOINT_ROWS or len(turns) != EXPECTED_TURN_ROWS or len(events_raw) != EXPECTED_EVENT_ROWS:
        print("[M9F BLOCKED] M9E row counts changed")
        return 2

    entry_map: dict[tuple[str, str, str, str], str] = {}
    for row in checkpoints + turns:
        entry_map[event_key(row)] = row["entry_server_open"]

    enriched_events: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in events_raw:
        key = event_key(row)
        entry_text = entry_map.get(key)
        if not entry_text:
            print(f"[M9F BLOCKED] event cannot be mapped back to panel row: {key}")
            return 2
        tf = row["timeframe"]
        if tf not in TF_MINUTES:
            print(f"[M9F BLOCKED] unknown timeframe: {tf}")
            return 2
        decision = parse_time(row["decision_time"])
        confirmed = parse_time(row["second_pivot_confirmed_by"])
        first_pivot = parse_time(row["first_pivot_time"])
        second_pivot = parse_time(row["second_pivot_time"])
        entry = parse_time(entry_text)
        age_minutes = (decision - confirmed).total_seconds() / 60.0
        if age_minutes < -1e-9:
            print(f"[M9F BLOCKED] future pivot confirmation detected: {row['proxy_trade_id']}")
            return 2
        age_bars = age_minutes / TF_MINUTES[tf]
        out = dict(row)
        out["entry_server_open"] = entry_text
        out["confirmation_age_minutes"] = age_minutes
        out["confirmation_age_bars"] = age_bars
        out["recency_bucket"] = recency_bucket(age_bars)
        out["locality"] = locality(first_pivot, second_pivot, entry)
        for cut in CUTS:
            out[f"confirmed_within_{cut}_bars"] = age_bars <= cut
        enriched_events.append(out)
        by_key[key].append(out)

    decision_rows: list[dict[str, Any]] = []
    for source in checkpoints + turns:
        key = event_key(source)
        events = by_key.get(key, [])
        out: dict[str, Any] = {
            "panel_kind": source["panel_kind"],
            "proxy_trade_id": source["proxy_trade_id"],
            "ticker": source["ticker"],
            "direction": source["direction"],
            "decision_time": source["decision_time"],
            "entry_server_open": source["entry_server_open"],
            "exit_server_open": source["exit_server_open"],
            "checkpoint_atr_ratio": source.get("checkpoint_atr_ratio", ""),
            "return_bps": source.get("return_bps", ""),
            "recovered_signal": source.get("recovered_signal", ""),
            "event_count_all": len(events),
        }
        for cut in CUTS:
            recent = [event for event in events if float(event["confirmation_age_bars"]) <= cut]
            out[f"within_{cut}_bars_event_count"] = len(recent)
            out[f"within_{cut}_bars_signature"] = signature(recent)
            for role in ("SUPPORTIVE", "OPPOSING"):
                for subtype_name in ("REGULAR", "HIDDEN"):
                    out[f"within_{cut}_bars_{role.lower()}_{subtype_name.lower()}_count"] = sum(
                        str(event["directional_role"]) == role and str(event["divergence_subtype"]) == subtype_name
                        for event in recent
                    )
        for loc in ("BOTH_PIVOTS_AFTER_SIGNAL", "SECOND_PIVOT_AFTER_SIGNAL", "PRE_SIGNAL_PAIR"):
            local_events = [event for event in events if event["locality"] == loc]
            out[f"{loc.lower()}_event_count"] = len(local_events)
            out[f"{loc.lower()}_signature"] = signature(local_events)
        decision_rows.append(out)

    decision_summary: list[dict[str, Any]] = []
    for panel_kind in ("CHECKPOINT", "FIRST_TURN"):
        panel = [row for row in decision_rows if row["panel_kind"] == panel_kind]
        return_key = "return_bps"
        recovery_key = "recovered_signal" if panel_kind == "CHECKPOINT" else None
        for cut in CUTS:
            field = f"within_{cut}_bars_signature"
            for sig in ("SUPPORTIVE_ONLY", "OPPOSING_ONLY", "BOTH", "NEITHER"):
                selected = [row for row in panel if row[field] == sig]
                decision_summary.append({
                    "panel_kind": panel_kind,
                    "recency_cutoff_bars": cut,
                    "signature": sig,
                    "ticker": "ALL",
                    "direction": "ALL",
                    **metrics(selected, return_key, recovery_key),
                })
                for ticker in ("XAUUSD", "BTCUSD"):
                    for direction in ("LONG", "SHORT"):
                        split = [row for row in selected if row["ticker"] == ticker and row["direction"] == direction]
                        decision_summary.append({
                            "panel_kind": panel_kind,
                            "recency_cutoff_bars": cut,
                            "signature": sig,
                            "ticker": ticker,
                            "direction": direction,
                            **metrics(split, return_key, recovery_key),
                        })

    context_summary: list[dict[str, Any]] = []
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in enriched_events:
        key = (
            row["panel_kind"], row["timeframe"], row["scale"], row["oscillator"],
            row["divergence_type"], row["directional_role"], row["recency_bucket"], row["locality"],
            row["ticker"], row["direction"],
        )
        groups[key].append(row)
    for key, rows in sorted(groups.items()):
        panel_kind, timeframe, scale, oscillator, div_type, role, bucket, loc, ticker, direction = key
        context_summary.append({
            "panel_kind": panel_kind,
            "timeframe": timeframe,
            "scale": scale,
            "oscillator": oscillator,
            "divergence_type": div_type,
            "directional_role": role,
            "recency_bucket": bucket,
            "locality": loc,
            "ticker": ticker,
            "direction": direction,
            **metrics(rows, "return_bps", "recovered_signal" if panel_kind == "CHECKPOINT" else None),
        })

    monthly: list[dict[str, Any]] = []
    for row in decision_rows:
        row["month"] = row["decision_time"][:7].replace(".", "-")
    for panel_kind in ("CHECKPOINT", "FIRST_TURN"):
        panel = [row for row in decision_rows if row["panel_kind"] == panel_kind]
        for cut in (2, 3, 5):
            field = f"within_{cut}_bars_signature"
            keys = sorted({(row["month"], row["ticker"], row["direction"], row[field]) for row in panel})
            for month, ticker, direction, sig in keys:
                selected = [row for row in panel if row["month"] == month and row["ticker"] == ticker and row["direction"] == direction and row[field] == sig]
                monthly.append({
                    "panel_kind": panel_kind,
                    "month": month,
                    "ticker": ticker,
                    "direction": direction,
                    "recency_cutoff_bars": cut,
                    "signature": sig,
                    **metrics(selected, "return_bps", "recovered_signal" if panel_kind == "CHECKPOINT" else None),
                })

    summary_out = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9F_DIVERGENCE_RECENCY_LOCALITY_AUDIT",
        "contract": "MOCHIPOYO_M9F_DIVERGENCE_RECENCY_LOCALITY_V1",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_only": True,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "checkpoint_rows": len(checkpoints),
        "first_turn_rows": len(turns),
        "divergence_event_rows": len(enriched_events),
        "recency_cutoffs_bars": list(CUTS),
        "recency_buckets": ["LE_2", "GT_2_LE_5", "GT_5_LE_10", "GT_10"],
        "locality_categories": ["BOTH_PIVOTS_AFTER_SIGNAL", "SECOND_PIVOT_AFTER_SIGNAL", "PRE_SIGNAL_PAIR"],
        "guardrails": {
            "future_pivot_confirmation_used": False,
            "same_sample_rule_promotion_allowed": False,
            "recency_cutoffs_are_observation_grid_only": True,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
        },
    }

    quality = {
        "upstream_m9e_expected_checkpoint_rows": EXPECTED_CHECKPOINT_ROWS,
        "upstream_m9e_expected_first_turn_rows": EXPECTED_TURN_ROWS,
        "upstream_m9e_expected_event_rows": EXPECTED_EVENT_ROWS,
        "future_confirmation_age_negative_count": sum(float(row["confirmation_age_minutes"]) < 0 for row in enriched_events),
        "recency_normalized_by_timeframe_bar_duration": True,
        "locality_uses_original_proxy_entry_server_open": True,
        "same_sample_threshold_promotion_allowed": False,
    }

    out_root = local_root / "outputs" / "M9F"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", summary_out)
    write_csv(archive / "02_enriched_divergence_events.csv", enriched_events)
    write_csv(archive / "03_decision_recency_panel.csv", decision_rows)
    write_csv(archive / "04_recency_signature_summary.csv", decision_summary)
    write_csv(archive / "05_context_recency_locality_summary.csv", context_summary)
    write_csv(archive / "06_monthly_recency_replication.csv", monthly)
    dump_json(archive / "07_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9F separates fresh versus stale causal divergence and current-episode versus pre-signal divergence. Recency cutoffs are observation bins only, not trading rules.\n",
        encoding="utf-8",
    )
    (archive / "08_audit.log").write_text(
        "\n".join([
            "status=PASS_EXPLORATORY_ONLY",
            "contract=MOCHIPOYO_M9F_DIVERGENCE_RECENCY_LOCALITY_V1",
            f"checkpoint_rows={len(checkpoints)}",
            f"first_turn_rows={len(turns)}",
            f"divergence_event_rows={len(enriched_events)}",
            "future_pivot_confirmation_used=false",
            "same_sample_rule_promotion_allowed=false",
            "m7c_formula_changed=false",
            "m7c_threshold_changed=false",
            "m8c_reset=false",
            "",
        ]),
        encoding="utf-8",
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_enriched_divergence_events.csv",
        "03_decision_recency_panel.csv", "04_recency_signature_summary.csv",
        "05_context_recency_locality_summary.csv", "06_monthly_recency_replication.csv",
        "07_data_quality.json", "08_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest_out = out_root / "LATEST"
    shutil.rmtree(latest_out, ignore_errors=True)
    shutil.copytree(archive, latest_out)
    print(f"[M9F PASS] checkpoint={len(checkpoints)} first_turn={len(turns)} events={len(enriched_events)}")
    print("[M9F OUTPUT]", latest_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
