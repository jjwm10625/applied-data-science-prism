import copy
import unittest
import numpy as np
import pandas as pd
from proxy_labels import apply_proxy_labels, TARGET, PROXY_COLUMNS
from model_transform import make_preprocessor

class ProxyLabelTests(unittest.TestCase):
    def setUp(self):
        self.cfg={'analysis_start':'2025-10-26','analysis_end_exclusive':'2026-10-08',
                  'suspect_intervals':[], 'label_upload_deadline_utc':None,
                  'proxy_label_policy':{'enabled':True,'assumed_collection_intervals':[['2025-10-26','2026-10-08']]}}
        self.frame=pd.DataFrame({
            'reference_date':['2026-01-01']*4+['2026-10-04'],
            'label_churn_7d':[0.,np.nan,np.nan,np.nan,np.nan],
            'label_reason':['confirmed_event_in_future_window','collection_reliability_unverified',
                            'unconfirmed_records_in_future_window','unexpected_reason','future_window_incomplete'],
            'label_event_min_utc':['2026-01-01T02:00:00Z',None,'2026-01-02T02:00:00Z',None,None],
            'label_event_max_utc':['2026-01-01T02:00:00Z',None,'2026-01-02T02:00:00Z',None,None],
            'recency_days':[1.,2.,3.,4.,5.],
        })
    def test_only_eligible_absence_becomes_proxy_one(self):
        r=apply_proxy_labels(self.frame,self.cfg)
        self.assertEqual(r[TARGET].iloc[:2].tolist(),[0.,1.])
        self.assertTrue(r[TARGET].iloc[2:].isna().all())
        self.assertEqual(r.label_proxy_assumption_applied.tolist(),[False,True,False,False,False])
        pd.testing.assert_frame_equal(self.frame,r[self.frame.columns],check_exact=True)
    def test_suspect_day_excludes_even_observed_activity(self):
        self.cfg['suspect_intervals']=[['2026-01-04','2026-01-05']]
        self.assertTrue(apply_proxy_labels(self.frame,self.cfg)[TARGET].isna().all())
    def test_assumption_scope_and_half_open_boundary(self):
        self.cfg['proxy_label_policy']['assumed_collection_intervals']=[['2026-01-01','2026-01-08']]
        self.assertEqual(apply_proxy_labels(self.frame,self.cfg)[TARGET].iloc[1],1)
        self.cfg['proxy_label_policy']['assumed_collection_intervals']=[['2026-01-01','2026-01-07']]
        self.assertTrue(apply_proxy_labels(self.frame,self.cfg)[TARGET].isna().all())
    def test_latest_even_with_activity_and_early_upload_cutoff(self):
        f=self.frame.iloc[[0]].copy();f['reference_date']='2026-10-04'
        self.assertTrue(apply_proxy_labels(f,self.cfg)[TARGET].isna().all())
        self.cfg['label_upload_deadline_utc']='2026-01-03T00:00:00Z'
        self.assertTrue(apply_proxy_labels(self.frame,self.cfg)[TARGET].isna().all())
    def test_explicit_assumption_and_no_leakage_columns(self):
        self.cfg['proxy_label_policy']['enabled']=False
        with self.assertRaises(ValueError):apply_proxy_labels(self.frame,self.cfg)
        for col in PROXY_COLUMNS:
            with self.assertRaises(ValueError):make_preprocessor([col])
    def test_reapply_proxy_from_current_run_preserves_strict_data(self):
        import json
        import tempfile
        from pathlib import Path
        from layout import artifact, prepare_run
        from proxy_labels import apply_to_run
        cfg=copy.deepcopy(self.cfg)
        cfg.update(split_dates=None,late_upload_policy='retrospective_snapshot')
        f=self.frame.iloc[:2].copy()
        f['user_key']=['u1','u2']; f['label_status']=['confirmed_activity','unknown']
        f['split']='not_configured'; f['platform_before_T']='iOS'; f['observed_history_days']=30
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); prepare_run(out)
            for w in [7,14,21,28]:
                f.assign(window_days=w).to_csv(artifact(out,f'features_{w}d_all.csv.gz'),index=False)
            artifact(out,'feature_roles.json').write_text(json.dumps({'numeric_candidates':['recency_days'],'management_and_quality':[]}))
            artifact(out,'quality_report.json').write_text(json.dumps({'features':{}}))
            pd.DataFrame([{'table':'features','column':'label_churn_7d','dtype':'float64','description':'strict'}]).to_csv(artifact(out,'column_dictionary.csv'),index=False)
            first=apply_to_run(out,cfg)
            original=pd.read_csv(artifact(out,'features_7d_all.csv.gz'))
            second=apply_to_run(out,cfg)
            pd.testing.assert_frame_equal(original,pd.read_csv(artifact(out,'features_7d_all.csv.gz')))
            self.assertEqual(first['proxy_label_counts'],second['proxy_label_counts'])
            d=pd.read_csv(artifact(out,'column_dictionary.csv'))
            self.assertEqual(int(d.column.isin(PROXY_COLUMNS).sum()),4)

    def test_reuse_rejects_feature_or_split_changes(self):
        from relabel import check_reuse_config
        old={'late_upload_policy':'retrospective_snapshot','split_dates':None}
        new=copy.deepcopy(old);new['late_upload_policy']='available_at_reference'
        with self.assertRaises(ValueError):check_reuse_config(old,new)
        new=copy.deepcopy(old);new['proxy_label_policy']={'enabled':True}
        check_reuse_config(old,new)

if __name__=='__main__':unittest.main()
