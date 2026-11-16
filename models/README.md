# 하이링구얼 이탈 예측 모델 (프리즘팀)

사용자의 최근 N일(7·14·21·28일) 행동 로그로 **향후 7일간 앱에 접속하지 않을 확률(이탈 확률)** 을 예측하는 모델 코드입니다.
로지스틱 회귀(baseline)와 RandomForest, XGBoost, CatBoost를 **같은 데이터 분할·피처·평가 방식**으로 비교합니다.

> 현재 트리 모델(RandomForest, XGBoost, CatBoost)은 **하이퍼파라미터 튜닝 전 기본 설정**입니다.

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `common.py` | 모든 모델이 공통으로 쓰는 코드: 데이터 로드·시간순 분할, 피처 생성, 사용자 가중치, 임계값 선정, 평가 지표, 학습·평가 반복 실행 |
| `train_logistic_regression.py` | 로지스틱 회귀 (baseline) |
| `train_random_forest.py` | RandomForest |
| `train_xgboost.py` | XGBoost |
| `train_catboost.py` | CatBoost |
| `bootstrap_ci.py` | 사용자 단위 Bootstrap 신뢰구간과 모델·기간 간 차이 검정 (`train_*.py`가 저장한 예측 확률 사용) |

각 `train_*.py`는 **모델 설정만** 담은 짧은 파일이고, 나머지 모든 처리는 `common.py`가 맡습니다.
따라서 `train_*.py`를 실행하려면 `common.py`가 **같은 폴더**에 있어야 합니다.
`bootstrap_ci.py`는 `common.py` 없이 `train_*.py`의 결과 파일(`results_*_preds.npz`)만 읽습니다.

## 실행 방법

```bash
pip install pandas numpy scikit-learn xgboost catboost

python train_logistic_regression.py churn_features.csv results_logistic_regression.csv
python train_random_forest.py       churn_features.csv results_random_forest.csv
python train_xgboost.py             churn_features.csv results_xgboost.csv
python train_catboost.py            churn_features.csv results_catboost.csv
```

- 입력: `churn_features.csv` (전처리 완료 데이터, 553,373행 × 44열, 저장소에는 포함하지 않음)
- 출력: 결과 CSV와 같은 이름의 `_preds.npz` (Test 예측 확률)
- 모델 하나씩 독립적으로 실행할 수 있습니다.
- 신뢰구간은 `train_*.py` 4개를 모두 실행한 뒤 `python bootstrap_ci.py . bootstrap_out`으로 계산합니다.
- 실행 시간은 환경에 따라 다르며, 2코어 기준 로지스틱 회귀는 수 초, 트리 모델은 모델당 수 분입니다.

## 입력 데이터와 라벨

- 한 행은 **사용자 × 기준일**입니다.
- `churn_label = 1`: 기준일 이후 7일간 접속·학습·유입 활동이 없음 (이탈)
- Test 이탈 비율은 약 80.9%로 클래스가 불균형합니다.

## 데이터 분할 (시간순, 경계마다 7일 purge)

| 구간 | 기간 | 행 수 | 사용자 수 |
| --- | --- | --- | --- |
| Train | 2026-01-01 ~ 05-24 | 330,405 | 8,412 |
| Validation | 2026-06-08 ~ 07-08 | 49,560 | 2,826 |
| Test | 2026-07-23 ~ 10-12 | 95,150 | 3,120 |

라벨이 이후 7일을 보기 때문에 분할 경계마다 7일을 비워 미래 정보가 섞이지 않게 했습니다.

## 피처 (`common.py`의 `build_features`)

관찰 기간 N(7·14·21·28일)마다 7일 구간(block)별 값을 만듭니다. (예: 28일 버전은 1~7일, 8~14일, 15~21일, 22~28일 구간)

| 피처 | 내용 |
| --- | --- |
| `active_days`, `learning_days` | 구간별 활동일 수, 학습일 수 |
| `diary_count`, `vocabulary_count`, `pronunciation_count`, `social_count`, `session_count` | 구간별 기능 이용 횟수 (`log1p` 변환) |
| `learning_ratio` | 구간별 학습일 / 활동일 |
| `recency_log`, `recency_윈도우밖` | 마지막 활동 이후 경과일(`log1p`), 관찰 기간 밖이면 1인 지시변수 |

**제외한 컬럼**
- `event_count`: 앱 이벤트 기록 방식 변경에 민감함
- `app_usage_days`: `active_days`와 거의 동일함
- `entry_days`: 2026-08-10 이전에는 값이 없어 학습 구간(Train)에서 전부 0임

## 학습과 평가 방식

| 항목 | 내용 |
| --- | --- |
| 학습 가중치 | 사용자별 `1/√n` (n = 그 사용자의 Train 행 수). 행이 많은 사용자의 영향을 줄임 |
| 임계값 | Validation에서 F1이 최대가 되는 값을 선택(0.30~0.95), Test에는 그대로 적용 |
| 시드 | 트리 모델 5개(0~4), 로지스틱 회귀는 결정적이라 1개 |
| 표준화 | 로지스틱 회귀만 Train 기준으로 fit |

> **임계값 기준은 확정 전입니다.** F1 최대 기준은 이탈 비율(80.9%)이 높아 약 91%의 사용자를 위험으로 분류합니다. 균형 정확도 또는 상위 k% 방식으로 바꾸는 것을 검토 중이며, 바꿀 때는 `common.py`의 `best_threshold` 함수만 수정하면 됩니다.

## 모델 설정

| 모델 | 설정 |
| --- | --- |
| LogisticRegression | C=1.0, 표준화 후 학습 |
| RandomForest | 200그루, 최소 잎 50, max_features=sqrt, max_samples=0.5 |
| XGBoost | 300그루, 깊이 4, learning_rate 0.05, subsample·colsample_bytree 0.8, min_child_weight 20 |
| CatBoost | 400회, 깊이 6, learning_rate 0.05 |

## 결과 CSV 컬럼

한 행은 `버전 × 모델 × 시드`입니다.

| 컬럼 | 의미 |
| --- | --- |
| `버전`, `모델`, `시드` | 관찰 기간, 모델 종류, 시드 |
| `임계값` | Validation에서 정한 값 |
| `AUC`, `PR_AUC`, `Brier` | 확률 기준 지표 (임계값과 무관, Brier는 낮을수록 좋음) |
| `F1`, `Precision`, `Recall`, `Accuracy`, `BalancedAcc` | 임계값 기준 지표 (이탈을 양성으로 봄) |
| `Prec_top20`, `Prec_top10` | 이탈 확률 상위 20%·10%를 푸시 대상으로 했을 때 실제 이탈 비율 |

> 이탈 비율이 80.9%라 "전부 이탈"로 예측해도 F1이 0.895, 정확도가 0.809입니다. 모델 평가는 **PR-AUC·AUC**를 중심으로 보고, F1·Accuracy는 보조로 참고하세요. (PR-AUC의 무작위 기준은 이탈 비율 0.809)

## 신뢰구간과 차이 검정 (`bootstrap_ci.py`)

Test 성능이 사용자 구성에 따라 얼마나 흔들리는지 **사용자 단위 Bootstrap**으로 확인합니다.

**방법**
1. Test 사용자를 같은 수만큼 복원추출합니다. 한 사용자의 모든 행(날짜)을 통째로 뽑습니다. (같은 사용자의 행은 서로 비슷해 독립이 아니므로, 행 단위로 뽑으면 구간이 실제보다 좁게 나옵니다.)
2. 뽑힌 사용자의 행으로 AUC와 PR-AUC를 계산합니다. 모델을 다시 학습하지 않고 저장된 예측 확률만 씁니다.
3. 1000번 반복해 2.5%~97.5% 구간을 95% 신뢰구간으로 씁니다.
4. **차이 검정**: 같은 표본에서 두 모델(또는 두 기간)의 지표 차이를 구하고, 차이의 95% 구간이 **0을 포함하지 않으면 유의하다**고 봅니다. 같은 사용자 구성에 두 결과가 함께 흔들려 공통 변동이 상쇄되므로, 개별 구간이 겹쳐 보여도 차이는 유의할 수 있습니다.

**출력 (`bootstrap_out/`)**

| 파일 | 내용 |
| --- | --- |
| `bootstrap_ci.csv` | 모델 × 기간별 AUC·PR-AUC 95% 구간 |
| `bootstrap_reps.csv` | 반복 횟수 200·500·1000 비교 (로지스틱 회귀, 시드 5개). 구간 끝점이 시드마다 흔들리는 정도 |
| `bootstrap_diff_versions.csv` | 기간 간 차이 (예: 28일 − 14일), 모델별 |
| `bootstrap_diff_models.csv` | 모델 간 차이 (예: CatBoost − LR), 기간별 |

**참고**
- 구간 계산에는 `train_*.py`가 저장한 **시드 평균 예측 확률**을 쓰므로, 트리 모델의 점추정값이 결과 CSV의 시드 평균 지표와 0.0002 안팎으로 다를 수 있습니다.
- 유의함은 "차이가 우연이 아니다"만 뜻하고, 차이가 크다는 뜻은 아닙니다. (예: 28일 − 21일 AUC 차이는 유의하지만 0.004)
- 반복 횟수 비교에서는 1000회가 구간 끝점이 가장 안정적이었습니다.

## 현재 결과 요약 (Test, 28일 버전)

| 모델 | AUC | PR-AUC | F1 |
| --- | --- | --- | --- |
| LogisticRegression | 0.7917 | 0.9229 | 0.9206 |
| RandomForest | 0.7952 | 0.9242 | 0.9208 |
| XGBoost | 0.7965 | 0.9249 | 0.9215 |
| CatBoost | 0.7966 | 0.9253 | 0.9214 |

- 모든 모델에서 관찰 기간이 길수록 성능이 올라갑니다. (LR 기준 AUC 7일 0.758 → 28일 0.792)
- 트리 모델은 LR보다 AUC가 0.005 이내로 소폭 높습니다. (튜닝 전)

## 다음 단계

- [ ] 하이퍼파라미터 튜닝 (Validation 기준 탐색 후 Test 1회 평가)
- [ ] 임계값 기준 확정 (균형 정확도 / 상위 k%)
- [ ] 예측 확률 보정(calibration) 확인
