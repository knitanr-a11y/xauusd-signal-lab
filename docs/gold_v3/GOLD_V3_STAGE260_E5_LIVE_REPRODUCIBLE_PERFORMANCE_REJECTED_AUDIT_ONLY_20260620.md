# GOLD V3 Stage260 E5 実データ監査
## 一方向displacement後の初回浅押し・再受容

作成日: 2026-06-20  
正式状態: `GOLD_V3_260_E5_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## 1. 結論

E5は、**entryのlive再現性はPASS**した。

- batch detectorとstreaming state machineは180候補で完全一致。
- prefix invarianceは40チェックポイントでPASS。
- restart invarianceは11分割地点でPASS。
- H1/H4の`source_close_time > decision_time`違反は0件。
- candidate_key重複は0件。
- entry時刻と同じM1 OPENが存在しない2件はfail-closedで除外。

したがって、E5の候補生成時刻、方向、decision_time、entry_timeはlive-replayで再現できる。

一方、性能ゲートは不合格だった。

- 全固定グリッド最大cost0期待値は`+2.38 USD`で、事前基準`+3 USD`未満。
- 2025H1のcost2最良セルは期待値`+0.41 USD`でもPF`1.078`で、基準PF`1.10`未満。
- 同じ固定セルは2025H2で`+1.11 USD / PF 1.22`だったが、2026H1部分で`-1.51 USD / PF 0.82`へ崩れた。

よって、entry再現性は合格だが、実運用昇格は行わない。

## 2. 結果前に固定したE5

定義コミット:

`1ef6ec742626fffce44006b3f51434f484c50930`

live再現性契約コミット:

`6d3f11718bd7fa8660ef2d62807a1cde2eeff40c`

構造:

1. 完了M15を3本連続使用。
2. 3本の純移動が因果H1 ATR14の0.80倍以上。
3. 方向効率が0.70以上。
4. 3本中2本以上が同方向実体。
5. 最終終値が3本レンジ端20%以内。
6. anchor後90分以内の最初の20〜50%浅押し。
7. 50%超の初回押しはINVALID_TOO_DEEP。
8. 浅押し後45分以内に元方向の上位20%領域へ再受容。
9. 再受容M15確定時刻と同時刻のM1 OPENをentryとする。

anchor完成時に価格、ATR、押し範囲、invalid水準を固定し、その後のATRで動かしていない。

## 3. live再現性監査

### batch / streaming parity

| 項目 | 結果 |
|---|---:|
| batch候補 | 180 |
| streaming候補 | 180 |
| 完全一致候補 | 180 |
| candidate_key重複 | 0 |
| 価格・ATR許容差 | 1e-9以内 |

一致列:

- candidate_key
- event_type
- direction
- anchor_time
- decision_time
- entry_time
- entry_price_source_time
- state_version
- anchor_start_price
- anchor_end_price
- anchor_move
- anchor_atr14
- efficiency

### prefix invariance

月末、2025H1/H2境界、代表イベント時刻を含む40チェックポイントで、履歴をその時刻までで切断して再実行した結果が、全履歴結果の同時刻以前と完全一致した。

### restart invariance

11地点でstate snapshotを保存し、新しいdetectorへ復元して続行した。最初から連続実行した180候補と完全一致した。

### fail-closed entry

- streaming完成候補: 180件
- 同時刻M1 OPENあり: 178件
- 同時刻M1 OPENなし: 2件

欠落2件は近い価格や次のM1へfallbackせず、entry未成立として除外した。

### source timing

- H1 future-source違反: 0件
- H4 future-source違反: 0件
- entry_time < decision_time: 0件
- candidate_key重複: 0件

## 4. 結果経路

live再現可能な178件を評価した。週末・欠損を跨がず固定ホライズンが完成した件数は次のとおり。

| horizon | 完了件数 | MFE平均 | MAE平均 |
|---|---:|---:|---:|
| 60分 | 171 | 9.18 | 7.48 |
| 120分 | 163 | 12.47 | 10.50 |
| 180分 | 156 | 15.26 | 13.16 |
| 240分 | 150 | 17.76 | 14.16 |

値幅は出るが、MAEも同時に増えている。

## 5. 固定TP/SL

全期間の粗上限診断で最も良かったセル:

- horizon 240分
- TP25 / SL5
- 件数150
- cost0期待値: `+2.38 USD`
- cost0 PF: `1.74`

粗期待値はこれまでのE2〜E4より改善したが、事前基準`+3 USD`へ届かない。

## 6. 発見・選定・固定検証

2025H1だけでcost2最良セルを選択した。

- horizon 240分
- TP25 / SL10

| 期間 | 件数 | cost2期待値 | PF |
|---|---:|---:|---:|
| 2025H1 | 64 | +0.41 | 1.08 |
| 2025H2 | 52 | +1.11 | 1.22 |
| 2026H1部分 | 34 | -1.51 | 0.82 |

2025H1は期待値プラスだが、PF1.10基準をわずかに下回った。さらに固定2026で崩れたため候補成立なし。

固定セルの月別:

- cost0: プラス13、マイナス4、ゼロ1か月
- cost2: プラス11、マイナス7か月
- cost3: プラス9、マイナス9か月
- cost5: プラス5、マイナス13か月

## 7. 方向診断

全期間の固定セルcost2:

- LONG: 110件、期待値`+1.40 USD`、PF`1.27`
- SHORT: 40件、期待値`-3.04 USD`、PF`0.61`

ただし期間別では:

- LONGは2025H1/H2でプラス、2026H1部分でマイナス。
- SHORTは2025H1/H2でマイナス、2026H1部分ではcost0のみ小幅プラス、cost2はマイナス。

全期間を見てからLONGだけを残すことは後付け方向フィルターになるため禁止する。年依存方向も作らない。

## 8. 事前採否基準

live再現性:

- batch / streaming完全一致: PASS
- prefix invariance: PASS
- restart invariance: PASS
- source timing違反0件: PASS
- M1欠落fail-closed: PASS

性能:

- 最大cost0期待値3ドル以上: FAIL
- 2025H1 cost2プラスかつPF1.10以上: FAIL（PF1.078）
- 同セル2025H2プラスかつPF1.10以上: PASS
- 固定2026安定: FAIL

事前定義どおり、性能基準3または4を失敗したため、matched control、追加特徴量、時間帯、方向フィルターによる救済へ進まない。

## 9. 判定

`LIVE_REPRODUCIBILITY_PASS_PERFORMANCE_REJECT`

E5は、liveで同じentryを再現できる候補検出器としては成立した。しかし、複数期間でコストを吸収するほど強くない。

今後の候補も、E5で確立したbatch/streaming、prefix、restart、M1 fail-closedを必須ゲートとして継承する。

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
