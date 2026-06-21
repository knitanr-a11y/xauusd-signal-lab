from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ENV = os.environ.copy()
ENV.update({
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
})


def run(name: str, *args: object) -> None:
    cmd = [sys.executable, str(BASE / name), *map(str, args)]
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=ENV)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step",
        choices=[
            "features", "prefix", "labels", "router", "train", "grid",
            "score-parity", "diagnostics", "finalize", "all",
        ],
        default="all",
    )
    parser.add_argument(
        "--family",
        choices=["LR_GLOBAL", "HGB_GLOBAL", "HGB_ROUTED"],
    )
    args = parser.parse_args()

    if args.step in ("features", "all"):
        run("stage275_build_features.py")

    if args.step in ("prefix", "all"):
        for part in range(8):
            run("stage275_prefix_part.py", part, 8)
        merge_code = (
            "import glob,pandas as pd;"
            "fs=sorted(glob.glob('/mnt/data/stage275_outcome_first_live_map/prefix_part_*.csv'));"
            "d=pd.concat([pd.read_csv(f) for f in fs],ignore_index=True).sort_values('decision_idx');"
            "d.to_csv('/mnt/data/stage275_outcome_first_live_map/stage275_prefix_feature_parity.csv',index=False);"
            "assert len(d)==256 and (d.status=='PASS').all()"
        )
        subprocess.run([sys.executable, "-c", merge_code], check=True, env=ENV)

    if args.step in ("labels", "all"):
        run("stage275_prepare_labels.py")

    if args.step in ("router", "all"):
        run("stage275_prepare_router_outcomes.py")

    if args.step == "train":
        if not args.family:
            parser.error("--family required for train")
        run("stage275_train_family.py", args.family)
    elif args.step == "all":
        for family in ("LR_GLOBAL", "HGB_GLOBAL", "HGB_ROUTED"):
            run("stage275_train_family.py", family)

    if args.step == "grid":
        if not args.family:
            parser.error("--family required for grid")
        run("stage275_eval_family_fast.py", args.family)
    elif args.step == "all":
        for family in ("LR_GLOBAL", "HGB_GLOBAL", "HGB_ROUTED"):
            run("stage275_eval_family_fast.py", family)
        run("stage275_finalize.py")

    if args.step in ("score-parity", "all"):
        run("stage275_score_chunk_parity.py")

    if args.step in ("diagnostics", "all"):
        run("stage275_near_diagnostics.py")

    if args.step == "all":
        run("stage275_finalize.py")

    if args.step in ("finalize", "all"):
        if args.step == "finalize":
            run("stage275_finalize.py")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                str(BASE / "test_stage275_outcome_first_live_map.py"),
            ],
            check=True,
            env=ENV,
        )


if __name__ == "__main__":
    main()
