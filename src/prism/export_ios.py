"""Export only an explicitly allowlisted demo user; app supplies live state."""

import argparse
import json
from pathlib import Path
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profiles", required=True)
    p.add_argument("--predictions", required=True)
    p.add_argument("--user-key", required=True)
    p.add_argument("--demo-id", required=True)
    p.add_argument("--reference-date", required=True)
    p.add_argument("--expires-at", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    profiles = pd.read_csv(a.profiles)
    predictions = pd.read_csv(a.predictions)
    profiles = profiles[
        profiles.user_key.eq(a.user_key)
        & profiles.reference_date.eq(a.reference_date)
        & profiles.eligible.eq(True)
    ]
    prediction = predictions[
        predictions.user_key.eq(a.user_key)
        & predictions.reference_date.eq(a.reference_date)
    ]
    if len(prediction) != 1 or profiles.empty:
        raise ValueError("Choose exactly one prediction/model and an eligible profile")
    expiry = pd.Timestamp(a.expires_at)
    if expiry.tz is None:
        raise ValueError("Expiry requires timezone")
    ref = pd.Timestamp(a.reference_date, tz="Asia/Seoul")
    if expiry <= ref:
        raise ValueError("Expiry must follow reference date")
    prob = float(prediction.iloc[0].probability)
    threshold = float(prediction.iloc[0].threshold)
    if not 0 <= prob <= 1 or not 0 <= threshold <= 1:
        raise ValueError("Invalid probability")
    schedules = []
    for r in profiles.itertuples():
        if r.route not in ["diary_write", "vocabulary_review", "pronunciation"]:
            raise ValueError("Unknown route")
        schedules.append(
            {
                "weekdayKST": int(r.weekday_kst),
                "notifyHour": int(r.notify_hour),
                "notifyDayOffset": int(r.notify_day_offset),
                "bandStartHour": int(r.time_band_start_hour),
                "bandHours": int(r.time_band_hours),
                "body": r.body,
                "route": r.route,
            }
        )
    payload = {
        "schemaVersion": 1,
        "demoUserID": a.demo_id,
        "referenceDate": a.reference_date,
        "expiresAt": expiry.isoformat(),
        "timezone": "Asia/Seoul",
        "churnProbability": prob,
        "threshold": threshold,
        "isRisk": prob >= threshold,
        "target": "observed_activity_proxy_7d",
        "schedules": schedules,
    }
    with Path(a.output).open("x") as out:
        json.dump(payload, out, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
