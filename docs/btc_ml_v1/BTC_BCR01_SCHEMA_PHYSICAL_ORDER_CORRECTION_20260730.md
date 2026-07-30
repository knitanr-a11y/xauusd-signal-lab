# BTC BCR01 — SQLite物理列順事故と修正

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T11:35:00+09:00`
- status: `BCR01_V100_INVALID_SCHEMA_ORDER_CHECK_CORRECTED_V101_RERUN_AUTHORIZED`

## 1. 初回提出物

提出ZIP:

`99_UPLOAD_PACKAGE(101).zip`

SHA256:

`47c38b81a465f1fa9adfbcd7901644cca8d3ab4f03f71cb9dd7353b368b602f1`

ZIPにはエラー用2ファイルだけが含まれていた。

- `00_READ_ME_FIRST.txt`
- `01_snapshot_error.json`

source snapshot、event ledger、候補結果、性能結果は作成されていない。

エラーJSONは次を明示している。

- `outcomes_opened=false`
- `performance_interpretation_performed=false`
- `source_runtime_modified=false`

したがって、初回runでfuture outcomeや性能情報が露出した事実はない。

## 2. 停止理由

BCR01 v1.0.0は`PRAGMA table_info(raw_alerts)`が返す物理列順と、fresh schemaで定義した論理export列順を完全一致比較していた。

active SQLite DBは、古いcollector schemaへ後から次の2列を`ALTER TABLE ADD COLUMN`したDBである。

- `event_key_origin`
- `worker_raw_json_origin`

SQLiteは追加列をtable末尾へ置く。そのため、必要な22列はすべて存在し、欠落・未知列もないのに、物理列順だけがfresh DBと異なった。

これはsource dataやCollectorの異常ではなく、BCR01の検証実装事故である。

## 3. 修正契約

BCR01 v1.0.1ではschemaを次のように検証する。

1. 必須列集合が完全一致すること
2. 欠落列が0であること
3. 未知列が0であること
4. 重複列が0であること
5. 列数が完全一致すること
6. 物理列順の差はmanifestへ記録すること
7. exportは常に凍結した論理列順を明示SELECTすること

つまり、migrationによる物理順差は許可するが、schema driftを緩めるわけではない。

## 4. 安全契約は不変

修正後も次は変わらない。

- SQLite URI `mode=ro`
- `PRAGMA query_only=ON`
- consistent read transaction
- allowlistは4tableのみ
- outcome-bearing tableをqueryしない
- raw DB、WAL、SHMをcopyしない
- Collector/M7Cを停止・再起動・変更しない
- candidate formulaを作らない
- WR/PF/DD/MFE/MAEを評価しない
- 異常時はerror ZIPを作って1回で停止

## 5. regression test

次の4テストを実行し、すべてPASSした。

1. fresh schema物理順で正常export
2. active DBと同じmigration後物理順で正常export
3. payload SHA不一致をfail-closed
4. 未知列追加をfail-closed

結果:

`4 passed`

## 6. 実装証拠

修正script commit:

`81ce359f919fba7b174ce2f8c5c25429b934ef2e`

script blob:

`34d2febf74e2d11dbdeb27f8fd68d2033311b9a8`

test commit:

`0da97025d2f2cef5b98f51523da9ffc98e3223a8`

test blob:

`0eda26243c8771314012658d02697d774adbca5e`

## 7. 次の実行

初回ZIPはsnapshot未作成の無効runであることが証明されたため、v1.0.1をpullした後の置換runを1回だけ許可する。

同じBATを使用する。

`scripts/btc_ml_v1/BCR01_outcome_blind_source_snapshot/01_run_BCR01.bat`

実行後は最初に生成された`LATEST/99_UPLOAD_PACKAGE.zip`を提出し、それ以上繰り返さない。

Collector/M7Cはそのまま稼働継続する。
