# GOLD V3 引き継ぎ
## Stage260 E6 live再現性PASS・性能REJECT → E7次

現在の正式状態:

`GOLD_V3_260_E6_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY`

## E6結論

E6「displacement継続失敗後の反対方向受容」はlive再現性PASS、性能REJECT。

live:

- batch/streaming raw anchor 545/545
- failure 113/113
- 完成候補 56/56完全一致
- M1 entryあり54、欠落2はfail-closed
- prefix 40地点PASS
- restart 11地点PASS
- H1/H4 future-source違反0

性能:

- 最大cost0期待値 +1.03ドル
- 2025H1 cost2最良セル H240 TP10 SL15: -0.81 / PF0.82
- 同セル2025H2: -4.06 / PF0.47
- 同セル2026H1部分: -4.50 / PF0.47

絶対母集団基準を失敗したためmatched control、placebo、追加特徴量は未実施。

## 次

`GOLD_V3_260_E7_CAUSAL_TICK_VOLUME_IMPULSE_PRICE_ACCEPTANCE_NEXT_AUDIT_ONLY`

理由:

E2〜E6のOHLC構造だけではMFEとMAEを十分に分離できなかった。アップロード済みデータでは、M5/M15/H1/H4/D1の重複期間でtick_volumeとspreadもgold# / goldsharp間の差0件を確認済み。tick_volumeはliveで確定足から取得できるため、次の独立情報として監査可能。

E7で結果前に固定すること:

1. 使用足は完了M5またはM15のみ。
2. tick_volumeの因果rolling分位。現在足を過去分布へ入れない。
3. volume burstと価格実体・方向効率の同時成立。
4. impulse確定後の短い価格受容または初回pullback。
5. batch/streaming、prefix、restart、M1 fail-closedを性能前にPASS。
6. 2025H1発見、2025H2選定、2026固定。
7. volumeなしplacebo、volume時刻シフト、random flagへ勝つこと。

注意:

- real_volumeは全0のため使わない。
- tick_volumeを実出来高と呼ばない。broker tick count proxyとして扱う。
- source間parityが崩れる時間足は使用しない。
- 全期間を見てLONGだけ、特定failure_typeだけを残さない。

## 維持契約

- entry時点で分かる情報だけを使う
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- CSV最新行closed、CSV timeはOPEN時刻
- HTFはsource_close_time <= decision_time
- 同一M1 TP/SLはSL優先
- MFE/MAEはホライズン終端
- 1 setup 1 trade
- live parityを性能より先に確認
- MT5発注、通知、AI API、live hook、order payload、autotrade、final signal禁止
- audit-only

主要参照:

- `docs/gold_v3/GOLD_V3_STAGE260_E6_FAILED_DISPLACEMENT_REVERSAL_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E6_LIVE_REPRODUCIBLE_PERFORMANCE_REJECTED_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e6_final_summary_20260620.json`
- `docs/gold_v3/stage260_e6_key_results_20260620.csv`
- `docs/gold_v3/stage260_e6_live_parity_20260620.json`
- `scripts/gold_v3/stage260_e6_detector.py`

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
