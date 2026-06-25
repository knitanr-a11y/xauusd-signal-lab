# GOLD_ML_V1 Batch023: 9候補ローカルexact replay

更新日: 2026-06-25

## 目的

現在の積み重ね9候補を、許可済みraw candle CSVからWindows 11 / Python 3.12で再生成し、正本exact trade registryと比較する。探索、閾値変更、自動補正は行わない。

## 対象

- GML1-PROV-007
- GML1-PROV-008
- GML1-WATCH-022-B
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-021-A
- GML1-WATCH-021-B
- GML1-WATCH-021-C

## リポジトリ内の実装

- Python: `scripts/gold_ml_v1/replay/nine_candidate_local_replay.py`
- one-click raw replay: `scripts/gold_ml_v1/replay/run_nine_candidate_local_replay.bat`
- registry-only parity: `scripts/gold_ml_v1/replay/run_nine_candidate_registry_parity.bat`
- frozen config: `config/gold_ml_v1/replay/nine_candidate_replay_config_20260625.json`
- expected metrics: `config/gold_ml_v1/replay/nine_candidate_expected_metrics_20260625.json`
- expected hashes: `config/gold_ml_v1/replay/nine_candidate_expected_sha256_20260625.json`
- exact registries: `config/gold_ml_v1/registries/`
- tests: `tests/gold_ml_v1/test_nine_candidate_local_replay.py`

## 必要なraw historicalファイル

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`
- `gold_v3_2023_2026_h4.csv`
- `gold_v3_2023_2026_d1.csv`

任意のlive append:

- `goldsharp_m1.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

historical最大bar-open時刻より後だけをappendする。

## 実行

リポジトリの任意の場所からBATを起動し、raw CSVフォルダを第1引数に渡す。

```bat
scripts\gold_ml_v1\replay\run_nine_candidate_local_replay.bat "C:\path\to\raw"
```

正本台帳だけを検査する場合:

```bat
scripts\gold_ml_v1\replay\run_nine_candidate_registry_parity.bat
```

## 出力

既定出力先:

- `outputs/gold_ml_v1/batch023_local_replay/`

主な出力:

- `raw_input_manifest.json`
- `raw_replay_comparison.csv`
- `raw_replay_summary.json`
- 候補ごとのlocal registry
- 候補ごとのmissing/extra差分
- 候補ごとの価格・R・outcome差分

## 終了コード

- 0: exact parity
- 1: input missingまたはinput contract違反
- 2: registry mismatch
- 3: metrics mismatch
- 4: environment/dependency/exception

## 現在分かっている未完了点

GitHubにはraw candle CSVを保存していないため、GitHub上だけではfull raw replayを実行できない。ユーザーPC上の許可済みraw CSVの保存場所を指定して実行する必要がある。

registry SHA、row count、metrics、PROV-020 / WATCH-021-A/B/C / WATCH-022-Bの親台帳派生一致は事前にPASSしている。full raw replayのPASSはまだ主張しない。

## 境界

- MT5 server timeをJSTへ変更しない。
- 最新行をopen扱いで削除しない。
- HTFはbar close後のみ利用する。
- exact M1 entryがなければinvalid。
- 同一M1内TP/SLはSL優先。
- 2026を使った閾値調整は禁止。
- mismatchを自動修正せず、差分を保存する。
- audit-onlyを維持する。
