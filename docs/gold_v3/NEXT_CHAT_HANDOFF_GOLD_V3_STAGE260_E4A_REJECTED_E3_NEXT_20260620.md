# GOLD V3 引き継ぎ
## Stage260 E4A不採用 → E3次

現在の正式状態:

`GOLD_V3_260_E4A_COMPRESSION_FIRST_EXPANSION_REJECTED_AUDIT_ONLY`

E4Aは事前固定した母集団条件で早期不採用。

主要結果:

- raw 224件、dedup120 203件
- paired 120分MFE差 -4.99ドル
- paired 120分MAE差 +6.48ドル悪化
- 全固定グリッド最大cost0期待値 -0.23ドル
- 2025H1発見セル H240 TP25 SL15はcost2 +0.98/PF1.18
- 同セル2025H2 cost2 -1.66/PF0.76
- 同セル2026H1部分 cost2 -6.28/PF0.45
- E4B初回リテストは未実行

初回ではない拡大は2025H1/H2で良かったが固定2026で失敗。全期間を見た探索的プラセボなので昇格禁止。

次:

`GOLD_V3_260_E3_MULTI_REACTION_LEVEL_BREAKOUT_FIRST_RETEST_NEXT_AUDIT_ONLY`

E3で先に固定すること:

1. 完了H1だけで複数回反応価格帯を作る
2. touch幅、最低touch数、touch間隔を結果前に固定する
3. M15確定突破と初回リテスト受容を分離する
4. levelはbreakout前に確定済みであること
5. matched controlは同曜日、MT5 hour、ATR帯、方向、level品質帯、近い四半期
6. 母集団差がなければ特徴量追加前に不採用

維持契約:

- entry時点で分かる情報だけを使う
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- CSV最新行closed、CSV timeはOPEN時刻
- HTFはsource_close_time <= decision_time
- 同一M1 TP/SLはSL優先
- MFE/MAEはホライズン終端
- 1 setup 1 trade
- 2025H1発見、2025H2選定、2026固定
- MT5発注、通知、live hook、order payload禁止
- audit-only

主要参照:

- `docs/gold_v3/GOLD_V3_STAGE260_E4_COMPRESSION_FIRST_EXPANSION_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E4A_REAL_DATA_EARLY_REJECTION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e4_final_summary_20260620.json`
- `docs/gold_v3/stage260_e4_key_results_20260620.csv`
