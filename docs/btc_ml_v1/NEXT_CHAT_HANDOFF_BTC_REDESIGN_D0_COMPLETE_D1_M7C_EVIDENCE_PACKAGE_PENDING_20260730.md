# BTC候補研究 次チャット完全引き継ぎ

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T06:31:00+09:00`
- status: `BTC_REDESIGN_D0_COMPLETE_D1_M7C_EVIDENCE_PACKAGE_PENDING_READ_ONLY`
- authority: `LATEST_DATED_HANDOFF`

## 0. この文書が現在の完全引き継ぎ

この文書は、BTC候補研究の現在地を新しいチャットへ引き継ぐための最新版である。

新しいチャットは、検索結果、古いhandoff、会話記憶、default branchから開始してはならない。必ずrepo直下の次の固定入口を最初に読む。

`START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`

固定入口がこの文書を最新版として指していることを確認してから続行する。

## 1. branch hard gate

必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

禁止:

- `main`を現在状態として読む
- default branchから同名ファイルを読む
- 別branchで実装、文書更新、候補研究を続ける
- branch不明時に記憶や類似ファイルで補う

branchが取得できない、または固定入口とこの文書が矛盾する場合は停止し、ユーザーへ事実だけを報告する。

## 2. 最初に読む順番

次の順番だけで読む。

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_D0_COMPLETE_D1_M7C_EVIDENCE_PACKAGE_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
7. `configs/btc_ml_v1/btc_candidate_research_redesign_contract_20260730.json`
8. `docs/btc_ml_v1/BTC_D1_M7C_COLLECTOR_SOURCE_INVENTORY_PRELIMINARY_20260730.md`
9. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

上記を読み終える前にrepo全体検索、候補コード探索、GOLD/MOCHIPOYO横断探索をしない。

## 3. 最初に読んではいけないもの

このBTC研究では次を権威文書として使用しない。

- repo直下 `AGENTS.md`
  - 現在の内容はGOLD_ML_V1用であり、このBTC研究を再開する入口ではない。
- `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
- `docs/gold_v3/**`
- `docs/gold_ml_v1/**`
- `config/gold_v3/**`
- `config/gold_ml_v1/**`
- `scripts/gold_v3/**`
- `scripts/gold_ml_v1/**`
- GOLD V2、旧GOLD、GOLD V3、DISC8、Stage41関連
- 旧BTC stacking handoff
- 旧BTC YouTube候補handoff
- FF05 recovery V3〜V11を実行再開させる文書
- 固定入口から参照されていない古いBTC handoff/current state/next action

MOCHIPOYOについても、branchやfolderを一般検索しない。現在のD1に必要な契約内容は本handoffと再設計書に要約済みである。

## 4. ユーザーの最終目的

目的は、壊れたFF05再実行を完走させることではない。

目的は、BTCUSDで将来使える可能性のある、しっかりしたトレード候補システムを作ることである。

二本柱:

### Track A — もちぽよ由来

- M7Cとcollectorに記録された実際のもちぽよsource alertを一次証拠として使う。
- 「どこでアラートが出たか」を見ずにRCIやEMAから想像だけで候補を作らない。
- 実アラートを見て、どの発火時点情報が共通するか、どの状態遷移を捉えているかを逆推定する。
- 完全複製は最終目的ではない。
- 元アラート再現の層と、BTCで勝てるように改善する層を分ける。
- 元アラートの一部を拾えなくても、BTCで期待値・安定性・損失制御が高い候補を優先できる。
- ただし再現できなかったものを、再現成功と偽らない。
- source matched、missed source、extra candidateを混ぜずに評価する。
- 負けを減らす工夫は、発火時点で利用可能な情報だけを使い、同じ結果期間で後付け最適化しない。

### Track B — 独立ベクトル

- もちぽよのRCI、EMA stack、state transitionの微調整ではない。
- 異なる相場原理から候補を作る。
- 例: trend continuation、pullback continuation、compression-to-expansion、breakout/retest/re-acceleration、overextension mean reversion、方向非対称、上位足regime＋下位足execution。
- Track Aと発火・損益が高相関なら「独立」と呼ばず同族扱いする。
- 単体PFだけでなく、発火重複、損益相関、共同DD、相場regimeごとの役割を評価する。

## 5. システムとして必要な視点

単純な勝率の良いルール作りではない。

最初から次を考慮する。

- data provenance
- exact input pathとSHA256
- bar clockとfeature availability
- future leakage防止
- train/design/OOS/fresh separation
- multiple testing
- parameter neighborhood stability
- LONG/SHORT非対称
- volatility/regime別安定性
- transaction cost、spread、slippage感応度
- one-position/overlap/state transition
- backtestとshadowのdecision parity
- candidate間の相関と共同DD
- drift監視
- fail-closed停止
- prospective startとledgerを消さない障害復旧
- research、frozen rule、shadow、liveの分離
- user明示承認なしの自動昇格禁止

## 6. 現在の正式状態

status:

`BTC_REDESIGN_D0_COMPLETE_D1_SOURCE_INVENTORY_NEXT_READ_ONLY`

完了:

- FF05 recovery V3〜V11をactive pathとして廃止
- 失敗履歴は監査記録として保持
- FF01〜FF04の因果・bar-open・exact M5 entry・fail-closed契約を再利用可能な証拠として保持
- BTC7Rをselection provenance不明のため隔離
- もちぽよsource-anchored Track Aを定義
- independent-vector Track Bを定義
- fidelity layerとvalue layerを分離
- research、freeze、shadow、live、monitoringを分離
- D0再設計書と契約を作成
- D1契約資料ベースのpreliminary inventoryを作成
- handoff常時維持契約を作成

未完了:

- ローカル現行M7C 7ファイルの実schema確認
- genuine source event timeの正式列確認
- collector collection timeとM7C decision timeのclock domain確認
- BTCUSD sourceとBTC candle sourceのsymbol/price/time mapping確認
- duplicate/revision/late event/cursor behavior確認
- outcome exposure inventory
- immutable D2 snapshot
- event ledger
- trigger grammar
- candidate formula
- performance evaluation
- prospective shadow

## 7. 以前の誤りと再発禁止

### 7.1 FF05 recoveryの継ぎ足し

V3〜V11で、前version import、dynamic import、monkey patch、共有workspace、自動再結合を重ね、作業が進まなかった。無限再帰も発生した。

再発禁止:

- VnがVn-1をimportする連鎖
- monkey patchでinput discoveryをすり替える
- source folderの共有削除・再生成
- 成功summaryだけ残りpayloadが消える構造
- 自動探索、fallback、似た名前の採用
- 実環境integration未確認のままユーザーへ再実行を繰り返し依頼する

### 7.2 「やり直す」の誤解

ユーザーの「やり直す」は、壊れたrecovery wrapperを作り直すことではなく、BTCで使えるトレード候補を、もちぽよ由来と別ベクトルの両方から研究し直すことだった。

以後、FF05 recovery修復を現在の主目的へ戻さない。

### 7.3 もちぽよの安直な推測

M7C/collectorの実発火を見ず、RCIやEMAの単純条件として候補を想像してはならない。

最初にsource evidence、timestamp、event class、state transitionを確認する。

## 8. M7C・collectorの位置づけ

M7Cは歴史的にBTCUSDとXAUUSDのdual-source prospective collector/reproduction trackである。

BTC研究では:

- BTCUSD source eventを主なsource anchorとする。
- XAUUSD eventは構造比較の副証拠に限定する。
- BTCとXAUUSDを理由なく一つの母集団に混ぜない。
- GOLD M10研究結果はBTC candidate設計へ入れない。

M7C・collectorは読み取り専用。

絶対禁止:

- 停止
- 再起動
- 初期化
- prospective start変更
- runtime manifest変更
- formula/threshold/grace/matching変更
- M8C、M9V、M9Y、M10B、M10E、M10P、M10P2、M10W系変更
- GOLD/MOCHIPOYO側へのBTC結果書込み

## 9. 現在の次アクションはD1だけ

次に行う作業:

`D1_M7C_COLLECTOR_SOURCE_INVENTORY_READ_ONLY`

ユーザーへ依頼済み:

次の既存7ファイルを、編集・停止・再起動せず、一つのZIPへまとめて添付してもらう。

フォルダ:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\m7c`

対象:

1. `latest_m7c_prospective_shadow.json`
2. `latest_m7c_shadow_loop_status.json`
3. `latest_m7c_source_event_comparisons.csv`
4. `latest_m7c_extra_proxy_signals.csv`
5. `latest_m7c_proxy_signals.csv`
6. `latest_m7c_proxy_decisions.csv`
7. `m7c_shadow_forever.log`

collector追加ファイルは、上記7ファイルに欠損、異常、cursor問題が見つかった場合だけ後で検討する。一度に小分け要求しない。

## 10. ZIP受領時の処理

新チャット開始時にZIPが既に添付されている場合、再提出を求めず、まずZIPを開いて正確な内容を確認する。

D1で行う:

- exact filenames
- file size
- SHA256
- schema
- row counts
- symbol counts
- transition counts
- prospective start consistency
- status/cycle/failure状態
- genuine source timestamp候補
- collection timestamp候補
- M7C decision timestamp候補
- clock domain
- SOURCE_MATCHED/MISSED_SOURCE/EXTRA_CANDIDATE/UNSUPPORTED representation
- duplicate/revision/late event/cursor behavior
- outcome列や将来情報が既に含まれるかのexposure inventory
- unresolved questions

D1で行わない:

- WR/PF/DD/MFE/MAEの性能解釈
- 候補式の作成
- gateの設計
- source snapshot code
- event ledger code
- 新しいBAT
- FF06
- shadow runtime

手動ZIPの件数は暫定であり、D2 immutable snapshotができるまでは正式固定件数にしない。

## 11. D1後の進め方

D1結果をユーザーへ提示し、未決事項を明示する。

勝手に決めない項目:

- genuine source eventの正式時刻列
- BTCUSD source eventとbroker candleの時刻mapping
- sourceと研究CSVのsymbol/price source同一性
- REENTRYの初期scope
- source EXITをexit教師に使うか、state transition証拠だけにするか
- outcome exposureの扱い
- 新research series prefix
- retrospective gate、fresh gate、DD、cost条件

ユーザー確認後だけD2を実装する。

D2以降の大枠:

- D2 immutable evidence snapshot and event ledger
- D3 trigger-signature and control design
- D4 outcome-blind density audit
- D5 retrospective walk-forward evaluation
- D6 complementarity and portfolio review
- D7 explicit approval後のrule/runtime freeze and prospective shadow

## 12. 現在禁止されていること

- old recovery BAT実行
- FF06作成
- candidate formula設計
- outcome performance解釈
- WR/PF/MFE/MAE分析
- new BAT
- shadow runtime
- Discord
- MT5 order
- lot設計
- live_ready
- final_signal
- automatic promotion
- collector/M7C/M8C/M9/M10の変更または停止
- GOLD資料の一般探索
- old BTC handoffからの再開

## 13. 引き継ぎ更新契約

今後、次が起きたら同じ作業内で引き継ぎを更新する。

- ZIPや結果を監査
- status/decision/next action変更
- blocker、事故、訂正
- design/contract/formula/gate freeze
- 実装作成・修正・廃止
- BAT実行依頼
- shadow/monitoring/停止判断

更新対象:

- repo直下固定入口
- 最新日付付きhandoff
- current_state
- next_action
- handoff policy JSON

古いhandoffは監査履歴として残すが、固定入口から外れた時点で`AUDIT_HISTORY_ONLY`。

## 14. 新チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/btc-fresh-forward-research

BTC候補研究の続きです。

最初にGitHub上の次の固定入口だけを読んでください。

START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md

そこに書かれた最新版handoffと許可ファイルを、指定順で最初から最後まで読んでください。

重要:
- default branchやmainを読まない
- repo全体検索から始めない
- AGENTS.mdはGOLD用なので、このBTC研究の入口として読まない
- GOLD V2 / 旧GOLD / GOLD V3 / GOLD_ML_V1 / DISC8 / Stage41を読まない
- 古いBTC handoff、旧stacking、FF05 recovery V3〜V11から再開しない
- MOCHIPOYO branchを一般探索しない
- M7C/collector/M8C/M9/M10を停止・再起動・変更しない
- 不明点を推測で実装しない

現在はBTC候補研究の再設計後です。
Track AはM7C/collectorの実source alertを一次証拠にするもちぽよ由来研究、Track Bは別相場原理の独立候補研究です。

現在の次作業はD1の読み取り専用source inventoryだけです。
添付ZIPがある場合は再提出を求めず、まず中身を確認してください。
候補式、WR/PF評価、新BAT、FF06、shadowにはまだ進まないでください。
```
