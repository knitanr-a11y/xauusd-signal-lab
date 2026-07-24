from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import shutil
import sys
import time
import zipfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
if str(MR) not in sys.path:
    sys.path.insert(0, str(MR))

import m7c_prospective_shadow as m7c

STAGE = "M10H_PRIMARY_SHORT_SOURCE_FIDELITY_AUDIT"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10h_primary_short_source_fidelity_audit_contract_20260725.json"
TICKER = "XAUUSD"
TIMEFRAME = "M15"
MATCHED_CLASSES = {"EXACT_MATCH", "EARLY_1_BAR", "LATE_1_BAR"}
MISSED_CLASSES = {"MISSED", "WRONG_TRANSITION_NEARBY"}
MIN_GROUP = 5


class AuditError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def load_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_read(paths: list[Path]) -> dict[Path, bytes]:
    for attempt in range(5):
        first = {path: path.read_bytes() for path in paths}
        time.sleep(0.15)
        second = {path: path.read_bytes() for path in paths}
        if all(first[path] == second[path] for path in paths):
            return second
        if attempt == 4:
            raise AuditError("M7C output files changed repeatedly during read")
    raise AuditError("unreachable")


def read_csv_bytes(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty percentile")
    pos = q * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    weight = pos - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


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


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def condition_pass(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    value = features.get(str(condition["feature"]))
    if value is None:
        return False
    op = str(condition["operator"])
    target = condition["value"]
    if op == "==":
        return value == target
    if isinstance(value, bool):
        return False
    number = float(value)
    threshold = float(target)
    if op == ">=":
        return number >= threshold
    if op == "<=":
        return number <= threshold
    raise AuditError(f"unsupported condition operator: {op}")


def build_feature_at_decision(
    series: Any,
    index_by_server_open: dict[datetime, int],
    *,
    decision_time_utc: datetime,
    offset_hours: float,
    built_at_utc: str,
) -> dict[str, Any]:
    current_server_open = decision_time_utc + timedelta(hours=offset_hours)
    current_index = index_by_server_open.get(current_server_open)
    if current_index is None or current_index <= 0:
        raise AuditError(f"M15 decision bar unavailable for {decision_time_utc.isoformat()}")
    selected_index = current_index - 1
    if selected_index + 1 < m7c.MINIMUM_WARMUP_BARS:
        raise AuditError(f"insufficient M15 warmup at {decision_time_utc.isoformat()}")
    return m7c._decision_features(
        series,
        selected_index,
        current_index,
        TICKER,
        offset_hours,
        decision_time_utc,
        built_at_utc,
    )


def numeric_feature_names(rows: list[dict[str, Any]]) -> list[str]:
    excluded = {
        "group", "classification", "raw_alert_id", "ticker", "source_decision_time_utc",
        "proxy_decision_time_utc", "source_transition", "proxy_transition", "proxy_kernel_id",
    }
    names: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key in excluded or key in names:
                continue
            if finite(value) is not None:
                names.append(key)
    return sorted(names)


def summarize_feature(group: str, feature: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    values = [number for row in rows if (number := finite(row.get(feature))) is not None]
    if not values:
        return None
    return {
        "group": group,
        "feature": feature,
        "count": len(values),
        "mean": sum(values) / len(values),
        "median": percentile(values, 0.5),
        "p25": percentile(values, 0.25),
        "p75": percentile(values, 0.75),
        "min": min(values),
        "max": max(values),
    }


def build_fidelity_gates(matched: list[dict[str, Any]], extras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(matched) < MIN_GROUP or len(extras) < MIN_GROUP:
        return []
    rows = matched + extras
    candidates: list[dict[str, Any]] = []
    for feature in numeric_feature_names(rows):
        source_values = [number for row in matched if (number := finite(row.get(feature))) is not None]
        extra_values = [number for row in extras if (number := finite(row.get(feature))) is not None]
        if len(source_values) < MIN_GROUP or len(extra_values) < MIN_GROUP:
            continue
        thresholds = sorted({percentile(source_values, q) for q in (0.10, 0.20, 0.30, 0.70, 0.80, 0.90)})
        for threshold in thresholds:
            for op in (">=", "<="):
                def accepted(value: float) -> bool:
                    return value >= threshold if op == ">=" else value <= threshold
                source_retention = sum(accepted(value) for value in source_values) / len(source_values)
                extra_acceptance = sum(accepted(value) for value in extra_values) / len(extra_values)
                extra_rejection = 1.0 - extra_acceptance
                if source_retention < 0.80:
                    continue
                candidates.append({
                    "feature": feature,
                    "accept_operator": op,
                    "threshold": threshold,
                    "matched_source_count": len(source_values),
                    "extra_proxy_count": len(extra_values),
                    "matched_source_retention": source_retention,
                    "extra_proxy_rejection": extra_rejection,
                    "balanced_score": source_retention * extra_rejection,
                    "exploratory_only": True,
                })
    candidates.sort(
        key=lambda row: (
            float(row["extra_proxy_rejection"]),
            float(row["matched_source_retention"]),
            float(row["balanced_score"]),
        ),
        reverse=True,
    )
    return candidates[:100]


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_PROSPECTIVE_EVIDENCE_AUDIT_ONLY":
            raise AuditError("unexpected M10H contract")

        local = local_root()
        m7c_dir = local / "logs" / "m7c"
        paths = {
            "report": m7c_dir / "latest_m7c_prospective_shadow.json",
            "comparisons": m7c_dir / "latest_m7c_source_event_comparisons.csv",
            "extras": m7c_dir / "latest_m7c_extra_proxy_signals.csv",
            "decisions": m7c_dir / "latest_m7c_proxy_decisions.csv",
            "manifest": local / "m7c_runtime" / "m7c_prospective_shadow_manifest_runtime.json",
            "env": local / ".env",
        }
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            raise AuditError("missing required local M7C input(s): " + "; ".join(missing))

        stable = stable_read([paths["report"], paths["comparisons"], paths["extras"], paths["decisions"]])
        report = json.loads(stable[paths["report"]].decode("utf-8"))
        comparisons = read_csv_bytes(stable[paths["comparisons"]])
        extras = read_csv_bytes(stable[paths["extras"]])
        decisions = read_csv_bytes(stable[paths["decisions"]])
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        if report.get("stage") != m7c.STAGE or report.get("prospective_start_utc") != manifest.get("prospective_start_utc"):
            raise AuditError("M7C report/runtime anchor mismatch")
        if report.get("audit_only") is not True or report.get("trade_outcome_fields_used") is not False:
            raise AuditError("unsafe or unexpected M7C report flags")

        env = load_env(paths["env"])
        mt5_root = Path(env.get("MT5_FILES_ROOT", ""))
        if not mt5_root.is_dir():
            raise AuditError(f"MT5_FILES_ROOT unavailable: {mt5_root}")
        m15_path = mt5_root / m7c.FILE_MAP[TICKER][TIMEFRAME]
        if not m15_path.is_file():
            raise AuditError(f"XAUUSD M15 file unavailable: {m15_path}")
        series = m7c.load_indicator_series(m15_path)
        index_by_server_open = {bar.server_open: index for index, bar in enumerate(series.bars)}
        offset_hours = float(report["offset_hours"][TICKER])
        built_at = str(report["built_at_utc"])
        short_rule = manifest["selected_kernels"]["PRIMARY_SHORT"]
        short_conditions = list(short_rule["conditions"])

        decision_map = {
            (row.get("ticker", ""), row.get("decision_time_utc", "")): row
            for row in decisions
        }

        source_rows: list[dict[str, Any]] = []
        miss_rows: list[dict[str, Any]] = []
        matched_features: list[dict[str, Any]] = []
        missed_features: list[dict[str, Any]] = []

        for row in comparisons:
            if row.get("ticker") != TICKER or row.get("source_transition") != "PRIMARY_SHORT":
                continue
            classification = str(row.get("classification", ""))
            if classification not in MATCHED_CLASSES | MISSED_CLASSES:
                continue
            decision_text = str(row["source_decision_time_utc"])
            decision_time = m7c.parse_utc(decision_text)
            features = build_feature_at_decision(
                series,
                index_by_server_open,
                decision_time_utc=decision_time,
                offset_hours=offset_hours,
                built_at_utc=built_at,
            )
            group = "SOURCE_MATCHED_SHORT" if classification in MATCHED_CLASSES else "SOURCE_MISSED_SHORT"
            enriched = {
                "group": group,
                "raw_alert_id": row.get("raw_alert_id"),
                "ticker": TICKER,
                "classification": classification,
                "source_decision_time_utc": decision_text,
                "proxy_decision_time_utc": row.get("proxy_decision_time_utc", ""),
                "proxy_transition": row.get("proxy_transition", ""),
                **features,
            }
            source_rows.append(enriched)
            if group == "SOURCE_MATCHED_SHORT":
                matched_features.append(enriched)
            else:
                missed_features.append(enriched)
                decision_row = decision_map.get((TICKER, decision_text))
                failed = [
                    f"{condition['feature']} {condition['operator']} {condition['value']}"
                    for condition in short_conditions
                    if not condition_pass(features, condition)
                ]
                state_before = "" if decision_row is None else str(decision_row.get("state_before", ""))
                emitted = "" if decision_row is None else str(decision_row.get("emitted_transition", ""))
                if decision_row is None:
                    reason = "NO_PROXY_DECISION_ROW"
                elif state_before != "IDLE":
                    reason = "STATE_NOT_IDLE"
                elif failed:
                    reason = "KERNEL_CONDITION_FAILURE"
                else:
                    reason = "KERNEL_MATCHED_BUT_TRANSITION_NOT_EMITTED_REVIEW"
                miss_rows.append({
                    "raw_alert_id": row.get("raw_alert_id"),
                    "source_decision_time_utc": decision_text,
                    "classification": classification,
                    "proxy_state_before": state_before,
                    "proxy_emitted_transition": emitted,
                    "diagnostic_reason": reason,
                    "failed_kernel_conditions": " | ".join(failed),
                    "rci9": features.get("rci9"),
                    "rci9_delta1": features.get("rci9_delta1"),
                    "rci9_turn_down": features.get("rci9_turn_down"),
                    "ema_alignment": features.get("ema_alignment"),
                    "ema20_minus_ema30_bps": features.get("ema20_minus_ema30_bps"),
                    "ema30_minus_ema40_bps": features.get("ema30_minus_ema40_bps"),
                    "current_open_minus_ema20_atr": features.get("current_open_minus_ema20_atr"),
                    "current_open_minus_ema40_atr": features.get("current_open_minus_ema40_atr"),
                })

        extra_rows: list[dict[str, Any]] = []
        for row in extras:
            if (
                row.get("ticker") != TICKER
                or row.get("proxy_transition") != "PRIMARY_SHORT"
                or row.get("classification") != "FINALIZED_EXTRA_PROXY_SIGNAL"
            ):
                continue
            decision_text = str(row["proxy_decision_time_utc"])
            features = build_feature_at_decision(
                series,
                index_by_server_open,
                decision_time_utc=m7c.parse_utc(decision_text),
                offset_hours=offset_hours,
                built_at_utc=built_at,
            )
            extra_rows.append({
                "group": "FINALIZED_EXTRA_PROXY_SHORT",
                "ticker": TICKER,
                "classification": row.get("classification"),
                "proxy_decision_time_utc": decision_text,
                "proxy_kernel_id": row.get("proxy_kernel_id", ""),
                **features,
            })

        feature_rows: list[dict[str, Any]] = []
        groups = {
            "SOURCE_MATCHED_SHORT": matched_features,
            "SOURCE_MISSED_SHORT": missed_features,
            "FINALIZED_EXTRA_PROXY_SHORT": extra_rows,
        }
        all_feature_rows = matched_features + missed_features + extra_rows
        for feature in numeric_feature_names(all_feature_rows):
            for group, rows in groups.items():
                summary = summarize_feature(group, feature, rows)
                if summary is not None:
                    feature_rows.append(summary)

        gates = build_fidelity_gates(matched_features, extra_rows)
        miss_reason_counts = dict(Counter(row["diagnostic_reason"] for row in miss_rows))
        top_gate = gates[0] if gates else None
        if len(matched_features) < MIN_GROUP or len(extra_rows) < MIN_GROUP:
            decision = "INSUFFICIENT_MATCHED_OR_EXTRA_SHORT_SAMPLE_FOR_FIDELITY_GATE_CLAIM"
        elif top_gate and float(top_gate["extra_proxy_rejection"]) >= 0.25:
            decision = "EXPLORATORY_SINGLE_FEATURE_FIDELITY_SIGNAL_FOUND_NOT_APPROVED"
        else:
            decision = "NO_CLEAR_SINGLE_FEATURE_FIDELITY_GATE_SIGNAL"

        output_root = local / "outputs" / "M10H"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_PRIMARY_SHORT_SOURCE_FIDELITY_AUDIT_ONLY",
            "run_at_utc": now_utc(),
            "m7c_prospective_start_utc": report["prospective_start_utc"],
            "m7c_built_at_utc": built_at,
            "ticker": TICKER,
            "timeframe": TIMEFRAME,
            "counts": {
                "genuine_source_primary_short_scored": len(source_rows),
                "source_matched_short": len(matched_features),
                "source_missed_short": len(missed_features),
                "finalized_extra_proxy_short": len(extra_rows),
            },
            "miss_reason_counts": miss_reason_counts,
            "candidate_fidelity_gate_count": len(gates),
            "top_candidate_fidelity_gate": top_gate,
            "decision": decision,
            "interpretation_contract": {
                "candidate_gates_are_exploratory_only": True,
                "no_proprietary_formula_claim": True,
                "no_trade_outcome_used": True,
                "no_mfe_mae_used": True,
                "m7c_kernel_modified": False,
                "if_sample_or_signal_insufficient": "proceed to separate Mochipoyo-independent SHORT discovery rather than force a refit",
            },
            "m7c_comparison_summary": report.get("comparison_summary", {}),
            "m7c_readiness": report.get("readiness", {}),
            "guardrails": {
                "audit_only": True,
                "historical_scan": False,
                "historical_backfill": False,
                "m7c_modified_or_reset": False,
                "m10b_modified_or_reset": False,
                "m10e_modified_or_reset": False,
                "discord_send": False,
                "mt5_order": False,
                "live_ready": False,
                "final_signal": False,
                "automatic_live_promotion": False,
            },
        }
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10H PRIMARY_SHORT source fidelity audit. Reads frozen M7C prospective evidence only. "
            "No outcomes, no historical scan, no M7C refit, no forward-system modification.\n",
            encoding="utf-8",
        )
        write_json(archive / "01_summary.json", summary)
        write_csv(archive / "02_source_primary_short_features.csv", source_rows)
        write_csv(archive / "03_finalized_extra_proxy_short_features.csv", extra_rows)
        write_csv(archive / "04_source_missed_short_reasons.csv", miss_rows)
        write_csv(archive / "05_feature_group_summary.csv", feature_rows)
        write_csv(archive / "06_candidate_fidelity_gates.csv", gates)
        write_json(archive / "07_input_integrity.json", {
            "m7c_report_sha256": sha256_bytes(stable[paths["report"]]),
            "m7c_source_comparisons_sha256": sha256_bytes(stable[paths["comparisons"]]),
            "m7c_extra_proxy_signals_sha256": sha256_bytes(stable[paths["extras"]]),
            "m7c_proxy_decisions_sha256": sha256_bytes(stable[paths["decisions"]]),
            "m7c_manifest_path": str(paths["manifest"]),
            "mt5_m15_path": str(m15_path),
            "offset_hours": offset_hours,
            "closed_m15_feature_builder_reused": True,
        })
        (archive / "08_audit.log").write_text("\n".join([
            "status=PASS_PRIMARY_SHORT_SOURCE_FIDELITY_AUDIT_ONLY",
            f"source_matched_short={len(matched_features)}",
            f"source_missed_short={len(missed_features)}",
            f"finalized_extra_proxy_short={len(extra_rows)}",
            f"decision={decision}",
            "trade_outcome_used=false",
            "historical_scan=false",
            "m7c_modified_or_reset=false",
            "m10b_modified_or_reset=false",
            "m10e_modified_or_reset=false",
            "discord_send=false",
            "mt5_order=false",
            "live_ready=false",
            "final_signal=false",
            "",
        ]), encoding="utf-8")
        names = [path.name for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(names):
                zf.write(archive / name, name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(
            f"[M10H PASS] matched={len(matched_features)} missed={len(missed_features)} "
            f"extra_short={len(extra_rows)} decision={decision}"
        )
        print("[M10H OUTPUT]", latest)
        return 0
    except Exception as exc:
        print(f"[M10H BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] M7C/M9V/M9Y/M10B/M10E unchanged.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
