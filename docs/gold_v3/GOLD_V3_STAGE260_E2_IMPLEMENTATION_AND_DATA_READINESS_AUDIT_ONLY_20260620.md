# GOLD V3 Stage260 E2 実装・データ準備監査

作成日: 2026-06-20  
対象: 前MT5セッション高値・安値のスイープと回収  
契約: AUDIT ONLY

## 現在の状態

正式な完了状態は引き続き次のままです。

`GOLD_V3_259_NORMAL_LOWVOL_SPECIALIST_SEARCH_DONE_AUDIT_ONLY`

Stage260 E2の作業状態は次です。

`GOLD_V3_260_E2_DEFINITION_AND_RUNNER_READY_REAL_DATA_BLOCKED_AUDIT_ONLY`

Stage260は未完了です。この環境では実市場データによるE2母集団・matched control・プラセボの数値結果を算出していません。実運用関連の状態はすべてOFFのままです。

## 引き継ぎ確認

次の引き継ぎファイルを先頭から最終行まで確認しました。

`docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_STAGE259_DONE_STAGE260_EVENT_FIRST_NEXT_COMPLETE_20260620.md`

隔離対象は開いていません。CSV最新行をclosedとする契約、CSV timeをOPEN時刻とする契約、確定HTFだけを使う契約、同一M1のTP/SLはSL優先、1 setup 1 trade、MFE/MAEはホライズン終端まで測る契約、時刻結合、cost2主判定、2025年前半発見・後半選定・2026固定を維持しました。

## E2定義

コード実装前に次の文書へ固定しました。

`docs/gold_v3/GOLD_V3_STAGE260_E2_PRIOR_DAY_SWEEP_RECLAIM_EVENT_DEFINITION_AUDIT_ONLY_20260620.md`

基準イベントは、前の完了MT5セッション高値または安値を因果H1 ATR14の0.05倍以上抜き、15分以内に0.02 ATR以上レンジ内へ確定終値で回収するものです。単発ヒゲを除くため、外側終値または外側で取引したM1が2本以上必要です。安値側はLONG、高値側はSHORTの対称定義です。

## 追加ファイル

- `configs/gold_v3/stage260_e2_audit_config.example.json`
- `scripts/gold_v3/gold_v3_260_e2_prior_day_sweep_reclaim_audit.py`
- `scripts/gold_v3/stage260_e2_common.py`
- `scripts/gold_v3/stage260_e2_event.py`
- `scripts/gold_v3/stage260_e2_evaluation.py`
- `scripts/gold_v3/stage260_e2_runner.py`
- `tests/gold_v3/test_gold_v3_260_e2_prior_day_sweep_reclaim_audit.py`

実装は、CSV契約監査、時刻ベースsource parity、15分超ギャップによるMT5セッション再構築、前セッション高安、因果H1 ATR、外部のStage258互換レジーム時系列、E2検出、matched control、全指定プラセボ、MFE/MAE、到達値と到達時間、固定TP/SLとcost0/1/2/3/5、PF・損益・期待値・DD・連敗、月・四半期・期間・方向・レジーム・MT5時間帯別集計を含みます。

## テスト

次の11契約テストが成功しました。

- 最新CSV行を保持し、timeをOPEN時刻として扱う
- 単発ヒゲを基準イベントにしない
- 継続した突破と確定回収を検出する
- SL先着後もMFE/MAEをホライズン終端まで測る
- 同一M1のTP/SLをSL優先にする
- 15分超ギャップでセッションを分ける
- 確定済みHTFだけを結合する
- 別CSVを行番号でなく時刻で比較する
- 固定ホライズン中の重複setupを抑止する
- matched controlの固定層条件とpair identityを維持する
- 空のプラセボ母集団を安全に処理する

結果:

`Ran 11 tests ... OK`

合成データによる全工程テストも完走しました。ただし合成結果はソフトウェア確認専用であり、E2の市場成績として扱いません。

## 実データ準備監査

前チャットの`/mnt/data`成果物はこの環境へ引き継がれていませんでした。また、引き継ぎに記載された既知の候補パスでは、必要なCSVとStage258互換レジーム時系列を取得できませんでした。

そのため、現時点で不足している入力は次です。

- gold# の M1/M5/M15/H1/H4/D1
- goldsharp の M1/M5/M15/H1/H4/D1
- Stage258互換の因果HIGH/NORMAL/TRANSITION時系列
- 完全なlive parityに必要な、事前既知の祝日・短縮セッションカレンダー

この不足により、実データsource parity、実MT5セッションカレンダー、E2件数、matched control差、プラセボ差、合格・不採用判定は未実施です。数値を推測または捏造していません。

## 次に進む固定条件

必要入力が安定したパスへ揃った後、固定済みE2定義を変更せずに次の順序で実行します。

1. source parity
2. MT5セッションカレンダー監査
3. E2 raw母集団
4. dedup後母集団
5. matched control比較
6. 全プラセボ比較
7. 早期不採用判定
8. 母集団差が明確な場合だけ少数特徴量を追加

2026年の結果を見て定義・閾値・方向・候補を変更しません。

## 結論

実装結論:

`E2_DEFINITION_AND_AUDIT_RUNNER_PASS`

市場エッジ結論:

`NOT_EVALUATED_DATA_UNAVAILABLE`

運用結論:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
