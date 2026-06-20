# GOLD V3 引き継ぎ
## Stage260 E3不採用 → E5次

現在の正式状態:

`GOLD_V3_260_E3_MULTI_REACTION_BREAKOUT_RETEST_REJECTED_AUDIT_ONLY`

E3は早期不採用。

主要結果:

- 確認済みH1反応点 5,343
- raw breakout 262
- 初回リテスト 129
- E3完成・dedup120 90
- 120分結果経路完了 82
- 全固定グリッド最大cost0期待値 +1.81ドル
- 2025H1 cost2最良セル -1.69 / PF0.52
- 同セル2025H2 -2.89 / PF0.32
- 同セル2026H1部分 -4.69 / PF0.20
- cost2月別 プラス1、マイナス15か月
- matched controlは厳密一致8組だけで、bootstrap区間はゼロを含む
- breakout-onlyとretest-onlyよりは改善したが、random flagへ勝てない

未来情報監査:

- level contextが突破M15 OPENより後: 0
- 最新反応確認が突破OPEN-4時間より後: 0
- リテストが突破以前: 0
- entryがリテスト以前: 0

次:

`GOLD_V3_260_E5_DIRECTIONAL_DISPLACEMENT_FIRST_PULLBACK_NEXT_AUDIT_ONLY`

E5の基本仮説:

- 静的な価格帯の突破ではなく、M15の高効率・一方向displacementをイベントにする
- displacement後の最初の浅い押し戻りだけを待つ
- 押し戻り後、元方向への再受容確定から入る
- 方向は実際のdisplacement方向で決め、年やレジームで固定しない

E5で結果前に固定すること:

1. displacementの本数、最低H1 ATR倍率、方向効率
2. 終値位置と実体比
3. 初回pullbackの深さ範囲と最大待機時間
4. 無効化深さ
5. 再受容条件
6. matched controlと主要プラセボ
7. 事前採否基準

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

- `docs/gold_v3/GOLD_V3_STAGE260_E3_MULTI_REACTION_BREAKOUT_FIRST_RETEST_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE260_E3_REAL_DATA_EARLY_REJECTION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage260_e3_final_summary_20260620.json`
- `docs/gold_v3/stage260_e3_key_results_20260620.csv`
- `docs/gold_v3/stage260_e3_causal_contract_audit_20260620.json`
