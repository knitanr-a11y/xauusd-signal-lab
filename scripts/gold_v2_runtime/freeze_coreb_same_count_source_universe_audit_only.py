#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
OUT_CONFIG = ROOT / "configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json"
MIN_UNIVERSE_RULES = 15
RAW_REL = Path("FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv")
REQ = ["policy","candidate_id","origin_id","direction","variant","tp_pips","sl_pips","rr","rr_bucket","base_condition","added_filter_text"]
PAT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|==|>|<)\s*(-?\d+(?:\.\d+)?)\s*$")

def files_dir() -> Path:
    return ROOT.parents[1] if len(ROOT.parents) >= 2 else ROOT.parent

def out_dir() -> Path:
    p = files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_same_count_source_universe_freeze_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_csv_any(p: Path) -> pd.DataFrame:
    last = None
    for kwargs in [dict(sep=None, engine="python"), dict(sep=","), dict(sep=";"), dict(sep="\t")]:
        try:
            df = pd.read_csv(p, **kwargs)
            if len(df.columns) > 1:
                return df
        except Exception as e:
            last = e
    raise RuntimeError(f"CSV_READ_FAILED: {p}: {last}")

def split_and(text: str):
    return [x.strip() for x in str(text).split(" AND ") if x.strip()]

def parse_condition(rule_id: str, column: str, text: str):
    rows, errs = [], []
    for i, part in enumerate(split_and(text)):
        m = PAT.match(part)
        if not m:
            errs.append({"rule_id":rule_id,"source_column":column,"condition_index":i,"raw_text":part,"error":"UNPARSED_CONDITION"})
            continue
        rows.append({"rule_id":rule_id,"source_column":column,"condition_index":i,"field":m.group(1),"operator":m.group(2),"value":float(m.group(3)),"raw_text":part})
    return rows, errs

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def main() -> int:
    out = out_dir()
    raw = files_dir() / RAW_REL
    created = datetime.now(timezone.utc).isoformat()
    if not raw.exists():
        summary = {"created_utc":created,"status":"RULE_SOURCE_MISSING","raw_ledger":str(raw),"same_count_source_ready":False,"signal_eligible":False}
        write_json(out / "gold_v2_coreb_same_count_source_universe_summary.json", summary)
        return 2
    df = read_csv_any(raw)
    missing_cols = [c for c in REQ if c not in df.columns]
    if missing_cols:
        summary = {"created_utc":created,"status":"RULE_SOURCE_MISSING","missing_columns":missing_cols,"raw_ledger":str(raw),"same_count_source_ready":False,"signal_eligible":False}
        write_json(out / "gold_v2_coreb_same_count_source_universe_summary.json", summary)
        return 2
    work = df.copy()
    work["policy"] = work["policy"].astype(str)
    work["direction"] = work["direction"].astype(str).str.upper()
    work = work[(work["direction"] == "BUY") & (work["policy"].str.contains("RR1", na=False))].copy()
    work["base_condition"] = work["base_condition"].astype(str).str.strip()
    work["added_filter_text"] = work["added_filter_text"].astype(str).str.strip()
    work = work[(work["base_condition"] != "") & (work["added_filter_text"] != "")]
    keys = ["policy","candidate_id","origin_id","direction","variant","tp_pips","sl_pips","rr","rr_bucket","base_condition","added_filter_text"]
    uni = work.groupby(keys, dropna=False).size().reset_index(name="source_row_count")
    uni = uni.sort_values(["policy","origin_id","variant","base_condition","added_filter_text"]).reset_index(drop=True)
    rules, cond_rows, err_rows = [], [], []
    for idx, r in uni.iterrows():
        rule_id = f"COREB_SAME_COUNT_SRC_{idx:04d}"
        base_rows, base_errs = parse_condition(rule_id, "base_condition", r["base_condition"])
        add_rows, add_errs = parse_condition(rule_id, "added_filter_text", r["added_filter_text"])
        rec = r.to_dict()
        rec["rule_id"] = rule_id
        rec["base_condition_objects"] = base_rows
        rec["added_filter_condition_objects"] = add_rows
        rules.append(rec)
        cond_rows.extend(base_rows + add_rows)
        err_rows.extend(base_errs + add_errs)
    rule_count = len(rules)
    if err_rows:
        status = "UNPARSED_SAME_COUNT_SOURCE_CONDITION"
    elif rule_count < MIN_UNIVERSE_RULES:
        status = "UNMAPPED_SAME_COUNT_SOURCE"
    else:
        status = "FROZEN_COREB_SAME_COUNT_SOURCE_UNIVERSE_READY_AUDIT_ONLY"
    ready = status.endswith("READY_AUDIT_ONLY")
    pd.DataFrame(rules).drop(columns=["base_condition_objects","added_filter_condition_objects"], errors="ignore").to_csv(out / "gold_v2_coreb_same_count_source_universe_rules.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cond_rows).to_csv(out / "gold_v2_coreb_same_count_source_universe_conditions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(err_rows).to_csv(out / "gold_v2_coreb_same_count_source_universe_parse_errors.csv", index=False, encoding="utf-8-sig")
    result = {"created_utc":created,"status":status,"audit_only":True,"component":COMPONENT,"raw_ledger":str(raw),"same_count_min":15,"source_universe_rule_count":rule_count,"condition_object_count":len(cond_rows),"parse_error_count":len(err_rows),"entry_time_history_reuse_allowed":False,"historical_same_count_live_reuse_allowed":False,"same_count_source_ready":ready,"signal_eligible":False,"final_signal_allowed":False,"step13_allowed":False,"notification_should_send":False,"source_universe_rules":rules}
    if ready:
        write_json(OUT_CONFIG, result)
        result["output_config"] = str(OUT_CONFIG)
        result["output_config_written"] = True
    else:
        result["output_config"] = str(OUT_CONFIG)
        result["output_config_written"] = False
    write_json(out / "gold_v2_coreb_same_count_source_universe_summary.json", {k:v for k,v in result.items() if k != "source_universe_rules"})
    (out / "GOLD_V2_COREB_SAME_COUNT_SOURCE_UNIVERSE_FREEZE_AUDIT_ONLY_REPORT.md").write_text("# GOLD V2 CoreB same-count source universe freeze audit-only report\n\n" + "\n".join(f"- {k}: `{v}`" for k,v in {k:v for k,v in result.items() if k != "source_universe_rules"}.items()), encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "source_universe_rules"}, ensure_ascii=False, indent=2))
    return 0 if ready else 2

if __name__ == "__main__":
    raise SystemExit(main())
