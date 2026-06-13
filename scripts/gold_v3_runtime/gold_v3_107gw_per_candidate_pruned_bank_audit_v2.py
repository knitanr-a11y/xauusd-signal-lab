#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

# Stage107GW V2 wrapper
# Fixes SESSIONDOW_* parser for session names that include underscores, e.g.
# SESSIONDOW_london_12_16_0.

import pandas as pd
import gold_v3_107gw_per_candidate_pruned_bank_audit as base


def filter_rows_v2(df, prune_id):
    if df.empty:
        return df
    if prune_id == 'ALL':
        return df
    if prune_id.startswith('HOUR_'):
        h = int(prune_id.split('_', 1)[1])
        return df[df.entry_hour == h]
    if prune_id.startswith('DOW_'):
        d = int(prune_id.split('_', 1)[1])
        return df[df.entry_dow == d]
    if prune_id.startswith('SESSIONDOW_'):
        rest = prune_id[len('SESSIONDOW_'):]
        nm, d = rest.rsplit('_', 1)
        return df[df.entry_hour.isin(list(base.SESSIONS[nm])) & (df.entry_dow == int(d))]
    if prune_id.startswith('SESSION_'):
        nm = prune_id[len('SESSION_'):]
        return df[df.entry_hour.isin(list(base.SESSIONS[nm]))]
    return df.iloc[0:0]


base.filter_rows = filter_rows_v2

if __name__ == '__main__':
    raise SystemExit(base.main())
