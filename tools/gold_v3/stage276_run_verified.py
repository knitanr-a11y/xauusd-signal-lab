from __future__ import annotations

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


def run(path: Path) -> None:
    command = [sys.executable, str(path)]
    print("RUN", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=ENV)


def main() -> None:
    run(BASE / "stage276_materialize_source_bundle.py")
    run(BASE / "stage276_run_all_materialized.py")


if __name__ == "__main__":
    main()
