#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path
from typing import Any
import pandas as pd

READY = "GOLD_V3_102_POST_LAST_DETECTION_GATE_ATTRITION_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_102_POST_LAST_DETECTION_GATE_ATTRITION_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "goldsharp_m15.csv").exists() and (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise SystemExit("Files dir not found")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as e:
        return {"_error": repr(e)}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def load_stage45(path: Path):
    spec = importlib.util.spec_from_file_location("gold_v3_stage45", path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def filter_text(f: dict[str, Any]) -> str:
    if f.get("type") == "cat":
        return f"{f.get('id')} {f.get('col')} != {f.get('val')} rank={f.get('rank')}"
    return f"{f.get('id')} NOT {f.get('col')} in [{f.get('lo')},{f.get('hi')}) rank={f.get('rank')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--start", default="2026-06-02 15:00:00")
    ap.add_argument("--end", default="")
    ap.add_argument("--output-dir", default="")
    args = ap.parse_args()

    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    base = src / "FX_OUTPUTS" / "gold_v3"
    out = Path(args.output_dir).resolve() if args.output_dir else base / "102c"
    out.mkdir(parents=True, exist_ok=True)

    p45 = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")
    p50q = base / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only" / "gold_v3_50_rolling_prior_60d_q70_state.csv"
    checks = []
    blockers = []
    for name, path in [("stage45", p45), ("stage50_q70", p50q), ("m15", src/"goldsharp_m15.csv"), ("h4", src/"goldsharp_h4.csv"), ("m5", src/"goldsharp_m5.csv")]:
        checks.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append({"blocker_id": f"{name}_missing", "reason": "REQUIRED_INPUT_MISSING", "detail": str(path), "severity": "BLOCKER"})

    attr_rows = []
    filt_rows = []
    seq_rows = []
    source_daily = pd.DataFrame()
    feature_summary = pd.DataFrame()
    if not blockers:
        try:
            st45 = load_stage45(p45)
            m15, _m5 = st45.prepare(src, "closed", 60, 0.70)
            q = read_csv(p50q)
            if not q.empty:
                q["m15_time_jst"] = pd.to_datetime(q["m15_time_jst"], errors="coerce")
                q = q.dropna(subset=["m15_time_jst"]).drop_duplicates("m15_time_jst")
                m15 = m15.drop(columns=["m15_atr28_q", "is_high_vol"], errors="ignore")
                m15 = m15.merge(q[["m15_time_jst", "atr28_q70", "high_vol_pass"]], left_on="time", right_on="m15_time_jst", how="left")
                m15["m15_atr28_q"] = pd.to_numeric(m15["atr28_q70"], errors="coerce")
                m15["is_high_vol"] = m15["high_vol_pass"].fillna(False).astype(bool)
            start = pd.Timestamp(args.start)
            end = pd.Timestamp(args.end) if args.end else pd.to_datetime(m15["time"], errors="coerce").max()
            m15w = m15[(pd.to_datetime(m15["time"], errors="coerce") >= start) & (pd.to_datetime(m15["time"], errors="coerce") <= end)].copy()
            src_rows = st45.source_rows(m15w)
            if not src_rows.empty:
                src_rows["day"] = pd.to_datetime(src_rows["time"]).dt.date.astype(str)
                source_daily = src_rows.groupby(["day", "source_rank"], dropna=False).size().rename("source_rows").reset_index()
            cols = ["h4_ret4", "m15_atr28", "m15_atr28_q", "is_high_vol", "jst_hour", "jst_weekday"]
            fs = []
            for c in cols:
                if c not in m15w.columns:
                    continue
                s = m15w[c]
                if pd.api.types.is_numeric_dtype(s) or c == "is_high_vol":
                    ss = pd.to_numeric(s, errors="coerce") if c != "is_high_vol" else s.astype(int)
                    fs.append({"feature": c, "non_null": int(ss.notna().sum()), "min": ss.min(), "median": ss.median(), "max": ss.max(), "true_count": int(ss.sum()) if c == "is_high_vol" else ""})
                else:
                    vc = s.astype(str).value_counts(dropna=False)
                    fs.append({"feature": c, "non_null": int(s.notna().sum()), "min": "", "median": "", "max": "", "true_count": "; ".join([f"{k}={v}" for k, v in vc.items()])})
            feature_summary = pd.DataFrame(fs)
            cands = st45.base_candidates() + st45.add_hv_siblings(st45.base_candidates())
            for c in cands:
                sub0 = src_rows[src_rows.source_rank.astype(str).isin(c["ranks"])].copy() if not src_rows.empty else pd.DataFrame()
                cur = sub0.copy()
                attr_rows.append({"candidate_label": c["label"], "stage": "source_rank_base", "rows": int(len(sub0)), "ranks": ",".join(map(str, c["ranks"]))})
                for f in c["filters"]:
                    if cur.empty:
                        before = 0; rejected = 0; after = 0
                    else:
                        before = int(len(cur))
                        keep = st45.keep_mask(cur, f)
                        rejected = int((~keep).sum())
                        cur = cur[keep].copy()
                        after = int(len(cur))
                    seq_rows.append({"candidate_label": c["label"], "filter_id": f.get("id", ""), "filter": filter_text(f), "before_rows": before, "rejected_rows": rejected, "after_rows": after})
                final_rows = int(len(cur))
                attr_rows.append({"candidate_label": c["label"], "stage": "after_all_filters_before_cooldown", "rows": final_rows, "ranks": ",".join(map(str, c["ranks"]))})
                for f in c["filters"]:
                    if sub0.empty:
                        rej = 0
                    else:
                        rej = int((~st45.keep_mask(sub0, f)).sum())
                    filt_rows.append({"candidate_label": c["label"], "filter_id": f.get("id", ""), "filter": filter_text(f), "rejected_from_base_rows": rej, "base_rows": int(len(sub0))})
            checks.append(ok("window_m15_rows_positive", len(m15w) > 0, len(m15w), ">0"))
            checks.append(ok("source_rows_positive_or_explain", len(src_rows) > 0, len(src_rows), ">0", "WARN"))
        except Exception as e:
            checks.append(ok("stage102_runtime", False, repr(e), "no_exception"))
            blockers.append({"blocker_id": "stage102_runtime_error", "reason": "RUNTIME_EXCEPTION", "detail": repr(e), "severity": "BLOCKER"})

    attr = pd.DataFrame(attr_rows)
    filt = pd.DataFrame(filt_rows)
    seq = pd.DataFrame(seq_rows)
    for c in checks:
        if c["result"] != "PASS" and c.get("severity") == "BLOCKER":
            blockers.append({"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"})
    status = READY if not blockers else BLOCKED

    attr.to_csv(out / "candidate_gate_attrition.csv", index=False, encoding="utf-8-sig")
    filt.to_csv(out / "filter_reject_counts.csv", index=False, encoding="utf-8-sig")
    seq.to_csv(out / "filter_sequential_attrition.csv", index=False, encoding="utf-8-sig")
    source_daily.to_csv(out / "source_rank_daily_counts.csv", index=False, encoding="utf-8-sig")
    feature_summary.to_csv(out / "recent_feature_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out / "validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")

    final = attr[attr["stage"].eq("after_all_filters_before_cooldown")].copy() if not attr.empty else pd.DataFrame()
    source_base = attr[attr["stage"].eq("source_rank_base")].copy() if not attr.empty else pd.DataFrame()
    top_final = final.sort_values("rows", ascending=False).head(20) if not final.empty else pd.DataFrame()
    top_seq_zero = seq[(seq["before_rows"] > 0) & (seq["after_rows"] == 0)].copy() if not seq.empty else pd.DataFrame()
    top_seq_zero = top_seq_zero.sort_values(["before_rows", "rejected_rows"], ascending=False).head(40) if not top_seq_zero.empty else pd.DataFrame()
    max_final_rows = int(final["rows"].max()) if not final.empty else 0
    max_source_rows = int(source_base["rows"].max()) if not source_base.empty else 0
    summary = {
        "status": status,
        "post_last_detection_gate_attrition_ready": status == READY,
        "audit_only": True,
        "live_ready": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "final_signal_enabled": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "pool_policy": POOL_POLICY,
        "window_start": args.start,
        "window_end": str(end) if 'end' in locals() else "",
        "source_rank_max_base_rows": max_source_rows,
        "candidate_max_rows_after_filters_before_cooldown": max_final_rows,
        "candidate_count_with_rows_after_filters": int((final["rows"] > 0).sum()) if not final.empty else 0,
        "blocker_count": len(blockers),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 102 PASTE_ME_POST_LAST_DETECTION_GATE_ATTRITION_SUMMARY",
        f"status: {status}",
        f"post_last_detection_gate_attrition_ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"window_start: {summary['window_start']}",
        f"window_end: {summary['window_end']}",
        f"source_rank_max_base_rows: {max_source_rows}",
        f"candidate_max_rows_after_filters_before_cooldown: {max_final_rows}",
        f"candidate_count_with_rows_after_filters: {summary['candidate_count_with_rows_after_filters']}",
        f"blocker_count: {len(blockers)}",
        "", "RECENT_FEATURE_SUMMARY", feature_summary.to_string(index=False) if not feature_summary.empty else "NO_FEATURE_SUMMARY",
        "", "SOURCE_RANK_DAILY_COUNTS", source_daily.to_string(index=False) if not source_daily.empty else "NO_SOURCE_ROWS",
        "", "TOP_CANDIDATES_AFTER_FILTERS", top_final.to_string(index=False) if not top_final.empty else "NO_CANDIDATE_ROWS_AFTER_FILTERS",
        "", "FILTERS_THAT_ZEROED_SEQUENTIAL_ROWS", top_seq_zero.to_string(index=False) if not top_seq_zero.empty else "NO_ZEROING_FILTERS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "source_rank_daily_counts.csv", "candidate_gate_attrition.csv", "filter_reject_counts.csv", "filter_sequential_attrition.csv", "recent_feature_summary.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 102 post-last-detection gate attrition\n\nStatus: `{status}`\n\n- max source base rows: `{max_source_rows}`\n- max candidate rows after filters: `{max_final_rows}`\n- candidates with rows after filters: `{summary['candidate_count_with_rows_after_filters']}`\n- blockers: `{len(blockers)}`\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
