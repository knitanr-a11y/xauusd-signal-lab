# BTC AI V1 — 多角的OHLC研究・相乗効果検証結果（Stages 41–44）

日付: 2026-08-04

正式状態:

`BTC_AI_V1_OHLC_MULTIPERSPECTIVE_STAGE44_COMPLETE_NEW_ATR_SHOCK_SPECIALIST_SUPPORTED_INTERACTION_SYNERGY_ROBUST_DIAGNOSTIC_2026_UNOPENED`

## 今回試した視点

同じOHLCだけを使い、既存条件の微調整ではなく次を別研究として実行した。

- inside-barの騙し
- 3本足break trap
- 高値・安値を両方抜く二段騙し
- 前日高安・前日終値の回収
- equal high / equal low liquidity sweep
- 3本足imbalanceの埋め戻し
- EMA加速失敗、EMA false cross、EMA20/50 squeeze
- ATR shock後の二段目拒否
- round number、フィボ押し、連続足、star/engulf、opening range
- AIがQ90で落とした発火のsecond chance
- 既存候補間の同方向・反対方向・勝敗後の発火順序
- 候補間の4時間conflict vetoと勝ち直後の追随抑制

2026、外部情報、volume、Shadow、Discord、MT5注文は使用していない。

## Stage 41A — 新しい低頻度スペシャリスト

2023だけで選択し、2024と2025を別々に検証した。

- 10 family
- 36 subtype
- 19,963 event
- 432 exact-M1 execution configurations
- discovery selected: 4
- formal supported: 1

### 残った候補

`ATR_SHOCK_SECOND_REJECTION_L2_LONG__SL0.75_TP2.00_H240`

意味:

1. 大きな上方向M15 shock足（range >= 2.5 ATR、body fraction >= 0.60）が出る。
2. 次の足がshock足中心線まで押し戻す。
3. 2本後のclosed M15が中心線より上で再び拒否し、close position >= 0.70、signed body >= 0.20 ATR。
4. 次のexact M1 openでLONG。
5. SL 0.75 ATR、TP 2 ATR、最大240分、同一M1衝突はSL優先。

| 期間 | 件数 | PF | 純損益 | DD |
|---|---:|---:|---:|---:|
| 2023 discovery | 19 | 1.1854 | +149.37 | 620.56 |
| 2024 validation | 14 | 1.2633 | +462.04 | 584.38 |
| 2025 validation | 16 | 2.4140 | +2412.41 | 1428.78 |
| 2023–2025 | 49 | 1.7088 | +3023.82 | 1428.78 |

- positive halfyears: 4/6
- month block-bootstrap P(net>0): 0.8730

## Stage 41B — AIが落とした発火のsecond chance

固定済みmeta LONG/SHORTでQ90不採用だった2,837発火から、方向回復、adverse sweep reclaim、反対break、compression releaseを1/2/4/8本後に検証した。

- events: 3,156
- subtype: 32
- execution configurations: 384
- discovery selected: 15
- diagnostic supported: **0**

結論: AIが落とした発火を遅れて拾い直す単純なsecond-chanceは相乗効果なし。

## Stage 41C — 既存3候補の固定相互作用

基準global one-position:

- 395件
- PF 1.3611
- 純損益 +27612.88

直近4時間に別sourceの反対方向発火があったシグナルを見送る固定veto:

- 383件
- PF 1.4244
- 純損益 +30699.43

2024H2では若干低下したが、2025H1・2025H2はどちらも改善した。これはこの時点ではretrospective synergy diagnosticであり、未使用holdoutの正式採用ではない。

## Stage 42 — 新候補を加えた4source相乗効果

4source:

- Stage37 expansion midpoint failure LONG
- Stage38 meta LONG
- Stage38 meta SHORT
- Stage41 ATR shock second rejection LONG

### 基準

- 416件
- PF 1.3696
- 純損益 +29231.32

### 固定interaction policy

`OPPOSITE_VETO_PRIOR_4H + SUPPRESS_SAME_DIRECTION_AFTER_RESOLVED_WIN_PRIOR_4H`

- 2024H2: 125件、PF 1.6556、+12647.48
- 2025H1: 121件、PF 1.4041、+10715.49
- 2025H2: 149件、PF 1.3802、+10173.90
- 合算: 395件、PF 1.4621、+33536.87
- positive months: 11
- positive D1 regimes: 3/3

コストstress:

- extra 11.25 USD/trade: PF 1.3872、+29093.12
- extra 22.50 USD/trade: PF 1.3171、+24649.37

基準との差のmonth-bootstrap:

- observed delta: +4305.55
- P(delta>0): 0.9820
- 5%–95%: +896.81 ～ +7773.37

基準から除かれた22件はPF 0.3203、純損益 -4717.75。DET、meta LONG、meta SHORT、新trapの全sourceから悪い発火を除いている。

## Stage 43 — 変な価格幾何

- 28 subtype
- 83,084 event
- 336 execution configurations
- round number、前日終値、フィボ押し、run exhaustion、EMA false cross、double touch neckline、star/engulf、opening range等
- formal supported: **0**

結論: 見た目だけのローソク形状や丸数字より、shock後の経路と複数候補の発火関係の方が有効だった。

## Stage 44 — 壊し試験

### 新ATR shock候補

- nonbase variants: 14
- combined PF > 1: 0.8571
- 2024/2025両方net positive: 0.7857
- matched-random net percentile: 0.9675
- matched-random PF percentile: 0.9730

lag1では定義上eventが0となり、lag4は弱化した。したがって「shock直後」ではなく、1本押して2本後に再拒否する経路が重要。一方、shock threshold、close-position、SL/TP、保有時間、コストの多数の近傍では合算PF>1を維持した。

### interaction policy

| 試験 | 件数 | PF | 純損益 |
|---|---:|---:|---:|
| WINDOW_2H | 405 | 1.4032 | +30583.88 |
| WINDOW_4H | 395 | 1.4621 | +33536.87 |
| WINDOW_6H | 387 | 1.4288 | +30591.00 |
| DROPOUT_NONE | 395 | 1.4621 | +33536.87 |
| DROP_DET_STAGE37 | 206 | 1.7067 | +24776.99 |
| DROP_META_LONG | 317 | 1.3134 | +18678.30 |
| DROP_META_SHORT | 313 | 1.3654 | +21896.74 |
| DROP_TRAP_STAGE41 | 376 | 1.4388 | +31062.07 |

- same-count random-selection percentile: 0.9940
- source timestamp month-shift placebo percentile: 0.9890

2h・4h・6hのすべてでPF>1.40。4hだけの一点最適化ではない。全sourceを残した4h policyが最大netで、Stage41候補の追加もnetを増加させた。

## 解釈上の境界

- ATR shock候補は2023 discovery、2024/2025 validationを通した正式research candidate。
- interaction policyは既存component結果を見た後に仮説化したため、robustなretrospective diagnosticであり、未使用holdoutを通した正式live policyではない。
- 2026は開いていない。
- Shadow、Discord、MT5、live-ready、final signalはすべてOFF。
