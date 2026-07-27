from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "M10W4_GOLD_LONG_PORTFOLIO_DIFFERENCE_FORENSICS_AUDIT_ONLY"
EXPECTED = {
    "CORE_BASELINE": ("06_core_baseline_accepted.csv", "bebdcfa104ada3400b8c1abf241b8a553a1cebb9731709a0fb3bac4cb211a51d"),
    "CORE_FILTERED": ("08_core_filtered_accepted.csv", "68ebfdffb6a1383e8eaa6bd1e1cd0ee06abef22f824a20fec8e1c9396631d0be"),
    "EXTENDED_BASELINE": ("10_extended_baseline_accepted.csv", "15ab87f8f8a3cedbbe16cda74c7cd18c7e40b3219b238efe6a7f818142dfc111"),
    "EXTENDED_FILTERED": ("12_extended_filtered_accepted.csv", "58be8b455101d7d2d92c569170b79ed910cc159390e50c35b915da62275d1d41"),
}
PAIRS = (("CORE_BASELINE", "CORE_FILTERED"), ("EXTENDED_BASELINE", "EXTENDED_FILTERED"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
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


def canonical_key(row: dict[str, str]) -> str:
    family = row["family"]
    trade_id = row["trade_id"]
    entry = row["actual_entry_time"]
    if family.startswith("H1_"):
        marker = "_H1_"
        if marker not in trade_id:
            raise RuntimeError(f"unexpected H1 trade_id: {trade_id}")
        suffix = trade_id.split(marker, 1)[1]
        return f"H1|{suffix}|{entry}"
    return f"{family}|{trade_id}|{entry}"


def public(row: dict[str, str]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "trade_id": row["trade_id"],
        "actual_entry_time": row["actual_entry_time"],
        "active_until": row["active_until"],
        "return_bps": float(row["return_bps"]),
        "year": int(row["actual_entry_time"][:4]),
        "canonical_key": canonical_key(row),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [float(r["return_bps"]) for r in rows]
    return {
        "count": len(rows),
        "net_bps": sum(vals),
        "wins": sum(v > 0 for v in vals),
        "losses": sum(v < 0 for v in vals),
        "avg_bps": (sum(vals) / len(vals)) if vals else None,
        "best_bps": max(vals) if vals else None,
        "worst_bps": min(vals) if vals else None,
    }


def group_aggregate(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return [{key: label, **aggregate(group)} for label, group in sorted(groups.items(), key=lambda x: str(x[0]))]


def compare(name: str, baseline: list[dict[str, str]], filtered: list[dict[str, str]]) -> dict[str, Any]:
    b = {canonical_key(r): public(r) for r in baseline}
    f = {canonical_key(r): public(r) for r in filtered}
    if len(b) != len(baseline) or len(f) != len(filtered):
        raise RuntimeError(f"duplicate canonical identity in {name}")
    common_keys = sorted(set(b) & set(f))
    baseline_only = [b[k] for k in sorted(set(b) - set(f))]
    filtered_only = [f[k] for k in sorted(set(f) - set(b))]
    parity_diffs = []
    for k in common_keys:
        diff = abs(float(b[k]["return_bps"]) - float(f[k]["return_bps"]))
        if diff > 1e-10:
            parity_diffs.append({"canonical_key": k, "baseline_return_bps": b[k]["return_bps"], "filtered_return_bps": f[k]["return_bps"], "abs_diff": diff})
    if parity_diffs:
        raise RuntimeError(f"common-trade return parity failed in {name}: first={parity_diffs[0]}")

    by_year = []
    years = sorted({r["year"] for r in baseline_only + filtered_only})
    for year in years:
        br = [r for r in baseline_only if r["year"] == year]
        fr = [r for r in filtered_only if r["year"] == year]
        by_year.append({
            "year": year,
            "baseline_only_count": len(br),
            "baseline_only_net_bps": sum(float(r["return_bps"]) for r in br),
            "filtered_only_count": len(fr),
            "filtered_only_net_bps": sum(float(r["return_bps"]) for r in fr),
            "filtered_minus_baseline_net_bps": sum(float(r["return_bps"]) for r in fr) - sum(float(r["return_bps"]) for r in br),
        })
    by_family_rows = []
    families = sorted({r["family"] for r in baseline_only + filtered_only})
    for family in families:
        br = [r for r in baseline_only if r["family"] == family]
        fr = [r for r in filtered_only if r["family"] == family]
        by_family_rows.append({
            "family": family,
            "baseline_only_count": len(br),
            "baseline_only_net_bps": sum(float(r["return_bps"]) for r in br),
            "filtered_only_count": len(fr),
            "filtered_only_net_bps": sum(float(r["return_bps"]) for r in fr),
        })
    return {
        "name": name,
        "common_count": len(common_keys),
        "baseline_only": baseline_only,
        "filtered_only": filtered_only,
        "baseline_only_metrics": aggregate(baseline_only),
        "filtered_only_metrics": aggregate(filtered_only),
        "by_year": by_year,
        "by_family": by_family_rows,
        "common_return_parity_pass": True,
    }


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        raise RuntimeError("LOCALAPPDATA unavailable")
    base = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    source = base / "outputs" / "M10W3" / "LATEST"
    if not source.is_dir():
        raise RuntimeError(f"M10W3 LATEST missing: {source}")

    raw: dict[str, list[dict[str, str]]] = {}
    hashes: dict[str, str] = {}
    for label, (filename, expected_hash) in EXPECTED.items():
        path = source / filename
        if not path.is_file():
            raise RuntimeError(f"required M10W3 source missing: {path}")
        actual_hash = sha256_file(path)
        hashes[label] = actual_hash
        if actual_hash != expected_hash:
            raise RuntimeError(f"M10W3 source hash changed for {label}: expected={expected_hash} actual={actual_hash}")
        raw[label] = read_csv(path)

    results = []
    for baseline_name, filtered_name in PAIRS:
        results.append(compare(baseline_name.replace("BASELINE", "FILTERED_MINUS_BASELINE"), raw[baseline_name], raw[filtered_name]))

    output_root = base / "outputs" / "M10W4"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    latest = output_root / "LATEST"
    archive.mkdir(parents=True, exist_ok=False)

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_USER_LOCAL_GOLD_LONG_PORTFOLIO_DIFFERENCE_FORENSICS_AUDIT_ONLY",
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "XAUUSD_GOLD_ONLY",
        "source_hashes": hashes,
        "comparisons": [{k: v for k, v in r.items() if k not in {"baseline_only", "filtered_only"}} for r in results],
        "guardrails": {
            "audit_only": True,
            "threshold_refit": False,
            "new_filter_search": False,
            "historical_backfill": False,
            "reads_SHORT_ledgers": False,
            "reads_M10E_fresh_outcomes_for_selection": False,
            "reads_M10P_or_M10P2": False,
            "modify_running_monitors": False,
            "btc_in_scope": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "automatic_live_promotion": False,
        },
    }
    (archive / "00_READ_ME_FIRST.txt").write_text("M10W4 GOLD LONG portfolio-difference forensics. Read-only; no threshold search and no fresh/SHORT outcomes.\n", encoding="utf-8")
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    diff_rows = []
    year_rows = []
    family_rows = []
    only_2025 = []
    top_rows = []
    for result in results:
        comp = result["name"]
        for side, rows in (("BASELINE_ONLY", result["baseline_only"]), ("FILTERED_ONLY", result["filtered_only"])):
            for row in rows:
                diff_rows.append({"comparison": comp, "side": side, **row})
                if row["year"] == 2025:
                    only_2025.append({"comparison": comp, "side": side, **row})
            ranked = sorted(rows, key=lambda r: abs(float(r["return_bps"])), reverse=True)[:20]
            for rank, row in enumerate(ranked, 1):
                top_rows.append({"comparison": comp, "side": side, "rank_by_abs_return": rank, **row})
        for row in result["by_year"]:
            year_rows.append({"comparison": comp, **row})
        for row in result["by_family"]:
            family_rows.append({"comparison": comp, **row})

    write_csv(archive / "02_all_changed_accepted_trades.csv", diff_rows)
    write_csv(archive / "03_yearly_decomposition.csv", year_rows)
    write_csv(archive / "04_family_decomposition.csv", family_rows)
    write_csv(archive / "05_2025_changed_accepted_trades.csv", only_2025)
    write_csv(archive / "06_top_abs_changed_trades.csv", top_rows)
    (archive / "07_audit.log").write_text("\n".join([
        "status=PASS_USER_LOCAL_GOLD_LONG_PORTFOLIO_DIFFERENCE_FORENSICS_AUDIT_ONLY",
        "scope=XAUUSD_GOLD_ONLY",
        *[f"{r['name']}: common={r['common_count']} baseline_only={r['baseline_only_metrics']['count']} filtered_only={r['filtered_only_metrics']['count']}" for r in results],
        "common_return_parity_pass=true",
        "threshold_refit=false",
        "new_filter_search=false",
        "reads_SHORT_ledgers=false",
        "reads_M10E_fresh_outcomes_for_selection=false",
        "reads_M10P_or_M10P2=false",
        "modify_running_monitors=false",
        "historical_backfill=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")

    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(latest.iterdir()):
            if path.is_file() and path != package:
                zf.write(path, path.name)

    print("[M10W4 PASS] GOLD LONG portfolio-difference forensics completed")
    for r in results:
        print(f"[{r['name']}] common={r['common_count']} baseline_only={r['baseline_only_metrics']['count']} filtered_only={r['filtered_only_metrics']['count']} baseline_only_net={r['baseline_only_metrics']['net_bps']} filtered_only_net={r['filtered_only_metrics']['net_bps']}")
    print(f"[PACKAGE] {package}")
    print("[SAFE] No threshold, SHORT/fresh outcome, runtime/start, or running monitor was modified or used for selection.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10W4 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Do not edit source ledgers, thresholds, or running monitors to force a pass.", file=sys.stderr)
        raise SystemExit(2)
