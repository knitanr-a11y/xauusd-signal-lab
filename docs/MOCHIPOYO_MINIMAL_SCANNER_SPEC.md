# MOCHIPOYO Minimal Scanner Specification

最終更新: 2026-05-06

このドキュメントは、GOLD/BTC もちぽよ式 live notification minimal scanner の実装前仕様である。

重要: このドキュメントはコード実装ではない。既存の full scan 系スクリプトを本番常時稼働に使わず、pair別の軽量リアルタイム判定へ移行するための仕様を固定する。

---

## 1. 固定方針

本番ライブ通知は、初回に full/heavy scan の結果を作ってそれを毎分読む方式にはしない。

採用する方式:

```text
CSV末尾更新検知
  -> pair別に必要最小限のtailだけ読む
  -> 更新があったpairだけminimal scan
  -> risk OKだけ通知候補化
  -> payload_key / ledger / stateで重複排除
  -> Discord通知
  -> audit logへ追記
```

full strict scan は、本番ライブループには入れない。
用途は minimal scan との一致検証専用とする。

---

## 2. live初回起動仕様

live本番初回起動では通知しない。

```text
起動時:
  各pairのbase CSV最新確定足timeを読む
  base_close_timeを計算する
  last_seen_base_close_time_by_pair に保存する
  通知はしない
```

理由:

```text
PC起動時に、すでに過去になった候補を通知してしまう可能性があるため。
```

dry-run / comparison では初回も判定してよい。

---

## 3. allowed_slices の扱い

現時点の allowed_slices は、旧候補の本採用復活ではなく、minimal scanner 検証用の通知対象sliceとして扱う。

```text
GOLD_H4_M5_SCALP|B|SELL
GOLD_H4_M15_DAYTRADE|B|SELL
GOLD_D1_H1_DAYTRADE|B|BUY
GOLD_D1_H1_DAYTRADE|A|BUY
GOLD_H4_M5_SCALP|A|SELL
GOLD_H4_M15_DAYTRADE|B|BUY

BTC_H4_M15_DAYTRADE|A|BUY
BTC_H4_M15_DAYTRADE|A|SELL
```

禁止:

```text
全pair scan
  -> 全candidate生成
  -> allowed_slicesで後段絞り込み
```

採用:

```text
allowed_slices
  -> 必要pairを先に決定
  -> 必要pairだけscan
  -> 必要rank/directionだけ判定
```

---

## 4. pair別トリガー

| pair | symbol | base timeframe | trigger |
|---|---|---:|---|
| GOLD_H4_M5_SCALP | GOLD | M5 | GOLD M5 CSVの最新確定足time更新 |
| GOLD_H4_M15_DAYTRADE | GOLD | M15 | GOLD M15 CSVの最新確定足time更新 |
| GOLD_D1_H1_DAYTRADE | GOLD | H1 | GOLD H1 CSVの最新確定足time更新 |
| BTC_H4_M15_DAYTRADE | BTC | M15 | BTC M15 CSVの最新確定足time更新 |

context timeframe の更新ではなく、base timeframe の更新で判定する。

例: GOLD_D1_H1_DAYTRADE は D1 をcontextに使うが、判定タイミングはH1更新である。

---

## 5. pair config 仕様

pair config は、比較スクリプト、minimal scanner、本番live loopで共通利用する。
比較用と本番用で別々にpair定義を書かない。

### 5.1 GOLD_H4_M5_SCALP

```yaml
pair_name: GOLD_H4_M5_SCALP
symbol: GOLD
base_timeframe: M5
trigger_timeframe: M5
base_csv_key: gold_m5
context:
  H4: gold_h4
allowed_slices:
  - candidate_rank: A
    direction: SELL
  - candidate_rank: B
    direction: SELL
tail_bars:
  M5: 6000
  H4: 1500
price_digits: 2
requires_spread: false
```

### 5.2 GOLD_H4_M15_DAYTRADE

```yaml
pair_name: GOLD_H4_M15_DAYTRADE
symbol: GOLD
base_timeframe: M15
trigger_timeframe: M15
base_csv_key: gold_m15
context:
  H4: gold_h4
allowed_slices:
  - candidate_rank: B
    direction: BUY
  - candidate_rank: B
    direction: SELL
tail_bars:
  M15: 5000
  H4: 1500
price_digits: 2
requires_spread: false
```

### 5.3 GOLD_D1_H1_DAYTRADE

```yaml
pair_name: GOLD_D1_H1_DAYTRADE
symbol: GOLD
base_timeframe: H1
trigger_timeframe: H1
base_csv_key: gold_h1
context:
  D1: gold_d1
allowed_slices:
  - candidate_rank: A
    direction: BUY
  - candidate_rank: B
    direction: BUY
tail_bars:
  H1: 1500
  D1: 800
price_digits: 2
requires_spread: false
```

### 5.4 BTC_H4_M15_DAYTRADE

```yaml
pair_name: BTC_H4_M15_DAYTRADE
symbol: BTC
base_timeframe: M15
trigger_timeframe: M15
base_csv_key: btc_m15
context:
  H4: btc_h4
allowed_slices:
  - candidate_rank: A
    direction: BUY
  - candidate_rank: A
    direction: SELL
tail_bars:
  M15: 5000
  H4: 1500
price_digits: 2
requires_spread: true
spread_source_csv_key: btc_m15
```

---

## 6. CSV key 定義

実ファイルパスを各pairに直接持たせず、CSV keyで参照する。

```yaml
csv_keys:
  gold_m5: goldsharp_m5.csv
  gold_m15: goldsharp_m15.csv
  gold_h1: goldsharp_h1.csv
  gold_h4: goldsharp_h4.csv
  gold_d1: goldsharp_d1.csv

  btc_m5: btcusdsharp_m5.csv
  btc_m15: btcusdsharp_m15.csv
  btc_h1: btcusdsharp_h1.csv
  btc_h4: btcusdsharp_h4.csv
```

実行時は `--csv-dir` と結合する。

```text
--csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
```

個別CSV引数も許可する場合の優先順位:

```text
1. 個別CSV引数が指定されていればそれを使う
2. なければ --csv-dir + csv_keys から組み立てる
```

---

## 7. timeframe minutes / close_time

```yaml
timeframe_minutes:
  M1: 1
  M5: 5
  M15: 15
  H1: 60
  H4: 240
  D1: 1440
```

close_time:

```text
close_time = time + timeframe_minutes
```

D1は、まずは単純に `time + 1日` として扱う。

---

## 8. confirmed-time rule

MTF結合は必ず以下を満たす。

```text
context_close_time <= base_close_time
```

pivot系は必ず以下を満たす。

```text
pivot_confirmed_time <= signal_close_time
entry_time >= signal_close_time
```

MTF結合では、contextの `time` ではなく `context_close_time` を使う。

NG:

```text
M5 00:00 に H1 00:00 を結合する
```

OK:

```text
M5 close_time >= H1 close_time のときだけH1を使用する
```

検証CSV・audit CSVには、最低限以下を残す。

```text
base_time
base_close_time
context_time
context_close_time
signal_close_time
entry_time
pivot_time
pivot_confirmed_time
```

---

## 9. safe CSV reader 仕様

### 9.1 目的

MT5 EA が追記中のCSVをPython側が安全に読むための共通部品とする。

担当:

```text
- tailだけ読む
- 末尾不完全行を除外
- parse不能行を除外
- time昇順チェック
- 重複time処理
- spread列確認
- 短時間リトライ
- close_time付与
- metadata返却
```

### 9.2 入力

```text
path
timeframe
tail_bars
required_columns
requires_spread
as_of_time optional
retry_count
retry_sleep_sec
```

初期値:

```text
retry_count = 3
retry_sleep_sec = 0.2
```

### 9.3 CSV列

EA v1.32想定:

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

spreadが必要な場合の追加必須列:

```text
spread
```

`real_volume` は存在すれば保持する。

### 9.4 区切り文字

初期仕様は自動判定。

```text
--csv-sep auto
--csv-sep ;
--csv-sep ,
```

初期値は `auto`。

自動判定:

```text
1. 先頭行を読む
2. ";" が多ければ semicolon
3. "," が多ければ comma
4. 判定不能なら CSV_SEPARATOR_UNKNOWN
```

### 9.5 tail read 方針

比較スクリプト:

```text
正確性優先。初期実装ではfull read可。
```

live minimal scanner:

```text
tail read必須。pandas full read禁止。
```

最終的には比較スクリプトも本番と同じsafe tail readerを使う。

### 9.6 末尾不完全行・parse不能行

除外条件:

```text
- 空行
- 列数がheaderより少ない
- timeがparseできない
- open/high/low/closeがparseできない
```

末尾の数行だけparse不能なら除外して続行してよい。
ファイル中間にparse不能がある場合は異常としてaudit errorに記録し、そのCSVを使うpairはskip推奨。

### 9.7 time parse

想定format:

```text
YYYY.MM.DD HH:MM
YYYY.MM.DD HH:MM:SS
YYYY-MM-DD HH:MM:SS
```

timezoneは付けず、naive datetimeで扱う。

### 9.8 数値parse

```text
open/high/low/close: float
tick_volume: float
spread: float
real_volume: float
```

### 9.9 time昇順チェック

同一time重複は許容するが、timeは非減少であること。

OK:

```text
10:00
10:05
10:05
10:10
```

NG:

```text
10:00
10:10
10:05
```

NGの場合:

```text
そのCSVを使うpairのscanをskip
audit logに TIME_NOT_ASCENDING を残す
```

勝手にsortしない。

### 9.10 同一time重複処理

同一timeが複数ある場合は最後の行を採用する。

```text
drop_duplicates(subset=["time"], keep="last")
```

同一timeでOHLCが違う場合はaudit warningに残す。

```text
duplicate_time_count
duplicate_time_ohlc_conflict_count
```

### 9.11 as_of_time処理

比較スクリプトで `--as-of-time` が指定された場合:

```text
df = df[df["close_time"] <= as_of_time]
```

`--as-of-time` 未指定の場合:

```text
CSV末尾まで使用
```

### 9.12 reader戻り値

DataFrameだけでなくmetadataも返す。

```text
df
read_status
error_reason
rows_raw
rows_valid
rows_dropped_parse
rows_dropped_incomplete
duplicate_time_count
duplicate_time_ohlc_conflict_count
latest_time
latest_close_time
```

---

## 10. payload_key builder 仕様

### 10.1 目的

payload_keyは、同一シグナルを一意に識別し、重複通知を防ぐための安定キーである。

絶対に入れないもの:

```text
source_filter_name
reason_text
risk_status
spread値
Discord文面
```

### 10.2 構成

正式固定:

```text
symbol
pair_name
candidate_rank
direction
signal_close_time
entry_time
entry_price_normalized
```

文字列形式:

```text
{symbol}|{pair_name}|{candidate_rank}|{direction}|{signal_close_time}|{entry_time}|{entry_price_normalized}
```

例:

```text
GOLD|GOLD_H4_M15_DAYTRADE|B|SELL|2026-05-06 10:15:00|2026-05-06 10:15:00|2320.45
BTC|BTC_H4_M15_DAYTRADE|A|BUY|2026-05-06 10:15:00|2026-05-06 10:15:00|64250.50
```

### 10.3 正規化ルール

```text
symbol: 大文字固定。GOLD / BTC
pair_name: config上のpair_nameを大文字固定
candidate_rank: 大文字固定。A / B
direction: 大文字固定。BUY / SELL
time format: YYYY-MM-DD HH:MM:SS
entry_price_normalized: GOLD/BTCとも小数2桁
```

価格丸め:

```text
format(price, ".2f")
```

`signal_close_time` と `entry_time` は現時点では同じになることが多いが、将来の仕様変更に備えて両方入れる。

payload_keyが作れない候補は通知しない。

```text
signal_close_time missing -> PAYLOAD_KEY_INVALID
entry_time missing -> PAYLOAD_KEY_INVALID
entry_price missing -> PAYLOAD_KEY_INVALID
```

---

## 11. minimal scanner 本体仕様

### 11.1 役割

minimal scanner は、指定されたpairだけを対象に、必要CSV tailから最新通知候補を生成する。

やらないこと:

```text
- 全pair scan
- Discord送信
- send ledger更新
- live loop sleep管理
- 初回起動state初期化
```

やること:

```text
- pair configに基づく必要CSV読込
- confirmed-time join
- allowed rank/directionのみ判定
- 候補の正規化
- risk enrich
- payload_key生成
- scanner resultを返す
```

### 11.2 入力

関数またはCLI内部APIとしては以下を受け取る。

```text
pair_config
csv_resolver
allowed_slices
as_of_time optional
tail_bars override optional
scan_recent_bars optional
risk_enrich_config
spread_config
```

重要:

```text
allowed_slicesから必要pairを決めた後に呼び出す。
minimal scanner側で全pair列挙しない。
```

### 11.3 出力

pairごとに以下を返す。

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

通知候補としてlive loopへ渡してよいのは `risk_ok_candidates_df` のみ。

### 11.4 候補正規化後の必須列

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
```

confirmed-time列:

```text
base_time
base_close_time
context_time
context_close_time
pivot_time
pivot_confirmed_time
```

risk列:

```text
risk_reject_reason
risk_distance
reward_distance
rr
```

BTC spread列:

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

### 11.5 risk enrich の位置

minimal scanner本体の出力は、原則 risk enrich 済みにする。

理由:

```text
- live loop側でrisk NGを誤って送信しないため
- full strict scan vs minimal scan比較でrisk_statusまで一致確認するため
- BTC spread-aware判定をscanner出力に含めるため
```

ただし実装上は、内部で以下の2段階に分ける。

```text
1. raw candidate generation
2. risk/spread enrichment + normalization
```

比較スクリプトでは raw と enriched の両方を保存できるようにする。

---

## 12. BTC spread仕様

BTCは必ずspread込みで判定する。

CSVに必要な列:

```text
spread
```

通知・監査に必要な値:

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

判定用spread初期仕様:

```text
effective_spread_price = max(current_spread_price, mode_spread_price)
```

理由:

```text
- currentだけだと一時的に低いspreadを拾う可能性がある
- modeだけだと現在の急拡大を見逃す可能性がある
- maxを使うと保守的になる
```

自動売買ではさらに厳しくする。

```text
spread取得不能 -> reject
spread_to_sl_ratio 上限超え -> reject
effective_rr_after_spread 下限未満 -> reject
```

---

## 13. state仕様

stateは2系統に分ける。

### 13.1 更新検知用state

```text
last_seen_base_close_time_by_pair
```

例:

```json
{
  "last_seen_base_close_time_by_pair": {
    "GOLD_H4_M5_SCALP": "2026-05-06 10:25:00",
    "GOLD_H4_M15_DAYTRADE": "2026-05-06 10:15:00",
    "GOLD_D1_H1_DAYTRADE": "2026-05-06 10:00:00",
    "BTC_H4_M15_DAYTRADE": "2026-05-06 10:15:00"
  }
}
```

### 13.2 通知重複防止用state

```text
last_notified_time_by_symbol_pair_direction
```

ただし、最重要の重複防止は send ledger の `payload_key` で行う。

---

## 14. send ledger仕様

実際に送信した通知を保存する。

最低限の列:

```text
sent_at
payload_key
symbol
pair_name
candidate_rank
direction
signal_close_time
entry_time
entry_price
sl_price
tp_price
risk_status
discord_status
message_hash
```

BTC追加:

```text
current_spread_price
mode_spread_price
effective_spread_price
spread_to_sl_ratio
effective_rr_after_spread
net_sl_after_spread_price
net_tp_after_spread_price
```

既にledgerにpayload_keyがある場合:

```text
duplicate skip
sendしない
```

risk NGの候補はsend ledgerには入れない。
監査ログには残す。

---

## 15. audit log仕様

audit logは、送ったものだけでなく、送らなかったものも記録する。

loop summary:

```text
run_started_at
run_finished_at
duration_sec
pair_name
base_timeframe
latest_base_close_time
previous_base_close_time
base_time_advanced
scan_executed
raw_candidates
risk_ok_candidates
risk_ng_candidates
duplicate_candidates
sent_candidates
skip_reason
error_summary
```

candidate audit:

```text
detected_at
symbol
pair_name
candidate_rank
direction
signal_close_time
entry_time
entry_price
sl_price
tp_price
risk_status
risk_reject_reason
payload_key
payload_key_status
duplicate_status
send_status
reason_text
base_close_time
context_close_time
pivot_confirmed_time
```

BTC追加:

```text
current_spread_price
mode_spread_price
effective_spread_price
spread_to_sl_ratio
effective_rr_after_spread
net_sl_after_spread_price
net_tp_after_spread_price
```

payload_keyが作れなかった候補もauditには残す。

```text
candidate_debug_id
payload_key
payload_key_status
```

payload_key_status:

```text
OK
INVALID_MISSING_FIELD
INVALID_PRICE
INVALID_TIME
```

---

## 16. full strict scan vs minimal scan 比較スクリプト仕様

スクリプト名案:

```text
scripts/compare_mochipoyo_full_strict_vs_minimal.py
```

目的:

```text
同じCSV時点、同じallowed_slices、同じrisk enrich、同じpayload_key仕様で、full strict scanとminimal scanの最新通知候補が一致するか確認する。
```

この比較にPASSしない限り、minimal scannerを本番live通知に使わない。

### 16.1 入力

```text
--csv-dir
--allowed-slices-json optional
--out-dir
--as-of-time optional
--lookback-candidates 50
--tail-m5 6000
--tail-m15 5000
--tail-h1 1500
--tail-h4 1500
--tail-d1 800
```

個別CSV引数を許可する場合:

```text
--gold-m5-csv
--gold-m15-csv
--gold-h1-csv
--gold-h4-csv
--gold-d1-csv
--btc-m15-csv
--btc-h4-csv
--btc-m5-csv optional
--btc-h1-csv optional
```

### 16.2 比較主キー

primary key:

```text
payload_key
```

fallback logical key:

```text
symbol
pair_name
candidate_rank
direction
signal_close_time
entry_time
entry_price_normalized
```

比較手順:

```text
1. payload_keyでouter join
2. full_only / minimal_only を抽出
3. fallback logical keyでも照合
4. fallbackでは一致するのにpayload_keyが違う場合は payload_key_diff として出す
```

### 16.3 比較項目

基本:

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
```

confirmed-time:

```text
base_time
base_close_time
context_time
context_close_time
pivot_time
pivot_confirmed_time
entry_time
```

risk:

```text
risk_status
risk_reject_reason
risk_distance
reward_distance
rr
```

BTC spread:

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

### 16.4 出力ファイル

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

summary列:

```text
run_at
as_of_time
allowed_slices_count
pairs_count
full_rows
minimal_rows
matched_rows
full_only_rows
minimal_only_rows
value_diff_rows
payload_key_diff_rows
status
```

status:

```text
PASS
FAIL
ERROR
```

### 16.5 合格条件

最新判定対象範囲で以下を満たす。

```text
full_only_rows = 0
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
```

初期比較範囲:

```text
lookback_candidates = 50
```

---

## 17. tail本数感度テスト

比較スクリプトに `--tail-sensitivity` モードを追加する案を採用する。

最大tail:

```text
M5  = 6000
M15 = 5000
H1  = 1500
H4  = 1500
D1  = 800
```

テストセット:

```text
set_1:
  M5 1000
  M15 1000
  H1 500
  H4 300
  D1 200

set_2:
  M5 3000
  M15 2000
  H1 1000
  H4 800
  D1 400

set_3:
  M5 6000
  M15 3000
  H1 1500
  H4 1500
  D1 800

set_4:
  M5 6000
  M15 5000
  H1 1500
  H4 1500
  D1 800
```

set_4を基準にする。

合格条件:

```text
最新判定対象範囲でpayload_keyと通知重要値が一致
```

通知重要値:

```text
direction
entry_time
entry_price_normalized
sl_price
tp_price
risk_status
reason_text
```

BTC追加:

```text
effective_spread_price
spread_to_sl_ratio
effective_rr_after_spread
```

---

## 18. pair別更新トリガーテスト

後段でlive loop側のテストとして作る。

確認すること:

```text
1. base CSVのtimeが進んだpairだけscanされる
2. context CSVだけ進んでもscanされない
3. 他pairのbase CSV更新に巻き込まれない
4. 未更新時はscanされない
5. 初回live起動では通知されない
```

出力:

```text
trigger_test_summary.csv
trigger_test_events.csv
```

---

## 19. 重複通知テスト

テスト1:

```text
同じCSVで2回連続実行
```

期待結果:

```text
1回目: send対象あり
2回目: sent 0 / duplicate skip
```

テスト2:

```text
同一シグナルが複数条件に一致
```

期待結果:

```text
payload_keyが同じなら1回だけ通知
```

テスト3:

```text
risk_status NGの候補
```

期待結果:

```text
通知しない
send ledgerにも入れない
audit logには残す
```

テスト4:

```text
risk_status NGだった候補が後でOKになった場合
```

期待結果:

```text
NG時点ではpayload_keyをsend ledgerに入れない
OKになった時点で初めて通知対象
```

---

## 20. エラー仕様

reader error:

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

payload error:

```text
PAYLOAD_MISSING_SYMBOL
PAYLOAD_MISSING_PAIR_NAME
PAYLOAD_MISSING_CANDIDATE_RANK
PAYLOAD_MISSING_DIRECTION
PAYLOAD_MISSING_SIGNAL_CLOSE_TIME
PAYLOAD_MISSING_ENTRY_TIME
PAYLOAD_MISSING_ENTRY_PRICE
PAYLOAD_PRICE_PARSE_FAILED
```

scan error:

```text
PAIR_CONFIG_MISSING
BASE_CSV_READ_FAILED
CONTEXT_CSV_READ_FAILED
CONFIRMED_TIME_JOIN_FAILED
RISK_ENRICH_FAILED
BTC_SPREAD_ENRICH_FAILED
```

---

## 21. 実装順序

新規コードを書く場合の順序は以下に固定する。

```text
1. pair config
2. safe CSV reader
3. payload_key builder
4. full strict scan出力の正規化
5. minimal scan出力の正規化
6. compare script
7. tail sensitivity mode
8. minimal scanner本体
9. live loop
10. Discord接続
```

live loopを先に書かない。
まず比較できる形を作る。
比較にPASSしてからminimal scanner本体。
最後にloop化する。

---

## 22. 本番使用条件

minimal scannerを本番live通知に使う条件:

```text
1. full strict scan vs minimal scan比較にPASSすること
2. tail本数感度テストにPASSすること
3. pair別更新トリガーテストにPASSすること
4. 重複通知テストにPASSすること
5. BTC spread-aware項目が欠損なく出力されること
6. risk_status OK以外が通知されないこと
```

この条件を満たすまでは、既存loopも新minimal loopも本番常時稼働に使わない。
