# Copy-paste prompt for the next chat

```text
repo: knitanr-a11y/xauusd-signal-lab

GOLD_ML_V1 / GML1-MLR1 の続きです。
最初に次を順番に読んで、記載された現在地から続けてください。

1. docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_MLR1_ML05A_DENSITY_AUDITED_20260627.md
2. config/gold_ml_v1/mlr1_stage_status_addendum_ml05a_density_20260627.json
3. config/gold_ml_v1/mlr1_stage_ml05a_density_audit_v1_20260627.json
4. config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json
5. config/gold_ml_v1/mlr1_ml_native_candidate_contract_v1_20260627.json
6. scripts/gold_ml_v1/mlr1/build_ml_native_candidate_proposals.py
7. config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json
8. config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json
9. config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json
10. config/gold_ml_v1/mlr1_user_pc_pinned_replay_acceptance_20260627.json
11. config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json

最終目標は、専門候補がproposalを出し、機械学習が現在の相場環境から期待値の高い候補だけを選び、競合・one-position・リスク管理を決定論的に処理し、shadowとprospective検証を経て自動売買へ進むことです。

重要:
- 全M15からMLが直接シグナルを作る方式を主方式にしない。
- 候補proposal + ML meta-modelが主方式。
- 旧Stage2のweights/scaler/threshold/feature contractは使わない。
- GOLD V2 / 旧GOLD / DISC8 / Stage41をfallbackにしない。
- audit-onlyを維持する。
- live、final signal、MT5注文、DiscordはまだOFF。
- 履歴用gold_v3_2023_2026とlive用Files直下goldsharp_*.csvを混ぜない。
- 16件の再現不能な旧候補はML対象外。
- exact再現可能な旧9候補はbenchmark-only。
- 現在のprimaryはML-native候補。

現在のML-05A v1 density結果:
- proposal 3,180件
- SHA256 d47a745402f4be01d7be5e1a6e830f33515e7317768363d745cff8ea09fb8219
- 合格family: MLC-001 / MLC-003 / MLC-006
- density-only v2が必要: MLC-002 / MLC-004 / MLC-005
- labels未結合
- candidate performance未確認

次にやること:
1. MLC-002 / 004 / 005 のLONG・SHORT別、年別、条件段階別のlabel-free condition funnelを作る。
2. 勝敗、PF、R、ML-03 labelを一切見ず、densityだけでv2定義を固定する。
3. 合格済みMLC-001 / 003 / 006 v1は変更しない。
4. accepted-v1 + revised-v2のcombined primary proposal registryを再生成する。
5. 全candidateが100～5000件かつ3年以上を満たすまでML-05Bのlabel joinへ進まない。

候補追加・削除・rename・promote・demoteやlive activationは、明示指示なしに行わないでください。
```
