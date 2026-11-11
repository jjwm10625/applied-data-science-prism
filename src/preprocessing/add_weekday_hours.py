from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. 파일 경로
# ============================================================

ROOT = Path("processed_kst")

EVENTS_PATH = ROOT / "clean_events.parquet"
NOTIFICATION_PATH = ROOT / "notification_features.parquet"

OUTPUT_PARQUET = ROOT / "notification_features_weekday.parquet"
OUTPUT_CSV = ROOT / "notification_features_weekday.csv"

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def main():

    # ========================================================
    # 2. 기존 데이터 불러오기
    # ========================================================

    print("데이터 불러오는 중...")

    notification = pd.read_parquet(NOTIFICATION_PATH)

    events = pd.read_parquet(
        EVENTS_PATH,
        columns=["user_id", "event_time"]
    )

    notification["reference_date"] = pd.to_datetime(
        notification["reference_date"]
    ).dt.normalize()

    events["event_time"] = pd.to_datetime(events["event_time"])

    events = events.dropna(
        subset=["user_id", "event_time"]
    ).copy()

    # 기존 전처리에서 KST로 변환된 event_time 사용
    events["event_date"] = events["event_time"].dt.normalize()
    events["weekday"] = events["event_time"].dt.dayofweek
    events["hour"] = events["event_time"].dt.hour

    # ========================================================
    # 3. 사용자 × 날짜 × 요일 × 시간별 이벤트 집계
    # ========================================================

    print("요일·시간대별 활동 집계 중...")

    daily = (
        events.groupby(
            ["user_id", "event_date", "weekday", "hour"]
        )
        .size()
        .reset_index(name="event_count")
    )

    # 요일 × 시간 = 7 × 24 = 168개 조합
    daily["weekday_hour"] = (
        daily["weekday"] * 24 + daily["hour"]
    )

    pivot = daily.pivot_table(
        index=["user_id", "event_date"],
        columns="weekday_hour",
        values="event_count",
        aggfunc="sum",
        fill_value=0
    )

    pivot = pivot.reindex(
        columns=range(168),
        fill_value=0
    )

    pivot.columns = [
        f"wh_{i}" for i in range(168)
    ]

    pivot = pivot.reset_index()

    # ========================================================
    # 4. 기준일 이전 28일 데이터 집계
    # ========================================================

    print("기준일별 최근 28일 활동 분석 중...")

    notification = notification.sort_values(
        ["user_id", "reference_date"]
    ).reset_index(drop=True)

    n = len(notification)

    weekday_hour_counts = np.zeros(
        (n, 168),
        dtype=np.int32
    )

    grouped = {
        user: group
        for user, group in pivot.groupby("user_id", sort=False)
    }

    columns = [
        f"wh_{i}" for i in range(168)
    ]

    for user, positions in notification.groupby(
        "user_id",
        sort=False
    ).indices.items():

        part = grouped.get(user)

        if part is None:
            continue

        dates = part["event_date"].to_numpy(
            dtype="datetime64[ns]"
        )

        refs = notification.loc[
            positions, "reference_date"
        ].to_numpy(dtype="datetime64[ns]")

        starts = np.searchsorted(
            dates,
            refs - np.timedelta64(28, "D"),
            side="left"
        )

        ends = np.searchsorted(
            dates,
            refs,
            side="left"
        )

        values = part[columns].to_numpy(
            dtype=np.int32
        )

        prefix = np.vstack([
            np.zeros((1, 168), dtype=np.int64),
            np.cumsum(values, axis=0, dtype=np.int64)
        ])

        sums = prefix[ends] - prefix[starts]

        weekday_hour_counts[positions] = sums

    # ========================================================
    # 5. 요일별 선호 시간 계산
    # ========================================================

    print("요일별 선호 시간 계산 중...")

    for weekday, name in enumerate(WEEKDAYS):

        start = weekday * 24
        end = start + 24

        counts = weekday_hour_counts[:, start:end]

        # 해당 요일 전체 이벤트 수
        total = counts.sum(axis=1)

        # 해당 요일에서 이벤트가 가장 많은 시간
        preferred_hour = np.argmax(
            counts,
            axis=1
        ).astype("float64")

        # 활동 기록이 없는 요일은 결측값 처리
        preferred_hour[total == 0] = np.nan

        notification[f"preferred_hour_{name}"] = (
            pd.Series(preferred_hour).astype("Int64")
        )

        notification[f"activity_count_{name}"] = total

    # ========================================================
    # 6. 데이터 검증
    # ========================================================

    print("데이터 검증 중...")

    # 사용자 × 기준일 중복 확인
    duplicates = notification.duplicated(
        ["user_id", "reference_date"]
    ).sum()

    if duplicates != 0:
        raise AssertionError(
            f"사용자·기준일 중복 발견: {duplicates}건"
        )

    # 요일별 이벤트 수 합계
    weekday_total = notification[
        [f"activity_count_{day}" for day in WEEKDAYS]
    ].sum(axis=1)

    # 기존 전체 이벤트 수와 비교
    mismatches = (
        weekday_total != notification["event_count_28d"]
    ).sum()

    if mismatches != 0:
        raise AssertionError(
            f"28일 이벤트 수 불일치: {mismatches}건"
        )

    # ========================================================
    # 7. Parquet / CSV 저장
    # ========================================================

    notification.to_parquet(
        OUTPUT_PARQUET,
        index=False
    )

    notification.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 8. 결과 출력
    # ========================================================

    print("\n요일별 선호 시간 결측 비율:")

    for day in WEEKDAYS:

        missing = notification[
            f"preferred_hour_{day}"
        ].isna().mean()

        print(f"{day}: {missing:.2%}")

    print("\n전처리 완료!")

    print(f"전체 행 수: {len(notification):,}")
    print(f"전체 컬럼 수: {len(notification.columns)}")

    print(f"\nParquet 저장: {OUTPUT_PARQUET}")
    print(f"CSV 저장: {OUTPUT_CSV}")

    print("\n검증 통과: 사용자·기준일 중복 없음")
    print("검증 통과: 요일별 이벤트 수 합계 일치")


if __name__ == "__main__":
    main()
    