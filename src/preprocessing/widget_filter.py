"""Exclude widget counters and lifecycle events from widget-only sessions."""
import pandas as pd

SESSION_EVENTS = {"session_start", "session_end"}


def widget_exclusion_mask(events, cutoff):
    """Classify sessions over all supplied dates, then remove only after cutoff.

    User IDs scope session IDs. Missing/-1 session IDs cannot identify a session.
    Any other event, including click_widget, protects a session's lifecycle events.
    """
    widget = events["event_type"].eq("widget_count")
    lifecycle = events["event_type"].isin(SESSION_EVENTS)
    valid = events["session_id"].notna() & events["session_id"].ne(-1)
    flags = events.loc[valid, ["user_id", "session_id"]].copy()
    flags["widget"] = widget.loc[valid]
    flags["other"] = (~(widget | lifecycle)).loc[valid]
    sessions = flags.groupby(["user_id", "session_id"])[["widget", "other"]].any()
    pure = sessions.index[sessions["widget"] & ~sessions["other"]]
    keys = pd.MultiIndex.from_frame(events[["user_id", "session_id"]])
    after = events["event_time"].ge(pd.Timestamp(cutoff))
    return after & (widget | (valid & lifecycle & keys.isin(pure)))
