# GOLD V3 引き継ぎ
## Stage260 E8 live再現性PASS・性能REJECT → E9次

現在の正式状態:

`GOLD_V3_260_E8_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## E8結論

E8「高tick activity下の吸収・拒否」はlive再現性PASS、性能REJECT。

- raw anchor 533/533
- 完成候補205/205完全一致
- prefix 40地点PASS
- restart 11地点PASS
- M1 entry欠落0
- 最大cost0期待値 +0.478ドル
- 2025H1 cost2最良セル -0.478 / PF0.890
- 2025H2 -2.409 / PF0.558
- 2026H1部分 -3.057 / PF0.679

絶対母集団基準を失敗したためmatched control、placebo、追加特徴量は未実施。

## 次

`GOLD_V3_260_E9_TICK_VOLUME_DROUGHT_TO_IGNITION_NEXT_AUDIT_ONLY`

独立仮説:

- E7の絶対volume burstやE8の吸収shapeではなく、同一server-slot基準で低activityが複数本続いた後の最初のactivity ignitionを対象にする。
- 完了M5だけを使う。
- 直近6本のvolume ratio中央値が低位、価格rangeも低位であることを事前状態とする。
- その後の最初のvolume burstと価格実体拡大をanchorにする。
- anchor後の短い受容、または浅い初回pullback後の再受容からentryする。
- 低activity履歴、burst、受容の全てをbatch/streamingで再現する。
- E7閾値の近隣調整ではなく、volume regime transitionとして定義固定する。

E9でも、定義固定 → source parity → batch/live parity → prefix/restart → 絶対母集団 → matched control → placeboの順を守る。

## 維持契約

- entry時点で分かる情報だけを使う
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- CSV最新行closed、CSV timeはOPEN時刻
- HTFはsource_close_time <= decision_time
- 同一M1 TP/SLはSL優先
- MFE/MAEはホライズン終端
- 1 setup 1 trade
- 2025H1発見、2025H2選定、2026固定
- live parityを性能より先に確認
- MT5発注、通知、AI API、live hook、order payload、autotrade、final signal禁止
- audit-only

主要参照:

- `docs/gold_v3/GOLD_V3_STAGE260_E8_TICK_VOLUME_ABSORPTION_REJECTION_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E8_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e8_final_summary_20260620.json`
- `docs/gold_v3/stage260_e8_key_results_20260620.csv`
- `docs/gold_v3/stage260_e8_live_parity_20260620.json`
- `scripts/gold_v3/stage260_e8_detector.py`

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
