# MOCHIPOYO Alert Research ファイル整理・番号付け契約

## 1. ユーザーの意図

ユーザー側の操作はBATを起動するだけである。

似た名前のファイルを探さなくて済むように、今後新しく作るStageでは次を徹底する。

- 内部Pythonとユーザー操作用BATを別フォルダに分ける
- ユーザーが起動するBATだけ、実ファイル名の先頭に `01_`、`02_`、`03_` の番号を付ける
- 指示では「batフォルダの02を起動」のように番号を中心に案内する
- 出力は1か所へまとめ、最新結果と提出物をすぐ見つけられるようにする

説明文だけに番号を付ける運用は禁止する。

## 2. 適用範囲

この契約は、2026-07-22以降に新しく作成するStage、実行ファイル、ユーザー向け出力へ適用する。

現在稼働中のM7C既存ファイルは変更しない。既存M7CのBAT、Python、ログ、CSV、JSONを、整理目的だけでrename、移動、再生成しない。

## 3. 新しいStageのフォルダ構成

新しいStageでは、内部処理とユーザー操作を次のように分離する。

```text
scripts/mochipoyo_alert_research/m8a/
  python/
    prepare_inputs.py
    run_coverage_audit.py
    build_upload_package.py

  bat/
    00_READ_ME_FIRST.txt
    01_prepare_inputs.bat
    02_run_coverage_audit.bat
    03_open_latest_results.bat
```

### pythonフォルダ

- 内部実装専用
- ユーザーへ直接実行を指示しない
- Pythonファイルへの番号付けは不要
- BATから相対パスで呼び出す

### batフォルダ

- ユーザーが触るファイルだけを置く
- BATの実ファイル名へ実行順の番号を付ける
- エクスプローラーで上から順に並ぶようにする
- `00_READ_ME_FIRST.txt`には、現在起動してよい番号と実行禁止の番号を明記する
- 起動、停止、確認、結果表示のBATを同じフォルダへまとめる
- 似た名前の無番号BATを同じStage内に重複して作らない

## 4. ユーザーへの実行指示

ユーザーへの通常指示は、長いPython名や内部パスを並べない。

例:

```text
M8Aのbatフォルダを開き、02_run_coverage_audit.batを起動してください。
```

または、既にフォルダが開いている場合:

```text
02を起動してください。
```

必ず次も併記する。

- 起動する番号
- 1回だけか常時実行か
- 同時に起動するBATがあるか
- どの表示で成功か
- どの表示なら停止するか

## 5. 出力ファイルの整理

各Stageのユーザー向け出力は、次の1か所へまとめる。

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8A\
  LATEST\
    00_READ_ME_FIRST.txt
    01_summary.json
    02_status.json
    03_source_matched.csv
    04_missed_source.csv
    05_extra_candidates.csv
    06_audit.log
    99_UPLOAD_PACKAGE.zip

  archive\
    20260722_180000\
      00_READ_ME_FIRST.txt
      01_summary.json
      02_status.json
      03_source_matched.csv
      04_missed_source.csv
      05_extra_candidates.csv
      06_audit.log
      99_UPLOAD_PACKAGE.zip
```

### LATESTフォルダ

- 常に最新結果だけを置く
- ユーザーには原則このフォルダだけを案内する
- `03_open_latest_results.bat`で直接開けるようにする
- 結果更新時は中身を安全に更新する

### archiveフォルダ

- 過去結果を実行日時ごとに保存する
- ユーザーへ通常は探させない
- 再現監査や差分調査時だけ使う

## 6. 出力ファイル名

ユーザーが確認または提出する出力は、実ファイル名へ番号を付ける。

基本順序:

```text
00_READ_ME_FIRST.txt
01_summary.json
02_status.json
03_主要明細.csv
04_補助明細.csv
05_追加候補.csv
06_audit.log
99_UPLOAD_PACKAGE.zip
```

ルール:

- 番号の後ろに短く明確な役割名を付ける
- 同じ意味の `latest_...`、`result_...`、`final_...` を乱立させない
- `00_READ_ME_FIRST.txt`にStage、実行日時、commit、各ファイルの意味、提出対象を記載する
- 通常提出物は `99_UPLOAD_PACKAGE.zip` 1個にまとめる
- ZIPに入っていない追加ファイルを後から小分けで要求しない

## 7. 引き継ぎ文の必須記載

今後の引き継ぎ文には、次を明記する。

- 現在稼働中の既存Stageは変更しないこと
- 次に新しく作るStageから `python` と `bat` を分離すること
- ユーザーが起動する番号付きBATの正確な名前
- 起動する番号と順番
- 出力の `LATEST` フォルダの正確な場所
- `99_UPLOAD_PACKAGE.zip`の正確な場所
- 提出タイミング
- 成功表示と停止条件

禁止:

- Pythonファイルをユーザーに探させる
- BATとPythonを同じフォルダへ混在させる
- 説明上だけ番号を付ける
- ユーザーに似た名前の出力を複数フォルダから探させる
- 必要ファイルを後から小分けに追加要求する

## 8. 現在のM7Cへの扱い

現在のM7Cは有効なprospective collection中であるため、整理のためだけに停止、rename、移動、再初期化しない。

この契約は、M7C正式レビュー後に新しく作るM8A以降の実行構成と出力構成から適用する。
