from __future__ import annotations

import os

os.environ["GML1_MT5_SYMBOL"] = "GOLD#"
os.environ["GML1_MT5_VOLUME"] = "0.01"
os.environ["GML1_MT5_VOLUME_A_CORE"] = "0.01"
os.environ["GML1_MT5_VOLUME_B_STATE"] = "0.01"
os.environ["GML1_MT5_VOLUME_P18"] = "0.01"
os.environ["GML1_MT5_VOLUME_W024A"] = "0.01"

import run_live_connected_once as connected

if __name__ == "__main__":
    raise SystemExit(connected.base.main())
