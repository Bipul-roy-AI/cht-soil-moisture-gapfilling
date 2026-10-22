import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from chtsm.data import validate_frame,validate_config,audit_frame,FEATURES
from chtsm.synthetic import make_fixture
from chtsm.models import fit_experiment,freeze_experiment,evaluate_final,make_model,load_frozen
from chtsm.metrics import scores,cluster_calibration,paired_block_delta
from chtsm.gaps import hidden_mask,temporal_predictions,spatial_subset

ROOT=Path(__file__).resolve().parents[1]


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.frame,cls.config=make_fixture(ROOT/'configs/study_v2.json')

    def test_requires_synthetic_opt_in(self):
        with self.assertRaisesRegex(ValueError,'opt-in'):validate_frame(self.frame,self.config)

    def test_duplicate_units_rejected(self):
        a=pd.concat([self.frame,self.frame.iloc[:1]])
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_frame(a,self.config,True)

    def test_mixed_versions_rejected(self):
        a=self.frame.copy();a.loc[0,'smap_collection']='WRONG'
        with self.assertRaisesRegex(ValueError,'version'):validate_frame(a,self.config,True)

    def test_qa_failed_target_excluded(self):
        a=self.frame.copy();a.loc[0,['sm_raw','target_present','sm_qa']]=[.4,1,1]
        b=validate_frame(a,self.config,True);self.assertTrue(pd.isna(b.loc[0,'target_sm']))

    def test_missing_export_not_natural_gap(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):audit_frame(self.frame.iloc[10:],self.config)

    def test_wrong_log_ratio_rejected(self):
        a=self.frame.copy();a['raw_vh_vv_db']=a.raw_vh_db/a.raw_vv_db
        with self.assertRaisesRegex(ValueError,'polarization'):validate_frame(a,self.config,True)

    def test_changed_export_settings_rejected(self):
        c=json.loads(json.dumps(self.config));c['sar_window_days']=24
        with self.assertRaisesRegex(ValueError,'Export configuration'):validate_frame(self.frame,c,True)

    def test_split_overlap_rejected(self):
        c=json.loads(json.dumps(self.config));c['split_years']['val']=[2019]
        with self.assertRaisesRegex(ValueError,'chronological'):validate_config(c)

    def test_spatial_buffer_can_refuse_impossible_design(self):
        with self.assertRaisesRegex(ValueError,'fewer than three'):spatial_subset(self.frame,['FICTIONAL_CELL_0'])


class MetricTests(unittest.TestCase):
    def test_constant_truth_r2_undefined(self):self.assertIsNone(scores([.3,.3],[.2,.4])['r2'])

    def test_calibration_counts_dates_not_repeated_pixels(self):
        dates=np.repeat(pd.date_range('2021-01-01',periods=30),5)
        d=pd.DataFrame({'date':dates,'target_sm':.4})
        self.assertEqual(cluster_calibration(d,np.repeat(.3,len(d)))['dates'],30)

    def test_paired_identical_predictions_have_zero_delta(self):
        d=pd.DataFrame({'date':pd.date_range('2022-01-01',periods=200),'target_sm':np.arange(200)/1000})
        p=d.target_sm+.01;r=paired_block_delta(d,p,p,repetitions=30)
        self.assertEqual(r['rmse_delta_a_minus_b'],0);self.assertEqual(r['interval'],[0,0])


class LeakageTests(unittest.TestCase):
    def test_imputation_fits_only_training_inputs(self):
        x=pd.DataFrame({'rain_1d_mm':[1,np.nan,3],'evi':[.2,.4,np.nan]})
        m=make_model('random_forest',42,dict(n_estimators=5,max_depth=2,min_samples_leaf=1))
        m.fit(x,[.1,.2,.3]);imputer=m.named_steps['features'].transformer_list[0][1]
        before=imputer.statistics_.copy();m.predict(pd.DataFrame({'rain_1d_mm':[1e8],'evi':[np.nan]}))
        np.testing.assert_array_equal(before,imputer.statistics_);np.testing.assert_allclose(before,[2,.3])

    def test_hidden_labels_cannot_influence_interpolation(self):
        d=pd.DataFrame({'cell_id':['a']*10,'date':pd.date_range('2022-01-01',periods=10),'target_sm':np.arange(10)/100})
        hidden=np.zeros(10,bool);hidden[3:6]=True
        for method in ['persistence','linear_interpolation']:
            p=temporal_predictions(d,hidden,method);altered=d.copy();altered.loc[hidden,'target_sm']=.99
            np.testing.assert_allclose(p,temporal_predictions(altered,hidden,method),equal_nan=True)

    def test_final_test_requires_explicit_gate(self):
        with self.assertRaisesRegex(ValueError,'disabled'):evaluate_final(pd.DataFrame(),'/tmp/no-run')


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.run_dir=Path(cls.tmp.name)/'run'
        cls.frame,cls.config=make_fixture(ROOT/'configs/study_v2.json')
        cls.meta,cls.selection=fit_experiment(cls.frame,cls.config,cls.run_dir,software_check=True,verbose=False)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_training_uses_val_and_separate_calibration(self):
        self.assertEqual(self.meta['selection_split'],'val');self.assertEqual(self.meta['calibration_split'],'calibration')
        self.assertEqual(len(self.selection),9)

    def test_test_targets_cannot_change_fitted_validation_scores(self):
        changed=self.frame.copy();test=changed.split=='test'
        changed.loc[test,'target_sm']=changed.loc[test,'target_sm']*.8+.02
        c=dict(self.config);c['algorithms']=['random_forest']
        _,selection=fit_experiment(changed,c,Path(self.tmp.name)/'perturbed_test',software_check=True,verbose=False)
        reference=self.selection.set_index('name').validation_macro_cell_rmse
        np.testing.assert_allclose(selection.validation_macro_cell_rmse,reference.loc[selection.name])

    def test_freeze_reload_evaluate_and_preserve_observed_targets(self):
        freeze_experiment(self.run_dir,'Fictional software verification: prespecified models; macro-cell RMSE primary; no observed Bangladesh result.')
        report,reconstruction=evaluate_final(self.frame,self.run_dir,True)
        self.assertEqual(len(report),9)
        known=reconstruction.target_sm.notna()
        np.testing.assert_allclose(reconstruction.loc[known,'complete_sm'],reconstruction.loc[known,'target_sm'])
        self.assertTrue((self.run_dir/'final_test/metrics.json').exists())
        changed=self.frame.copy();changed.loc[0,'rain_1d_mm']+=1
        with self.assertRaisesRegex(ValueError,'Dataset changed'):load_frozen(changed,self.run_dir)


try:
    import ee
    from ee.apitestcase import ApiTestCase
except ImportError:
    ApiTestCase=None

if ApiTestCase:
    class EarthEngineGraphTests(ApiTestCase):
        def test_full_month_graph_serializes_without_live_server(self):
            from chtsm.gee import build_month
            config=json.loads((ROOT/'configs/study_v2.json').read_text());config['relative_orbit']=1
            roi=ee.Geometry.Rectangle([91.8,22,92,22.2]);proj=ee.Projection('EPSG:4326').atScale(9000)
            collection=ee.ImageCollection(config['smap_collection'])
            with patch('chtsm.gee.district_geometry',return_value=roi),patch('chtsm.gee.target_projection',return_value=(collection,proj,'test-grid',{})),patch.object(ee.Number,'getInfo',return_value=1):
                table,_=build_month(config,'2021-06-01','2021-06-03',pilot_cells=2)
                graph=table.serialize();self.assertIn('sampleRegions',graph);self.assertIn('reduceResolution',graph)


if __name__=='__main__':unittest.main()
