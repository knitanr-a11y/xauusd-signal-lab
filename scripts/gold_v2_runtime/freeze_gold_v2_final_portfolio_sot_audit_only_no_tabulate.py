#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run 12Q final portfolio SOT freeze without pandas optional tabulate.

The original 12Q script uses pandas.DataFrame.to_markdown for the Markdown
report. Some user environments do not have the optional `tabulate` package.
This wrapper patches DataFrame.to_markdown with a small dependency-free
Markdown table writer, then delegates to the original 12Q main().

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _format_cell(value: Any) -> str:
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.6g}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _to_markdown_no_tabulate(self: pd.DataFrame, index: bool = True, **_: Any) -> str:
    df = self.copy()
    if index:
        df = df.reset_index()
    headers = [str(c) for c in df.columns]
    if not headers:
        return "_No columns._"
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    if len(df) == 0:
        return "\n".join(lines)
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(_format_cell(row[c]) for c in df.columns) + " |")
    return "\n".join(lines)


pd.DataFrame.to_markdown = _to_markdown_no_tabulate  # type: ignore[assignment]

import freeze_gold_v2_final_portfolio_sot_audit_only as base  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(base.main())
