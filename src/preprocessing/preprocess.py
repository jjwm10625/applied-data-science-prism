import gzip
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, date, timezone, timedelta

import pandas as pd

from widget_filter import widget_exclusion_mask

# ============================================================
# 1. 기본 설정
# ============================================================

DATA_DIR = Path("export_data/734177")

# 기존 processed 폴더를 덮어쓰지 않음
OUTPUT_DIR = Path("processed_kst")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 분석 기간: KST 기준
START_DATE = date(2025, 10, 8)
END_DATE = date(2026, 10, 26)

# KST 2026-08-30부터 widget_count 및 위젯 전용 세션의 시작/종료 제외
WIDGET_EXCLUSION_START = date(2026, 8, 30)

# 이상 데이터로 확인된 amplitude_id는 전체 기간 제외
EXCLUDED_AMPLITUDE_IDS = {
    "1580917700694",
    "1477164074673",
    "1688838832116",
    "1644032753256",
    "1625616709263",
    "1374897089120",
}

UTC = timezone.utc
KST = timezone(timedelta(hours=9))

# ============================================================
# 2. 기능별 이벤트 분류
# ============================================================

FEATURE_EVENTS = {
    "diary": {
        "submitted_entry_diary",
        "submitted_post_diary",
        "click_write_diary.submit_entry",
    },
    "vocabulary": {
        "view_vocabulary.page",
        "click_vocab_review_btn",
        "click_vocabulary.review_btn",
        "click_vocabulary.voca_lookup",
    },
    "pronunciation": {
        "click_diary_pronunciation_btn",
        "click_vocab_pronunciation_btn",
    },
    "social": {
        "click_empathy_action",
        "click_feed.empathy_action",
        "click_user_profile.follow",
    },
}

# ============================================================
# 3. 데이터 저장 구조
# ============================================================

daily = defaultdict(lambda: {
    "event_count": 0,
    "sessions": set(),
    "diary_count": 0,
    "vocabulary_count": 0,
    "pronunciation_count": 0,
    "social_count": 0,
})

seen_uuid = set()
clean_records = []

files = sorted(DATA_DIR.rglob("*.json.gz"))

if not files:
    raise FileNotFoundError(
        f"원본 파일을 찾을 수 없습니다: {DATA_DIR.resolve()}"
    )

print("=== KST 기준 전처리 시작 ===")
print("원본 파일:", len(files))
print("분석 기간:", START_DATE, "~", END_DATE)
print("시간대: UTC → Asia/Seoul (KST)")

# ============================================================
# 4. 원본 이벤트 읽기 및 정제
# ============================================================

for i, filepath in enumerate(files, 1):

    with gzip.open(filepath, "rt", encoding="utf-8") as f:

        for line in f:

            if not line.strip():
                continue

            event = json.loads(line)

            user_id = event.get("amplitude_id")
            event_time = event.get("event_time")
            event_type = event.get("event_type")
            uuid = event.get("uuid")

            # 필수 정보가 없는 이벤트 제외
            if user_id is None or not event_time:
                continue

            if str(user_id) in EXCLUDED_AMPLITUDE_IDS:
                continue

            # ------------------------------------------------
            # UTC → KST 변환
            # ------------------------------------------------

            dt_utc = datetime.fromisoformat(event_time)

            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=UTC)
            else:
                dt_utc = dt_utc.astimezone(UTC)

            dt_kst = dt_utc.astimezone(KST)

            # 한국 날짜 기준
            day = dt_kst.date()

            # ------------------------------------------------
            # 분석 기간 필터링
            # ------------------------------------------------

            if not START_DATE <= day <= END_DATE:
                continue

            # ------------------------------------------------
            # 중복 이벤트 제거
            # ------------------------------------------------

            if uuid is not None:
                if uuid in seen_uuid:
                    continue

                seen_uuid.add(uuid)

            # ------------------------------------------------
            # 사용자 및 세션 정보
            # ------------------------------------------------

            user_id = str(user_id)
            session_id = event.get("session_id")

            # ------------------------------------------------
            # 정제 이벤트 저장
            # ------------------------------------------------

            clean_records.append({
                "user_id": user_id,

                # KST 시간 (시간대 정보 없는 datetime으로 저장)
                "event_time": dt_kst.replace(tzinfo=None),

                # 원본 UTC 시간 보존
                "event_time_utc": dt_utc.replace(tzinfo=None),

                # KST 날짜
                "event_date": day,

                "event_type": event_type,
                "session_id": session_id,
                "uuid": uuid,
            })

    if i % 500 == 0 or i == len(files):
        print(f"처리 완료: {i:,}/{len(files):,}")

# ============================================================
# 5. 정제 이벤트 저장
# ============================================================

if not clean_records:
    raise ValueError("분석 기간에 해당하는 이벤트가 없습니다.")

clean_df = pd.DataFrame(clean_records)

# 모든 관측 날짜의 이벤트로 세션을 판별한 후 날짜 조건을 적용한다.
excluded = widget_exclusion_mask(clean_df, WIDGET_EXCLUSION_START)
excluded_widget_counts = clean_df.loc[excluded, "event_type"].value_counts().to_dict()
clean_df = clean_df.loc[~excluded].copy()
del clean_records

# 필터링 완료 후 집계하여 세션 수, 활동일, 라벨도 동일 기준을 사용한다.
for event in clean_df.itertuples(index=False):
    row = daily[(event.user_id, event.event_date)]
    row["event_count"] += 1
    if pd.notna(event.session_id) and event.session_id != -1:
        row["sessions"].add(event.session_id)
    for feature, event_names in FEATURE_EVENTS.items():
        if event.event_type in event_names:
            row[f"{feature}_count"] += 1

clean_df = clean_df.sort_values(
    ["user_id", "event_time"]
).reset_index(drop=True)

clean_df.to_parquet(
    OUTPUT_DIR / "clean_events.parquet",
    index=False
)

# ============================================================
# 6. 사용자별 일간 활동 데이터 생성
# ============================================================

daily_records = []

for (user_id, day), row in daily.items():

    daily_records.append({
        "user_id": user_id,
        "date": day,
        "event_count": row["event_count"],
        "session_count": len(row["sessions"]),
        "diary_count": row["diary_count"],
        "vocabulary_count": row["vocabulary_count"],
        "pronunciation_count": row["pronunciation_count"],
        "social_count": row["social_count"],
    })

daily_df = pd.DataFrame(daily_records)

daily_df = daily_df.sort_values(
    ["user_id", "date"]
).reset_index(drop=True)

daily_df.to_parquet(
    OUTPUT_DIR / "daily_activity.parquet",
    index=False
)

# ============================================================
# 7. 결과 검증
# ============================================================

assert clean_df["user_id"].notna().all()
assert clean_df["event_time"].notna().all()

assert not daily_df.duplicated(
    ["user_id", "date"]
).any()

assert (
    daily_df["event_count"].sum() == len(clean_df)
), "일간 이벤트 합계가 정제 이벤트 수와 다릅니다."

# UTC와 KST 시간 차이 확인
time_diff = (
    clean_df["event_time"] - clean_df["event_time_utc"]
)

assert (
    time_diff == pd.Timedelta(hours=9)
).all(), "UTC → KST 변환 오류"

# ============================================================
# 8. 최종 결과 출력
# ============================================================

print("\n=== KST 기준 전처리 완료 ===")

print("정제 이벤트:", f"{len(clean_df):,}")
print("전체 기간 제외 amplitude_id:", sorted(EXCLUDED_AMPLITUDE_IDS))
print("위젯 이벤트 제외 시작일(KST):", WIDGET_EXCLUSION_START)
print("제외한 위젯 이벤트:", dict(excluded_widget_counts))
print("사용자 ID:", f"{clean_df['user_id'].nunique():,}")
print("일간 활동 데이터:", f"{len(daily_df):,}")

print(
    "최초 이벤트(KST):",
    clean_df["event_time"].min()
)

print(
    "마지막 이벤트(KST):",
    clean_df["event_time"].max()
)

print("\n=== 시간대별 이벤트 수 (KST) ===")

print(
    clean_df["event_time"]
    .dt.hour
    .value_counts()
    .sort_index()
    .to_string()
)

print("\n=== 생성 파일 ===")
print((OUTPUT_DIR / "clean_events.parquet").resolve())
print((OUTPUT_DIR / "daily_activity.parquet").resolve())

print("\n검증 결과: PASS")
