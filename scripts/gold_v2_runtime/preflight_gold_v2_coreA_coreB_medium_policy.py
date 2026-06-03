#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GOLD V2 CoreA/CoreB/MEDIUM policy preflight.

This script validates that the frozen audit-only policy config is internally safe
and that the required input files exist under Files/FX_OUTPUTS.

It does not call AI APIs, Discord, MT5, or any live trading hooks.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd


@dataclass
class Check:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight GOLD V2 CoreA/CoreB/MEDIUM policy")
    parser.add_argument(
        "--config",
        default="configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json",
        help="Policy JSON path relative to repo root or absolute path",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def resolve_path(path_text: str, *, base: Path) -> Path:
    p = Path(path_text)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def resolve_files_path(path_text: str) -> Path:
    text = path_text.replace("\\", "/")
    if text.startswith("Files/"):
        return (files_dir_from_repo() / text[len("Files/"):]).resolve()
    return resolve_path(path_text, base=repo_root())


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreA_coreB_medium_policy_preflight"


def add_check(checks: List[Check], name: str, ok: bool, message: str, detail: str = "") -> None:
    checks.append(Check(name, "OK" if ok else "ERROR", message, detail))


def safe_load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_row_count(path: Path) -> int:
    try:
        return int(len(pd.read_csv(path, nrows=10000000)))
    except Exception:
        return -1


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, base=root)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    checks: List[Check] = []

    add_check(checks, "config_exists", config_path.exists(), f"config_path={config_path}")
    if not config_path.exists():
        pd.DataFrame([asdict(c) for c in checks]).to_csv(output_dir / "gold_v2_policy_preflight_checks.csv", index=False, encoding="utf-8-sig")
        return 2

    try:
        cfg = safe_load_json(config_path)
        add_check(checks, "config_json_parse", True, "JSON parsed")
    except Exception as exc:
        add_check(checks, "config_json_parse", False, "JSON parse failed", repr(exc))
        pd.DataFrame([asdict(c) for c in checks]).to_csv(output_dir / "gold_v2_policy_preflight_checks.csv", index=False, encoding="utf-8-sig")
        return 2

    safety = cfg.get("safety", {})
    for key in ["ai_api_enabled", "discord_enabled", "mt5_order_enabled", "live_hook_enabled"]:
        add_check(checks, f"safety_{key}_false", safety.get(key) is False, f"{key}={safety.get(key)}")
    add_check(checks, "safety_audit_only_true", safety.get("audit_only") is True, f"audit_only={safety.get('audit_only')}")

    coreb = cfg.get("coreB", {})
    add_check(checks, "coreB_rr_125", abs(float(coreb.get("rr", -1)) - 1.25) < 1e-12, f"rr={coreb.get('rr')}")
    add_check(checks, "coreB_buy_only", coreb.get("direction") == "BUY_ONLY", f"direction={coreb.get('direction')}")
    add_check(checks, "coreB_same_count_min_15", int(coreb.get("same_count_min", -1)) == 15, f"same_count_min={coreb.get('same_count_min')}")
    add_check(checks, "coreB_cap3", coreb.get("sizing") == "CAP3", f"sizing={coreb.get('sizing')}")

    confluence = cfg.get("confluence", {})
    add_check(checks, "confluence_extra_0p5", abs(float(confluence.get("initial_extra_coreB_exposure", -1)) - 0.5) < 1e-12, f"initial_extra_coreB_exposure={confluence.get('initial_extra_coreB_exposure')}")

    medium = cfg.get("medium", {})
    expected_medium = ["RANGE96_REFINED", "VOL_TRMEAN32_REFINED", "TIER2_HVT"]
    add_check(checks, "medium_enabled", medium.get("enabled") is True, f"medium.enabled={medium.get('enabled')}")
    add_check(checks, "medium_priority_order", medium.get("priority_order") == expected_medium, f"priority_order={medium.get('priority_order')}")

    watch = cfg.get("watch", {}).get("ORIGIN010_REFINED", {})
    add_check(checks, "origin010_watch_not_default", watch.get("enabled_by_default") is False, f"enabled_by_default={watch.get('enabled_by_default')}")

    inputs = cfg.get("inputs", {})
    input_dirs = {
        "core_input_dir": inputs.get("core_input_dir_default"),
        "rr125_input_dir": inputs.get("rr125_input_dir_default"),
        "medium_input_dir": inputs.get("medium_input_dir_default"),
    }
    required_by_dir = {
        "core_input_dir": ["abc_stack_cap_2025_fold4_cluster_ledger.csv", "abc_stack_cap_2026_cluster_ledger.csv"],
        "rr125_input_dir": ["rr125_top_ledgers.csv"],
        "medium_input_dir": ["coreb_refined_rule_ledgers.csv"],
    }

    input_audit_rows: List[Dict[str, Any]] = []
    for dir_name, dir_text in input_dirs.items():
        if not dir_text:
            add_check(checks, f"{dir_name}_configured", False, "missing dir config")
            continue
        dir_path = resolve_files_path(dir_text)
        add_check(checks, f"{dir_name}_exists", dir_path.exists() and dir_path.is_dir(), f"{dir_path}")
        for filename in required_by_dir[dir_name]:
            file_path = dir_path / filename
            exists = file_path.exists()
            rows = csv_row_count(file_path) if exists else -1
            add_check(checks, f"file_exists_{filename}", exists, f"{file_path}", f"rows={rows}")
            input_audit_rows.append({"input_dir": dir_name, "path": str(file_path), "exists": exists, "rows": rows})

    checks_df = pd.DataFrame([asdict(c) for c in checks])
    input_audit_df = pd.DataFrame(input_audit_rows)
    checks_df.to_csv(output_dir / "gold_v2_policy_preflight_checks.csv", index=False, encoding="utf-8-sig")
    input_audit_df.to_csv(output_dir / "gold_v2_policy_preflight_input_files.csv", index=False, encoding="utf-8-sig")

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "output_dir": str(output_dir),
        "status": "OK" if (checks_df["status"] == "OK").all() else "ERROR",
        "error_count": int((checks_df["status"] != "OK").sum()),
        "checks": [asdict(c) for c in checks],
        "input_files": input_audit_rows,
    }
    (output_dir / "gold_v2_policy_preflight_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[DONE] status={summary['status']} output_dir={output_dir}")
    print(checks_df.to_string(index=False))
    return 0 if summary["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
