from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("processed_kst")

EVENTS = ROOT / "clean_events.parquet"
CHURN = ROOT / "churn_features.parquet"
OUTPUT = ROOT / "notification_features.parquet"


def main():
    # 1. 파일 확인
    if not EVENTS.exists() or not CHURN.exists():
        raise FileNotFoundError(
            "clean_events.parquet와 churn_features.parquet가 필요합니다."
        )

    # 2. 이탈 예측 데이터에서 기준일 및 기능별 활동량 가져오기
    base = pd.read_parquet(
        CHURN,
        columns=[
            "user_id",
            "reference_date",
            "diary_count_28d",
            "vocabulary_count_28d",
            "pronunciation_count_28d",
            "social_count_28d",
        ],
    )

    base["reference_date"] = pd.to_datetime(
        base["reference_date"]
    ).dt.normalize()

    if base.duplicated(["user_id", "reference_date"]).any():
        raise ValueError("사용자·기준일 조합에 중복이 있습니다.")

    # 3. 이벤트 데이터 불러오기
    events = pd.read_parquet(
        EVENTS,
        columns=["user_id", "event_time"],
    )

    events["event_time"] = pd.to_datetime(events["event_time"])
    events = events.dropna(subset=["user_id", "event_time"])

    # event_time은 기존 전처리에서 KST로 변환된 값
    events["event_date"] = events["event_time"].dt.normalize()
    events["hour"] = events["event_time"].dt.hour
    events["weekday"] = events["event_time"].dt.dayofweek

    # 4. 사용자별·날짜별 시간대 활동 횟수
    hour_daily = (
        events.groupby(["user_id", "event_date", "hour"])
        .size()
        .unstack("hour", fill_value=0)
        .reindex(columns=range(24), fill_value=0)
    )

    hour_daily.columns = [f"h{h}" for h in range(24)]
    hour_daily = hour_daily.reset_index()

    # 5. 사용자별·날짜별 요일 활동 횟수
    weekday_daily = (
        events.groupby(["user_id", "event_date", "weekday"])
        .size()
        .unstack("weekday", fill_value=0)
        .reindex(columns=range(7), fill_value=0)
    )

    weekday_daily.columns = [f"w{d}" for d in range(7)]
    weekday_daily = weekday_daily.reset_index()

    daily = hour_daily.merge(
        weekday_daily,
        on=["user_id", "event_date"],
        how="left",
        validate="one_to_one",
    )

    del events, hour_daily, weekday_daily

    daily = daily.sort_values(
        ["user_id", "event_date"]
    )

    base = base.sort_values(
        ["user_id", "reference_date"]
    ).reset_index(drop=True)

    n = len(base)

    hour_counts = np.zeros((n, 24), dtype=np.int32)
    weekday_counts = np.zeros((n, 7), dtype=np.int32)

    # 6. 기준일 이전 28일 활동만 집계
    grouped_daily = {
        user: part
        for user, part in daily.groupby("user_id", sort=False)
    }

    for user, positions in base.groupby(
        "user_id", sort=False
    ).indices.items():

        part = grouped_daily.get(user)

        if part is None:
            continue

        dates = part["event_date"].to_numpy(
            dtype="datetime64[ns]"
        )

        refs = base.loc[
            positions, "reference_date"
        ].to_numpy(dtype="datetime64[ns]")

        starts = np.searchsorted(
            dates,
            refs - np.timedelta64(28, "D"),
            side="left",
        )

        ends = np.searchsorted(
            dates,
            refs,
            side="left",
        )

        columns = (
            [f"h{h}" for h in range(24)]
            + [f"w{w}" for w in range(7)]
        )

        values = part[columns].to_numpy(
            dtype=np.int32
        )

        prefix = np.vstack([
            np.zeros((1, 31), dtype=np.int64),
            np.cumsum(values, axis=0, dtype=np.int64),
        ])

        sums = prefix[ends] - prefix[starts]

        hour_counts[positions] = sums[:, :24]
        weekday_counts[positions] = sums[:, 24:]

    # 7. 선호 시간·요일 계산
    hour_total = hour_counts.sum(axis=1)
    weekday_total = weekday_counts.sum(axis=1)

    if not np.array_equal(hour_total, weekday_total):
        raise AssertionError(
            "시간대별·요일별 이벤트 수가 일치하지 않습니다."
        )

    preferred_hour = np.argmax(
        hour_counts, axis=1
    ).astype("float64")

    preferred_weekday = np.argmax(
        weekday_counts, axis=1
    ).astype("float64")

    preferred_hour[hour_total == 0] = np.nan
    preferred_weekday[weekday_total == 0] = np.nan

    hour_peak = hour_counts.max(axis=1)
    weekday_peak = weekday_counts.max(axis=1)

    # 8. 선호 기능 계산
    feature_cols = [
        "diary_count_28d",
        "vocabulary_count_28d",
        "pronunciation_count_28d",
        "social_count_28d",
    ]

    feature_names = np.array([
        "diary",
        "vocabulary",
        "pronunciation",
        "social",
    ], dtype=object)

    feature_counts = base[feature_cols].to_numpy(
        dtype=np.float64
    )

    feature_peak = feature_counts.max(axis=1)

    preferred_feature = feature_names[
        np.argmax(feature_counts, axis=1)
    ].copy()

    preferred_feature[feature_peak <= 0] = None

    # 9. 결과 데이터 생성
    out = base[
        ["user_id", "reference_date"]
    ].copy()

    out["preferred_hour"] = pd.Series(
        preferred_hour
    ).astype("Int64")

    out["preferred_weekday"] = pd.Series(
        preferred_weekday
    ).astype("Int64")

    out["preferred_feature"] = pd.Series(
        preferred_feature,
        dtype="string",
    )

    out["hour_activity_count"] = hour_peak
    out["weekday_activity_count"] = weekday_peak
    out["feature_activity_count"] = feature_peak.astype("int64")

    out["event_count_28d"] = hour_total

    out["preferred_hour_share"] = np.divide(
        hour_peak,
        hour_total,
        out=np.full(n, np.nan),
        where=hour_total > 0,
    )

    out["preferred_weekday_share"] = np.divide(
        weekday_peak,
        weekday_total,
        out=np.full(n, np.nan),
        where=weekday_total > 0,
    )

    feature_total = feature_counts.sum(axis=1)

    out["preferred_feature_share"] = np.divide(
        feature_peak,
        feature_total,
        out=np.full(n, np.nan),
        where=feature_total > 0,
    )

    # 10. 기존 이탈 예측 데이터와 검증
    churn_totals = pd.read_parquet(
        CHURN,
        columns=[
            "user_id",
            "reference_date",
            "event_count_28d",
        ],
    )

    churn_totals["reference_date"] = pd.to_datetime(
        churn_totals["reference_date"]
    ).dt.normalize()

    checked = out[
        ["user_id", "reference_date", "event_count_28d"]
    ].merge(
        churn_totals,
        on=["user_id", "reference_date"],
        validate="one_to_one",
        suffixes=("_notification", "_churn"),
    )

    if len(checked) != len(out):
        raise AssertionError(
            "이탈 예측 데이터와 사용자·기준일이 일치하지 않습니다."
        )

    mismatches = (
        ~np.isclose(
            checked["event_count_28d_notification"],
            checked["event_count_28d_churn"],
        )
    ).sum()

    if mismatches:
        raise AssertionError(
            f"28일 이벤트 수 불일치: {mismatches:,}건"
        )

    # 11. Parquet 저장
    out.to_parquet(OUTPUT, index=False)

    print(f"\n저장 완료: {OUTPUT}")
    print(f"행 수: {len(out):,}")
    print(f"사용자 수: {out['user_id'].nunique():,}")
    print(f"컬럼 수: {len(out.columns)}")

    print("\n선호도 결측 비율:")
    print(
        out[
            [
                "preferred_hour",
                "preferred_weekday",
                "preferred_feature",
            ]
        ].isna().mean()
    )

    print("\n컬럼 자료형:")
    print(out.dtypes)

    print("\n검증 완료")


if __name__ == "__main__":
    main()