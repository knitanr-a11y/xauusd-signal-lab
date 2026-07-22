# MOCHIPOYO Alert Research 次チャット引き継ぎ V2

## 0. この文書が正式

repo: `knitanr-a11y/xauusd-signal-lab`

branch: `feature/mochipoyo-alert-research`

このV2文書を正式な次チャット入口とする。

旧文書

`docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M7C_24_SUPPORTED_CONTINUE_TO_FORMAL_GATE_20260722.md`

の「説明上の01〜06」解釈は誤りであり、ファイル整理方針として使用しない。

追加で読む順番:

1. `config/mochipoyo_alert_research/current_state_20260722.json`
2. `config/mochipoyo_alert_research/next_action_20260722.json`
3. `config/mochipoyo_alert_research/objective_coverage_plus_value_add_20260722.json`
4. `docs/mochipoyo_alert_research/FILE_ORGANIZATION_AND_NUMBERING_CONVENTION_20260722.md`

## 1. 現在の正式状態

status:

`M7C_VALID_FORWARD_COLLECTION_24_SUPPORTED_EVENTS_CONTINUE_AUDIT_ONLY`

stage:

`M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY`

有効なprospective start:

`2026-07-20T14:54:15Z`

この時刻とruntime manifestは固定済み。変更、削除、再作成、再初期化しない。

ユーザーのローカルでは次の2プロセスが別ウィンドウで稼働中。

- Cloudflare collector: 60秒間隔
- M7C prospective shadow: 300秒間隔

チャット切替だけを理由に停止・再起動しない。

最新確認時点:

- M7C status: `RUNNING`
- cycles: 488
- successful cycles: 488
- failed cycles: 0
- last exit code: 0

## 2. 最新forward snapshot

- prospective開始後source event: 26
- M7C正式対応対象: 24
- unsupported REENTRY: 2
- scored source event: 24
- exact match: 15
- within one M15 bar: 17
- missed source: 7
- wrong transition nearby: 0
- finalized extra proxy signal: 24
- pending grace extra: 0

recall:

- exact: 15/24 = 62.5%
- within one M15 bar: 17/24 = 70.8333%

銘柄別:

- BTCUSD: 13
- XAUUSD: 11

transition別:

- PRIMARY_LONG: 10
- PRIMARY_SHORT: 2
- LONG_EXIT: 10
- SHORT_EXIT: 2

正式レビュー条件:

- supported source events >= 30: あと6
- BTCUSD >= 10: 達成
- XAUUSD >= 10: 達成
- PRIMARY_LONG >= 5: 達成
- PRIMARY_SHORT >= 5: あと3
- total EXIT >= 10: 達成

総数30とPRIMARY_SHORT 5を含む全条件到達までM7Cを変更しない。

## 3. ユーザーの最終目標

完全複製だけを最終目標にしない。

優先順位:

1. 対応可能なもちぽよsourceアラートをできるだけ取りこぼさない
2. 独自の追加アラートが増えることは許容する
3. source matchedとextra candidateを分けて評価する
4. extra candidateの中から負けやすいものを発生時点情報だけで削減する
5. source matchedアラートをextra用gateで黙って消さない

分類:

- `SOURCE_MATCHED`
- `MISSED_SOURCE`
- `EXTRA_CANDIDATE`
- `EXTRA_ACCEPTED`
- `EXTRA_REJECTED`

現在のextra 24件は24トレードではない。ENTRYとEXITを含むsignal数であり、勝敗・PF・DDは未評価。

## 4. M7C凍結契約

収集中は変更禁止:

- KERNEL-L1
- KERNEL-S1
- EXIT-L0
- EXIT-S0
- thresholds
- grace period
- exact/within-one-bar matching
- one-to-one matching
- runtime manifest
- prospective start
- review gates

凍結式:

- PRIMARY_LONG: `IDLE AND rci9_turn_up AND BULLISH_STACK`
- PRIMARY_SHORT: `IDLE AND rci9_turn_down AND BEARISH_STACK`
- LONG_EXIT: `ACTIVE_LONG AND rci9 >= 78.333333333333`
- SHORT_EXIT: `ACTIVE_SHORT AND rci9 <= -75`
- REENTRY: `NOT_MODELED_OR_SCORED`

因果契約:

- M15
- 新M15バー開始時に判定
- 直前の完全確定M15特徴だけ使用
- current M15はopenだけ使用可
- current high/low/close禁止
- future bars禁止
- outcome、MFE、MAE、PF、win/loss禁止
- historical replay禁止
- cross-timeframe candidate extraction禁止

安全状態:

- audit-only: ON
- Discord send: OFF
- MT5 order: OFF
- live ready: OFF
- final signal: OFF
- entry gate: OFF

## 5. ファイル整理・番号付けの正しい意図

ユーザーの要望は、説明に番号を付けることではない。

**これから新しく作る実行ファイルとユーザー向け出力ファイルの実ファイル名そのものへ番号を付け、同じStageの専用フォルダへまとめること。**

既存M7Cファイルはもう変更しない。番号付け目的でrename、移動、停止、再生成しない。

M8A以降で新しく作るものから適用する。

必須ルール:

- ユーザー操作用BATは同じStageの`operator`フォルダへ集約
- 実ファイル名を `00_`、`01_`、`02_` の順で番号付け
- 同じ実行のJSON、CSV、LOGは1つのrunフォルダへ集約
- ユーザー向け出力の実ファイル名も番号付け
- `00_READ_ME_FIRST.txt`を置く
- 通常提出用には`99_UPLOAD_PACKAGE`フォルダまたはZIPを作る
- 複数フォルダから似た名前のファイルを探させない
- 必要ファイルを後から小分けに要求しない

例:

```text
scripts/mochipoyo_alert_research/m8a/operator/
  00_READ_ME_FIRST.txt
  01_run_prepare_inputs.bat
  02_run_coverage_audit.bat
  03_open_results.bat
```

```text
outputs/mochipoyo_alert_research/M8A/<run_id>/
  00_READ_ME_FIRST.txt
  01_summary.json
  02_status.json
  03_source_matched.csv
  04_missed_source.csv
  05_extra_candidates.csv
  06_audit.log
  99_UPLOAD_PACKAGE/
```

詳細契約:

`docs/mochipoyo_alert_research/FILE_ORGANIZATION_AND_NUMBERING_CONVENTION_20260722.md`

## 6. 現在のM7Cで提出する既存ファイル

現行M7Cは既存名称のまま継続する。

正式条件到達時に次の7ファイルを一括提出してもらう。

場所:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\m7c`

必要ファイル:

1. `latest_m7c_prospective_shadow.json`
2. `latest_m7c_shadow_loop_status.json`
3. `latest_m7c_source_event_comparisons.csv`
4. `latest_m7c_extra_proxy_signals.csv`
5. `latest_m7c_proxy_signals.csv`
6. `latest_m7c_proxy_decisions.csv`
7. `m7c_shadow_forever.log`

collector障害時だけ追加:

- `collector_forever.log`
- `latest_loop_status.json`
- `latest_collection_result.json`

## 7. 正式条件到達後の順番

1. 現行7ファイルを固定保存
2. M7C manual review
3. M8A coverage gap audit
4. M8B extra signal outcome audit
5. M8C extra loss reduction gate shadow
6. M8D incremental portfolio review

M8A以降の新規実行ファイル・出力ファイルから、実ファイル名番号付けと専用フォルダ集約を適用する。

## 8. 停止・異常条件

次の場合はM7Cを止め、勝手に再初期化せず原因調査する。

- exit code 2
- statusが`COLLECTING`以外のcontract block/error
- prospective_start_utcが`2026-07-20T14:54:15Z`から変化
- failed_cycles > 0
- start以前のlate event検出
- runtime manifest mismatch
- collector停止・失敗
- 明確な新source alertがあるのにcursorが進まない

M7C停止時もcollectorは原則継続する。

## 9. 絶対禁止

- チャット切替だけでcollectorやM7Cを停止しない
- runtime initializerを再実行しない
- runtime manifestを削除・上書き・再作成しない
- prospective startを変更しない
- 正式件数を0からやり直さない
- M7C途中でformula、threshold、grace、matchingを変更しない
- extraを自動失敗扱いしない
- 勝敗未評価のextraを有用と主張しない
- source matchedをextra用gateで黙って消さない
- REENTRYを現在の正式recallへ混ぜない
- future leakageを使わない
- Discord、MT5 order、live ready、final signalを有効化しない
- 新規ファイルで説明上だけ番号を付ける
- 新規出力を複数フォルダへ散らしユーザーに探させる

## 10. 次チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

MOCHIPOYO Alert Researchの続きです。

最初に次のV2引き継ぎ文を最初から最後まで読んでください。

docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M7C_24_SUPPORTED_CONTINUE_TO_FORMAL_GATE_V2_20260722.md

旧V1引き継ぎ文の「説明上の01〜06」解釈は使わないでください。

現在、Cloudflare collectorとM7C prospective shadowはローカルで別ウィンドウ稼働中です。チャット切替だけで停止・再起動・runtime再初期化しないでください。

有効なprospective_start_utcは2026-07-20T14:54:15Zです。runtime manifestを触らず、正式24件から継続してください。

正式レビューは、supported source events 30以上、PRIMARY_SHORT 5以上を含む全gate到達後です。現在は総数あと6件、PRIMARY_SHORTあと3件です。

最終目標は、もちぽよsourceのcoverageを基準にし、追加アラートを許容し、後工程で追加分の負けを削減することです。

ファイル整理のユーザー意図は、説明に番号を付けることではありません。既存M7Cファイルは変更せず、M8A以降で新しく作る実行ファイルとユーザー向け出力ファイルの実ファイル名へ番号を付け、同じStageの専用フォルダへまとめてください。提出用には1つの99_UPLOAD_PACKAGEを作ってください。

必要ファイルを後から小分けに要求しないでください。

audit-only継続です。Discord send、MT5 order、live ready、final signal、entry gateはすべてOFFです。
```
