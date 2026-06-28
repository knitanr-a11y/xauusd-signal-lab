from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from live_store import DeferredRun, append_jsonl, atomic_write_text
from live_runtime import run_live_once
from live_runtime_base import find_live_dir

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_BUSY = 4
EXIT_DEFERRED = 5


def repo_root() -> Path:
    resolved = Path(__file__).resolve()
    return resolved.parents[3] if len(resolved.parents) > 3 else Path.cwd()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one audit-only live research challenger pass"
    )
    parser.add_argument("--live-dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root() / "outputs/gold_ml_v1/live_research_challenger",
    )
    return parser


def failure_payload(status: str, exc: Exception) -> dict[str, str]:
    return {
        "status": status,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "time": pd.Timestamp.now().floor("s").strftime("%Y-%m-%d %H:%M:%S"),
    }


def main() -> int:
    args = build_parser().parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    try:
        live_dir = find_live_dir(args.live_dir)
        payload = run_live_once(live_dir, output_dir)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "new_candidate_count": payload["new_candidate_count"],
                    "output_dir": str(output_dir),
                },
                ensure_ascii=False,
            )
        )
        return EXIT_OK
    except DeferredRun as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = failure_payload("DEFERRED", exc)
        atomic_write_text(
            output_dir / "latest_status.json",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        append_jsonl(output_dir / "live_audit.jsonl", payload)
        print(str(exc), file=sys.stderr)
        return EXIT_DEFERRED
    except RuntimeError as exc:
        message = str(exc)
        print(message, file=sys.stderr)
        return EXIT_BUSY if message.startswith("BUSY:") else EXIT_INPUT
    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        pd.errors.ParserError,
    ) as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = failure_payload("FAIL", exc)
        atomic_write_text(
            output_dir / "latest_status.json",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        append_jsonl(output_dir / "live_audit.jsonl", payload)
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
