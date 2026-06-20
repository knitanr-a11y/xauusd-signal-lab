# GOLD V3 Stage260 E8 実データ監査
## 高tick activity下の吸収・拒否と反対方向受容

作成日: 2026-06-20  
正式状態: `GOLD_V3_260_E8_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## 結論

E8はentryのlive再現性を完全に満たしたが、性能は明確に不合格だった。

- batch / streaming raw anchor: 533 / 533
- 完成候補: 205 / 205完全一致
- prefix invariance: 40地点PASS
- restart invariance: 11地点PASS
- H1/H4 future-source違反、entry前倒し、candidate_key重複: 0件
- 同時刻M1 OPEN欠落: 0件

全固定グリッド最大cost0期待値は`+0.477552 USD`で、事前基準`+3 USD`を大きく下回った。2025H1のcost2最良セルも`-0.478056 USD / PF0.890151`で赤字だったため、matched control・placebo・追加特徴量へ進まず早期不採用とした。

## 結果前に固定したE8

定義コミット:

`d63b9c87e1b497d2dfab4651ad2cd2a3a5d01f8c`

M5の同一server-slot因果tick-volume基準を使用した。

volume条件:

- slot volume ratio 1.80以上
- slot causal percentile 0.90以上
- global causal percentile 0.85以上

吸収shape:

- rangeが0.10 H1 ATR以上
- TR ratio 1.25以上
- body ratio 0.30以下
- 片側wick ratio 0.55以上
- 優勢wickが反対wickの1.50倍以上
- レンジ端から45%以上close-back

上ヒゲ吸収はSHORT、下ヒゲ吸収はLONG。anchor後2本以内にanchor closeから0.03 H1 ATR以上反対方向へ確定し、直前終値更新かつ反対方向実体を満たした場合だけentryとした。

## live再現性監査

完全一致列:

- candidate_key
- direction
- anchor_time
- decision_time
- entry_time
- entry_price_source_time
- anchor OHLC / range
- anchor H1 ATR14
- tick_volume
- slot median / ratio / percentile
- global volume percentile
- body ratio
- upper / lower wick ratio
- TR ratio

追加監査:

- prefix 40/40 PASS
- restart 11/11 PASS
- candidate_key重複 0
- H1/H4 future-source違反 0
- entry_time < decision_time 0
- M1欠落 0

## 結果経路

| horizon | 完了件数 | MFE平均 | MAE平均 |
|---|---:|---:|---:|
| 60分 | 201 | 12.14 | 14.65 |
| 120分 | 192 | 15.54 | 19.99 |
| 180分 | 183 | 18.66 | 23.51 |
| 240分 | 172 | 21.31 | 25.55 |

全ホライズンでMAE平均がMFE平均を上回った。高activityの長いヒゲを単純な反転吸収と解釈しても、逆方向優位を作れなかった。

## 固定TP/SL

全期間の粗上限診断で最良:

- horizon 120分
- TP20 / SL5
- 件数192
- cost0期待値 `+0.477552 USD`
- PF `1.142413`

事前基準3ドルへ届かない。

## 発見・選定・固定検証

2025H1だけで選んだcost2最良セル:

- horizon 60分
- TP20 / SL15

| 期間 | 件数 | cost0期待値 | cost2期待値 | cost2 PF |
|---|---:|---:|---:|---:|
| 2025H1 | 72 | +1.522 | -0.478 | 0.890 |
| 2025H2 | 90 | -0.409 | -2.409 | 0.558 |
| 2026H1部分 | 39 | -1.057 | -3.057 | 0.679 |

発見期間の最良セル自体が赤字であり、正式候補は0件。

月別cost2はプラス6か月、マイナス12か月。

## 方向診断

固定セルcost2:

- LONG: -2.167 USD / PF0.620
- SHORT: -1.082 USD / PF0.825

両方向とも赤字であり、方向フィルターで救済できる余地もない。

## 採否

live再現性:

- batch/streaming完全一致: PASS
- prefix invariance: PASS
- restart invariance: PASS
- source timing違反0件: PASS
- M1 fail-closed: PASS

性能:

- 最大cost0期待値3ドル以上: FAIL
- 2025H1 cost2プラス・PF1.10以上: FAIL
- 2025H2固定条件プラス・PF1.10以上: FAIL
- 固定2026プラス: FAIL

事前契約に従い、matched controlとplaceboは未実施。

## 判定

`LIVE_REPRODUCIBILITY_PASS_PERFORMANCE_REJECT`

E8はliveで同じentryを再現できるが、高tick activity下の長いヒゲを反転吸収として使う優位性はない。

次は、絶対volume burstではなく、低activityが連続した後の最初のactivity ignitionという独立仮説をE9で監査する。

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
