# BTC AI V1 — H4 outside state-transition research 正式結果

日付: 2026-08-04  
branch: `feature/btc-h4-outside-state-transition-research`  
base: `feature/btc-h4-outside-mechanism-audit@6fb7685180fa7fa8d8ad0c4bcf10e12b25797e36`  
事前登録commit: `065f39d9be7bfc37f6b8f6f9b35928251c983e25`

## 正式結論

`BTC_AI_V1_H4_OUTSIDE_STATE_TRANSITION_ALL_FOUR_HYPOTHESES_REJECTED_RETROSPECTIVE_MECHANISM_EVIDENCE`

事前登録した4状態は、transition association gateと固定trade gateの両方を通過しなかった。新しいProspective Shadowは作成しない。H4 outside研究線の負結果は削除せず保持する。Stage55は変更していない。

## 研究境界

- entry時点までのclosed H4/D1/M15情報だけを状態判定に使用
- transitionはH4 close後の次16本の実在M15だけで判定
- exact M1 entry、fallbackなし、same-M1 collisionはSL優先
- common execution: decision M15 ATR14 × 1.00 SL、2R TP、720 existing M1 hold、cost 22.50 USD
- health gate: OFF / not applicable
- 2023～2026年7月はconsumed history上のretrospective mechanism evidence

## Pipeline

| 段階 | 件数 |
|---|---:|
| H4 outside events（96 H4 warmup後） | 332 |
| raw state-trade candidates | 235 |
| dedup candidates | 235 |
| exact-M1 / one-position trades | 235 |
| resolved-only live再現trade | 235 |
| unresolved | 0 |

## 全outside eventの最初のtransition — 2024～2026年7月

| Transition | Events | Rate |
|---|---:|---:|
| MIDPOINT_REVERSION | 34 / 262 | 12.98% |
| CONTINUATION_BREAK | 89 / 262 | 33.97% |
| FAILED_EXTREME_REJECTION | 112 / 262 | 42.75% |
| NONE_WITHIN_16_M15 | 27 / 262 | 10.31% |

最も多かったのは `FAILED_EXTREME_REJECTION` 42.75%、次が `CONTINUATION_BREAK` 33.97%。body確認付きmidpoint回帰は12.98%だった。outside barは深いmidpoint回帰より、極値を試して内側へ戻る浅い拒否が多かったが、その頻度だけでは利益edgeにならなかった。

## Association gate

| State hypothesis | Events | 事前指定transition | State rate | Baseline | Lift | 判定 |
|---|---:|---|---:|---:|---:|---|
| 両側volatility shock → 即時逆張り | 18 | MIDPOINT_REVERSION | 0.00% | 12.98% | -12.98% | REJECT |
| H4 trend整合 → 外側継続 | 87 | CONTINUATION_BREAK | 37.93% | 33.97% | +3.96% | REJECT |
| H4 trend逆行 → midpoint回帰 | 91 | MIDPOINT_REVERSION | 15.38% | 12.98% | +2.41% | REJECT |
| D1方向衝突 → 極値失敗反転 | 125 | FAILED_EXTREME_REJECTION | 37.60% | 42.75% | -5.15% | REJECT |

4状態とも、指定transitionをbaselineから十分に濃縮できなかった。H4 trend整合でcontinuationは37.93%まで上がったが、baseline 33.97%との差は+3.96ポイントに留まり、最頻transitionにもならなかった。

## 固定trade成績 — 2024～2026年7月

| State / trade translation | Trades | 勝率 | PF | Net USD | Max DD | 2024 PF | 2025 PF | 2026 PF | 判定 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 両側volatility shock → 即時逆張り | 18 | 44.44% | 1.396 | +2,100.89 | 1,947.72 | 0.792 | 1.347 | inf | REJECT |
| H4 trend整合 → 外側継続 | 59 | 22.03% | 0.503 | -8,315.12 | 10,051.58 | 0.662 | 0.467 | 0.305 | REJECT |
| H4 trend逆行 → midpoint回帰 | 32 | 37.50% | 1.035 | +213.72 | 1,310.10 | 0.992 | 1.505 | 0.417 | REJECT |
| D1方向衝突 → 極値失敗反転 | 72 | 30.56% | 0.700 | -5,095.14 | 9,490.19 | 0.632 | 0.440 | 2.190 | REJECT |

## 弱いpost-result lead

`STATE_TWO_SIDED_VOLATILITY_SHOCK` の即時逆張りだけは18件、PF 1.396、net +2,100.89 USD、最大winner除外PF 1.108、double-cost PF 1.306だった。LONG PF 1.292、SHORT PF 1.489で方向片寄りも小さい。

ただし次のため正式候補ではない。

- 合算18件、2026年は2件でfrequency floor未達
- 2024 PF 0.792・net -532.16 USD
- net/DD 1.079で1.50未満
- 事前指定したmidpoint transitionはstate内で0件で、想定機構が確認されていない
- 結果後にthresholdを緩めたり別transitionへ読み替えない

## その他の所見

- H4 trend整合のcontinuation tradeはPF 0.503で明確に不支持。
- H4 trend逆行midpoint回帰は32件、PF 1.035でほぼ横ばい。2025 PF 1.505だったが2026 PF 0.417へ崩れた。
- D1方向衝突のfailed-extremeは全体PF 0.700。2026 PF 2.190だけを後付け採用しない。
- causal volatility診断ではH4 trend逆行midpointのhigh-volがPF 1.221だったが、結果後sliceのため救済しない。

## Causal / live再現監査

- H4 event close時点で未確定のD1/H4/M15情報は不使用
- prior-96 H4 ATR medianはshift(1)し、current H4を履歴へ早入れしていない
- exact entry M1欠損0件
- entry後のM1欠損区間は人工足を作らずposition継続
- one-positionはstate familyごと、cross-state global one-positionはaudit-only
- synthetic test 2件PASS
- future/open/as-of use count 0

## 最終境界

- 4状態すべて `STATE_HYPOTHESIS_NOT_SUPPORTED`
- fresh Prospective Shadow: 作成しない
- H4 outside state thresholdの結果後調整: しない
- Stage55: 変更なし
- MT5 orders / live trading / live-ready / final signal / Discord: OFF
