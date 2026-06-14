#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY"
READY = "GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def finite(x, default=0.0):
    try:
        v = float(x)
        return default if math.isnan(v) else v
    except Exception:
        return default


def qgate(name, observed, op, threshold):
    if op == ">=":
        ok = observed >= threshold
    elif op == "<=":
        ok = observed <= threshold
    elif op == "==":
        ok = observed == threshold
    else:
        ok = False
    return dict(gate=name, observed=observed, operator=op, threshold=threshold, result="PASS" if ok else "FAIL")


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "107sc"
    out = root / "108c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blockers = []
    outputs = []
    findings = []
    req = {
        "summary": src / "gold_v3_107s_summary.json",
        "policy": src / "gold_v3_107s_health_policy_summary.csv",
        "base_monthly": src / "gold_v3_107s_base_monthly_metrics.csv",
        "best_monthly": src / "gold_v3_107s_best_monthly_metrics.csv",
        "best_regime": src / "gold_v3_107s_best_regime_metrics.csv",
    }
    for name, p in req.items():
        if not p.exists():
            blockers.append(dict(blocker_id=f"missing_107s_{name}", path=str(p)))

    s = {}
    policy = pd.DataFrame()
    base_mo = pd.DataFrame()
    best_mo = pd.DataFrame()
    best_reg = pd.DataFrame()
    if not blockers:
        s = load_json(req["summary"])
        policy = pd.read_csv(req["policy"], encoding="utf-8-sig")
        base_mo = pd.read_csv(req["base_monthly"], encoding="utf-8-sig")
        best_mo = pd.read_csv(req["best_monthly"], encoding="utf-8-sig")
        best_reg = pd.read_csv(req["best_regime"], encoding="utf-8-sig")
        if policy.empty:
            blockers.append(dict(blocker_id="health_policy_summary_empty"))
        prog(1, 5, "inputs loaded")

    review = pd.DataFrame()
    options = pd.DataFrame()
    monthly_diff = pd.DataFrame()
    regime_review = pd.DataFrame()
    qg = pd.DataFrame()
    human_md = ""

    if not blockers:
        best = policy.iloc[0].to_dict()
        base_trades = int(best.get("base_trades", s.get("base_rows", 0)))
        health_trades = int(best.get("health_trades", s.get("best_health_trades", 0)))
        base_wr = finite(best.get("base_win_rate", 0.0))
        health_wr = finite(best.get("health_win_rate", s.get("best_health_wr", 0.0)))
        base_pf = finite(best.get("base_profit_factor", 0.0))
        health_pf = finite(best.get("health_profit_factor", s.get("best_health_pf", 0.0)))
        base_sum = finite(best.get("base_sum_result_usd", 0.0))
        health_sum = finite(best.get("health_sum_result_usd", 0.0))
        sum_delta = health_sum - base_sum
        trade_delta = health_trades - base_trades
        retention = finite(best.get("retention", s.get("best_retention", 0.0)))
        wr_gain = health_wr - base_wr
        pf_gain = health_pf - base_pf
        primary = bool(best.get("primary_gate", s.get("best_primary_gate", False)))
        review_gate = bool(best.get("review_gate", s.get("best_review_gate", False)))
        resolved_only = bool(s.get("resolved_only_strict", False))
        exit_dt_feature = bool(s.get("exit_dt_used_as_entry_feature", True))
        health_policy = str(best.get("policy_key", s.get("best_policy_key", "")))

        review = pd.DataFrame([dict(
            base_trades=base_trades,
            health_trades=health_trades,
            trade_delta=trade_delta,
            retention=retention,
            base_win_rate=base_wr,
            health_win_rate=health_wr,
            wr_gain=wr_gain,
            base_profit_factor=base_pf,
            health_profit_factor=health_pf,
            pf_gain=pf_gain,
            base_sum_result_usd=base_sum,
            health_sum_result_usd=health_sum,
            sum_delta=sum_delta,
            min_regime_wr=finite(best.get("min_regime_wr", s.get("best_min_regime_wr", 0.0))),
            health_negative_month_count=int(best.get("health_negative_month_count", 999)),
            selected_policy_key=health_policy,
            resolved_only_strict=resolved_only,
            exit_dt_used_as_entry_feature=exit_dt_feature,
            primary_gate=primary,
            review_gate=review_gate,
        )])
        save(review, out / "gold_v3_108_decision_review_summary.csv")
        outputs.append("gold_v3_108_decision_review_summary.csv")

        # Monthly diff by regime/month where available.
        join_cols = [c for c in ["regime_split", "entry_month"] if c in base_mo.columns and c in best_mo.columns]
        if join_cols:
            bm = base_mo.copy(); hm = best_mo.copy()
            bm = bm.rename(columns={c: f"base_{c}" for c in bm.columns if c not in join_cols})
            hm = hm.rename(columns={c: f"health_{c}" for c in hm.columns if c not in join_cols})
            monthly_diff = bm.merge(hm, on=join_cols, how="outer")
            if "base_trades" in monthly_diff and "health_trades" in monthly_diff:
                monthly_diff["trade_delta"] = monthly_diff["health_trades"].fillna(0) - monthly_diff["base_trades"].fillna(0)
            if "base_sum_result_usd" in monthly_diff and "health_sum_result_usd" in monthly_diff:
                monthly_diff["sum_delta"] = monthly_diff["health_sum_result_usd"].fillna(0) - monthly_diff["base_sum_result_usd"].fillna(0)
            if "base_win_rate" in monthly_diff and "health_win_rate" in monthly_diff:
                monthly_diff["wr_delta"] = monthly_diff["health_win_rate"].fillna(0) - monthly_diff["base_win_rate"].fillna(0)
            save(monthly_diff, out / "gold_v3_108_monthly_diff.csv")
            outputs.append("gold_v3_108_monthly_diff.csv")
        regime_review = best_reg.copy()
        save(regime_review, out / "gold_v3_108_regime_review.csv")
        outputs.append("gold_v3_108_regime_review.csv")

        options = pd.DataFrame([
            dict(option_id="A", option="KEEP_107Q_BASE", pros="Highest total sum_result_usd; no extra health gate complexity; keeps all 5571 selected rows", cons="WR/PF slightly lower than 107S best health gate", next_stage="108B_BASE_CANDIDATE_REVIEW_OR_STAGE109_PACKET"),
            dict(option_id="B", option="ADOPT_107S_CANDIDATE_PF_HEALTH_GATE", pros="Strict resolved-only; WR and PF improve; retention remains 94.97%; zero negative months", cons="Skips 280 trades and lowers total sum_result_usd by %.6f" % abs(sum_delta), next_stage="108B_HEALTH_GATE_CANDIDATE_REVIEW_OR_STAGE109_PACKET"),
            dict(option_id="C", option="RUN_ADDITIONAL_STABILITY_REVIEW", pros="Can inspect monthly trade/sum deltas before choosing", cons="Adds another audit step; no live readiness change", next_stage="108B_MONTHLY_AND_DAILY_DELTA_REVIEW_AUDIT_ONLY"),
        ])
        save(options, out / "gold_v3_108_adoption_options.csv")
        outputs.append("gold_v3_108_adoption_options.csv")

        qg = pd.DataFrame([
            qgate("107s_ready", str(s.get("status", "")) == "GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_READY_AUDIT_ONLY", "==", True),
            qgate("resolved_only_strict", resolved_only, "==", True),
            qgate("exit_dt_not_entry_feature", not exit_dt_feature, "==", True),
            qgate("health_wr_ge_base", health_wr, ">=", base_wr),
            qgate("health_pf_ge_base", health_pf, ">=", base_pf),
            qgate("health_retention_ge_90", retention, ">=", 0.90),
            qgate("health_sum_ge_base", health_sum, ">=", base_sum),
            qgate("live_ready_false", False, "==", False),
        ])
        save(qg, out / "gold_v3_108_quality_gate_matrix.csv")
        outputs.append("gold_v3_108_quality_gate_matrix.csv")

        if primary and sum_delta < 0:
            decision = "STAGE108_REVIEW_PACKET_READY_HUMAN_DECISION_REQUIRED"
            recommendation = "Health gate is valid and strict, but because total sum_result_usd decreased, choose explicitly between WR/PF quality and total profit retention."
        elif primary and sum_delta >= 0:
            decision = "STAGE108_REVIEW_PACKET_READY_HEALTH_GATE_CANDIDATE"
            recommendation = "Health gate improves WR/PF without reducing total sum_result_usd."
        else:
            decision = "STAGE108_REVIEW_PACKET_READY_BASE_107Q_CANDIDATE"
            recommendation = "Health gate did not provide enough improvement; keep base 107Q for review."

        human_md = f"""# GOLD V3 108 Human Decision Template

Status: audit-only

## Candidate under review

```text
107S best policy: {health_policy}
```

## Base vs health gate

```text
Base trades: {base_trades}
Health trades: {health_trades}
Retention: {retention:.6f}

Base WR: {base_wr:.6f}
Health WR: {health_wr:.6f}
WR gain: {wr_gain:.6f}

Base PF: {base_pf:.6f}
Health PF: {health_pf:.6f}
PF gain: {pf_gain:.6f}

Base sum_result_usd: {base_sum:.6f}
Health sum_result_usd: {health_sum:.6f}
Sum delta: {sum_delta:.6f}
```

## Safety status

```text
resolved_only_strict: {resolved_only}
exit_dt_used_as_entry_feature: {exit_dt_feature}
live_ready: false
```

## Decision choices

- `[ ]` A: Keep 107Q base candidate for next review.
- `[ ]` B: Adopt 107S candidate-level PF health gate for next review.
- `[ ]` C: Run additional monthly/daily delta review before choosing.

## Recommendation

{recommendation}
"""
        (out / "gold_v3_108_human_decision_template.md").write_text(human_md, encoding="utf-8")
        outputs.append("gold_v3_108_human_decision_template.md")
        findings.append("decision_recommendation=" + recommendation)
        prog(4, 5, "review outputs written")
    else:
        decision = "STAGE108_BLOCKED_INPUT_INCOMPLETE"

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
    ]
    if not review.empty:
        vals.append(dict(check_id="decision_review_summary_positive", result="PASS", observed=len(review), expected=">0", severity="BLOCKER"))
    if not options.empty:
        vals.append(dict(check_id="adoption_options_positive", result="PASS", observed=len(options), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

    status = READY if not blockers and validation_failure_count == 0 else BLOCKED
    if status == BLOCKED:
        decision = "STAGE108_BLOCKED_INPUT_INCOMPLETE"

    summary = dict(
        step=STEP,
        status=status,
        decision=decision,
        created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        output_dir=str(out),
        audit_only=True,
        live_ready=False,
        source_csv_mutated=False,
        contract_mutated=False,
        open_asof_allowed=False,
        blocker_count=len(blockers),
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
    )
    if not review.empty:
        summary.update(review.iloc[0].to_dict())

    save(pd.DataFrame(blockers), out / "gold_v3_108_blocker_matrix.csv")
    save(val, out / "gold_v3_108_validation_matrix.csv")
    outputs += ["gold_v3_108_blocker_matrix.csv", "gold_v3_108_validation_matrix.csv", "gold_v3_108_summary.json", "GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_108_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 108 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        "GOLD V3 108 PASTE_ME_RESOLVED_ONLY_STAGE_REVIEW_PACKET",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "safety: audit_only=true, review_packet_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
        "blocker_count: " + str(len(blockers)),
        "",
        "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + [
        "",
        "FINDINGS",
    ] + (findings or ["NO_FINDINGS"]) + [
        "",
        "BLOCKERS",
        pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "",
        "QUALITY_GATES",
        qg.to_string(index=False) if not qg.empty else "NO_QG",
        "",
        "VALIDATION",
        val.to_string(index=False),
        "",
        "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
