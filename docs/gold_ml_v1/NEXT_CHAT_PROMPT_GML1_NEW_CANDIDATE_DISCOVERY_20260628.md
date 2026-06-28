# Next-chat prompt — GML1 new candidate discovery

Copy the text below into the new chat.

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を順番に読んで、続きから進めてください。

1. AGENTS.md
2. START_HERE_GOLD_ML_V1_NEXT_CHAT.md
3. docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_LIVE_AUDIT_AND_NEW_CANDIDATE_DISCOVERY_20260628.md
4. config/gold_ml_v1/current_state_20260628.json
5. config/gold_ml_v1/next_action_20260628.json
6. config/gold_ml_v1/live_research_challenger/live_runtime_contract_20260628.json
7. config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json
8. docs/gold_ml_v1/CURRENT_GML1_HANDOFF_20260627.md
9. config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json

現在status:
GML1_LIVE_AUDIT_4_SLEEVES_READY_P16_P19_HISTORICAL_ONLY_NEW_DISCOVERY_NEXT

重要な区別:
- 履歴上のcandidate stack
- 過去成績を出した6戦略portfolio
- 現在live判定可能な4戦略
を混同しないでください。

現在live auditで新規判定可能なのは次の4袖だけです。
- A_CORE / GML1-WATCH-022-C
- B_STATE / H1-D1 REENTRY24-C
- P18 / GML1-PROV-018-APPROX
- W024A / GML1-WATCH-024-A

P16/P19について:
- 過去portfolioには含まれる
- 元のmodel/scaler/feature order/score registry/numeric threshold/training code/inference codeは回収不能
- frozen exclusion decision_timeはhistorical reconstruction専用
- fresh inferenceは禁止
- ML-04や別モデルで代用禁止
- 新モデルをrecovered P16/P19と呼ばない

このチャットで完了済み:
- PR #63 historical research challenger local runtime
- PR #64 persistent audit-only BAT live loop
- PR #65 fast signature probe, M1 tail read, delayed-write/timeframe sync
- PR #66 wall-clock anchored 2-second polling and completion-drift removal

ML-05A density v2はPR #41ですでに完了済みです。次作業として繰り返さないでください。

次に行う正式stage:
GML1_NEW_INDEPENDENT_CANDIDATE_DISCOVERY_V1_AUDIT_ONLY

目的:
P16/P19を再現したと装わず、現在の4つのlive-capable sleevesに対して独立性があり、trade countとtotal Rを補える新しいLONG/SHORT候補を探索すること。

最初に行うこと:
1. 現在repo/mainの状態を監査
2. current four-live-sleeve benchmarkとhistorical six-sleeve referenceを凍結
3. labelsや成績を見る前にnew candidate discovery contractを作成してGitHubへ保存
4. causal closed-bar deterministic proposal grammarを定義
5. raw proposalsをdedup/one-position/outcome filtering前に保存
6. label-free density・方向・時間帯・regime・overlap audit
7. 定義とhashを凍結してから初めてlabelsをjoin

最初の成果物:
- config/gold_ml_v1/new_candidate_discovery_v1_contract_20260628.json
- candidate-family specification
- deterministic raw proposal builder
- label-free density and overlap audit
- closed-bar causality / historical-live parity tests

絶対禁止:
- GOLD V2 / old GOLD / DISC8 / Stage41を読まない・使わない
- Batch024を再開しない
- GML1-PROV-030-Aを再実行・修復・救済・fallback利用しない
- P16/P19のfrozen exclusion時刻を未来判定に使わない
- density調整中にlabels/PF/WR/Rを見ること
- 2025/2026を見てretuneすること
- final signal / Discord / MT5 order
- 自動promotion / registration

CSV timeはMT5 server naive bar-openです。JST変換で判定しないでください。
CSV最新有効行はclosed契約です。
exact M1 entry row必須、next-M1 fallback禁止、same-M1 collisionはprotective優先です。

まず読了後、
- live audit 4袖実装済み
- P16/P19 historical-only
- ML-05A v2完了済み
- 次はnew independent candidate discovery v1
- audit-only継続
を短く確認し、そのままrepo監査とdiscovery contract作成から開始してください。
```
