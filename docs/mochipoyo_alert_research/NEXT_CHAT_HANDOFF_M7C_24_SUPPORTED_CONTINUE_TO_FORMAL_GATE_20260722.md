# MOCHIPOYO Alert Research 次チャット引き継ぎ

## 0. 最初に読むこと

repo: `knitanr-a11y/xauusd-signal-lab`

branch: `feature/mochipoyo-alert-research`

この文書を最初から最後まで読み、記載された現在地から続けること。

追加で読むファイルは次の順番に限定する。

1. `config/mochipoyo_alert_research/current_state_20260722.json`
2. `config/mochipoyo_alert_research/next_action_20260722.json`
3. `config/mochipoyo_alert_research/objective_coverage_plus_value_add_20260722.json`
4. `docs/mochipoyo_alert_research/OPERATOR_NUMBERED_RUN_FILES_AND_HANDOFF_CONVENTION_20260720.md`
5. 必要な場合だけM7C実装・manifest・最新添付結果を確認する

過去の無効なpre-catchup M7C開始結果を正式forward evidenceとして再利用しない。

---

## 1. 現在の正式状態

status:

`M7C_VALID_FORWARD_COLLECTION_24_SUPPORTED_EVENTS_CONTINUE_AUDIT_ONLY`

stage:

`M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY`

現在の有効なprospective start:

`2026-07-20T14:54:15Z`

この時刻は固定済みであり、変更・再作成・初期化しない。

ユーザーのローカルでは、次の2プロセスが別ウィンドウで稼働中。

- Cloudflare collector: 60秒間隔
- M7C prospective shadow: 300秒間隔

チャット切替だけを理由に停止・再起動・再初期化してはいけない。

最新確認時点のM7C loop:

- status: `RUNNING`
- cycles: `488`
- successful_cycles: `488`
- failed_cycles: `0`
- last_exit_code: `0`

---

## 2. 最新forward snapshot

最新レポート時刻:

`2026-07-22T07:55:44Z`

| 項目 | 件数 |
|---|---:|
| prospective開始後のsource event | 26 |
| M7C正式対応対象 | 24 |
| unsupported REENTRY | 2 |
| scored source event | 24 |
| 完全一致 | 15 |
| 1本以内一致 | 17 |
| 取りこぼし | 7 |
| wrong transition nearby | 0 |
| 確定extra proxy signal | 24 |
| grace保留中extra | 0 |

recall:

- exact recall: `15 / 24 = 62.5%`
- within-one-M15-bar recall: `17 / 24 = 70.8333%`

銘柄別:

- BTCUSD: 13
- XAUUSD: 11

transition別:

- PRIMARY_LONG: 10
- PRIMARY_SHORT: 2
- LONG_EXIT: 10
- SHORT_EXIT: 2

正式レビュー条件の現在地:

- supported source events 30以上: 未達、あと6件
- BTCUSD 10以上: 達成
- XAUUSD 10以上: 達成
- PRIMARY_LONG 5以上: 達成
- PRIMARY_SHORT 5以上: 未達、あと3件
- EXIT合計10以上: 達成

したがって、現時点ではまだ

`INSUFFICIENT_FORWARD_SAMPLE`

であり、M7Cを変更せず継続する。

---

## 3. ユーザーが確定した最終目標

完全再現そのものを最終目標にしない。

正式な優先順位は次の通り。

1. 対応可能なもちぽよsourceアラートをできるだけ取りこぼさない
2. 独自の追加アラートが増えることは許容する
3. 追加アラートはsource再現アラートと別枠で評価する
4. 追加分の中から負けやすいものを発生時点情報だけで削減する
5. sourceに対応したアラートを、追加分の負け削減フィルターで黙って消さない

分類を必ず分ける。

- `SOURCE_MATCHED`: もちぽよsourceに対応したproxy transition
- `MISSED_SOURCE`: 対応対象sourceをproxyが拾えなかったもの
- `EXTRA_CANDIDATE`: source一致がない追加proxy signal。自動失敗ではない
- `EXTRA_ACCEPTED`: 別forwardまたはfrozen walk-forwardで有用性を確認した追加候補
- `EXTRA_REJECTED`: 発生時点情報だけのgateにより不採用となった追加候補

現在の24件のextraは24トレードを意味しない。ENTRYとEXITを含むsignal数であり、まだ勝敗・PF・DD評価は未実施。

---

## 4. M7Cの凍結契約

M7C収集中は次を変更しない。

- KERNEL-L1
- KERNEL-S1
- EXIT-L0
- EXIT-S0
- threshold
- grace period
- exact/within-one-bar matching rule
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
- 直前の完全確定M15特徴だけを使用
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

---

## 5. 実行ファイルと実行順

### 重要

以下の番号は正式な操作番号。

物理ファイルは現在まだ安全移行前の旧名称である。番号付き物理ファイル名を存在するものとして案内してはいけない。

次の安全なstage切替時には、呼び出し元・文書・停止処理を同時修正して物理ファイル名も番号付きへ移行する。

### 01 — collector常時実行

現在の物理ファイル:

`scripts/mochipoyo_alert_research/run_collect_events_cloudflare_forever.bat`

将来の番号付き物理名:

`01_run_collect_events_cloudflare_forever.bat`

役割:

- Cloudflareからraw alertを収集
- 60秒間隔
- M7Cとは別ウィンドウで常時実行

現在稼働中なら、チャット切替時に触らない。

### 02 — runtime初期化・1回限定

現在の物理ファイル:

`scripts/mochipoyo_alert_research/run_initialize_m7c_prospective_shadow_runtime_once.bat`

将来の番号付き物理名:

`02_run_initialize_m7c_prospective_shadow_runtime_once.bat`

**現在は実行禁止。**

有効なruntime manifestは既に作成済み。再実行すると前向き開始点を壊すため、勝手に実行しない。

### 03 — M7C one-shot確認

現在の物理ファイル:

`scripts/mochipoyo_alert_research/run_build_m7c_prospective_shadow_once.bat`

将来の番号付き物理名:

`03_run_build_m7c_prospective_shadow_once.bat`

通常継続中は実行不要。停止原因調査や、明示的なone-shot確認時だけ使用する。

### 04 — M7C常時実行

現在の物理ファイル:

`scripts/mochipoyo_alert_research/run_m7c_prospective_shadow_forever.bat`

将来の番号付き物理名:

`04_run_m7c_prospective_shadow_forever.bat`

役割:

- 300秒間隔でM7C監査
- collectorとは別ウィンドウで常時実行
- contract exit code 2でfail-closed停止

現在稼働中なら、チャット切替時に触らない。

### 05 — M7C停止専用

現在の物理ファイル:

`scripts/mochipoyo_alert_research/stop_m7c_prospective_shadow_forever.bat`

将来の番号付き物理名:

`05_stop_m7c_prospective_shadow_forever.bat`

正常収集中は使わない。明示的停止または異常調査時のみ使用。

### 06 — ログフォルダを開く

現在の物理ファイル:

`scripts/mochipoyo_alert_research/open_mochipoyo_monitor_folders.bat`

将来の番号付き物理名:

`06_open_mochipoyo_monitor_folders.bat`

任意。collector、M7C、derivedの各フォルダを開く。

---

## 6. ローカル保存先

runtime manifest:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\m7c_runtime\m7c_prospective_shadow_manifest_runtime.json`

collector logs:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\collector`

M7C logs:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\m7c`

derived logs:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\derived`

---

## 7. 次に提出してもらうファイル

### 正式条件到達時に最初から一括で必要

次チャットでは後から小分けに要求しない。最初に次の7ファイルを案内する。

1. `latest_m7c_prospective_shadow.json`
2. `latest_m7c_shadow_loop_status.json`
3. `latest_m7c_source_event_comparisons.csv`
4. `latest_m7c_extra_proxy_signals.csv`
5. `latest_m7c_proxy_signals.csv`
6. `latest_m7c_proxy_decisions.csv`
7. `m7c_shadow_forever.log`

場所:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\m7c`

### collector障害がある場合だけ追加

1. `collector_forever.log`
2. `latest_loop_status.json`
3. `latest_collection_result.json`

collectorが正常なら毎回要求しない。

### runtime receipt

`m7c_runtime_start_receipt.json`は通常の定期確認では不要。prospective startやmanifestの整合に疑義が出た場合だけ要求する。

---

## 8. 次の正式レビュー開始条件

次の全条件が揃うまでM7Cを変更せず収集する。

- supported source events >= 30
- BTCUSD >= 10
- XAUUSD >= 10
- PRIMARY_LONG >= 5
- PRIMARY_SHORT >= 5
- total EXIT >= 10

現在不足:

- supported source events: あと6
- PRIMARY_SHORT: あと3

30件だけ到達してPRIMARY_SHORTが5未満なら、まだ正式レビューを開始しない。

PRIMARY_SHORTが5件に到達しても総数30未満なら、まだ正式レビューを開始しない。

---

## 9. 正式条件到達後の順番

### M7C manual review

最初に最新ファイルを固定保存し、次を監査する。

- SOURCE_MATCHED
- MISSED_SOURCE
- unsupported REENTRY
- EXTRA_CANDIDATE
- exact match
- within-one-bar match
- ticker別
- transition別
- state-machine連鎖

exact proprietary formulaを再現したと自動主張しない。

### M8A — Coverage Gap Audit

取りこぼしを調査する。

- outcomeを使わず、発生時点情報だけでcoverage拡張候補を設計
- recall優先
- 現在のM7Cサンプルに後付けで式を変更しない

### M8B — Extra Signal Outcome Audit

extra candidateの時刻を先に固定してから、将来結果を別工程で評価する。

- transaction costsを含める
- outcomeを見て過去の発火時刻を変えない
- source matchedとextraを混ぜない

### M8C — Extra Loss Reduction Gate Shadow

追加候補だけを対象に、発生時点情報で負けやすいものを削減する。

source matchedを黙って消すgateにしない。

### M8D — Incremental Portfolio Review

次の3構成を比較する。

1. source-anchor only
2. source-anchor + all extras
3. source-anchor + accepted extras after loss-reduction gate

評価項目:

- 件数
- 勝率
- cost込みPF
- 純利益
- DD
- 最大連敗
- ticker別
- LONG/SHORT別
- source matchedとextraの寄与分解

---

## 10. 停止・異常条件

次の場合はM7Cを止め、勝手に再初期化せず原因調査する。

- exit code 2
- `COLLECTING`以外のcontract block/error
- `prospective_start_utc`が`2026-07-20T14:54:15Z`から変化
- failed_cycles > 0
- prospective start以前のlate event検出
- runtime manifest mismatch
- collector停止・失敗
- 明確な新source alertがあるのにcollector cursorが進まない

M7Cが止まってもcollectorは原則別プロセスで継続する。

---

## 11. ユーザー自身のWebhook誤送信について

ユーザーは、同じWebhookへ自分のアラートを一度送ったと報告した。

- 送信は当時のraw ID 75より後
- message/bodyは空または不足
- 当時確認したcollector snapshotでは新しい保存行を特定できなかった
- 具体的なraw rowの証拠はない

したがって、推測でIDを除外してはいけない。

除外する場合は、保存行の時刻・ticker・event・payloadなどの具体的証拠を特定し、annotationとして監査可能に除外する。

runtime manifestや正式開始点を作り直す理由にはしない。

---

## 12. 絶対禁止

- チャット切替だけでcollectorやM7Cを停止しない
- runtime initializerを再実行しない
- runtime manifestを削除・上書き・再作成しない
- prospective startを変更しない
- 正式件数を0からやり直さない
- M7C途中でformula、threshold、grace、matchingを変更しない
- extraを自動失敗扱いしない
- extraの有用性を勝敗未評価のまま主張しない
- 取りこぼし改善と追加分の負け削減を同じgateに混ぜない
- source matchedアラートを黙って削るentry gateを作らない
- REENTRYを現在の正式recallに混ぜない
- future leakageを使わない
- Discord send、MT5 order、live ready、final signalを有効化しない
- ユーザーに必要ファイルを後出しで小分けに要求しない
- 実在しない番号付き物理ファイル名を実行するよう案内しない

---

## 13. 次チャット開始用プロンプト

以下を次チャットの最初に貼る。

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

MOCHIPOYO Alert Researchの続きです。

最初に次のGitHub文書を最初から最後まで読んでください。

docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M7C_24_SUPPORTED_CONTINUE_TO_FORMAL_GATE_20260722.md

次に文書内で指定されたcurrent_state、next_action、objective contractだけを順番どおり確認してください。

現在、Cloudflare collectorとM7C prospective shadowはユーザーのローカルで別ウィンドウ稼働中です。
チャット切替だけを理由に停止・再起動・runtime再初期化しないでください。

有効なprospective_start_utcは2026-07-20T14:54:15Zです。
runtime manifestの削除・再作成・上書きは禁止です。
正式件数を0からやり直さないでください。

最新確認時点:
- supported source events: 24
- exact match: 15
- within one M15 bar: 17
- missed: 7
- unsupported REENTRY: 2
- extra proxy signals: 24
- BTCUSD: 13
- XAUUSD: 11
- PRIMARY_LONG: 10
- PRIMARY_SHORT: 2
- LONG_EXIT: 10
- SHORT_EXIT: 2
- M7C successful cycles: 488
- failed cycles: 0

正式レビューは、総数30以上かつPRIMARY_SHORT 5以上を含む全gate到達後です。
現在はM7Cを変更せず継続してください。

最終目標は完全複製だけではありません。
もちぽよsourceの取りこぼしを減らすことを基準にし、独自の追加アラートは許容し、後工程で追加分の負けを削減します。
source matched、missed source、extra candidateを必ず別評価してください。

実行ファイルの説明では必ず01〜06の番号を先頭に付け、現在の物理旧名と将来の番号付き名を混同しないでください。
必要提出ファイルは最初から一括で明記し、後出しで小分け要求しないでください。

audit-only継続です。
Discord send、MT5 order、live ready、final signal、entry gateはすべてOFFです。
```

---

## 14. 次チャットの最初の返答に求めること

次チャットは文書を読んだ後、まず次だけを簡潔に確認する。

1. 現在の2プロセスを止めない
2. runtime manifestを触らない
3. M7Cを24件から継続する
4. 正式gateまであと6件、PRIMARY_SHORTあと3件
5. 最終目標はcoverage anchor + useful extras + losing-extra reduction
6. 次に必要なファイルと提出タイミングを理解した

この確認前に実装や再初期化を始めない。
