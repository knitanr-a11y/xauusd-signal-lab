# GOLD V3 Stage266E Component Expansion Audit

作成日: 2026-06-21  
正式状態: `GOLD_V3_266E_C1_ONLY_COMPONENT_STACK_INSUFFICIENT_FREQUENCY_AUDIT_ONLY`

## 結論

C1をStage266D契約どおり再現し、C2専用cost5 gate、C3 raw監視、新候補C4/C5を追加した。

- C1: qualification PASS。固定componentとして維持。
- C2: 専用cost5 gateが悪化。gate不採用。
- C3: raw期待値は強いが、source・方向の偏りとcost5勝率不足でstack未採用。
- C4: 頻度は増えたが、LONG側が赤字でgateも勝率を改善せず不採用。
- C5: raw34件で赤字、2026悪化。候補定義を不採用。

qualified componentはC1だけ。C1のみのstackはcost5でプラスだが、42件、月間中央値4件で目標頻度に届かない。

## C1 frozen reproduction

Stage266D resolved OOF 74件についてgate accept/rejectは74/74完全一致。

- accepted 52件
- cost2勝率 61.54%
- cost5勝率 57.69%
- cost5期待値 +8.225 USD/oz
- cost5 PF 2.075
- rejected cost5期待値 -14.994

新family追加でC1のfamily_overlapや特徴定義が変わらないよう隔離した。

## C2 specialized cost5 gate

OOF raw 38件:
- cost2勝率 57.89%
- cost5期待値 +2.166
- cost5 PF 1.247

gate accepted 18件:
- cost2勝率 55.56%
- cost5勝率 50.00%
- cost5期待値 +0.455
- cost5 PF 1.054

rejected側のcost5期待値は+3.705。専用gateは負けを削らず、良い候補を多く削った。C2 gateは不採用。

## C3 raw compression

46件:
- cost2勝率 60.87%
- cost5勝率 52.17%
- cost5期待値 +8.356
- cost5 PF 2.499

全体は強いが、
- 2025 cost5期待値 +1.723 / 勝率42.86%
- 2026 cost5期待値 +29.460 / 勝率81.82%
- LONG cost5勝率43.24%
- SHORTは9件だけ

で、最近のSHORT少数大勝への依存が残る。raw監視を続け、現段階ではstackへ入れない。

## C4 previous-bar breakout

全resolved 223件で頻度は増えたが:
- cost2勝率 52.47%
- cost5期待値 -1.200
- cost5 PF 0.879

OOF gate accepted 77件:
- cost2勝率 51.95%
- cost5勝率 45.45%
- cost5期待値 +0.392
- cost5 PF 1.039

方向差が大きい:
- LONG 193件、cost5期待値 -3.361、PF0.667
- SHORT 30件、cost5期待値 +12.696、PF2.461

SHORT only化は禁止なのでfamily全体を不採用。広すぎる1本高安ブレイクはLONGのノイズを増やした。

## C5 inside-bar breakout

全resolved 34件:
- cost2勝率 47.06%
- cost2期待値 -6.098
- cost5期待値 -9.098
- cost5 PF 0.377

2025はほぼ損益ゼロ、2026は大幅赤字。inside bar単体では有効な構造候補にならなかった。

## C1-only stacked portfolio

未約定pending、active suppressionを含めて再生した。

- resolved 42件
- cost2 PnL +398.92
- cost2期待値 +9.498
- cost2勝率 59.52%
- cost2 PF 2.286
- cost5 PnL +272.92
- cost5期待値 +6.498
- cost5勝率 57.14%
- cost5 PF 1.750
- max DD 118.24
- top5利益依存 44.40%
- tradeがある月 10か月
- 月間trade中央値 4件

収益品質は維持したが、ユーザー目標の月間中央値6件・100件以上には未達。

## 因果・再現性

- CSV timeはOPEN時刻として処理。
- H4 decision_time=time+4時間。
- H1/D1はsource_close_time <= decision_timeだけを使用。
- C1 Stage266D gate判定74/74一致。
- 新familyの追加でC1 feature contractを変更しない。
- M1は事前pending stopのgap/touchとexit順序だけに使用。

## 今回の判断

1. C1は固定componentとして残す。
2. C2の現在gateは破棄し、setup定義自体を分割する。
3. C3は削らずraw sampleを増やす。
4. C4/C5はstackしない。
5. 次は別の構造candidateを追加する。単純に水準期間を短くする候補は増やさない。

## 次候補の優先順位

- C6: H4 false-break reclaim continuation
- C7: H4 trend pullbackの内部構造を2種類へ分割
- C8: H4 session-range breakout。official calendar準備後。

C6/C7は現在のOHLCだけで実装可能。C8はcalendar準備後。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
