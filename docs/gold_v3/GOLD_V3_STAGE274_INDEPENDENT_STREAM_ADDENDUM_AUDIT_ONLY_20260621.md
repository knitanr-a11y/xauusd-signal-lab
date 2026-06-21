# Stage274 Independent Stream Addendum

作成日: 2026-06-21
状態: `GOLD_V3_274_INDEPENDENT_STREAM_ADDENDUM_LOCKED_AUDIT_ONLY`

## 理由

発見段階でA_PDとA_H1S20、またはB_PDとB_H1S20をfamily全体の先着順で抑制すると、ソート優先variantが他variantの候補を消し、公平な固定セル比較にならない。

## 固定解釈

- 12-cell discovery比較の24 trading-hour cooldownは`level_variant × direction`内で適用する。
- TP 1.5R/2.0R/2.5Rは同じaccepted event streamを共有する。
- exact same entryで複数variantが成立してもall-candidate ledgerでは両方保持する。
- familyごとのchosen cell確定後、そのchosen variantだけでfinal independent streamを構成する。
- family間は統合しない。
- suppressed候補は別ledgerに全件保存する。

この解釈は結果計算前に固定し、結果後に変更しない。
