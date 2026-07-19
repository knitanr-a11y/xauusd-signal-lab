# Mochipoyo Alert Research — M7A完了 / M7B次作業 引き継ぎ

作成日: 2026-07-20 JST  
repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

---

## 1. 最初に読むもの

次チャットでは、必ず次の順番で確認する。

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M7A_DONE_M7B_FROZEN_TRIGGER_KERNEL_NEXT_20260720.md`
2. `config/mochipoyo_alert_research/current_state_20260720.json`
3. `config/mochipoyo_alert_research/next_action_20260720.json`
4. `docs/mochipoyo_alert_research/STAGE_M7A_ALERT_TRIGGER_SIGNATURE_AUDIT_CONTRACT.md`
5. `scripts/mochipoyo_alert_research/alert_trigger_signature_audit.py`
6. 必要時のみ、M6A〜M6Cの契約文書と実装を確認する

M7A実装基準コミット:

```text
31c815fcdff82401cb1d02c54b1abb6b83ec84ef
```

M7A現在地スナップショット追加コミット:

```text
fea0b8570d57964049d711c3db6eadc7ab7fe993
```

M7B次作業契約追加コミット:

```text
7522ea65b9a659ce92b12a78dd07cadeea6ca5c2
```

---

## 2. プロジェクトの最終目的

本物のTradingViewもちぽよアラートを起点に、独立した期待値判定層を作り、最終的に自動売買へつなげる。

目的は次の2段階に分かれる。

### A. 本物アラートが機能する相場環境を特定する

```text
本物LONG / SHORT / EXIT / 再通知
↓
M5・M15・H1・H4・D1の確定情報
↓
勝ちやすい環境 / 負けやすい環境
↓
即時 / 待機 / 再エントリー / 見送り
```

### B. CSVからアラート発生条件の独立近似器を作る

```text
本物アラートが出たM15境界
vs
同じ状態なのにアラートが出なかったM15境界
↓
独立した再現候補条件
↓
新しい本物アラートで前向き再現検証
↓
十分に安定した後のみ、過去CSVや他時間軸へ展開
```

もちぽよインジケーターの内部コードや非公開ロジックを再構築したと主張してはいけない。実データから作るものは、あくまで独立したproxy / approximationである。

---

## 3. 絶対に維持する契約

### ソースイベント

- 本物イベントの正式情報はCloudflare Worker / SQLiteのWebhookイベントID
- チャートラベルの移動・再描画は再通知判定に使用しない
- 同方向再通知はチャート上でラベルが変わらなくても、独立した`REENTRY_ALERT`
- TradingViewの時刻・価格はsource reference
- MT5 CSVは独立比較・特徴量・経路測定に使用

### 状態機械

```text
IDLE + LONG       → ACTIVE_LONG
ACTIVE_LONG + LONG → REENTRY_LONG
ACTIVE_LONG + LONG_EXIT → IDLE

IDLE + SHORT       → ACTIVE_SHORT
ACTIVE_SHORT + SHORT → REENTRY_SHORT
ACTIVE_SHORT + SHORT_EXIT → IDLE
```

反対方向の通知は、正式EXIT前に自動でポジション方向を切り替えるものとして扱わない。

### 因果性

- closed bars only
- 未来足禁止
- ピボット / ZigZag proxyは右側確認が完了してからのみ使用
- アラート発生条件推定では、アラート足の高値・安値・終値を使用しない
- M7Aの判定時点は、新しいM15足の開始時刻
- 使用可能なのは直前に完全確定したM15足までと、新しいM15足の始値のみ

### 取引・通知

以下はすべてOFFのまま維持する。

```text
entry gate
Discord send
MT5 order
live ready
final signal
automatic trading rule approval
historical scan approval
cross-timeframe scan approval
```

---

## 4. データ・ローカル環境

SQLite:

```text
C:\Users\regen\AppData\Local\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3
```

MT5 Files root:

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
```

対象CSV:

```text
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv

btcusdsharp_m1.csv
btcusdsharp_m5.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
btcusdsharp_h4.csv
btcusdsharp_d1.csv
```

現在の観測区間ではMT5 server offsetはUTC+3で整合している。ただしDSTを永久固定してはいけない。新しい期間ではM4整合監査を再実行し、offset変化を区間分割する。

---

## 5. これまでのStage

### M0 — 保護・分離

- 既存GOLD V3 / BTC YouTube運用へ触れない
- もちぽよ研究は専用feature branch
- audit-only

### M1 / M2 — Webhook収集

- Cloudflare Worker `mochipoyo-webhook`
- D1 `mochipoyo-alerts`
- `POST /tradingview`
- protected `GET /events`
- 常時収集BAT / lock / log

### M3 — エピソード化

- connection test ID1をユーザー確認済みで除外
- PRIMARY / REENTRY / EXITを状態機械で整理
- 19 episodes
- 17 closed
- 2 open
- 5 reentries
- anomaly 0

### M4 — TradingView / MT5整合

- CSV時刻はMT5 server bar open
- `utc_open = server_open - inferred_offset`
- 最新確定足は`utc_close <= decision_time_utc`
- 205 / 205 alignment PASS
- future violation 0

### M5 — 因果的特徴量

契約:

```text
MOCHIPOYO_M5_CAUSAL_FEATURES_V1
```

41 eligible events × 5 timeframes = 205 snapshots。

主な特徴量:

- EMA20 / 30 / 40
- RCI9 / 14 / 18
- MACD 6 / 13 / 4
- ATR14
- ローソク形状
- tick volume ratio
- 直近5 / 10 / 20本レンジ位置
- causal confirmed pivot proxy 5/3/2, 12/5/3 reference

### M6A — 本物アラート即時入口 / source EXIT経路台帳

契約:

```text
MOCHIPOYO_M6A_SOURCE_OUTCOMES_V1
```

- virtual entries 24
- resolved 22
- open 2
- path metrics 22
- future violation 0
- R / USD未定義
- SL / TP / sizingなし

### M6B — 機能条件マップ

- 22 resolvedのうち20件が一度は1 M5 ATR以上順行
- source EXITプラス16件
- 方向検出には可能性あり
- 即時入口では大きな逆行が多い
- M15有利側端やREENTRYに暫定的な良さが見えた
- サンプルが小さいためルール採用は禁止

### M6C — M5入口タイミング比較

比較した入口:

1. 次M1始値reference
2. 最初の方向一致M5終値
3. M5直前2本抜け
4. 押し戻し後2本抜け
5. 二番底 / 二番天井ネックライン抜け

境界修正:

```text
M5候補時刻 < MT5 EXIT reference時刻
```

同時刻または後の候補はmissed扱いで、全体停止しない。

M6C PASS:

- source entries 24
- closed 22
- open 2
- candidate rows 120
- detected 101
- missed 19
- outcome rows 92
- future violations 0

暫定傾向:

- GOLD LONGはM5直前2本抜け待ちに可能性
- SHORTは即時または最初の方向一致M5が比較的強い
- REENTRYは待ちすぎると利益を失いやすい
- ただし未承認

### M7A — 本物アラート発生シグネチャ探索

実装コミット:

```text
31c815fcdff82401cb1d02c54b1abb6b83ec84ef
```

実行結果:

```text
status: PASS
stage: M7A_ALERT_TRIGGER_SIGNATURE_AUDIT
contract: MOCHIPOYO_M7A_TRIGGER_SIGNATURE_V1
built_at_utc: 2026-07-19T17:45:00Z
```

M7Aはデータベースを書き換えない。ローカルの派生JSON / CSVのみ生成する。

生成物:

```text
latest_alert_trigger_signature_audit.json
latest_alert_trigger_event_features.csv
latest_alert_trigger_candidate_rules.csv
```

ローカル既定位置:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\
```

---

## 6. M7Aの検証設計

### positive labels

本物のWebhook / SQLiteイベントのみ。

### negative controls

各銘柄について、最初の本物イベントから最後の本物イベントまでのM15 decision boundaryのみ。

Webhook収集開始前の過去CSVは、アラート記録がないだけで実際には通知が出ていた可能性がある。そのため、現時点では過去全体をno-eventと扱っていない。

### 6 transition classes

```text
PRIMARY_LONG
PRIMARY_SHORT
REENTRY_LONG
REENTRY_SHORT
LONG_EXIT
SHORT_EXIT
```

状態が異なるものを対照群に混ぜない。

- PRIMARY_LONG / PRIMARY_SHORT: `state_before == IDLE`
- REENTRY_LONG / LONG_EXIT: `state_before == ACTIVE_LONG`
- REENTRY_SHORT / SHORT_EXIT: `state_before == ACTIVE_SHORT`

---

## 7. M7A PASS件数

全体:

```text
eligible genuine events: 41
decision samples: 472
event decisions: 41
no-event decisions: 431
```

transition counts:

```text
PRIMARY_LONG   9
PRIMARY_SHORT 10
REENTRY_LONG   1
REENTRY_SHORT  4
LONG_EXIT      7
SHORT_EXIT    10
```

state-before counts:

```text
IDLE         215
ACTIVE_LONG  125
ACTIVE_SHORT 132
```

BTCUSD:

```text
observation: 2026-07-15T08:30:00Z ～ 2026-07-17T23:30:00Z
decisions: 253
events: 19
no-event: 234
```

XAUUSD:

```text
observation: 2026-07-15T09:45:00Z ～ 2026-07-17T18:15:00Z
decisions: 219
events: 22
no-event: 197
```

---

## 8. M7Aで見えた主要シグネチャ

重要: 以下は同じ短い観測区間で探索・評価されたexploratory ruleである。まだ再現器として承認されていない。

### ALL — PRIMARY LONG

```text
rci9_turn_up == True
AND ema_alignment == BULLISH_STACK
```

```text
positive total: 9
matched positive: 7
matched control: 2
precision: 77.78%
recall: 77.78%
lift: 18.58
```

単条件`rci9_turn_up == True`は9件中8件を拾った。

### ALL — PRIMARY SHORT

```text
rci9_turn_down == True
AND rci9 >= 25
```

```text
positive total: 10
matched positive: 10
matched control: 6
precision: 62.5%
recall: 100%
lift: 13.44
```

単条件`rci9_turn_down == True`は10件すべてを拾った。

### ALL — LONG EXIT

```text
rci9 >= 78.3333
AND rci14_delta1 >= 10.1099
```

```text
positive total: 7
matched positive: 7
matched control: 1
precision: 87.5%
recall: 100%
lift: 15.625
```

### ALL — SHORT EXIT

```text
rci9 <= -75
AND rci14_delta1 <= -29.3187
```

```text
positive total: 10
matched positive: 8
matched control: 0
precision: 100%
recall: 80%
lift: 13.2
```

### ALL — REENTRY SHORT

```text
rci9_turn_down == True
AND rci9 >= 65
```

```text
positive total: 4
matched positive: 4
matched control: 2
precision: 66.67%
recall: 100%
```

ただし4件のみ。

### ALL — REENTRY LONG

positiveは1件のみ。最上位ルールが1/1でも証拠にはならない。

---

## 9. XAUUSDだけの主要候補

### XAU PRIMARY LONG

```text
rci9_turn_up == True
AND rci14_delta1 <= -9.23077
```

```text
positive total: 6
matched positive: 4
matched control: 0
precision: 100%
recall: 66.67%
```

### XAU PRIMARY SHORT

```text
rci9_turn_down == True
AND macd_zero_proximity_atr <= 0.218057
```

```text
positive total: 5
matched positive: 5
matched control: 3
precision: 62.5%
recall: 100%
```

### XAU LONG EXIT

```text
rci9 >= 78.3333
AND macd_signal_bps >= 1.37003
```

```text
5 / 5 positive
0 control
```

### XAU SHORT EXIT

```text
rci9 <= -75
AND macd_line_bps <= -0.0673285
```

```text
5 / 5 positive
0 control
```

### XAU reentry

```text
REENTRY_LONG: 0件
REENTRY_SHORT: 1件
```

再通知条件の固定は禁止。

---

## 10. 現時点の重要な解釈

### 発火核として最も一貫しているもの

```text
LONG primary  : RCI9の局所的な上向き転換
SHORT primary : RCI9の局所的な下向き転換
LONG exit     : RCI9が上側極端域
SHORT exit    : RCI9が下側極端域
```

PRIMARY SHORTではRCI9 turn-downが10/10を拾った。PRIMARY LONGでもRCI9 turn-upが8/9を拾った。

これは、ユーザーが想定していたRCI反転を中心とする枠組みと整合する。ただし、これだけで内部条件が判明したとは言えない。

### 二次条件はscopeごとに変わる

LONGの二次条件は、ALLではbullish EMA stack、XAUではRCI14の逆方向変化が上位になった。

SHORTの二次条件は、ALLではRCI9水準、XAUではMACD zero proximityが上位になった。

この差は、銘柄固有条件の可能性もあるが、短期間への過適合の可能性もある。

### EXITは対称的なRCI極端域が有望

LONG EXITは上側、SHORT EXITは下側のRCI9極端域が強い。

ただし厳しいpair ruleではSHORT EXIT 10件中2件を落とした。単純な閾値固定ではなく、極端域への到達・継続・反転のどれが本体かをM7Bで分ける必要がある。

---

## 11. 現時点でしてはいけないこと

- M7A最上位ルールをそのままもちぽよ内部式と呼ぶ
- 最上位ルールをそのまま売買条件にする
- M6A〜M6Cの勝敗やMFE / MAEを使って発火式を選ぶ
- 41イベントだけで閾値を細かく最適化する
- pre-collector全履歴をno-eventとして再学習する
- 直ちに過去全CSVを「本物もちぽよアラート」として抽出する
- M5 / H1へ同じ数値閾値をそのまま移植する
- XAU REENTRY LONGのルールを作る
- REENTRY SHORT 4件 / XAU 1件を確定条件とする
- Discord通知を開始する
- MT5注文を開始する
- live-ready / final signalにする

---

## 12. 次の正式Stage

```text
M7B_FROZEN_TRIGGER_KERNEL_VALIDATION_AUDIT_ONLY
```

目的:

M7Aの多数の探索候補から、銘柄をまたいで共通して見えた少数の核だけを凍結し、過適合・閾値依存・誤検出の詳細を監査する。

### 優先するcore candidates

```text
PRIMARY_LONG
state == IDLE
AND rci9_turn_up == True

PRIMARY_SHORT
state == IDLE
AND rci9_turn_down == True

LONG_EXIT
state == ACTIVE_LONG
AND rci9 upper extreme candidate

SHORT_EXIT
state == ACTIVE_SHORT
AND rci9 lower extreme candidate
```

二次条件は固定前に、ALL / BTC / XAUでの安定性を比較する。

### M7Bで必ず出すもの

1. frozen rule manifest
2. 各本物イベントのtrue positive / false negative一覧
3. no-event false positive一覧
4. false positiveが連続発生するcluster分析
5. BTCで作った核をXAUで確認、XAUで作った核をBTCで確認するcross-symbol audit
6. leave-one-event-outまたは同等の閾値感度監査
7. one-sample artifactとscope-specific artifactの明示的除外
8. M7C prospective shadowへ進めるかPASS / BLOCKED

### M7Bで使ってはいけないもの

```text
M6A source EXIT利益
M6B expansion class
M6C入口損益
MFE
MAE
勝率
PF
将来足
アラート足OHLC
```

M7Bは発火再現性のみを見る。期待値評価は別Stageのまま分離する。

---

## 13. M7B後の順序

### M7C — prospective shadow reproduction

凍結したproxyを、新しく到着する本物イベントに対して前向き比較する。

```text
proxyが先に出た
本物と同じM15で出た
1本早い / 遅い
方向が違う
本物なしで余分に出た
本物を落とした
```

を記録する。

### その後のみ — full historical candidate extraction

M7Cで安定した場合、過去CSV全体から独立proxy candidateを抽出する。

抽出されたものを「過去の本物もちぽよ通知」と呼ばない。名称は必ず、

```text
MOCHIPOYO_INDEPENDENT_PROXY_CANDIDATE
```

など、独立候補であることが分かるものにする。

### さらにその後 — cross-timeframe mapping

M5 / H1等では、時間軸ごとにRCI・EMA・MACDを再計算し、閾値も別監査する。

M15の閾値をそのまま流用しない。

---

## 14. 新しいアラートが増えた場合

新しいWebhookイベントがSQLiteへ追加されたら、上流を順番に更新する。

```text
M3 episodes
M4 alignment
M5 feature snapshots
M6A source outcomes
M6B context map
M6C entry timing
M7A trigger signature audit
```

ただし、M6A以降はopen episodeのEXITが未到着なら未解決のまま保持する。

M7Bでルールを凍結した後は、新しいイベントを使って同じ閾値を再最適化してはいけない。新しいイベントはforward verificationに使う。

---

## 15. 次チャット開始用プロンプト

以下を新しいチャットへそのまま貼る。

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初に、次の順番で必ず読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M7A_DONE_M7B_FROZEN_TRIGGER_KERNEL_NEXT_20260720.md
2. config/mochipoyo_alert_research/current_state_20260720.json
3. config/mochipoyo_alert_research/next_action_20260720.json
4. docs/mochipoyo_alert_research/STAGE_M7A_ALERT_TRIGGER_SIGNATURE_AUDIT_CONTRACT.md
5. scripts/mochipoyo_alert_research/alert_trigger_signature_audit.py

現在の正式状態:

M7A_ALERT_TRIGGER_SIGNATURE_AUDIT_DONE_AUDIT_ONLY

M7A実装基準コミット:
31c815fcdff82401cb1d02c54b1abb6b83ec84ef

M7A実データ結果はPASSです。

- genuine events 41
- M15 decision samples 472
- event decisions 41
- no-event controls 431
- PRIMARY_LONG 9
- PRIMARY_SHORT 10
- REENTRY_LONG 1
- REENTRY_SHORT 4
- LONG_EXIT 7
- SHORT_EXIT 10

主なexploratory signature:

- PRIMARY_LONG: RCI9 local turn-upが中心
- PRIMARY_SHORT: RCI9 local turn-downが中心
- LONG_EXIT: RCI9上側極端域が中心
- SHORT_EXIT: RCI9下側極端域が中心

ただし、内部式を特定したとは断定しません。
過去全履歴抽出、他時間軸抽出、売買採用は未承認です。

次は:

M7B_FROZEN_TRIGGER_KERNEL_VALIDATION_AUDIT_ONLY

M7Bでは、M7Aの大量の探索候補をさらに最適化するのではなく、銘柄間で安定した少数のcoreだけを凍結し、event-by-event miss、false positive、cross-symbol stability、threshold sensitivityを監査してください。

絶対条件:

- audit-only
- genuine Webhook/SQLite eventsがpositive source
- no-event controlsはverified observation window内のみ
- alert-bar high/low/close禁止
- closed M15 features only
- future leakage禁止
- M6A/M6B/M6Cの利益・MFE・MAEを発火条件選択に使用しない
- proprietary internal formulaを再現したと主張しない
- historical full scan未承認
- cross-timeframe extraction未承認
- entry gate OFF
- Discord OFF
- MT5 order OFF
- live-ready OFF
- final signal OFF
- reentryはサンプル不足のため固定しない

不明点を憶測で実装せず、契約上の曖昧さが実装結果を変える場合は先に確認してください。
```

---

## 16. 現在の正式結論

M7Aにより、もちぽよの発火には少なくとも次の独立シグネチャが強く関連している可能性が示された。

```text
PRIMARY LONG  : RCI9の下側からの局所反転
PRIMARY SHORT : RCI9の上側からの局所反転
LONG EXIT     : RCI9上側極端域
SHORT EXIT    : RCI9下側極端域
```

特にPRIMARY SHORTの`rci9_turn_down`は今回10/10、PRIMARY LONGの`rci9_turn_up`は8/9だった。

これは過去サンプル抽出や他時間軸候補作成へつながる重要な前進である。一方、現在の結果は2銘柄・約2.5日・41イベントの同一探索区間内の結果である。

したがって、次は過去スキャンではなく、少数coreを凍結して再現性を監査するM7Bが正式な次作業である。
