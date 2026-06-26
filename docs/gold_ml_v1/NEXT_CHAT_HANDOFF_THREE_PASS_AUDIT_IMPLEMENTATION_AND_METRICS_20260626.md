# GOLD_ML_V1 次チャット引き継ぎ 3回監査

Date: 2026-06-26  
Status: `THREE_PASS_HANDOFF_AUDIT_COMPLETE`  
Authoritative stack: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`

## 0. 結論

3回の独立確認を実施し、次の不足を修正した。

1. WATCH-029-A / WATCH-030-Aの個別configが旧`accumulated=false`のままだった。
2. WATCH-031-Aの個別configが旧Research WATCH表記のままだった。
3. 「研究ロジック・成績は確定したが、repo実行コードには未実装」という状態を候補別に示す表がなかった。
4. 追加候補の全期間、強コスト、2026、年別成績を1か所で比較できる台帳がなかった。

修正後の状態:

- accumulated: 15
- Research WATCH: 9
- retired: WATCH-031-A
- audit-only
- このチャットで追加した029〜034の**実行コード実装は0件**
- config、研究ロジック、監査成績、実装契約はGitHub保存済み

重要: `accumulated`は研究stackへの採用状態であり、runtime code実装済みを意味しない。

---

## 1. 第1確認 — 状態・候補・成績の完全性

### 1.1 状態照合

照合対象:

- `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
- WATCH-029-A〜034-Cの個別config
- retired WATCH-031-A
- handoff snapshot

確認結果:

- stack Wの15 accumulated / 9 Research WATCH / 1 retiredと一致。
- WATCH-029-A / 030-Aの個別configを`ACCUMULATED_POST_AUDIT_PROSPECTIVE_ONLY`へ同期。
- WATCH-031-Aの個別configを`RETIRED_INVALID_UNDER_MINIMUM_TP5_RULE`へ変更。
- WATCH-031-Aは実装禁止、ID再利用禁止、監査履歴のみ保存。

### 1.2 追加候補の成績台帳

以下はXAUUSD価格差。口座損益ではない。

| ID | state | exit | Base n | Base hit/positive | Base PF | Base mean | Base total | Base DD | Strong n | Strong hit/positive | Strong PF | Strong mean | Strong total | Strong DD | 2026 n | 2026 PF | 2026 total |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WATCH-029-A | accumulated | TP5 / emergency 10 / 12h | 198 | TP 77.78%, positive 81.82% | 2.603 | +2.446 | +484.22 | 30.00 | 198 | TP 76.26%, positive 80.30% | 2.246 | +2.155 | +426.77 | 30.00 | 23 | 2.375 | +55.00 |
| WATCH-030-A | accumulated | TP5 / emergency 10 / 12h | 106 | TP 71.70%, positive 77.36% | 1.849 | +1.680 | +178.11 | 35.00 | 108 | TP 68.52%, positive 73.15% | 1.495 | +1.129 | +121.93 | 38.14 | 14 | 3.000 | +40.00 |
| WATCH-032-A | research | TP5 / protective 6 / 24h | 97 | TP=positive 71.13% | 2.119 | +1.878 | +182.20 | 18.00 | 98 | TP=positive 69.39% | 1.891 | +1.602 | +156.98 | 18.30 | 14 | 3.056 | +37.00 |
| WATCH-033-A | research | component TP5/7.5 / protective 5 / 8h | 70 | full TP 50.00%, positive 71.43% | 2.434 | +1.743 | +122.01 | 10.00 | 70 | full TP 50.00%, positive 71.43% | 2.150 | +1.514 | +105.95 | 10.72 | 13 | 2.250 | +25.00 |
| WATCH-034-A | research | fixed TP75 / protective 10 / 168h | 96 | TP 18.75%, positive 29.17% | 2.403 | +9.939 | +954.17 | 74.25 | 98 | TP 17.35%, positive 27.55% | 2.195 | +8.744 | +856.90 | 70.70 | 17 strong | 3.090 | +253.30 |
| WATCH-034-B | research | fixed TP100 / protective 5 / 168h | 112 | TP 5.36%, positive 15.18% | 2.195 | +5.067 | +567.47 | 80.00 | 112 | TP 6.25%, positive 14.29% | 2.095 | +4.785 | +535.87 | 81.60 | 16 strong | 2.798 | +128.40 |
| WATCH-034-C | research | 25% at +50, 75% runner +100, initial protective 8 | 101 | runner 7.92%, milestone 23.76%, positive 29.70% | 2.573 | +8.845 | +893.37 | 68.00 | 101 | runner 6.93%, milestone 21.78%, positive 27.72% | 2.279 | +7.489 | +756.37 | 69.20 | 17 strong | 2.679 | +176.80 |

WATCH-033-Aのpositive rateはprofitable time exitを含む。full target hit rateと混同しない。

WATCH-034-A/B/Cは同じentry lineageの排他的exit variant。3つの件数・損益を足してはいけない。

### 1.3 年別成績

#### WATCH-029-A Base / Strong cost

| Year | Base n | Base TP rate | Base PF | Base total | Strong n | Strong TP rate | Strong PF | Strong total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 66 | 74.24% | 3.730 | +186.57 | 66 | 74.24% | 3.238 | +175.28 |
| 2024 | 47 | 80.85% | 3.050 | +130.75 | 47 | 80.85% | 3.027 | +129.87 |
| 2025 | 62 | 77.42% | 1.861 | +111.90 | 62 | 74.19% | 1.544 | +81.62 |
| 2026 cutoff | 23 | 82.61% | 2.375 | +55.00 | 23 | 78.26% | 1.800 | +40.00 |

#### WATCH-030-A Base / Strong cost

| Year | Base n | Base TP rate | Base PF | Base total | Strong n | Strong TP rate | Strong PF | Strong total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 31 | 64.52% | 1.920 | +51.24 | 31 | 64.52% | 1.813 | +46.35 |
| 2024 | 33 | 75.76% | 1.984 | +62.04 | 35 | 65.71% | 1.159 | +15.48 |
| 2025 | 28 | 67.86% | 1.350 | +24.83 | 28 | 67.86% | 1.298 | +21.50 |
| 2026 cutoff | 14 | 85.71% | 3.000 | +40.00 | 14 | 85.71% | 2.911 | +38.60 |

#### WATCH-032-A Base / Strong cost

| Year | Base n | Base TP rate | Base PF | Base total | Strong n | Strong TP rate | Strong PF | Strong total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 36 | 72.22% | 2.372 | +75.20 | 37 | 67.57% | 1.844 | +56.08 |
| 2024 | 25 | 64.00% | 1.481 | +26.00 | 25 | 64.00% | 1.428 | +23.50 |
| 2025 | 22 | 72.73% | 2.222 | +44.00 | 22 | 72.73% | 2.142 | +41.80 |
| 2026 cutoff | 14 | 78.57% | 3.056 | +37.00 | 14 | 78.57% | 2.945 | +35.60 |

#### WATCH-033-A Base / Strong cost

| Year | Base n | Base positive | Base full TP | Base PF | Base total | Strong n | Strong positive | Strong full TP | Strong PF | Strong total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 16 | 68.75% | 25.00% | 2.421 | +19.72 | 16 | 68.75% | 25.00% | 1.610 | +11.69 |
| 2024 | 22 | 81.82% | 50.00% | 4.451 | +56.01 | 22 | 81.82% | 50.00% | 4.049 | +51.52 |
| 2025 | 19 | 63.16% | 57.89% | 1.608 | +21.28 | 19 | 63.16% | 57.89% | 1.533 | +19.04 |
| 2026 cutoff | 13 | 69.23% | 69.23% | 2.250 | +25.00 | 13 | 69.23% | 69.23% | 2.162 | +23.70 |

#### WATCH-034-A Strong cost

| Year | n | TP75 hits | TP rate | PF | mean | total | DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 21 | 1 | 4.76% | 1.407 | +2.936 | +61.66 | 70.70 |
| 2024 | 26 | 5 | 19.23% | 2.565 | +10.943 | +284.52 | 60.60 |
| 2025 | 34 | 6 | 17.65% | 1.980 | +7.571 | +257.42 | 70.70 |
| 2026 cutoff | 17 | 5 | 29.41% | 3.090 | +14.900 | +253.30 | 50.50 |

#### WATCH-034-B Strong cost

| Year | n | TP100 hits | TP rate | PF | mean | total | DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 22 | 0 | 0.00% | 1.899 | +3.544 | +77.96 | 35.70 |
| 2024 | 33 | 3 | 9.09% | 2.908 | +8.256 | +272.46 | 61.20 |
| 2025 | 41 | 2 | 4.88% | 1.302 | +1.391 | +57.05 | 81.60 |
| 2026 cutoff | 16 | 2 | 12.50% | 2.798 | +8.025 | +128.40 | 40.80 |

#### WATCH-034-C Strong cost

| Year | n | milestone hits | runner hits | runner rate | PF | mean | total | DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 21 | 2 | 0 | 0.00% | 1.545 | +3.156 | +66.27 | 56.70 |
| 2024 | 28 | 6 | 2 | 7.14% | 2.876 | +11.398 | +319.16 | 48.60 |
| 2025 | 35 | 10 | 2 | 5.71% | 1.999 | +5.547 | +194.14 | 40.50 |
| 2026 cutoff | 17 | 4 | 3 | 17.65% | 2.679 | +10.400 | +176.80 | 40.50 |

---

## 2. 第2確認 — どこまで実装済みか

### 2.1 実装レベル定義

- Level 0: idea only
- Level 1: audit logic prototyped and diagnostic backtest completed
- Level 2: config, metrics and implementation contract committed
- Level 3: executable candidate detector committed
- Level 4: exact-M1 execution integration and parity tests committed
- Level 5: accumulated portfolio replay integration
- Level 6: runtime/live integration

### 2.2 現在の到達点

このチャットで追加したWATCH-029〜034は**すべてLevel 2**。

| ID | audit prototype/backtest | config committed | metrics committed | implementation contract | executable detector in repo | exact-M1 integration | parity tests | portfolio integration | live/runtime |
|---|---|---|---|---|---|---|---|---|---|
| WATCH-029-A | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |
| WATCH-030-A | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |
| WATCH-032-A | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |
| WATCH-033-A | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |
| WATCH-034-A | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |
| WATCH-034-B | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |
| WATCH-034-C | 完了 | 完了 | 完了 | 完了 | 未実装 | 未実装 | 未実装 | 未実装 | 未実装 |

### 2.3 GitHubで確認した事実

各candidate creation commitのchanged fileはcandidate config JSONだけだった。

- WATCH-029-A creation: config only
- WATCH-030-A creation: config only
- WATCH-032-A creation: config only
- WATCH-033-A creation: config only
- WATCH-034-A/B/C creation: config only

その後に追加されたのはstack、診断結果、実装契約、handoff文書。candidate-specific Python module、unit test、parity test、CLI wiring、runtime wiringはcommitされていない。

### 2.4 ローカル監査コードの扱い

探索時には一時的なPython scripts、M1 resolved registry、CSV artifactを生成してbacktestした。しかし、それらの大半はチャットsandboxのローカルartifactであり、GitHubの実行コードとしては保存していない。

新チャットはローカルartifactが残っている前提で進めてはならない。

実装時は:

1. implementation contractからコード化
2. raw CSVからregistryを再生成
3. この文書のexpected metricsへparity
4. 差異があれば実装を止めて原因監査

### 2.5 候補別blocker

| ID | 実装開始に必要なもの | 主なblocker |
|---|---|---|
| WATCH-029-A | frozen 13 proposal registry、canonical source-family map、exact_group_size | 元13候補の完全proposal再現とfamily mapがrepoに未固定 |
| WATCH-030-A | common feature engine、previous-day high、M15/H4 detector、M1 resolver | detector moduleとparity test未実装 |
| WATCH-032-A | OR13 session builder、M15/H4 slope、range-state、M1 resolver | detector moduleとparity test未実装 |
| WATCH-033-A | R13_19 range、rolling20、3component priority、component-specific TP、M1 resolver | union/priority/time-exit parityが未実装 |
| WATCH-034-A/B/C | common Inside+NR7 detector、H1/H4 causal join、3種類のexit policy | sibling exclusivity、168h resolver、runner orderingのtest未実装 |

---

## 3. 第3確認 — 次チャットが迷わないか

### 3.1 読み順

次チャットは次の順で読む。

1. `docs/gold_ml_v1/NEXT_CHAT_START_HERE_20260626.md`
2. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
3. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_15_ACCUMULATED_9_WATCHES_20260626.md`
4. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
5. `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
6. `config/gold_ml_v1/handoff_snapshot_20260626.json`
7. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
8. 対象candidate config

### 3.2 用語の固定

- accumulated = research stackに残す判断。実行コード実装済みではない。
- Research WATCH = prospective監視候補。実装済みではない。
- implemented = executable detector + M1 resolver integration + parity testsがGitHubにcommit済みの場合だけ使用する語。
- local audit prototype = 一時scriptで診断済みだがrepo executable implementationではない。
- USD-price = XAUUSD価格差。口座損益ではない。

### 3.3 絶対に誤読しない事項

- WATCH-029-A / 030-Aはaccumulatedだが未実装。
- WATCH-032-A / 033-A / 034-A/B/CはResearch WATCHかつ未実装。
- WATCH-031-Aはretired、実装禁止。
- WATCH-034-A/B/Cは3候補を同時注文しない。
- 034の件数・損益を合算しない。
- 033のpositive rateとfull TP rateを混同しない。
- 2024〜2026をholdoutと呼ばない。
- true prospectiveは2026-06-26より後。

### 3.4 次チャットの最初の回答

repoを読んだ後、次だけを報告する。

- authoritative stack ID
- accumulated 15
- Research WATCH 9
- retired WATCH-031-A
- implementation level 2/6
- added WATCH executable implementation count 0
- audit-only維持

ユーザーの次の指示前に実装・再探索・昇格を始めない。

---

## 4. 3回監査結果

### Pass 1 — candidate/state/metrics

`PASS_AFTER_CORRECTION`

- 候補数一致
- state矛盾修正
- all/base/strong-cost/2026/year metricsを台帳化

### Pass 2 — implementation status

`PASS_AFTER_CORRECTION`

- Level 2/6と明記
- executable implementation 0件と明記
- candidate別blockerを明記

### Pass 3 — navigation and ambiguity

`PASS_AFTER_CORRECTION`

- 読み順へ本監査文書を追加
- accumulatedとimplementedを分離
- 031 retired、034 sibling exclusivity、033 metric semanticsを再確認

## 5. 残る既知の制限

- frozen nine全てのexact registryは揃っていない。
- accumulated15全体のauthoritative raw-event portfolio replayは未完了。
- WATCH-029-Aのfrozen 13 proposal registry/family mapは未固定。
- local audit scriptsと大きなresolved registriesはGitHub executable sourceではない。
- 034-A/B/Cの最終採用variantは未決定。
- prospective実績はまだ0件。

これらは漏れではなく、明示された未完了項目である。
