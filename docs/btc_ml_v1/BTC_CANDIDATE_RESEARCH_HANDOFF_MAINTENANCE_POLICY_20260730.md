# BTC候補研究 引き継ぎ維持契約

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- scope: BTCUSD candidate research redesign only

## 1. 目的

この研究は長期化し、途中で新しいチャットへ移る可能性が高い。したがって、チャット終了直前だけでなく、いつ切り替わっても正しい地点から再開できるよう、引き継ぎを常時維持する。

引き継ぎは、会話の記憶や古い文書名の推測に依存しない。GitHub上の固定入口から、その時点の最新版だけへ到達できる構造にする。

## 2. 権威の順序

新しいチャットは必ず次の順で判断する。

1. repo直下 `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. そこに記載された唯一の `latest_dated_handoff`
3. そこに記載された `current_state`
4. そこに記載された `next_action`
5. そこから明示的に許可された設計書・契約・提出物

固定入口から参照されていない古いhandoff、旧current state、旧next action、過去のチャット開始文は監査履歴であり、再開根拠にしてはならない。

## 3. branch hard gate

- 必ず `feature/btc-fresh-forward-research` を明示指定して読む。
- default branch、`main`、別branchから同名ファイルを読まない。
- branchが存在しない、取得できない、または内容が食い違う場合は作業を停止し、推測で代替しない。
- 新しいチャットは、branchを確認する前にrepo全体検索を行わない。

## 4. 読み取り範囲の原則

### 4.1 最初に読んでよいもの

固定入口と、固定入口が列挙した正確なファイルだけ。

### 4.2 最初に読んではいけないもの

- repo直下 `AGENTS.md`。現状はGOLD_ML_V1向けであり、このBTC研究の権威文書ではない。
- `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
- `docs/gold_v3/**`
- `docs/gold_ml_v1/**`
- `config/gold_v3/**`
- `config/gold_ml_v1/**`
- `scripts/gold_v3/**`
- `scripts/gold_ml_v1/**`
- 旧GOLD、GOLD V2、GOLD V3、DISC8、Stage41関連
- 古いBTC handoff、旧BTC stacking開始文、旧FF recovery実行文
- `feature/mochipoyo-alert-research`の広範な探索

### 4.3 MOCHIPOYO例外

M7CとcollectorはBTCUSDを含むdual-source一次証拠なので、BTC研究に必要な場合がある。ただし、読むことが許されるのは最新版handoffが正確なパスで列挙した契約文書またはユーザー提出ファイルだけ。

禁止:

- MOCHIPOYO branchを一般検索する
- M8C、M9、M10系列をBTC候補の参考として横断的に読む
- GOLDの成績、閾値、候補式、portfolio判断をBTCへ移植する
- collector、M7C、その他monitorを停止・再起動・変更する
- MOCHIPOYO側へBTC研究結果を書き込む

## 5. 更新が必須となるタイミング

次のいずれかが起きた同じ作業内で、引き継ぎを更新する。

- ユーザー提出ZIPや結果を受領・監査した
- status、decision、next actionが変わった
- 新しい疑問、blocker、事故、訂正が生じた
- 設計、契約、候補grammar、評価gateを凍結した
- 実装を作成・修正・廃止した
- BAT実行をユーザーへ依頼する状態になった
- shadow、監視、停止判断へ移った
- 会話が長くなり、いつ上限へ達してもおかしくない

軽微な説明だけで正式状態が変わらない場合は、毎メッセージ更新する必要はない。ただし、未記録の正式判断を複数ターン持ち越してはならない。

## 6. 毎回更新する4層

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. 新しい日付付き完全handoff、または現行handoffの明示的な最新版
3. `configs/btc_ml_v1/btc_candidate_research_current_state_YYYYMMDD.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_YYYYMMDD.json`

必要に応じてhandoff policy JSONの`latest_dated_handoff`、許可ファイル、禁止ファイル、pending evidenceも更新する。

## 7. 日付付きhandoffの必須内容

- repo、branch、記録日時
- この文書が最新版であること
- 最初に読む正確な順番
- 読んではいけないpathと旧文書
- 現在status、decision、completed、pending
- ユーザーの最終目的
- Track AとTrack Bの区別
- データ・時刻・因果契約
- 使用可能な証拠と禁止証拠
- 実行中monitorの保護条件
- 直前に起きた事故・誤解・再発禁止
- 次に行う一つの作業
- 明示承認なしに進んではいけない後続作業
- ユーザー提出物が必要なら正確なファイル名と場所
- 新チャット開始用プロンプト

## 8. 古いhandoffの扱い

古いhandoffは削除・上書き・renameして歴史を隠さない。ただし、各古い文書は最新版入口から外れた時点で`AUDIT_HISTORY_ONLY`となる。

新チャットが検索で古いhandoffを先に見つけた場合も、その文書から作業を始めず、repo直下の固定入口へ戻る。

## 9. fail-closed

次の場合は作業を進めない。

- 固定入口とcurrent stateが矛盾する
- branchが違う
- handoffがGOLD文書を一般参照するよう指示している
- latest handoffが不明
- ユーザー提出物の世代・出所が不明
- 実行中M7C/collectorの変更が必要に見える
- outcomeを開く許可が不明

推測、fallback、似たファイルの自動採用は禁止する。
