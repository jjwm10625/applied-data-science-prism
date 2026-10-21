# Prism | HiLingual

**Applied Data Science · Fall 2026**

사용자 행동 로그 기반 이탈 위험 예측 및 개인화 재참여 알림 시스템

---

## 01. Project Overview

Prism(프리즘)은 HiLingual 사용자의 행동 데이터를 분석하여 향후 7일간의 활동 미관측 위험을 예측하고, 사용자별 이용 패턴을 반영한 개인화 재참여 알림을 제공하는 프로젝트입니다.

Amplitude 행동 로그를 활용해 사용자별 활동 빈도, 최근 접속 시점, 기능 이용 패턴 등을 분석하고, 머신러닝 모델을 통해 이탈 위험도를 산출합니다.

예측 결과는 사용자별 주 이용 요일·시간대 및 선호 기능과 결합하여 재참여 알림의 대상, 시점, 내용을 결정하는 데 활용합니다.

> **데이터 해석 시 유의사항**
>
> 본 프로젝트의 이탈 라벨은 향후 7일간 활동이 관측되지 않은 상태를 나타내는 대리 라벨(Proxy Label)입니다. 데이터 수집이 안정적이라는 가정하에 생성되며, 실제 미접속이나 서비스 탈퇴가 확인되었음을 의미하지 않습니다.

## 02. Key Features

| 기능                      | 설명                                                |
| :------------------------ | :-------------------------------------------------- |
| **Data Preprocessing**    | Amplitude 행동 로그 정제 및 사용자 단위 데이터 집계 |
| **Feature Engineering**   | 7·14·21·28일 관찰 기간별 행동 Feature 생성          |
| **Churn Prediction**      | 머신러닝 기반 향후 7일 활동 미관측 위험 예측        |
| **Model Evaluation**      | 모델별·관찰 기간별 성능 비교 및 확률 신뢰성 평가    |
| **User Personalization**  | 주 이용 요일·시간대 및 선호 기능 분석               |
| **Notification Strategy** | 사용자별 알림 문구·발송 시점·이동 화면 결정         |
| **Dashboard**             | Streamlit 기반 예측 및 평가 결과 시각화             |

## 03. Tech Stack

| 분야             | 기술                                  |
| :--------------- | :------------------------------------ |
| Language         | Python, Swift                         |
| Data Analytics   | Amplitude, pandas, NumPy              |
| Machine Learning | scikit-learn, XGBoost, CatBoost       |
| Visualization    | Matplotlib, Streamlit                 |
| iOS Integration  | SwiftUI, UserNotifications, Deep Link |
| Collaboration    | Git, GitHub                           |

일부 기술은 도입 예정이며, 실제 모델 학습·대시보드 실행·iOS 연동 검증은 아직 완료되지 않았습니다.

## 04. Project Structure

```text
AppliedDataScience-Prism/
│
├── pipeline/                 # 기존 데이터 전처리 파이프라인
│
├── src/
│   └── prism/
│       ├── load_data.py      # 모델링 데이터 로드 및 검증
│       ├── split.py          # 시간 기준 데이터 분할
│       ├── train.py          # 모델 학습 및 저장
│       ├── predict.py        # 이탈 위험도 예측
│       ├── evaluate.py       # 모델 성능 평가
│       ├── personalize.py    # 사용자 이용 패턴 및 알림 개인화
│       ├── export_ios.py     # iOS 테스트용 JSON 생성
│       └── legacy.py         # 기존 전처리 함수 재사용
│
├── configs/                  # 모델·데이터 분할·개인화 설정
├── dashboard/
│   └── app.py                # Streamlit 대시보드
├── requirements/             # 기능별 추가 의존성
├── tests/                    # 모듈 단위 테스트
├── docs/                     # 데이터 계약 및 연동 문서
│
├── data/                     # 원본 데이터 (Git 제외)
├── outputs/                  # 전처리 결과 (Git 제외)
├── models/                   # 학습 모델 및 실험 기록 (Git 제외)
├── results/                  # 예측·평가 결과 (Git 제외)
│
├── requirements.txt
└── README.md
```

기존 전처리 파이프라인은 `pipeline/`에 보존하며, 신규 모델링 모듈은 `src/prism/`에서 관리합니다.

## 05. Getting Started

### 5.1. 환경 설정

Python 가상환경을 생성하고 기본 의존성을 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m pip install -e .
```

필요한 기능에 따라 추가 패키지를 설치합니다.

```bash
# 모델 학습 및 평가
python -m pip install -r requirements/modeling.txt

# Streamlit 대시보드
python -m pip install -r requirements/dashboard.txt
```

### 5.2. 데이터 전처리

Amplitude 행동 로그를 정제하고 모델링 데이터를 생성합니다.

```bash
# 기존 전처리 파이프라인 실행
python pipeline/run.py

# 모델링 CSV 생성
python pipeline/export_modeling_csv.py outputs/<새_실행_ID>

# 정제 데이터 및 Feature 재생성
python pipeline/rebuild_features.py outputs/final
```

### 5.3. 모델 학습

학습 전 `configs/split.example.json`의 시간 분할 기준을 설정해야 합니다. 날짜가 지정되지 않으면 학습이 중단됩니다.

```bash
python -m prism.train \
  --output models/experiment_001
```

### 5.4. 모델 평가 및 예측

```bash
# 모델 성능 평가
python -m prism.evaluate \
  --predictions models/experiment_001 \
  --output results/evaluation

# 사용자별 이탈 위험도 예측
python -m prism.predict \
  --model models/experiment_001/logistic_regression_w7_seed11.joblib \
  --features outputs/final/handoff/modeling_dataset.csv \
  --output results/predictions.csv
```

### 5.5. 개인화 분석

```bash
python -m prism.personalize \
  --events outputs/final/data/events_clean.csv.gz \
  --reference-date YYYY-MM-DD \
  --output results/personalization.csv
```

### 5.6. 대시보드

```bash
streamlit run dashboard/app.py
```

> **실행 관련 안내**
>
> - 기존 결과를 보호하기 위해 새로운 출력 폴더를 사용합니다.
> - 최신 사용자 예측에는 학습 시점과 동일한 컬럼 구조의 Feature가 필요합니다.
> - 위 명령어는 프로젝트에 구성된 실행 인터페이스를 기준으로 작성되었으며, 실제 데이터 기반 모델 학습 및 전체 기능 검증은 아직 수행되지 않았습니다.

## 06. Dataset & Modeling

### Dataset Summary

현재 생성된 모델링 데이터의 구성은 다음과 같습니다.

| 항목           |                 값 |
| :------------- | -----------------: |
| 사용자 키      |            6,467개 |
| 모델링 데이터  |   35,807행 × 216열 |
| 관찰 기간      | 7 / 14 / 21 / 28일 |
| 예측 대상 기간 |           향후 7일 |
| Feature 후보   |   관찰 기간별 30개 |
| 기준일 간격    |    7일 (임시 설정) |

각 행은 하나의 사용자 키와 기준일에 대응하며, 네 가지 관찰 기간의 Feature를 함께 포함합니다.

사용자 키 수는 실제 사람 수와 일치하지 않을 수 있습니다.

### Target Distribution

**Target:** `label_proxy_churn_7d`

| Label  | 정의                     | 데이터 수 |
| :----- | :----------------------- | --------: |
| `0`    | 향후 7일 내 활동 관측    |     7,967 |
| `1`    | 향후 7일 활동 미관측     |    27,840 |
| 미확정 | 관측 부족 또는 판정 불가 |     1,464 |

미확정 라벨은 전체 데이터에 보존하며, 확정 라벨을 사용하는 모델링 데이터와 구분합니다.

### Feature Engineering

사용자별 행동 로그에서 다음 특성을 생성합니다.

- **Recency:** 기준일 시점의 최근 접속 이후 경과일
- **Frequency:** 관찰 기간 내 활동일 수 및 세션 수
- **Feature Usage:** 일기 작성, 단어장 복습, 발음 듣기 등 기능별 이용 횟수
- **Engagement Trend:** 이전 기간 대비 활동량 변화
- **Observation Window:** 7·14·21·28일 관찰 기간별 특성

모델 입력에는 `feature_roles.json`에 정의된 해당 관찰 기간의 후보 Feature 30개만 사용합니다.

사용자 식별자, 기준일, 정답 라벨 및 품질 관련 정보는 기본 모델 입력에서 제외합니다.

### Data Split & Validation

데이터 누수를 방지하고 평가 조건을 일관되게 유지하기 위해 다음 원칙을 적용합니다.

1. 시간 기준으로 Train / Validation / Test를 분리합니다.
2. 모든 관찰 기간에 동일한 시간 분할을 적용합니다.
3. 이전 구간의 라벨 관측 기간이 다음 구간을 침범하는 경우 해당 행을 제외합니다.
4. 결측치 처리 및 스케일링 등 학습이 필요한 변환은 Train 데이터에만 `fit`합니다.
5. 모델과 분류 임계값은 Validation 데이터로 선택합니다.
6. Test 데이터는 최종 성능 보고에만 사용합니다.

**데이터 가용성 관련 제한**

현재 Feature는 `retrospective_snapshot` 기준으로 생성됩니다. 따라서 기준일 이후 업로드된 과거 행동이 포함될 수 있으며, 이는 당시 실제로 이용 가능한 데이터만 사용한 검증과는 다릅니다.

또한 기능별 이벤트가 관측되지 않은 경우를 모두 실제 미사용 횟수 `0`으로 해석하지 않습니다.

### Evaluation Metrics

| 지표        | 평가 목적                        |
| :---------- | :------------------------------- |
| F1-score    | Precision과 Recall의 균형        |
| Precision   | 이탈 위험 분류의 정밀도          |
| Recall      | 실제 이탈 위험 사용자 탐지율     |
| AP (PR-AUC) | 클래스 불균형을 고려한 분류 성능 |
| Brier Score | 예측 확률의 정확도               |

Logistic Regression을 기준 모델로 사용하며, RandomForest·XGBoost·CatBoost와 성능을 비교할 계획입니다.

동일한 Test set에서 관찰 기간별·시드별 평가 결과를 비교하고 평균과 표준편차를 보고합니다.

## 07. Documentation & Tests

### Documentation

| 문서                                     | 내용                          |
| :--------------------------------------- | :---------------------------- |
| [Preprocessing](pipeline/README.md)      | 기존 데이터 전처리 파이프라인 |
| [Data Contracts](docs/data_contracts.md) | 모듈 간 입력·출력 데이터 형식 |
| [Validation](docs/VALIDATION.md)         | 데이터 및 기능 검증 기록      |
| [iOS Interface](docs/ios/interface.md)   | Dev 앱 연동 계약 및 예제      |

### Unit Tests

```bash
# 기존 전처리 테스트
python -B -m unittest discover \
  -s pipeline -p 'test_*.py' -v

# 신규 협업 모듈 테스트
python -B -m unittest discover \
  -s tests -v
```

### Current Limitations

현재 추가 검증이 필요한 항목은 다음과 같습니다.

- 실제 데이터 기반 모델 학습 및 성능 평가
- XGBoost 및 CatBoost 실행 검증
- Streamlit 대시보드 실행 검증
- iOS Dev 앱 실기기 알림 및 딥링크 검증

기존 Xcode 프로젝트는 변경하지 않았습니다.

## 08. Team Members

**Team Prism — 프리즘**

| 이름   | 역할       | 담당 업무                                     |
| :----- | :--------- | :-------------------------------------------- |
| 이다은 | Modeling   | 모델 학습, 하이퍼파라미터 튜닝, Baseline 구현 |
| 조영서 | Data       | 데이터 수집, 전처리, Feature 생성             |
| 박주현 | Evaluation | 성능 평가, 오류 분석, 결과 시각화             |
| 진하연 | Writing    | 보고서 작성, 발표 자료 제작, 일정 관리        |

개인화 분석, 대시보드 및 iOS 연동의 세부 담당은 팀 협의 후 확정합니다.

## 09. Collaboration

**Repository:** [AppliedDataScience-Prism](https://github.com/jjwm10625/applied-data-science-prism)

GitHub 기반 협업을 진행하며, 담당 기능별 Feature Branch와 Pull Request를 사용합니다.

### Collaboration Rules

- 기능별 브랜치에서 개발한 후 Pull Request를 생성합니다.
- 코드 변경 시 관련 테스트와 문서를 함께 수정합니다.
- 데이터 컬럼이나 입출력 형식을 변경할 경우 데이터 계약 문서를 함께 갱신합니다.
- 원본 데이터, 개인정보, 비밀키, 모델 파일 및 실험 결과는 Git에 업로드하지 않습니다.
- 기존 전처리 결과를 덮어쓰지 않도록 출력 경로를 분리합니다.

모델링에 필요한 데이터는 GitHub가 아닌 별도 경로로 전달하며, 팀원은 제공받은 `outputs/final/handoff/` 데이터를 사용합니다.

---

**Applied Data Science · Fall 2026 | Team Prism**
