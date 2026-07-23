from __future__ import annotations

import csv
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MATCHED = {"EXACT_MATCH", "EARLY_1_BAR", "LATE_1_BAR"}
PRIMARY = {"PRIMARY_LONG", "PRIMARY_SHORT"}


def dt(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package(folder: Path) -> None:
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_status.json",
        "03_proxy_primary_candidates.csv", "04_gate_decisions.csv",
        "05_source_attribution.csv", "06_audit.log",
    ]
    with zipfile.ZipFile(folder / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            z.write(folder / name, name)


def main() -> int:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    runtime = root / "runtime" / "m8c"
    manifest_path = runtime / "m8c_forward_shadow_manifest.json"
    if not manifest_path.is_file():
        print("[M8C BLOCKED] runtime manifest missing; run BAT 01 first")
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    start = dt(manifest["prospective_start_utc"])

    m7c = root / "logs" / "m7c"
    p_signals = m7c / "latest_m7c_proxy_signals.csv"
    p_source = m7c / "latest_m7c_source_event_comparisons.csv"
    p_extra = m7c / "latest_m7c_extra_proxy_signals.csv"
    missing = [str(p) for p in (p_signals, p_source, p_extra) if not p.is_file()]
    if missing:
        print(f"[M8C BLOCKED] missing inputs={missing}")
        return 2

    signals = read_csv(p_signals)
    source = read_csv(p_source)
    extras = read_csv(p_extra)

    src_map: dict[tuple[str, str, str], dict] = {}
    for r in source:
        pdt = (r.get("proxy_decision_time_utc") or "").strip()
        ptr = (r.get("proxy_transition") or "").strip()
        if pdt and ptr and r.get("classification") in MATCHED:
            src_map[(r["ticker"], pdt, ptr)] = r
    extra_map = {
        (r["ticker"], r["proxy_decision_time_utc"], r["proxy_transition"]): r
        for r in extras
    }

    candidates = []
    for r in signals:
        tr = r.get("proxy_transition", "")
        if tr not in PRIMARY:
            continue
        t = dt(r["proxy_decision_time_utc"])
        if t <= start:
            continue
        key = (r["ticker"], r["proxy_decision_time_utc"], tr)
        s = src_map.get(key)
        e = extra_map.get(key)
        if s:
            attribution = "SOURCE_MATCHED"
            attr_detail = s.get("classification", "")
            raw_alert_id = s.get("raw_alert_id", "")
        elif e and e.get("classification") == "FINALIZED_EXTRA_PROXY_SIGNAL":
            attribution = "EXTRA_FINALIZED"
            attr_detail = "FINALIZED_EXTRA_PROXY_SIGNAL"
            raw_alert_id = ""
        elif e and e.get("classification") == "PENDING_SOURCE_ARRIVAL_GRACE":
            attribution = "PENDING_GRACE"
            attr_detail = "PENDING_SOURCE_ARRIVAL_GRACE"
            raw_alert_id = ""
        else:
            attribution = "PENDING_ATTRIBUTION"
            attr_detail = ""
            raw_alert_id = ""

        challenger_accept = not (r["ticker"] == "BTCUSD" and tr == "PRIMARY_LONG")
        x = dict(r)
        x.update({
            "control_accept": True,
            "challenger_accept": challenger_accept,
            "challenger_reason": "REJECT_BTCUSD_PRIMARY_LONG" if not challenger_accept else "ACCEPT",
            "gate_uses_future_source_match": False,
            "later_attribution": attribution,
            "later_attribution_detail": attr_detail,
            "matched_source_raw_alert_id": raw_alert_id,
        })
        candidates.append(x)

    candidates.sort(key=lambda r: (r["proxy_decision_time_utc"], r["ticker"], r["proxy_transition"]))
    total = len(candidates)
    btc_long = sum(r["ticker"] == "BTCUSD" and r["proxy_transition"] == "PRIMARY_LONG" for r in candidates)
    accepted = sum(bool(r["challenger_accept"]) for r in candidates)
    source_matched = sum(r["later_attribution"] == "SOURCE_MATCHED" for r in candidates)
    extra_final = sum(r["later_attribution"] == "EXTRA_FINALIZED" for r in candidates)
    pending = total - source_matched - extra_final
    requirements = {
        "total_future_proxy_primary_candidates_ge_30": total >= 30,
        "future_btcusd_primary_long_proxy_candidates_ge_8": btc_long >= 8,
        "future_challenger_accepted_proxy_candidates_ge_15": accepted >= 15,
    }
    ready = all(requirements.values())
    stage_status = "READY_FOR_FORWARD_OUTCOME_REVIEW" if ready else "COLLECTING"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M8C_EXTRA_LOSS_REDUCTION_GATE_FORWARD_SHADOW",
        "status": stage_status,
        "run_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prospective_start_utc": manifest["prospective_start_utc"],
        "historical_backfill_used": False,
        "control_candidate_count": total,
        "challenger_accepted_count": accepted,
        "challenger_rejected_count": total - accepted,
        "challenger_accepted_fraction": (accepted / total if total else None),
        "btcusd_primary_long_candidate_count": btc_long,
        "later_source_matched_count": source_matched,
        "later_extra_finalized_count": extra_final,
        "pending_attribution_count": pending,
        "review_requirements": requirements,
        "source_anchor_separate": True,
        "source_anchor_suppressed_by_gate": False,
        "gate_rule": "REJECT BTCUSD PRIMARY_LONG ON PROXY BRANCH ONLY",
        "gate_inputs": ["ticker", "proxy_transition"],
        "future_source_match_used_as_gate_input": False,
        "outcomes_used_for_gate_decision": False,
        "m8b_18_reused_as_validation": False,
        "audit_only": True,
    }
    status = {
        "status": stage_status,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
        "real_entry_gate_enabled": False,
        "m7c_formula_changed": False,
        "m7c_threshold_changed": False,
        "m7c_runtime_manifest_changed": False,
        "generator_state_changed_by_gate": False,
    }

    out_root = root / "outputs" / "M8C"
    latest = out_root / "LATEST"
    previous_count = None
    if (latest / "01_summary.json").is_file():
        try:
            previous_count = json.loads((latest / "01_summary.json").read_text(encoding="utf-8")).get("control_candidate_count")
        except Exception:
            previous_count = None

    temp = out_root / "_build"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True, exist_ok=False)
    dump(temp / "01_summary.json", summary)
    dump(temp / "02_status.json", status)
    base_fields = list(signals[0].keys()) if signals else ["ticker", "proxy_decision_time_utc", "proxy_transition"]
    fields = base_fields + [
        "control_accept", "challenger_accept", "challenger_reason", "gate_uses_future_source_match",
        "later_attribution", "later_attribution_detail", "matched_source_raw_alert_id",
    ]
    write_csv(temp / "03_proxy_primary_candidates.csv", candidates, fields)
    gate_rows = [{
        "ticker": r["ticker"], "proxy_decision_time_utc": r["proxy_decision_time_utc"],
        "proxy_transition": r["proxy_transition"], "control_accept": r["control_accept"],
        "challenger_accept": r["challenger_accept"], "challenger_reason": r["challenger_reason"],
        "decision_time_inputs_only": True,
    } for r in candidates]
    write_csv(temp / "04_gate_decisions.csv", gate_rows, [
        "ticker", "proxy_decision_time_utc", "proxy_transition", "control_accept",
        "challenger_accept", "challenger_reason", "decision_time_inputs_only",
    ])
    attr_rows = [{
        "ticker": r["ticker"], "proxy_decision_time_utc": r["proxy_decision_time_utc"],
        "proxy_transition": r["proxy_transition"], "later_attribution": r["later_attribution"],
        "later_attribution_detail": r["later_attribution_detail"],
        "matched_source_raw_alert_id": r["matched_source_raw_alert_id"],
        "used_as_gate_input": False,
    } for r in candidates]
    write_csv(temp / "05_source_attribution.csv", attr_rows, [
        "ticker", "proxy_decision_time_utc", "proxy_transition", "later_attribution",
        "later_attribution_detail", "matched_source_raw_alert_id", "used_as_gate_input",
    ])
    (temp / "00_READ_ME_FIRST.txt").write_text(
        "MOCHIPOYO M8C Forward Shadow\n"
        f"Status: {stage_status}\nProspective start UTC: {manifest['prospective_start_utc']}\n\n"
        "CONTROL accepts all future proxy PRIMARY candidates.\n"
        "CHALLENGER rejects only BTCUSD PRIMARY_LONG on the proxy branch.\n"
        "Source anchor is separate and is not suppressed. Later source-match attribution is never used as a gate input.\n"
        "M8B 18 trades are not validation data. No outcomes are used in this collection stage.\n"
        "Normal review package: 99_UPLOAD_PACKAGE.zip\n",
        encoding="utf-8",
    )
    (temp / "06_audit.log").write_text(
        f"status={stage_status}\nprospective_start_utc={manifest['prospective_start_utc']}\n"
        f"control_candidate_count={total}\nchallenger_accepted_count={accepted}\n"
        f"challenger_rejected_count={total-accepted}\nbtcusd_primary_long_candidate_count={btc_long}\n"
        f"review_requirements={json.dumps(requirements, sort_keys=True)}\n",
        encoding="utf-8",
    )
    package(temp)

    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(temp, latest)
    shutil.rmtree(temp)
    if previous_count != total:
        archive = out_root / "archive" / now.strftime("%Y%m%d_%H%M%S")
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(latest, archive)

    print(f"[M8C {stage_status}] total={total} accepted={accepted} rejected={total-accepted} btc_long={btc_long}")
    print(f"[M8C OUTPUT] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
