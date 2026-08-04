# BTC AI V1 — 累積研究記録 through Stage55 / 次はシンプル裁量型ルール

日付: 2026-08-04  
repository: `knitanr-a11y/xauusd-signal-lab`  
authoritative branch: `feature/btc-ai-v1-data-acquisition`

## 1. この文書の目的

ここまでのBTC AI V1研究を失わず、Stage55 prospective Shadowを凍結したまま、次の独立研究へ進めるための累積記録である。

詳細な数値、実装、契約、監査、失敗記録は既存の `config/btc_ai_v1/`、`docs/btc_ai_v1/`、`scripts/btc_ai_v1/`、`tests/btc_ai_v1/` が正本である。この文書はそれらを置き換えず、現在地と次の研究境界を一か所にまとめる。

## 2. 固定データ・実行契約

- 対象: XM `BTCUSD#`
- closed OHLCのみ
- timeframes: M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- open/as-of足を作らない
- exact M1 entry。entry時刻のM1が欠けていればfallbackしない
- 同一M1でSL/TPへ触れた場合はSL優先
- 1 BTC completed tradeの固定往復cost: 22.50 USD
- 外部市場、funding、open interest、order flow、tick volume、real volumeは未許可

## 3. Stage00–36で得たこと

詳細:

- `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`
- `docs/btc_ai_v1/RESEARCH_HISTORY_STAGE31_36_ADDENDUM_20260804.md`

主な結論:

- deterministic rule、binary ML、多様なclassifier、continuous target、pairwise rankingを広く試した
- 2024–2025で残ったML finalistは、消費済み2026診断で全滅した
- failure root causeは、固定costだけでなくOHLC state transitionとconditional meaning shiftによるlate SHORT selectionだった
- state/phase/transition expert、sequence model、event anchor、path shape、delayed confirmationも正式survivorなし
- rolling window、soft recency、expanding/decay consensus、causal cooldownでもsupported configurationなし

Stage36 formal status:

`BTC_AI_V1_OHLC_ONLY_ORDERING_AND_ADAPTATION_SEARCH_EXHAUSTED_THROUGH_STAGE35_NO_SUPPORTED_CANDIDATE`

この結果は「OHLCに研究余地が一切ない」という意味ではない。同じscore、window、threshold、month、D1、directionを後付けで救済する余地がないという意味である。

## 4. Stage37 — deterministic deception specialist

詳細:

`docs/btc_ai_v1/BTC_AI_V1_STAGE37_DECEPTION_SPECIALIST_RESULT_20260804.md`

残った候補:

`EXPANSION_MIDPOINT_FAILURE_L2_LONG__SL1.00_TP2.00_H480`

- 2024 discovery: 141件、PF 1.4514、net +10,903.70
- 2025 validation: 132件、PF 1.0728、net +2,133.97
- 合算: 273件、PF 1.2438、net +13,037.67
- robustness gateはPASS

ただし後の2026診断ではFAILし、promotionは停止された。

## 5. Stages38–39 — AI meta fakeout

詳細:

`docs/btc_ai_v1/BTC_AI_V1_STAGE38_39_META_FAKEOUT_RESULT_20260804.md`

固定meta candidates:

- LONG: `UNION_FIRST_CROSS__L1__LONG__SCORE_CONFIRM_STATE__LGBM_D3__Q90`
- SHORT: `UNION_FIRST_CROSS__L1__SHORT__SCORE_CONFIRM__LGBM_D3__Q90`

2024H2+2025 one-position stack:

- 188件
- PF 1.6033
- net +20,700.13
- DD 3,376.32
- robustness gateはPASS

しかし2026診断ではLONG/SHORT/stackすべてFAILし、promotionは停止された。

## 6. Stages41–44 — multi-perspective / ATR shock / interaction

詳細:

`docs/btc_ai_v1/BTC_AI_V1_STAGE41_44_MULTIPERSPECTIVE_SYNERGY_RESULT_20260804.md`

正式research specialistとして残った候補:

`ATR_SHOCK_SECOND_REJECTION_L2_LONG__SL0.75_TP2.00_H240`

2023–2025:

- 49件
- PF 1.7088
- net +3,023.82
- DD 1,428.78

4source interaction policyはretrospective diagnosticとして強かったが、未使用holdoutを通した正式live policyではなかった。

Stage43のround number、fib、opening range、star/engulf等の見た目中心の価格幾何はformal supported 0だった。

## 7. Stage45 — consumed 2026 diagnosis

詳細:

`docs/btc_ai_v1/BTC_AI_V1_STAGE45_CONSUMED_2026_DIAGNOSTIC_RESULT_20260804.md`

2026年1–7月:

- Stage37 deterministic: FAIL
- meta LONG: FAIL
- meta SHORT: FAIL
- meta stack: FAIL
- 2h/4h/6h interaction policy: 全FAIL
- ATR shock specialist: 10件、PF 1.9082、net +1,084.64

ATR shockは低頻度research specialistとして維持するが、少件数であり単体主力やlive promotionではない。

## 8. Stages46–54からStage55へ

Stage45後も、regime break、低頻度specialist、騙し後の反転SHORTを独立に調べた。詳細な中間成果はbranch上の契約・結果・履歴に残っている。

Stage54の正式survivorは0。ただし2,880構成を確認した後、post-selection diagnosticとして次の2 familyをStage55へ固定した。

1. `M1_CP30_Q70_M1_BEARISH_EMA20_15M_SHORT_TP2R_MAX240`
2. `M5_LEVEL_REJECTION_010_M5_TWO_BAR_BEARISH_SHORT_TP2R_MAX480`

これらは正式validation survivorsではない。過去結果をさらに掘って採用するのではなく、条件固定後のfresh prospective evidenceでmultiple-testing overfitを判定する対象である。

## 9. Stage55 prospective Shadow — 実機状態

詳細:

- `docs/btc_ai_v1/BTC_AI_V1_STAGE55_DUAL_REVERSE_SHORT_PROSPECTIVE_SHADOW_20260804.md`
- `docs/btc_ai_v1/BTC_AI_V1_STAGE55_DISCORD_ENTRY_ALERT_ADDENDUM_20260804.md`
- `config/btc_ai_v1/stage55_dual_reverse_short_shadow_contract_20260804.json`
- `config/btc_ai_v1/current_state_stage55_20260804.json`

実機activation:

- status: `READY_NO_BACKFILL_ACTIVATED`
- activation cutoff: `2026-08-04 10:52:00` MT5
- accepted candidates at activation: 0
- live H4/M15/M5/M1 CSVを使用
- Shadow loopとDiscord sidecarはユーザー報告で起動済み
- Discord実テスト受信の明示記録はこの文書では未確認

Windows実装修正:

- live exporterのcomma-delimited CSVに対応
- research exporterのsemicolon-delimited CSVも維持
- console title/logへ `BTC Stage55 Shadow` / `[BTC_STAGE55_SHADOW]` を追加
- no-backfill baseline、candidate条件、SL/TP、model、Q70、stateは変更していない

観測終了gateはfamilyごとに両方必要:

- closed trade 20件以上
- activationから6暦月以上

## 10. 現在保持する研究資産

### 稼働中

- Stage55 dual reverse-SHORT prospective Shadow
- observation-only
- Discord accepted-entry delivery only
- MT5 orders / live trading / live-ready / final signal: OFF

### 低頻度research specialist

- ATR shock second rejection LONG

### promotion停止・復活禁止

- Stage37 deterministic midpoint failure
- Stage38/39 meta LONG/SHORT/stack
- 2h/4h/6h interaction policy
- 2026だけで再浮上したPF1.3–1.4候補

### 失敗から得た知識

-複雑なAIや大量featureが自動的に方向edgeを作るわけではない
- 同じ情報に対するthreshold/window救済は不安定だった
- 低頻度でも明確なprice pathと非対称payoffを持つ候補は残る場合がある
- 発火数を増やすためだけに条件を緩めると、選択バイアスと不安定性が増える

## 11. 次の独立研究 — シンプルな裁量型ルール

ユーザー提案:

> 裁量では、意外とシンプルな手法の方が勝てる場合がある。

この方向を新しいresearch cycleとして許可する。ただし、すでに2023–2026 OHLCを広く見ているため、歴史結果をuntouched validationとは呼ばない。全historical resultはretrospective exploratory evidenceであり、採用にはfresh no-backfill prospective evidenceが必要である。

### 設計原則

1. 人がチャート上で説明できるルールに限定する。
2. first passはMLを使わない。
3. 1候補は原則として「上位足context 1個 + setup 1個 + confirmation 1個 + fixed execution」で構成する。
4. 小さな事前固定hypothesis listを使い、大量grid searchをしない。
5. indicatorを重ねすぎない。価格、EMA、ATR、直近高安、前日高安など最低限にする。
6. entry前にclosed足だけで判断し、exact M1で実行する。
7. frequencyを増やすための後付け緩和を禁止する。
8. TP/SL/holdは少数の事前固定policyだけを比較する。
9. negative resultも全件保存する。
10. historicalに良くても、fresh Shadowなしではpromotionしない。

### 最初に検討する少数family

A. 上位足trend + 押し戻り + 再開

- H4またはH1の明確なEMA方向
- M15がEMAまたは直近break levelへ押す
- M5/M15の単純な反転closeで再開確認

B. 高安sweep + close-back

- 前日高安または固定lookback高安を一度抜く
- closed barで水準内へ戻る
- 次のbarで戻り方向を確認

C. compression breakout + first retest

- 小さなrange/inside compression
- closed breakout
- 最初のretestがbreak levelを維持

D. impulse exhaustion + simple reversal

- ATR基準の大きな一方向bar
- 追随失敗
- midpointまたは直近小高安の回収

これらは「過去に似た単語を試したことがない」という意味ではない。今回の新規性は、複雑なscoreや大量parameter探索ではなく、少数の人間可読なentry grammarと固定executionを、独立cycleとして事前登録する点にある。

## 12. 次研究の分離

Stage55 checkoutとbranchでは新研究を実装しない。

推奨:

- Stage55 runtime clone: `C:\xauusd-signal-lab-btc-stage55`
- next research clone: `C:\xauusd-signal-lab-btc-simple-rules`
- proposed branch: `feature/btc-simple-discretionary-rule-research`

Stage55のruntime state、local_config、model、candidate logic、notificationは凍結したまま継続する。

## 13. 禁止事項

- Stage55のQ70、confirmation、SL、TP、hold変更
- Stage55 family削除
- Discord通知や目視印象をStage55選択へ利用
- 過去・recovery notification backfill
- 2026で良かった条件だけを復活
- simple rule研究で大量parameter miningを再開
- MT5 order、live trading、live-ready、final signal

## 14. 現在の正式状態

`BTC_AI_V1_STAGE55_ACTIVE_OBSERVATION_CONTINUES_SIMPLE_HUMAN_READABLE_RULE_RESEARCH_AUTHORIZED_SEPARATELY`

Stage55を止めず、次は別branch・別cloneでシンプル裁量型ルールを少数事前登録して研究する。
