# MOCHIPOYO Minimal Scanner Implementation Plan

最終更新: 2026-05-06

このドキュメントは、`docs/MOCHIPOYO_MINIMAL_SCANNER_SPEC.md` を実装へ移す直前のファイル構成・責務分割・実装順序メモである。

重要: まだ実装コードそのものではない。live loop を先に書かず、共通部品と比較スクリプトから作る。

---

## 1. 実装の基本方針

本番live通知は以下の方式にする。

```text
CSV末尾更新検知
  -> pair別minimal scan
  -> risk OKだけ通知候補化
  -> payload_key / ledger / stateで重複排除
  -> Discord通知
  -> audit log追記
```

以下は本番常時稼働に使わない。

```text
scripts/run_mochipoyo_live_notify_loop.py
scripts/run_mochipoyo_live_notify_loop_light.py
```

full strict scan は比較基準としてだけ使う。

---

## 2. 最初に作る共通部品

最初に作る実装ファイルは、live loopではなく以下の共通部品にする。

```text
scripts/mochipoyo_minimal_config.py
scripts/mochipoyo_safe_csv_reader.py
scripts/mochipoyo_payload_key.py
```

この3つは、以下の全てから共通利用する。

```text
- full strict scan vs minimal scan 比較スクリプト
- minimal scanner本体
- tail本数感度テスト
- pair別live loop
```

---

## 3. scripts/mochipoyo_minimal_config.py

### 3.1 目的

pair config / CSV key / timeframe minutes / allowed_slices を一元管理する。

比較用と本番用で別々にpair定義を書かない。

### 3.2 含めるもの

```text
TIMEFRAME_MINUTES
CSV_KEYS
DEFAULT_ALLOWED_SLICES
PAIR_CONFIGS
DEFAULT_TAIL_BARS
```

### 3.3 TIMEFRAME_MINUTES

```python
TIMEFRAME_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}
```

### 3.4 CSV_KEYS

```python
CSV_KEYS = {
    "gold_m5": "goldsharp_m5.csv",
    "gold_m15": "goldsharp_m15.csv",
    "gold_h1": "goldsharp_h1.csv",
    "gold_h4": "goldsharp_h4.csv",
    "gold_d1": "goldsharp_d1.csv",
    "btc_m5": "btcusdsharp_m5.csv",
    "btc_m15": "btcusdsharp_m15.csv",
    "btc_h1": "btcusdsharp_h1.csv",
    "btc_h4": "btcusdsharp_h4.csv",
}
```

### 3.5 DEFAULT_ALLOWED_SLICES

```python
DEFAULT_ALLOWED_SLICES = [
    {"pair_name": "GOLD_H4_M5_SCALP", "candidate_rank": "A", "direction": "SELL"},
    {"pair_name": "GOLD_H4_M5_SCALP", "candidate_rank": "B", "direction": "SELL"},
    {"pair_name": "GOLD_H4_M15_DAYTRADE", "candidate_rank": "B", "direction": "BUY"},
    {"pair_name": "GOLD_H4_M15_DAYTRADE", "candidate_rank": "B", "direction": "SELL"},
    {"pair_name": "GOLD_D1_H1_DAYTRADE", "candidate_rank": "A", "direction": "BUY"},
    {"pair_name": "GOLD_D1_H1_DAYTRADE", "candidate_rank": "B", "direction": "BUY"},
    {"pair_name": "BTC_H4_M15_DAYTRADE", "candidate_rank": "A", "direction": "BUY"},
    {"pair_name": "BTC_H4_M15_DAYTRADE", "candidate_rank": "A", "direction": "SELL"},
]
```

### 3.6 PAIR_CONFIGS

```python
PAIR_CONFIGS = {
    "GOLD_H4_M5_SCALP": {
        "pair_name": "GOLD_H4_M5_SCALP",
        "symbol": "GOLD",
        "base_timeframe": "M5",
        "trigger_timeframe": "M5",
        "base_csv_key": "gold_m5",
        "context": {"H4": "gold_h4"},
        "allowed_slices": [
            {"candidate_rank": "A", "direction": "SELL"},
            {"candidate_rank": "B", "direction": "SELL"},
        ],
        "tail_bars": {"M5": 6000, "H4": 1500},
        "price_digits": 2,
        "requires_spread": False,
    },
    "GOLD_H4_M15_DAYTRADE": {
        "pair_name": "GOLD_H4_M15_DAYTRADE",
        "symbol": "GOLD",
        "base_timeframe": "M15",
        "trigger_timeframe": "M15",
        "base_csv_key": "gold_m15",
        "context": {"H4": "gold_h4"},
        "allowed_slices": [
            {"candidate_rank": "B", "direction": "BUY"},
            {"candidate_rank": "B", "direction": "SELL"},
        ],
        "tail_bars": {"M15": 5000, "H4": 1500},
        "price_digits": 2,
        "requires_spread": False,
    },
    "GOLD_D1_H1_DAYTRADE": {
        "pair_name": "GOLD_D1_H1_DAYTRADE",
        "symbol": "GOLD",
        "base_timeframe": "H1",
        "trigger_timeframe": "H1",
        "base_csv_key": "gold_h1",
        "context": {"D1": "gold_d1"},
        "allowed_slices": [
            {"candidate_rank": "A", "direction": "BUY"},
            {"candidate_rank": "B", "direction": "BUY"},
        ],
        "tail_bars": {"H1": 1500, "D1": 800},
        "price_digits": 2,
        "requires_spread": False,
    },
    "BTC_H4_M15_DAYTRADE": {
        "pair_name": "BTC_H4_M15_DAYTRADE",
        "symbol": "BTC",
        "base_timeframe": "M15",
        "trigger_timeframe": "M15",
        "base_csv_key": "btc_m15",
        "context": {"H4": "btc_h4"},
        "allowed_slices": [
            {"candidate_rank": "A", "direction": "BUY"},
            {"candidate_rank": "A", "direction": "SELL"},
        ],
        "tail_bars": {"M15": 5000, "H4": 1500},
        "price_digits": 2,
        "requires_spread": True,
        "spread_source_csv_key": "btc_m15",
    },
}
```

### 3.7 必要な関数

```text
get_pair_config(pair_name)
get_required_pair_names(allowed_slices)
get_csv_filename(csv_key)
resolve_csv_path(csv_dir, csv_key, overrides=None)
get_timeframe_minutes(timeframe)
normalize_allowed_slice(row)
filter_allowed_slices_for_pair(allowed_slices, pair_name)
```

### 3.8 禁止事項

```text
- 各スクリプトにpair configを重複定義しない
- allowed_slices後段絞り込み前提で全pairをscanしない
- source_filter_nameをpayload_key構成に入れない
```

---

## 4. scripts/mochipoyo_safe_csv_reader.py

### 4.1 目的

MT5 EAが追記中のCSVを安全に読む共通reader。

### 4.2 最初に作る型

```text
CsvReadResult
```

含める情報:

```text
df
read_status
error_reason
path
timeframe
rows_raw
rows_valid
rows_dropped_parse
rows_dropped_incomplete
duplicate_time_count
duplicate_time_ohlc_conflict_count
latest_time
latest_close_time
```

Python実装では `dataclass` を使う想定。

### 4.3 必要な関数

```text
detect_csv_separator(path) -> str
parse_mt5_time(value) -> datetime | NaT
read_ohlc_csv_safe(path, timeframe, tail_bars, required_columns, requires_spread=False, as_of_time=None, csv_sep="auto", retry_count=3, retry_sleep_sec=0.2) -> CsvReadResult
validate_required_columns(columns, required_columns, requires_spread)
add_close_time(df, timeframe)
check_time_non_decreasing(df)
drop_duplicate_times_keep_last(df)
```

### 4.4 readerの初期仕様

比較スクリプトでは、初期実装は正確性優先でfull read可。

ただし、live minimal scannerではtail read必須とする。

段階:

```text
Phase 1: 比較スクリプト用。full read可。ただしreader APIはtail_barsを受ける。
Phase 2: live用。ファイル末尾から必要行数 + safety marginのみ読む実装へ切替。
```

### 4.5 CSV仕様

EA v1.32想定列:

```text
time, open, high, low, close, tick_volume, spread, real_volume
```

必須列:

```text
time
open
high
low
close
tick_volume
```

BTCなどspread必須の場合:

```text
spread
```

### 4.6 error_reason

```text
CSV_NOT_FOUND
CSV_EMPTY
CSV_HEADER_INVALID
CSV_SEPARATOR_UNKNOWN
CSV_REQUIRED_COLUMN_MISSING
CSV_PARSE_FAILED
TIME_NOT_ASCENDING
SPREAD_COLUMN_MISSING
NO_ROWS_AFTER_AS_OF_TIME
```

### 4.7 重要な挙動

```text
- 末尾不完全行は除外してよい
- 中間parse不能行は異常として扱う
- time非減少チェックに失敗したら、そのCSVを使うpairはskip
- 勝手にsortしない
- 同一timeは最後の行を採用
- 同一timeでOHLCが違う場合はwarning metadataに残す
- close_time = time + timeframe_minutes を必ず付与
```

---

## 5. scripts/mochipoyo_payload_key.py

### 5.1 目的

同一シグナルを一意に識別する安定payload_keyを生成する。

### 5.2 payload_key構成

```text
symbol|pair_name|candidate_rank|direction|signal_close_time|entry_time|entry_price_normalized
```

### 5.3 必要な関数

```text
normalize_symbol(symbol) -> str
normalize_pair_name(pair_name) -> str
normalize_candidate_rank(candidate_rank) -> str
normalize_direction(direction) -> str
format_signal_time(value) -> str
normalize_price(value, digits=2) -> str
build_payload_key(row_or_fields, price_digits=2) -> PayloadKeyResult
build_logical_key(row_or_fields, price_digits=2) -> tuple
```

### 5.4 PayloadKeyResult

```text
payload_key
payload_key_status
entry_price_normalized
error_reason
```

`dataclass` を使う想定。

### 5.5 payload_key_status

```text
OK
INVALID_MISSING_FIELD
INVALID_PRICE
INVALID_TIME
```

### 5.6 禁止事項

payload_keyには以下を入れない。

```text
source_filter_name
reason_text
risk_status
spread値
Discord文面
```

---

## 6. その次に作る比較用部品

共通3部品の後、いきなりlive loopではなく、比較スクリプト用の正規化部品を作る。

候補:

```text
scripts/mochipoyo_candidate_normalizer.py
scripts/compare_mochipoyo_full_strict_vs_minimal.py
```

### 6.1 scripts/mochipoyo_candidate_normalizer.py

目的:

```text
full strict scan出力とminimal scan出力を同じ列名・同じ型・同じpayload_key仕様に揃える。
```

必要な関数:

```text
normalize_full_strict_candidates(df) -> DataFrame
normalize_minimal_candidates(df) -> DataFrame
apply_payload_keys(df, price_digits_by_symbol_or_pair) -> DataFrame
split_risk_ok_ng(df) -> tuple[DataFrame, DataFrame]
```

必須列:

```text
symbol
pair_name
candidate_rank
direction
signal_close_time
entry_time
entry_price
entry_price_normalized
sl_price
tp_price
risk_status
payload_key
reason_text
base_time
base_close_time
context_time
context_close_time
pivot_time
pivot_confirmed_time
```

BTC追加列:

```text
current_spread_points
current_spread_price
mode_spread_points
mode_spread_price
effective_spread_price
spread_to_sl_ratio
effective_rr_after_spread
net_sl_after_spread_price
net_tp_after_spread_price
```

### 6.2 scripts/compare_mochipoyo_full_strict_vs_minimal.py

目的:

```text
同じCSV時点で、full strict scan と minimal scan の最新通知候補が一致するか確認する。
```

初期入力:

```text
--csv-dir
--out-dir
--allowed-slices-json optional
--as-of-time optional
--lookback-candidates 50
--tail-m5 6000
--tail-m15 5000
--tail-h1 1500
--tail-h4 1500
--tail-d1 800
```

出力:

```text
comparison_summary.csv
comparison_full_filtered.csv
comparison_minimal.csv
comparison_matched.csv
comparison_full_only.csv
comparison_minimal_only.csv
comparison_value_diff.csv
comparison_payload_key_diff.csv
comparison_errors.csv
```

合格条件:

```text
full_only_rows = 0
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
```

---

## 7. minimal scanner本体の予定ファイル

比較用の土台ができた後に作る。

```text
scripts/mochipoyo_minimal_scanner.py
```

### 7.1 役割

```text
- 指定pairだけscanする
- 必要CSVだけ読む
- confirmed-time joinを守る
- allowed rank/directionだけ判定する
- risk/spread enrich済みの候補を返す
```

### 7.2 やらないこと

```text
- 全pair scan
- Discord送信
- ledger更新
- live loop sleep管理
- 初回state初期化
```

### 7.3 入力

```text
pair_config
csv_dir / csv_overrides
allowed_slices
as_of_time optional
tail_bars override optional
scan_recent_bars optional
risk_enrich_config
spread_config
```

### 7.4 出力

```text
scan_status
pair_name
symbol
base_timeframe
latest_base_close_time
raw_candidates_df
normalized_candidates_df
risk_ok_candidates_df
risk_ng_candidates_df
errors
reader_metadata
```

---

## 8. live loop予定ファイル

最後に作る。

```text
scripts/run_mochipoyo_live_notify_loop_minimal.py
```

### 8.1 役割

```text
- state読み込み
- 初回live起動時は通知せずstate初期化
- 毎分、各pairのbase CSV末尾timeだけ確認
- timeが進んだpairだけminimal scannerを呼ぶ
- risk_ok_candidatesだけ送信候補にする
- payload_keyでledger重複確認
- Discord送信
- ledger/state/audit log更新
```

### 8.2 初回live起動

```text
通知しない
last_seen_base_close_time_by_pairだけ初期化する
```

### 8.3 禁止事項

```text
- full strict scanをlive loop内で呼ばない
- run_mochipoyo_live_dryrun_strict.pyをlive loop内で呼ばない
- 更新なし時に重い処理をしない
- context更新だけでpair scanしない
```

---

## 9. state / ledger / audit予定ファイル

live loop実装時に作る。

候補:

```text
scripts/mochipoyo_live_state.py
scripts/mochipoyo_live_ledger.py
scripts/mochipoyo_live_audit.py
```

### 9.1 mochipoyo_live_state.py

担当:

```text
- state JSON読み込み
- state JSON保存
- last_seen_base_close_time_by_pair更新
- last_notified_time_by_symbol_pair_direction更新
```

### 9.2 mochipoyo_live_ledger.py

担当:

```text
- send ledger CSV読み込み
- payload_key重複確認
- 送信済み行追記
```

### 9.3 mochipoyo_live_audit.py

担当:

```text
- loop summary保存
- candidate audit保存
- error summary保存
```

---

## 10. 実装順序の最終固定

```text
1. scripts/mochipoyo_minimal_config.py
2. scripts/mochipoyo_safe_csv_reader.py
3. scripts/mochipoyo_payload_key.py
4. scripts/mochipoyo_candidate_normalizer.py
5. scripts/compare_mochipoyo_full_strict_vs_minimal.py
6. compare script の通常比較を通す
7. compare script に --tail-sensitivity を追加
8. scripts/mochipoyo_minimal_scanner.py
9. full strict scan vs minimal scan PASS確認
10. tail本数感度テスト PASS確認
11. scripts/mochipoyo_live_state.py
12. scripts/mochipoyo_live_ledger.py
13. scripts/mochipoyo_live_audit.py
14. scripts/run_mochipoyo_live_notify_loop_minimal.py
15. pair別更新トリガーテスト
16. 重複通知テスト
17. Discord送信再確認
```

---

## 11. まだ作らないもの

以下はまだ作らない。

```text
- 自動売買発注ロジック
- AI評価連携の再接続
- 既存full loopの改造
- 既存run_mochipoyo_live_notify_loop.pyの置き換え
- 既存run_mochipoyo_live_notify_loop_light.pyの本番利用
```

---

## 12. 次に実装するなら

最初の実装対象は以下。

```text
scripts/mochipoyo_minimal_config.py
scripts/mochipoyo_safe_csv_reader.py
scripts/mochipoyo_payload_key.py
```

この3つだけを先に作り、単体で確認する。

その後に比較スクリプトへ進む。
