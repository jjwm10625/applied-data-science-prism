import unittest
import numpy as np
import pandas as pd
from run import label_decision, assign_split, midnight, covered
from model_transform import make_preprocessor

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.c={'analysis_start':'2025-10-26','analysis_end_exclusive':'2026-10-08',
                'verified_collection_intervals':[], 'suspect_intervals':[], 'split_dates':None}
        self.t=midnight('2026-01-01'); self.end=self.t+pd.Timedelta(days=7)
    def test_labels(self):
        self.assertEqual(label_decision(self.t,self.end,1,2,self.c)[0],0)
        self.assertTrue(np.isnan(label_decision(self.t,self.end,0,1,self.c)[0]))
        self.assertTrue(np.isnan(label_decision(self.t,self.end,0,0,self.c)[0]))
        self.c['verified_collection_intervals']=[['2026-01-01','2026-01-08']]
        self.assertEqual(label_decision(self.t,self.end,0,0,self.c)[0],1)
        self.c['suspect_intervals']=[['2026-01-04','2026-01-05']]
        self.assertTrue(np.isnan(label_decision(self.t,self.end,0,0,self.c)[0]))
    def test_latest_even_with_activity(self):
        t=midnight('2026-10-05')
        self.assertTrue(np.isnan(label_decision(t,t+pd.Timedelta(days=7),1,0,self.c)[0]))
    def test_purge_and_exact_boundary(self):
        self.c['split_dates']={'validation_start':'2026-02-01','test_start':'2026-03-01'}
        f=pd.DataFrame({'reference_date':['2026-01-25','2026-01-26','2026-02-01','2026-02-23','2026-03-01']})
        self.assertEqual(assign_split(f,self.c).tolist(),['train','purged_label_overlap','validation','purged_label_overlap','test'])
    def test_midnight_session(self):
        ts=pd.to_datetime(['2026-01-01T14:59:59Z','2026-01-01T15:00:00Z'],utc=True).tz_convert('Asia/Seoul')
        self.assertEqual(ts.strftime('%Y-%m-%d').tolist(),['2026-01-01','2026-01-02'])
        f=pd.DataFrame({'user_key':['u','u'],'device_key':['d','d'],'session_id':['1','1'],'day':ts.date})
        self.assertEqual(len(f.drop_duplicates(['user_key','device_key','session_id'])),1)
        self.assertEqual(len(f.drop_duplicates()),2)
    def test_transform_train_only(self):
        p=make_preprocessor(['x'],['category'],scale=True)
        p.fit(pd.DataFrame({'x':[1.,3.],'category':['a','a']}))
        before=p.named_transformers_['numeric'].named_steps['scale'].mean_.copy()
        p.transform(pd.DataFrame({'x':[1000.],'category':['unseen']}))
        np.testing.assert_equal(before,p.named_transformers_['numeric'].named_steps['scale'].mean_)
        with self.assertRaises(ValueError): make_preprocessor(['user_key'])

if __name__=='__main__': unittest.main()
