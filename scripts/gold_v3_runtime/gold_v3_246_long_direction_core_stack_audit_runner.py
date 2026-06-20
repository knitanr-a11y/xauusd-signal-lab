#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import gold_v3_245_refined_setup_one_trade_stack_audit as stage245

# Stage246 uses the shared Stage245 CSV reader for M5 as well.
stage245.TF_MIN["m5"] = 5

import gold_v3_246_long_direction_core_stack_audit as stage246


if __name__ == "__main__":
    raise SystemExit(stage246.main())
