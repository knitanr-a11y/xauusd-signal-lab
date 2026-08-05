# BTC AI V1 Stage 37 — 騙し・低頻度スペシャリスト研究結果

日付: 2026-08-04

正式状態:

`STAGE37_ONE_DETERMINISTIC_DECEPTION_SPECIALIST_SUPPORTED_STAGE38_ROBUSTNESS_PASS`

## 研究変更

Stage 31〜36のwindow・threshold救済は再開していない。今回は同じOHLCから、新しい因果イベントと遅延entryを定義した。

全72 subtype、33,912 event、864 execution構成を評価した。選択は2024年だけで行い、2025年は構成固定後に開いた。

## 正式に残った候補

`EXPANSION_MIDPOINT_FAILURE_L2_LONG__SL1.00_TP2.00_H480`

1. 大きな下方向M15 expansion足が出る。
2. closed M15を2本待つ。
3. 価格がそのexpansion足の中心線より上へ終値で戻る。
4. 次のexact M1 openでLONG。
5. SL 1 ATR、TP 2 ATR、最大480 M1、spread 22.5 USD、同一M1衝突はSL優先。

| 期間 | 件数 | PF | 純損益 | 最大DD | positive halfyears |
|---|---:|---:|---:|---:|---:|
| 2024 discovery | 141 | 1.4514 | 10,903.70 | 3,582.72 | 2/2 |
| 2025 validation | 132 | 1.0728 | 2,133.97 | 6,256.47 | 1/2 |
| 合算 | 273 | 1.2438 | 13,037.67 | 6,256.47 | 3/4 |

block-bootstrap P(net > 0): `0.92875`

## 壊し試験

- one-factor非base変種: 17
- 合算PF > 1の割合: `0.8824`
- 2025純損益positiveの割合: `0.9412`
- spread 1.5倍の合算PF: `1.2219`
- spread 2倍の合算PF: `1.1823`
- matched-random net percentile: `0.9990`
- matched-random PF percentile: `0.9955`

凍結済みrobustness gateはすべてPASS。

2024だけで選んだ16 specialistを用いた6つの事前定義stackはformal gateを通過しなかった。Stage37で正式に残るのは上記1候補だけ。

Shadow、Discord、MT5発注、live-ready、final signalはOFF。2026は使用していない。
