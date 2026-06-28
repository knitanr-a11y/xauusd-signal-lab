# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GML1_LIVE_AUDIT_4_SLEEVES_READY_P16_P19_HISTORICAL_ONLY_NEW_DISCOVERY_NEXT`

Read `AGENTS.md` first, then:

1. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_LIVE_AUDIT_AND_NEW_CANDIDATE_DISCOVERY_20260628.md`
2. `config/gold_ml_v1/current_state_20260628.json`
3. `config/gold_ml_v1/next_action_20260628.json`
4. `config/gold_ml_v1/live_research_challenger/live_runtime_contract_20260628.json`
5. `config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json`
6. `docs/gold_ml_v1/CURRENT_GML1_HANDOFF_20260627.md`
7. `config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`

The 2026-06-28 GitHub handoff is authoritative. Do not ask the user to paste or download another handoff.

Current live audit runtime:

- A_CORE / WATCH-022-C
- B_STATE / H1-D1 REENTRY24-C
- P18 / PROV-018-APPROX
- W024A / WATCH-024-A

P16 and P19 remain historical-only because their original fresh-inference ML artifacts were not recovered. Frozen exclusion times must never be used for future bars.

ML-05A density v2 is already completed. Do not repeat it.

Next stage:

`GML1_NEW_INDEPENDENT_CANDIDATE_DISCOVERY_V1_AUDIT_ONLY`

Start by auditing current main and writing the new discovery contract before inspecting labels or candidate performance.

Absolute restrictions:

- GOLD_ML_V1 only
- no GOLD V2 / old GOLD / DISC8 / Stage41
- no Batch024 restart
- no PROV-030-A restart or fallback
- no P16/P19 model substitution
- no final signal / Discord / MT5 order
- audit-only remains active

CSV `time` is MT5 server bar-open time. The latest valid row is closed by contract. Exact M1 entry is required and same-M1 collision resolves protective first.
