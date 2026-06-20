# GOLD V3 Stage261 定義固定
## Stage260候補ポートフォリオ・情報不足監査

作成日: 2026-06-20  
状態: `GOLD_V3_261_CANDIDATE_PORTFOLIO_INFORMATION_GAP_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage260 E2〜E8で得られた候補を同一形式へ統合し、単一候補の追加探索を続ける前に、次を監査する。

1. 候補が同じ潜在的値幅イベントを重複検出しているか。
2. 固定セル損益が独立しているか、同時に悪化しているか。
3. 複数の小さなedgeを固定ルールで合算すると期間安定性が改善するか。
4. OHLC＋tick_volumeだけで改善余地が残るか、追加情報源が必要か。

この監査は既知データを使うretrospective meta-auditであり、結果が良くてもlive昇格や正式候補採用を行わない。次の未見データ監査または新しい外部情報取得方針を決めるためだけに使用する。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- Stage260で既に固定された各候補の定義・方向・entryを変更しない。
- 各候補の損益セルは、そのStageで2025H1だけから選ばれたfrozen discovery cellを使用する。
- 全期間最良セル、方向別最良、月別最良、failure-type別最良を使用しない。
- Stage261で候補の閾値、entry、TP、SL、horizonを再最適化しない。
- 2026を見て候補、重み、優先順位を変更しない。
- この監査結果からMT5発注、通知、live hook、order payload、autotrade、final signalを作らない。

## 候補群

### live-parity済み群

- E5: displacement後の初回浅押し・再受容
- E6: displacement継続失敗後の反転受容
- E7: tick-volume impulse＋価格受容
- E8: tick-volume absorption＋反対方向受容

この4候補だけをportfolio eligibility監査の対象とする。

### 診断専用群

- E2: prior-day sweep/reclaim
- E3: multi-reaction level breakout/retest
- E4: compression first expansion

E2〜E4はlive parityがStage261契約で確認されていないため、イベント重複と情報系統の診断だけに使用し、portfolio PnLへ含めない。

## 固定セル

- E2: H60 TP15 SL5
- E3: H60 TP10 SL5
- E4: H240 TP25 SL15
- E5: H240 TP25 SL10
- E6: H240 TP10 SL15
- E7: H240 TP25 SL10
- E8: H60 TP20 SL15

すべて各Stageの2025H1 discovery cellをそのまま使用する。

## canonical trade ledger

候補ごとに次を統一する。

- candidate_id
- candidate_family
- live_parity_tier
- entry_time
- direction
- half / quarter / month
- fixed_horizon
- fixed_tp
- fixed_sl
- result
- exit_min
- exit_time = entry_time + exit_min
- gross_pnl
- cost2_pnl

同じcandidate_id内でentry_time重複がある場合はデータ契約FAIL。

## 重複監査

候補ペアごとに次を計算する。

- entry時刻差 ±5 / ±15 / ±30 / ±60 / ±120分以内のevent overlap率
- overlap時の同方向率
- overlap時の反対方向率
- 同一120分window内で少なくとも一方が発生する件数
- Jaccard-like overlap: matched pairs / union events

matchingは各候補ペアで時刻差が最小のものを非復元で対応させる。結果や方向を使ってmatchingを選ばない。

## 損益相関監査

固定セルcost2を使用する。

- 日次PnL相関: eventがない日は0
- 週次PnL相関
- 月次PnL相関
- 同日発生tradeだけの符号一致率
- rolling 3か月相関

件数が少ない相関はnを明記し、強い結論を出さない。

## 事前固定ポートフォリオ

### P1 PARALLEL_EQUAL_UNIT

E5〜E8の固定セルtradeを各1unitでそのまま合算する。候補重複時も全tradeを保持する。これは共通リスク露出診断用であり、実運用形ではない。

### P2 ONE_ACTIVE_FIRST_COME

全候補をentry_time順に並べ、portfolioにactive tradeがない時だけ最初の候補を受け入れる。

- active_until = accepted tradeのexit_time
- `entry_time < active_until`の候補は抑制
- 同一entry_timeのtieはcandidate_id昇順 E5→E6→E7→E8
- 損益、方向、将来結果を優先順位に使わない

### P3 ONE_ACTIVE_120M

P2と同じだが、accepted entryから固定120分は全候補を抑制する。Stage260の共通イベント重複を除く診断用。

### P4 E5_E7_PREDECLARED_COMPLEMENT

E5とE7だけを各1unitで並列合算する。理由は結果ではなく、Stage260定義上の情報源が異なるためである。

- E5: OHLC directional displacement/pullback
- E7: causal tick-volume impulse/acceptance

E6/E8はそれぞれE5/E7の反転系であり、まず親系統間の補完性を確認する。

## portfolio評価

各P1〜P4についてcost2で次を表示する。

- trade数
- PnL
- expectancy
- PF
- win rate
- max drawdown
- max losing streak
- 月別PnL
- 2025H1 / 2025H2 / 2026H1部分
- positive / negative month数
- candidate別寄与
- 同時露出数または抑制件数

## 小edge継続判断基準

Stage261は昇格判定ではなく、次の未見データ研究へ進む価値を判定する。

`PORTFOLIO_ROUTE_WORTH_NEW_HOLDOUT`とするには、事前固定P2またはP4がすべて満たす必要がある。

1. cost2 expectancyが2025H1、2025H2、2026H1部分のすべてで0以上。
2. cost2 PFが全期間1.10以上。
3. 18か月中positive monthが10か月以上。
4. 単一候補が全PnLの80%以上を占めない。
5. candidate間の日次PnL相関が0.50未満の組み合わせを含む。
6. 全期間max drawdownが、構成候補の単純合計max drawdownより25%以上小さい。

既知データ上でこの基準を通過してもlive昇格は禁止し、新しい未見holdout期間が必要。

## 情報不足判定

次のいずれかなら`NEW_INFORMATION_REQUIRED`とする。

- 全候補の日次・月次損益相関が高く、同じ潜在値幅factorを再包装している。
- P2/P4が期間別に安定しない。
- 2026劣化が複数候補で共通する。
- MFE拡大とMAE拡大が候補横断で同時に発生する。
- tick_volume候補もprice-only候補と同じ時刻へ集中する。

追加情報の優先順位は結果後に次のカテゴリ単位で決め、個別閾値を最適化しない。

- tick arrival timing / sub-bar tick path
- bid/ask and spread path
- external USD/rate/futures synchronization
- pre-known macro calendar
- broker/source robustness

## 判定可能な正式状態

- `GOLD_V3_261_PORTFOLIO_ROUTE_WORTH_NEW_HOLDOUT_AUDIT_ONLY`
- `GOLD_V3_261_NEW_INFORMATION_REQUIRED_AUDIT_ONLY`
- `GOLD_V3_261_INSUFFICIENT_COMMON_LEDGER_BLOCKED_AUDIT_ONLY`

いずれもlive-readyではない。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
