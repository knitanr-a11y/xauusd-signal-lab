# GOLD V3 Stage260 E6 実データ監査
## displacement継続失敗後の反対方向受容

作成日: 2026-06-20  
正式状態: `GOLD_V3_260_E6_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## 結論

E6は、**entryのlive再現性はPASS**したが、性能基準で不採用とする。

- batchとstreamingのraw anchorは545件で一致。
- failureは113件で一致。
- 完成候補は56件で完全一致。
- prefix invarianceは40地点PASS。
- restart invarianceは11地点PASS。
- H1/H4未来参照、entry前倒し、candidate_key重複は0件。
- entry同時刻M1 OPENがない2件はfail-closedで除外。

残るlive再現可能entry 54件の最大cost0期待値は`+1.03 USD`で、事前基準`+3 USD`へ届かなかった。2025H1のcost2最良セルも期待値`-0.81 USD`、PF`0.82`で赤字だったため、matched control・placebo・追加特徴量へ進まず早期不採用とした。

## 結果前に固定したE6

定義コミット:

`35dedc5d2c675b1d659af52e93a558bf3c994dac`

E5と同一の因果的3本M15 displacement anchorを使用した。

- 純移動0.80 H1 ATR以上
- 方向効率0.70以上
- 3本中2本以上が同方向実体
- 終値が3本レンジ端20%以内
- 直前8本に同方向・同等以上anchorなし

anchor後90分以内に50%超のdeep closeまたは65% close invalidationをfailureとして確定し、その後45分以内に元moveの80%以上を反対方向へ戻して確定した場合だけE6 entryを作った。

failure確定前には逆方向へ入っていない。anchor価格、ATR、50%・65%・80%水準はanchor時点で固定し、その後のATRで変更していない。

## live再現性監査

| 項目 | batch | streaming |
|---|---:|---:|
| raw anchor | 545 | 545 |
| failure | 113 | 113 |
| 完成候補 | 56 | 56 |

完成候補は次の列まで完全一致した。

- candidate_key
- direction
- original_direction
- anchor_time
- failure_time
- failure_type
- decision_time
- entry_time
- entry_price_source_time
- anchor_start_price
- anchor_end_price
- anchor_move
- anchor_atr14
- efficiency

追加監査:

- prefix checks: 40/40 PASS
- restart checks: 11/11 PASS
- candidate_key重複: 0
- H1 future-source違反: 0
- H4 future-source違反: 0
- entry_time < decision_time: 0
- M1欠落: 2件をentry未成立として除外

## 結果経路

| horizon | 完了件数 | MFE平均 | MAE平均 |
|---|---:|---:|---:|
| 60分 | 53 | — | — |
| 120分 | 53 | 12.88 | 12.24 |
| 180分 | 53 | — | — |
| 240分 | 52 | — | — |

120分では値幅は出たが、MFEとMAEがほぼ同水準で、方向優位を十分に作れていない。

## 固定TP/SL

全期間の粗上限診断で最も良かったセル:

- horizon 60分
- TP5 / SL15
- 件数53
- cost0期待値: `+1.03 USD`
- cost0 PF: `1.47`

事前基準のcost0期待値3ドルへ大きく届かない。

## 発見・選定・固定検証

2025H1だけで選んだcost2最良セル:

- horizon 240分
- TP10 / SL15

| 期間 | 件数 | cost0期待値 | cost2期待値 | cost2 PF |
|---|---:|---:|---:|---:|
| 2025H1 | 20 | +1.19 | -0.81 | 0.82 |
| 2025H2 | 20 | -2.06 | -4.06 | 0.47 |
| 2026H1部分 | 12 | -2.50 | -4.50 | 0.47 |

発見期間の最良セル自体が赤字であり、正式候補は0件。

## failure type診断

固定セルcost2の事後診断:

| failure type | 件数 | cost2期待値 | PF |
|---|---:|---:|---:|
| DEEP_CLOSE_50 | 16 | +0.02 | 1.00 |
| INVALID_CLOSE_65 | 36 | -4.21 | 0.44 |

DEEP_CLOSE_50だけなら悪化が小さいが、全期間結果を見た後の選別になる。さらに期待値とPFも候補水準ではないため、後付けfailure-typeフィルターとして昇格させない。

## 採否

live再現性:

- batch / streaming完全一致: PASS
- prefix invariance: PASS
- restart invariance: PASS
- source timing違反0件: PASS
- M1欠落fail-closed: PASS

性能:

- 最大cost0期待値3ドル以上: FAIL
- 2025H1 cost2プラス・PF1.10以上: FAIL
- 2025H2固定条件プラス・PF1.10以上: FAIL
- 固定2026プラス: FAIL

事前契約に従い、matched controlとplaceboは未実施。弱い母集団を後付け条件で救済しない。

## 判定

`LIVE_REPRODUCIBILITY_PASS_PERFORMANCE_REJECT`

E6もliveで同じentryを再現できるが、コストを吸収する優位性はない。

次は価格だけでは区別できなかった「本物の注文流入」を少しでも捉えるため、source parityが確認できるtick_volumeを使ったE7「因果的出来高インパルス＋価格受容」を、結果前に定義固定して監査する。

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
