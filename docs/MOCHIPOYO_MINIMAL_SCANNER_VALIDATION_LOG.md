# MOCHIPOYO Minimal Scanner Validation Log

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 live notification minimal scanner の実装・検証ログである。

目的は、full strict scan と minimal scan の一致確認、tail本数感度、pair別candidate generatorの追加状況を、実装判断の根拠として残すこと。

---

## 1. 実装済み共通部品

```text
scripts/mochipoyo_minimal_config.py
scripts/mochipoyo_safe_csv_reader.py
scripts/mochipoyo_payload_key.py
scripts/mochipoyo_candidate_normalizer.py
scripts/compare_mochipoyo_full_strict_vs_minimal.py
scripts/mochipoyo_minimal_scanner.py
scripts/mochipoyo_candidate_generators.py
```

---

## 2. GOLD_H4_M5_SCALP 検証結果

対象slice:

```text
GOLD_H4_M5_SCALP|A|SELL
GOLD_H4_M5_SCALP|B|SELL
```

minimal generator は既存の audited 関数を再利用している。

```text
scan_mochipoyo_multi_tf_candidates.py:
  add_indicators
  confirmed_join
  scan_pair

filter_mochipoyo_candidate_events.py:
  rank_ok
  has_any_divergence
  has_granville
  apply_cooldown
  apply_daily_cap
```

### 2.1 minimal generator 初回出力

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test
```

結果:

```text
GOLD_H4_M5_SCALP:
  scan_status = OK
  base_rows = 6000
  context_frames = H4
  raw_candidates = 79
  normalized_candidates = 45
  risk_ok_candidates = 0
  risk_ng_candidates = 0
  error_count = 0
```

normalized candidates 内訳:

```text
GOLD_H4_M5_SCALP A SELL = 33
GOLD_H4_M5_SCALP B SELL = 12
payload_ok = 45 / 45
```

risk_ok_candidates が0なのは、現時点で minimal generator に risk/SL/TP enrich を接続していないため正常。

---

## 3. GOLD_H4_M5_SCALP: full strict payload との比較

比較対象:

```text
full:
  data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_payloads.csv
minimal:
  data\results\mochipoyo\minimal_generator_test\minimal_candidates_normalized_gold_h4_m5_scalp.csv
pair:
  GOLD_H4_M5_SCALP
```

pair絞り込み比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_payloads.csv --minimal-csv data\results\mochipoyo\minimal_generator_test\minimal_candidates_normalized_gold_h4_m5_scalp.csv --pair-name GOLD_H4_M5_SCALP --out-dir data\results\mochipoyo\minimal_compare_gold_h4_m5_pair_only --lookback-candidates 50
```

結果:

```text
full_rows = 19
minimal_rows = 45
matched_rows = 19
full_only_rows = 0
minimal_only_rows = 26
value_diff_rows = 0
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

解釈:

```text
full strict payload に出ていた GOLD_H4_M5_SCALP 19件は、minimal側に全件存在。
一致した19件について value_diff / payload_key_diff は0。
minimal_only 26件は、full payloadが直近通知payloadに限定されているため発生。
```

---

## 4. GOLD_H4_M5_SCALP: full strict allowed_events との比較

比較対象:

```text
full:
  data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv
minimal:
  data\results\mochipoyo\minimal_generator_test\minimal_candidates_normalized_gold_h4_m5_scalp.csv
pair:
  GOLD_H4_M5_SCALP
```

重なり期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_generator_test\minimal_candidates_normalized_gold_h4_m5_scalp.csv --pair-name GOLD_H4_M5_SCALP --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_h4_m5_allowed_events_overlap --lookback-candidates 0
```

結果:

```text
alignment_mode = OVERLAP
alignment_status = APPLIED
alignment_start_signal_close_time = 2026-04-13 11:20:00
alignment_end_signal_close_time = 2026-05-06 01:05:00

full_rows = 48
minimal_rows = 45
matched_rows = 41
full_only_rows = 7
minimal_only_rows = 4
value_diff_rows = 0
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

差分は主に 2026-04-20〜2026-04-22 に集中。

解釈:

```text
full_only / minimal_only は、tail開始位置による ZigZag / pivot / divergence / cooldown 初期状態差の可能性が高い。
一致した41件は value_diff / payload_key_diff なし。
```

---

## 5. GOLD_H4_M5_SCALP tail本数感度: M5 6000 vs 12000

追加実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_tail12000 --tail-m5 12000 --tail-h4 1500
```

結果:

```text
GOLD_H4_M5_SCALP:
  base_rows = 12000
  raw_candidates = 150
  normalized_candidates = 97
  error_count = 0
```

6000 vs 12000 の共通期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\minimal_generator_test\minimal_candidates_normalized_gold_h4_m5_scalp.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_tail12000\minimal_candidates_normalized_gold_h4_m5_scalp.csv --pair-name GOLD_H4_M5_SCALP --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_h4_m5_tail6000_vs_tail12000 --lookback-candidates 0
```

結果:

```text
alignment_mode = OVERLAP
alignment_start_signal_close_time = 2026-04-13 11:20:00
alignment_end_signal_close_time = 2026-05-06 01:05:00

full_rows = 45
minimal_rows = 45
matched_rows = 45
full_only_rows = 0
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
```

結論:

```text
GOLD_H4_M5_SCALP の共通期間では、M5 tail 6000 と 12000 の候補は完全一致。
したがって、少なくとも直近範囲では tail 6000 の候補生成は安定。
ただし古い期間まで検証する場合、tail 12000の方が候補数は増える。
```

---

## 6. GOLD_H4_M15_DAYTRADE 検証結果

対象slice:

```text
GOLD_H4_M15_DAYTRADE|B|BUY
GOLD_H4_M15_DAYTRADE|B|SELL
```

実装:

```text
scripts/mochipoyo_candidate_generators.py の SUPPORTED_GENERATOR_PAIRS に GOLD_H4_M15_DAYTRADE を追加。
既存の add_indicators / confirmed_join / scan_pair / event filter 経路を再利用。
```

### 6.1 minimal generator 初回出力

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_gold_h4_m15
```

結果:

```text
GOLD_H4_M15_DAYTRADE:
  scan_status = OK
  base_rows = 5000
  context_frames = H4
  raw_candidates = 85
  normalized_candidates = 23
  risk_ok_candidates = 0
  risk_ng_candidates = 0
  error_count = 0
```

normalized candidates 内訳:

```text
GOLD_H4_M15_DAYTRADE B SELL = 13
GOLD_H4_M15_DAYTRADE B BUY  = 10
payload_ok = 23 / 23
```

### 6.2 full strict payload との比較

比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_payloads.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_gold_h4_m15\minimal_candidates_normalized_gold_h4_m15_daytrade.csv --pair-name GOLD_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_h4_m15_payload_overlap --lookback-candidates 0
```

結果:

```text
full_rows = 1
minimal_rows = 1
matched_rows = 1
full_only_rows = 0
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

結論:

```text
full strict payload に出ていた GOLD_H4_M15_DAYTRADE 1件は minimal側と完全一致。
```

### 6.3 full strict allowed_events との比較

比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_gold_h4_m15\minimal_candidates_normalized_gold_h4_m15_daytrade.csv --pair-name GOLD_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_h4_m15_allowed_events_overlap --lookback-candidates 0
```

結果:

```text
full_rows = 36
minimal_rows = 23
matched_rows = 23
full_only_rows = 13
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

結論:

```text
minimal generator が出した GOLD_H4_M15_DAYTRADE 23件は、full strict allowed_events側に全件存在。
full_only 13件は、tail開始位置またはwarmup差による可能性が高い。
```

### 6.4 tail本数感度: M15 5000 vs 10000

追加実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_gold_h4_m15_tail10000 --tail-m15 10000 --tail-h4 1500
```

結果:

```text
GOLD_H4_M15_DAYTRADE:
  base_rows = 10000
  raw_candidates = 168
  normalized_candidates = 39
  error_count = 0
```

5000 vs 10000 の共通期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\minimal_generator_test_gold_h4_m15\minimal_candidates_normalized_gold_h4_m15_daytrade.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_gold_h4_m15_tail10000\minimal_candidates_normalized_gold_h4_m15_daytrade.csv --pair-name GOLD_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_h4_m15_tail5000_vs_tail10000 --lookback-candidates 0
```

結果:

```text
full_rows = 23
minimal_rows = 23
matched_rows = 23
full_only_rows = 0
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
```

結論:

```text
GOLD_H4_M15_DAYTRADE の共通期間では、M15 tail 5000 と 10000 の候補は完全一致。
したがって、少なくとも直近範囲では tail 5000 の候補生成は安定。
```

---

## 7. GOLD_D1_H1_DAYTRADE 検証結果

対象slice:

```text
GOLD_D1_H1_DAYTRADE|A|BUY
GOLD_D1_H1_DAYTRADE|B|BUY
```

実装:

```text
scripts/mochipoyo_candidate_generators.py の SUPPORTED_GENERATOR_PAIRS に GOLD_D1_H1_DAYTRADE を追加。
既存の add_indicators / confirmed_join / scan_pair / event filter 経路を再利用。
```

### 7.1 minimal generator 初回出力

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_gold_d1_h1
```

結果:

```text
GOLD_D1_H1_DAYTRADE:
  scan_status = OK
  base_rows = 1500
  context_frames = D1
  raw_candidates = 39
  normalized_candidates = 24
  risk_ok_candidates = 0
  risk_ng_candidates = 0
  error_count = 0
```

normalized candidates 内訳:

```text
GOLD_D1_H1_DAYTRADE A BUY = 22
GOLD_D1_H1_DAYTRADE B BUY = 2
payload_ok = 24 / 24
```

### 7.2 full strict payload との比較

比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_payloads.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_gold_d1_h1\minimal_candidates_normalized_gold_d1_h1_daytrade.csv --pair-name GOLD_D1_H1_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_d1_h1_payload_overlap --lookback-candidates 0
```

結果:

```text
full_rows = 0
minimal_rows = 24
alignment_status = EMPTY_SIDE
```

解釈:

```text
gold_mochipoyo_live_dryrun_strict_payloads.csv の直近payload内に GOLD_D1_H1_DAYTRADE が無かったため、payload比較は比較不能。
これはエラーではない。
```

### 7.3 full strict allowed_events との比較

比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_gold_d1_h1\minimal_candidates_normalized_gold_d1_h1_daytrade.csv --pair-name GOLD_D1_H1_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_d1_h1_allowed_events_overlap --lookback-candidates 0
```

結果:

```text
full_rows = 31
minimal_rows = 24
matched_rows = 24
full_only_rows = 7
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

結論:

```text
minimal generator が出した GOLD_D1_H1_DAYTRADE 24件は、full strict allowed_events側に全件存在。
full_only 7件は、tail開始位置またはwarmup差による可能性が高い。
```

### 7.4 tail本数感度: H1 1500 vs 3000

追加実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_gold_d1_h1_tail3000 --tail-h1 3000 --tail-d1 800
```

結果:

```text
GOLD_D1_H1_DAYTRADE:
  base_rows = 3000
  raw_candidates = 75
  normalized_candidates = 60
  error_count = 0
```

1500 vs 3000 の共通期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\minimal_generator_test_gold_d1_h1\minimal_candidates_normalized_gold_d1_h1_daytrade.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_gold_d1_h1_tail3000\minimal_candidates_normalized_gold_d1_h1_daytrade.csv --pair-name GOLD_D1_H1_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_gold_d1_h1_tail1500_vs_tail3000 --lookback-candidates 0
```

結果:

```text
full_rows = 24
minimal_rows = 24
matched_rows = 24
full_only_rows = 0
minimal_only_rows = 0
value_diff_rows = 0
payload_key_diff_rows = 0
```

結論:

```text
GOLD_D1_H1_DAYTRADE の共通期間では、H1 tail 1500 と 3000 の候補は完全一致。
したがって、少なくとも直近範囲では tail 1500 の候補生成は安定。
```

---

## 8. BTC_H4_M15_DAYTRADE 検証結果

対象slice:

```text
BTC_H4_M15_DAYTRADE|A|BUY
BTC_H4_M15_DAYTRADE|A|SELL
```

実装:

```text
scripts/mochipoyo_candidate_generators.py の SUPPORTED_GENERATOR_PAIRS に BTC_H4_M15_DAYTRADE を追加。
既存の add_indicators / confirmed_join / scan_pair / event filter 経路を再利用。
```

重要:

```text
BTCは candidate generation だけでは本番通知不可。
spread込みrisk enrichが必須。
通知には current_spread_price / mode_spread_price / effective_spread_price / spread_to_sl_ratio / effective_rr_after_spread / net_sl_after_spread_price / net_tp_after_spread_price を必ず含める。
```

### 8.1 minimal generator 初回出力

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_btc_h4_m15
```

結果:

```text
BTC_H4_M15_DAYTRADE:
  scan_status = OK
  base_rows = 5000
  context_frames = H4
  raw_candidates = 95
  normalized_candidates = 72
  risk_ok_candidates = 0
  risk_ng_candidates = 0
  error_count = 0
```

normalized candidates 内訳:

```text
BTC_H4_M15_DAYTRADE A BUY  = 52
BTC_H4_M15_DAYTRADE A SELL = 20
payload_ok = 72 / 72
```

### 8.2 full strict payload との比較

比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\btc_mochipoyo_live_dryrun_strict_payloads.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --pair-name BTC_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_btc_h4_m15_payload_overlap --lookback-candidates 0
```

結果:

```text
full_rows = 20
minimal_rows = 24
matched_rows = 18
full_only_rows = 2
minimal_only_rows = 6
value_diff_rows = 198
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

解釈:

```text
value_diff_rows が大きい主因は、full payload 側には risk/spread enrich済み列があり、minimal側にはまだ無いこと。
現段階では candidate一致だけを見る。
```

### 8.3 full strict allowed_events との比較

比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\live_dryrun\btc_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --pair-name BTC_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_btc_h4_m15_allowed_events_overlap --lookback-candidates 0
```

結果:

```text
full_rows = 69
minimal_rows = 72
matched_rows = 48
full_only_rows = 21
minimal_only_rows = 24
value_diff_rows = 0
payload_key_diff_rows = 0
status = NORMALIZED_ONLY_NO_RISK
```

解釈:

```text
GOLD 3pairより差分が大きい。
BTC candidate generation は動作OKだが、初期PASSとはまだ扱わない。
```

### 8.4 tail本数感度: M15 5000 vs 10000

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail10000 --tail-m15 10000 --tail-h4 1500
```

結果:

```text
BTC_H4_M15_DAYTRADE:
  base_rows = 10000
  raw_candidates = 202
  normalized_candidates = 160
  error_count = 0
```

5000 vs 10000 の共通期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail10000\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --pair-name BTC_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_btc_h4_m15_tail5000_vs_tail10000 --lookback-candidates 0
```

結果:

```text
full_rows = 72
minimal_rows = 71
matched_rows = 63
full_only_rows = 9
minimal_only_rows = 8
value_diff_rows = 0
payload_key_diff_rows = 0
```

結論:

```text
BTCは M15 tail 5000 では不足。
ZigZag / pivot / divergence / cooldown の初期位置影響がGOLDより強い。
```

### 8.5 tail本数感度: M15 10000 vs 15000

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail15000 --tail-m15 15000 --tail-h4 1500
```

結果:

```text
BTC_H4_M15_DAYTRADE:
  base_rows = 15000
  raw_candidates = 305
  normalized_candidates = 231
  error_count = 0
```

10000 vs 15000 の共通期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail10000\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail15000\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --pair-name BTC_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_btc_h4_m15_tail10000_vs_tail15000 --lookback-candidates 0
```

結果:

```text
full_rows = 160
minimal_rows = 159
matched_rows = 158
full_only_rows = 2
minimal_only_rows = 1
value_diff_rows = 0
payload_key_diff_rows = 0
```

### 8.6 tail本数感度: M15 15000 vs 20000

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail20000 --tail-m15 20000 --tail-h4 1500
```

結果:

```text
BTC_H4_M15_DAYTRADE:
  base_rows = 20000
  raw_candidates = 387
  normalized_candidates = 293
  error_count = 0
```

15000 vs 20000 の共通期間比較:

```cmd
python scripts\compare_mochipoyo_full_strict_vs_minimal.py --full-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail15000\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --minimal-csv data\results\mochipoyo\minimal_generator_test_btc_h4_m15_tail20000\minimal_candidates_normalized_btc_h4_m15_daytrade.csv --pair-name BTC_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\minimal_compare_btc_h4_m15_tail15000_vs_tail20000 --lookback-candidates 0
```

結果:

```text
full_rows = 231
minimal_rows = 230
matched_rows = 229
full_only_rows = 2
minimal_only_rows = 1
value_diff_rows = 0
payload_key_diff_rows = 0
```

差分確認:

```text
full_only:
  2025-12-01 21:45 SELL
  2025-12-02 13:45 SELL

minimal_only:
  2025-12-02 00:00 SELL
```

解釈:

```text
差分は tail overlap 開始直後の 2025-12-01〜2025-12-02 に集中。
最新付近の差分ではない。
したがって、tail開始直後の ZigZag / pivot / divergence / cooldown 初期化差と見る。
```

### 8.7 BTC candidate generation 現時点の結論

```text
BTC_H4_M15_DAYTRADE candidate generation:
  実装状態: 動作OK。ただしGOLDほど完全一致ではないため初期PASS扱いは保留。
  tail5000: 不足
  tail10000: 大幅改善
  tail15000以上: 差分はtail開始直後の数件に限定
  本番通知利用: risk/spread enrich前なので不可
```

暫定仕様:

```text
BTC_H4_M15_DAYTRADE:
  M15 tail は 15000 以上を採用候補にする。
  tail全期間の完全一致は必須にしない。
  tail開始直後の差分はwarmup影響として扱う。
  live通知判定は最新確定足/直近数本だけに限定する。
  最新側で full strict と一致するかを別途確認する。
```

---

## 9. 現時点の判定

```text
GOLD_H4_M5_SCALP candidate generation:
  実装状態: 初期PASS相当
  risk/SL/TP enrich: 未接続
  本番通知利用: まだ不可

GOLD_H4_M15_DAYTRADE candidate generation:
  実装状態: 初期PASS相当
  risk/SL/TP enrich: 未接続
  本番通知利用: まだ不可

GOLD_D1_H1_DAYTRADE candidate generation:
  実装状態: 初期PASS相当
  risk/SL/TP enrich: 未接続
  本番通知利用: まだ不可

BTC_H4_M15_DAYTRADE candidate generation:
  実装状態: 動作OK。ただしtail全期間完全一致ではないため初期PASS扱いは保留
  risk/spread enrich: 未接続
  本番通知利用: 不可
```

本番通知に進むための残課題:

```text
1. GOLD candidates に risk/SL/TP enrich を接続
2. BTC candidates に spread込みrisk enrich を接続
3. risk_status OK / btc_live_risk_status OK のみ通知対象にする
4. pair別更新トリガー確認
5. ledger重複通知確認
6. Discord dry-run確認
```

---

## 10. 次の実装対象

次は candidate generation ではなく、risk enrich 接続へ進む。

候補:

```text
scripts/enrich_mochipoyo_live_payload_risk.py
```

方針:

```text
- 既存 enrich ロジックを読み、minimal scanner output に接続できる最小I/Fを決める。
- GOLDは live_risk_status == OK のみ通知候補。
- BTCは btc_live_risk_status == OK かつ spread関連列が揃ったものだけ通知候補。
- BTCは spread_to_sl_ratio / effective_rr_after_spread / net_sl_after_spread_price / net_tp_after_spread_price を比較必須項目にする。
```
