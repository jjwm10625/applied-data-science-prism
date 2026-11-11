import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'preprocessing'))
from behavior_groups import daily_behavior_flags


class BehaviorGroupTests(unittest.TestCase):
    def test_distinct_days_multiple_groups_and_automatic_events(self):
        events = pd.DataFrame([
            ('a', '2026-09-01 10:00', 'click_widget'),
            ('a', '2026-09-01 10:01', 'click_push_notification'),
            ('a', '2026-09-01 10:02', 'view_page'),
            ('a', '2026-09-01 10:03', 'click_diary_pronunciation_btn'),
            ('a', '2026-09-01 10:04', 'click_diary_pronunciation_btn_play'),
            ('a', '2026-09-02 10:00', 'session_start'),
            ('a', '2026-09-02 10:01', 'widget_count'),
            ('a', '2026-09-02 10:02', 'new_unknown_event'),
            ('b', '2026-09-01 10:00', 'click_notification.profile_view'),
        ], columns=['user_id', 'event_time', 'event_type'])
        result = daily_behavior_flags(events).set_index(['user_id', 'date'])
        self.assertEqual(result.loc[('a', pd.Timestamp('2026-09-01'))].tolist(), [True, True, True])
        self.assertFalse(result.loc[('a', pd.Timestamp('2026-09-02'))].any())
        self.assertEqual(result.loc[('b', pd.Timestamp('2026-09-01'))].tolist(), [False, False, True])


if __name__ == '__main__':
    unittest.main()
