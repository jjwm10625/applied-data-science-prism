import pandas as pd
import numpy as np

from behavior_groups import BEHAVIOR_EVENTS, EVENT_TO_GROUP

# ============================================================
# 1. 기본 설정
# ============================================================

DATA_DIR = "processed_kst"

daily = pd.read_parquet(f"{DATA_DIR}/daily_activity.parquet")
features = pd.read_parquet(f"{DATA_DIR}/churn_features.parquet")

DATA_START = pd.Timestamp("2025-10-08")
DATA_END = pd.Timestamp("2026-10-26")

START_DATE = DATA_START + pd.Timedelta(days=28)
END_DATE = pd.Timestamp("2026-10-19")

COUNT_COLS = [
    "event_count",
    "session_count",
    "diary_count",
    "vocabulary_count",
    "pronunciation_count",
    "social_count",
]

WINDOWS = [7, 14, 21, 28]

SAMPLE_SIZE = 1000
RANDOM_STATE = 42

# ============================================================
# 2. 데이터 형식 정리
# ============================================================

daily["date"] = pd.to_datetime(
    daily["date"]
).dt.normalize()

features["reference_date"] = pd.to_datetime(
    features["reference_date"]
).dt.normalize()

daily["user_id"] = daily["user_id"].astype(str)
features["user_id"] = features["user_id"].astype(str)

events = pd.read_parquet(f"{DATA_DIR}/clean_events.parquet", columns=["user_id", "event_time", "event_type"])
events["event_time"] = pd.to_datetime(events["event_time"])
assert events.event_type.isin(EVENT_TO_GROUP).all(), "비그룹 이벤트가 활동 데이터에 남음"
# Independently collect distinct observed dates for each behavior.
behavior_dates = {
    group: {str(uid): part["event_time"].dt.normalize().drop_duplicates().sort_values()
            for uid, part in events.loc[events.event_type.isin(names)].groupby("user_id")}
    for group, names in BEHAVIOR_EVENTS.items()
}
del events

errors = []
checked = 0

print("=== KST Feature 검증 시작 ===")
print("일간 활동 데이터:", f"{len(daily):,}")
print("전체 학습 샘플:", f"{len(features):,}")

# ============================================================
# 3. 전체 데이터 기본 검사
# ============================================================

assert not daily.duplicated(
    ["user_id", "date"]
).any(), "일간 데이터 중복"

assert not features.duplicated(
    ["user_id", "reference_date"]
).any(), "Feature 중복"

assert features.isna().sum().sum() == 0, "Feature 결측치 존재"

assert features["churn_label"].isin(
    [0, 1]
).all(), "이탈 라벨 오류"

assert daily["date"].between(
    DATA_START, DATA_END
).all(), "일간 활동 데이터 기간 오류"

assert features["reference_date"].between(
    START_DATE, END_DATE
).all(), "기준일 범위 오류"

assert (
    features["active_days_28d"] >= 1
).all(), "최근 28일 활동 조건 오류"

assert (
    daily[COUNT_COLS] >= 0
).all().all(), "음수 활동량 존재"

print("전체 데이터 기본 검사: PASS")

# ============================================================
# 4. 사용자별 활동 기록
# ============================================================

activity = {
    uid: group.set_index("date").sort_index()
    for uid, group in daily.groupby("user_id")
}

# 재현 가능한 무작위 샘플 1,000개
sample = features.sample(
    n=min(SAMPLE_SIZE, len(features)),
    random_state=RANDOM_STATE
)

# ============================================================
# 5. Feature 및 이탈 라벨 검증
# ============================================================

for row in sample.itertuples(index=False):

    user = activity[row.user_id]
    ref = row.reference_date

    # --------------------------------------------------------
    # 5-1. 과거 7·14·21·28일 Feature 검증
    # --------------------------------------------------------

    for window in WINDOWS:

        past = user.loc[
            (user.index >= ref - pd.Timedelta(days=window))
            & (user.index < ref)
        ]

        for col in COUNT_COLS:

            expected = past[col].sum()
            actual = getattr(row, f"{col}_{window}d")

            if not np.isclose(expected, actual):
                errors.append((
                    row.user_id,
                    ref,
                    f"{col}_{window}d",
                    expected,
                    actual
                ))

        expected_days = (past["event_count"] > 0).sum()
        actual_days = getattr(
            row,
            f"active_days_{window}d"
        )

        if expected_days != actual_days:
            errors.append((
                row.user_id,
                ref,
                f"active_days_{window}d",
                expected_days,
                actual_days
            ))

        for behavior in BEHAVIOR_EVENTS:
            dates_for_user = behavior_dates[behavior].get(row.user_id, pd.Series([], dtype="datetime64[ns]"))
            expected_group_days = ((dates_for_user >= ref - pd.Timedelta(days=window)) & (dates_for_user < ref)).sum()
            actual_group_days = getattr(row, f"{behavior}_days_{window}d")
            if actual_group_days != expected_group_days:
                errors.append((row.user_id, ref, f"{behavior}_days_{window}d", expected_group_days, actual_group_days))

    # --------------------------------------------------------
    # 5-2. 마지막 활동 이후 경과일 검증
    # --------------------------------------------------------

    previous = user.loc[
        (user.index < ref)
        & (user["event_count"] > 0)
    ]

    if previous.empty:
        errors.append((
            row.user_id,
            ref,
            "recency_days",
            "이전 활동 기록 필요",
            row.recency_days
        ))
    else:
        expected_recency = (
            ref - previous.index.max()
        ).days

        if expected_recency != row.recency_days:
            errors.append((
                row.user_id,
                ref,
                "recency_days",
                expected_recency,
                row.recency_days
            ))

    # --------------------------------------------------------
    # 5-3. 미래 7일 이탈 라벨 검증
    # --------------------------------------------------------

    future = user.loc[
        (user.index > ref)
        & (user.index <= ref + pd.Timedelta(days=7))
    ]

    expected_label = int(
        future["event_count"].sum() == 0
    )

    if expected_label != row.churn_label:
        errors.append((
            row.user_id,
            ref,
            "churn_label",
            expected_label,
            row.churn_label
        ))

    # --------------------------------------------------------
    # 5-4. 최근 28일 활동 조건 확인
    # --------------------------------------------------------

    if row.active_days_28d < 1:
        errors.append((
            row.user_id,
            ref,
            "28일 활동 조건",
            ">= 1",
            row.active_days_28d
        ))

    checked += 1

# ============================================================
# 6. 검증 결과 출력
# ============================================================

print("\n=== KST 전처리 검증 결과 ===")

print("전체 샘플:", f"{len(features):,}")
print("검증한 샘플:", f"{checked:,}")
print("발견된 오류:", len(errors))

if errors:

    print("\n=== 오류 예시 (최대 10개) ===")

    for error in errors[:10]:
        print(error)

    print("\n검증 결과: FAIL")

else:

    print(
        "\nPASS: 검사한 샘플의 Feature 및 "
        "이탈 라벨이 일간 활동 데이터와 일치합니다."
    )

print(
    "\n※ 원본 이벤트의 의미 및 시간대 해석의 정확성은 "
    "별도 검증이 필요합니다."
)
if errors:
    raise SystemExit(1)
