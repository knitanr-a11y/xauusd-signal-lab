# GOLD V3 Stage260 E7 実データ監査
## 因果的tick-volumeインパルス＋価格受容

作成日: 2026-06-20  
正式状態: `GOLD_V3_260_E7_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## 結論

E7はentryのlive再現性を完全に満たしたが、事前固定した性能基準へわずかに届かず不採用とする。

- batchとstreamingのraw anchorは674件で一致。
- 完成候補は205件で完全一致。
- prefix invarianceは40地点PASS。
- restart invarianceは11地点PASS。
- H1/H4 future-source違反、entry前倒し、candidate_key重複は0件。
- entry同時刻M1 OPENがない1件はfail-closedで除外。
- live再現可能entryは204件。

全固定グリッド最大cost0期待値は`+2.971257 USD`で、事前基準`+3.0 USD`に`0.028743 USD`届かなかった。丸めて合格にはしない。

2025H1で選んだ固定セルはcost2期待値`+2.415 USD / PF1.412`だったが、2025H2では`+0.364 USD / PF1.059`となりPF1.10基準を下回り、固定2026では`-0.563 USD / PF0.930`へ低下した。

よってlive再現性PASS、性能REJECTとする。

## 結果前に固定したE7

定義コミット:

`63a49898cf02edc9556ec09f499a7275fdd0e34a`

M5確定足だけを使用した。

### tick-volume条件

- 同一MT5 5分slotの過去60観測、最低20観測
- current barを履歴へ入れる前に中央値と分位を計算
- slot volume ratio 1.80以上
- slot causal percentile 0.90以上
- 直近2,880本global causal percentile 0.85以上

### price条件

- M5実体が因果H1 ATR14の0.12倍以上
- body/range 0.65以上
- M5 TRが過去288本中央値の1.50倍以上
- 終値がレンジ端15%以内

### 受容

anchor後2本、最大10分以内に、anchor closeから0.03 H1 ATR以上同方向へ確定し、直前終値更新かつ同方向実体を必須とした。受容前にanchor midpointを反対側へ終値で越えた場合はINVALID。

entryは受容M5確定時刻と同時刻のM1 OPEN。M1欠落時はfallbackしない。

## source parity

M5のgold# / goldsharp完全重複58,092本で、tick_volume差0、spread差0、OHLC差0を確認済み。tick_volumeは実出来高ではなくbroker tick-count proxyとして扱った。M5/M15のreal_volumeは全行0のため使用していない。

## live再現性監査

| 項目 | batch | streaming |
|---|---:|---:|
| raw anchor | 674 | 674 |
| 完成候補 | 205 | 205 |

完全一致列:

- candidate_key
- direction
- anchor_time
- decision_time
- entry_time
- entry_price_source_time
- anchor_open / close
- anchor_h1_atr14
- tick_volume
- slot_median_volume
- slot_volume_ratio
- slot_volume_percentile
- global_volume_percentile
- body_ratio
- tr_ratio

追加監査:

- prefix: 40/40 PASS
- restart: 11/11 PASS
- candidate_key重複: 0
- H1/H4 future-source違反: 0
- entry_time < decision_time: 0
- M1欠落1件: entry未成立として除外

## 結果経路

| horizon | 完了件数 | MFE平均 | MAE平均 |
|---|---:|---:|---:|
| 60分 | 201 | 15.83 | 13.48 |
| 120分 | 189 | 20.97 | 19.67 |
| 180分 | 176 | 23.59 | 23.22 |
| 240分 | 167 | 26.06 | 24.27 |

volume impulseにより大きな値幅は検出できたが、MAEもほぼ同じ速度で増加した。

## 固定TP/SL

全期間の粗上限診断で最良:

- horizon 240分
- TP25 / SL10
- 件数167
- cost0期待値 `+2.971257 USD`
- PF `1.568919`

事前基準3ドルをわずかに下回る。

## 発見・選定・固定検証

2025H1だけで選んだcost2最良セルも、同じH240 TP25 SL10だった。

| 期間 | 件数 | cost0期待値 | cost2期待値 | cost2 PF |
|---|---:|---:|---:|---:|
| 2025H1 | 63 | +4.415 | +2.415 | 1.412 |
| 2025H2 | 74 | +2.364 | +0.364 | 1.059 |
| 2026H1部分 | 30 | +1.437 | -0.563 | 0.930 |

2025H2のPF1.10基準を下回り、固定2026でcost2赤字となったため候補成立なし。

月別cost2はプラス9か月、マイナス9か月だった。

## 方向診断

全期間の固定セルcost2:

- LONG: +0.316 USD / PF1.049
- SHORT: +1.651 USD / PF1.264

ただしSHORTだけを残す判断は全期間結果確認後の後付けになる。期間別では2026にLONGが悪化しSHORTが改善するなど非定常であり、方向フィルターへ昇格させない。

## 採否

live再現性:

- batch/streaming完全一致: PASS
- prefix invariance: PASS
- restart invariance: PASS
- source timing違反0件: PASS
- M1欠落fail-closed: PASS

性能:

- 最大cost0期待値3ドル以上: FAIL
- 2025H1 cost2プラス・PF1.10以上: PASS
- 2025H2固定条件プラス・PF1.10以上: FAIL
- 固定2026プラス: FAIL

事前契約に従い、matched controlとplaceboは未実施。0.03ドル弱の不足を理由に閾値変更や後付け選別を行わない。

## 判定

`LIVE_REPRODUCIBILITY_PASS_PERFORMANCE_REJECT`

E7はStage260で最も強い母集団だったが、複数期間でコストを安定して吸収する条件を満たさなかった。

次は同じtick-volume情報を使うが、継続ではなく「高activityにもかかわらず価格が進まない吸収・拒否」を独立仮説としてE8で監査する。E7閾値の近隣調整や受容条件の緩和は行わない。

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
