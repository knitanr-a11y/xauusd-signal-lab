from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_csv_gzip(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                frame.to_csv(
                    text,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Join active event proposals to resolved labels")
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--join-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.join_contract.read_text(encoding="utf-8"))
    if sha256_file(args.proposals) != contract["proposal_registry_sha256"]:
        raise ValueError("Active proposal SHA256 mismatch")
    if sha256_file(args.labels) != contract["label_registry_sha256"]:
        raise ValueError("Label registry SHA256 mismatch")

    proposals = pd.read_csv(args.proposals, parse_dates=["decision_time"])
    labels = pd.read_csv(
        args.labels,
        parse_dates=["decision_time", "entry_time", "exit_bar_open_time", "exit_time"],
    )
    if proposals.duplicated(["decision_time", "candidate_id"]).any():
        raise ValueError("Duplicate active candidate event")
    if proposals["decision_time"].duplicated().any():
        raise ValueError("Active event core must be non-overlapping by decision_time")
    if labels.duplicated(["decision_time", "direction"]).any():
        raise ValueError("Duplicate label key")

    events = proposals.merge(
        labels,
        on=["decision_time", "direction"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not events["_merge"].eq("both").all():
        missing = events.loc[events["_merge"] != "both", ["decision_time", "candidate_id", "direction"]]
        raise ValueError(f"Unresolved active event labels: {missing.to_dict(orient='records')}")
    events = events.drop(columns=["_merge"]).sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)
    if len(events) != int(contract["expected"]["resolved_event_rows"]):
        raise ValueError("Resolved active event row count mismatch")
    if events.isna().any().any():
        raise ValueError("Null active event value")
    numeric = events.select_dtypes(include=[np.number]).to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("Nonfinite active event value")
    if not (events["entry_time"] == events["decision_time"]).all():
        raise ValueError("Entry time differs from decision time")
    if not (events["exit_time"] >= events["entry_time"]).all():
        raise ValueError("Exit before entry")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "gml1_active_event_registry_v1.csv.gz"
    summary_path = args.output_dir / "gml1_active_event_registry_summary_v1.json"
    deterministic_csv_gzip(events, output_path)
    summary = {
        "system_id": "GML1-EVENT-CORE",
        "version": "v1",
        "status": "RESOLVED_ACTIVE_EVENT_REGISTRY_BUILT",
        "rows": int(len(events)),
        "unique_decisions": int(events["decision_time"].nunique()),
        "candidate_count": int(events["candidate_id"].nunique()),
        "direction_counts": {
            str(key): int(value)
            for key, value in events["direction"].value_counts().sort_index().items()
        },
        "event_registry_sha256": sha256_file(output_path),
        "deployment_allowed": False,
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
