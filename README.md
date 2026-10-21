
# Prism | HiLingual

**Applied Data Science · Fall 2026**

사용자 행동 로그 기반 이탈 위험 예측 및 개인화 재참여 알림 시스템

---

## 01. Overview

HiLingual 사용자의 행동 로그를 분석하여 향후 7일간의 활동 미관측 위험을 예측하고, 개인별 이용 패턴에 맞는 재참여 알림을 제공하는 프로젝트입니다.

Amplitude 데이터를 기반으로 사용자별 활동 빈도, 최근 접속 시점, 기능 이용 패턴을 분석하고, 머신러닝을 활용해 이탈 위험도를 산출합니다.

> 이탈 여부는 향후 7일간의 활동 관측 여부를 기반으로 정의한 대리 라벨(Proxy Label)이며, 실제 서비스 탈퇴 여부와는 다릅니다.

## 02. Key Features

| 기능 | 설명 |
|:---|:---|
| Data Preprocessing | Amplitude 행동 로그 정제 및 사용자 단위 집계 |
| Feature Engineering | 7·14·21·28일 관찰 기간별 Feature 생성 |
| Churn Prediction | 머신러닝 기반 향후 7일 이탈 위험 예측 |
| Model Evaluation | 모델별·관찰 기간별 성능 비교 |
| Personalization | 사용자별 이용 요일·시간대 및 선호 기능 분석 |
| Notification | 개인화 알림 문구·발송 시점·이동 화면 결정 |
| Dashboard | 예측 및 평가 결과 시각화 |

## 03. Tech Stack

| 분야 | 기술 |
|:---|:---|
| Language | Python, Swift |
| Data | Amplitude, pandas, NumPy |
| Machine Learning | scikit-learn, XGBoost, CatBoost |
| Dashboard | Streamlit |
| iOS | SwiftUI, UserNotifications, Deep Link |
| Collaboration | Git, GitHub |

일부 기능과 기술은 구현 및 검증 예정입니다.

## 04. Project Structure

```text
AppliedDataScience-Prism/
├── pipeline/             # 데이터 전처리
├── src/prism/
│   ├── load_data.py      # 데이터 로드
│   ├── split.py          # 데이터 분할
│   ├── train.py          # 모델 학습
│   ├── predict.py        # 이탈 위험 예측
│   ├── evaluate.py       # 성능 평가
│   ├── personalize.py    # 개인화 분석
│   ├── export_ios.py     # iOS 연동 데이터 생성
│   └── legacy.py         # 기존 전처리 함수 재사용
├── configs/              # 실행 설정
├── dashboard/            # Streamlit 대시보드
├── requirements/         # 추가 의존성
├── tests/                # 테스트
├── docs/                 # 프로젝트 문서
├── data/                 # 원본 데이터 (Git 제외)
├── outputs/              # 전처리 결과 (Git 제외)
├── models/               # 학습 모델 (Git 제외)
├── results/              # 평가 결과 (Git 제외)
└── README.md
```

## 05. Getting Started

### Installation

```bash
git clone https://github.com/jjwm10625/applied-data-science-prism.git
cd applied-data-science-prism

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m pip install -e .
```

모델링 및 대시보드 실행에 필요한 추가 의존성은 다음과 같이 설치합니다.

```bash
python -m pip install -r requirements/modeling.txt
python -m pip install -r requirements/dashboard.txt
```

### Run

```bash
# 데이터 전처리
python pipeline/run.py

# 모델 학습
python -m prism.train --output models/experiment_001

# 모델 평가
python -m prism.evaluate \
  --predictions models/experiment_001 \
  --output results/evaluation

# 대시보드
streamlit run dashboard/app.py
```

모델 학습 전 시간 분할 설정과 모델링 데이터 준비가 필요합니다.

## 06. Documentation

| 문서 | 설명 |
|:---|:---|
| [Preprocessing](pipeline/README.md) | 데이터 전처리 |
| [Data Contracts](docs/data_contracts.md) | 모듈 입출력 형식 |
| [Validation](docs/VALIDATION.md) | 검증 기록 |
| [iOS Interface](docs/ios/interface.md) | iOS 연동 |

## 07. Team Members

**Team Prism — 프리즘**

| 이름 | 역할 | 담당 업무 |
|:---|:---|:---|
| 이다은 | Modeling | 모델 학습 및 최적화 |
| 조영서 | Data & iOS | 데이터 수집·전처리·Feature 생성 및 iOS 구현 |
| 박주현 | Evaluation | 모델 평가 및 결과 시각화 |
| 진하연 | Writing | 보고서 및 발표 자료 제작 |

---

**Applied Data Science · Fall 2026 | Team Prism**
