"""Explicit proxy target; preserve strict labels and all pre-T features."""
import json
import numpy as np
import pandas as pd
from layout import artifact

TARGET = 'label_proxy_churn_7d'
PROXY_COLUMNS = [TARGET, 'label_proxy_status', 'label_proxy_reason', 'label_proxy_assumption_applied']
STATEMENT = ('과거 데이터에서는 향후 7일간 관측 가능한 앱 활동이 없는 상태를 예측한다. '
             '수집 안정성을 가정한 대리 라벨을 사용하며, 실제 미접속과의 차이를 한계로 보고한다.')


def apply_proxy_labels(frame, cfg):
    """Use audited strict evidence; never reinterpret ambiguous records as inactivity."""
    from run import midnight, covered
    policy = cfg.get('proxy_label_policy', {})
    if not policy.get('enabled', False):
        raise ValueError('Proxy assumption must be explicitly enabled in configuration')
    intervals = policy.get('assumed_collection_intervals', [])
    result = frame.copy()
    decisions = []
    for r in frame.itertuples():
        t = midnight(r.reference_date)
        end = t + pd.Timedelta(days=7)
        if t < midnight(cfg['analysis_start']) or end > midnight(cfg['analysis_end_exclusive']):
            decision = (np.nan, 'unknown', 'future_window_incomplete', False)
        elif cfg.get('label_upload_deadline_utc') and pd.Timestamp(cfg['label_upload_deadline_utc']).tz_convert('Asia/Seoul') < end:
            decision = (np.nan, 'unknown', 'upload_snapshot_before_window_end', False)
        elif any(midnight(a) < end and midnight(b) > t for a, b in cfg['suspect_intervals']):
            decision = (np.nan, 'unknown', 'suspect_collection_interval', False)
        elif not covered(t, end, intervals):
            decision = (np.nan, 'unknown', 'outside_proxy_assumption_scope', False)
        elif pd.notna(r.label_churn_7d) and r.label_churn_7d == 0:
            decision = (0, 'observed_activity', 'confirmed_event_in_future_window', False)
        elif pd.notna(r.label_event_min_utc) or pd.notna(r.label_event_max_utc):
            decision = (np.nan, 'unknown', 'unconfirmed_records_in_future_window', False)
        elif r.label_reason in {'collection_reliability_unverified', 'complete_verified_window_without_records'}:
            assumed = pd.isna(r.label_churn_7d)
            decision = (1, 'proxy_no_observed_activity',
                        'no_records_under_collection_stability_assumption' if assumed else 'complete_verified_window_without_records', assumed)
        else:
            decision = (np.nan, 'unknown', 'strict_evidence_not_eligible_for_proxy', False)
        decisions.append(decision)
    result[PROXY_COLUMNS] = pd.DataFrame(decisions, index=result.index)
    result[TARGET] = result[TARGET].astype('float64')
    return result


def apply_to_run(out, cfg):
    """Refresh only target/subset/report artifacts in a new or newly generated run."""
    from run import dump, sha
    tables = {}
    old_hashes = {}
    common = None
    for w in [7, 14, 21, 28]:
        path = artifact(out, f'features_{w}d_all.csv.gz')
        old_hashes[str(path.relative_to(out))] = sha(path)
        before = pd.read_csv(path, float_precision='round_trip')
        # A current run contains the unchanged strict evidence, so a separate old run is unnecessary.
        before = before.drop(columns=[c for c in PROXY_COLUMNS if c in before])
        after = apply_proxy_labels(before, cfg)
        pd.testing.assert_frame_equal(before, after[before.columns], check_exact=True)
        keys = after[['user_key', 'reference_date', 'label_churn_7d', 'label_status', 'label_reason', 'split', *PROXY_COLUMNS]]
        if common is None:
            common = keys.copy()
        else:
            pd.testing.assert_frame_equal(common, keys, check_exact=True)
        after.to_csv(path, index=False)
        eligible = after[TARGET].notna() & after.split.ne('purged_label_overlap')
        after[eligible].to_csv(artifact(out, f'features_{w}d_labeled.csv.gz'), index=False)
        after[after.label_proxy_reason.eq('future_window_incomplete')].to_csv(artifact(out, f'features_{w}d_inference.csv.gz'), index=False)
        if cfg['split_dates']:
            for split in ['train', 'validation', 'test']:
                after[eligible & after.split.eq(split)].to_csv(artifact(out, f'features_{w}d_{split}.csv.gz'), index=False)
        # Serialized round-trip must preserve every original value, including model inputs.
        reread = pd.read_csv(path, float_precision='round_trip')
        pd.testing.assert_frame_equal(before, reread[before.columns], check_exact=True)
        tables[w] = after
    f = tables[7].copy()
    f['excluded'] = f[TARGET].isna()
    f['reference_month'] = f.reference_date.str[:7]
    f['history_group'] = pd.cut(f.observed_history_days, [0, 60, 180, np.inf], labels=['28_to_60', '61_to_180', 'over_180'])
    for dim in ['platform_before_T', 'reference_month', 'history_group', 'user_key']:
        g = f.groupby(dim, observed=True).agg(rows=('user_key', 'size'), excluded=('excluded', 'sum'))
        g['excluded_ratio'] = g.excluded / g.rows
        g.to_csv(artifact(out, f'proxy_label_exclusion_by_{dim}.csv.gz'))
    transitions = f.assign(strict=f.label_churn_7d.fillna('unknown'), proxy=f[TARGET].fillna('unknown'))
    transitions.groupby(['strict', 'proxy'], dropna=False).size().rename('rows').to_csv(artifact(out, 'label_policy_transitions.csv'))
    def counts(series):
        return {'0': int(series.eq(0).sum()), '1': int(series.eq(1).sum()), 'unknown': int(series.isna().sum())}
    report = {
        'statement': policy_statement(cfg), 'modeling_target': TARGET,
        'assumed_collection_intervals': cfg['proxy_label_policy']['assumed_collection_intervals'],
        'assumption_is_verified_fact': False, 'strict_labels_preserved': True,
        'features_and_original_columns_unchanged': True, 'same_samples_labels_splits_across_windows': True,
        'rows_per_window': len(f), 'user_keys': int(f.user_key.nunique()),
        'strict_label_counts': counts(f.label_churn_7d), 'proxy_label_counts': counts(f[TARGET]),
        'proxy_reasons': f.label_proxy_reason.value_counts().to_dict(),
        'proxy_unknown_ratio': float(f[TARGET].isna().mean()),
        'modeling_eligible_rows_per_window': int((f[TARGET].notna() & f.split.ne('purged_label_overlap')).sum()),
        'split_configured': cfg['split_dates'] is not None,
        'pre_update_feature_sha256': old_hashes,
        'scope': 'Existing cohort and legacy v2 event rule on iOS and Android; no platform/version completeness claim.',
        'late_upload_policy': cfg['late_upload_policy'],
        'limitations': ['Actual inactivity and telemetry absence may differ.',
                       'Ambiguous records remain unknown.',
                       'Retrospective snapshot does not prove point-in-time availability.',
                       'No deployment/version evidence was added by this relabeling.'],
    }
    dump(artifact(out, 'proxy_label_report.json'), report)
    roles = json.loads(artifact(out, 'feature_roles.json').read_text())
    roles.update(modeling_target=TARGET, strict_reference_target='label_churn_7d', target_definition=policy_statement(cfg))
    roles['management_and_quality'] = list(dict.fromkeys([*roles['management_and_quality'], *PROXY_COLUMNS]))
    dump(artifact(out, 'feature_roles.json'), roles)
    dictionary = pd.read_csv(artifact(out, 'column_dictionary.csv'))
    dictionary = dictionary[~(dictionary.table.eq('features') & dictionary.column.isin(PROXY_COLUMNS))]
    meanings = {
        TARGET: '대리 정답: 0 미래 접속 확인, 1 수집 안정성 가정하의 미래 7일 기록 없음, 결측 판정 보류. 실제 미접속 확정 아님',
        'label_proxy_status': '대리 라벨 판정 상태; 모델 입력 금지',
        'label_proxy_reason': '대리 라벨 판정 또는 제외 근거; 모델 입력 금지',
        'label_proxy_assumption_applied': '엄격 라벨 결측을 수집 안정성 가정으로 대리 라벨 1로 판정했는지; 모델 입력 금지',
    }
    extra = pd.DataFrame([{'table': 'features', 'column': c, 'dtype': str(f[c].dtype), 'description': desc} for c, desc in meanings.items()])
    pd.concat([dictionary, extra], ignore_index=True).to_csv(artifact(out, 'column_dictionary.csv'), index=False)
    quality = json.loads(artifact(out, 'quality_report.json').read_text())
    quality['proxy_labels'] = report
    quality['features']['modeling_target'] = TARGET
    quality['features']['strict_label_counts_note'] = 'Existing label_counts/label_reasons describe preserved strict target, not modeling target.'
    dump(artifact(out, 'quality_report.json'), quality)
    artifact(out, 'quality_report.sha256').write_text(sha(artifact(out, 'quality_report.json')) + '  quality_report.json\n')
    return report


def policy_statement(cfg):
    return cfg['proxy_label_policy'].get('statement', STATEMENT)
