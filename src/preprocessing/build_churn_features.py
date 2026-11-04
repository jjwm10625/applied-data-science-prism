import pandas as pd
from pathlib import Path

from behavior_groups import BEHAVIOR_EVENTS, GROUP_COLUMNS, daily_behavior_flags

# ============================================================
# 1. 기본 설정
# ============================================================

DATA_DIR = Path("processed_kst")

INPUT = DATA_DIR / "daily_activity.parquet"
OUTPUT = DATA_DIR / "churn_features.parquet"

# KST 기준 실제 데이터 기간
DATA_START = pd.Timestamp("2025-10-08")
DATA_END = pd.Timestamp("2026-10-26")

# 과거 28일 + 미래 7일 확보
START_DATE = DATA_START + pd.Timedelta(days=28)
END_DATE = DATA_END - pd.Timedelta(days=7)

WINDOWS = [7, 14, 21, 28]

COUNT_COLS = [
    "event_count",
    "session_count",
    "diary_count",
    "vocabulary_count",
    "pronunciation_count",
    "social_count",
]

# 팀원 논의 후 변경 가능
REQUIRE_RECENT_ACTIVITY = True

# ============================================================
# 2. 데이터 불러오기
# ============================================================

if not INPUT.exists():
    raise FileNotFoundError(f"파일이 없습니다: {INPUT}")

daily = pd.read_parquet(INPUT)

daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
daily["user_id"] = daily["user_id"].astype(str)

# All daily counts and group flags use the same reviewed behavior events.
events = pd.read_parquet(DATA_DIR / "clean_events.parquet", columns=["user_id", "event_time", "event_type"])
events["user_id"] = events["user_id"].astype(str)
group_daily = daily_behavior_flags(events)
daily = daily.merge(group_daily, on=["user_id", "date"], how="left", validate="one_to_one")
assert daily[GROUP_COLUMNS].notna().all().all(), "그룹 활동일 집계 누락"
daily["behavior_active"] = daily[GROUP_COLUMNS].any(axis=1)
assert daily["behavior_active"].all(), "비그룹 이벤트만 있는 일간 기록 존재"
del events, group_daily

# ============================================================
# 3. 기본 검증
# ============================================================

assert not daily.duplicated(
    ["user_id", "date"]
).any(), "사용자·날짜 중복이 존재합니다."

assert daily["date"].between(
    DATA_START, DATA_END
).all(), "분석 기간 밖의 데이터가 존재합니다."

assert daily[COUNT_COLS].notna().all().all(), "활동량 결측치가 존재합니다."

assert (daily[COUNT_COLS] >= 0).all().all(), "음수 활동량이 존재합니다."

print("=== KST 기준 Feature 생성 시작 ===")
print("사용자 ID:", daily["user_id"].nunique())
print("데이터 기간:", DATA_START.date(), "~", DATA_END.date())
print("기준일 기간:", START_DATE.date(), "~", END_DATE.date())
print("최근 28일 활동 조건:", REQUIRE_RECENT_ACTIVITY)

# ============================================================
# 4. 기존 결과 보존
# ============================================================

# ============================================================
# 5. 사용자별 Feature 생성
# ============================================================

results = []
total_users = daily["user_id"].nunique()

dates = pd.date_range(
    DATA_START,
    DATA_END,
    freq="D"
)

for i, (user_id, group) in enumerate(
    daily.groupby("user_id"), 1
):

    group = group.set_index("date").sort_index()

    # 사용자 최초 활동일 다음 날부터 기준일 생성 가능
    first_reference = max(
        START_DATE,
        group.index.min() + pd.Timedelta(days=1)
    )

    if first_reference > END_DATE:
        continue

    # 활동이 없는 날짜는 0으로 채움
    full = group[COUNT_COLS + GROUP_COLUMNS + ["behavior_active"]].reindex(
        dates,
        fill_value=0
    )

    # 기준일 당일 이벤트는 Feature에서 제외
    past = full.shift(1, fill_value=0)

    features = pd.DataFrame(index=dates)

    # --------------------------------------------------------
    # 7·14·21·28일 행동 Feature
    # --------------------------------------------------------

    for window in WINDOWS:

        rolling = past.rolling(
            window,
            min_periods=window
        )

        for col in COUNT_COLS:
            features[f"{col}_{window}d"] = (
                rolling[col].sum()
            )

        features[f"active_days_{window}d"] = (
            past["behavior_active"]
            .gt(0)
            .rolling(window, min_periods=window)
            .sum()
        )

        for behavior in BEHAVIOR_EVENTS:
            features[f"{behavior}_days_{window}d"] = (
                past[f"{behavior}_active"].rolling(window, min_periods=window).sum()
            )

    # --------------------------------------------------------
    # 마지막 활동 이후 경과일
    # --------------------------------------------------------

    last_active = pd.Series(
        dates.where(full["behavior_active"].gt(0)),
        index=dates
    ).ffill().shift(1)

    features["recency_days"] = (
        features.index.to_series() - last_active
    ).dt.days

    # --------------------------------------------------------
    # 미래 7일 이탈 라벨
    # --------------------------------------------------------

    future_7d = sum(
        full["behavior_active"].astype("int8").shift(-offset)
        for offset in range(1, 8)
    )

    features["churn_label"] = (
        future_7d.eq(0).astype("int8")
    )

    # --------------------------------------------------------
    # 학습 샘플 포함 조건
    # --------------------------------------------------------

    eligible = (
        features.index.to_series().between(
            first_reference,
            END_DATE
        )
    )

    # 최근 28일 활동 조건 (선택 사항)
    if REQUIRE_RECENT_ACTIVITY:
        eligible &= features["active_days_28d"].gt(0)

    selected = features.loc[eligible].copy()

    if selected.empty:
        continue

    selected["user_id"] = user_id
    selected["reference_date"] = selected.index

    results.append(
        selected.reset_index(drop=True)
    )

    if i % 500 == 0:
        print(f"처리 완료: {i:,}/{total_users:,}")

# ============================================================
# 6. 데이터 통합
# ============================================================

if not results:
    raise ValueError("생성된 학습 데이터가 없습니다.")

df = pd.concat(
    results,
    ignore_index=True
)

# ============================================================
# 7. 최종 검증
# ============================================================

assert df["reference_date"].between(
    START_DATE,
    END_DATE
).all(), "기준일 범위 오류"

assert df["churn_label"].isin(
    [0, 1]
).all(), "이탈 라벨 오류"

assert not df.duplicated(
    ["user_id", "reference_date"]
).any(), "중복 학습 샘플 존재"

assert not df.isna().any().any(), "결측치 존재"

if REQUIRE_RECENT_ACTIVITY:
    assert (
        df["active_days_28d"] > 0
    ).all(), "최근 28일 활동 조건 위반"

# ============================================================
# 8. 결과 저장
# ============================================================

df.to_parquet(
    OUTPUT,
    index=False
)

df.to_csv(DATA_DIR / "churn_features.csv", index=False, encoding="utf-8-sig")

print("\n=== KST 기준 Feature 생성 완료 ===")

print("전체 샘플:", f"{len(df):,}")
print("사용자 ID:", f"{df['user_id'].nunique():,}")

print(
    "이탈 비율:",
    round(df["churn_label"].mean() * 100, 2),
    "%"
)

print("컬럼 수:", len(df.columns))

print(
    "기준일 범위:",
    df["reference_date"].min().date(),
    "~",
    df["reference_date"].max().date()
)

print("저장 위치:", OUTPUT.resolve())