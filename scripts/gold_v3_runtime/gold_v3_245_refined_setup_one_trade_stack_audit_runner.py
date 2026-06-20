#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd

import gold_v3_245_refined_setup_one_trade_stack_audit as stage245


def fixed_make_signal_frame(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    signal = stage245.build_features(frames["m15"], "m15")
    for tf in ["h1", "h4", "d1"]:
        htf = stage245.build_features(frames[tf], tf)
        source_time = f"{tf}_source_close_time"
        htf = htf.rename(columns={"close_time": source_time})
        keep = list(dict.fromkeys([source_time] + [c for c in htf.columns if c.startswith(tf + "_")]))
        selected = htf.loc[:, keep]
        if selected.columns.duplicated().any():
            duplicates = selected.columns[selected.columns.duplicated()].tolist()
            raise RuntimeError(f"duplicate HTF columns after dedupe for {tf}: {duplicates}")
        signal = pd.merge_asof(
            signal.sort_values("close_time"),
            selected.sort_values(source_time),
            left_on="close_time",
            right_on=source_time,
            direction="backward",
            allow_exact_matches=True,
        )
    return signal.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


stage245.make_signal_frame = fixed_make_signal_frame


if __name__ == "__main__":
    raise SystemExit(stage245.main())
