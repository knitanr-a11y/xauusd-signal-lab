#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path
from typing import Any
import pandas as pd

READY = "GOLD_V3_103_HIGH_VOL_REACHABILITY_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_103_HIGH_VOL_REACHABILITY_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "goldsharp_m15.csv").exists() and (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise SystemExit("Files dir not found")


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


def ok(cid: str, passed: bool, obs: Any, exp: Any, sev: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": cid, "result": "PASS" if passed else "FAIL", "observed": obs, "expected": exp, "severity": sev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--start", default="2026-06-02 15:00:00")
    ap.add_argument("--end", default="")
    ap.add_argument("--output-dir", default="")
    args = ap.parse_args()

    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    base = src / "FX_OUTPUTS" / "gold_v3"
    out = Path(args.output_dir).resolve() if args.output_dir else base / "103c"
    out.mkdir(parents=True, exist_ok=True)
    p45 = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")
    p50q = base / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only" / "gold_v3_50_rolling_prior_60d_q70_state.csv"
    checks = []
    blockers = []
    for name, path in [("stage45", p45), ("stage50_q70", p50q), ("m15", src/"goldsharp_m15.csv"), ("h4", src/"goldsharp_h4.csv"), ("m5", src/"goldsharp_m5.csv")]:
        checks.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append({"blocker_id": f"{name}_missing", "reason": "REQUIRED_INPUT_MISSING", "detail": str(path), "severity": "BLOCKER"})
    rows = []
    feature = pd.DataFrame()
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
            win = m15[(pd.to_datetime(m15["time"], errors="coerce") >= start) & (pd.to_datetime(m15["time"], errors="coerce") <= end)].copy()
            src_rows = st45.source_rows(win)
            hv_all = win[win["is_high_vol"].fillna(False).astype(bool)].copy()
            hv_src = src_rows[src_rows["is_high_vol"].fillna(False).astype(bool)].copy() if not src_rows.empty else pd.DataFrame()
            base_cands = st45.base_candidates()
            hv_cands = st45.add_hv_siblings(base_cands)
            cand_map = {c["label"]: c for c in base_cands}
            for hc in hv_cands:
                base_label = hc["label"].split("__HV_")[0].replace("HV_", "", 1)
                bc = cand_map.get(base_label)
                ranks = hc["ranks"]
                src_base = src_rows[src_rows.source_rank.astype(str).isin(ranks)].copy() if not src_rows.empty else pd.DataFrame()
                hv_universe = hv_all.copy()
                hv_src_base = src_base[src_base["is_high_vol"].fillna(False).astype(bool)].copy() if not src_base.empty else pd.DataFrame()
                cur_base = src_base.copy()
                cur_hv = src_base.copy()
                if bc is not None:
                    for f in bc["filters"]:
                        if not cur_base.empty:
                            cur_base = cur_base[st45.keep_mask(cur_base, f)].copy()
                    for f in hc["filters"]:
                        if not cur_hv.empty:
                            cur_hv = cur_hv[st45.keep_mask(cur_hv, f)].copy()
                inherited_source_blocked_hv = max(0, len(hv_universe) - len(hv_src_base))
                rows.append({
                    "hv_candidate_label": hc["label"],
                    "base_candidate_label": base_label,
                    "ranks": ",".join(map(str, ranks)),
                    "window_m15_rows": int(len(win)),
                    "high_vol_m15_rows": int(len(hv_all)),
                    "source_rows_for_ranks": int(len(src_base)),
                    "high_vol_source_rows_for_ranks": int(len(hv_src_base)),
                    "high_vol_rows_blocked_by_inherited_source_conditions": int(inherited_source_blocked_hv),
                    "base_after_original_filters": int(len(cur_base)),
                    "hv_after_original_filters_plus_high_vol": int(len(cur_hv)),
                    "reachable_as_high_vol_sibling": bool(len(cur_hv) > 0),
                })
            fs = []
            for col in ["m15_atr28", "m15_atr28_q", "h4_ret4", "is_high_vol", "jst_hour", "jst_weekday"]:
                if col not in win.columns: continue
                s = win[col]
                if col == "jst_weekday":
                    vc = s.astype(str).value_counts(dropna=False)
                    fs.append({"feature": col, "summary": "; ".join([f"{k}={v}" for k, v in vc.items()])})
                else:
                    ss = s.astype(int) if col == "is_high_vol" else pd.to_numeric(s, errors="coerce")
                    fs.append({"feature": col, "non_null": int(ss.notna().sum()), "min": ss.min(), "median": ss.median(), "max": ss.max(), "true_count": int(ss.sum()) if col == "is_high_vol" else ""})
            feature = pd.DataFrame(fs)
            checks.append(ok("window_rows_positive", len(win) > 0, len(win), ">0"))
            checks.append(ok("high_vol_rows_positive", len(hv_all) > 0, len(hv_all), ">0", "WARN"))
        except Exception as e:
            checks.append(ok("stage103_runtime", False, repr(e), "no_exception"))
            blockers.append({"blocker_id": "stage103_runtime_error", "reason": "RUNTIME_EXCEPTION", "detail": repr(e), "severity": "BLOCKER"})
    df = pd.DataFrame(rows)
    for c in checks:
        if c["result"] != "PASS" and c.get("severity") == "BLOCKER":
            blockers.append({"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"})
    status = READY if not blockers else BLOCKED
    df.to_csv(out / "high_vol_reachability.csv", index=False, encoding="utf-8-sig")
    feature.to_csv(out / "high_vol_feature_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out / "validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")
    reachable = int(df["reachable_as_high_vol_sibling"].sum()) if not df.empty else 0
    max_hv_after = int(df["hv_after_original_filters_plus_high_vol"].max()) if not df.empty else 0
    max_hv_source = int(df["high_vol_source_rows_for_ranks"].max()) if not df.empty else 0
    max_hv_univ = int(df["high_vol_m15_rows"].max()) if not df.empty else 0
    summary = {
        "status": status,
        "high_vol_reachability_ready": status == READY,
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
        "high_vol_m15_rows": max_hv_univ,
        "max_high_vol_source_rows_for_ranks": max_hv_source,
        "reachable_high_vol_sibling_count": reachable,
        "max_hv_after_original_filters_plus_high_vol": max_hv_after,
        "blocker_count": len(blockers),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    top = df.sort_values(["hv_after_original_filters_plus_high_vol", "high_vol_source_rows_for_ranks"], ascending=False).head(40) if not df.empty else pd.DataFrame()
    blocked = df[df["high_vol_source_rows_for_ranks"].eq(0)].head(40) if not df.empty else pd.DataFrame()
    paste = [
        "GOLD V3 103 PASTE_ME_HIGH_VOL_REACHABILITY_SUMMARY",
        f"status: {status}",
        f"high_vol_reachability_ready: {str(status == READY).lower()}",
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
        f"high_vol_m15_rows: {max_hv_univ}",
        f"max_high_vol_source_rows_for_ranks: {max_hv_source}",
        f"reachable_high_vol_sibling_count: {reachable}",
        f"max_hv_after_original_filters_plus_high_vol: {max_hv_after}",
        f"blocker_count: {len(blockers)}",
        "", "HIGH_VOL_FEATURE_SUMMARY", feature.to_string(index=False) if not feature.empty else "NO_FEATURE_ROWS",
        "", "TOP_HIGH_VOL_REACHABILITY", top.to_string(index=False) if not top.empty else "NO_REACHABILITY_ROWS",
        "", "HIGH_VOL_SOURCE_ZERO_ROWS_SAMPLE", blocked.to_string(index=False) if not blocked.empty else "NO_SOURCE_ZERO_ROWS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "high_vol_reachability.csv", "high_vol_feature_summary.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 103 high-vol reachability\n\nStatus: `{status}`\n\n- high_vol_m15_rows: `{max_hv_univ}`\n- max_high_vol_source_rows_for_ranks: `{max_hv_source}`\n- reachable_high_vol_sibling_count: `{reachable}`\n- max_hv_after_original_filters_plus_high_vol: `{max_hv_after}`\n- blockers: `{len(blockers)}`\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
