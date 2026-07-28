# BTC ML V1 ファイル整理・番号付け契約

Date: 2026-07-29  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Active research branch: `feature/mochipoyo-alert-research`

## 1. 目的

ユーザーがファイルを探し回らず、各Stageの `bat` フォルダを開いて番号順に操作できる状態を維持する。

今後新しく作るBTC ML V1のStageでは次を徹底する。

- 内部Pythonとユーザー操作用BATを別フォルダに置く
- ユーザーが起動するBATの実ファイル名へ `01_`、`02_`、`03_` の番号を付ける
- `00_READ_ME_FIRST.txt` に実行順、実行回数、成功表示、停止条件、提出物を明記する
- 最新結果は常に `LATEST` へまとめる
- 過去結果は実行時刻別の `archive` に保存する
- 通常提出物は `99_UPLOAD_PACKAGE.zip` 1個へまとめる
- 提出物を作る実行BATは、成功後に同じBATから `LATEST` フォルダを自動で開く
- エラー、BLOCKED、FAILED時は `pause` してコマンド画面を残し、メッセージを確認できるようにする
- リポジトリ直下へ新しいBTC研究BATを置かない

説明上だけ番号を付け、実ファイル名には番号を付けない運用は禁止する。

## 2. もちぽよアラート研究との分離

`mochipoyo_alert_research` と `btc_ml_v1` は同じリポジトリ・同じ作業ブランチ内に存在するが、研究正本は別である。

- `mochipoyo_alert_research`: もちぽよ由来のgenuine source、proxy、M7C/M8C等のmulti-asset forward研究
- `btc_ml_v1`: BTC4/BTC5/BTC6/BTC7R/BTC9R stacking・availability・候補別評価研究

現在の正式作業ブランチは `feature/mochipoyo-alert-research` である。フォルダを分離することは、作業ブランチを `main` へ変更することを意味しない。ブランチ変更はユーザーの明示指示なしに行わない。

Stage 01のPythonが出力する `INFERRED_WITH_MAIN_LOGIC` およびコードコメント内の `current-main` は、既存BTC関数の由来・再利用契約を示す固定表現であり、実行対象ブランチが `main` であることを意味しない。

禁止:

- 整理目的だけで、稼働中のもちぽよcollectorやM7C/M8C/M9V/M9Yを停止、移動、rename、resetする
- BTC ML V1のStageを `scripts/mochipoyo_alert_research` 配下へ新規追加する
- もちぽよ/GOLDの候補条件、payoff、runnerルールをBTC ML V1へ根拠なく移植する
- BTC ML V1の候補条件をもちぽよ側へ自動反映する
- ユーザー確認なしに作業ブランチを `main` へ変更する

フォルダ操作体系は共通化するが、研究データ、契約、候補定義、prospective start、runtime stateは統合しない。

## 3. 新しいStageの標準構成

```text
scripts/btc_ml_v1/<stage_name>/
  python/
    <internal_implementation>.py

  bat/
    00_READ_ME_FIRST.txt
    01_<first_action>.bat
    02_<second_action_or_open_results>.bat
```

### pythonフォルダ

- 内部実装専用
- ユーザーへ直接起動を指示しない
- Pythonファイルへの番号付けは不要
- BATから正確な相対パスで呼び出す

### batフォルダ

- ユーザーが操作するファイルだけを置く
- 実行順がエクスプローラー上で分かる番号付き名称にする
- 同じStage内へ似た意味の無番号BATを重複作成しない
- エラー、BLOCKED、FAILED、必要出力欠落、結果フォルダopen失敗の各経路では、エラー内容を表示して `pause` 後に終了する
- 提出物を生成する主実行BATは、成功後に `LATEST` を自動で開く
- 結果再表示用BATは、後から `LATEST` を開き直す補助導線として残してよい
- `00_READ_ME_FIRST.txt` に次を必ず書く
  - 起動する番号と順番
  - 1回だけか常時実行か
  - 同時実行の可否
  - 成功表示
  - BLOCKED/FAILED時の停止条件
  - エラー時に画面が残ること
  - 成功後にどのBATが結果フォルダを開くか
  - `LATEST` の場所
  - 提出するファイル

## 4. 出力構成

新しいBTC ML V1 Stageのユーザー向け出力は、原則として次へ置く。

```text
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\<NN_stage_name>\
  LATEST\
    00_READ_ME_FIRST.txt
    01_summary.json
    02_report.txt
    03_<main_detail>.csv        # 必要なStageのみ
    04_<supporting_detail>.csv  # 必要なStageのみ
    99_UPLOAD_PACKAGE.zip

  archive\
    <UTC execution timestamp>\
      00_READ_ME_FIRST.txt
      01_summary.json
      02_report.txt
      03_<main_detail>.csv
      04_<supporting_detail>.csv
      99_UPLOAD_PACKAGE.zip
```

### LATEST

- 常に最新の完了結果だけを置く
- ユーザーには通常 `LATEST` だけを案内する
- 提出物生成が成功したら、主実行BATから自動で開く
- `02_open_latest_results.bat` 等で後から直接開き直せるようにする
- 更新前の結果は `archive` に残す

### archive

- 過去結果を実行時刻別に保存する
- 通常操作ではユーザーに探させない
- 再現監査や差分調査時だけ使用する

## 5. 出力ファイル名

基本順序:

```text
00_READ_ME_FIRST.txt
01_summary.json
02_report.txt
03_主要明細.csv
04_補助明細.csv
99_UPLOAD_PACKAGE.zip
```

ルール:

- ファイル名だけで用途が分かる短い役割名を付ける
- 同じ意味の `latest_...`、`result_...`、`final_...` を乱立させない
- `00_READ_ME_FIRST.txt` にStage、実行日時、commit、各ファイルの意味、提出対象を記載する
- ZIPに含まれない追加ファイルを後から小分けで要求しない
- 生ローソク足CSVを提出ZIPへ含めない

## 6. 既存runtimeの扱い

この契約は、2026-07-29以降に新しく作るBTC ML V1 Stageへ適用する。

既存のBTC operational runtime、Discord/demo関連、永続state、既存BAT、既存ログは、整理目的だけでrename、移動、再生成しない。変更が必要な場合は、参照先、起動契約、永続state、再起動手順を別途精査したうえで行う。

## 7. Stage 01の正式配置

Fresh-forward availability audit:

```text
scripts/btc_ml_v1/fresh_forward_availability/
  python/
    audit_btc_fresh_forward_availability.py

  bat/
    00_READ_ME_FIRST.txt
    01_run_availability_audit.bat
    02_open_latest_results.bat
```

Output:

```text
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\
  LATEST\
    00_READ_ME_FIRST.txt
    01_availability_summary.json
    02_availability_report.txt
    99_UPLOAD_PACKAGE.zip
  archive\
    <UTC execution timestamp>\
```

Stage 01はavailability read-onlyであり、fresh performance evaluator、candidate engine、reproduction、collector、Discord、MT5 order、live-ready、final-signalを実行しない。

`01_run_availability_audit.bat` は、成功後に同じBATから `LATEST` を自動で開く。エラーまたは出力欠落時は `pause` して画面を残す。`02_open_latest_results.bat` は、提出時または後日の確認時に `LATEST` を開き直す補助BATであり、エラー時は同様に画面を残す。

## 8. 今後の引き継ぎ必須事項

BTC ML V1の引き継ぎには次を記載する。

- 現在のbranchと基準commit
- 現在のStage番号とStage名
- ユーザーが起動する番号付きBATの正確な場所
- 起動順と実行回数
- 成功後に結果フォルダを開くBAT
- エラー時に画面が残ること
- `LATEST` の正確な場所
- `99_UPLOAD_PACKAGE.zip` の正確な場所
- 成功表示と停止条件
- 既存runtimeを変更したか否か
- もちぽよ/GOLD研究を変更したか否か
- 次Stageを開始してよい条件
