# GOLD_ML_V1 local reproduction implementation handoff

Date: 2026-06-27
Status: audit-only

## Current progress

- The existing frozen nine have a user-PC verified local replay PASS.
- Current stack contains 15 accumulated candidates and 9 Research WATCH candidates.
- The remaining 15 candidates do not yet have complete candidate-specific executable replay modules committed to GitHub.
- Do not modify the frozen-nine replay while adding later candidates.

## Next implementation target

Start with `GML1-WATCH-030-A`.

The 2026-06-27 chat completed a sandbox implementation and validation, but executable files could not be committed through the available GitHub write action. Candidate state was not changed.

Validated acceptance values for the future GitHub implementation:

- proposal rows: 124
- Base rows: 106
- Strong rows: 108
- proposal SHA256: `bf28f5b2672a6d8e135bd2ff358525d65ceeabb08a228c5661409bcd90936c38`
- Base SHA256: `0c3c52444ba4520bd3a539b322354b104628b4f00c3b8683aa2df652af57d637`
- Strong SHA256: `817156e38e3a348887b76459d71c2093317075579b843703eb9631eb3b979113`

Required additive files:

- `scripts/gold_ml_v1/replay/watch030a_local_replay.py`
- `scripts/gold_ml_v1/replay/run_watch030a_local_replay.bat`
- `config/gold_ml_v1/replay/watch030a_replay_config_20260627.json`
- `config/gold_ml_v1/replay/watch030a_expected_metrics_v2_strict_20260627.json`
- `config/gold_ml_v1/watch030a_v2_strict_reproduction_status_20260627.json`
- `tests/gold_ml_v1/test_watch030a_local_replay.py`
- `docs/gold_ml_v1/GOLD_ML_V1_WATCH030A_LOCAL_REPLAY_V2_STRICT_20260627.md`

Read these authoritative sources before implementation:

1. `docs/gold_ml_v1/NEXT_CHAT_START_HERE_20260626.md`
2. `docs/gold_ml_v1/NEXT_CHAT_FINAL_VERIFICATION_20260626.md`
3. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
4. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_V2_20260626.md`
5. `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
6. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
7. the WATCH-030-A candidate config

Acceptance gate:

- executable candidate reproducer committed
- exact input identity check committed
- deterministic Windows runner committed
- expected output hashes committed
- unit and parity tests committed and passing
- user-PC raw replay matches all three hashes
- no changes to candidate state, portfolio state, or runtime controls

Recommended order after WATCH-030-A:

1. WATCH-032-A
2. WATCH-033-A
3. WATCH-034 common entry implementation with separate A/B/C outputs
4. WATCH-026-A/B
5. WATCH-027-A/B
6. WATCH-028-A/B
7. WATCH-024-A
8. WATCH-025-A after its audit contract is complete
9. WATCH-029-A after its missing frozen source registry and family map are available

Non-negotiable boundaries:

- GOLD_ML_V1 only
- audit-only
- exact input timestamp matching
- causal closed-bar features only
- deterministic ordering
- immutable candidate IDs
- no portfolio or runtime activation
- no new candidate search until reproduction work is complete

First action in the next chat: verify that the seven WATCH-030-A files are absent from main, then add them on a branch and run the acceptance gate above.
