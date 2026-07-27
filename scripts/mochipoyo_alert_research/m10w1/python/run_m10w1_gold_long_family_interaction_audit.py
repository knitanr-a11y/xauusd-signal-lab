from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "M10W1_GOLD_LONG_FAMILY_HISTORICAL_INTERACTION_AUDIT_ONLY"
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
EXPECTED = {
    "M5_RUNNER75": ("07_m5_runner75_ledger.csv", "e9fe20d31e02359f853e94f1afd9f3a8b295ccda6cef81e8e4617dea42eaac86"),
    "H1_RUNNER50": ("09_h1_runner50_ledger.csv", "bfeaa63735faec23b6904ea52314e42b7a881f62b413a9c161225bdd17dd3b81"),
    "H4_ENTRY": ("10_h4_entry_ledger.csv", "e450764550f6a983ab618457639776405f3e63ea2527e8f6c8976cdb7f60a3d5"),
}
CORE = ("M5_RUNNER75", "H1_RUNNER50")
EXTENDED = ("M5_RUNNER75", "H1_RUNNER50", "H4_ENTRY")
COSTS = (0.5, 1.0, 1.5, 2.0)


def pt(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def ft(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
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


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count":0,"win_rate":None,"profit_factor_bps":None,"net_bps":0.0,"average_win_bps":None,"average_loss_bps":None,"payoff_ratio":None,"max_drawdown_bps":0.0,"max_losing_streak":0}
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]
    gross_loss = abs(sum(losses))
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None
    eq = peak = max_dd = 0.0
    streak = max_streak = 0
    for value in values:
        eq += value
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)
        streak = streak + 1 if value < 0 else 0
        max_streak = max(max_streak, streak)
    return {
        "count": len(values),
        "win_rate": sum(x > 0 for x in values) / len(values),
        "profit_factor_bps": None if gross_loss == 0 else sum(wins) / gross_loss,
        "net_bps": sum(values),
        "average_win_bps": avg_win,
        "average_loss_bps": avg_loss,
        "payoff_ratio": None if avg_win is None or avg_loss in (None, 0) else avg_win / abs(avg_loss),
        "max_drawdown_bps": max_dd,
        "max_losing_streak": max_streak,
    }


def normalize(family: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if row.get("direction") != "LONG":
            raise RuntimeError(f"non-LONG row found in {family}: {row.get('direction')}")
        entry = pt(row["actual_entry_time"])
        if family == "H4_ENTRY":
            end = pt(row["exit_time"])
            pnl = float(row["native_return_bps"])
        else:
            end = pt(row["active_until"])
            pnl = float(row["weighted_return_bps"])
        if end <= entry:
            raise RuntimeError(f"non-positive holding interval in {family}: {row.get('trade_id')}")
        output.append({
            "family": family,
            "trade_id": row.get("trade_id", ""),
            "actual_entry_time": ft(entry),
            "active_until": ft(end),
            "return_bps": pnl,
            "entry_dt": entry,
            "end_dt": end,
        })
    return sorted(output, key=lambda r: (r["entry_dt"], r["family"], r["trade_id"]))


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k not in {"entry_dt", "end_dt"}}


def pairwise_overlap(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    minutes = 0.0
    exact_entry = 0
    for left in a:
        for right in b:
            if left["entry_dt"] == right["entry_dt"]:
                exact_entry += 1
            start = max(left["entry_dt"], right["entry_dt"])
            end = min(left["end_dt"], right["end_dt"])
            if end > start:
                count += 1
                minutes += (end - start).total_seconds() / 60.0
    return {"pairwise_overlap_count":count,"pairwise_overlap_minutes":minutes,"exact_same_entry_timestamp_count":exact_entry}


def independent(families: tuple[str, ...], data: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [row for family in families for row in data[family]]
    rows.sort(key=lambda r: (r["entry_dt"], r["family"], r["trade_id"]))
    return rows, metrics([float(r["return_bps"]) for r in rows])


def single_capital(families: tuple[str, ...], data: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = [row for family in families for row in data[family]]
    rows.sort(key=lambda r: (r["entry_dt"], r["family"], r["trade_id"]))
    by_time: dict[datetime, set[str]] = {}
    for row in rows:
        by_time.setdefault(row["entry_dt"], set()).add(row["family"])
    ties = {time: fams for time, fams in by_time.items() if len(fams) > 1}
    if ties:
        first = min(ties)
        raise RuntimeError(f"exact same entry timestamp across families; fail-closed by contract: {ft(first)} {sorted(ties[first])}")
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    active_until: datetime | None = None
    active_family: str | None = None
    active_trade_id: str | None = None
    for row in rows:
        if active_until is not None and row["entry_dt"] < active_until:
            skipped.append({**row,"skip_reason":"CROSS_FAMILY_SINGLE_CAPITAL_ACTIVE","active_family":active_family,"active_trade_id":active_trade_id,"blocked_until":ft(active_until)})
            continue
        accepted.append(row)
        active_until = row["end_dt"]
        active_family = row["family"]
        active_trade_id = row["trade_id"]
    return accepted, skipped, metrics([float(r["return_bps"]) for r in accepted])


def cost_rows(view: str, accepted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = [float(r["return_bps"]) for r in accepted]
    for cost in COSTS:
        row = {"view": view, "extra_cost_bps_per_accepted_trade": cost, **metrics([x - cost for x in base])}
        rows.append(row)
    return rows


def yearly_rows(view: str, accepted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for row in accepted:
        groups.setdefault(row["entry_dt"].year, []).append(row)
    return [{"view":view,"year":year,**metrics([float(r["return_bps"]) for r in sorted(rows,key=lambda x:x["entry_dt"])])} for year, rows in sorted(groups.items())]


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        raise RuntimeError("LOCALAPPDATA unavailable")
    base = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    source = base / "outputs" / "M10A" / "LATEST"
    if not source.is_dir():
        raise RuntimeError(f"M10A LATEST missing: {source}")

    raw: dict[str, list[dict[str, str]]] = {}
    hashes: dict[str, str] = {}
    for family, (filename, expected_hash) in EXPECTED.items():
        path = source / filename
        if not path.is_file():
            raise RuntimeError(f"required M10A ledger missing: {path}")
        actual_hash = sha256_file(path)
        hashes[family] = actual_hash
        if actual_hash != expected_hash:
            raise RuntimeError(f"M10A source hash changed for {family}: expected={expected_hash} actual={actual_hash}")
        raw[family] = read_csv(path)

    data = {family: normalize(family, rows) for family, rows in raw.items()}
    family_metrics = [{"family":family,**metrics([float(r["return_bps"]) for r in rows])} for family, rows in data.items()]

    overlap_rows: list[dict[str, Any]] = []
    pairs = (("M5_RUNNER75","H1_RUNNER50"),("M5_RUNNER75","H4_ENTRY"),("H1_RUNNER50","H4_ENTRY"))
    for left, right in pairs:
        overlap_rows.append({"family_a":left,"family_b":right,**pairwise_overlap(data[left],data[right])})

    core_ind_rows, core_ind_metrics = independent(CORE, data)
    core_acc, core_skip, core_single_metrics = single_capital(CORE, data)
    ext_ind_rows, ext_ind_metrics = independent(EXTENDED, data)
    ext_acc, ext_skip, ext_single_metrics = single_capital(EXTENDED, data)

    summary = {
        "project":"MOCHIPOYO_ALERT_RESEARCH",
        "stage":STAGE,
        "status":"PASS_USER_LOCAL_GOLD_LONG_FAMILY_INTERACTION_AUDIT_ONLY",
        "built_at_utc":datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope":"XAUUSD_GOLD_ONLY",
        "source_hashes":hashes,
        "views":{
            "CORE":{
                "families":list(CORE),
                "independent_arm_combined":core_ind_metrics,
                "single_capital_first_come_first_served":core_single_metrics,
                "single_capital_skip_count":len(core_skip),
                "accepted_count_by_family":{family:sum(r["family"]==family for r in core_acc) for family in CORE}
            },
            "EXTENDED_REFERENCE_SENSITIVITY":{
                "families":list(EXTENDED),
                "independent_arm_combined":ext_ind_metrics,
                "single_capital_first_come_first_served":ext_single_metrics,
                "single_capital_skip_count":len(ext_skip),
                "accepted_count_by_family":{family:sum(r["family"]==family for r in ext_acc) for family in EXTENDED}
            }
        },
        "pairwise_overlap":overlap_rows,
        "guardrails":{
            "audit_only":True,"historical_backfill":False,"threshold_refit":False,"reads_SHORT_ledgers":False,"reads_M10P_or_M10P2_fresh_outcomes":False,"executes_M10V":False,"M10V_20_20_gate_unchanged":True,"modify_running_monitors":False,"btc_in_scope":False,"discord_send":False,"mt5_order":False,"live_ready":False,"final_signal":False,"automatic_live_promotion":False
        }
    }

    output_root = base / "outputs" / "M10W1"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    latest = output_root / "LATEST"
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text("M10W1 GOLD LONG-only historical family interaction audit. No SHORT data and no fresh M10P/M10P2 outcomes are read.\n", encoding="utf-8")
    (archive / "01_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_csv(archive / "02_family_metrics.csv", family_metrics)
    write_csv(archive / "03_pairwise_overlap.csv", overlap_rows)
    write_csv(archive / "04_core_single_capital_accepted.csv", [public_row(r) for r in core_acc])
    write_csv(archive / "05_core_single_capital_skips.csv", [public_row(r) for r in core_skip])
    write_csv(archive / "06_extended_single_capital_accepted.csv", [public_row(r) for r in ext_acc])
    write_csv(archive / "07_extended_single_capital_skips.csv", [public_row(r) for r in ext_skip])
    write_csv(archive / "08_cost_sensitivity.csv", cost_rows("CORE_SINGLE_CAPITAL",core_acc)+cost_rows("EXTENDED_SINGLE_CAPITAL",ext_acc))
    write_csv(archive / "09_yearly.csv", yearly_rows("CORE_SINGLE_CAPITAL",core_acc)+yearly_rows("EXTENDED_SINGLE_CAPITAL",ext_acc))
    (archive / "10_audit.log").write_text("\n".join([
        "status=PASS_USER_LOCAL_GOLD_LONG_FAMILY_INTERACTION_AUDIT_ONLY",
        "scope=XAUUSD_GOLD_ONLY",
        f"core_single_capital_count={len(core_acc)}",
        f"core_single_capital_skips={len(core_skip)}",
        f"extended_single_capital_count={len(ext_acc)}",
        f"extended_single_capital_skips={len(ext_skip)}",
        "reads_SHORT_ledgers=false",
        "reads_M10P_or_M10P2_fresh_outcomes=false",
        "executes_M10V=false",
        "modify_running_monitors=false",
        "historical_backfill=false",
        "threshold_refit=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]),encoding="utf-8")

    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for path in sorted(latest.iterdir()):
            if path.is_file() and path != package:
                zf.write(path,path.name)

    print("[M10W1 PASS] GOLD LONG family interaction audit completed")
    print(f"[CORE] accepted={len(core_acc)} skips={len(core_skip)} PF={core_single_metrics['profit_factor_bps']} net={core_single_metrics['net_bps']} DD={core_single_metrics['max_drawdown_bps']}")
    print(f"[EXTENDED] accepted={len(ext_acc)} skips={len(ext_skip)} PF={ext_single_metrics['profit_factor_bps']} net={ext_single_metrics['net_bps']} DD={ext_single_metrics['max_drawdown_bps']}")
    print(f"[PACKAGE] {package}")
    print("[SAFE] No SHORT/fresh runtime/start/threshold/monitor was modified or used for selection.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10W1 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No running monitor/runtime/start/threshold was intentionally modified.", file=sys.stderr)
        raise SystemExit(2)
