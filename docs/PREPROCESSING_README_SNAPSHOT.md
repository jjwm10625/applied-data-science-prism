# 프리즘 · HiLingual

**팀원에게 전달:** [modeling_dataset.csv](outputs/final/handoff/modeling_dataset.csv) — 35,807행 × 216열

**보고서:** [전처리 결과 보고서](outputs/final/reports/PREPROCESSING_REPORT.md)

```text
.
├── data/                 원본 · 비교 기준 · 과거 기록 압축본
├── pipeline/             실행 코드 · 설정 · 테스트
└── outputs/final/
    ├── handoff/          팀 전달용 CSV · 컬럼 설명 · 사용법
    ├── reports/          서술형 보고서 · 품질 요약
    │   ├── schema/      전체 컬럼 설명 · 이벤트 매핑
    │   ├── quality/     수집 현황 · 라벨 제외 현황
    │   └── validation/  검증 결과 · 테스트 로그
    ├── data/            정제 이벤트 · 일일 집계
    ├── features/        기간별 전체·라벨 보유·추론 표본
    ├── personalization/ 개인화 분석 자료
    └── provenance/      실행 코드 사본 · 설정 · 해시
```

정답은 **`label_proxy_churn_7d`**입니다. 0은 7,967행, 1은 27,840행입니다. 수집 안정성을 가정한 로그 기준 7일 미활동을 예측하며, 실제 미접속을 확정한 라벨은 아닙니다. 미확정 1,464행과 기존 엄격 라벨은 전체 Feature 파일에 보존했습니다.

[팀 전달 설명서](outputs/final/handoff/README.md) · [품질 요약](outputs/final/reports/DATA_QUALITY.md) · [실행 방법](pipeline/README.md) · [설정](pipeline/config.json)

프로젝트 루트에서 실행:

```bash
# 모델링용 단일 CSV 생성
python3 pipeline/export_modeling_csv.py outputs/final

# 기존 Feature를 유지하고 대리 라벨만 새 실행으로 생성
python3 pipeline/relabel.py outputs/final

# 전체 파이프라인 실행이 필요한 경우
python3 pipeline/run.py
```

`pipeline`은 현재 실행 코드, `provenance/code`는 당시 실행 기록입니다. 원본과 `.pseudonym_key`는 보존했습니다. 모델링 담당자에게는 `handoff` 폴더를 전달하고, 원본·비밀키·과거 다운로드 코드는 공유하지 마세요.

현재 대상: 최근 28일 접속 확인 + 최초 관측 이후 28일 이상. 기준일 7일 간격은 임시 설정이며 최종 시간 분할 전입니다.

대상 조건만 바꾸어 재생성: `python3 pipeline/rebuild_features.py outputs/final`
