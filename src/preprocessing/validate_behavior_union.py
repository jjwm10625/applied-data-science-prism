"""Exhaustively validate eligibility, union/group days, recency and labels."""
import numpy as np
import pandas as pd
from behavior_groups import BEHAVIOR_EVENTS, EVENT_TO_GROUP


def main():
    events = pd.read_parquet('processed_kst/clean_events.parquet')
    features = pd.read_parquet('processed_kst/churn_features.parquet')
    assert events.event_type.isin(EVENT_TO_GROUP).all()
    events['date'] = events.event_time.dt.normalize()
    by_user = {uid: part for uid, part in events.groupby('user_id')}
    by_features = {uid: part for uid, part in features.groupby('user_id')}
    refs = np.arange(np.datetime64('2025-11-05'), np.datetime64('2026-10-20'))
    checked = 0
    for uid, event in by_user.items():
        dates = np.sort(event.date.unique()).astype('datetime64[D]')
        end = np.searchsorted(dates, refs)
        eligible = (end - np.searchsorted(dates, refs - np.timedelta64(28, 'D'))) > 0
        expected_refs = refs[eligible]
        if uid not in by_features:
            assert len(expected_refs) == 0, uid
            continue
        f = by_features[uid].sort_values('reference_date')
        actual_refs = f.reference_date.to_numpy(dtype='datetime64[D]')
        np.testing.assert_array_equal(actual_refs, expected_refs, err_msg=uid)
        end = np.searchsorted(dates, actual_refs)
        for window in [7, 14, 21, 28]:
            start = actual_refs - np.timedelta64(window, 'D')
            expected = end - np.searchsorted(dates, start)
            np.testing.assert_array_equal(f[f'active_days_{window}d'], expected)
            for group, names in BEHAVIOR_EVENTS.items():
                group_dates = np.sort(event.loc[event.event_type.isin(names), 'date'].unique()).astype('datetime64[D]')
                expected = np.searchsorted(group_dates, actual_refs) - np.searchsorted(group_dates, start)
                np.testing.assert_array_equal(f[f'{group}_days_{window}d'], expected)
        assert (end > 0).all()
        expected_recency = (actual_refs - dates[end - 1]).astype(int)
        np.testing.assert_array_equal(f.recency_days, expected_recency)
        expected_label = (np.searchsorted(dates, actual_refs + np.timedelta64(7, 'D'), side='right') ==
                          np.searchsorted(dates, actual_refs, side='right')).astype(int)
        np.testing.assert_array_equal(f.churn_label, expected_label)
        checked += len(f)
    assert checked == len(features)
    print(f'PASS: all {checked:,} rows, eligibility, union/group activity days, recency and labels')


if __name__ == '__main__':
    main()
