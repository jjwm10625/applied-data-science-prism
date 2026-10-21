"""HiLingual preprocessing: pandas/NumPy; reuse established anonymized identities.
Run from any directory: python pipeline/run.py [--config PATH]
"""
from __future__ import annotations
import argparse, collections, gzip, hashlib, hmac, io, json, platform, shutil, sqlite3, zipfile
from datetime import datetime, timezone
from pathlib import Path
from layout import artifact, prepare_run
import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
TZ = 'Asia/Seoul'

def select(conditions, choices, default):
    return np.select([np.asarray(pd.Series(c).fillna(False), dtype=bool) for c in conditions], choices, default=default)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def midnight(value):
    return pd.Timestamp(value, tz=TZ)


def covered(start, end, intervals):
    """All calendar dates in half-open interval must be explicitly certified."""
    days = pd.date_range(start, end, inclusive='left', freq='D')
    return bool(len(days)) and all(any(midnight(a) <= d < midnight(b) for a,b in intervals) for d in days)


def label_decision(t, end, active, uncertain, cfg):
    if t < midnight(cfg['analysis_start']) or end > midnight(cfg['analysis_end_exclusive']):
        return np.nan, 'unknown', 'future_window_incomplete'
    if cfg.get('label_upload_deadline_utc') and pd.Timestamp(cfg['label_upload_deadline_utc']).tz_convert(TZ) < end:
        return np.nan, 'unknown', 'upload_snapshot_before_window_end'
    if active > 0:
        return 0, 'confirmed_activity', 'confirmed_event_in_future_window'
    if uncertain > 0:
        return np.nan, 'unknown', 'unconfirmed_records_in_future_window'
    suspect = any(midnight(a) < end and midnight(b) > t for a,b in cfg['suspect_intervals'])
    if suspect or not covered(t, end, cfg['verified_collection_intervals']):
        return np.nan, 'unknown', 'collection_reliability_unverified'
    return 1, 'confirmed_no_observed_activity', 'complete_verified_window_without_records'


def assign_split(frame, cfg):
    dates = cfg['split_dates']
    result = pd.Series('not_configured', index=frame.index)
    if dates is None: return result
    v, te = midnight(dates['validation_start']), midnight(dates['test_start'])
    if v >= te: raise ValueError('validation_start must precede test_start')
    t = pd.to_datetime(frame.reference_date).dt.tz_localize(TZ)
    result[:] = select([t < v, t < te], ['train', 'validation'], default='test')
    purge = ((t < v) & (t + pd.Timedelta(days=7) > v)) | ((t >= v) & (t < te) & (t + pd.Timedelta(days=7) > te))
    result[purge] = 'purged_label_overlap'
    return result


def extract_extra(db, paths, secret, report):
    db.execute('CREATE TABLE extra(event_key TEXT PRIMARY KEY, server_upload_time_utc TEXT, bookmark_action TEXT, empathy_action TEXT)')
    counts = collections.Counter(); batch = []
    for path in paths:
        print('원본 필요 속성 추출:', path.name, flush=True)
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(('.json.gz', '.json', '.jsonl')): continue
                with z.open(name) as raw:
                    stream = gzip.GzipFile(fileobj=raw) if name.endswith('.gz') else raw
                    with io.TextIOWrapper(stream, encoding='utf-8') as f:
                        for line in f:
                            if not line.strip(): continue
                            r = json.loads(line); counts['raw_rows'] += 1
                            if not r.get('uuid'): raise ValueError('Missing raw UUID: enrichment requires explicit conflict handling')
                            key = hmac.new(secret, f"event:{r.get('app')}:{r['uuid']}".encode(), hashlib.sha256).hexdigest()
                            props = r.get('event_properties') or {}
                            actions = []
                            for prop in ['bookmark_action', 'empathy_action']:
                                val = props.get(prop) if isinstance(props, dict) else None
                                safe = str(val).lower() if str(val).lower() in {'add', 'remove'} else ''
                                if val is not None and not safe: counts[prop + '_unsupported'] += 1
                                actions.append(safe)
                            batch.append((key, r.get('server_upload_time') or '', *actions))
                            if len(batch) >= 10000:
                                db.executemany('INSERT INTO extra VALUES (?,?,?,?)', batch); batch.clear()
        db.commit()
    if batch: db.executemany('INSERT INTO extra VALUES (?,?,?,?)', batch)
    db.commit(); report['raw_enrichment'] = dict(counts)


def clean_events(cfg, out, policy, mapping, report, db):
    parts = []; stats = collections.Counter(); event_keys = set()
    feature_map = policy['feature_event_mapping']
    allowed = set(policy['activity_policy']['screen_events'] + policy['activity_policy']['additional_active_events'])
    dest = artifact(out, 'events_clean.csv.gz')
    usecols = ['user_key','device_key','event_key','event_type_original','event_type','event_time_utc',
               'session_id','platform','version_name','char_count','has_photo','is_first_play','quality_flags']
    with gzip.open(dest, 'wt', encoding='utf-8', newline='') as target:
        for c in pd.read_csv(ROOT / cfg['clean_input'], usecols=usecols, dtype='string', chunksize=cfg['chunk_size']):
            stats['input_rows'] += len(c)
            for col in c: stats['input_missing_' + col] += int(c[col].isna().sum())
            if c.event_key.isna().any() or c.event_key.duplicated().any() or any(k in event_keys for k in c.event_key):
                raise ValueError('Missing/conflicting event keys: inspect before joining raw properties')
            event_keys.update(c.event_key)
            db.execute('DROP TABLE IF EXISTS requested')
            db.execute('CREATE TEMP TABLE requested(event_key TEXT PRIMARY KEY)')
            db.executemany('INSERT INTO requested VALUES (?)', ((x,) for x in c.event_key))
            extra = pd.read_sql_query('SELECT extra.* FROM extra JOIN requested USING(event_key)', db)
            c = c.merge(extra, on='event_key', how='left', validate='one_to_one', indicator=True)
            if not c['_merge'].eq('both').all(): raise AssertionError('Raw enrichment unmatched')
            c = c.drop(columns='_merge')
            standardized = c.event_type_original.replace(mapping)
            stats['mapping_mismatches'] += int((standardized != c.event_type).sum())
            c['event_type'] = standardized
            c['event_time_utc'] = pd.to_datetime(c.event_time_utc, utc=True, errors='coerce', format='mixed')
            c['server_upload_time_utc'] = pd.to_datetime(c.server_upload_time_utc, utc=True, errors='coerce', format='mixed')
            c['event_time_kst'] = c.event_time_utc.dt.tz_convert(TZ)
            c['date_kst'] = c.event_time_kst.dt.strftime('%Y-%m-%d')
            c['weekday_kst'] = c.event_time_kst.dt.weekday.astype('Int8')
            c['hour_kst'] = c.event_time_kst.dt.hour.astype('Int8')
            c['upload_delay_hours'] = (c.server_upload_time_utc - c.event_time_utc).dt.total_seconds() / 3600
            for flag, mask in {'invalid_event_time':c.event_time_utc.isna(), 'missing_user':c.user_key.isna(),
                               'missing_upload_time':c.server_upload_time_utc.isna(), 'negative_upload_delay':c.upload_delay_hours.lt(0)}.items():
                stats[flag] += int(mask.sum())
                c['quality_flags'] = c.quality_flags.fillna('') + np.where(mask, '|' + flag, '')
            old_char = c.char_count
            c['char_count'] = pd.to_numeric(c.char_count, errors='coerce')
            stats['invalid_numeric_char_count'] += int((old_char.notna() & c.char_count.isna()).sum())
            stats['negative_char_count'] += int(c.char_count.lt(0).sum())
            c.loc[c.char_count.lt(0), 'char_count'] = np.nan
            for col in ['has_photo','is_first_play']:
                stats['invalid_boolean_' + col] += int((c[col].notna() & ~c[col].str.lower().isin(['true','false','1','0'])).sum())
                c[col] = c[col].str.lower().map({'true':True, 'false':False,'1':True,'0':False}).astype('boolean')
            # Preserve session strings exactly; accept only positive integers and a known device.
            valid = c.session_id.str.fullmatch(r'[0-9]+').fillna(False) & c.session_id.str.contains(r'[1-9]').fillna(False) & c.device_key.notna()
            c['session_id_original'] = c.session_id
            c['session_valid'] = valid
            c['session_id'] = c.session_id.str.lstrip('0').where(valid)
            c['active_event'] = (c.event_type.isin(allowed) | (c.event_type.str.startswith('click_') & ~c.event_type.isin(policy['activity_policy']['excluded_clicks']))).astype('int8')
            c['activity_status'] = np.where(c.active_event.eq(1), 'confirmed_activity', 'unconfirmed_record')
            c['activity_reason'] = select([c.active_event.eq(1),c.event_type.isin(['session_start','session_end']),c.event_type.str.contains('widget')], ['legacy_v2_activity_rule','session_record_only','widget_scope_unverified'], default='not_in_activity_rule')
            c['action_kind'] = select([c.event_type.str.startswith('submitted_'),c.event_type.str.startswith('click_'),c.event_type.isin(allowed)],['completion','click','screen_or_action'],default='other')
            for prop in ['bookmark_action','empathy_action']:
                c[prop] = c[prop].replace('', 'unknown')
            c['behavior_category'] = select([c.event_type.str.contains('bookmark'),c.event_type.str.contains('empathy'),c.event_type.str.contains('pronunciation'),c.event_type.str.contains('vocab'),c.event_type.str.contains('diary'),c.event_type.str.contains('push')],['bookmark','empathy','pronunciation','vocabulary','diary','push'], default='other')
            for feat, events in feature_map.items(): c[feat] = c.event_type.isin(events).astype('int8')
            for kind in ['bookmark','empathy']:
                for action in ['add','remove','unknown']:
                    c[f'{kind}_{action}_count'] = (c.behavior_category.eq(kind) & c[kind+'_action'].eq(action)).astype('int8')
            c.to_csv(target,index=False,header=not parts)
            # Retain only aggregation fields in memory; free text properties are never exported.
            parts.append(c.drop(columns=['quality_flags','char_count','has_photo','is_first_play','upload_delay_hours','activity_reason','action_kind','bookmark_action','empathy_action']))
            print('정제 행:',stats['input_rows'],flush=True)
    e = pd.concat(parts,ignore_index=True)
    report['cleaning'] = dict(stats)
    report['cleaning']['output_rows'] = len(e)
    report['cleaning']['user_keys'] = e.user_key.nunique()
    report['cleaning']['duplicate_event_keys'] = len(e)-len(event_keys)
    return e


def daily_aggregate(e, cfg, out, report):
    feats = [x for x in e if x.endswith('_count')]
    keys = ['user_key','date_kst']
    valid = e.dropna(subset=keys)
    g = valid.groupby(keys,observed=True)
    d = g.agg(total_event_count=('event_type','size'),active_event_count=('active_event','sum'),
              first_event_time_utc=('event_time_utc','min'),last_event_time_utc=('event_time_utc','max')).join(g[feats].sum())
    a = valid[valid.active_event.eq(1)]
    sessions = a[a.session_valid].drop_duplicates(keys+['device_key','session_id']).groupby(keys).size()
    d['session_count'] = sessions.reindex(d.index,fill_value=0)
    d['active_flag'] = d.active_event_count.gt(0).astype('int8')
    d['activity_status'] = np.where(d.active_flag.eq(1),'confirmed_activity','unconfirmed_record')
    reasons = valid.groupby(keys).activity_status.agg(lambda x: 'legacy_v2_activity_rule' if 'confirmed_activity' in x.values else 'records_without_confirmed_activity')
    d['activity_reason'] = reasons
    d['last_active_time_utc'] = a.groupby(keys).event_time_utc.max()
    d['unconfirmed_event_count'] = d.total_event_count-d.active_event_count
    d['collection_status'] = 'unverified'
    d = d.reset_index()
    old = pd.read_csv(ROOT/cfg['daily_input'],dtype={'user_key':'string','date_kst':'string'})
    comparison = old.merge(d,on=keys,how='outer',indicator=True,suffixes=('_old','_new'),validate='one_to_one')
    cols = [x for x in old if x not in keys]
    mismatches = {x:int(comparison[x+'_old'].ne(comparison[x+'_new']).sum()) for x in cols}
    report['daily_comparison'] = {'old_rows':len(old),'new_rows':len(d),'unmatched_rows':int(comparison['_merge'].ne('both').sum()),'column_mismatch_counts':mismatches,
                                 'confirmed_days':int(d.active_flag.sum()),'unconfirmed_days':int(d.active_flag.eq(0).sum())}
    if any(mismatches.values()) or report['daily_comparison']['unmatched_rows']: raise AssertionError('Unexpected legacy daily differences')
    d.to_csv(artifact(out, 'user_daily_activity.csv.gz'),index=False)
    return d, feats


def build_features(e, d, feats, cfg, out, report):
    days = d.copy(); days['day'] = pd.to_datetime(days.date_kst).dt.tz_localize(TZ)
    ev = e.dropna(subset=['user_key','event_time_utc']).sort_values('event_time_utc')
    first = ev.groupby('user_key').event_time_kst.min().dt.normalize()
    sessions = ev[ev.active_event.eq(1) & ev.session_valid][['user_key','device_key','session_id','event_time_kst']]
    rows = {w:[] for w in cfg['windows_days']}; profiles = []
    refs = pd.date_range(cfg['reference_start'],cfg['reference_end_inclusive'],freq=f"{cfg['reference_interval_days']}D",tz=TZ)
    max_used_checks = 0; label_checks = 0
    for t in refs:
        print('Feature 기준일:',t.date(),flush=True)
        prior = days[days.day < t]
        if cfg['late_upload_policy'] == 'available_at_reference':
            pe = ev[(ev.event_time_kst < t) & (ev.server_upload_time_utc < t)]
            recent = pe[(pe.event_time_kst >= t-pd.Timedelta(days=cfg['eligibility_recent_active_days'])) & pe.active_event.eq(1)].user_key.unique()
            first_available = pe.groupby('user_key').event_time_kst.min().dt.normalize()
            eligible = first_available.index[(t-first_available).dt.days >= cfg['minimum_observed_history_days']].intersection(recent)
        else:
            recent = prior[(prior.day >= t-pd.Timedelta(days=cfg['eligibility_recent_active_days'])) & prior.active_flag.eq(1)].user_key.unique()
            eligible = first.index[(t-first).dt.days >= cfg['minimum_observed_history_days']].intersection(recent)
        if not len(eligible): continue
        base = pd.DataFrame(index=pd.Index(eligible,name='user_key'))
        base['reference_date'] = t.strftime('%Y-%m-%d')
        base['first_observed_date'] = first.reindex(eligible).dt.strftime('%Y-%m-%d')
        base['observed_history_days'] = (t-first.reindex(eligible)).dt.days
        platform_before = ev[(ev.event_time_kst < t) & ev.user_key.isin(eligible)]
        if cfg['late_upload_policy']=='available_at_reference': platform_before=platform_before[platform_before.server_upload_time_utc<t]
        base['platform_before_T'] = platform_before.groupby('user_key').platform.last().reindex(eligible).fillna('unknown')
        future = ev[(ev.event_time_kst >= t) & (ev.event_time_kst < t+pd.Timedelta(days=7)) & ev.user_key.isin(eligible)]
        if cfg['label_upload_deadline_utc']:
            future = future[future.server_upload_time_utc <= pd.Timestamp(cfg['label_upload_deadline_utc'])]
        if len(future):
            assert future.event_time_kst.ge(t).all() and future.event_time_kst.lt(t+pd.Timedelta(days=7)).all()
            label_checks += len(future)
        fg = future.groupby('user_key').active_event.agg(['sum','size']).reindex(eligible,fill_value=0)
        decisions = [label_decision(t,t+pd.Timedelta(days=7),r['sum'],r['size']-r['sum'],cfg) for _,r in fg.iterrows()]
        base[['label_churn_7d','label_status','label_reason']] = pd.DataFrame(decisions,index=base.index)
        base['label_event_min_utc'] = future.groupby('user_key').event_time_utc.min()
        base['label_event_max_utc'] = future.groupby('user_key').event_time_utc.max()
        base['split'] = assign_split(base.reset_index(),cfg).to_numpy()
        for w in cfg['windows_days']:
            start = t-pd.Timedelta(days=w)
            events = ev[(ev.event_time_kst >= start) & (ev.event_time_kst < t) & ev.user_key.isin(eligible)]
            if cfg['late_upload_policy']=='available_at_reference': events=events[events.server_upload_time_utc<t]
            assert events.event_time_kst.lt(t).all()
            max_used_checks += len(events)
            f = base.copy(); f['window_days'] = w
            g = events.groupby('user_key')
            active = events[events.active_event.eq(1)]
            f['confirmed_active_days'] = active.groupby('user_key').date_kst.nunique().reindex(eligible,fill_value=0)
            f['active_event_count'] = active.groupby('user_key').size().reindex(eligible,fill_value=0)
            f['unique_active_sessions'] = active[active.session_valid].drop_duplicates(['user_key','device_key','session_id']).groupby('user_key').size().reindex(eligible,fill_value=0)
            f['active_events_without_valid_session'] = active[~active.session_valid].groupby('user_key').size().reindex(eligible,fill_value=0)
            # Missing days remain a quality field, never declared inactive.
            recorded = g.date_kst.nunique().reindex(eligible,fill_value=0)
            f['unconfirmed_record_days'] = recorded-f.confirmed_active_days
            f['no_record_days'] = w-recorded
            f['collection_verified_days'] = sum(covered(day,day+pd.Timedelta(days=1),cfg['verified_collection_intervals']) and not any(midnight(a)<=day<midnight(b) for a,b in cfg['suspect_intervals']) for day in pd.date_range(start,t,inclusive='left'))
            f['collection_unverified_days'] = w-f.collection_verified_days
            f['actions_per_active_day'] = f.active_event_count.div(f.confirmed_active_days.replace(0,np.nan))
            f['feature_max_event_time_utc'] = g.event_time_utc.max()
            # Recency may use earlier history, still strictly before T.
            before_active = platform_before[platform_before.active_event.eq(1)]
            last = before_active.groupby('user_key').event_time_utc.max().reindex(eligible)
            f['last_confirmed_activity_utc'] = last
            f['recency_days'] = (t-last).dt.total_seconds()/86400
            f['recency_reason'] = np.where(last.notna(),'observed_before_T','no_confirmed_activity_before_T')
            half = start+pd.Timedelta(days=w/2)
            early = active[active.event_time_kst<half].groupby('user_key').size().reindex(eligible,fill_value=0)
            late = active[active.event_time_kst>=half].groupby('user_key').size().reindex(eligible,fill_value=0)
            f['active_count_first_half']=early; f['active_count_second_half']=late
            f['activity_change_difference']=late-early
            f['activity_change_ratio']=(late-early).div(early.replace(0,np.nan))
            f['change_denominator_zero']=early.eq(0)
            sums = g[feats].sum().reindex(eligible,fill_value=0)
            for feat in feats:
                verified = covered(start,t,cfg['feature_verified_intervals'].get(feat,[])) and not any(midnight(a)<t and midnight(b)>start for a,b in cfg['suspect_intervals'])
                f[feat] = sums[feat].where(sums[feat].gt(0) | verified)
                f[feat+'_coverage_verified'] = verified
            rows[w].append(f.reset_index())
            if w == 28:
                # One vote per active date/hour and per active date/category, not per click.
                for group_col, kind in [('hour_kst','hour'),('weekday_kst','weekday'),('behavior_category','behavior')]:
                    votes=active.drop_duplicates(['user_key','date_kst',group_col]).groupby(['user_key',group_col]).size().rename('support_days').reset_index()
                    votes['reference_date']=t.strftime('%Y-%m-%d'); votes['window_days']=w; votes['profile_type']=kind
                    votes= votes.rename(columns={group_col:'profile_value'})
                    votes['evidence_status']=np.where(votes.support_days>=cfg['personalization_min_active_days'],'sufficient_by_config','insufficient')
                    profiles.append(votes)
    if not all(rows.values()):
        raise ValueError('No eligible samples: check reference dates, prior activity and minimum history settings')
    tables={w:pd.concat(v,ignore_index=True) for w,v in rows.items()}
    common = tables[7][['user_key','reference_date','label_churn_7d','label_status','label_reason','split']]
    for w,f in tables.items():
        pd.testing.assert_frame_equal(common,f[common.columns])
        numeric=f.select_dtypes(include='number')
        assert not np.isinf(numeric.to_numpy(dtype=float,na_value=np.nan)).any()
        f.to_csv(artifact(out, f'features_{w}d_all.csv.gz'),index=False)
        f[f.label_churn_7d.notna() & f.split.ne('purged_label_overlap')].to_csv(artifact(out, f'features_{w}d_labeled.csv.gz'),index=False)
        f[f.label_reason.eq('future_window_incomplete')].to_csv(artifact(out, f'features_{w}d_inference.csv.gz'),index=False)
        if cfg['split_dates']:
            for split in ['train','validation','test']:
                f[f.label_churn_7d.notna() & f.split.eq(split)].to_csv(artifact(out, f'features_{w}d_{split}.csv.gz'),index=False)
    pd.concat(profiles,ignore_index=True).to_csv(artifact(out, 'personalization_profiles.csv.gz'),index=False)
    sample=tables[7].copy(); sample['excluded_unknown_label']=sample.label_churn_7d.isna()
    sample['reference_month']=sample.reference_date.str[:7]
    sample['history_group']=pd.cut(sample.observed_history_days,[0,60,180,np.inf],labels=['28_to_60','61_to_180','over_180'])
    for col in ['platform_before_T','reference_month','history_group','user_key']:
        summary=sample.groupby(col,observed=True).agg(rows=('user_key','size'),excluded=('excluded_unknown_label','sum'))
        summary['excluded_ratio']=summary.excluded/summary.rows
        summary.to_csv(artifact(out, f'label_exclusion_by_{col}.csv.gz'))
    common[common.split.eq('purged_label_overlap')].to_csv(artifact(out, 'split_exclusions.csv.gz'),index=False)
    report['features']={'rows_per_window':len(common),'users':common.user_key.nunique(),'label_counts':sample.label_churn_7d.value_counts(dropna=False).to_dict(),
                        'label_reasons':sample.label_reason.value_counts().to_dict(),'unknown_label_ratio':float(sample.excluded_unknown_label.mean()),
                        'future_event_boundary_checks':label_checks,'feature_event_boundary_checks':max_used_checks,'common_samples_labels_splits_equal':True,
                        'split_configured':cfg['split_dates'] is not None,'purged_rows':int(common.split.eq('purged_label_overlap').sum())}
    # Explicit model candidates, selected by team; management/label fields excluded.
    model_cols=['confirmed_active_days','active_event_count','unique_active_sessions','active_events_without_valid_session','actions_per_active_day',
                'recency_days','active_count_first_half','active_count_second_half','activity_change_difference','activity_change_ratio','change_denominator_zero',*feats]
    dump(artifact(out, 'feature_roles.json'),{'numeric_candidates':model_cols,'categorical_candidates':[],
                                 'management_and_quality':[c for c in tables[7] if c not in model_cols],
                                 'warning':'Observed telemetry counts; missing feature zeros mean coverage unverified. No fitting performed.'})
    return tables


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--config',type=Path,default=Path(__file__).with_name('config.json')); args=parser.parse_args()
    cfg=json.loads(args.config.read_text())
    if cfg['windows_days'] != [7,14,21,28]: raise ValueError('Comparison requires [7,14,21,28]')
    if cfg['late_upload_policy'] not in ['retrospective_snapshot','available_at_reference']: raise ValueError('Unknown late upload policy')
    if cfg['minimum_observed_history_days']<28 or cfg['reference_interval_days']<1: raise ValueError('Invalid cohort settings')
    out=ROOT/'outputs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'); out.mkdir(parents=True); prepare_run(out)
    for file in Path(__file__).parent.glob('*.py'): shutil.copy2(file,artifact(out, file.name))
    for name in ['requirements.txt','requirements-tested.txt','README.md']: 
        if Path(__file__).with_name(name).exists(): shutil.copy2(Path(__file__).with_name(name),artifact(out, name))
    dump(artifact(out, 'config.json'),cfg)
    policy=json.loads((ROOT/cfg['policy_report']).read_text()); original=json.loads((ROOT/'data/baseline/processed/preprocessing_report.json').read_text())
    dump(artifact(out, 'legacy_policy.json'),policy)
    paths=sorted((ROOT/'data/raw').glob('*.zip'))
    inputs=[*paths,ROOT/cfg['clean_input'],ROOT/cfg['daily_input'],ROOT/cfg['policy_report'],ROOT/'data/baseline/processed/preprocessing_report.json',ROOT/'data/baseline/evidence/preprocess_events.py',ROOT/'data/baseline/evidence/check_activity.py',ROOT/'data/baseline/evidence/activity_check_summary.json']
    report={'packages':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,'scikit_learn':sklearn.__version__},
            'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in inputs},'raw_zip_count':len(paths)}
    secret=(ROOT/'.pseudonym_key').read_bytes()
    if len(secret)!=32: raise ValueError('Existing pseudonym key invalid; never generate replacement')
    dbpath=artifact(out, 'enrichment.sqlite'); db=sqlite3.connect(dbpath)
    try:
        extract_extra(db,paths,secret,report)
        e=clean_events(cfg,out,policy,original['mapping'],report,db)
    finally:
        db.close(); dbpath.unlink(missing_ok=True)
    d,feats=daily_aggregate(e,cfg,out,report)
    pd.DataFrame([{'original':a,'standard':b,'basis':'existing preprocess_events.py + user supplied mapping','verification':'independent historical release equivalence not verified'} for a,b in original['mapping'].items()]).to_csv(artifact(out, 'event_mapping.csv'),index=False)
    coverage=e.groupby(['platform','version_name','event_type_original','event_type'],dropna=False).agg(first_observed_utc=('event_time_utc','min'),last_observed_utc=('event_time_utc','max'),observed_count=('event_type','size')).reset_index()
    coverage['coverage_status']='observed_range_only_not_collection_guarantee'; coverage.to_csv(artifact(out, 'event_collection_by_version.csv'),index=False)
    e.groupby(['date_kst','platform'],dropna=False).size().rename('event_count').to_csv(artifact(out, 'daily_collection_counts.csv'))
    tables=build_features(e,d,feats,cfg,out,report)
    report['verification']={'legacy_event_rows_equal':len(e)==original['output_rows'],'legacy_user_keys_equal':e.user_key.nunique()==original['amplitude_based_user_keys'],
        'legacy_mapping_rows':int(e.event_type_original.ne(e.event_type).sum()),'midnight_kst_hour_0_rows':int(e.hour_kst.eq(0).sum()),
        'kst_date_conversion_matches':bool(e.event_time_kst.dt.strftime('%Y-%m-%d').eq(e.date_kst).all()),
        'active_rule_validity':'aggregate equality is not evidence of semantic correctness'}
    dictionary=[]
    descriptions=column_descriptions()
    for name,frame in [('events_clean',e),('user_daily_activity',d),('features',tables[7])]:
        for col in frame:
            desc=descriptions.get(col)
            if desc is None:
                if col.endswith('_coverage_verified'): desc='해당 기능의 관찰 기간 전체 수집 신뢰성이 설정으로 확인되었는지'
                elif col.endswith('_count'): desc='관측된 해당 행동 이벤트 수; Feature에서 0이고 수집 미확정이면 결측'
                else: desc='관리/품질 정보: '+col
            dictionary.append({'table':name,'column':col,'dtype':str(frame[col].dtype),'description':desc})
    # Full exported event schema includes fields removed from in-memory aggregation.
    exported=pd.read_csv(artifact(out, 'events_clean.csv.gz'),nrows=0)
    known={r['column'] for r in dictionary if r['table']=='events_clean'}
    for c in exported:
        if c not in known: dictionary.append({'table':'events_clean','column':c,'dtype':'see serialized CSV','description':descriptions.get(c,c+' (정제 이벤트 부가 정보)')})
    pd.DataFrame(dictionary).to_csv(artifact(out, 'column_dictionary.csv'),index=False)
    report['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    dump(artifact(out, 'quality_report.json'),report)
    (artifact(out, 'quality_report.sha256')).write_text(sha(artifact(out, 'quality_report.json'))+'  quality_report.json\n')
    if cfg.get('proxy_label_policy', {}).get('enabled', False):
        from proxy_labels import apply_to_run
        apply_to_run(out, cfg)
    from validate_outputs import audit
    audit(out)
    print('완료:',out,flush=True)


def column_descriptions():
    return {
        'user_key':'기존 Amplitude ID HMAC 가명. 실제 사람 수/가입 ID를 뜻하지 않음',
        'device_key':'기존 기기 HMAC 가명','event_key':'기존 프로젝트/UUID HMAC 가명',
        'event_type_original':'원본 이벤트명','event_type':'기존 4개 매핑을 적용한 표준 이벤트명',
        'event_time_utc':'행동 발생 UTC 시각','event_time_kst':'행동 발생 KST 공통 분석 시각; 사용자 현지 시각 아님',
        'date_kst':'KST 날짜','weekday_kst':'월요일=0, 일요일=6','hour_kst':'KST 0~23시',
        'session_id':'양의 정수 세션 ID; 사용자/기기와 함께 사용','session_valid':'양의 정수 ID와 device_key 존재',
        'active_event':'기존 v2 접속 규칙 일치 1; 나머지 0은 미확인',
        'active_flag':'일일 접속 확인 1, 접속 미확인 0','activity_status':'confirmed_activity 또는 unconfirmed_record',
        'activity_reason':'적용 규칙 또는 세션/위젯 등 미확인 이유','action_kind':'click/completion/screen_or_action/other 구분',
        'behavior_category':'알림 분석용 넓은 행동 분류; 이벤트명 통합이나 의미 동등성 주장 아님',
        'server_upload_time_utc':'Export 기준 업로드 UTC 시각','upload_delay_hours':'서버 업로드-행동 시각; 음수는 품질 이상',
        'session_count':'해당 일 활동 확인 고유 사용자/기기/세션 수; 기간 합산 금지',
        'last_event_time_utc':'최후 관측 이벤트; 실제 앱 종료 시각 아님',
        'first_observed_date':'최초 관측 KST 날짜; 실제 가입일 아님','reference_date':'KST 00:00 기준일 T',
        'window_days':'[T-w일,T) 관찰 기간','label_churn_7d':'0 미래 접속 확인; 1 신뢰 가능한 7일 활동 미관측; 그 외 결측',
        'label_status':'라벨 판정 상태','label_reason':'라벨 판정/미확정 이유','split':'시간 분할; 미설정은 not_configured',
        'recency_days':'T-마지막 접속 확인 시각, 일 단위; T 이전 전체 관측 이력 사용',
        'unique_active_sessions':'관찰 기간 전체 고유 사용자/기기/session_id; 활동 확인 이벤트에서 직접 계산',
        'no_record_days':'관찰 기간 내 사용자 이벤트가 없는 날짜 수; 미접속으로 해석 금지',
        'unconfirmed_record_days':'기록은 있지만 접속 확인 이벤트는 없는 날짜 수',
        'activity_change_ratio':'(후반 활동 이벤트 수-전반 수)/전반 수; 전반 0이면 결측',
        'activity_change_difference':'동일 길이 전후반 활동 이벤트 수 차이; 7/21일은 정오에서 분리',
        'actions_per_active_day':'접속 확인 이벤트 수/접속 확인 활동일 수; 분모 0 결측',
        'bookmark_action':'원본 속성 add/remove; 그 외 unknown','empathy_action':'원본 속성 add/remove; 그 외 unknown',
        'quality_flags':'시간/식별자/업로드 이상 플래그','platform':'원본 플랫폼','version_name':'원본 앱 버전',
    }

if __name__=='__main__': main()
