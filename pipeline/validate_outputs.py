"""Independent exported-file audit. Can rerun without rescanning raw ZIPs."""
import argparse, collections, hashlib, json, platform, shutil, subprocess, sys
from pathlib import Path
from layout import artifact, prepare_run
import numpy as np
import pandas as pd


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def audit(out):
    report=json.loads((artifact(out, 'quality_report.json')).read_text())
    cfg=json.loads((artifact(out, 'config.json')).read_text())
    daily_file=pd.read_csv(artifact(out, 'user_daily_activity.csv.gz'))
    unconfirmed_example=daily_file[daily_file.active_flag.eq(0)].iloc[0].to_dict()
    missing=collections.Counter(); counts=collections.Counter(); examples={}; schema=None
    utc_min=None; utc_max=None; late=0
    for c in pd.read_csv(artifact(out, 'events_clean.csv.gz'),chunksize=100000,dtype={'user_key':'string','device_key':'string','event_key':'string','session_id':'string','session_id_original':'string','version_name':'string','has_photo':'string','is_first_play':'string','quality_flags':'string'}):
        missing.update(c.isna().sum().to_dict())
        schema={col:str(c[col].dtype) for col in c}
        time=pd.to_datetime(c.event_time_utc,utc=True,format='mixed')
        upload=pd.to_datetime(c.server_upload_time_utc,utc=True,format='mixed')
        if utc_min is None: utc_min=time.min(); utc_max=time.max()
        else: utc_min=min(utc_min,time.min()); utc_max=max(utc_max,time.max())
        counts['upload_later_than_24h']+=int(((upload-time).dt.total_seconds()>86400).sum())
        counts['invalid_session_rows']+=int((~c.session_valid).sum())
        for action in ['bookmark_add_count','bookmark_remove_count','empathy_add_count','empathy_remove_count']:
            counts[action]+=int(c[action].sum())
        masks={'ordinary_activity':c.active_event.eq(1),'legacy_mapping':c.event_type_original.ne(c.event_type),
               'unconfirmed_widget':c.activity_reason.eq('widget_scope_unverified'),'kst_midnight':c.hour_kst.eq(0)}
        for kind,mask in masks.items():
            counts[kind]+=int(mask.sum())
            if kind not in examples and mask.any():
                examples[kind]=c.loc[mask,['event_key','user_key','event_type_original','event_type','event_time_utc','event_time_kst','date_kst','hour_kst','activity_status','activity_reason']].iloc[0].to_dict()
        assert (time.dt.tz_convert('Asia/Seoul').dt.strftime('%Y-%m-%d')==c.date_kst).all()
    checks={}; manifest=json.loads((artifact(out, 'feature_roles.json')).read_text()); common=None
    target=manifest.get('modeling_target', 'label_churn_7d')
    for w in [7,14,21,28]:
        f=pd.read_csv(artifact(out, f'features_{w}d_all.csv.gz'), float_precision='round_trip')
        t=pd.to_datetime(f.reference_date).dt.tz_localize('Asia/Seoul').dt.tz_convert('UTC')
        used=pd.to_datetime(f.feature_max_event_time_utc,utc=True,format='mixed')
        last=pd.to_datetime(f.last_confirmed_activity_utc,utc=True,format='mixed')
        lmin=pd.to_datetime(f.label_event_min_utc,utc=True,format='mixed')
        lmax=pd.to_datetime(f.label_event_max_utc,utc=True,format='mixed')
        assert (used.isna() | (used<t)).all()
        assert (last.isna() | (last<t)).all()
        assert (lmin.isna() | ((lmin>=t) & (lmin<t+pd.Timedelta(days=7)))).all()
        assert (lmax.isna() | ((lmax>=t) & (lmax<t+pd.Timedelta(days=7)))).all()
        keys=f[['user_key','reference_date','label_churn_7d','label_reason','split'] + ([target,'label_proxy_status','label_proxy_reason','label_proxy_assumption_applied'] if target != 'label_churn_7d' else [])]
        assert not keys.duplicated(['user_key','reference_date']).any()
        if common is None:common=keys
        else:pd.testing.assert_frame_equal(common,keys)
        assert not np.isinf(f.select_dtypes('number').to_numpy()).any()
        numeric_candidates=manifest['numeric_candidates']
        assert not set(numeric_candidates)&{'user_key','reference_date','label_churn_7d','label_reason','label_status'}
        if target != 'label_churn_7d':
            from proxy_labels import apply_proxy_labels, PROXY_COLUMNS
            expected=apply_proxy_labels(f.drop(columns=PROXY_COLUMNS),cfg)
            pd.testing.assert_frame_equal(f[PROXY_COLUMNS],expected[PROXY_COLUMNS],check_exact=True)
            assert not any(c.startswith('label_') for c in numeric_candidates)
            if cfg.get('label_upload_deadline_utc') is None:
                for ref, group in f.groupby('reference_date'):
                    end=(pd.Timestamp(ref)+pd.Timedelta(days=7)).strftime('%Y-%m-%d')
                    future=daily_file[daily_file.date_kst.ge(ref) & daily_file.date_kst.lt(end)]
                    totals=future.groupby('user_key')[['total_event_count','active_event_count']].sum().reindex(group.user_key,fill_value=0)
                    assert totals.loc[group.loc[group[target].eq(1),'user_key'],'total_event_count'].eq(0).all()
                    assert totals.loc[group.loc[group[target].eq(0),'user_key'],'active_event_count'].gt(0).all()
            selected=f[f[target].notna() & f.split.ne('purged_label_overlap')].reset_index(drop=True)
            labeled=pd.read_csv(artifact(out,f'features_{w}d_labeled.csv.gz'),float_precision='round_trip')
            pd.testing.assert_frame_equal(selected,labeled,check_exact=True)
        checks[w]={'rows':len(f),'modeling_target':target,'labeled':int(f[target].notna().sum()),'strict_labeled':int(f.label_churn_7d.notna().sum()),'boundary_checks_passed':True,
                   'feature_missing_counts':f[numeric_candidates].isna().sum().to_dict()}
    test=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_*.py','-v'],text=True,capture_output=True)
    (artifact(out, 'test_results.txt')).write_text(test.stdout+test.stderr)
    if test.returncode:raise AssertionError('Unit tests failed; see test_results.txt')
    audit_report={'event_missing_counts':dict(missing),'serialized_schema':schema,'counts':dict(counts),'examples':examples,
                  'unconfirmed_day_example':unconfirmed_example,'feature_checks':checks,'first_event_utc':str(utc_min),'last_event_utc':str(utc_max),
                  'test_exit_code':test.returncode,'python_executable':sys.executable}
    (artifact(out, 'independent_validation.json')).write_text(json.dumps(audit_report,ensure_ascii=False,indent=2,default=str))
    shutil.copy2(__file__,artifact(out, 'validate_outputs.py'))
    shutil.copy2(Path(__file__).with_name('layout.py'),artifact(out, 'layout.py'))
    # Add explicit meanings for every model candidate and generic audit fields.
    dictionary=pd.read_csv(artifact(out, 'column_dictionary.csv'))
    actual_feature_cols=pd.read_csv(artifact(out, 'features_7d_all.csv.gz'),nrows=0).columns
    dictionary=dictionary[~dictionary.table.eq('features') | dictionary.column.isin(actual_feature_cols)]
    roles=json.loads((artifact(out, 'feature_roles.json')).read_text())
    roles['management_and_quality']=[x for x in roles['management_and_quality'] if x in actual_feature_cols]
    (artifact(out, 'feature_roles.json')).write_text(json.dumps(roles,ensure_ascii=False,indent=2))
    desc={
        'confirmed_active_days':'관찰 구간에서 접속 확인 이벤트가 있는 고유 KST 날짜 수',
        'active_event_count':'기존 v2 규칙에 부합하는 관측 이벤트 수',
        'total_event_count':'접속 판정과 무관한 모든 관측 이벤트 수',
        'active_events_without_valid_session':'접속 확인 이벤트 중 유효 기기/세션 조합이 없는 수',
        'collection_verified_days':'수집 검증 구간에 있고 의심 구간에는 없는 날짜 수',
        'collection_unverified_days':'관찰 일수-검증된 수집 날짜 수',
        'observed_history_days':'T와 최초 관측 KST 날짜 사이 일수; 가입 후 경과일 아님',
        'platform_before_T':'T 이전 마지막 비결측 플랫폼; 복수 플랫폼 사용을 배제하지 않음',
        'first_event_time_utc':'일일 최초 관측 UTC 시각',
        'last_active_time_utc':'일일 마지막 접속 확인 이벤트 UTC 시각',
        'last_confirmed_activity_utc':'T 이전 전체 이력 마지막 접속 확인 UTC 시각',
        'feature_max_event_time_utc':'해당 관찰 구간의 최후 이벤트 시각; T 미만 검사',
        'label_event_min_utc':'[T,T+7일) 라벨 참조 이벤트 중 최초 시각',
        'label_event_max_utc':'[T,T+7일) 라벨 참조 이벤트 중 최후 시각',
        'active_count_first_half':'관찰 구간 전반부의 접속 확인 이벤트 수',
        'active_count_second_half':'관찰 구간 후반부의 접속 확인 이벤트 수',
        'change_denominator_zero':'변화율 분모인 전반부 접속 확인 이벤트 수가 0인지',
        'collection_status':'일일 수집 완전성은 미검증: unverified',
        'recency_reason':'마지막 접속 확인 시각 관측/결측 근거',
        'session_id_original':'원본 세션 문자열; 직접 사용자/기기 식별자 아님',
        'char_count':'일기 문자 수, 비숫자/음수 결측; 본문은 포함하지 않음',
        'has_photo':'사진 포함 여부(참/거짓/결측)',
        'is_first_play':'최초 재생 여부(참/거짓/결측)',
    }
    for key,val in desc.items(): dictionary.loc[dictionary.column.eq(key),'description']=val
    mapping=json.loads((artifact(out, 'legacy_policy.json')).read_text())['feature_event_mapping']
    for key,events in mapping.items():
        dictionary.loc[dictionary.column.eq(key),'description']='관측 이벤트 '+', '.join(events)+' 횟수. Feature의 수집 미검증 0은 결측'
    for kind in ['bookmark','empathy']:
        for action in ['add','remove','unknown']:
            dictionary.loc[dictionary.column.eq(f'{kind}_{action}_count'),'description']=f'{kind} 행동 분류의 원본 action={action} 관측 횟수; 기존 좁은 이벤트 집계와 범위 다름'
    extra=[]
    profile_descriptions={'user_key':'기존 가명 사용자 키','profile_value':'profile_type에 따른 시간/요일/행동 분류 값','support_days':'해당 값이 관측된 고유 활동 날짜 수','reference_date':'KST 00:00 기준일 T','window_days':'T 이전 집계 기간(28일)','profile_type':'hour/weekday/behavior','evidence_status':'설정된 최소 근거 날짜 수 충족 여부'}
    for col,desc in profile_descriptions.items(): extra.append({'table':'personalization_profiles','column':col,'dtype':'see CSV','description':desc})
    dictionary=dictionary[dictionary.table.ne('personalization_profiles')]
    dictionary=pd.concat([dictionary,pd.DataFrame(extra)],ignore_index=True)
    dictionary.to_csv(artifact(out, 'column_dictionary.csv'),index=False)
    collection=pd.read_csv(artifact(out, 'daily_collection_counts.csv'))
    daily_totals=collection.groupby('date_kst').event_count.sum()
    calendar=pd.DataFrame(index=pd.date_range(daily_totals.index.min(),daily_totals.index.max(),freq='D').strftime('%Y-%m-%d'))
    calendar.index.name='date_kst'
    calendar['observed_event_count']=daily_totals.reindex(calendar.index,fill_value=0)
    calendar['collection_status']='unverified'
    calendar.loc[calendar.index >= cfg['analysis_end_exclusive'],'collection_status']='partial_or_outside_analysis'
    calendar.to_csv(artifact(out, 'collection_calendar.csv'))
    feature=report['features']; daily=report['daily_comparison']
    labels=common[target].value_counts().to_dict()
    target_unknown_ratio=float(common[target].isna().mean())
    if target == 'label_churn_7d':
        label_note='엄격 라벨만 사용합니다. 수집 신뢰성을 검증하지 않은 구간의 무기록은 미확정입니다. 두 클래스 확보 여부를 확인한 뒤 학습하세요.'
    else:
        proxy=report['proxy_labels']
        label_note=(proxy['statement']+'\n\n모델링 정답은 label_proxy_churn_7d입니다. 기존 label_churn_7d는 엄격한 비교용 정답으로 보존했습니다. '
                    '대리 라벨 1은 실제 미접속을 확정하지 않습니다. 미래 범위 부족과 미확인 기록은 결측을 유지했습니다. '
                    '시간 분할은 미설정이면 팀 합의 후 적용해야 합니다. 현재 결과는 retrospective_snapshot 가용성 기준을 확인해야 합니다.')
    text=f'''# 데이터 품질 및 검증 결과

정제 이벤트 {report['cleaning']['output_rows']:,}행, 가명 사용자 키 {report['cleaning']['user_keys']:,}개입니다. 가명 키 수는 실제 사람 수가 아닙니다.

- 일일 집계 {daily['new_rows']:,}행: 접속 확인 {daily['confirmed_days']:,}, 접속 미확인 {daily['unconfirmed_days']:,}.
- 기존 모든 일일 컬럼의 사용자·날짜별 값 불일치: {sum(daily['column_mismatch_counts'].values())}건. 이벤트명 4개 매핑 적용 행: {report['verification']['legacy_mapping_rows']:,}.
- 관찰 기간별 Feature {feature['rows_per_window']:,}행, 대상 사용자 키 {feature['users']:,}개. 네 기간 대상/라벨/분할 동일.
- 모델링 정답 컬럼: {target}. 라벨 분포: {labels}. 미확정 비율 {target_unknown_ratio:.2%}.
- 보존된 엄격 라벨의 사유별 건수: {feature['label_reasons']}.
- 시간 분할 설정 여부: {feature['split_configured']}. 현재 전체 데이터 fit 또는 모델 학습은 수행하지 않았습니다.
- 24시간 초과 지연 업로드: {counts['upload_later_than_24h']:,}행. 지연 업로드와 수집 완결 여부는 별개입니다.
- 일반 사례/구버전 매핑/위젯 미확인/자정 사례는 independent_validation.json에 가명 예시와 검사 건수를 저장했습니다.
- Feature 사용 시각 <T 및 라벨 근거 [T,T+7일) 검사를 실제 출력 파일에서 재확인했습니다. 단위 테스트 결과는 test_results.txt입니다.

{label_note}

일별 이벤트 존재와 집계 합계 일치만으로 접속 판정 타당성이나 수집 완전성을 주장하지 않습니다.

기존 집계는 유지했으며 새로 추가된 북마크/공감 add/remove 집계는 원본 속성에 근거합니다. 개인정보 자유 텍스트를 제외하고 필요한 속성만 추출했습니다. 기본 지연 업로드 정책은 {cfg['late_upload_policy']}입니다. README의 당시 가용성 한계를 확인하세요.

제외 구성은 label_exclusion_by_platform_before_T.csv.gz, label_exclusion_by_reference_month.csv.gz, label_exclusion_by_history_group.csv.gz, label_exclusion_by_user_key.csv.gz에서 비교할 수 있습니다. 아래 플랫폼·관측 이력 표는 제외 전 행 수/제외 행 수/제외 비율입니다.
'''
    for dim in ['platform_before_T','history_group']:
        s=pd.read_csv(artifact(out, f'label_exclusion_by_{dim}.csv.gz'))
        text+='\n```text\n'+s.to_string(index=False)+'\n```\n'
    monthly=pd.read_csv(artifact(out, 'label_exclusion_by_reference_month.csv.gz'))
    users=pd.read_csv(artifact(out, 'label_exclusion_by_user_key.csv.gz'))
    text+='\n기간별 제외 현황:\n\n```text\n'+monthly.to_string(index=False)+'\n```\n'
    text+=f'\n대상 사용자 키 {len(users):,}개 중 모든 기준일 라벨이 미확정인 키는 {int(users.excluded.eq(users.rows).sum()):,}개입니다.\n'
    text+=f'\n업로드가 행동 시각보다 빠른 기록 {report["cleaning"]["negative_upload_delay"]:,}행은 음수 지연 품질 플래그로 보존했습니다. 실제 원인은 미확정입니다.\n'
    if target != 'label_churn_7d':
        text+='\n위 기존 제외 표는 엄격 라벨 기준입니다. 아래는 대리 라벨 기준입니다.\n'
        for dim in ['platform_before_T','reference_month','history_group']:
            summary=pd.read_csv(artifact(out,f'proxy_label_exclusion_by_{dim}.csv.gz'))
            text+='\n```text\n'+summary.to_string(index=False)+'\n```\n'
        text+='\n대리 라벨 사유별 건수: '+str(report['proxy_labels']['proxy_reasons'])+'\n'
    (artifact(out, 'DATA_QUALITY.md')).write_text(text,encoding='utf-8')
    hashes={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='audit_manifest.json'}
    (artifact(out, 'audit_manifest.json')).write_text(json.dumps({'sha256':hashes,'note':'Final artifacts after independent audit; quality_report output hashes are pre-audit stage hashes.'},indent=2))
    print('독립 검증 완료:',out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_directory',type=Path);a=p.parse_args();audit(a.run_directory.resolve())
