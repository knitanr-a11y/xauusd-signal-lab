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

- historical replay: `scripts/gold_ml_v1/replay/nine_candidate_local_replay.py`
- historical replay BAT: `scripts/gold_ml_v1/replay/run_nine_candidate_local_replay.bat`
- registry-only parity: `scripts/gold_ml_v1/replay/run_nine_candidate_registry_parity.bat`
- goldsharp live source preflight: `scripts/gold_ml_v1/replay/goldsharp_live_source_preflight.py`
- goldsharp preflight BAT: `scripts/gold_ml_v1/replay/run_goldsharp_live_source_preflight.bat`
- artifact installer: `scripts/gold_ml_v1/tools/install_batch023_local_replay_artifacts.py`
- installer BAT: `scripts/gold_ml_v1/tools/run_install_batch023_local_replay_artifacts.bat`
- source contract: `config/gold_ml_v1/replay/historical_live_source_contract_20260625.json`
- frozen candidate config: `config/gold_ml_v1/replay/nine_candidate_replay_config_20260625.json`
- expected metrics: `config/gold_ml_v1/replay/nine_candidate_expected_metrics_20260625.json`
- expected hashes: `config/gold_ml_v1/replay/nine_candidate_expected_sha256_20260625.json`
- tests: `tests/gold_ml_v1/test_nine_candidate_local_replay.py`
- source-separation tests: `tests/gold_ml_v1/test_goldsharp_live_source_preflight.py`
- GitHub Actions: `.github/workflows/gold_ml_v1_batch023_tests.yml`

## source contract

### historical exact replay

historical replayは次の5ファイルだけを使う。

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`
- `gold_v3_2023_2026_h4.csv`
- `gold_v3_2023_2026_d1.csv`

`goldsharp_*.csv`はhistorical exact replayへ混ぜない。

### live audit / future signal source

ライブの新規closed bar観測には次だけを使う。

- `goldsharp_m1.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

ライブ時にhistoricalを参照できるのは、indicator warmupと連続性確保だけである。historical行から新規ライブシグナルを発生させてはならない。

新規ライブ判定対象は、各timeframeでhistorical最大bar-open時刻より後の`goldsharp`行だけとする。重複・過去側の`goldsharp`行は継続性監査には使えるが、新規判定対象にはしない。

CSV最新行はclosed row契約であり、open扱いで削除しない。時刻はMT5 server timeのまま扱う。

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

## 3. historical exact replay

`gold_v3_2023_2026`の5ファイルが入るフォルダを第1引数に渡す。

```bat
scripts\gold_ml_v1\replay\run_nine_candidate_local_replay.bat "C:\path\to\gold_v3_2023_2026"
```

このBATは`--mode raw`でhistoricalフォルダだけを検索する。親フォルダにある`goldsharp_*.csv`は読み込まない。

出力:

- `outputs/gold_ml_v1/batch023_historical_replay/`
- `raw_input_manifest.json`
- `raw_replay_comparison.csv`
- `raw_replay_summary.json`
- 候補ごとのlocal registry
- 候補ごとのmissing/extra差分
- 候補ごとの価格・R・outcome差分

## 4. goldsharp live source preflight

第1引数にhistoricalフォルダ、第2引数に`goldsharp_*.csv`があるMQL5 Filesフォルダを渡す。

```bat
scripts\gold_ml_v1\replay\run_goldsharp_live_source_preflight.bat "C:\path\to\gold_v3_2023_2026" "C:\path\to\MQL5\Files"
```

preflightは各timeframeについて次を保存する。

- historical / goldsharpのSHA256と行数
- 時刻昇順、重複、OHLC、spread監査
- historical最大時刻
- goldsharpの重複・backfill行数
- historical最大時刻より後のgoldsharp operational行数
- historical行の新規ライブシグナル対象数が0であること

出力:

- `outputs/gold_ml_v1/goldsharp_live_source_preflight/goldsharp_live_source_preflight.json`
- `outputs/gold_ml_v1/goldsharp_live_source_preflight/goldsharp_live_source_preflight.csv`

このpreflightは入力源分離の監査であり、live signal送信や注文は行わない。

## 終了コード

- 0: exact parity / preflight pass
- 1: input missingまたはinput contract違反
- 2: registry mismatch
- 3: metrics mismatch
- 4: environment/dependency/exception

## 現在の未完了点

GitHubへの実装は完了した。registry SHA、row count、metrics、PROV-020 / WATCH-021-A/B/C / WATCH-022-Bの親台帳派生一致は事前にPASSしている。

ユーザーPC上のhistoricalフォルダとliveフォルダは確認済みだが、この環境からユーザーPCのCドライブへアクセスできないため、historical raw replayとgoldsharp preflightの実行結果はまだ取得していない。PASSは実行結果を確認するまで主張しない。

## 境界

- MT5 server timeをJSTへ変更しない。
- 最新行をopen扱いで削除しない。
- HTFはbar close後のみ利用する。
- exact M1 entryがなければinvalid。
- 同一M1内TP/SLはSL優先。
- historical replayへgoldsharpを混ぜない。
- liveの新規判定足はgoldsharpだけ。
- historical backlogから新規シグナルを出さない。
- 2026を使った閾値調整は禁止。
- mismatchを自動修正せず、差分を保存する。
- audit-onlyを維持する。
