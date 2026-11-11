import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'preprocessing'))
from widget_filter import widget_exclusion_mask


class WidgetFilterTests(unittest.TestCase):
    def test_session_scope_boundary_and_mixed_activity(self):
        rows = [
            ('a', 1, '2026-08-29 23:59', 'session_start', False),
            ('a', 1, '2026-08-30', 'widget_count', True),
            ('a', 1, '2026-08-30', 'session_end', True),
            # Same session ID for another user must not contaminate classification.
            ('b', 1, '2026-08-30', 'session_start', False),
            ('b', 1, '2026-08-30', 'click_widget', False),
            ('b', 1, '2026-08-30', 'widget_count', True),
            # Real activity before cutoff also protects this session.
            ('a', 2, '2026-08-29', 'view_page', False),
            ('a', 2, '2026-08-30', 'widget_count', True),
            ('a', 2, '2026-08-30', 'session_end', False),
            ('a', -1, '2026-08-30', 'widget_count', True),
            ('a', -1, '2026-08-30', 'session_end', False),
            ('a', None, '2026-08-30', 'widget_count', True),
            ('a', None, '2026-08-30', 'session_start', False),
            ('a', 3, '2026-08-29', 'widget_count', False),
            ('a', 4, '2026-08-30', 'session_start', False),
        ]
        events = pd.DataFrame(rows, columns=['user_id', 'session_id', 'event_time', 'event_type', 'expected'])
        events.event_time = pd.to_datetime(events.event_time, format='mixed')
        self.assertEqual(widget_exclusion_mask(events, '2026-08-30').tolist(), events.expected.tolist())


if __name__ == '__main__':
    unittest.main()
