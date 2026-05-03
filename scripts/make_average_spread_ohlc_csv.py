from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if "spread" not in df.columns:
        raise ValueError(f"CSV has no spread column: {path}")
    return df.copy()


def compute_average_spread_points(
    spread: pd.Series,
    *,
    min_spread_points: float | None,
    max_spread_points: float | None,
    lower_quantile: float | None,
    upper_quantile: float | None,
) -> tuple[float, pd.Series, dict[str, float | int | None]]:
    s = pd.to_numeric(spread, errors="coerce").dropna()
    if s.empty:
        raise ValueError("No valid spread values")

    mask = pd.Series(True, index=s.index)
    lower_value = None
    upper_value = None

    if lower_quantile is not None:
        lower_value = float(s.quantile(lower_quantile))
        mask &= s >= lower_value
    if upper_quantile is not None:
        upper_value = float(s.quantile(upper_quantile))
        mask &= s <= upper_value
    if min_spread_points is not None:
        mask &= s >= min_spread_points
    if max_spread_points is not None:
        mask &= s <= max_spread_points

    filtered = s[mask]
    if filtered.empty:
        raise ValueError("No spread values left after filtering")

    avg = float(filtered.mean())
    stats: dict[str, float | int | None] = {
        "raw_count": int(len(s)),
        "filtered_count": int(len(filtered)),
        "excluded_count": int(len(s) - len(filtered)),
        "raw_min": float(s.min()),
        "raw_median": float(s.median()),
        "raw_mean": float(s.mean()),
        "raw_max": float(s.max()),
        "filtered_min": float(filtered.min()),
        "filtered_median": float(filtered.median()),
        "filtered_mean": avg,
        "filtered_max": float(filtered.max()),
        "lower_quantile": lower_quantile,
        "upper_quantile": upper_quantile,
        "lower_quantile_value": lower_value,
        "upper_quantile_value": upper_value,
        "min_spread_points": min_spread_points,
        "max_spread_points": max_spread_points,
    }
    return avg, filtered, stats


def write_notes(path: Path, *, source_csv: Path, out_csv: Path, avg_spread_points: float, point_size: float, stats: dict[str, float | int | None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    avg_spread_price = avg_spread_points * point_size
    lines = [
        "# Average Spread OHLC CSV Notes",
        "",
        f"source_csv: `{source_csv}`",
        f"out_csv: `{out_csv}`",
        "",
        "## Average spread used",
        "",
        "```text",
        f"average_spread_points = {avg_spread_points}",
        f"point_size = {point_size}",
        f"average_spread_price = {avg_spread_price}",
        "```",
        "",
        "## Filter stats",
        "",
        "```text",
    ]
    for key, value in stats.items():
        lines.append(f"{key}: {value}")
    lines.extend([
        "```",
        "",
        "The output CSV keeps all OHLC/volume rows unchanged and replaces only the spread column with the filtered average spread points.",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace OHLC CSV spread with filtered average spread points.")
    parser.add_argument("--in-csv", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--notes", type=Path, default=None)
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--min-spread-points", type=float, default=None)
    parser.add_argument("--max-spread-points", type=float, default=None)
    parser.add_argument("--lower-quantile", type=float, default=None)
    parser.add_argument("--upper-quantile", type=float, default=0.95)
    parser.add_argument("--round-spread-points", type=int, default=6)
    args = parser.parse_args()

    in_csv = resolve_path(args.in_csv)
    out_csv = resolve_path(args.out_csv)
    notes = resolve_path(args.notes) if args.notes else out_csv.with_suffix(".spread_notes.md")

    if args.point_size <= 0:
        raise ValueError("--point-size must be positive")
    for q_name, q_value in [("lower_quantile", args.lower_quantile), ("upper_quantile", args.upper_quantile)]:
        if q_value is not None and not (0 <= q_value <= 1):
            raise ValueError(f"--{q_name.replace('_', '-')} must be between 0 and 1")

    df = read_csv(in_csv)
    avg_spread_points, _filtered, stats = compute_average_spread_points(
        df["spread"],
        min_spread_points=args.min_spread_points,
        max_spread_points=args.max_spread_points,
        lower_quantile=args.lower_quantile,
        upper_quantile=args.upper_quantile,
    )
    avg_spread_points = round(avg_spread_points, args.round_spread_points)

    out = df.copy()
    out["spread"] = avg_spread_points
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    write_notes(notes, source_csv=in_csv, out_csv=out_csv, avg_spread_points=avg_spread_points, point_size=args.point_size, stats=stats)

    print("Source CSV:", in_csv)
    print("Output CSV:", out_csv)
    print("Notes:", notes)
    print("Rows:", len(out))
    print("Average spread points:", avg_spread_points)
    print("Average spread price:", avg_spread_points * args.point_size)
    print("Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
