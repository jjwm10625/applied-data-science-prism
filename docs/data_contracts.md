# 모듈 입출력 계약

## 기존 전처리 (변경 없음)

- 이벤트: `outputs/final/data/events_clean.csv.gz`. 이벤트 1행 단위. UTC·KST, 원본/표준 이벤트명, 가명 키, 세션·접속 판정·기능 카운터.
- 일일: `outputs/final/data/user_daily_activity.csv.gz`. `(user_key,date_kst)` 고유.
- 기간별: `outputs/final/features/features_{7,14,21,28}d_all.csv.gz`. `(user_key,reference_date)` 고유. 엄격·대리 라벨, 미확정 사유, Feature 최대 시각 포함.
- Wide: `outputs/final/handoff/modeling_dataset.csv`. 공통 4개, 모델 후보 120개, 품질 92개. `feature_roles.json`으로 컬럼 선택.
- 원본 기능 0은 수집 여부 미확인 시 결측일 수 있음. 일괄 0 대체 금지.
- 빈 미래 범위를 대리 라벨 1로 임의 생성하지 않음. 기존 정의 유지.

## 학습/추론

입력 roles의 `target`, `model_columns_by_window`, `definition`을 사용합니다. wide 데이터와 기간별 원본 roles는 형식이 다르므로 혼용하지 않습니다. `reference_date`는 KST 00:00이고 y는 미래 7일 대리 라벨입니다.

모델 `.joblib`에는 pipeline(전처리+분류기), features 순서, target, threshold, window_days, model, seed, split_settings, dataset_sha256, target_definition, experiment, environment가 포함됩니다. 원본 식별자/비밀키는 포함하지 않습니다. 모델도 분석 정보를 담으므로 Git에서 제외합니다.

예측 CSV: `user_key, reference_date, probability, threshold, predicted_label, window_days, model, seed`. 실험 학습 출력에는 추가로 `y_true, split`이 있습니다. 확률은 [0,1], 위험 분류는 확률 >= threshold. 동일 키/기준일 중복 금지. 최신 입력 생성은 모델 학습과 별개의 작업이며 분류기가 미래 정답을 요구하지 않습니다.

`sample_splits.csv`는 공통 분할, `split_exclusions.csv`는 라벨 경계 제외 표본입니다. 동일 실험 내 네 기간 모두 동일합니다.

## 평가

입력 `*_predictions.csv`. 동일 구간의 사용자/기준일/y_true가 모든 모델·기간·시드에서 일치해야 합니다. `metrics.csv`, `metrics_summary.csv`(mean/std/count), `calibration.csv`를 저장합니다. std는 표본 표준편차(ddof=1)이며 결정적 모델의 시드 차이가 없을 수 있습니다. AP는 한 클래스만 존재하면 결측입니다. 모델/임계값의 추가 최적화는 평가 모듈에서 하지 않습니다.

## 개인화

`personalize.py`는 T 이전 접속 확인 기록만 분석합니다. `available_at_reference` 선택 시 upload<T도 요구합니다. 유효 세션의 과거 최초 접속 확인 시각을 사용하므로 정확한 session_start 이벤트나 실제 앱 실행 시각과 구분합니다.

출력 1행은 사용자·기준일·대상 요일(월=0~일=6)입니다. `window_days`, `time_band_start_hour`, `time_band_hours`, `notify_hour`, `notify_day_offset`, `time_source`, `session_support_days`, `weekday_support_days`, `preferred_function`, `eligible`, `reason`, `body`, `route`, `session_time_basis`, `availability_policy`를 포함합니다.

세션은 사용자·기기·유효 세션으로 중복 제거, 시간대 투표는 고유 날짜 수로 집계합니다. 같은 시간대가 동률이면 최근 근거, 이마저 같으면 이른 구간을 선택합니다. 요일별 근거 부족이면 전체 시간대, 전체 근거 부족이면 제외합니다. 기능은 고유 이용일 수→최근 기록→이벤트 수→이름 순으로 결정합니다. 기본 3일 미만이면 제외합니다. 현 기능 후보는 일기·단어·발음이며 시작/클릭 이벤트를 사용합니다. 문구·라우트는 설정에서 관리합니다.

고정 시간 구간을 사용하므로 23시와 0시는 서로 다른 구간에 속합니다. 순환 군집화를 구현했다고 주장하지 않습니다. 21~24시 구간은 다음 날 00시에 후보가 생깁니다. notify_day_offset=1로 표시하고 실제 예약 날짜 기준 하루 1회 제한을 적용합니다.

기존 `personalization_profiles.csv.gz`는 시간/요일/행동별 근거 자료이며 새 최종 의사결정 CSV와 다른 형식입니다. 기존 파일을 덮어쓰지 않습니다.
