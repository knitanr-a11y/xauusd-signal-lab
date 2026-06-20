# GOLD V3 引き継ぎ
## Stage260 E2不採用 → E4次

現在の正式状態:

`GOLD_V3_260_E2_PRIOR_DAY_SWEEP_RECLAIM_REJECTED_AUDIT_ONLY`

E2は母集団段階で早期不採用。

主要理由:

- 固定グリッド最大cost0期待値 約+0.65ドル
- cost1以降は全セル赤字
- 最大cost2 PF 約0.79
- 2025年前半の最良cost2セルも期待値-2.24、PF0.42
- matched controlとの経路差が小さい
- +10分、-5分、-0.5ATR等のプラセボが真のE2より良い
- 追加特徴量探索は禁止

正確なStage258レジーム時系列は復元できなかった。未来結果を見てproxyを作らず、E2は絶対的な母集団弱さとプラセボ失敗により不採用とした。

次:

`GOLD_V3_260_E4_COMPRESSION_FIRST_EXPANSION_NEXT_AUDIT_ONLY`

E4で最初に行うこと:

1. 長時間圧縮をentry-known情報だけで定義する
2. 圧縮終了と初回拡大のdecision_timeを固定する
3. H1/M15/M5のsource_close_time監査を行う
4. 同曜日・同MT5時間・同ATR帯・同レジーム・同方向条件のmatched controlを作る
5. 母集団差がなければ特徴量追加前に不採用にする

維持事項:

- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- CSV最新行closed
- CSV timeはOPEN時刻
- HTFはsource_close_time <= decision_time
- 同一M1 TP/SLはSL優先
- MFE/MAEはホライズン終端
- 1 setup 1 trade
- 2025H1発見、2025H2選定、2026固定
- MT5発注・通知・live hook・autotrade・order payload禁止
- audit-only

主要参照:

- `docs/gold_v3/GOLD_V3_STAGE260_E2_REAL_DATA_EARLY_REJECTION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e2_final_summary_20260620.json`
- `docs/gold_v3/stage260_e2_key_results_20260620.csv`
- `docs/gold_v3/stage260_e2_source_parity_20260620.csv`
