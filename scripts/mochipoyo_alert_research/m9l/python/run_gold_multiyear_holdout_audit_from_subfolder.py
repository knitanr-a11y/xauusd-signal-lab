from __future__ import annotations

import run_gold_multiyear_holdout_audit as base

SUBFOLDER = "gold_v3_2023_2026"


def main() -> int:
    base.EXPECTED = {
        timeframe: (f"{SUBFOLDER}/{filename}", expected_hash)
        for timeframe, (filename, expected_hash) in base.EXPECTED.items()
    }
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
