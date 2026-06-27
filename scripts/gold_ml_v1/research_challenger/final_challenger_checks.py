from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from final_challenger_metrics import (
    IDS,
    basic_check,
    component_metric,
    load_csv,
    metric,
    record_set,
    same_metrics,
    sha256,
)


def verify(artifact_dir: Path, manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[int, pd.DataFrame]]:
    checks: list[dict[str, Any]] = []
    hash_details, hash_ok = {}, True
    for filename, info in manifest["files"].items():
        path = artifact_dir / filename
        actual = sha256(path) if path.exists() else None
        ok = actual == info["local_sha256"]
        hash_ok &= ok
        hash_details[filename] = {"exists": path.exists(), "actual": actual, "expected": info["local_sha256"], "passed": ok}
    checks.append({"name": "artifact_hashes", "passed": hash_ok, "details": hash_details})

    summary = json.loads((artifact_dir / "completion_challenger_v1_summary.json").read_text(encoding="utf-8"))
    completion: dict[int, pd.DataFrame] = {}
    completion_details, completion_ok = {}, True
    annual_keys = ["trades", "win_rate", "pf", "R", "DD", "top5_removed_R", "top5pct_removed_R", "positive_months", "negative_months"]
    component_keys = ["trades", "win_rate", "pf", "R", "mean_size"]
    for year in (2024, 2025, 2026):
        df = load_csv(artifact_dir / f"completion_challenger_v1_{year}.csv")
        completion[year] = df
        annual_ok, annual_diff = same_metrics(metric(df), summary[str(year)], annual_keys)
        actual_components = component_metric(df)
        component_diff = {}
        for comp, expected in summary[str(year)]["components"].items():
            ok, diff = same_metrics(actual_components.get(comp, {}), expected, component_keys)
            if not ok:
                component_diff[comp] = diff
        year_ok = annual_ok and not component_diff
        completion_ok &= year_ok
        completion_details[str(year)] = {"passed": year_ok, "annual_diff": annual_diff, "component_diff": component_diff}
        checks.append(basic_check(df, f"completion_basic_{year}", False, True))
    checks.append({"name": "completion_parity", "passed": completion_ok, "details": completion_details})

    watch_summary = json.loads((artifact_dir / "watch_addon_decision_summary.json").read_text(encoding="utf-8"))
    watch022: dict[int, pd.DataFrame] = {}
    watch_details, watch_ok = {}, True
    for year in (2024, 2025, 2026):
        raw = load_csv(artifact_dir / f"watch022c_challenger_{year}.csv")
        after = load_csv(artifact_dir / f"watch022c_challenger_{year}.csv", True)
        watch022[year] = after
        key = "2026_partial" if year == 2026 else str(year)
        expected = watch_summary["challenger_comparison"][key]["after"]
        exp = {"trades": expected["trades"], "win_rate": expected["win_rate"], "pf": expected["pf"], "R": expected["R"], "DD": expected["DD"]}
        metric_ok, metric_diff = same_metrics(metric(after), exp, list(exp))
        before = completion[year]
        noncore_ok = record_set(before[~before["comp"].eq("A_CORE")]) == record_set(after[~after["comp"].eq("A_CORE")])
        subset_ok = record_set(after[after["comp"].eq("A_CORE")]) <= record_set(before[before["comp"].eq("A_CORE")].assign(candidate_id=IDS["A_CORE"]))
        omission_ok = int(raw["candidate_id"].isna().sum()) == int(raw["comp"].eq("A_CORE").sum()) and int(raw["w"].isna().sum()) == int(raw["comp"].eq("A_CORE").sum())
        year_ok = metric_ok and noncore_ok and subset_ok and omission_ok
        watch_ok &= year_ok
        watch_details[str(year)] = {"passed": year_ok, "metric_diff": metric_diff, "noncore_unchanged": noncore_ok, "strict_subset": subset_ok, "known_omission_only": omission_ok}
        checks.append(basic_check(raw, f"watch022c_basic_{year}", True))
    checks.append({"name": "watch022c_replacement", "passed": watch_ok, "details": watch_details})

    final_summary = json.loads((artifact_dir / "watch024a_addition_summary.json").read_text(encoding="utf-8"))
    exact = pd.read_csv(artifact_dir / "watch024a_exact_candidate_trades.csv")
    exact["decision_time"] = pd.to_datetime(exact["decision_time"], errors="raise")
    exact["exit_time"] = pd.to_datetime(exact["exit_time"], errors="raise")
    final_frames: dict[int, pd.DataFrame] = {}
    final_details, final_ok = {}, True
    for year in (2024, 2025, 2026):
        raw = load_csv(artifact_dir / f"watch024a_challenger_{year}.csv")
        final = load_csv(artifact_dir / f"watch024a_challenger_{year}.csv", True)
        final_frames[year] = final
        expected = final_summary["portfolio_addition"]["before_after"][str(year)]["after"]
        exp = {
            "trades": expected["trades"], "win_rate": expected["win_rate"],
            "pf": expected["profit_factor"], "R": expected["total_r"],
            "DD": expected["max_drawdown_r"], "positive_months": expected["positive_months"],
            "negative_months": expected["negative_months"],
        }
        metric_ok, metric_diff = same_metrics(metric(final), exp, list(exp))
        prior_set, final_set = record_set(watch022[year]), record_set(final)
        additions = final[final["comp"].eq("W024A")]
        source = exact[exact["decision_time"].dt.year.eq(year)]
        transformed = pd.DataFrame({
            "candidate_id": IDS["W024A"], "decision_time": source["decision_time"],
            "exit_time": source["exit_time"], "r": pd.to_numeric(source["base_r"]),
            "direction": source["direction"], "comp": "W024A", "w": 1.0, "size": 1.0,
            "weighted_r": pd.to_numeric(source["base_r"]),
        })
        prior_ok = prior_set <= final_set
        addition_ok = record_set(additions) == record_set(transformed)
        no_other = len(final_set - prior_set) == len(additions)
        year_ok = metric_ok and prior_ok and addition_ok and no_other
        final_ok &= year_ok
        final_details[str(year)] = {"passed": year_ok, "metric_diff": metric_diff, "watch022c_preserved": prior_ok, "watch024a_exact_base_r": addition_ok, "no_other_additions": no_other}
        checks.append(basic_check(raw, f"watch024a_basic_{year}", True))
    checks.append({"name": "watch024a_final_addition", "passed": final_ok, "details": final_details})

    rules = json.loads((artifact_dir / "stable_loss_leaf_rules.json").read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for rule in rules:
        counts[rule["candidate"]] = counts.get(rule["candidate"], 0) + 1
    expected_counts = manifest["ml_lineage"]["stable_loss_rule_counts"]
    ml_ok = counts == expected_counts and manifest["ml_lineage"]["candidate_local_model_artifacts_present"] is False
    checks.append({"name": "ml_lineage_audit", "passed": ml_ok, "details": {"rule_counts": counts, "expected": expected_counts, "fresh_inference": False, "substitution": "forbidden"}})
    return checks, final_frames
