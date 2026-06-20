# GOLD V3 引き継ぎ
## Stage260 E5 live再現性PASS・性能REJECT

現在の正式状態:

`GOLD_V3_260_E5_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## E5結論

E5「一方向displacement後の初回浅押し・再受容」は、entryのlive再現性はPASSしたが、性能基準で不採用。

live再現性:

- batch候補180件
- streaming候補180件
- 完全一致180件
- prefix invariance 40チェックPASS
- restart invariance 11地点PASS
- candidate_key重複0
- H1/H4 future-source違反0
- entry同時刻M1 OPEN欠落2件はfail-closedで除外

性能:

- live再現可能entry 178件
- 最大cost0期待値 +2.38ドル（基準3ドル未満）
- 2025H1 cost2最良セル H240 TP25 SL10: +0.41 / PF1.078
- 同セル2025H2: +1.11 / PF1.22
- 同セル2026H1部分: -1.51 / PF0.82

LONGだけを残すと全期間では良く見えるが、全期間確認後の後付け方向フィルターになるうえ、固定2026ではLONGも赤字。昇格禁止。

## E5以降の必須live契約

すべての候補で以下を性能評価前に実施する。

1. batch detectorとstreaming state machineを別実装
2. candidate_key、direction、anchor_time、decision_time、entry_time完全一致
3. prefix invariance
4. restart invariance
5. `source_close_time <= decision_time`
6. entry同時刻M1 OPENがなければfail-closed
7. open中の足、未来方向、未来最良entry、未来session end禁止
8. resolved-only healthは`exit_time <= current_entry_time`だけ

このゲートを失敗した候補は、成績が良くてもBLOCKEDまたはREJECT。

## 次の研究方向

次は、E5継続ではなく補完的なE6を優先する。

`GOLD_V3_260_E6_FAILED_DISPLACEMENT_REVERSAL_NEXT_AUDIT_ONLY`

基本仮説:

- E5と同じ因果的displacement anchorを使用
- 浅押し継続が失敗し、50%超の深押しまたは65% close invalidationが確定
- その後、元方向への復帰ではなく反対方向への価格受容が確定した場合だけ逆方向候補
- 年やレジームで方向を固定しない
- invalidation確定前に反対方向へ入らない
- E5の失敗イベントを結果を見て選別せず、E6定義を結果前に固定する

E6でも、定義固定 → batch/live parity → prefix/restart parity → 絶対母集団 → matched control → placeboの順を守る。

## 維持契約

- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- CSV最新行closed
- CSV timeはOPEN時刻
- HTFは`source_close_time <= decision_time`
- 同一M1 TP/SLはSL優先
- MFE/MAEはホライズン終端
- 1 setup 1 trade
- 2025H1発見、2025H2選定、2026固定
- MT5発注、Discord通知、AI API、live hook、order payload、autotrade、final signal禁止
- audit-only

主要参照:

- `docs/gold_v3/GOLD_V3_STAGE260_LIVE_REPRODUCIBILITY_CONTRACT_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E5_DIRECTIONAL_DISPLACEMENT_FIRST_PULLBACK_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E5_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e5_final_summary_20260620.json`
- `docs/gold_v3/stage260_e5_live_parity_20260620.json`
- `scripts/gold_v3/stage260_live_replay_contract.py`

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
