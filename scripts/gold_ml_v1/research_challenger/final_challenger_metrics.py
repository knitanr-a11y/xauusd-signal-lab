from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

COLS = ["candidate_id", "decision_time", "exit_time", "r", "direction", "comp", "w", "size", "weighted_r"]
IDS = {
    "A_CORE": "GML1-WATCH-022-C",
    "B_STATE": "GML1-H1D1-STATEFUL-REENTRY24-C",
    "P16": "GML1-PROV-016-APPROX",
    "P18": "GML1-PROV-018-APPROX",
    "P19": "GML1-PROV-019-APPROX",
    "W024A": "GML1-WATCH-024-A",
}
WEIGHTS = {"A_CORE": 1.0, "B_STATE": 1.0, "P16": 0.5, "P18": 0.25, "P19": 1.0, "W024A": 1.0}
SIZES = {
    "A_CORE": 1.4769230769230768,
    "B_STATE": 1.4769230769230768,
    "P16": 0.7384615384615384,
    "P18": 0.3692307692307692,
    "P19": 1.4769230769230768,
    "W024A": 1.0,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def near(a: Any, b: Any, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))


def sort_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(
        ["decision_time", "exit_time", "comp", "candidate_id", "direction"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)


def load_csv(path: Path, normalize: bool = False) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [column for column in COLS if column not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    df = df[COLS].copy()
    df["decision_time"] = pd.to_datetime(df["decision_time"], errors="raise")
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="raise")
    for column in ["r", "w", "size", "weighted_r"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if normalize:
        mask = df["comp"].eq("A_CORE")
        df.loc[mask & df["candidate_id"].isna(), "candidate_id"] = IDS["A_CORE"]
        df.loc[mask & df["w"].isna(), "w"] = WEIGHTS["A_CORE"]
    return sort_frame(df)


def metric(df: pd.DataFrame) -> dict[str, Any]:
    values = df["weighted_r"].astype(float)
    gp = float(values[values > 0].sum())
    gl = float(-values[values < 0].sum())
    equity = values.cumsum().to_numpy(float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    dd = peaks[1:] - equity if len(equity) else np.array([], dtype=float)
    months = df.assign(month=df["decision_time"].dt.to_period("M")).groupby("month")["weighted_r"].sum()
    wins = values[values > 0].sort_values(ascending=False)
    top5pct = int(math.ceil(0.05 * len(df)))
    return {
        "trades": int(len(df)),
        "win_rate": float((df["r"] > 0).mean()) if len(df) else None,
        "pf": gp / gl if gl else None,
        "R": float(values.sum()),
        "DD": float(dd.max()) if len(dd) else 0.0,
        "top5_removed_R": float(values.sum() - wins.head(5).sum()),
        "top5pct_removed_R": float(values.sum() - wins.head(top5pct).sum()),
        "positive_months": int((months > 0).sum()),
        "negative_months": int((months < 0).sum()),
    }


def component_metric(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for comp, group in df.groupby("comp", sort=True):
        values = group["weighted_r"].astype(float)
        gp = float(values[values > 0].sum())
        gl = float(-values[values < 0].sum())
        result[str(comp)] = {
            "trades": int(len(group)),
            "win_rate": float((group["r"] > 0).mean()),
            "pf": gp / gl if gl else None,
            "R": float(values.sum()),
            "mean_size": float(group["size"].mean()),
        }
    return result


def same_metrics(actual: dict[str, Any], expected: dict[str, Any], keys: list[str]) -> tuple[bool, dict[str, Any]]:
    diff = {
        key: {"actual": actual.get(key), "expected": expected.get(key)}
        for key in keys
        if not near(actual.get(key), expected.get(key))
    }
    return not diff, diff


def record_set(df: pd.DataFrame) -> set[tuple[Any, ...]]:
    records: set[tuple[Any, ...]] = set()
    for row in df[COLS].itertuples(index=False, name=None):
        normalized: list[Any] = []
        for value in row:
            if isinstance(value, pd.Timestamp):
                normalized.append(value.isoformat(sep=" "))
            elif pd.isna(value):
                normalized.append(None)
            elif isinstance(value, (float, np.floating)):
                normalized.append(round(float(value), 12))
            else:
                normalized.append(value)
        records.add(tuple(normalized))
    return records


def basic_check(df: pd.DataFrame, stage: str, allow_blank_core: bool, allow_watch022b: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    if (df["exit_time"] < df["decision_time"]).any():
        errors.append("exit precedes decision")
    if df[["r", "size", "weighted_r"]].isna().any().any():
        errors.append("missing numeric values")
    blank = df["candidate_id"].isna() | df["w"].isna()
    allowed = df["comp"].eq("A_CORE") if allow_blank_core else pd.Series(False, index=df.index)
    if (blank & ~allowed).any():
        errors.append("unexpected identity omission")
    if not np.allclose(df["weighted_r"], df["r"] * df["size"], rtol=1e-10, atol=1e-10):
        errors.append("weighted_r mismatch")
    for comp, expected_id in IDS.items():
        part = df[df["comp"].eq(comp)]
        if part.empty:
            continue
        accepted = {expected_id}
        if comp == "A_CORE" and allow_watch022b:
            accepted.add("GML1-WATCH-022-B")
        ids = set(part["candidate_id"].dropna().astype(str))
        if not ids.issubset(accepted):
            errors.append(f"{comp}: unexpected IDs {sorted(ids)}")
        if not np.allclose(part["size"], SIZES[comp], rtol=1e-10, atol=1e-10):
            errors.append(f"{comp}: size mismatch")
        observed_w = part["w"].dropna()
        if len(observed_w) and not np.allclose(observed_w, WEIGHTS[comp], rtol=1e-10, atol=1e-10):
            errors.append(f"{comp}: weight mismatch")
    return {"name": stage, "passed": not errors, "details": {"rows": int(len(df)), "errors": errors}}
