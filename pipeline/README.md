# 프리즘 · HiLingual 데이터 전처리

기존 정제본/일일 집계/가명 키를 보존하고 pandas·NumPy로 재집계하며, 원본 ZIP에서는 서버 업로드 시각과 북마크·공감 action만 추가 추출합니다. 모델 학습·성능 평가·실제 알림 발송·실사용자 연결은 포함하지 않습니다.

## 7일 예측 대상과 라벨 정책

> 과거 데이터에서는 향후 7일간 관측 가능한 앱 활동이 없는 상태를 예측한다. 수집 안정성을 가정한 대리 라벨을 사용하며, 실제 미접속과의 차이를 한계로 보고한다.

FR-1의 관찰 기간은 그대로 7·14·21·28일이며 정답 구간은 `[T,T+7일)`입니다. 네 세트는 동일한 사용자·기준일과 라벨을 사용합니다. FR-2에서 산출할 확률은 **로그 기준 향후 7일 미활동의 대리 라벨 확률**이며 실제 미접속 확률로 검증됐다고 표현하지 않습니다. 성능 지표와 확률 구간별 실제 비율도 대리 라벨 기준으로 평가했다고 보고해야 합니다.

- 모델링 정답: **`label_proxy_churn_7d`**. 0은 미래 접속 확인, 1은 수집 안정성 가정하의 미래 7일 기록 없음, 결측은 판정 보류입니다.
- 보존된 엄격 정답: `label_churn_7d`, `label_status`, `label_reason`. 원래 값은 변경하지 않습니다.
- `label_proxy_status`, `label_proxy_reason`, `label_proxy_assumption_applied`에 판정과 가정 적용 여부를 기록합니다. 이 컬럼들과 모든 `label_*` 컬럼은 모델 입력에서 제외합니다.
- 가정 범위는 `proxy_label_policy.assumed_collection_intervals`의 `[2025-10-26,2026-10-08)`입니다. 이 구간의 수집 완전성이 검증된 것은 아닙니다. iOS·Android 기존 대상을 유지하는 분석 가정이며 플랫폼·버전의 구현 검증 결과가 아닙니다.
- 미래 7일이 분석/가정 범위를 벗어나거나 의심 구간과 겹치면 제외합니다. 접속 확인 없이 세션·위젯 등 미확인 기록만 있어도 결측을 유지합니다.
- `verified_collection_intervals`와 Feature 수집 품질 플래그는 그대로 둡니다. 가정을 수집 검증 사실로 바꾸지 않습니다.
- 기존 접속 이벤트 규칙은 이번 변경에서 바꾸지 않았습니다. iOS 코드 조사만으로 Android나 과거 버전을 승격하지 않습니다.

## 현재 대상 선정과 Feature 재생성

최근 **28일** 안에 접속 확인 기록이 있고, 최초 관측 KST 날짜로부터 기준일까지 **28일 이상** 지난 사용자 키를 대상으로 합니다. 가입일이나 실제 사람 수를 뜻하지 않습니다. 기준일은 KST 00:00, 7일 간격의 **임시 분석 설정**이며 팀 합의 전입니다. 시간 분할 날짜도 미설정입니다.

정제·일일 집계 규칙을 유지하고 대상 선정만 바꿀 때는 다음 명령으로 기존 결과를 검증해 재사용합니다. 새 실행 폴더에 Feature·라벨·개인화 프로필·단일 모델링 CSV를 생성하고 원본 실행을 보존합니다.

```bash
python3 pipeline/rebuild_features.py outputs/final --config pipeline/config.json
```

원본 정제 또는 접속 판정 규칙이 바뀌면 전체 파이프라인을 사용하세요.

## 라벨만 다시 생성 (기존 결과 재사용)

기본 정제·일일 집계·Feature를 재계산하지 않습니다. 기존 실행을 보존하고 새 `_proxy` 실행 폴더에 데이터 사본, 새 라벨과 학습 대상 파일, 근거·검증 기록을 저장합니다. 입력 이벤트·개인화 데이터는 바이트 해시가 동일하며 기존 모든 Feature/엄격 라벨 값도 동일한지 검사합니다.

```bash
python3 pipeline/relabel.py outputs/final --config pipeline/config.json
```

이 명령은 엄격 라벨을 보존하고 있는 현재 최종 실행을 입력으로 사용합니다. 기존 대리 라벨은 새 실행에서 다시 계산합니다. 관찰 기간·대상 선정·시간 분할·업로드 정책 등 기존 계산에 영향을 주는 설정을 바꾸면 재사용을 거부합니다. 그런 변경은 아래 전체 파이프라인으로 생성하세요. 특히 `available_at_reference`로 바꾸려면 Feature도 다시 계산해야 합니다.

## VS Code 전체 실행

프로젝트 폴더를 열고 터미널에서 실행합니다. Python 3.9 이상을 사용하세요.

```bash
cd /Users/youngseo/Assignment/hilingual-data
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r pipeline/requirements.txt
python -m unittest discover -s pipeline -p 'test_*.py' -v
python pipeline/run.py --config pipeline/config.json
```

VS Code의 Python: Select Interpreter에서 `.venv/bin/python`을 선택합니다. 실행 결과는 매번 새로운 `outputs/<UTC 실행 ID>/`에 저장됩니다. 기존 ZIP·정제본·일일 집계는 덮어쓰지 않습니다. 입력이 현재처럼 UUID 충돌/누락이 없는지 검사하며 다른 데이터에서 충돌이 있으면 임의 병합하지 않고 중단합니다. 원본 재정제의 중복 제거는 기존 코드가 완료했으므로 반복하지 않습니다.

이 스크립트는 프로젝트 안 `pipeline`에서 실행하세요. 결과 폴더의 코드 사본은 재현 기록입니다. 재실행하려면 프로젝트 내 코드/설정과 당시 입력 해시를 맞춥니다. 기존 `.pseudonym_key`가 반드시 필요하며 새로 만들지 않습니다. 비밀키는 읽기만 하고 결과/해시에 포함하지 않습니다.

## 폴더 구성

- `data/raw/`: 원본 ZIP 13개와 다운로드 기록
- `data/baseline/`: 재실행과 기존 결과 대조에 필요한 정제본·일일 집계
- `pipeline/`: 현재 실행 코드·설정·의존성·테스트
- `outputs/<실행 ID>/data/`: 새 정제 이벤트와 일일 집계
- `outputs/<실행 ID>/features/`: 7·14·21·28일 Feature·라벨, 변수 역할
- `outputs/<실행 ID>/personalization/`: 개인화 프로필
- `outputs/<실행 ID>/reports/`: 서술형 보고서와 품질 요약. `schema/`는 컬럼·매핑, `quality/`는 집계·제외 현황, `validation/`은 검증·해시·테스트 기록
- `outputs/<실행 ID>/provenance/`: 설정·패키지·해시, `code/` 안에 실행 코드 사본
- `data/history/`: 고유한 과거 작업 기록의 압축본. 중복 대용량 파일은 현재 최종 결과를 참조합니다.
- `data/baseline/evidence/`: 현재 실행이 참조하는 기존 코드와 검사 근거.

아래 결과 파일명은 위 하위 폴더를 기준으로 찾습니다. 기존 실행의 설정·보고서·코드 사본은 당시 기록을 유지하므로 이전 경로가 남아 있을 수 있습니다. `provenance/path_relocations.json`에 이동 경로가 기록되어 있습니다. 재실행에는 현재 `pipeline/config.json`을 사용하세요.

## 단계와 결과

1. 정제: `events_clean.csv.gz`. 기존 user_key/device_key/event_key 유지, UTC와 KST 날짜/요일/시간, 원본·표준 이벤트명, 행동 분류, 접속 판정 근거, 안전한 add/remove 속성, 업로드 시각. 이벤트 CSV는 청크로 처리하고 필요한 집계 필드만 메모리에 유지합니다. 약 147만 행의 집계용 이벤트는 메모리에 올리므로 수 GB 여유를 권장합니다. SQLite는 원본 속성 조인용 임시 파일이고 실행 후 삭제합니다.
2. 집계: `user_daily_activity.csv.gz`. 이벤트가 있는 사용자·날짜만 생성합니다. `active_flag=0`은 접속 미확인이며 정상 미접속이 아닙니다. 기존 13개 기능 집계를 그대로 유지하고 북마크/공감 add/remove/unknown 집계를 별도 추가했습니다. 기존 컬럼과 모든 사용자·일별 값이 같은지 검사합니다.
3. 모델링: `features_{7,14,21,28}d_all.csv.gz`. 네 파일의 사용자·기준일·라벨·시간 분할은 같습니다. `_labeled`는 설정상 모델링 정답의 미확정 라벨과 분할 경계 제거 행을 제외한 파일이며 아직 train 파일이 아닙니다. 현재 기본 정답은 `label_proxy_churn_7d`입니다. `_inference`는 미래 7일 범위가 부족한 행입니다. 전체 파일에 모든 미확정 행을 보존합니다.
4. 개인화: 정제 이벤트와 `personalization_profiles.csv.gz`를 같은 user_key로 연결합니다. 기준일 이전 28일 동안 날짜·시간대 또는 날짜·행동 분류당 한 표를 부여합니다. 클릭 수가 많은 날을 과대평가하지 않도록 반복 이벤트를 제거합니다. 한 날짜가 여러 시간대에 표를 줄 수 있고, 범주는 넓은 기능 분류입니다. 시간대/요일/기능별 3일 미만 근거는 insufficient입니다. 기록이 전혀 없는 범주는 행이 없으며 선호 0이 아닙니다.
5. 기록: `event_mapping.csv`, `column_dictionary.csv`, `event_collection_by_version.csv`, `daily_collection_counts.csv`, `quality_report.json`, `feature_roles.json`, `label_exclusion_by_*.csv.gz`, `split_exclusions.csv.gz`, 코드·설정 사본. 입력/출력 SHA-256 및 패키지 버전을 기록합니다. 보고서 자체 해시는 별도 `.sha256`에 저장합니다. 출력 파일 독립 검증 후의 최종 해시는 `audit_manifest.json`에 기록합니다. 품질 요약은 `DATA_QUALITY.md`, 테스트 로그는 `test_results.txt`를 확인하세요.

팀 공유에는 실행 결과 폴더를 사용합니다. 원본 ZIP, 기존 다운로드 코드의 인증 정보, `.pseudonym_key`는 공유하지 않습니다. 이름·이메일·일기·푸시 토큰·원본 사용자/기기 식별자는 추출하지 않습니다. 자유 텍스트 page 등도 새 결과에 포함하지 않습니다. 가명 키도 접근 권한을 제한하세요. 가명 키 수는 실제 사람 수가 아닙니다.

## 분석 기준과 미확정 사항

- T는 KST 00:00, 관찰 구간은 `[T-w일,T)`, 라벨 구간은 `[T,T+7일)`입니다. KST는 공통 분석 기준으로 실제 사용자 현지 시각이 아닙니다.
- 기본 기준일은 2025-11-23부터 7일 간격입니다. 최초 관측 후 28일 이상, 최근 7일 접속 확인 사용자만 선정합니다. 4개 기간의 비교 대상을 같게 하고 너무 짧은 관측 이력을 피하기 위한 분석 선택입니다. 가입일 또는 활동 시작일 추정이 아니며 신규 사용자는 이번 비교 대상에서 제외됩니다. 조건은 config에서 변경할 수 있습니다.
- 2025-10-01의 1건과 10-02~10-25 무기록 구간은 수집 신뢰성이 불확실합니다. 기본 분석 범위는 2025-10-26부터 2026-10-08 **직전**까지입니다. 10-26 이후 매일 기록이 있어도 수집 완전성을 뜻하지 않습니다. 2026-10-08은 불완전한 날이므로 최신 추론 Feature에는 이전 시각만 사용하며 해당 날을 포함한 미래 정답은 붙이지 않습니다.
- `verified_collection_intervals`는 기본 빈 목록입니다. 운영 측이 전체 플랫폼/버전의 수집과 지연 업로드 완료를 검증한 반개구간만 등록하세요. `suspect_intervals`와 겹치는 날은 신뢰 가능으로 세지 않습니다. 기능별 전체 수집 검증은 `feature_verified_intervals`에 기능 컬럼별 반개구간으로 명시합니다. 근거 없이 추가하지 마세요.
- Feature의 기능 횟수가 양수면 관측된 횟수이며 실제 전체 이용량의 하한일 수 있습니다. 0인데 기능 수집이 검증되지 않았다면 결측입니다. `*_coverage_verified`로 수집 상태를 표시합니다. 접속일/활동 이벤트/세션 수는 관측량이며 무기록 날짜를 미접속으로 선언하지 않습니다. 버전별 최초·최후 관측 범위는 수집 시작/종료 확증이 아닙니다.
- 기존 4개 이벤트명 매핑은 기존 코드와 사용자 제공 규칙이 근거입니다. 배포 버전별 코드 동등성은 독립 검증되지 않았습니다. 추가 이벤트명 매핑은 없습니다. 클릭과 처리 완료를 구분하며, 완료 이벤트만으로 접속 확인을 추가하지 않습니다.
- 북마크/공감의 add/remove는 원본 속성으로 확인합니다. 다른 값/없는 속성은 unknown입니다. `click_feedback.bookmark_action`, `click_bookmark_action`, `bookmark_action`은 이름을 합치지 않고 별도 추가·삭제 집계에서 넓은 행동 분류로 묶습니다. 공감도 마찬가지입니다. 기존 empathy_count 등과 새 전체 행동 집계의 범위가 다릅니다.
- iOS sceneDidBecomeActive에서 widget_count를 전송할 수 있다는 확인은 배포 버전·Android 범위를 확증하지 않습니다. 위젯/세션 기록만 있는 날은 기존대로 미확인입니다. 마지막 이벤트는 실제 앱 종료가 아닙니다.
- 일일 session_count 합은 자정을 넘는 세션을 중복 계산할 수 있습니다. Feature의 unique_active_sessions는 기간 전체 이벤트에서 사용자·기기·양의 정수 session_id로 중복 제거합니다. 원래 세션 문자열은 session_id_original에 보존하고 유효하지 않은 값은 session_id에서 결측 처리합니다.
- 전후반은 관찰 기간을 정확히 같은 시간 길이로 분리합니다. 7/21일 구간의 중간은 정오입니다. 변화율 `(후반-전반)/전반`은 전반 0이면 결측이며 별도 플래그를 둡니다. recency는 T 이전 전체 관측 이력의 마지막 접속 확인을 사용하므로 관찰 구간보다 오래된 이력을 쓸 수 있습니다. 찾지 못하면 결측/사유입니다.

## 보존된 엄격 라벨과 지연 업로드

- 미래 7일이 기본 분석 범위 안에 들어오고 접속 확인 이벤트가 있으면 0입니다.
- 미래 범위가 부족하면 접속 확인 기록이 일부 있어도 최신 기준일 정답은 미확정입니다.
- 미래 7일 전체 수집 신뢰성이 확인되고, 접속 확인 이벤트도 미확인 기록도 없을 때만 1입니다.
- 세션/위젯 등 미확인 기록만 있거나 수집 신뢰성이 미확정이면 결측입니다. 여기서 이탈은 영구 탈퇴가 아니라 정한 기준에 따른 향후 7일 앱 활동 미관측입니다.
- **엄격 라벨에는 현재 1이 없습니다.** 모델링에는 별도 대리 라벨을 사용합니다. `label_exclusion_by_*`는 엄격 라벨 기준, `proxy_label_exclusion_by_*`는 대리 라벨 기준 제외 현황입니다. 가정에 따른 새 라벨 분포는 `proxy_label_report.json`, 변경 전후는 `label_policy_transitions.csv`에 기록합니다.
- Export는 서버 업로드 기준입니다. 기본 `late_upload_policy=retrospective_snapshot`은 현재 스냅샷에서 발생 시각 `<T`인 이벤트를 사용합니다. T 후 업로드된 과거 행동이 포함될 수 있으므로 실시간 당시 가용성 백테스트와 다릅니다. `available_at_reference`는 Feature와 대상 선정에서 서버 업로드 시각도 `<T`인 행만 사용합니다. 업로드 시각이 없으면 그 모드에서 제외합니다. 모델 평가 목적에는 이 모드로 재생성하는 것이 적절합니다.
- `label_upload_deadline_utc`를 설정하면 그 UTC 시각까지 업로드된 이벤트만 라벨 근거로 사용합니다. 기본 null은 모든 스냅샷 기록입니다. 지연 업로드가 완결되었다는 근거는 없으며 완결 여부를 검증하지 않은 구간을 verified에 넣으면 안 됩니다.

## 시간 분할과 sklearn

기본 `split_dates=null`이며 최종 분할을 임의로 확정하지 않습니다. 합의 후 다음 형태로 입력하세요(날짜는 팀에서 결정).

```json
"split_dates": {"validation_start": "YYYY-MM-DD", "test_start": "YYYY-MM-DD"}
```

앞 구간의 `T+7일`이 다음 시작을 넘는 행은 `purged_label_overlap`로 남기고 학습용 파일에서 제외합니다. 정확히 같으면 반개구간이므로 허용합니다. 네 기간에 동일한 분할을 적용합니다. 무작위 행 분할은 없습니다.

`model_transform.py`는 숫자 결측 대체, 선택적 스케일링, 범주형 결측 대체/인코딩을 제공합니다. 모델별로 scale을 선택하고 `feature_roles.json`의 후보에서 팀이 변수 목록을 확정하세요. user_key/기준일/라벨은 입력으로 사용하지 않습니다.

```python
from pipeline.model_transform import transform_splits
# y_train = train["label_proxy_churn_7d"]
# Feature는 feature_roles.json의 후보에서 확정하고, label_*는 전부 제외하세요.
# train, validation, test: 합의된 시간 분할 파일을 읽은 DataFrame
# 변환기만 학습하며 예측 모델은 학습하지 않습니다.
transformer, X_train, X_validation, X_test = transform_splits(
    train, validation, test,
    numeric=["confirmed_active_days", "unique_active_sessions", "recency_days"],
    categorical=[], scale=False,
)
```

전체 데이터 fit은 하지 않습니다. 완전히 결측인 숫자 변수는 sklearn imputer의 keep_empty_features로 유지되지만 모델링 팀이 의미를 검토해 제외할 수 있습니다. 숫자 결측 표시자가 추가됩니다. 모든 집계 합계가 일치해도 접속 규칙의 의미적 타당성이 입증된 것은 아닙니다.

## 출력 파일만 재검증

원본 ZIP을 다시 처리하지 않고 다음 명령으로 출력의 시각 경계/결측/일반·구버전·자정 사례를 재검증할 수 있습니다.

```bash
python pipeline/validate_outputs.py outputs/<실행_ID>
```

실행 환경에서 검증한 정확한 패키지 버전은 실행 폴더 `reports/validation/quality_report.json`의 packages를 확인하세요.

## 모델링 담당자에게 단일 CSV 전달

```bash
python3 pipeline/export_modeling_csv.py outputs/final
```

`handoff/modeling_dataset.csv` 한 파일에 사용자·기준일당 한 행, 7·14·21·28일 Feature를 열 방향으로 합칩니다. 정답은 한 번만 저장합니다. `w7__` 등은 모델 후보, `q7__` 등은 품질 정보입니다. 동일 행의 해당 기간 w 컬럼만 선택해 기간별 비교를 진행하세요. 전체 216열을 그대로 모델에 넣지 않습니다. Feature 재계산 없이 원래 네 CSV와 값이 같은지 확인하고, CSV 저장·재읽기 검증 및 해시를 기록합니다.
