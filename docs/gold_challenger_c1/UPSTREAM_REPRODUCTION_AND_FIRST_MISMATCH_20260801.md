# DATA V3 Upstream Reproduction and Reference Difference

The DATA_V3 E40 router was rebuilt from the read-only frozen V19 router source and the authoritative `(3)` source manifest. The V17 frozen causal wave grammar was applied independently.

The old V10 ledger is reference-only because it was generated from unavailable `(2)` inputs. The first comparison difference is preserved rather than repaired:

- timestamp: `2024-07-02 01:15:00`
- classification: `DATA_VERSION_MISMATCH`
- reference row: absent
- DATA_V3 chosen side: `SHORT`
- DATA_V3 LONG rank: `0.008566533409480296`
- DATA_V3 SHORT rank: `0.251284980011422`
- DATA_V3 P90 classification: false
- entry M1 index: `530301`

The complete structured record is `outputs/first_mismatch.json`. No threshold, timestamp, source merge, wave state, or execution rule was changed to approach the old result.
