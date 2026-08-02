# GOLD SCALP PATH-SHAPE NEIGHBORS V1 — Reproduction Note

Date: 2026-08-02

## Data

Use the existing GOLD candle CSVs only:

- M1 primary plus continuation source;
- M5/H1/H4 event candidate cache from the preceding regime/first-passage research;
- MT5 broker-server naive time;
- closed rows only.

## Shared execution

- spread: 0.30 USD once;
- exact M1 outcome resolution;
- protective stop first when TP and stop are both reachable in one M1;
- initial SL <= 5 USD;
- TP >= 5 USD;
- breakeven allowed;
- recorded entry spread gate <= 30 points;
- global one-position non-overlap.

## Representation sample

- 170,664 structural event rows;
- 110,863 unique valid entry/structural-side pairs;
- preceding 60 contiguous M1 bars;
- canonicalize price channels in the proposed structural direction;
- fit or standardize representation on 2023H1 only;
- do not use trade outcomes in PCA, autoencoder or multi-scale representation construction.

## Pseudo-forward

Half-year eras:

- 2023H1
- 2023H2
- 2024H1
- 2024H2
- 2025H1
- 2025H2
- 2026H1
- 2026JUL

Formal target sequences begin at 2024H2. For each calibration or target block, retrieve neighbors separately from each fully prior half-year era. Weight eras equally rather than weighting by row count.

## Representations

### PCA

- input channels: directional return, directional body, range, favorable wick, adverse wick, directional close location, causal volume z-score and causal spread z-score;
- 60 bars × 8 channels = 480 inputs;
- standardize on 2023H1;
- PCA 16 dimensions, whitened;
- use corrected selection requiring `summary.k == requested_k`.

### Denoising autoencoder

- same 480 standardized inputs;
- encoder 480 -> 128 -> 48 -> 24;
- GELU activations;
- Gaussian input noise 0.03 during training;
- AdamW, learning rate 0.001;
- chronological 80/20 split inside 2023H1;
- maximum 20 epochs;
- no outcome labels.

### Deterministic multi-scale

Forty fixed dimensions:

- twelve 5-minute directional-return bins;
- eight cumulative directional-return checkpoints;
- directional efficiency at four horizons;
- range mean and range standard deviation at four horizons;
- favorable-minus-adverse wick balance at four horizons;
- causal volume-z mean at four horizons.

Standardize on 2023H1 only.

## Neighbor contracts

Cross-event diagnostic:

- k in 5, 10, 20;
- follow or fade;
- eight exit policies;
- era-balanced expected-PnL selection.

Same-event win-rate studies:

- restrict neighbors to the same structural event;
- k in 5, 10, 20;
- require at least two historical eras;
- TP5/SL2.5, TP5/SL3 and TP5/SL3-BE2 only;
- follow-only or follow/fade;
- prioritize minimum-era and average-era positive-PnL rates.

## Audit correction

The initial cross-event selection function failed to filter the saved summary table by requested k. The corrected rerun added the explicit k filter. Only the corrected files with `_fixed` suffix and the consolidated audit are formal.

## Decision rule

Do not promote any representation unless its frozen target block is positive and it subsequently requalifies through the same causal contract. All three calibration winners failed their immediately following targets, so promotion count is zero.
