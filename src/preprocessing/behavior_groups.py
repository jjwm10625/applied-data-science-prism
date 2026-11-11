"""Explicit, reviewable mapping for model activity.

Unknown events do not enter a group automatically. The union defines activity,
recency, labels, eligible users and notification timing throughout the pipeline.
"""
import pandas as pd

BEHAVIOR_EVENTS = {
    "entry": {"click_widget", "click_push_notification"},
    "learning": {
        "click_home.diary_write", "click_write_diary.textfield",
        "click_write_diary.submit_cta", "click_write_diary.submit_entry",
        "submitted_entry_diary", "submitted_post_diary",
        "click_feedback.post_diary", "click_feedback.submitted_post_diary",
        "write_diary.click_scan_text", "click_scan_text", "click_write_diary.scan_text",
        "click_vocabulary.voca_lookup", "click_vocab_review_btn",
        "click_vocabulary.review_btn", "click_diary_pronunciation_btn",
        "click_vocab_pronunciation_btn", "click_diary_pronunciation_btn_play",
        "click_vocab_pronunciation_btn_play",
    },
    "app_usage": {
        "[Amplitude] Screen Viewed", "pageview", "view_page", "write_diary.pageview",
        "view_home.page", "view_my_feed.page", "view_posted_diary.page",
        "view_vocabulary.page", "view_feedback.page", "view_write_diary.page",
        "viewe_profile_user", "view_profile_user", "view_feed.view_profile_user",
        "view_home.opend_diary_view", "click_home.diary_view",
        "click_feed.profile_view", "click_home.profile", "click_user_profile.profile_view",
        "click_notification.profile_view", "click_user_profile.follow",
        "click_empathy_action", "click_feed.empathy_action", "bookmark_action",
        "click_bookmark_action", "click_feedback.bookmark_action",
        "click_back", "click_back_diary", "click_back_feedback",
        "write_diary.click_back_diary", "click_write_diary.back_diary",
        "click_feedback.back_feedback", "click_dropdown", "click_write_diary.dropdown",
        "click_home.more_menu", "click_home.switch_language", "click_feed.refresh",
        "click_feedback.toggle", "click_feedback_toggle", "click_posted_diary.toggle",
        "click_vocabulary.sort_changed", "click_vocabulary.voca_sort_changed",
        "click_vocabulary.unknown_filter", "click_onboarding.skip", "click_onborading.skip",
        "click_home.streak_revive",
    },
}

GROUP_COLUMNS = [f"{group}_active" for group in BEHAVIOR_EVENTS]
EVENT_TO_GROUP = {event: group for group, events in BEHAVIOR_EVENTS.items() for event in events}
assert len(EVENT_TO_GROUP) == sum(map(len, BEHAVIOR_EVENTS.values()))


def daily_behavior_flags(events):
    """One boolean per user/KST date/group, regardless of event multiplicity."""
    frame = events[["user_id", "event_time", "event_type"]].copy()
    frame["date"] = pd.to_datetime(frame["event_time"]).dt.normalize()
    for group, names in BEHAVIOR_EVENTS.items():
        frame[f"{group}_active"] = frame["event_type"].isin(names)
    return frame.groupby(["user_id", "date"], as_index=False)[GROUP_COLUMNS].max()
