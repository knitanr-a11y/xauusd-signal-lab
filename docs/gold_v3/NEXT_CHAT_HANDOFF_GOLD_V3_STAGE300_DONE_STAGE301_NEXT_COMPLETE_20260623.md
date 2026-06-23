# NEXT CHAT HANDOFF — GOLD V3 Stage300完了 / Stage301実行待ち

Date: 2026-06-23  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch policy: **mainへ直接反映のみ**  
Current handoff state: **Stage300実行完了、Stage301 feature-contract diagnosticは準備済み・未実行**

---

# 0. この文書の目的

この文書は、現在のチャットで実施したStage280 parity調査、途中で判明した誤り、GitHub mainへ反映したファイル、ユーザー環境で得た実行結果、現在地点、次に実行するStage301、その後の分岐を新しいチャットへ正確に引き継ぐためのもの。

新しいチャットでは、この文書を最初から最後まで読み、Stage295以前へ戻って同じ調査をやり直さないこと。

**再開地点はStage301 feature-contract diagnosticの実行結果確認。**

---

# 1. 2026-06-23 三重確認の結果

この引き継ぎ文書は、次の3段階で再確認した。

## 1回目 — 数値・時系列確認

ユーザー実行ログと現行学習コードの固定値を照合した。

確認済み:

- Stage280 expected threshold / fixture
- Stage280 fit_n / cal_n / positive_fit
- Stage280 2026 test_n / positives / ROC-AUC / PR-AUC
- Stage281 expected threshold / fixture
- Stage300 335モデルの結果
- Stage301が未実行であること

この確認で、旧文書の次の誤りを発見し修正した。

**誤:** 初回Stage280 `fit_n=1714 / cal_n=492 / positive_fit=75`  
**正:** 履歴不足時の初回は `fit_n=1714 / cal_n=492 / positive_fit=0`。  
`positive_fit=75`は、その後に母集団を`4974 / 1809`へ直したうえでLONG-onlyと誤解釈した時の値。

## 2回目 — GitHub main実ファイル確認

次の現物をmainで確認した。

- Stage292候補priority
- Stage292 DD / cooldown / resolved-loss gate
- Stage293 Stage67 seed + actual live BASE close契約
- Stage292 bootstrap JSON
- Stage280/281 training constants
- Stage300 diagnostic
- Stage301 feature-contract diagnostic
- Stage301 artifact-recovery diagnostic
- Stage301実行BAT

## 3回目 — 新チャットが迷わないか確認

次を明文化した。

- Stage300結果は**ユーザー実行ログ由来**
- Stage301スクリプトは**GitHub mainで確認済み**
- Stage301 feature-contract diagnosticは**まだ実行されていない**
- 現在BATが実行するのはfeature-contract diagnostic
- artifact recoveryはfeature-contract不一致時の次工程で、現在BATには接続していない
- `final_signal_enabled=True`だが、MT5注文とDiscordはOFF
- 近似候補を正式採用しない

---

# 2. 絶対禁止事項・不変契約

以下は必ず維持する。

- GOLD V3は `audit-only`
- GOLD V2 / 旧GOLD / DISC8 / Stage41は
  - 読まない
  - 使わない
  - 参照しない
  - fallbackにしない
- CSV最新行はCSV契約上 `closed`
- `open` / `as-of` 禁止
- candidate / entry / gateはentry時点で知り得るclosed情報だけ
- health / rolling / cooldown判断は `exit_dt <= current entry_dt` のresolved-only
- 時刻基準はJSTではなく **MT5サーバー時刻**
- Stage280 / 281 / 284の既存契約は、明示変更しない限り維持
- 2026データを学習へ使わない
- parity tolerance `1e-12`を緩めない
- 近似モデルや近似thresholdを正式採用しない
- `expected`値を書き換えてPASS扱いしない
- ユーザーにブランチ選択やPR判断を求めない
- production変更は **mainへ直接反映**
- ユーザー操作は原則 `GitHub Desktop → main → Fetch origin → Pull origin`
- final signal判定は有効
- MT5自動注文はOFF
- Discord通知はOFF
- partial closeはOFF

---

# 3. 検証済みGitHub mainスナップショット

以下のSHAは2026-06-23の再確認時点。

- Stage280/281 training:
  - `scripts/gold_v3_runtime/gold_v3_289_train_live_models_audit.py`
  - blob SHA: `8798908e8a3a6bcf54af82929f451d5696d1be28`
- Stage292 live candidates:
  - `scripts/gold_v3_runtime/gold_v3_292_live_candidates.py`
  - blob SHA: `4eb349b325360b97f973880fd258682e4504d0a8`
- Stage292 portfolio state:
  - `scripts/gold_v3_runtime/gold_v3_292_portfolio_state.py`
  - blob SHA: `d09e4b3525642c3966c5ce6b11f18b7c92b5d692`
- Stage292 live runner:
  - `scripts/gold_v3_runtime/gold_v3_292_safe_portfolio_live.py`
  - blob SHA: `441b07b1ebe1fed8056e5ec3e88e21c8f7cc1814`
- Stage293 BASE health:
  - `scripts/gold_v3_runtime/gold_v3_293_base_health_live.py`
  - blob SHA: `1214973caa7019601be2a504869112c2dd1de306`
- Stage292 bootstrap:
  - `docs/gold_v3/gold_v3_stage292_safe_portfolio_bootstrap.json`
  - blob SHA: `a602126031ca093fb4286eac52b62b416304d7df`
- Stage300 diagnostic:
  - `scripts/gold_v3_runtime/gold_v3_300_stage280_hyperparameter_diagnostic.py`
  - blob SHA: `45ee4f14ce2cc2ec3b2eb2bff39f898b557faec9`
- Stage301 feature-contract diagnostic:
  - `scripts/gold_v3_runtime/gold_v3_301_stage280_feature_contract_diagnostic.py`
  - blob SHA: `927741da9c75f7992821ad216c4d53f2c2bc4916`
- Stage301 artifact recovery:
  - `scripts/gold_v3_runtime/gold_v3_301_stage280_artifact_recovery.py`
  - blob SHA: `306f94e62266712acaebe698811c1f08501f89d6`
- 現在のStage301実行BAT:
  - `scripts/gold_v3_runtime/bat/run_gold_v3_295_stage280_population_diagnostic.bat`
  - blob SHA: `33c5e29f82638b169e8095478f7b0a96ff83745b`

新しいチャットでは、mainが更新されている可能性があるため、必要なら再度fetchして現物を確認すること。

---

# 4. Stage292 / Stage293の現行契約

## 4.1 Stage292 safe portfolio priority

mainコードで確認済み:

- BASE priority `0`
- Stage280 priority `10`
- Stage281 priority `20`
- Stage286 priority `60`

## 4.2 Stage292 gate

mainコードで確認済み:

- pending/open最大1
- additionはDD `<= 30`
- addition共通cooldown `12h`
- Stage281は直近resolved BASE loss後`72h`以内
- Stage286はDD `<= 10`
- Stage286は直近resolved addition loss後`24h`
- BASE holdingがMT5 server hour `00/01`へ重なる場合は拒否
- candidateは`entry_dt, priority, candidate_id`順

## 4.3 Stage292出力状態

mainコードで確認済み:

- `final_signal_enabled=True`
- `mt5_order_enabled=False`
- `discord_enabled=False`
- actual fill / close updateが必要

## 4.4 Stage293 BASE health

mainコードで確認済み:

- Stage67 closed outcomesはcutover history snapshotとしてのみ使用
- bootstrap後はStage292 ledgerの実際のBASE CLOSEDだけを追加
- live BASE closeは `bootstrap.asof < exit_dt <= current entry_dt` のresolved-only
- rolling window `30`
- minimum history `20`
- PF threshold `1.10`
- loss streak limit `3`

## 4.5 Stage292 bootstrap

main JSONで確認済み:

- status: `GOLD_V3_292_SAFE_PORTFOLIO_BOOTSTRAP_READY`
- portfolio: `PLUS_STRICT_SAFE`
- as-of: `2026-06-19 15:51:00`
- equity: `965.6008808154019`
- peak: `985.2064859116765`
- realized drawdown: `19.605605096274644`
- last candidate entry: `2026-06-19 08:30:00`
- last candidate loss exit: `2026-04-29 21:45:00`
- last BASE exit: `2026-06-19 15:51:00`
- last BASE pnl: `-19.605605096274644`
- open position: `false`

Stage292 / 293 CIが過去にPASSしたことは過去チャット記録由来。今回の三重確認ではCIを再実行していないため、最新CI状態を断言する場合は新チャットで確認すること。

---

# 5. Stage289履歴回収で完了したこと

## 5.1 exporter

- `scripts/gold_v3_runtime/mt5/ExportGoldStage289TrainingHistory_v110.mq5`
- `scripts/gold_v3_runtime/bat/install_gold_v3_289_training_m1_exporter.bat`

## 5.2 ユーザー取得済み履歴

ユーザー実行ログ由来:

- M1 rows `902109`
  - first `2023-12-01 01:00:00`
  - last `2026-06-23 13:56:00`
- M5 rows `180597`
- M15 rows `60203`
- H1 rows `20002`
- H4 rows `10000`
- D1 rows `5000`

preflight結果:

- status `PASS`
- blockers `[]`
- H1 decisions 2024-2025: `11822`
- valid M1 240m windows: `10271`
- coverage ratio: `0.8688039248858062`
- closed CSV contract: `true`

履歴不足は現在の阻害要因ではない。

---

# 6. parity固定値

## 6.1 Stage280 expected

現行学習コードおよび監査結果で使用中:

- threshold: `0.5927349103795366`
- fixture score: `0.5949591748604749`
- fixture time: `2026-06-19 08:00:00`
- tolerance: `1e-12`
- fit_n: `4974`
- cal_n: `1809`
- positive_fit: `245`
- test_n: `1606`
- test positives: `65`
- 2026 ROC-AUC: `0.6904307891978236`
- 2026 PR-AUC: `0.08009367826075599`

期待bucket:

- q90: n `120`, hits `10`
- q95: n `64`, hits `8`
- q97.5: n `25`, hits `3`
- q99: n `11`, hits `1`

## 6.2 Stage281 expected

- threshold: `0.5525199124029727`
- fixture score: `0.6586538142862226`
- fixture time: `2026-06-17 10:00:00`
- tolerance: `1e-12`

ユーザー実行ログで完全一致済み:

- fit_n `16041`
- cal_n `6371`
- positive_fit `2515`
- parity `true`

Stage281は変更しない。

---

# 7. このチャットで行ったStage280調査

## 7.1 履歴不足時の初回再学習

ユーザー実行ログ由来:

- Stage280 fit_n `1714`
- Stage280 cal_n `492`
- Stage280 positive_fit `0`
- Stage281 fit_n `2941`
- Stage281 cal_n `6371`
- Stage281 positive_fit `0`

原因は、当時参照していたM1履歴が短く、未来240分ラベル窓と学習期間が不足していたこと。

ここはLONG-only `positive_fit=75`の段階とは別。

## 7.2 Stage295 population diagnostic

追加:

- `scripts/gold_v3_runtime/gold_v3_295_stage280_population_diagnostic.py`

確定した母集団:

`H4 non-neutral AND future_valid`

元監査の`fit_n=4974 / cal_n=1809`へ完全一致した。

`future_valid`は以下を満たす行:

- ATRが有効
- exact M1 entryが存在
- 未来240分窓に十分なM1がある
- 不完全な未来窓を陰性として残さない

## 7.3 LONG-only誤解釈

母集団修正後、一度Stage280をLONG-onlyと誤解釈した。

結果:

- fit_n `4974`
- cal_n `1809`
- positive_fit `75`
- threshold `0.21033218812350174`
- fixture `0.5560333414497304`

75 / 4974 = 約1.5%で、元監査REV base rate約4.9%と不整合。

この解釈は誤り。Stage296 LONG-only文書はsuperseded扱い。

## 7.4 pooled REVへ修正

現在の教師候補:

- H4非中立の両方向
- predicted reversal direction = `-h4_trend`
- LONG / SHORT両方のREV onsetを陽性
- signed featureをpredicted REV方向へ正規化
- future_validだけ学習

結果:

- fit_n `4974`
- cal_n `1809`
- positive_fit `245`
- fit base rate `0.049256131885806194`
- Stage281 parity `true`

ただしStage280は不一致:

- threshold `0.601208947025034`
- fixture `0.671670783296924`

---

# 8. Stage298 diagnostic

ファイル:

- `scripts/gold_v3_runtime/gold_v3_298_stage280_model_variant_diagnostic.py`

比較:

- direction normalizationあり / なし
- wick swapあり / なし
- relative align / raw align
- volume / spread有無
- engineered特徴有無
- global onset / filtered onset

ユーザー実行ログの最良候補:

- `normalized_no_wick_swap_global_onset`
- threshold `0.5935126932083092`
- fixture `0.6280999852097368`
- ROC-AUC約 `0.68749`
- test_nが`1602`で、元監査`1606`より4件少なかった

完全一致なし。

---

# 9. Stage299 diagnostic

ファイル:

- `scripts/gold_v3_runtime/gold_v3_299_stage280_wick_weight_diagnostic.py`

比較:

- no-swap raw reject
- no-swap directional reject
- raw wick列除外
- full wick swap
- raw align
- volume / spread除外
- scale_pos_weight / balanced / none / bagging

ユーザー実行ログの1位:

- frame `normalized_no_swap_directional_reject`
- weight `scale_pos`
- threshold `0.6034414845184862`
- fixture `0.6177927062319107`
- ROC-AUC `0.6927569510307992`
- PR-AUC `0.08063170773927932`

完全一致なし。

---

# 10. Stage300 hyperparameter diagnostic

ファイル:

- `scripts/gold_v3_runtime/gold_v3_300_stage280_hyperparameter_diagnostic.py`

探索:

- positive-class weight
- n_estimators
- learning_rate
- num_leaves
- max_depth
- min_child_samples
- reg_alpha / reg_lambda
- colsample_bytree
- random_state
- max_bin
- min_split_gain
- min_child_weight
- 上位候補周辺のlocal refinement

ユーザー実行ログ:

- status: `GOLD_V3_300_STAGE280_HYPERPARAMETER_DIAGNOSTIC_READY`
- evaluated_models: `335`
- exact_matches: `[]`

1位:

- frame `normalized_no_swap_directional_reject_no_raw_wicks`
- feature_count `266`
- n_estimators `220`
- learning_rate `0.03`
- num_leaves `15`
- max_depth `5`
- min_child_samples `60`
- reg_alpha `1.5`
- reg_lambda `6.0`
- scale_pos_weight `18.5`
- threshold `0.5926760775274067`
- fixture `0.6102252160407501`
- ROC-AUC `0.6901013328008786`
- PR-AUC `0.08101204299523959`

1位bucket:

- q90 `109 / 8`
- q95 `62 / 7`
- q97.5 `22 / 2`
- q99 `12 / 1`

元監査bucket:

- q90 `120 / 10`
- q95 `64 / 8`
- q97.5 `25 / 3`
- q99 `11 / 1`

結論:

**335通りで完全一致しなかったため、残差を単純なLightGBMハイパーパラメータ差と扱わない。**

候補順位も異なる。次は特徴一覧、特徴順序、時間足構成、テスト母集団を調べる。

**Stage300をもう一度実行しない。**

---

# 11. 現在の次工程 — Stage301-A feature-contract diagnostic

GitHub mainで確認済み:

- `scripts/gold_v3_runtime/gold_v3_301_stage280_feature_contract_diagnostic.py`

これは準備済みだが、**ユーザー環境ではまだ実行されていない。**

比較するfeature variant:

- all current order
- sorted order
- reversed order
- timeframe-grouped order
- raw wick除外
- volume除外
- spread除外
- volume + spread除外
- engineered除外
- engineered only
- M1 / M5 / M15 / H1 / H4 / D1各drop
- LTF only
- HTF only
- 複数時間足組合せ
- 各variantのsorted / timeframe-grouped版

モデル設定:

- Stage300 rank1
- Stage300 rank2
- Stage300 scalar best
- Stage300 near-fixture

テスト母集団:

1. `future_valid_first1606`
2. `all_non_neutral_first1606`
3. `all_non_neutral_through_fixture_plus4h`

出力status:

`GOLD_V3_301_STAGE280_FEATURE_CONTRACT_DIAGNOSTIC_READY`

出力ファイル:

`stage301_stage280_feature_contract_diagnostic.json`

この診断はモデルやthresholdを正式保存しない。

---

# 12. Stage301-B artifact recovery

GitHub mainに補助スクリプトとして存在:

- `scripts/gold_v3_runtime/gold_v3_301_stage280_artifact_recovery.py`

検索対象:

- 現在clone
- sibling clone
- GOLD V3 output
- reachable Git blobs
- unreachable Git blobs
- Stage280 source / feature list / model artifact
- expected threshold / fixture / AUC token

禁止領域を除外する:

- gold_v2
- old_gold
- disc8
- stage41
- legacy_gold

**現在のBATはartifact recoveryを実行しない。**

Stage301-Aで`exact_matches=[]`だった場合に、BAT接続または専用BAT追加をmainへ直接行ってから実行する。

---

# 13. 現在のBATとユーザーが次に行う操作

GitHub main上のBAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_295_stage280_population_diagnostic.bat`

現在の内容はStage301-A feature-contract diagnosticを実行する。

期待ログ:

`[INFO] Running Stage280 feature-contract diagnostic...`

実行対象:

`gold_v3_301_stage280_feature_contract_diagnostic.py`

## 新しいチャット開始直後の操作

1. GitHub Desktopでrepoが`knitanr-a11y/xauusd-signal-lab`であることを確認
2. branchが`main`であることを確認
3. `Fetch origin`
4. 更新がある場合だけ`Pull origin`
5. BATを実行

```text
scripts\gold_v3_runtime\bat\
run_gold_v3_295_stage280_population_diagnostic.bat
```

出力:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\
289_training_history\
stage301_stage280_feature_contract_diagnostic.json
```

ファイル添付できない場合は、次だけコピペする。

- `status`
- `search`
- `exact_matches`
- `ranking`先頭10件

---

# 14. Stage301結果後の分岐

## A. exact_matchesが1件以上

以下をすべて確認する。

- fit_n `4974`
- cal_n `1809`
- positive_fit `245`
- test_n `1606`
- positive_test `65`
- threshold完全一致
- fixture完全一致
- ROC-AUC完全一致
- PR-AUC完全一致
- q90 / q95 / q97.5 / q99 bucket完全一致

すべて一致した候補だけStage280本体へ反映する。

その後:

- Stage289 training report PASS確認
- model artifact hash作成
- Stage292 / 293 CI確認
- one-shot Stage292実行
- final signal判定は有効
- MT5 order / DiscordはOFFのまま

## B. exact_matches=[]

rankingが近くても近似採用しない。

次へ進む:

1. Stage301-B artifact recoveryをBATへ接続する変更をmainへ直接反映
2. ローカルclone / sibling clone / Git reachable / unreachable blobを検索
3. 元Stage280学習コード、feature list、model artifactを回収
4. 回収原本からparityを再現

## C. 原本も見つからない

- expected値を変更しない
- toleranceを緩めない
- 近似モデルをlive採用しない
- Stage280をBLOCKEDのまま維持
- Stage281は維持
- Stage292でStage280をどう扱うかは既存契約と安全条件で判断
- 勝手にfallbackしない

---

# 15. 情報源の区別

## GitHub main現物で確認済み

- Stage280/281 expected constants
- Stage292 priorities
- Stage292 DD / cooldown / loss gates
- Stage292 final signal / MT5 / Discord flags
- Stage293 Stage67 seed契約
- Stage292 bootstrap値
- Stage300 script
- Stage301-A feature diagnostic
- Stage301-B recovery script
- 現在のBAT

## ユーザー実行ログ由来

- Stage289履歴行数とcoverage
- 初回履歴不足時のfit/cal/positive数
- LONG-only修正後の75 positives
- pooled REVの245 positives
- Stage298結果
- Stage299結果
- Stage300 335モデル結果
- Stage281完全parity結果

## 過去チャット記録由来だが今回再実行していない

- Stage292 / Stage293 CIが過去にPASSしたこと

新しいチャットでは、この区別を崩さず、未確認事項を確認済みとして断言しない。

---

# 16. このチャットで発生した誤りと再発防止

発生した誤り:

1. future_validだけでthreshold / fixtureまで一致すると断言した
2. Stage280をLONG-onlyと誤解釈した
3. main反映確認前に「修正済み」と言った
4. Pullが出ない理由をローカルclone違いと推測した
5. 診断前に最終契約と表現した
6. GitHubへ残すべき引き継ぎをダウンロード文書として渡した
7. 引き継ぎ初版で、初回`positive_fit=0`と後段LONG-only`positive_fit=75`を混同した

再発防止:

「修正済み」「完了」「一致」と言う前に、必ず次を確認する。

- remote mainの実ファイル
- blob SHAまたはcommit
- ユーザー実行ログ
- exact parity
- その数値の情報源

---

# 17. 新チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab

GitHub mainの以下の引き継ぎ文書を最初から最後まで読んで、現在地点から続けてください。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_STAGE300_DONE_STAGE301_NEXT_COMPLETE_20260623.md

絶対禁止:
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない・使わない・参照しない・fallbackにしない
- CSV最新行はclosed、open/as-of禁止
- 時刻はMT5サーバー時刻
- resolved-onlyは exit_dt <= current entry_dt
- 2026を学習に使わない
- parity toleranceを緩めない
- 近似threshold・近似モデルを採用しない
- mainへ直接反映
- 私にブランチやPRの選択を求めない
- MT5 order / Discord / partial closeはOFF

現在地点:
- Stage300はユーザー環境で実行済み
- 335モデルを評価したが exact_matches=[]
- Stage301-A feature-contract diagnosticはGitHub mainに準備済みだが未実行
- 現在のBATはStage301-Aを実行する
- Stage301-B artifact recoveryは、Stage301-A不一致時の次工程

まず引き継ぎ文書を読んだうえで、
1. 現在地点
2. 次に実行するBAT
3. Stage301結果後の分岐
を簡潔に説明してください。
```

---

# 18. 現在地点の一文

**Stage300で335モデルを比較してハイパーパラメータだけでは完全parityを再現できないと確認済み。次はStage301-Aで特徴一覧・特徴順序・時間足構成・テスト母集団を比較し、exact matchがなければStage301-Bで元Stage280原本回収へ進む。**
