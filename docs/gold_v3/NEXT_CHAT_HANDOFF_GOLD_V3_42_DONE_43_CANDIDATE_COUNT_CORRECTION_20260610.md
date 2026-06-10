# GOLD V3 42 -> 43 candidate count correction

Created JST: 2026-06-10

## Why this file exists

The prior handoff wording incorrectly narrowed the Stage43 honmei set to three names. That loses the broader candidate context and can make the next chat think only three candidates exist.

This is not acceptable.

## Confirmed candidate names from current artifacts

The confirmed Stage36 active candidate set has seven candidates:

```text
R01_P7_R1_ONLY_CD60_PRUNE_015
R02_P8_R1_ONLY_CD60_PRUNE_015
R03_P1_R1_ONLY_CD60_PRUNE_111
R04_P4_R1_ONLY_CD60_PRUNE_115
R05_P9_MAIN_R1_R2_CD90_PRUNE_133
R06_P11_MAIN_R1_R2_CD90_PRUNE_132
R07_P13_MAIN_R1_R2_CD120_PRUNE_122
```

The user explicitly wanted the following restore candidate added to the serious review set:

```text
R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024
```

Therefore the currently confirmed names are eight, not nine.

## Unresolved ninth candidate warning

The user stated that the candidate set should be nine. The current handoff documents do not contain the ninth name.

Do not invent the ninth candidate.

Before Stage43, the next chat must resolve this mismatch by checking the Stage22/23/24/30/36 artifacts and the user's latest decision. If the ninth name cannot be verified from source artifacts or explicit user clarification, Stage43 must stop with a candidate-count blocker.

## Candidate count blocker condition

Stage43 must not proceed if the intended candidate count remains ambiguous.

Blocker status to use if unresolved:

```text
GOLD_V3_43_BLOCKED_CANDIDATE_COUNT_MISMATCH_AUDIT_ONLY
```

Reason:

```text
Current handoff confirms 7 Stage36 active candidates plus 1 Stage22 restore candidate = 8 confirmed names, while the user expects 9 candidates. The ninth candidate name is not present in the handoff and must be verified before contract generation.
```

## Correct handling

1. Read the four prior handoff docs.
2. Read this correction file.
3. Verify candidate count from source artifacts.
4. If the ninth candidate is confirmed, include it in Stage43 exact entry/prune contract.
5. If the ninth candidate is not confirmed, stop with the blocker above.

## Safety

Do not continue with a guessed nine-candidate contract. Do not silently drop a candidate. Do not create live code.
