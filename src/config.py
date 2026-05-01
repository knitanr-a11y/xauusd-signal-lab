from pathlib import Path


# Project root: xauusd-signal-lab/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Data folders
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
FEATURES_DATA_DIR = DATA_DIR / "features"
LABELS_DATA_DIR = DATA_DIR / "labels"
RESULTS_DATA_DIR = DATA_DIR / "results"

# Initial target symbols/timeframes.
# File names are expected to be lowercase, e.g. xauusd_m15.csv.
DEFAULT_SYMBOLS = ["xauusd", "btcusd"]
DEFAULT_TIMEFRAMES = ["m15", "h1"]

# MT5 CSV column schema exported by mt5/export_ohlc_multi.mq5
REQUIRED_OHLC_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "spread",
]

# Timeframe intervals in minutes for quality checks
TIMEFRAME_MINUTES = {
    "m1": 1,
    "m2": 2,
    "m3": 3,
    "m4": 4,
    "m5": 5,
    "m6": 6,
    "m10": 10,
    "m12": 12,
    "m15": 15,
    "m20": 20,
    "m30": 30,
    "h1": 60,
    "h2": 120,
    "h3": 180,
    "h4": 240,
    "h6": 360,
    "h8": 480,
    "h12": 720,
    "d1": 1440,
}
