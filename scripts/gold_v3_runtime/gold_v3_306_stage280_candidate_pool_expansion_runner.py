#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import gold_v3_306_stage280_candidate_pool_expansion as stage306


def corrected_build_trade_cache(year_models, outcomes):
    cache = {}
    family_results = []
    for family in stage306.FAMILIES:
        name = family["name"]
        for quantile in stage306.QUANTILES:
            combined = []
            yearly = {}
            for model in year_models:
                year = int(model["year"])
                threshold = model["thresholds"][quantile]
                selected = []
                for index, template in outcomes[name].items():
                    if pd.Timestamp(template["decision_dt"]).year != year:
                        continue
                    score = model["scores"].get(index)
                    if score is None or score < threshold:
                        continue
                    trade = dict(template)
                    trade["ml_score"] = float(score)
                    trade["context_index"] = int(index)
                    trade["year"] = year
                    selected.append(trade)

                # Pool replay must receive every raw selected candidate. Applying the
                # one-position rule here would remove trades that can become available
                # after another family wins an earlier overlap during combined replay.
                cache[(name, quantile, year)] = selected

                standalone = stage306.one_position(selected)
                metrics = stage306.base.summarize_trades(standalone)
                yearly[str(year)] = {
                    "threshold": threshold,
                    "raw": len(selected),
                    "metrics": metrics,
                }
                combined.extend(standalone)

            aggregate = stage306.base.summarize_trades(combined)
            worst_year_r = min(
                value["metrics"]["spread_adjusted_total_r"]
                for value in yearly.values()
            )
            minimum_year_trades = min(
                value["metrics"]["trades"] for value in yearly.values()
            )
            passed = bool(
                aggregate["trades"] >= 50
                and minimum_year_trades >= 12
                and aggregate["win_rate"] >= 0.52
                and stage306.pf_value(aggregate) >= 1.40
                and aggregate["spread_adjusted_max_drawdown_r"] <= 10.0
                and worst_year_r > 0
            )
            family_results.append({
                "candidate_key": f"{name}|{quantile}",
                "family": name,
                "quantile": quantile,
                "aggregate": aggregate,
                "minimum_year_trades": minimum_year_trades,
                "worst_year_r": worst_year_r,
                "research_pass": passed,
                "yearly": yearly,
            })

    family_results.sort(
        key=lambda row: (
            not row["research_pass"],
            -row["aggregate"]["trades"],
            -row["aggregate"]["spread_adjusted_total_r"],
        )
    )
    return cache, family_results


stage306.build_trade_cache = corrected_build_trade_cache

if __name__ == "__main__":
    raise SystemExit(stage306.main())
