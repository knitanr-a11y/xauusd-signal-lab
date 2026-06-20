# GOLD V3 引き継ぎ
## Stage260 E7 live再現性PASS・性能REJECT → E8次

現在の正式状態:

`GOLD_V3_260_E7_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## E7結論

E7「因果的tick-volumeインパルス＋価格受容」はlive再現性PASS、性能REJECT。

live:

- batch/streaming raw anchor 674/674
- 完成候補205/205完全一致
- M1 entryあり204、欠落1はfail-closed
- prefix 40地点PASS
- restart 11地点PASS
- H1/H4 future-source違反0

性能:

- 最大cost0期待値 +2.971257ドル（基準3ドルに0.028743届かず）
- 2025H1固定セル H240 TP25 SL10: cost2 +2.415 / PF1.412
- 同セル2025H2: +0.364 / PF1.059（基準1.10未満）
- 同セル2026H1部分: -0.563 / PF0.930
- cost2月別: プラス9、マイナス9

厳格な事前基準に従い、丸め合格、閾値緩和、SHORTだけの採用は禁止。絶対母集団基準を失敗したためmatched controlとplaceboは未実施。

## 次

`GOLD_V3_260_E8_TICK_VOLUME_ABSORPTION_REJECTION_NEXT_AUDIT_ONLY`

E8の独立仮説:

- E7のような高volume＋高効率継続ではなく、高いtick activityにもかかわらず価格実体が進まない吸収を対象とする。
- M5 tick_volumeは同一server-slot因果基準を使用。
- 小実体、長い片側wick、レンジ端からのclose-backをanchorとする。
- upper-wick吸収後はSHORT、lower-wick吸収後はLONG。
- 次の確定M5で反対方向の価格受容が成立した時だけentry。
- volume急増がない同形状、volume shift、slot randomを主要placeboとする。
- E7閾値の微調整や受容緩和ではなく、別の市場メカニズムとして定義固定する。

E8でも、定義固定 → source parity → batch/live parity → prefix/restart → 絶対母集団 → matched control → placeboの順を守る。

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

- `docs/gold_v3/GOLD_V3_STAGE260_E7_CAUSAL_TICK_VOLUME_IMPULSE_ACCEPTANCE_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E7_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e7_final_summary_20260620.json`
- `docs/gold_v3/stage260_e7_key_results_20260620.csv`
- `docs/gold_v3/stage260_e7_live_parity_20260620.json`
- `scripts/gold_v3/stage260_e7_detector.py`

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
