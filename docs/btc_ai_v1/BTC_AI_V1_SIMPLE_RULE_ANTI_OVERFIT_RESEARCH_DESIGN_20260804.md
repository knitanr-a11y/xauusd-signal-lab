# BTC AI V1 — シンプル裁量型ルール研究・過学習防止設計

日付: 2026-08-04

正式方針:

`SIMPLE_HUMAN_READABLE_RULES_WITH_SMALL_PREREGISTERED_HYPOTHESIS_SET_AND_FRESH_PROSPECTIVE_CONFIRMATION`

## 1. 目的

次のBTC研究では、複雑なAIや大量の閾値探索ではなく、人がチャート上で説明できるシンプルな値動きルールを研究する。

ただし、シンプルなルールでも、結果を見てから方向・時間帯・ATR帯・期間・EMA値・SL/TPを選べば過学習する。したがって、ルールの単純さだけでなく、研究手順そのものを固定する。

## 2. 既存研究との境界

2023～2026年7月のXM `BTCUSD#` OHLCは、これまでのStages 00–55で広く使用・確認済みである。

したがって、今後その期間で得る成績は:

`RETROSPECTIVE_EXPLORATORY_EVIDENCE_ON_CONSUMED_HISTORY`

として扱う。

これは過去データを使えないという意味ではない。過去データは、実装確認、候補の粗い淘汰、年・半期・コスト・近傍安定性の壊し試験に使う。ただし、過去成績だけで正式採用・live-ready・最終シグナルとはしない。

正式な未使用確認は、ルール凍結後のfresh no-backfill prospective Shadowで行う。

## 3. Stage55との完全分離

Stage55は現在、次の2familyを凍結してuser PCで観測中である。

- `M1_CP30_Q70_M1_BEARISH_EMA20_15M_SHORT_TP2R_MAX240`
- `M5_LEVEL_REJECTION_010_M5_TWO_BAR_BEARISH_SHORT_TP2R_MAX480`

activation cutoff:

`2026-08-04 10:52:00` MT5 broker-server time

新研究はStage55のbranch、checkout、state、model、Q70、confirmation、SL、TP、hold、Discord notifierを変更しない。

新研究は別branch・別cloneで行う。

Proposed branch:

`feature/btc-simple-discretionary-rule-research`

Proposed clone:

`C:\xauusd-signal-lab-btc-simple-rules`

## 4. 第一段階の研究形式

第一段階はdeterministic rules onlyとする。

- MLなし
- AI scoreなし
- outcomeを使ったfeature selectionなし
- 外部市場、funding、open interest、order flow、tick volume、real volumeなし
- closed OHLCのみ
- MT5 broker-server naive time
- exact M1 entry、欠損時fallbackなし
- same-M1 TP/SL collisionはSL優先
- roundtrip costは1 BTCあたり22.50 USD

各familyは原則として次だけで構成する。

1. 上位足contextを最大1つ
2. setupを1つ
3. confirmationを1つ
4. 固定entry/SL/TP/maximum hold

## 5. 仮説数の上限

結果を見る前に、最大4familyを登録する。

初期family候補:

1. `HTF_TREND_PULLBACK_RECLAIM_RESUME`
2. `PREVIOUS_OR_LOOKBACK_HIGH_LOW_SWEEP_CLOSE_BACK`
3. `COMPRESSION_BREAKOUT_FIRST_RETEST`
4. `ATR_IMPULSE_EXHAUSTION_SIMPLE_REVERSAL`

各familyについて:

- 正式base rule: 1個
- robustness近傍: 最大2個
- 全体上限: 12 configurations

近傍構成は最良parameterを選ぶためではない。base ruleが一点依存かを壊すためだけに使う。

重要:

- baseが不合格で近傍だけが合格しても、近傍を新baseへ昇格しない
- 良かった方向だけ残さない
- 良かった年・月・D1・ATR帯だけ残さない
- 結果後に第5familyを追加しない
- 大量gridを「シンプル研究」と呼ばない

## 6. 実行前に凍結する項目

各familyについて、結果を一切開く前に次をGitHubへ保存する。

- family ID
- 売買方向または対称方向の扱い
- 使用timeframe
- higher-timeframe context
- setup
- confirmation
- decision timestamp
- exact entry timestamp
- SL
- TP
- maximum hold
- same-bar priority
- cost
- one-position/non-overlap rule
- missing-M1 rule
- frequency floor
- 合格・不採用gate
- 近傍2個の変更点

数値gateは次チャットで提案し、ユーザー承認後にfreezeする。freeze前にPnL、PF、勝率、年別成績を実行・閲覧しない。

## 7. 過去期間の使い方

過去を完全なuntouched holdoutとは呼ばないが、計算手順は時系列で固定する。

- 2023: 実装・イベント成立・時刻整合のsanity audit
- 2024: temporal stress slice A
- 2025: temporal stress slice B
- 2026-01～2026-07: consumed diagnostic slice C

すべてのルールを実装・凍結した後、同じ一回のformal historical runで全sliceを出力する。2024を見て2025用に修正しない。2025を見て2026用に修正しない。

## 8. 必須評価

最低限、次を全base familyについて同じ形式で報告する。

- trades
- trades/month
- win rate
- PF
- net
- maximum drawdown
- year/half-year/month results
- LONG/SHORT split when applicable
- maximum winner removed
- fixed cost ×2
- base versus preregistered neighbors
- profit concentration by month and top trades
- exact-M1 gap count
- no-overlap and same-M1 collision audit

不採用結果も削除しない。

## 9. 過学習防止の判定原則

- PF最大の構成を選ばない
- base ruleを先に指定する
- neighborsは選択候補ではなく壊し試験
- 成績が悪いfamilyを黙って削除しない
- 件数不足を結果後の閾値緩和で救済しない
- 勝った方向だけを後付け採用しない
- 1期間だけ良い候補を採用しない
- 1～2 tradeの大勝ち依存を採用しない
- Discord画像や裁量印象をselection labelにしない

## 10. 最終判定

歴史検証を通過した候補も、状態は:

`RESEARCH_CANDIDATE_REQUIRES_FRESH_PROSPECTIVE_CONFIRMATION`

までとする。

その後、別のno-backfill Shadowで次を事前固定する。

- activation cutoff
- minimum closed trades
- minimum calendar months
- 途中parameter変更禁止
- 悪い観測も全件保存

fresh Shadowを通過するまで、MT5 orders、live trading、live-ready、final signalはOFF。
