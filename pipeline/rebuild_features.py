"""Rebuild cohort/features using audited events and daily data; preserve source run."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from layout import artifact, prepare_run
from run import ROOT, TZ, sha, dump, build_features
from proxy_labels import apply_to_run
from validate_outputs import audit
from export_modeling_csv import export


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    args = parser.parse_args()
    source = args.source.resolve()
    cfg = json.loads(args.config.read_text())
    previous = json.loads(artifact(source, 'config.json').read_text())
    allowed = {'eligibility_recent_active_days', 'reference_start', 'reference_end_inclusive',
               'reference_interval_days', 'minimum_observed_history_days', 'split_dates'}
    changed = {k: {'old': previous.get(k), 'new': cfg.get(k)}
               for k in set(previous) | set(cfg) if previous.get(k) != cfg.get(k)}
    if set(changed) - allowed:
        raise ValueError('Changes outside cohort/split settings require full pipeline')
    if cfg['minimum_observed_history_days'] < 28 or cfg['reference_interval_days'] < 1 or cfg['eligibility_recent_active_days'] < 1:
        raise ValueError('Invalid cohort settings')
    manifest = json.loads(artifact(source, 'audit_manifest.json').read_text())
    print('Source audit manifest type:', type(manifest).__name__, flush=True)
    # Independently verify every reused artifact against recorded source manifest.
    expected = manifest.get('sha256', manifest.get('output_sha256', manifest.get('files', {})))
    if not expected:
        raise ValueError('Unrecognized audit manifest')
    out = ROOT / 'outputs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_cohort28')
    prepare_run(out)
    names = ['events_clean.csv.gz', 'user_daily_activity.csv.gz', 'legacy_policy.json',
             'column_dictionary.csv', 'event_mapping.csv', 'event_collection_by_version.csv',
             'daily_collection_counts.csv']
    for name in names:
        p = artifact(source, name)
        key = str(p.relative_to(source))
        recorded = expected.get(key)
        if isinstance(recorded, dict): recorded = recorded.get('sha256')
        if recorded != sha(p): raise ValueError('Source hash mismatch: ' + key)
        shutil.copy2(p, artifact(out, name))
    for p in Path(__file__).parent.glob('*.py'): shutil.copy2(p, artifact(out, p.name))
    for name in ['README.md', 'requirements.txt', 'requirements-tested.txt']:
        shutil.copy2(Path(__file__).with_name(name), artifact(out, name))
    dump(artifact(out, 'config.json'), cfg)
    report = json.loads(artifact(source, 'quality_report.json').read_text())
    report.pop('output_sha256', None)
    report['rebuild'] = {'source_manifest_sha256': sha(artifact(source, 'audit_manifest.json')),
                         'changed_settings': changed, 'reused_event_and_daily_values': True,
                         'reference_schedule_status': 'provisional_pending_team_agreement'}
    excluded = {'quality_flags','char_count','has_photo','is_first_play','upload_delay_hours',
                'activity_reason','action_kind','bookmark_action','empathy_action'}
    header = pd.read_csv(artifact(out, 'events_clean.csv.gz'), nrows=0).columns
    strings = {c: 'string' for c in ['user_key','device_key','event_key','session_id','session_id_original','version_name']}
    e = pd.read_csv(artifact(out, 'events_clean.csv.gz'), usecols=[c for c in header if c not in excluded], dtype=strings)
    for c in ['event_time_utc','server_upload_time_utc']:
        e[c] = pd.to_datetime(e[c], utc=True, format='mixed')
    e['event_time_kst'] = e.event_time_utc.dt.tz_convert(TZ)
    d = pd.read_csv(artifact(out, 'user_daily_activity.csv.gz'), dtype={'user_key':'string'})
    feats = [c for c in e if c.endswith('_count')]
    print('Rebuilding features:', len(e), 'events;', changed, flush=True)
    build_features(e, d, feats, cfg, out, report)
    dump(artifact(out, 'quality_report.json'), report)
    apply_to_run(out, cfg)
    audit(out)
    export(out)
    print('완료:', out, flush=True)


if __name__ == '__main__':
    main()
