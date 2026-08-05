# BTC AI V1 Stage 45 — 2026年1～7月固定条件診断

日付: 2026-08-04

正式状態:

`BTC_AI_V1_STAGE45_CONSUMED_2026_DIAGNOSTIC_COMPLETE_ONLY_ATR_SHOCK_SPECIALIST_POSITIVE_META_AND_INTERACTION_FAILED_NO_LIVE_PROMOTION`

## 結論

2026年1～7月を、2025年までに固定した条件のまま診断した。

- Stage37 deterministic: **FAIL**
- AI meta LONG: **FAIL**
- AI meta SHORT: **FAIL**
- AI meta stack: **FAIL**
- Stage41 ATR shock specialist: **プラス継続**
- 過去に良かった2h/4h/6h interaction policy: **すべてFAIL**
- PF1.3～1.4隔離候補: 一部は再浮上したが、正式復活なし

2026は過去のBTC研究ですでに消費済みであり、未使用holdoutとは呼ばない。ただし、今回の候補・モデル・Q90・確認本数・実行条件は2026集計前に固定し、月別再学習の未来混入監査は全件0だった。

## 固定候補の2026結果

| 候補 | 件数 | 勝率 | PF | 純損益 | DD | プラス月 |
|---|---:|---:|---:|---:|---:|---:|
| Stage37 midpoint-failure LONG | 110 | 30.00% | 0.8981 | -2172.86 | 6092.52 | 4/7 |
| AI meta LONG | 47 | 38.30% | 0.9025 | -851.69 | 3423.63 | 3/7 |
| AI meta SHORT | 33 | 36.36% | 0.8274 | -910.82 | 3075.44 | 3/7 |
| AI meta stack | 80 | 37.50% | 0.8742 | -1762.51 | 5862.72 | 3/7 |
| ATR shock second-rejection LONG | 10 | 40.00% | 1.9082 | +1084.64 | 763.45 | 3/7 |

## ATR shock候補の件数について

2026年は10件、4勝6敗、PF 1.9082、純損益 +1,084.64。

2023～2025の49件を加えると:

- 59件
- 18勝41敗
- PF 1.7524
- 純損益 +4108.45
- 月ブロックbootstrap P(net > 0): 0.9153
- trade-bootstrap PF 5%点: 0.9713

件数は少ない。PFが高い理由は、勝率ではなくTP 2 ATR / SL 0.75 ATRの非対称損益にある。trade-bootstrapのPF 5%点は1未満なので、単体で主力扱いできるほど確実ではない。

一方、発火頻度は2025年16件、2026年7カ月10件で大きく崩れておらず、低頻度専門家として残す価値はある。

## interaction policyの2026結果

| 方式 | 件数 | PF | 純損益 | DD |
|---|---:|---:|---:|---:|
| 条件なしglobal first arrival | 196 | 0.9239 | -2728.75 | 9296.37 |
| 2時間veto＋勝ち直後抑制 | 190 | 0.9086 | -3185.71 | 9721.58 |
| 4時間veto＋勝ち直後抑制 | 185 | 0.8783 | -4179.49 | 10030.53 |
| 6時間veto＋勝ち直後抑制 | 177 | 0.8575 | -4736.88 | 9214.07 |

2024H2～2025では改善していたが、2026では2h/4h/6hすべて基準より悪い。したがって相乗効果ルールは採用しない。

## PF1.3～1.4でも不採用だった理由

PFだけを採用基準にすると、見た期間の偶然を拾う。

### 典型例1: discoveryだけPF1.42

`CLOSE_BREAK_FIRST_RECLAIM_W48_L4_SHORT`

- 2024 discovery PF: 1.4228
- 2025 validation PF: 0.8938、赤字
- 2026 diagnostic PF: 1.8381
- 2024～2026年7月合算 PF: 1.1341

2026で再浮上したが、2025で崩れ、3期間合算も正式基準1.15未満。周期的な監視候補にはできるが、固定採用はできない。

### 典型例2: 2025だけPF1.45

`UNION_COOLDOWN4__L1__LONG__SCORE_CONFIRM_STATE__LGBM_D3__Q90`

- 2024H2 discovery PF: 0.8185
- 2025 PF: 1.4459
- 2026 PF: 0.8910
- 2024H2～2026年7月合算 PF: 1.1010

2025だけを見れば魅力的だが、前後期間でPF1未満。採用していたら2026で赤字だった。

### 典型例3: PF1.32のLogit LONG

`UNION_FIRST_CROSS__L2__LONG__SCORE_CONFIRM__LOGIT_L2__Q90`

- 2024H2 discovery PF: 0.5375
- 2025 PF: 1.3283
- 2026 PF: 1.2444
- 2024H2～2026年7月合算 PF: 1.0943

2025と2026はプラスだが、最初の選択期間で大きく負け、合算PFはまだ低い。2026を見てから復活させると後付けになるため、正式採用ではなくwatchlistに置く。

## 件数の扱い

少件数だから自動不採用ではない。

- 少件数候補: 複数年で方向が一致し、損益構造とbootstrapを確認する。
- 高頻度AI候補: 月、半期、方向、コスト、再学習seedで広く残る必要がある。
- 1期間だけPF1.3～1.4: 採用しない。
- 低件数でも2023選択→2024検証→2025検証→2026診断が同方向: specialistとして残す。

今回、少件数でも残ったのはATR shock候補だけ。

## 因果監査

- underlying future train: 0
- underlying unresolved train: 0
- previous-month calibration violation: 0
- validation-month violation: 0
- meta future train: 0
- meta unresolved train: 0
- 2026を見た後のparameter変更: 0
- 外部情報・volume: 使用なし

## 現在の判断

1. ATR shock候補は低頻度research specialistとして維持。
2. Stage37 deterministicとAI metaは2026 diagnostic failとしてpromotion停止。
3. 2h/4h/6h interaction policyは不採用。
4. PF1.3～1.4再浮上候補は別watchlist。正式候補へ戻さない。
5. Shadow、Discord、MT5、live-ready、final signalはOFF。
