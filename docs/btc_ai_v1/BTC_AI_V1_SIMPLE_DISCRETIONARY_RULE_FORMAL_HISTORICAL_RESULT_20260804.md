# BTC AI V1 — シンプル裁量型ルール formal historical result

日付: 2026-08-04  
repository: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/btc-simple-discretionary-rule-research`  
branch base: `1fd920f62f0145470e50e5430e7b605693532a36`  
事前登録commit: `dfa401d8af2da588d6695b70ad5a2d1ec2dea256`

## 正式結論

事前登録した4familyのformal baseは、すべて数値gate不合格となった。

正式状態:

`BTC_AI_V1_SIMPLE_DISCRETIONARY_RULES_ALL_FOUR_BASES_REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE`

近傍構成は壊し試験であり、baseの代替候補ではない。よって、近傍だけが良かった場合も昇格させない。

今回の結果から新しいProspective Shadowは作成しない。

以下はすべてOFFのまま維持する。

- MT5 orders
- live trading
- live-ready
- final signal
- Discord delivery
- automatic promotion

Stage55は別branch・別runtimeで稼働継続中であり、今回の研究では変更していない。

## データ・実行契約

- XM `BTCUSD#`
- closed OHLCのみ
- M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- exact M1 entry
- exact entry M1欠損は無効、fallbackなし
- same-M1でSL/TPへ触れた場合はSL優先
- 1 BTC往復cost 22.50 USD
- double-cost診断 45.00 USD
- 外部市場、funding、open interest、order flow、tick volume、real volume不使用
- 2023～2026年7月は `RETROSPECTIVE_EXPLORATORY_EVIDENCE_ON_CONSUMED_HISTORY`

## pipeline件数

| 段階 | 件数 |
|---|---:|
| raw configuration-level candidates | 26,426 |
| same-timestamp duplicates removed | 6 |
| deduplicated candidates | 26,420 |
| exact-entry M1欠損 | 15 configuration rows / 5 unique events |
| structure SLのnon-positive risk無効 | 10 configuration rows |
| exact-M1 valid candidates | 26,395 |
| one-position trades | 20,481 |
| open中抑制 | 5,914 |
| health gate | OFF / not applicable |
| resolved-only live再現trade | 20,481 |
| unresolved end-of-data | 0 |
| same-M1 collision、SL-first | 8 |
| 保有中に欠損M1区間を跨いだtrade | 592 |

entry後にM1行が存在しない区間については、人工M1を作成していない。positionは継続し、maximum holdの360本は実在M1だけを数えた。entry予定時刻にexact M1がないcandidateのみ無効化した。

## formal base成績 — 2024～2026年7月

| family | trades | 勝率 | PF | 純損益 USD | Max DD | マイナス月 / 31 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---|
| HTF trend pullback | 1,984 | 34.02% | 0.833 | -62,308.61 | 64,516.98 | 24 | REJECT |
| high/low sweep close-back | 1,061 | 38.17% | 0.896 | -29,538.35 | 38,986.79 | 18 | REJECT |
| compression first retest | 1,030 | 31.75% | 0.757 | -27,884.35 | 29,992.62 | 26 | REJECT |
| ATR impulse exhaustion | 869 | 36.36% | 0.985 | -2,437.65 | 16,053.49 | 15 | REJECT |

## 年・期間別

### HTF trend pullback base

| slice | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023 sanity | 780 | 33.46% | 0.622 | -20,057.80 |
| 2024 | 801 | 35.96% | 0.908 | -12,415.69 |
| 2025 | 771 | 30.87% | 0.755 | -41,886.72 |
| 2026-01～07 | 412 | 36.17% | 0.883 | -8,006.20 |
| 2026-07のみ | 50 | 44.00% | 1.032 | +160.08 |

### high/low sweep close-back base

| slice | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023 sanity | 330 | 42.73% | 0.898 | -2,796.76 |
| 2024 | 419 | 37.47% | 0.868 | -14,179.61 |
| 2025 | 422 | 38.86% | 0.925 | -9,648.00 |
| 2026-01～07 | 220 | 38.18% | 0.881 | -5,710.75 |
| 2026-07のみ | 33 | 42.42% | 1.162 | +851.98 |

### compression first retest base

| slice | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023 sanity | 388 | 26.03% | 0.408 | -11,333.81 |
| 2024 | 412 | 30.10% | 0.695 | -13,702.04 |
| 2025 | 391 | 34.53% | 0.856 | -6,849.55 |
| 2026-01～07 | 227 | 29.96% | 0.671 | -7,332.76 |
| 2026-07のみ | 29 | 31.03% | 0.794 | -378.33 |

### ATR impulse exhaustion base

| slice | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023 sanity | 260 | 38.08% | 0.845 | -2,719.85 |
| 2024 | 323 | 37.15% | 1.093 | +5,416.50 |
| 2025 | 367 | 35.15% | 0.911 | -7,099.71 |
| 2026-01～07 | 179 | 37.43% | 0.974 | -754.44 |
| 2026-07のみ | 28 | 53.57% | 1.726 | +1,777.19 |

## baseと近傍

| family | configuration | role | trades | PF | net USD | 最大winner除外PF | double-cost PF |
|---|---|---|---:|---:|---:|---:|---:|
| HTF trend pullback | `BASE_ATR_SL` | base | 1,984 | 0.833 | -62,308.61 | 0.828 | 0.735 |
| HTF trend pullback | `N1_FIXED_180_SL` | neighbor | 2,189 | 0.858 | -40,919.30 | 0.857 | 0.719 |
| HTF trend pullback | `N2_STRUCTURE_SL` | neighbor | 1,902 | 0.887 | -43,991.82 | 0.876 | 0.792 |
| high/low sweep | `BASE_PREVIOUS_D1_STRUCTURE_SL` | base | 1,061 | 0.896 | -29,538.35 | 0.885 | 0.821 |
| high/low sweep | `N1_LOOKBACK96_STRUCTURE_SL` | neighbor | 1,442 | 0.902 | -37,973.22 | 0.895 | 0.827 |
| high/low sweep | `N2_PREVIOUS_D1_ATR_SL` | neighbor | 1,192 | 0.910 | -21,661.97 | 0.900 | 0.812 |
| compression | `BASE_RETEST_STRUCTURE_SL` | base | 1,030 | 0.757 | -27,884.35 | 0.734 | 0.609 |
| compression | `N1_ATR_SL` | neighbor | 984 | 0.788 | -37,679.02 | 0.778 | 0.689 |
| compression | `N2_FIXED_180_SL` | neighbor | 1,009 | 0.779 | -30,236.75 | 0.777 | 0.653 |
| ATR impulse | `BASE_ATR_SL` | base | 869 | 0.985 | -2,437.65 | 0.971 | 0.878 |
| ATR impulse | `N1_FIXED_180_SL` | neighbor | 874 | 0.907 | -10,522.81 | 0.904 | 0.759 |
| ATR impulse | `N2_IMPULSE_STRUCTURE_SL` | neighbor | 829 | 1.057 | +11,484.01 | 1.042 | 0.966 |

ATR impulseのstructure-SL近傍だけは合算PF 1.057、net +11,484.01 USDだった。しかしformal baseが不合格であるため昇格させない。また、この近傍自身も最大winner除外PF 1.10とdouble-cost PF 1.05の事前gateを通過していない。

## 方向別・causal volatility別

| family | segment | trades | PF | net USD |
|---|---|---:|---:|---:|
| HTF trend pullback | LONG | 1,086 | 0.837 | -30,736.59 |
| HTF trend pullback | SHORT | 898 | 0.830 | -31,572.02 |
| HTF trend pullback | high vol | 1,028 | 0.869 | -29,135.41 |
| HTF trend pullback | low vol | 956 | 0.780 | -33,173.20 |
| high/low sweep | LONG | 490 | 0.849 | -21,748.94 |
| high/low sweep | SHORT | 571 | 0.944 | -7,789.41 |
| high/low sweep | high vol | 775 | 0.886 | -25,371.48 |
| high/low sweep | low vol | 286 | 0.932 | -4,166.87 |
| compression | LONG | 499 | 0.773 | -12,355.40 |
| compression | SHORT | 531 | 0.743 | -15,528.95 |
| compression | high vol | 331 | 0.904 | -4,067.27 |
| compression | low vol | 699 | 0.671 | -23,817.08 |
| ATR impulse | LONG | 454 | 1.151 | +12,819.00 |
| ATR impulse | SHORT | 415 | 0.815 | -15,256.66 |
| ATR impulse | high vol | 573 | 1.000 | -39.51 |
| ATR impulse | low vol | 296 | 0.945 | -2,398.15 |

ATR impulse LONG、2026年7月、高volなど、一部sliceだけを見ると良い箇所は存在した。しかし、結果後に良かった方向・月・ATR帯だけを残すことは禁止されているため、救済や再定義は行わない。

## base 4familyのglobal one-position audit

| period | trades | 勝率 | PF | net USD | Max DD |
|---|---:|---:|---:|---:|---:|
| 2023 sanity | 1,449 | 34.64% | 0.686 | -30,639.56 | 30,639.56 |
| 2024 | 1,613 | 35.46% | 0.887 | -32,921.84 | 44,942.39 |
| 2025 | 1,615 | 34.67% | 0.863 | -49,063.35 | 59,370.71 |
| 2026-01～07 | 868 | 36.06% | 0.886 | -16,252.50 | 22,909.74 |
| 2024～2026-07 | 4,096 | 35.28% | 0.876 | -98,237.69 | 110,672.09 |
| 2026-07のみ | 119 | 43.70% | 1.184 | +2,333.09 | 3,287.64 |

これはaudit-onlyであり、family別の正式判定には使用していない。

## causal・再現監査

- setup・context・confirmation・SL計算にはdecision時点までのclosed barだけを使用した。
- open/as-of足、将来高値・安値・終値、将来ATR、将来HTF状態を使用していない。
- CSV最新行はclosedとして扱った。
- exact M1 entry欠損時は無効化し、次のM1へfallbackしていない。
- same-M1 SL/TP collisionはSL-first。
- one-positionはconfigurationごとに独立適用し、cross-family overlapはfamily評価では許可した。
- 2023-01-01～2023-02-15の実データparity sliceで、reference実装と高速実装はraw candidate semantics 762件、trade 558件が完全一致した。
- synthetic testでexact-entry欠損、entry後M1欠損区間の継続、adverse gap open、same-M1 collisionを確認した。
- input SHA256とrun auditを別JSONへ保存する。

## 最終境界

4baseすべて不合格であり、`RESEARCH_CANDIDATE_REQUIRES_FRESH_PROSPECTIVE_CONFIRMATION`へ到達したfamilyはない。

不採用結果も削除せず、正式research recordとして維持する。Stage55には影響を与えない。
