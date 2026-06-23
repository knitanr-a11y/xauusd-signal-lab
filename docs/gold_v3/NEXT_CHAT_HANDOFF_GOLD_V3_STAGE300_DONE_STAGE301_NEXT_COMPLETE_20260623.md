# NEXT CHAT HANDOFF — GOLD V3 Stage300 done / Stage301 next

Date: 2026-06-23  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch policy: **main direct only**  
Current state: `GOLD_V3_STAGE300_DONE_STAGE301_FEATURE_CONTRACT_DIAGNOSTIC_NEXT_AUDIT_ONLY`

---

## 0. この文書の目的

この文書は、このチャットで実施した作業、途中で判明した誤り、GitHub mainへ反映した内容、ユーザー環境での実行結果、現在地、次に実行するStage301、その後の分岐までを完全に引き継ぐためのもの。

新しいチャットではこの文書を最初から最後まで読み、同じ調査を最初からやり直さず、**Stage301実行結果の解析から再開すること**。

---

# 1. 絶対禁止事項・不変契約

以下は必ず維持する。

- GOLD V3は `audit-only`
- GOLD V2 / 旧GOLD / DISC8 / Stage41は読まない・使わない・参照しない・fallbackにしない
- CSV最新行はCSV契約上 `closed`
- `open` / `as-of` 禁止
- candidate / entry / gate はentry時点で知り得るclosed情報だけ
- health / rolling / cooldown判断は `exit_dt <= current entry_dt` のresolved-only
- 時刻基準はJSTではなく **MT5サーバー時刻**
- Stage280 / 281 / 284の既存契約は、明示変更しない限り維持
- 2026データを学習へ使わない
- parity toleranceを緩めない
- 近似モデルや近似thresholdを正式採用しない
- `expected`値を書き換えてPASS扱いしない
- ユーザーにブランチ選択やPR判断を求めない
- production変更は **mainへ直接反映**
- ユーザー操作は原則 `GitHub Desktop → main → Fetch origin → Pull origin`
- MT5自動注文OFF
- Discord通知OFF
- partial close OFF

---

# 2. Stage292 / 293の維持事項

## Stage292 safe portfolio

組み合わせ:

- BASE priority 0
- Stage280 priority 10
- Stage281 priority 20
- Stage286 priority 60

主要契約:

- pending/open最大1
- additionはDD <= 30
- shared cooldown 12h
- Stage281は直近resolved BASE loss後72h以内
- Stage286はDD <= 10
- Stage286は直近resolved addition loss後24h
- BASE overlapでMT5 server hour 00/01は拒否
- MT5 order / DiscordはOFF

## Stage293 resolved-only BASE health

- 初期seedはStage67のみ
- bootstrap後は実際のStage292 BASE closeだけ
- bootstrap as-of: `2026-06-19 15:51`
- equity: `965.6008808154019`
- peak: `985.2064859116765`
- DD: `19.605605096274644`
- last BASE pnl: `-19.605605096274644`

Stage292 / 293のCIはこれまで繰り返しPASS。

---

# 3. Stage289履歴回収で完了したこと

履歴エクスポーター:

`scripts/gold_v3_runtime/mt5/ExportGoldStage289TrainingHistory_v110.mq5`

インストーラー:

`scripts/gold_v3_runtime/bat/install_gold_v3_289_training_m1_exporter.bat`

取得済み履歴:

- M1 rows `902109`, first `2023-12-01 01:00:00`
- M5 rows `180597`
- M15 rows `60203`
- H1 rows `20002`前後
- H4 rows `10000`
- D1 rows `5000`

preflight:

`scripts/gold_v3_runtime/gold_v3_289_training_history_preflight.py`

ユーザー実行結果:

- `status = PASS`
- blockers `[]`
- H1 decisions `11822`
- valid M1 240m windows `10271`
- coverage ratio `0.8688039248858062`

履歴不足は現在の阻害要因ではない。

---

# 4. parity固定値

## Stage280 expected

- threshold `0.5927349103795366`
- fixture score `0.5949591748604749`
- fixture time `2026-06-19 08:00:00`
- fit_n `4974`
- cal_n `1809`
- positive_fit `245`
- test_n `1606`
- test positives `65`
- 2026 ROC-AUC `0.6904307891978236`
- 2026 PR-AUC `0.08009367826075599`

期待bucket:

- q90: n `120`, hits `10`
- q95: n `64`, hits `8`
- q97.5: n `25`, hits `3`
- q99: n `11`, hits `1`

## Stage281 expected

- threshold `0.5525199124029727`
- fixture score `0.6586538142862226`
- fixture time `2026-06-17 10:00:00`

Stage281はユーザー環境で完全一致済み:

- fit_n `16041`
- cal_n `6371`
- positive_fit `2515`
- parity `true`

Stage281は変更しない。

---

# 5. このチャットでのStage280調査の時系列

## 5.1 最初の問題

Stage280ローカル学習が元監査と一致しなかった。

初期状態:

- LONG-onlyで学習
- fit_n `1714`
- cal_n `492`
- positive_fit `75`
- threshold / fixtureとも不一致

この時点では母集団自体が違っていた。

## 5.2 Stage295 population diagnostic

追加:

`scripts/gold_v3_runtime/gold_v3_295_stage280_population_diagnostic.py`

診断結果:

元監査の母集団 `fit_n=4974 / cal_n=1809` に完全一致した条件は、

- H4 trend非中立
- 未来240分のM1判定窓が完全に有効

つまり:

`h4_non_neutral AND future_valid`

時間帯除外、D1条件、全特徴finite条件ではなかった。

未来240分が不足する行を陰性として残すのではなく、学習母集団から除外する必要があると確定。

## 5.3 誤ったLONG-only解釈

一度、Stage280を `REV_LONG` の名前どおりLONGだけ陽性と解釈した。

結果:

- fit_n `4974`
- cal_n `1809`
- positive_fit `75`
- threshold `0.21033218812350174`
- fixture `0.5560333414497304`

positive_fit 75 / 4974 = 約1.5%で、元Stage280 REVの約4.9%と整合しなかった。この解釈は誤り。

Stage296文書はsuperseded扱いへ更新。

## 5.4 pooled REVへ修正

正しい母集団・教師候補:

- H4非中立の両方向
- predicted REV direction = `-h4_trend`
- LONG / SHORT両方のREV onsetを陽性
- 特徴をpredicted REV directionへ正規化
- future_valid行だけ学習

結果:

- fit_n `4974`
- cal_n `1809`
- positive_fit `245`
- fit base rate `0.049256131885806194`
- Stage281 parity `true`

母集団と陽性数は完全一致したがStage280は不一致:

- threshold `0.601208947025034`
- fixture `0.671670783296924`

---

# 6. Stage298 model variant diagnostic

追加:

`scripts/gold_v3_runtime/gold_v3_298_stage280_model_variant_diagnostic.py`

比較:

- direction normalizationあり / なし
- wick swapあり / なし
- relative align / raw align
- volume/spread有無
- engineered features有無
- global onset / filtered onset

最良候補:

`normalized_no_wick_swap_global_onset`

主結果:

- threshold `0.5935126932083092`
- fixture `0.6280999852097368`
- ROC-AUC 約 `0.68749`
- test_nが1602で元監査1606より4件少なかった

完全一致せず。

---

# 7. Stage299 wick / weight diagnostic

追加:

`scripts/gold_v3_runtime/gold_v3_299_stage280_wick_weight_diagnostic.py`

比較した特徴フレーム:

1. normalized no-swap raw reject
2. normalized no-swap directional reject
3. directional reject + raw wick列除外
4. 全wick swap
5. raw align
6. volume/spread除外

比較した重み:

- scale_pos_weight
- balanced
- none
- scale_pos_weight + bagging

test_nを1606へ修正。

Stage299 1位:

- frame `normalized_no_swap_directional_reject`
- weight `scale_pos`
- threshold `0.6034414845184862`
- fixture `0.6177927062319107`
- ROC-AUC `0.6927569510307992`
- PR-AUC `0.08063170773927932`

完全一致せず。単純なwick解釈や重み方式だけでは元モデルを再現できないと判明。

---

# 8. Stage300 hyperparameter diagnostic

追加:

`scripts/gold_v3_runtime/gold_v3_300_stage280_hyperparameter_diagnostic.py`

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

評価モデル数 `335`

結果:

`exact_matches = []`

Stage300 1位:

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

結果:

- threshold `0.5926760775274067`
- fixture `0.6102252160407501`
- ROC-AUC `0.6901013328008786`
- PR-AUC `0.08101204299523959`

bucket:

- q90 `109 / 8`
- q95 `62 / 7`
- q97.5 `22 / 2`
- q99 `12 / 1`

元監査bucket:

- q90 `120 / 10`
- q95 `64 / 8`
- q97.5 `25 / 3`
- q99 `11 / 1`

重要結論:

**335通りのモデル設定でも完全一致しないため、残差はLightGBMハイパーパラメータではない。**

候補順位そのものが異なるため、特徴一覧・特徴順序・特徴構築・テスト母集団・元学習コードのどれかが違う。同じハイパーパラメータ探索を続けない。

---

# 9. 現在remote mainにあるStage301

## 9.1 Stage301 feature-contract diagnostic

`scripts/gold_v3_runtime/gold_v3_301_stage280_feature_contract_diagnostic.py`

現在の次ステップ。

比較内容:

- 全特徴current order
- sorted order
- reversed order
- timeframe grouped order
- raw wick除外
- volume除外
- spread除外
- volume+spread除外
- engineered除外
- engineered only
- M1 / M5 / M15 / H1 / H4 / D1各drop
- LTF only
- HTF only
- 複数時間足組合せ
- 各variantのsorted / timeframe grouped

モデル設定:

- Stage300 rank1
- Stage300 rank2
- Stage300 scalar best
- Stage300 near-fixture

テスト母集団:

1. `future_valid_first1606`
2. `all_non_neutral_first1606`
3. `all_non_neutral_through_fixture_plus4h`

出力:

`stage301_stage280_feature_contract_diagnostic.json`

status:

`GOLD_V3_301_STAGE280_FEATURE_CONTRACT_DIAGNOSTIC_READY`

モデル・thresholdは保存しない。

## 9.2 Stage301 artifact recovery diagnostic

追加済み:

`scripts/gold_v3_runtime/gold_v3_301_stage280_artifact_recovery.py`

目的:

- ローカルclone
- sibling clone
- GOLD V3 output
- reachable Git blobs
- unreachable Git blobs
- Stage280関連モデル / source / exact scalar token

を検索する。

ただし、既存BATは現在feature-contract diagnosticを実行する。artifact recoveryはStage301 feature-contractが不一致だった場合の次の分岐。

---

# 10. 現在のBAT状態

現在remote main上:

`scripts/gold_v3_runtime/bat/run_gold_v3_295_stage280_population_diagnostic.bat`

はStage301 feature-contract diagnosticを実行する。

期待ログ:

`[INFO] Running Stage280 feature-contract diagnostic...`

実行対象:

`gold_v3_301_stage280_feature_contract_diagnostic.py`

出力:

`stage301_stage280_feature_contract_diagnostic.json`

---

# 11. 新しいチャットで最初に行うこと

ユーザー側:

1. GitHub Desktopでmainを確認
2. 更新がある場合のみ `Fetch origin → Pull origin`
3. 次を実行

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

ファイル添付できない場合は次だけコピペでよい:

- `status`
- `search`
- `exact_matches`
- `ranking`先頭10件

---

# 12. Stage301結果後の分岐

## A. exact_matchesが1件以上

以下をすべて確認:

- fit_n = 4974
- cal_n = 1809
- positive_fit = 245
- test_n = 1606
- positive_test = 65
- threshold完全一致
- fixture完全一致
- ROC-AUC完全一致
- PR-AUC完全一致
- q90/q95/q97.5/q99 bucket完全一致

すべて一致した候補だけStage280本体へ反映。

反映後:

- Stage289 training report PASS
- model artifact hash作成
- Stage292 / 293 CI
- one-shot Stage292実行
- MT5 order / DiscordはOFFのまま

## B. exact_matches = [] だがranking上位が近い

近いだけでは採用しない。

次へ移行:

1. `gold_v3_301_stage280_artifact_recovery.py`を実行可能なBATへ切替
2. ローカル旧clone / sibling clone / Git unreachable blobを検索
3. 元Stage280学習コード、feature list、model artifactを回収
4. 回収原本から再現

## C. exact_matches = [] かつfeature variantでも大きく不一致

元学習コードまたは保存モデルがない限り、完全parity再現は不可能と判断。

この場合:

- expected値を変更しない
- toleranceを緩めない
- 近似モデルをlive採用しない
- Stage280をBLOCKEDのまま維持
- Stage281は維持
- Stage292はStage280なしで動かすかどうかを既存契約に基づいて判断
- 勝手にfallbackしない

---

# 13. 現在の重要ファイル

## Stage280 / 289

- `scripts/gold_v3_runtime/gold_v3_289_stage280_features.py`
- `scripts/gold_v3_runtime/gold_v3_289_train_live_models_audit.py`
- `scripts/gold_v3_runtime/gold_v3_289_training_history_preflight.py`

## 診断

- `scripts/gold_v3_runtime/gold_v3_295_stage280_population_diagnostic.py`
- `scripts/gold_v3_runtime/gold_v3_298_stage280_model_variant_diagnostic.py`
- `scripts/gold_v3_runtime/gold_v3_299_stage280_wick_weight_diagnostic.py`
- `scripts/gold_v3_runtime/gold_v3_300_stage280_hyperparameter_diagnostic.py`
- `scripts/gold_v3_runtime/gold_v3_301_stage280_feature_contract_diagnostic.py`
- `scripts/gold_v3_runtime/gold_v3_301_stage280_artifact_recovery.py`

## BAT

- `scripts/gold_v3_runtime/bat/run_gold_v3_295_stage280_population_diagnostic.bat`
- `scripts/gold_v3_runtime/bat/run_gold_v3_292_safe_portfolio_live.bat`
- `scripts/gold_v3_runtime/bat/run_gold_v3_292_safe_portfolio_live_continuous.bat`

## exporter

- `scripts/gold_v3_runtime/mt5/ExportGoldStage289TrainingHistory_v110.mq5`
- `scripts/gold_v3_runtime/bat/install_gold_v3_289_training_m1_exporter.bat`

## CI

- `.github/workflows/stage294-ci.yml`
- `.github/workflows/stage297-ci.yml`

---

# 14. このチャットで発生した誤り

以下の誤った断言があった。新しいチャットでは繰り返さない。

1. future_validだけでthreshold/fixtureまで一致すると断言した
2. Stage280をLONG-onlyと解釈した
3. main反映確認前に「修正済み」と言った
4. GitHub DesktopでPullが出ない原因をローカルclone違いと推測した
5. 診断結果前に最終契約と表現した
6. GitHubへ残すべき引き継ぎをローカルダウンロード文書として渡した

必ず次を確認してから「修正済み」「完了」と言う:

- remote mainの実ファイル
- commit
- ユーザー実行ログ
- exact parity

---

# 15. 新チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab

GitHub mainの以下の文書を最初から最後まで読んで、現在地点から続けてください。

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

このチャットではStage295〜300まで実施済みです。

確定:
- Stage280 fit_n=4974
- cal_n=1809
- positive_fit=245
- test_n=1606
- positive_test=65
- Stage281 parity=true
- Stage300で335モデル探索したが exact_matches=[]

現在remote mainにはStage301 feature-contract diagnosticがあります。
次は以下の実行結果を解析する段階です。

scripts\gold_v3_runtime\bat\
run_gold_v3_295_stage280_population_diagnostic.bat

期待ログ:
[INFO] Running Stage280 feature-contract diagnostic...

出力:
stage301_stage280_feature_contract_diagnostic.json

まず引き継ぎ内容を理解したこと、現在地点、次にすることを簡潔に説明してください。
```

---

# 16. 現在地点

**Stage300でハイパーパラメータ原因を否定済み。次はStage301で特徴量契約・特徴順序・テスト母集団を比較し、exact matchがなければ元Stage280原本回収へ移る。**
