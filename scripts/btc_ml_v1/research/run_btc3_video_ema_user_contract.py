from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

import btc3_video_ema_method_exploration as engine


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    args = engine.parse_args(argv)
    # User contract: EMA200 invalidation exists only before entry.
    # After entry, exits are the structural SL, TP1, break-even after TP1, and TP2.
    args.close_on_ema200_invalidation = False
    return args


def run(args: argparse.Namespace) -> dict[str, Any]:
    args.close_on_ema200_invalidation = False
    result = engine.run(args)
    result["pre_entry_ema200_invalidation_only"] = True
    result["post_entry_exit_contract"] = "STRUCTURAL_SL_TP_ONLY_NO_EMA200_EXIT"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=engine._json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
