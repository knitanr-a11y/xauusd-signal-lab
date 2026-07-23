from __future__ import annotations

import csv
import json
import os
import shutil
import sqlite3
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

TF = "%Y.%m.%d %H:%M:%S"
TRANSITIONS = {"PRIMARY_LONG", "PRIMARY_SHORT", "REENTRY_LONG", "REENTRY_SHORT", "LONG_EXIT", "SHORT_EXIT"}
FILES = {
    "XAUUSD_M1": "goldsharp_m1.csv",
    "XAUUSD_M15": "goldsharp_m15.csv",
    "BTCUSD_M1": "btcusdsharp_m1.csv",
    "BTCUSD_M15": "btcusdsharp_m15.csv",
}


def dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def event_transition(event: str, state: str) -> tuple[str, str, str]:
    e = event.upper().strip()
    if e == "LONG":
        if state == "IDLE": return "PRIMARY_LONG", "ACTIVE_LONG", "OK"
        if state == "ACTIVE_LONG": return "REENTRY_LONG", state, "OK"
        return "UNRESOLVED_OPPOSITE_LONG", state, "OPPOSITE_WHILE_ACTIVE"
    if e == "SHORT":
        if state == "IDLE": return "PRIMARY_SHORT", "ACTIVE_SHORT", "OK"
        if state == "ACTIVE_SHORT": return "REENTRY_SHORT", state, "OK"
        return "UNRESOLVED_OPPOSITE_SHORT", state, "OPPOSITE_WHILE_ACTIVE"
    if e == "LONG_EXIT":
        if state == "ACTIVE_LONG": return "LONG_EXIT", "IDLE", "OK"
        return "UNRESOLVED_LONG_EXIT", state, "EXIT_STATE_MISMATCH"
    if e == "SHORT_EXIT":
        if state == "ACTIVE_SHORT": return "SHORT_EXIT", "IDLE", "OK"
        return "UNRESOLVED_SHORT_EXIT", state, "EXIT_STATE_MISMATCH"
    return "UNKNOWN_EVENT", state, "UNKNOWN_EVENT"


def locate_files_root(root: Path) -> Path:
    meta = root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if meta.is_file():
        p = Path(json.loads(meta.read_text(encoding="utf-8")).get("mt5_files_root", ""))
        if p.is_dir(): return p
    appdata = Path(os.environ.get("APPDATA", ""))
    candidates = []
    for p in (appdata / "MetaQuotes" / "Terminal").glob("*/MQL5/Files") if appdata else []:
        if all((p / name).is_file() for name in FILES.values()): candidates.append(p)
    if len(candidates) != 1:
        raise RuntimeError(f"MT5 Files root ambiguous/missing: {candidates}")
    return candidates[0]


def csv_coverage(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    if not rows or "time" not in rows[0]:
        raise RuntimeError(f"empty/unexpected CSV: {path}")
    return {"file": path.name, "rows": len(rows), "first_time": rows[0]["time"], "last_time": rows[-1]["time"]}


def main() -> int:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    db = root / "mochipoyo_alerts.sqlite3"
    if not db.is_file():
        print(f"[M9A BLOCKED] SQLite missing: {db}")
        return 2
    try:
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        annotations = {int(r[0]) for r in con.execute("SELECT raw_alert_id FROM raw_alert_annotations WHERE annotation_type='CONNECTION_TEST'").fetchall()}
        raw = con.execute("SELECT cloudflare_id,ticker,event,bar_time_utc,fired_at_utc FROM raw_alerts ORDER BY fired_at_utc,cloudflare_id").fetchall()
        assigned = {int(r[0]): str(r[1]) for r in con.execute("SELECT raw_alert_id,event_role FROM episode_events").fetchall()}
        align = {int(r[0]): str(r[1]) for r in con.execute("SELECT raw_alert_id,mt5_server_time FROM mt5_alignment WHERE timeframe='M15' AND alignment_status='ALIGNED_CLOSED_BAR'").fetchall()}
    except Exception as exc:
        print(f"[M9A BLOCKED] SQLite schema/read failed: {exc}")
        return 2
    finally:
        try: con.close()
        except Exception: pass

    eligible = [r for r in raw if int(r["cloudflare_id"]) not in annotations]
    states = defaultdict(lambda: "IDLE")
    inventory: list[dict[str, Any]] = []
    parity_mismatch = 0
    unresolved = 0
    for r in eligible:
        ticker = str(r["ticker"])
        before = states[ticker]
        tr, after, diag = event_transition(str(r["event"]), before)
        states[ticker] = after
        rid = int(r["cloudflare_id"])
        expected_role = "PRIMARY_ALERT" if tr.startswith("PRIMARY_") else "REENTRY_ALERT" if tr.startswith("REENTRY_") else "EXIT_ALERT" if tr in {"LONG_EXIT","SHORT_EXIT"} else ""
        stored_role = assigned.get(rid, "")
        parity = "NOT_STORED" if not stored_role else "MATCH" if stored_role == expected_role else "MISMATCH"
        if parity == "MISMATCH": parity_mismatch += 1
        if tr not in TRANSITIONS: unresolved += 1
        inventory.append({
            "raw_alert_id": rid, "ticker": ticker, "raw_event": str(r["event"]),
            "fired_at_utc": str(r["fired_at_utc"]), "bar_time_utc": str(r["bar_time_utc"]),
            "state_before": before, "derived_transition": tr, "state_after": after,
            "diagnostic": diag, "stored_episode_role": stored_role, "stored_role_parity": parity,
            "m15_server_open_if_aligned": align.get(rid, ""),
        })
    if parity_mismatch:
        print(f"[M9A BLOCKED] existing episode-role parity mismatches={parity_mismatch}")
        return 2

    counts = Counter(r["derived_transition"] for r in inventory)
    genuine_primary = [r for r in inventory if r["derived_transition"] in {"PRIMARY_LONG", "PRIMARY_SHORT"}]
    primary_by_ticker = Counter(r["ticker"] for r in genuine_primary)

    m7c_path = root / "logs" / "m7c" / "latest_m7c_source_event_comparisons.csv"
    m7c_info: dict[str, Any] = {"exists": m7c_path.is_file()}
    if m7c_path.is_file():
        m7c_rows = read_csv(m7c_path)
        ids = {r.get("raw_alert_id", "") for r in m7c_rows if r.get("raw_alert_id", "")}
        m7c_info.update({
            "row_count": len(m7c_rows), "unique_raw_alert_ids": len(ids),
            "columns": list(m7c_rows[0].keys()) if m7c_rows else [],
            "classification_counts": dict(Counter(r.get("classification", "") for r in m7c_rows)),
        })

    try:
        files_root = locate_files_root(root)
        coverage = []
        for label, filename in FILES.items():
            x = csv_coverage(files_root / filename); x["series"] = label; coverage.append(x)
    except Exception as exc:
        print(f"[M9A BLOCKED] MT5 coverage read failed: {exc}")
        return 2

    replay_capacity = []
    for ticker, m15_name in (("XAUUSD", FILES["XAUUSD_M15"]), ("BTCUSD", FILES["BTCUSD_M15"])):
        first = next((r for r in genuine_primary if r["ticker"] == ticker and r["m15_server_open_if_aligned"]), None)
        rows = read_csv(files_root / m15_name)
        if first:
            boundary = datetime.strptime(first["m15_server_open_if_aligned"], TF)
            pre = sum(datetime.strptime(r["time"], TF) < boundary for r in rows)
            replay_capacity.append({"ticker": ticker, "first_genuine_primary_server_open": first["m15_server_open_if_aligned"], "m15_rows_before_first_genuine_primary": pre, "m15_total_rows": len(rows)})
        else:
            replay_capacity.append({"ticker": ticker, "first_genuine_primary_server_open": "", "m15_rows_before_first_genuine_primary": None, "m15_total_rows": len(rows)})

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9A_SAMPLE_EXPANSION_AVAILABILITY_AUDIT",
        "status": "PASS",
        "audit_only": True,
        "eligible_genuine_raw_alerts": len(inventory),
        "derived_transition_counts": dict(counts),
        "genuine_primary_count": len(genuine_primary),
        "genuine_primary_by_ticker": dict(primary_by_ticker),
        "unresolved_state_machine_events": unresolved,
        "stored_episode_role_parity_mismatches": parity_mismatch,
        "m7c_source_comparison": m7c_info,
        "mt5_files_root": str(files_root),
        "replay_capacity": replay_capacity,
        "next_recommended_population_tiers": ["TIER_A_GENUINE_SOURCE_PRIMARY", "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH"],
        "m8c_reset": False,
        "m7c_changed": False,
    }

    out_root = root / "outputs" / "M9A"
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump(archive / "01_summary.json", summary)
    write_csv(archive / "02_genuine_event_inventory.csv", inventory)
    write_csv(archive / "03_mt5_coverage.csv", coverage)
    dump(archive / "04_m7c_source_comparison_diagnostics.json", m7c_info)
    write_csv(archive / "05_proxy_replay_capacity.csv", replay_capacity)
    (archive / "00_READ_ME_FIRST.txt").write_text("M9A sample-expansion availability audit. Genuine source and proxy replay must remain separate tiers.\n", encoding="utf-8")
    (archive / "06_audit.log").write_text(f"status=PASS\ngenuine_primary_count={len(genuine_primary)}\nunresolved={unresolved}\nrole_parity_mismatch={parity_mismatch}\n", encoding="utf-8")
    names = ["00_READ_ME_FIRST.txt","01_summary.json","02_genuine_event_inventory.csv","03_mt5_coverage.csv","04_m7c_source_comparison_diagnostics.json","05_proxy_replay_capacity.csv","06_audit.log"]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name in names: z.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M9A PASS] genuine_primary_count={len(genuine_primary)} unresolved={unresolved}")
    print(f"[M9A OUTPUT] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
