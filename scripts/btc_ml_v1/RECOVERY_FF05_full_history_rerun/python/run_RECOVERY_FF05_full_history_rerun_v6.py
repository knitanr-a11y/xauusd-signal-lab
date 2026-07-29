from __future__ import annotations

import fnmatch
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
V5_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun_v5.py"

spec = importlib.util.spec_from_file_location("ff05_recovery_direct_v5", V5_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load direct-path rerun module: {V5_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def safe_pattern_targets(pattern: str, direct_paths):
    """Intercept BTC CSV searches without hijacking generic non-CSV scans."""
    normalized = str(pattern).replace("\\", "/").lower()
    basename = Path(normalized).name
    looks_like_csv_search = (
        ".csv" in basename
        or "csv" in normalized
        or any(name.lower() in normalized for name in module.TARGET_FILENAMES.values())
    )
    if not looks_like_csv_search:
        return []

    matched = []
    for timeframe, path in direct_paths.items():
        filename = module.TARGET_FILENAMES[timeframe].lower()
        if (
            fnmatch.fnmatch(filename, basename)
            or filename in normalized
            or (timeframe.lower() in normalized and "btc" in normalized)
        ):
            matched.append(path)
    return sorted(set(matched), key=lambda item: str(item).lower())


module._pattern_targets = safe_pattern_targets

if __name__ == "__main__":
    raise SystemExit(module.main())
