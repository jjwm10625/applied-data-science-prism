<p align="center">
  <img src="assets/images/hilingual-branding.svg" width="100%" alt="하이링구얼 브랜드 배너" />
</p>

<br>

<div align="center">

# 📊 하이링구얼 Hilingual Data

**사용자의 오늘을 읽고, 내일의 학습을 이어갑니다.**

사용자 행동 분석 · 이탈 예측 데이터 · 개인화 알림

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/pandas-150458?style=flat-square&amp;logo=pandas&amp;logoColor=white" alt="pandas" />
  <img src="https://img.shields.io/badge/NumPy-013243?style=flat-square&amp;logo=numpy&amp;logoColor=white" alt="NumPy" />
  <img src="https://img.shields.io/badge/Amplitude-FF6B3B?style=flat-square" alt="Amplitude" />
  <img src="https://img.shields.io/badge/Parquet-242424?style=flat-square" alt="Parquet" />
</p>

데이터사이언스응용 프로젝트 · **PRISM**

[🚀 빠른 시작](#quick-start) &nbsp;·&nbsp; [🗂️ 데이터](#data) &nbsp;·&nbsp; [🔎 분석 기준](#criteria) &nbsp;·&nbsp; [📂 프로젝트 구조](#structure)

</div>

<br>

---

## 📌 프로젝트 소개

HiLingual은 영어 일기로 꾸준한 학습 루틴을 만드는 서비스입니다. 이 저장소는 HiLingual의 Amplitude 이벤트 로그를 정제하고, 사용자별 행동을 분석용 데이터로 변환하는 프로젝트입니다. 모든 이벤트를 한국 시간(KST)으로 맞춘 뒤, 유입·앱 이용·학습 활동을 집계합니다.

두 가지 분석을 위한 데이터셋을 생성합니다.

| 분석 목적 | 생성하는 데이터 |
| :--- | :--- |
| **📉 사용자 이탈 예측** | 최근 7·14·21·28일의 활동량, 행동 그룹별 활동일, 최근 활동 이후 경과일, 이탈 라벨 |
| **🔔 개인화 알림** | 최근 28일의 기능 선호도, 선호 요일·시간, 요일별 선호 시간 |

현재 구현 범위는 **데이터 전처리·피처 생성·검증**입니다. 모델 학습과 예측은 후속 단계입니다.


<br>

## 🛠 기술 스택

| 기술 | 역할 |
| :--- | :--- |
| **Python** | 전처리 파이프라인과 검증 스크립트 실행 |
| **pandas · NumPy** | 이벤트 정제, 시계열 집계, 피처 계산 |
| **PyArrow · Parquet** | 분석용 중간 데이터와 결과 저장 |
| **Amplitude** | 사용자 행동 이벤트 로그 제공 |

<a id="quick-start"></a>

## 🚀 빠른 시작

**준비 사항:** Python 3.9 이상, Bash, 패키지 설치를 위한 인터넷 연결. macOS·Linux 또는 Windows의 WSL에서 실행할 수 있습니다.

저장소를 내려받습니다.

```bash
git clone https://github.com/jjwm10625/applied-data-science-prism.git
cd applied-data-science-prism
git checkout develop
```

프로젝트 최상위 폴더에서 **아래 한 명령으로 실행합니다.**

```bash
bash run.sh
```

가상환경 생성 → 의존성 설치 → 이벤트 정제 → 이탈 피처 생성 → 알림 피처 생성 → 검증까지 순서대로 진행합니다. 의존성은 [requirements.txt](requirements.txt)에 정의되어 있으며, 기존 `.venv`가 있으면 재사용합니다.

> 결과는 `processed_kst/`에 저장됩니다. 재실행하면 같은 이름의 결과 파일을 덮어씁니다. 원본 전체를 처리하므로 데이터 규모와 실행 환경에 따라 시간과 메모리가 필요합니다.

<br>

<a id="data"></a>

## 🗂️ 데이터

### 입력 데이터

원본 Amplitude 로그는 **저장소에 포함**되어 있어 별도 다운로드 없이 실행할 수 있습니다.

```text
export_data/734177/YYYY-MM/*.json.gz
```

- **형식:** gzip으로 압축한 JSON Lines 이벤트 로그
- **분석 기간:** 2025-10-08 ~ 2026-10-26, KST 기준
- **사용자 식별자:** 서비스 계정 ID가 아닌 Amplitude의 `amplitude_id`

원본을 별도로 전달받았다면 같은 경로에 배치하면 됩니다. 전처리는 하위 폴더의 모든 `*.json.gz` 파일을 읽습니다. 원본 경로와 분석 기간은 [preprocess.py](src/preprocessing/preprocess.py)에서 확인할 수 있습니다.

### 결과 데이터

| 파일 · `processed_kst/` 기준 | 내용 |
| :--- | :--- |
| `churn_features.csv` | 사용자·기준일별 이탈 예측 피처와 라벨 |
| `notification_features_weekday.csv` | 사용자·기준일별 알림 선호도와 요일별 선호 시간 |
| `clean_events.parquet` | 정제된 이벤트 |
| `daily_activity.parquet` | 사용자별 일간 활동 집계 |

최종 데이터는 CSV와 Parquet로 저장됩니다. 파생 데이터와 가상환경은 Git 추적 대상에서 제외되어 있으며, 실행 후 로컬에서 확인할 수 있습니다.

<br>

<a id="criteria"></a>

## 🔎 분석 기준

### 활동의 정의

[행동 그룹 매핑](src/preprocessing/behavior_groups.py)에 정의한 **65개 이벤트**만 활동으로 인정합니다.

| 행동 그룹 | 대표 행동 |
| :--- | :--- |
| **유입 · Entry** | 위젯 클릭, 푸시 알림 클릭 |
| **앱 이용 · App usage** | 화면 조회, 프로필·피드 탐색, 소셜 반응 |
| **학습 · Learning** | 일기 작성 관련 행동, 단어 찾기·복습, 발음 사용 |

같은 날 여러 그룹을 이용해도 전체 활동일은 **1일**로 계산합니다. 그룹별 활동일은 각각 집계합니다. 활동일, 최근 활동 경과일, 이탈 라벨, 분석 대상 선정, 알림 집계에 동일한 이벤트 기준을 적용합니다.

`widget_count`, 자동 세션 시작·종료, 미분류 이벤트와 코드에 지정된 이상 사용자 6명은 제외합니다. 위젯·푸시·프로필 알림의 클릭 이벤트는 유지합니다.

### 관측 구간과 이탈 라벨

| 항목 | 기준 |
| :--- | :--- |
| 기준일 범위 | 2025-11-05 ~ 2026-10-19 |
| 분석 대상 | 기준일 직전 28일에 활동한 사용자 |
| 피처 관측 구간 | 기준일 직전 7·14·21·28일 |
| 이탈 라벨 | 기준일 다음 날부터 7일간 활동이 없으면 `churn_label = 1` |
| 기준일 당일 | 피처와 라벨 계산에서 제외 |

학습 활동일은 학습 완료일이 아닌 **관련 행동이 발생한 날**입니다. 화면 조회 이벤트만으로 실제 전경 조회와 자동 화면 전환을 완전히 구분할 수는 없습니다. 활동이 없는 요일의 선호 시간과 사용하지 않은 기능의 선호도는 결측값일 수 있습니다.

<br>

<a id="structure"></a>

## 📂 프로젝트 구조

```text
.
├── assets/images/               # README 브랜딩 이미지
├── run.sh                       # 환경 준비부터 생성·검증까지 한 번에 실행
├── requirements.txt             # Python 의존성
├── export_data/734177/           # 월별 Amplitude 원본
├── processed_kst/               # 생성된 CSV·Parquet
├── src/
│   ├── preprocessing/           # 정제, 피처 생성, 검증
│   └── modeling/                # 후속 모델링 작업 공간
├── tests/                       # 행동 그룹·위젯 필터 테스트
├── reports/                     # 이벤트 분류와 분석 보고서
├── notebooks/                   # 탐색·실험 공간
├── models/                      # 학습 모델 저장 공간
├── configs/                     # 설정 파일 공간
└── docs/                        # 작업 문서
```

<br>

## ✅ 검증과 참고 자료

`run.sh`는 피처 검증과 전체 행의 행동 그룹·활동일·최근 활동 경과일·이탈 라벨 검증을 실행합니다. 생성된 결과만 다시 검증하려면 아래 명령을 사용합니다.

```bash
.venv/bin/python src/preprocessing/validate_features.py
.venv/bin/python src/preprocessing/validate_behavior_union.py
```

필터와 행동 그룹의 단위 테스트는 다음과 같이 실행합니다.

```bash
.venv/bin/python -m unittest discover -s tests
```

- [행동 그룹 매핑](reports/behavior_group_mapping.md)
- [이벤트 모델링 분류](reports/event_modeling_classification.md)
- [이벤트 최초 관측일](reports/event_introductions.md)

이벤트 최초 관측일 보고서는 `.venv/bin/python src/preprocessing/report_event_introductions.py`로 갱신할 수 있습니다. 최초 관측일은 실제 기능 출시일과 다를 수 있습니다.
