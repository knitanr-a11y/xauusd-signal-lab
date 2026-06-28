from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from live_data import probe_latest_bars
from live_execution_live_wr import process_execution_cycle
from live_store import DeferredRun, append_jsonl, atomic_write_text, load_registry
from live_runtime import run_live_once
from live_runtime_base import acquire_lock, find_live_dir

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_BUSY = 4
EXIT_DEFERRED = 5


def repo_root() -> Path:
    resolved = Path(__file__).resolve()
    return resolved.parents[3] if len(resolved.parents) > 3 else Path.cwd()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one live research challenger and optional delivery/execution pass"
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


def _latest_m1_close(payload: dict[str, object], live_dir: Path) -> pd.Timestamp:
    latest = payload.get("latest_closed")
    if isinstance(latest, dict) and latest.get("M1"):
        return pd.Timestamp(latest["M1"])
    probe = probe_latest_bars(live_dir)
    return pd.Timestamp(probe["M1"]["close"])


def _attach_execution(
    payload: dict[str, object],
    *,
    live_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    now_text = str(
        payload.get("time")
        or pd.Timestamp.now().floor("s").strftime("%Y-%m-%d %H:%M:%S")
    )
    registry = load_registry(output_dir / "live_candidates.csv")
    execution = process_execution_cycle(
        live_dir=live_dir,
        output_dir=output_dir,
        registry=registry,
        latest_m1_close=_latest_m1_close(payload, live_dir),
        now_text=now_text,
        repo_root=repo_root(),
    )
    payload["execution"] = execution
    append_jsonl(
        output_dir / "live_execution_audit.jsonl",
        {
            "time": now_text,
            "runtime_status": payload.get("status"),
            **execution,
        },
    )
    atomic_write_text(
        output_dir / "latest_status.json",
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    return payload


def main() -> int:
    args = build_parser().parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    pipeline_lock = output_dir / "live_pipeline.lock"
    pipeline_locked = False
    try:
        acquire_lock(pipeline_lock)
        pipeline_locked = True
        live_dir = find_live_dir(args.live_dir)
        payload = run_live_once(live_dir, output_dir)
        payload = _attach_execution(
            payload,
            live_dir=live_dir,
            output_dir=output_dir,
        )
        execution = payload.get("execution", {})
        execution_status = (
            execution.get("status") if isinstance(execution, dict) else "UNKNOWN"
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "execution_status": execution_status,
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
    finally:
        if pipeline_locked:
            pipeline_lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
