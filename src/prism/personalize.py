"""Session-derived weekday/time preference and click-based function preference."""

import argparse
import json
from pathlib import Path
import pandas as pd


def analyze(events, reference_date, cfg):
    t = pd.Timestamp(reference_date)
    t = t.tz_localize("Asia/Seoul") if t.tz is None else t.tz_convert("Asia/Seoul")
    if t != t.normalize():
        raise ValueError("Reference must be KST midnight")
    e = events.copy()
    e["time"] = pd.to_datetime(
        e.event_time_utc, utc=True, format="mixed"
    ).dt.tz_convert("Asia/Seoul")
    e = e[e.time.lt(t) & e.active_event.eq(1)].copy()
    if e.empty:
        return pd.DataFrame()
    start = t - pd.Timedelta(days=cfg["window_days"])
    valid = e[e.session_valid.eq(True) & e.device_key.notna() & e.session_id.notna()]
    sessions = valid.groupby(
        ["user_key", "device_key", "session_id"], as_index=False
    ).time.min()
    sessions = sessions[sessions.time.ge(start)].copy()
    sessions["date"] = sessions.time.dt.date
    sessions["weekday"] = sessions.time.dt.weekday
    band = cfg["time_band_hours"]
    if band not in [1, 2, 3, 4, 6, 8, 12]:
        raise ValueError("Band must divide 24")
    sessions["band"] = (sessions.time.dt.hour // band) * band
    actions = e[e.time.ge(start)].copy()
    actions["date"] = actions.time.dt.date
    # Starts/clicks only; completed callbacks are not new user actions.
    name = actions.event_type.fillna("")
    actions["function"] = None
    actions.loc[
        name.str.contains("diary") & name.str.startswith("click_"), "function"
    ] = "diary"
    actions.loc[
        name.str.contains("vocab") & name.str.startswith("click_"), "function"
    ] = "vocabulary"
    actions.loc[
        name.str.contains("pronunciation") & name.str.startswith("click_"), "function"
    ] = "pronunciation"
    rows = []

    def peak(frame):
        g = (
            frame.groupby("band")
            .agg(days=("date", "nunique"), last=("time", "max"))
            .reset_index()
        )
        return int(
            g.sort_values(
                ["days", "last", "band"], ascending=[False, False, True]
            ).iloc[0]["band"]
        )

    for user in actions.user_key.unique():
        s = sessions[sessions.user_key.eq(user)]
        f = actions[actions.user_key.eq(user) & actions.function.notna()]
        pref = (
            f.groupby("function")
            .agg(days=("date", "nunique"), count=("time", "size"), last=("time", "max"))
            .reset_index()
        )
        pref = pref[pref.days.ge(cfg["min_feature_days"])]
        # Active days first, recency second, clicks third to reduce repetition bias.
        favorite = (
            None
            if pref.empty
            else pref.sort_values(
                ["days", "last", "count", "function"],
                ascending=[False, False, False, True],
            ).iloc[0]["function"]
        )
        for weekday in range(7):
            same = s[s.weekday.eq(weekday)]
            enough = s.date.nunique() >= cfg["min_session_days"]
            source = (
                "weekday"
                if same.date.nunique() >= cfg["min_weekday_days"]
                else "overall_fallback"
            )
            eligible = bool(enough and favorite is not None)
            hour = peak(same if source == "weekday" else s) if enough else None
            template = cfg["templates"].get(favorite, {})
            rows.append(
                {
                    "user_key": user,
                    "reference_date": t.strftime("%Y-%m-%d"),
                    "window_days": cfg["window_days"],
                    "weekday_kst": weekday,
                    "time_band_start_hour": hour,
                    "time_band_hours": band,
                    "notify_hour": None if hour is None else (hour + band) % 24,
                    "notify_day_offset": (
                        None if hour is None else int(hour + band >= 24)
                    ),
                    "time_source": source if enough else "insufficient",
                    "session_support_days": s.date.nunique(),
                    "weekday_support_days": same.date.nunique(),
                    "preferred_function": favorite,
                    "eligible": eligible,
                    "reason": (
                        "sufficient_history"
                        if eligible
                        else "insufficient_sessions_or_function"
                    ),
                    "body": template.get("body") if eligible else None,
                    "route": template.get("route") if eligible else None,
                    "session_time_basis": "earliest_confirmed_event_per_valid_session",
                }
            )
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", required=True)
    p.add_argument("--reference-date", required=True)
    p.add_argument("--config", default="configs/personalization.json")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--availability",
        choices=["retrospective_snapshot", "available_at_reference"],
        default="retrospective_snapshot",
    )
    a = p.parse_args()
    columns = [
        "user_key",
        "device_key",
        "session_id",
        "session_valid",
        "active_event",
        "event_type",
        "event_time_utc",
        "server_upload_time_utc",
    ]
    e = pd.read_csv(
        a.events,
        usecols=columns,
        dtype={"user_key": "string", "device_key": "string", "session_id": "string"},
    )
    if a.availability == "available_at_reference":
        t = pd.Timestamp(a.reference_date, tz="Asia/Seoul")
        e = e[pd.to_datetime(e.server_upload_time_utc, utc=True, format="mixed").lt(t)]
    f = analyze(e, a.reference_date, json.loads(Path(a.config).read_text()))
    if f.empty:
        raise ValueError("No eligible historical activity; output not created")
    f["availability_policy"] = a.availability
    with Path(a.output).open("x") as out:
        f.to_csv(out, index=False)


if __name__ == "__main__":
    main()
