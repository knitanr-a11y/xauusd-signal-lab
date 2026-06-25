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

## GitHub実装

- Python: `scripts/gold_ml_v1/replay/nine_candidate_local_replay.py`
- one-click raw replay: `scripts/gold_ml_v1/replay/run_nine_candidate_local_replay.bat`
- registry-only parity: `scripts/gold_ml_v1/replay/run_nine_candidate_registry_parity.bat`
- artifact installer: `scripts/gold_ml_v1/tools/install_batch023_local_replay_artifacts.py`
- installer BAT: `scripts/gold_ml_v1/tools/run_install_batch023_local_replay_artifacts.bat`
- frozen config: `config/gold_ml_v1/replay/nine_candidate_replay_config_20260625.json`
- expected metrics: `config/gold_ml_v1/replay/nine_candidate_expected_metrics_20260625.json`
- expected hashes: `config/gold_ml_v1/replay/nine_candidate_expected_sha256_20260625.json`
- tests: `tests/gold_ml_v1/test_nine_candidate_local_replay.py`
- GitHub Actions: `.github/workflows/gold_ml_v1_batch023_tests.yml`

## 1. 正本artifactをインストール

Batch023 ZIPを任意の場所へ保存し、リポジトリ内で次を実行する。

```bat
scripts\gold_ml_v1\tools\run_install_batch023_local_replay_artifacts.bat "C:\path\to\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
```

installerは次をfail-closedで検証する。

- ZIP SHA256: `d1e9ab8cbeb7d73c8cf75f688bad39af0d64982901fbcd4474c1b230802b53b9`
- 9候補exact registryのSHA256と行数
- PROV-015 parent-event registry
- WATCH-021派生に必要な54-feature registry

PASSしたファイルだけを`config/gold_ml_v1/registries/`へ配置する。

## 2. registry parity

```bat
scripts\gold_ml_v1\replay\run_nine_candidate_registry_parity.bat
```

確認対象:

- registry SHA256
- 行数
- metrics再計算
- PROV-020の親台帳派生
- WATCH-021-A/B/Cの親台帳派生
- WATCH-022-Bの親台帳派生

## 3. 必要なraw candle CSV

historical必須:

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`
- `gold_v3_2023_2026_h4.csv`
- `gold_v3_2023_2026_d1.csv`

live appendは任意:

- `goldsharp_m1.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

historical最大bar-open時刻より後だけをappendする。

## 4. raw replay

raw CSVを含むフォルダを第1引数へ渡す。

```bat
scripts\gold_ml_v1\replay\run_nine_candidate_local_replay.bat "C:\path\to\raw"
```

rawフォルダ配下は再帰検索するため、5ファイルが同じ直下フォルダにある必要はない。

## 出力

- `outputs/gold_ml_v1/batch023_local_replay/`
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

## 現在の未完了点

GitHubへの実装は完了した。registry SHA、row count、metrics、PROV-020 / WATCH-021-A/B/C / WATCH-022-Bの親台帳派生一致は事前にPASSしている。

ただし、許可済みraw candle CSVのユーザーPC上の保存フォルダが未提示のため、full raw replayはまだ実行していない。raw replayのPASSは主張しない。

## 境界

- MT5 server timeをJSTへ変更しない。
- 最新行をopen扱いで削除しない。
- HTFはbar close後のみ利用する。
- exact M1 entryがなければinvalid。
- 同一M1内TP/SLはSL優先。
- 2026を使った閾値調整は禁止。
- mismatchを自動修正せず、差分を保存する。
- audit-onlyを維持する。
