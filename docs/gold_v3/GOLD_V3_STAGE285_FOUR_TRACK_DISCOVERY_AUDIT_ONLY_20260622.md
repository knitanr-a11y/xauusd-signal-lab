# GOLD V3 Stage285 4系統候補探索監査（2026-06-22）

正式状態:
`GOLD_V3_285_CROSS_ASSET_LONG_SHADOW_LEAD_OTHER_FAMILIES_NO_DISCOVERY_AUDIT_ONLY`

## 1. 入力データ

XMTrading-MT5 3から同一server・同一取得方式で次を取得した。

- GOLD#
- SILVER#
- USDJPY#
- EURUSD#
- US500Cash#
- US100Cash#
- M5 / M15 / H1 / H4 / D1
- 2023-01から2026-06-22

30ファイルすべてAVAILABLE、重複0、非単調0、取得error 0。
既存GOLD CSVと今回のGOLD#を重複期間で比較し、OHLC、tick volume、spread、real volumeは全時間足で完全一致した。
USD indexとyield proxyは連続履歴を確認できなかったため使用せず、代替sourceも使わない。

## 2. 検証契約

- M15確定ごとのdecision
- 外部M15/H1/H4はbar close後のみas-of結合
- 2024 development
- 2025 confirmation
- 2026 display only
- M5 triggerは次の60分以内
- entryはtrigger確定後の次M5 open
- M1 first touch、同一M1はSL
- rollover overlay、基準459件優先
- cost 0.60 / 1.00 USD per 1oz
- 最低0.01 lot = 1oz

## 3. Cross-asset

Ridge walk-forward modelのAUC:

| model | 2024 | 2025 | 2026 |
|---|---:|---:|---:|
| CROSS LONG | 0.579 | 0.598 | 0.554 |
| CROSS SHORT | 0.570 | 0.548 | 0.527 |

LONGのq90 target liftは1.29 / 1.44 / 1.03で、外部相場にはLONG確認情報が残った。
SHORTは実売買へ変換すると安定しなかった。

### Raw cross LONG shadow lead

`CROSS_LONG_Q95_EMA20_E175_CD120`

- external score >= preceding six-month q95
- M5 EMA20 reclaim
- next M5 open LONG
- TP1.75ATR / SL1.0ATR / max6h
- cooldown120m

| 年 | 件数 | PF | cost1 PF | 利益 | DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 90 | 1.428 | 1.250 | +96.72 | 39.71 |
| 2025 | 87 | 1.123 | 1.039 | +52.09 | 149.36 |
| 2026途中 | 64 | 1.117 | 1.077 | +77.82 | 218.14 |

3期間ともプラスだが、最低lot固定ではH1 ATR拡大によりDDが大きすぎる。
月次損益相関はStage280=0.261、Stage281=0.126で、候補としては比較的独立している。

### 最低lot用のentry risk gate診断

ロットを下げられないため、entry時点で
`H1 ATR + 0.60 <= 10 USD`
の時だけ候補を許可する診断を行った。

`CROSS_LONG_Q95_EMA20_E175_FULL_SL_CAP10_SHADOW`

| 年 | 件数 | PF | cost1 PF | 利益 | DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 89 | 1.354 | 1.183 | +80.16 | 39.71 |
| 2025 | 44 | 1.252 | 1.128 | +38.07 | 38.61 |
| 2026途中 | 0 | - | - | 0.00 | 0.00 |

2026は全候補のminimum-lot full SLが10 USDを超えたため0件だった。
これは2026結果を方向・score・exitへ戻して調整したものではないが、cap gridを確認後に選定したためSHADOW限定とする。

### 既存④との統合（Stage285再評価のbalanced controller）

既存Stage280+281:

| 年 | 件数 | PF | 利益 | DD |
|---|---:|---:|---:|---:|
| 2024 | 228 | 1.675 | +260.86 | 28.94 |
| 2025 | 215 | 1.847 | +478.91 | 42.92 |
| 2026途中 | 99 | 2.688 | +851.17 | 66.06 |

cap10 cross追加:

| 年 | 件数 | PF | 利益 | DD |
|---|---:|---:|---:|---:|
| 2024 | 282 | 1.560 | +295.58 | 41.88 |
| 2025 | 236 | 1.798 | +507.75 | 61.02 |
| 2026途中 | 99 | 2.688 | +851.17 | 66.06 |

2024/2025の件数は+54/+21増えたが、DDも+12.94/+18.09増えた。
2026はrisk gateにより追加0件なので既存値と同じ。

cap8.5ではportfolio DDをほぼ増やさず2024/2025件数を286/231まで増やせたが、候補単体の2025 cost1 PFが0.943のため正式leadにはしない。portfolio synergy diagnosticとしてのみ保存する。

## 4. M1～M15形状クラスタ

2023だけで12 clusterの中心を固定し、2024以降へ適用した。
最良の高頻度候補:

`SHAPE_LONG_C6_EMA20_E175_CD120`

| 年 | 件数 | PF | cost1 PF | 利益 | DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 292 | 1.044 | 0.922 | +40.29 | 99.37 |
| 2025 | 297 | 1.161 | 1.085 | +260.69 | 290.87 |
| 2026途中 | 110 | 1.110 | 1.074 | +143.37 | 387.23 |

件数は多いが2024 cost stressで負け、DDが大きすぎる。NO_DISCOVERY。

## 5. 失敗ブレイク・ボラ収縮拡大

failed breakdown LONGの最良でもPFは0.975 / 1.056 / 1.024で、独立edgeを確認できなかった。

収縮拡大near miss:
`SQ_Q20_D0P35_LONG_EMA20_E175_CD120`

| 年 | 件数 | PF | 利益 | DD |
|---|---:|---:|---:|---:|
| 2024 | 62 | 1.208 | +41.91 | 45.48 |
| 2025 | 69 | 1.370 | +132.76 | 111.55 |
| 2026途中 | 29 | 0.552 | -182.19 | 215.48 |

2026を見て追加条件で救済せず、NO_DISCOVERY。

## 6. SHORT専用

6～8時間契約のnear miss:
`SHORT_EXHAUST_Q90_EMA20_E225_CD120`

| 年 | 件数 | PF | cost1 PF | 利益 | DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 76 | 1.256 | 1.138 | +71.08 | 57.84 |
| 2025 | 77 | 1.109 | 1.045 | +54.13 | 124.23 |
| 2026途中 | 25 | 0.830 | 0.808 | -69.13 | 164.91 |

SHORT専用model、external SHORT、shape SHORT、failed breakout SHORTを比較したが安定候補なし。
既存E125_100_4Hも追加確認したが、2024/2025を通過するSHORTは0件だった。
したがってSHORTはNO_DISCOVERY。

## 7. 正式判断

- 新規ACTIVE追加: NONE
- Stage280: unchanged
- Stage281: unchanged
- Stage284: unchanged
- Cross raw LONG: SHADOW_LEAD
- Cross cap10: SHADOW_NEAR_MISS
- cap8.5 portfolio synergy: DIAGNOSTIC_ONLY
- shape cluster: NO_DISCOVERY
- failed breakout / squeeze: NO_DISCOVERY
- SHORT: NO_DISCOVERY
- live_ready / final signal / MT5 order / Discord / partial close: OFF

次に必要なのは、cap10 crossを新しい未見期間でSHADOW蓄積すること。
内部OHLCの追加threshold tuningで救済しない。
