# GOLD V3 完全引き継ぎ
## Stage259完了 → Stage260 Event-First Edge Discovery 次
### 作成日: 2026-06-20

repo: `knitanr-a11y/xauusd-signal-lab`

---

# 0. 30秒で分かる現在地

## 今までしたこと

Stage250〜259で、以下を順番に検証した。

1. 相場レジームで既存候補をON/OFFするルーター
2. 押し目・戻り目の勝敗特徴量マイニング
3. 値幅機会モデルとエントリートリガーの二段階化
4. 一度逆行した後の反転切り替え検出
5. 反転突破後の初回リテストと構造SL
6. H1で10〜20ドル伸びる足をM1/M5へ分解
7. 値幅拡大ゲートと初回リテストの結合
8. 方向を価格自身に選ばせるOCOブレイク
9. 高ボラ／通常・低ボラの専門戦略ルーター
10. 通常・低ボラ専用の平均回帰・レンジ戦略探索

## それで判明したこと

- インジケーター条件を大量に組み合わせるだけでは強い候補にならない。
- 押し目・戻り目の広い母集団は粗い期待値が弱い。
- 反転突破後の初回リテストは、入口改善として最も手応えがあった。
- H1の大幅値幅が出やすい環境は、D1/H4/M5の高ATR・高出来高で検出できる。
- ただし「値幅が出る方向」を年をまたいで固定予測するのは不安定。
- 相場をHIGH / NORMAL / TRANSITIONへ因果的に分けるルーターは、候補常時ONより明確に改善した。
- 高ボラ専門だけは2025・2026の両年でcost2後プラス。
- 通常・低ボラ専門は未完成。現在はNORMALとTRANSITIONをNO_SIGNALにするのが安全。
- 現在の高ボラ専門安全版は研究候補であり、実運用昇格は不可。
- 強い候補を作るには、弱いセットアップをフィルターで磨くのではなく、市場参加者の注文が集中する「イベント」から母集団を作る必要がある。

## 次にすること

Stage260では条件総当たりをやめ、次の4イベントを最初から独立に検証する。

1. MT5セッション開始後のオープニングドライブ
2. 前日高値・安値のスイープと回収
3. H1/H4複数回反応価格の突破後初回リテスト
4. 長時間圧縮後の初回拡大

イベント群を、同曜日・同MT5時間・同ATR帯・同レジームの非イベント対照群と比較する。

母集団そのものに差がないイベントは、特徴量を追加する前に不採用とする。

---

# 1. 現在の正式ステータス

現在:

`GOLD_V3_259_NORMAL_LOWVOL_SPECIALIST_SEARCH_DONE_AUDIT_ONLY`

次:

`GOLD_V3_260_EVENT_FIRST_EDGE_DISCOVERY_AUDIT_ONLY`

現在の安全なルーター解釈:

- `HIGH`:
  高ボラ専門をaudit/shadow研究候補として維持
- `NORMAL`:
  専門候補未完成のためNO_SIGNAL
- `TRANSITION`:
  NO_SIGNAL
- 実運用:
  不可

---

# 2. 絶対禁止事項

GOLD V3は現在も **audit-only**。

以下は読まない・使わない・参照しない・fallbackにしないこと。

- GOLD V2
- 旧GOLD
- DISC8
- Stage41 feature-only snapshot
- 過去の隔離済みtrading source

禁止:

- MT5発注
- Discord通知
- live hook
- autotrade
- 注文payload生成
- NO_SIGNAL時の通知・注文
- 結果が良く見えるような候補の恣意的削除
- 2026年を見て2025年条件を変更
- 年ごとに手動で戦略条件を切り替える
- 高ボラだからSHORTなど、年依存の方向をハードコード
- CSV行番号を別取得CSVへ流用
- 未確定足の利用
- 将来のスイング確定情報を入力特徴へ混入
- 2026年成績を候補選定・閾値決定に利用

candidate poolは広く保持する。

候補を落とす場合は、

- 固定基準
- 理由
- 件数
- 期間
- 近隣条件
- プラセボ結果

を残す。

---

# 3. CSV・確定足・エントリー契約

CSV最新行はCSV契約上 **closed**。
open/as-of扱いは禁止。

ただし全CSVの`time`はローソク足の **OPEN時刻**。

利用可能時刻:

- M1 = open + 1分
- M5 = open + 5分
- M15 = open + 15分
- H1 = open + 1時間
- H4 = open + 4時間
- D1 = open + 1日
  - D1には既知の時刻契約上の注意点があるため、利用時は監査列を残す

HTF利用条件:

`source_close_time <= signal_time / decision_close_time`

を満たすものだけbackward mergeする。

エントリー:

- シグナル足・確認足が確定した後
- 最初のM1始値

決済:

- 同一M1でTP・SL両方へ触れた場合はSL優先

1 setup 1 trade:

- active中は同候補を無視
- 決済後、条件が一度falseになるまでrearmしない

MFE/MAE:

- ホライズン終端まで計算する
- SL先着時点でMFE/MAE走査を止めない
- TP/SL先着結果と、最終MFE/MAEを別々に保存する

---

# 4. MT5サーバー時刻・取引禁止帯

`gold#`と`goldsharp`の2025年H1重複5,894本を比較済み。

確認結果:

- 時刻オフセット0時間
- OHLC差0件

このデータではCSVの`time`をMT5／サーバー足OPEN時刻として扱う。

JST時間で固定的に取引時間を決めない。
MT5／CSVサーバー時刻を使う。

時刻ギャップ15分超をセッション境界として検出する。

取引禁止:

- 各取引セッション開始後60分
- 各取引セッション終了前60分
- 予定保有時間が安全終了時刻をまたぐ候補
- MT5日付変更をまたぐ取引
- 週末をまたぐ取引
- 祝日短縮セッションをまたぐ取引

ユーザー体感:

- 通常の総コスト感は概ね1ドル前後
- 滑る時は1〜2ドル程度
- 通常5ドル滑ることはない
- MT5日付変更・週跨ぎは値段が飛ぶので取引しない

現在の評価コスト:

- `cost1` = 通常想定
- `cost2` = 主判定
- `cost3` = 厳しいストレス
- `cost5` = 極端な参考値のみ

注意:

現状は固定ドルコストの代理評価。
Bid/Ask、実スプレッド、手数料、約定スリッページの実データ評価は未完了。

---

# 5. 以前の監査で判明し、現在も拘束する事項

以下はStage250以前の重要知見で、今後も再発禁止。

- Stage69検出器は死んでいない。
  - NO_SIGNALが続いたのは、直近で条件が出ていない／入口ゲートで落ちたため。
  - NO_SIGNAL連続だけを理由に候補や検出器を削除しない。
- R2は高ATR相場で入口落ちしていた問題があった。
  - 高ボラ候補はsetup検出だけでなく、entry gate通過率を必ず監査する。
- HV兄弟が`is_high_vol=True`を拾わず、逆に除外していた問題があった。
  - 高ボラフラグの真偽条件を逆転させない。
- 初期proxyではtrue high-vol LONG全敗、SHORT全勝という極端な結果があった。
  - ただし後のStage255〜257で方向関係は年をまたいで不安定と判明。
  - 「高ボラならSHORT」と固定しない。
- 通常候補が実装上LONG固定になっている可能性が懸念された。
  - LONG/SHORT対称性とdirection列を必ず監査する。
- JST判定とMT5/CSV時刻の混同が問題になった。
  - 現在はMT5／CSVサーバー時刻を主契約とする。
- CSV最新行はclosed。
  - open/as-of除外ロジックを追加して最新closed行を誤って落とさない。
- candidate poolを外さない方針は継続。
- Stage99〜106までの監視・監査到達点を壊さない。
  - audit-only
  - NO_SIGNALは正常出力
  - live/order/notificationへ接続しない

---

# 6. 修正済み実装バグ・再発禁止

## 6.1 HTF source_close_time重複列

Stage245で、

`h1_source_close_time`

がkeepリストへ二重追加され、

`ValueError: The column label 'h1_source_close_time' is not unique`

が発生した。

再発防止:

- source_time列を明示的に1回だけ追加
- prefix抽出時にsource_time自身を除外
- merge前に列名重複監査

## 6.2 MFE/MAEの途中打ち切り

Stage252でSL先着時点に走査を止め、後のMFEが失われた。

修正済み:

- TP/SL初回先着は記録
- MFE/MAEはホライズン終端まで計算

## 6.3 H1ローリング履歴不足

Stage257初回で2025年開始時にH1ローリング履歴を切っていた。

修正済み:

- 2023年以前からの確定H1履歴を使って2025年分位を作る
- 検証開始日で特徴履歴をリセットしない

## 6.4 CSV行番号の再利用

再取得したM1 CSVとキャッシュ済みイベントで24行差があった。

修正済み:

- 行番号・indexで再結合しない
- `entry_time`等の時刻で厳密結合
- 時刻不一致を監査出力

## 6.5 gold# / goldsharp source parity

重複期間でOHLC一致を確認済み。

- M5 58,092本: 差0
- M15 19,363本: 差0
- H1 5,894本: 差0
- H4 1,541本: 差0
- D1 258本: 差0

ただし新しく取得したCSVは、毎回source parityを再確認する。

---

# 7. Stage250〜259で実際にしたことと判明したこと

## Stage250 — Causal Regime Router

### したこと

- 既存候補を相場レジーム別にON/OFF
- 最近180日の候補PFを追うルーター
- 候補構造とレジームの適合を固定したルーター
- 2025・2026比較

### 判明

最近PF追随は失敗。

- conservative PF5 約0.98
- balanced PF5 約0.82
- health gate付き PF5 約0.64

理由:

- 最近勝った候補を追うとレジーム転換で遅行する。

固定構造レジームルーター:

- 2025+2026 67件
- PF5 約1.34
- 損益約+200

ただし:

- 2025単体PF5約1.14
- Q4依存
- live昇格不可

結論:

- 最近PF追随は不採用
- レジーム構造適合は有効な研究方向

---

## Stage251 — Entry-known Feature Mining

### したこと

- 押し目・戻り目を広く36,766件生成
- エントリー時点で確定済みの約50特徴
- ロジスティック回帰
- 浅い決定木
- スコアカード
- 月次walk-forward

繰り返し出た特徴:

- 進行方向の値幅余地
- M5相対出来高
- M5 ATR比
- M5 EMA50/200方向
- H1 MACDヒストグラム改善
- H1 EMA20/50方向
- D1 ATR比

### 判明

OOS選択後:

- cost0平均約+0.52
- cost3 PF約0.64
- cost5 PF約0.47

結論:

- 特徴量選別では少し改善
- 入口母集団自体の粗いエッジが弱すぎる
- 勝ちだけを見るのでなく、同じ候補の負けとの比較が必須

---

## Stage252 — Opportunity × Trigger

### したこと

- 機会モデル:
  将来MFEがTP幅へ届くか
- トリガーモデル:
  その機会をSL先行せず利益化できるか
- 月次walk-forward

### 判明

- 値幅機会の識別には多少効果
- 既存M1/M5トリガーでcost5後プラス月0
- 機会後の価格経路と入口がボトルネック

---

## Stage253 — Reversal Switch

### したこと

- セットアップ後の逆行
- 下落／上昇失速
- 反転足
- M1高安値突破
- 安値切り上げ／高値切り下げ
- 二番底／二番天井
- EMA再奪回
- 出来高クライマックス
- 複合スコア

### 判明

逆行後に最終TP幅へ進んだケース捕捉率:

- 25%逆行: 約94%
- 50%逆行: 約90%
- 75%逆行: 約86%

ただし:

- 最良粗期待値約+0.51
- cost3・cost5赤字

結論:

- 反転点検出は可能
- 反転直後の成行は弱い

---

## Stage254 — First Retest + Structural SL

### したこと

- 反転突破後の初回リテスト
- 突破水準
- EMA20
- 反転足中央
- 38.2 / 50 / 61.8%戻し
- 反発確認型
- 事前指値相当
- 構造SL
- TP5 / 10 / 15
- 60 / 120分

### 判明

最良SHORT:

- 突破水準への事前指値相当
- TP15
- 120分
- 約250件
- cost0 PF約2.35
- cost0平均約+3.03
- cost3 PF約1.01
- cost5 PF約0.63

LONG:

- cost0平均約+2.95

結論:

- 入口改善として最も手応えあり
- ただしcost2〜3への余裕は薄い
- 指値相当は実Bid/Ask・ティックでの約定確認が今後必要

---

## Stage255 — H1 Expansion Lower-TF Decomposition

### したこと

- H1開始5 / 10 / 15 / 30分後
- そこまでの確定M1/M5特徴だけを入力
- 残り時間で10 / 15 / 20ドル拡大をラベル
- 2025年前半で学習
- 2025後半で選定
- 2026固定

安定特徴:

1. D1 ATR過去分位
2. D1 ATR14/ATR50
3. M5出来高分位
4. M5 ATR分位
5. 直前H1出来高分位
6. H1開始後M1レンジ
7. H4 ATR分位
8. D1 EMA50/200方向
9. M5 ATR14/ATR50
10. H4 ATR14/ATR50

### 判明

- 大幅値幅が出る環境は高リフトで検出できる
- 高ATR＋高出来高＋初動レンジ拡大が中心
- 同じ局面で上下両方へ大きく動くことが多い
- 方向純度不足
- expansion gateとしては有効
- 売買方向・入口は別に必要

---

## Stage256 — Expansion Gate × First Retest

### したこと

- Stage255拡大ゲート
- Stage254初回リテスト
- 単純拡大ゲート
- TP先着方向モデルゲート
- 2025固定→2026

### 判明

単純ゲートで2025後半の粗期待値中央値:

- LONG +1.72 → +4.89
- SHORT +1.33 → +3.35

しかし:

- 2026 SHORTで悪化

方向モデル:

- 2025内で8候補
- 2026 cost5 PF約0.37

結論:

- 拡大環境は比較的安定
- 拡大方向の固定予測は年をまたいで不安定

---

## Stage257 — Direction-neutral OCO Breakout + First Retest

### したこと

- 拡大ゲート時点で方向を決めない
- 観測レンジ高値・安値を固定
- 最初に終値突破した側だけ採用
- 反対側破棄
- 初回リテスト
- 構造SL／固定SL
- TP10 / 15 / 20 / 25
- 120 / 180 / 240分

全16,320変種。

### 判明

最良:

- cost0平均約+2.65
- cost3 PF約0.94
- cost5 PF約0.68

2025前半・後半両方でcost3後プラス:

- 0件

結論:

- 方向予測問題は減った
- 粗期待値3ドル未満が残った
- OCO自体は正しい設計だが強度不足

---

## Stage258 — Two-regime Specialist Router

### したこと

因果的レジーム:

- HIGH
- NORMAL
- TRANSITION

相対特徴:

- H1/H4 ATR過去分位
- ATR14/ATR50
- 継続判定
- ヒステリシス

STRICT分布:

2025:

- HIGH 16.9%
- NORMAL 33.9%
- TRANSITION 49.1%

2026:

- HIGH 16.7%
- NORMAL 38.3%
- TRANSITION 45.0%

### 判明

同じ8候補を常時ON:

- 638件
- cost2 PF0.917
- 損益-265.45
- DD588.81

2相場ルーター:

- 232件
- cost2 PF1.213
- 損益+234.14
- DD179.84

年別:

- 2025 PF1.228、+192.14
- 2026 PF1.163、+42.00

高ボラ専門:

- 2025 cost2 PF約1.26
- 2026 cost2 PF約1.32

通常専門:

- 2026 6件全敗

結論:

- レジームON/OFFは有効
- HIGH専門だけが両年で機能
- NORMAL専門未完成

---

## Stage259 — Normal / Low-vol Specialist Search

### したこと

高ボラ候補を流用せず、通常・低ボラ専用に作り直した。

224基本構造、1,768変種。

対象:

- レンジ端反発
- ブレイク失敗回収
- 二番底・二番天井
- EMA20/50平均回帰
- BB外側回収
- 圧縮レンジ端
- M1だまし抜け
- M1二番底・二番天井

### 判明

- cost2で2025前半・後半両方プラス: 0
- cost1でも安定通過: 0
- 最も近いEMA20平均回帰SHORTもcost2両年PF1未満

Stage259安全版:

- 2025:
  139件、cost2 PF1.217、+145.54
- 2026:
  46件、cost2 PF1.317、+72.00
- 全期間:
  185件、cost2 PF1.243、+217.54
- cost3 PF約1.03

これはNORMALでも勝てるようになったのではない。

- HIGHだけ稼働
- NORMALをNO_SIGNAL
- TRANSITIONをNO_SIGNAL

として損失を避けた結果。

---

# 8. 現時点で使えるもの／使えないもの

## 研究上使える

- 確定足・時刻契約
- MT5セッション境界検出
- rollover / weekend除外
- HIGH / NORMAL / TRANSITIONレジーム分類
- HIGH専門候補
- Stage254初回リテスト構造
- Stage255値幅拡大環境ゲート
- cost1 / cost2 / cost3評価
- no-lookahead監査
- 2025選定→2026固定評価の枠組み

## 未完成・使わない

- 最近PF追随ルーター
- NORMAL一括平均回帰
- 高ボラ方向の固定LONG/SHORT予測
- 反転直後の成行
- OCOだけでの売買候補
- cost5を通常主判定にすること
- Stage254の指値相当を実約定確認なしで運用
- 2026だけ良かった候補
- 実運用・注文・通知

---

# 9. 現時点の本質的な結論

インジケーター条件を増やすだけでは強い候補にならない。

理由:

- EMA、RSI、MACD、ATRは同じOHLCの変形が多い
- 数千変種でも同一クラスターの兄弟が多い
- 弱い母集団をフィルターで磨いている
- 市場参加者が注文を出さざるを得ない理由が弱い

強い候補には、

`イベント発生時だけ、対照群より将来価格分布が明確に偏る`

必要がある。

今後は、

- setup-first
- indicator-first
- grid-search-first

ではなく、

- event-first
- control-group comparison
- placebo destruction test

へ切り替える。

---

# 10. Stage260の目的

正式名称:

`GOLD_V3_260_EVENT_FIRST_EDGE_DISCOVERY_AUDIT_ONLY`

目的:

- 市場構造上の理由があるイベント母集団を作る
- 非イベント対照群との差を最初に確認
- 差がないものは特徴量追加前に終了
- 差があるイベントだけを少数特徴で磨く
- 独立イベントクラスターを複数作り、合計頻度を確保

---

# 11. Stage260で検証する4イベント

## E1. MT5セッション開始後のオープニングドライブ

定義候補:

- 実セッション開始時刻はCSVギャップから取得
- 開始前30 / 60 / 120分レンジ
- 開始後5 / 10 / 15分の値幅
- 出来高増加
- ATR拡大
- レンジ片側の確定突破
- 初回浅い押し戻り

固定時刻だけを理由にエントリーしない。
開始後に注文集中が実際に確認された場合だけイベント。

注意:

セッション開始後60分を現在は禁止している。
Stage260ではまず「イベントのエッジ発見」として監査する。
既存禁止契約を変更して運用候補へ昇格してはいけない。
有効性が出た場合に、禁止60分を再設計する別監査が必要。

## E2. 前日高値・安値のスイープと回収

定義候補:

- 前日高値／安値をM1/M5で一度抜く
- 抜け幅をATR正規化
- 抜けた側へ進めない
- 元レンジ内へ確定終値で回収
- 回収時間
- 滞在時間
- 出来高
- 反対方向の構造突破
- 初回リテスト

単なるヒゲだけで定義しない。

## E3. H1/H4複数回反応価格の突破後初回リテスト

重要価格は過去だけで定義。

候補:

- 過去20 / 40 / 80本
- H1/H4高安値cluster
- ATR許容幅内で2 / 3 / 4回反応
- 最後の反応後に一定時間経過
- 確定終値突破
- 初回リテスト
- 構造SL

未来の反応回数を使わない。

## E4. 長時間圧縮後の初回拡大

候補:

- H1/M15 ATR分位低位
- BB幅低位
- 高安値レンジ縮小
- M5出来高変化
- 圧縮継続時間
- 初回確定突破
- 初回リテスト

Stage255の「すでに高ボラ」ではなく、
「高ボラになる直前」を狙う。

---

# 12. 対照群の作り方

各イベントについて必ずmatched controlを作る。

一致条件:

- 同じ曜日
- 同じMT5時間帯
- 同じATR帯
- 同じHIGH / NORMAL / TRANSITION
- 同じ方向条件
- 近い月／四半期
- ただし対象イベントなし

比較:

- イベント群
- 非イベント対照群
- ランダム時点
- 時刻シフト群
- 水準シフト群

単純な全時間平均とだけ比較しない。

---

# 13. 必須評価

イベント発生時点から:

- MFE
- MAE
- MFE/MAE比
- 5 / 10 / 15 / 20 / 25ドル到達
- TP/SL先着
- 到達時間
- 逆行後回復率
- cost0
- cost1
- cost2
- cost3
- PF
- 損益
- 期待値
- 最大DD
- 最大連敗
- 月別
- 四半期別
- LONG/SHORT
- 2025前半
- 2025後半
- 2026固定
- HIGH/NORMAL/TRANSITION別
- セッション別

---

# 14. 必須プラセボ試験

- イベント時刻を±5 / ±10 / ±15分シフト
- 水平価格を±0.5 / ±1.0ATRシフト
- LONG/SHORT反転
- 日付ランダム化
- 曜日入れ替え
- レジーム逆割当
- event flagを同件数ランダム抽出へ置換
- 確認条件を外した母集団

本物のイベントのみが明確に優位でなければならない。

---

# 15. Stage260の早期不採用基準

以下なら、そのイベントは特徴量を足す前に終了。

- cost0粗期待値が弱い
- matched controlとの差が小さい
- 2025前半・後半で符号反転
- プラセボと同等
- 1四半期だけで利益
- 件数が極端に少ない
- 近隣閾値で崩壊
- 実質同一イベント兄弟しか残らない
- event timeより後の情報が定義に混入

---

# 16. Stage260の合格目標

主判定: `cost2`

目標:

- 2025年・2026年とも損益プラス
- cost2 PF >= 1.30
- cost3 PF >= 1.00前後
- cost0粗期待値最低3ドル
- 理想は5ドル以上
- 片方の四半期だけに依存しない
- 1イベント最低20件/年を目安
- 近隣TP/SLでも大崩れしない
- プラセボに明確に勝つ
- matched controlより明確に良い
- 同一兄弟を独立候補として水増ししない
- audit-only
- NO_SIGNALを許容

頻度方針:

1つの高頻度候補を無理に作らない。

`月10〜20件の独立イベント × 5〜10クラスター`

で合計頻度を作る。

---

# 17. 検証順序

Stage260では4イベントを同時に複雑化しない。

推奨順:

1. E2 前日高安スイープ
   - 定義が明確
   - 過去価格だけで作りやすい
2. E4 圧縮後初回拡大
   - Stage255の知見を活用
3. E3 H1/H4重要価格
   - 水平価格clusterの因果監査が必要
4. E1 オープニングドライブ
   - 現在の開始後60分禁止契約との整合監査が必要

最初は各イベントの母集団差だけを出す。
売買ルール最適化は後。

---

# 18. 未解決事項

- 実Bid/Ask・実スプレッド・手数料・ティックスリッページ評価は未完了
- 指値相当の実約定可能性は未監査
- 2026は研究過程で既に何度も観測されており、完全な未見holdoutではない
- 現データは2026年6月頃までで、将来レジームの追加検証が必要
- NORMALを水平レンジ／低ボラトレンド／圧縮直前へ分ける案は未完了
- 経済指標後第二波は外部指標カレンダーが必要なためStage260初回4イベントには入れていない
- セッション開始イベントが有効でも、現在の開始後60分禁止を即解除しない
- cost2で利益が出ても実運用昇格ではない

---

# 19. 使用可能な重要ファイル

## Stage258

- `/mnt/data/stage258_result_summary.md`
- `/mnt/data/stage258_final_summary.json`
- `/mnt/data/stage258_two_regime_router/stage258_strategy_summary.csv`
- `/mnt/data/stage258_two_regime_router/stage258_strategy_monthly.csv`
- `/mnt/data/stage258_two_regime_router/stage258_locked_specialists_selected_on_2025.csv`
- `/mnt/data/stage258_two_regime_router/stage258_two_regime_router_trades.csv`
- `/mnt/data/stage258_two_regime_router/stage258_static_union_always_on_trades.csv`
- `/mnt/data/stage258_two_regime_router/stage258_regime_distribution.csv`
- `/mnt/data/stage258_two_regime_router/stage258_mt5_session_calendar.csv`
- `/mnt/data/stage258_two_regime_router/stage258_trade_time_audit.csv`
- `/mnt/data/stage258_two_regime_router/stage258_no_lookahead_audit.csv`
- `/mnt/data/gold_v3_258_two_regime_specialist_router_audit.py`

## Stage259

- `/mnt/data/stage259_result_summary.md`
- `/mnt/data/stage259_final_summary.json`
- `/mnt/data/stage259_normal_specialist/stage259_variant_summary.csv`
- `/mnt/data/stage259_normal_specialist/stage259_base_candidate_catalog.csv`
- `/mnt/data/stage259_normal_specialist/stage259_strategy_summary.csv`
- `/mnt/data/stage259_normal_specialist/stage259_strategy_monthly.csv`
- `/mnt/data/stage259_normal_specialist/stage259_no_lookahead_audit.csv`
- `/mnt/data/stage259_normal_family_diagnostics.csv`
- `/mnt/data/stage259_crossyear_cost1_diagnostics.csv`
- `/mnt/data/gold_v3_259_normal_lowvol_specialist_search_audit.py`

## それ以前の重要参照

- `/mnt/data/stage254_result_summary.md`
- `/mnt/data/stage255_result_summary.md`
- `/mnt/data/stage256_result_summary.md`
- `/mnt/data/stage257_result_summary.md`
- `/mnt/data/gold_v3_254_first_retest_structural_sl_audit.py`
- `/mnt/data/gold_v3_255_h1_expansion_lower_tf_decomposition_audit.py`
- `/mnt/data/gold_v3_257_direction_neutral_oco_breakout_retest_audit.py`

## 元データ候補

- `gold#_m1.csv`
- `gold#_m5.csv`
- `gold#_m15.csv`
- `gold#_h1.csv`
- `gold#_h4.csv`
- `gold#_d1.csv`
- `goldsharp_m1.csv`
- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

新チャットでは`/mnt/data`が引き継がれない可能性がある。
このhandoffと必要CSV・成果物を再アップロードする。

---

# 20. 新チャットで最初に確認すること

1. handoffを最後まで読む
2. 禁止ソースを開かない
3. 必要CSVが存在するか確認
4. CSV timeがOPEN時刻であることを再確認
5. 最新行をclosedとして扱う
6. source parityを確認
7. MT5セッションカレンダーを再構築
8. cost1/2/3契約を確認
9. Stage260の4イベント定義をコード前に文書化
10. まずイベント母集団と対照群を比較
11. 差があるイベントだけ特徴量探索
12. audit-onlyを維持

---

# 21. 次チャット開始用プロンプト

repo: knitanr-a11y/xauusd-signal-lab

GOLD V3の続きです。

まず添付の
`NEXT_CHAT_HANDOFF_GOLD_V3_STAGE259_DONE_STAGE260_EVENT_FIRST_NEXT_COMPLETE_20260620.md`
を最後まで読んで、Stage260から続けてください。

絶対禁止:
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- fallbackに使わない
- GOLD V3はaudit-only
- MT5発注、Discord通知、live hook、autotrade禁止
- CSV最新行はclosed
- CSV timeはローソク足OPEN時刻
- HTFはsource_close_time <= decision timeのみ
- 同一M1 TP/SLはSL優先
- 1 setup 1 trade
- NO_SIGNAL時は何もしない
- 2026を見て2025条件を変更しない
- candidate poolを恣意的に削らない
- CSV行番号ではなく時刻で結合する
- MFE/MAEはホライズン終端まで計算する
- MT5日付変更・週末・祝日短縮をまたぐ取引は禁止

現在:
`GOLD_V3_259_NORMAL_LOWVOL_SPECIALIST_SEARCH_DONE_AUDIT_ONLY`

現在の安全解釈:
- HIGH: audit/shadow研究候補
- NORMAL: NO_SIGNAL
- TRANSITION: NO_SIGNAL
- 実運用昇格不可

次:
`GOLD_V3_260_EVENT_FIRST_EDGE_DISCOVERY_AUDIT_ONLY`

Stage260では条件総当たりをやめ、次の4イベントの母集団エッジをmatched controlと比較してください。

1. MT5セッション開始後のオープニングドライブ
2. 前日高値・安値のスイープと回収
3. H1/H4複数回反応価格の突破後初回リテスト
4. 長時間圧縮後の初回拡大

必須:
- 同曜日・同MT5時間・同ATR帯・同レジームの非イベント対照群
- MFE/MAE
- TP/SL先着
- cost0/1/2/3
- PF、期待値、DD、連敗
- 月別・四半期別
- LONG/SHORT
- 2025前半で発見
- 2025後半で選定
- 2026へ無変更固定
- 時刻シフト、水準シフト、方向反転、日付ランダム化、レジーム逆割当のプラセボ
- 母集団自体に差がないイベントは特徴量追加前に不採用
- 実運用昇格禁止

最初はE2「前日高値・安値のスイープと回収」から開始してください。
