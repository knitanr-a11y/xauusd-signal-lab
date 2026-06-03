#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Strict JSON sanitizer for GOLD V2 runtime candidate outputs.

The exporter primarily writes CSV and JSONL, but pandas conversions can turn
missing optional numeric fields into NaN when building latest_by_dataset JSON.
Python's json module can write NaN by default, but strict JSON consumers may
reject it.

This post-processor rewrites JSON/JSONL outputs so that:
  - NaN becomes null
  - +inf becomes "inf"
  - -inf becomes "-inf"
  - json.dumps(..., allow_nan=False) is used

It does not call AI APIs, Discord, MT5, or live hooks.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sanitize GOLD V2 runtime candidate JSON outputs for strict JSON parsers")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_runtime_signal_candidates_audit_only"


def sanitize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return value
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize(v) for v in value]
    return value


def load_json_lenient(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_strict(path: Path, data: Any) -> None:
    path.write_text(json.dumps(sanitize(data), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def rewrite_json_file(path: Path) -> bool:
    if not path.exists():
        return False
    data = load_json_lenient(path)
    write_json_strict(path, data)
    # Re-parse with strict constant rejection. This should not encounter NaN/Infinity.
    json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    return True


def rewrite_jsonl_file(path: Path) -> bool:
    if not path.exists():
        return False
    out_lines = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        out_lines.append(json.dumps(sanitize(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"line {line_no}: {x}")))
    return True


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    if not output_dir.exists():
        print(f"[ERROR] output_dir not found: {output_dir}")
        return 2

    rewritten = []
    for name in [
        "gold_v2_runtime_signal_candidates_latest.json",
        "gold_v2_runtime_signal_candidates_summary.json",
    ]:
        path = output_dir / name
        if rewrite_json_file(path):
            rewritten.append(str(path))

    jsonl_path = output_dir / "gold_v2_runtime_signal_candidates.jsonl"
    if rewrite_jsonl_file(jsonl_path):
        rewritten.append(str(jsonl_path))

    print("[OK] strict JSON sanitize completed")
    for path in rewritten:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
