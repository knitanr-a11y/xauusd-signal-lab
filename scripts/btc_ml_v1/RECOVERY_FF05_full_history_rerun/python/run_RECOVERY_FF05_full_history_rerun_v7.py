from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V6_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun_v6.py"

v6_spec = importlib.util.spec_from_file_location("ff05_recovery_direct_v6", V6_PATH)
if v6_spec is None or v6_spec.loader is None:
    raise RuntimeError(f"cannot load direct-path rerun module: {V6_PATH}")
v6_module = importlib.util.module_from_spec(v6_spec)
sys.modules[v6_spec.name] = v6_module
try:
    v6_spec.loader.exec_module(v6_module)
except Exception:
    sys.modules.pop(v6_spec.name, None)
    raise

v5_module = v6_module.module


def load_original_module_v7():
    """
    Load the frozen FF05 loader as a real registered Python module.

    The original direct-path attempt called exec_module() before placing the
    module in sys.modules. The decompressed FF05 source uses postponed type
    annotations and dataclasses, whose decorator resolves cls.__module__ via
    sys.modules. Without registration Python raises:
      AttributeError: 'NoneType' object has no attribute '__dict__'
    """
    loader_path = v5_module.ORIGINAL_LOADER
    if not loader_path.is_file():
        raise FileNotFoundError(f"FF05 loader missing: {loader_path}")

    module_name = "ff05_original_direct_v7"
    spec = importlib.util.spec_from_file_location(module_name, loader_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load original FF05 module: {loader_path}")

    original_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = original_module
    try:
        spec.loader.exec_module(original_module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    if not callable(getattr(original_module, "main", None)):
        raise RuntimeError("original FF05 module has no callable main")
    return original_module


v5_module.load_original_module = load_original_module_v7

if __name__ == "__main__":
    raise SystemExit(v5_module.main())
