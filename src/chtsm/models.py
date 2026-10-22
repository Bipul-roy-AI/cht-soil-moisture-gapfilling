"""Train/validation selection, separate calibration, and an explicit final-test gate."""
import hashlib
import json
import platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer,MissingIndicator
from sklearn.pipeline import Pipeline,FeatureUnion
from sklearn.linear_model import LinearRegression
from .data import FEATURES,FEATURE_GROUPS,audit_frame,frame_digest,save_json
from .metrics import summarize,cluster_calibration,block_interval,paired_block_delta,scores


def code_hashes():
    root=Path(__file__).parent
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*.py'))}


class Baseline:
    def __init__(self,kind):self.kind=kind
    def fit(self,df):
        self.mean=float(df.target_sm.mean())
        self.cell=df.groupby('cell_id').target_sm.mean().to_dict()
        self.month=df.groupby(df.date.dt.month).target_sm.mean().to_dict()
        self.cell_month=df.groupby(['cell_id',df.date.dt.month]).target_sm.mean().to_dict()
        if self.kind=='era5_linear':
            self.linear=Pipeline([('imputer',SimpleImputer(keep_empty_features=True)),('model',LinearRegression())])
            self.linear.fit(df[['era5_sm_prev']],df.target_sm)
        return self
    def predict(self,df):
        if self.kind=='global_mean':return np.repeat(self.mean,len(df))
        if self.kind=='seasonal_cell':
            return np.array([self.cell_month.get((c,m),self.month.get(m,self.cell.get(c,self.mean)))
                             for c,m in zip(df.cell_id,df.date.dt.month)])
        return np.clip(self.linear.predict(df[['era5_sm_prev']]),0,1)


def make_model(algorithm,seed,parameters,device='cpu'):
    if algorithm=='random_forest':
        estimator=RandomForestRegressor(random_state=seed,n_jobs=2,**parameters)
    elif algorithm=='xgboost':
        try:from xgboost import XGBRegressor
        except ImportError as e:raise ImportError('Install xgboost or xgboost-cpu before training') from e
        estimator=XGBRegressor(random_state=seed,n_jobs=2,tree_method='hist',device=device,
                               objective='reg:squarederror',**parameters)
    else:raise ValueError('Unknown algorithm')
    # No early stopping on test. Two fixed capacity candidates are selected on val only.
    return Pipeline([('features',FeatureUnion([
        ('values',SimpleImputer(strategy='median',keep_empty_features=True)),
        ('missing',MissingIndicator(features='all',error_on_new=False))])),('model',estimator)])


def predict_entry(entry,frame):
    if entry['algorithm']=='baseline':return entry['estimator'].predict(frame)
    return np.clip(entry['estimator'].predict(frame[entry['features']]),0,1)


def fit_experiment(frame,config,directory,device='cpu',software_check=False,verbose=True):
    out=Path(directory)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new run folder; results are protected')
    if software_check and not config.get('synthetic'):raise ValueError('Reduced software-check settings require fictional data')
    audit=audit_frame(frame,config,require_complete=not software_check)
    partitions={s:frame[(frame.split==s)&frame.target_sm.notna()].copy()
                for s in ['train','val','calibration']}
    if any(not len(v) for v in partitions.values()):raise ValueError('Need observed train, val and calibration targets')
    train,val,cal=[partitions[s] for s in ['train','val','calibration']]
    out.mkdir(parents=True,exist_ok=True)
    save_json(out/'planned_configuration.json',config)
    entries={};selection=[]
    def keep(name,entry):
        vp=predict_entry(entry,val);cp=predict_entry(entry,cal)
        entry['validation']=summarize(val,vp)
        entry['calibration']=cluster_calibration(cal,cp,config['alpha'])
        entries[name]=entry
        selection.append({'name':name,'validation_macro_cell_rmse':entry['validation']['macro_cell_rmse'],
                          'algorithm':entry['algorithm'],'features':entry.get('features',[]),
                          'parameters':entry.get('parameters',{}),'seed':entry.get('seed')})
    for name in ['global_mean','seasonal_cell','era5_linear']:
        keep(name,{'algorithm':'baseline','estimator':Baseline(name).fit(train),'kind':name})
    for algorithm in config['algorithms']:
        if algorithm=='random_forest':
            grid=[dict(n_estimators=40 if software_check else 150,max_depth=8,min_samples_leaf=5),
                  dict(n_estimators=40 if software_check else 150,max_depth=10,min_samples_leaf=10)]
        else:
            grid=[dict(n_estimators=40 if software_check else 250,max_depth=3,learning_rate=.05,subsample=.9,colsample_bytree=.9),
                  dict(n_estimators=40 if software_check else 350,max_depth=5,learning_rate=.03,subsample=.9,colsample_bytree=.9)]
        for group,features in FEATURE_GROUPS.items():
            for seed in config['seeds']:
                if verbose:print(f'Fitting {algorithm} / {group} / seed {seed}; selection uses validation only',flush=True)
                best=None
                for params in grid:
                    estimator=make_model(algorithm,seed,params,device)
                    estimator.fit(train[features],train.target_sm)
                    score=summarize(val,np.clip(estimator.predict(val[features]),0,1))['macro_cell_rmse']
                    if best is None or score<best[0]:best=(score,estimator,params)
                _,estimator,params=best
                keep(f'{algorithm}_{group}_seed{seed}',{'algorithm':algorithm,'estimator':estimator,
                     'features':features,'feature_group':group,'parameters':params,'seed':seed})
    selected=min(selection,key=lambda r:(r['validation_macro_cell_rmse'],r['name']))['name']
    ranges={col:[float(train[col].min()),float(train[col].max())]
            for col in FEATURES if train[col].notna().any()}
    import sklearn
    try:
        import xgboost
        xgboost_version=xgboost.__version__
    except ImportError:
        xgboost_version=None
    metadata={'configuration':config,'snapshot_sha256':frame_digest(frame),'source_sha256':code_hashes(),
              'selected_model':selected,'selection_split':'val','calibration_split':'calibration',
              'software_check':software_check,'environment':{'python':platform.python_version(),
              'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,
              'xgboost':xgboost_version},'device':device,
              'training_cell_counts':train.groupby('cell_id').size().to_dict(),'training_feature_ranges':ranges}
    out.mkdir(parents=True,exist_ok=True)
    joblib.dump(entries,out/'models.joblib',compress=3)
    save_json(out/'metadata.json',metadata);save_json(out/'input_audit.json',audit)
    save_json(out/'validation_selection.json',{'selected_model':selected,'models':selection})
    save_json(out/'calibration.json',{k:e['calibration'] for k,e in entries.items()})
    return metadata,pd.DataFrame(selection)


def freeze_experiment(directory,protocol_note):
    out=Path(directory)
    if len(protocol_note.strip())<30:raise ValueError('Record a concrete frozen question, comparisons and primary outcome')
    if (out/'frozen_protocol.json').exists():raise ValueError('Protocol already frozen')
    if (out/'final_test').exists():raise ValueError('Cannot newly freeze a protocol after test inspection')
    meta=json.loads((out/'metadata.json').read_text())
    if meta['source_sha256']!=code_hashes():raise ValueError('Source changed since training; use a new reproducible run')
    frozen={'protocol_note':protocol_note,'snapshot_sha256':meta['snapshot_sha256'],
            'models_sha256':hashlib.sha256((out/'models.joblib').read_bytes()).hexdigest(),
            'metadata_sha256':hashlib.sha256((out/'metadata.json').read_bytes()).hexdigest(),
            'source_sha256':code_hashes(),'notice':'Local analysis freeze, not external preregistration or approval.'}
    save_json(out/'frozen_protocol.json',frozen)
    return frozen


def load_frozen(frame,directory):
    out=Path(directory);frozen_path=out/'frozen_protocol.json'
    if not frozen_path.exists():raise ValueError('Freeze the validation-selected protocol before final testing')
    meta=json.loads((out/'metadata.json').read_text());frozen=json.loads(frozen_path.read_text())
    if frame_digest(frame)!=frozen['snapshot_sha256']:raise ValueError('Dataset changed since protocol freeze')
    if code_hashes()!=frozen['source_sha256']:raise ValueError('Source changed since protocol freeze')
    for name,key in [('models.joblib','models_sha256'),('metadata.json','metadata_sha256')]:
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=frozen[key]:raise ValueError('Run artifact changed')
    # Only load trusted files generated by this pipeline; joblib is not safe for unknown uploads.
    return meta,joblib.load(out/'models.joblib')


def support_flags(frame,meta):
    count=frame.cell_id.map(meta['training_cell_counts']).fillna(0)
    unsupported=count<meta['configuration']['minimum_cell_training_targets']
    outside=np.zeros(len(frame),bool)
    for col,(lo,hi) in meta['training_feature_ranges'].items():
        outside|=((frame[col]<lo)|(frame[col]>hi)).fillna(False).to_numpy()
    return pd.DataFrame({'unsupported_cell':unsupported.to_numpy(),'outside_training_ranges':outside,
                         'low_radar_coverage':frame.sar_valid_fraction.fillna(0).to_numpy()<.1,
                         'missing_vegetation':frame.evi.isna().to_numpy()})


def evaluate_final(frame,directory,allow_final_test=False):
    if not allow_final_test:raise ValueError('Final test is disabled; explicitly enable only after protocol freeze')
    meta,entries=load_frozen(frame,directory);out=Path(directory)/'final_test'
    if out.exists():raise ValueError('Final test outputs already exist; do not silently tune/rewrite them')
    test=frame[frame.split=='test'].copy().reset_index(drop=True)
    if not test.target_sm.notna().any():raise ValueError('No observed final-test reference targets')
    out.mkdir();report={};predictions={}
    for name,entry in entries.items():
        p=predict_entry(entry,test);predictions[name]=p
        value=summarize(test,p);value['block_uncertainty']=block_interval(test,p)
        radius=entry['calibration']['radius'];known=test.target_sm.notna().to_numpy()
        covered=np.abs(test.target_sm.to_numpy()-p)<=radius
        value['empirical_interval_coverage']=float(covered[known].mean())
        widths=np.minimum(p+radius,1)-np.maximum(p-radius,0)
        value['mean_prediction_interval_width']=float(widths[known].mean())
        daily=pd.DataFrame({'date':test.loc[known,'date'],'covered':covered[known]}).groupby('date').covered.all()
        value['empirical_daily_simultaneous_coverage']=float(daily.mean())
        value['interval_radius']=radius
        subsets={}
        for key,labels in [('season',np.where(test.date.dt.month.isin([6,7,8,9,10]),'Jun-Oct','Nov-May')),
                           ('forest_fraction_bin',pd.cut(test.forest_fraction,[-.001,.3,.7,1.001],labels=['low','mixed','high'])),
                           ('slope_bin',pd.cut(test.slope_deg,[-.001,5,15,90],labels=['0-5','5-15','15+']))]:
            subsets[key]={str(k):scores(test.loc[np.asarray(labels)==k,'target_sm'],p[np.asarray(labels)==k])
                          for k in pd.unique(labels) if pd.notna(k)}
        value['subgroups']=subsets;report[name]=value
    paired={}
    for algorithm in meta['configuration']['algorithms']:
        for seed in meta['configuration']['seeds']:
            climate=f'{algorithm}_climate_seed{seed}'
            for group in ['climate_raw_sar','climate_rtc_sar']:
                name=f'{algorithm}_{group}_seed{seed}'
                paired[name+'_minus_climate']=paired_block_delta(test,predictions[name],predictions[climate])
    save_json(out/'metrics.json',{'models':report,'paired_sensor_comparisons':paired,
              'notice':'SMAP-product reconstruction on observed QA-passing targets; no independent field accuracy claim.'})
    test_out=test[['date','cell_id','lon','lat','target_sm','missing_reason']].copy()
    for name,p in predictions.items():test_out[name]=p
    test_out.to_csv(out/'all_model_predictions.csv',index=False)
    # Reconstruct only missing usable targets; preserve original QA-passing observations.
    chosen=entries[meta['selected_model']];p=predict_entry(chosen,frame);flags=support_flags(frame,meta)
    p[flags.unsupported_cell.to_numpy()]=np.nan
    reconstruction=frame[['date','cell_id','lon','lat','target_sm','missing_reason']].reset_index(drop=True).copy()
    reconstruction=pd.concat([reconstruction,flags],axis=1)
    reconstruction['model_prediction']=p
    reconstruction['complete_sm']=reconstruction.target_sm.fillna(reconstruction.model_prediction)
    reconstruction['is_reconstructed']=reconstruction.target_sm.isna()&reconstruction.model_prediction.notna()
    radius=chosen['calibration']['radius']
    reconstruction['prediction_lower']=np.maximum(p-radius,0);reconstruction['prediction_upper']=np.minimum(p+radius,1)
    reconstruction.to_csv(out/'selected_model_reconstruction.csv',index=False)
    save_json(out/'interpretation.json',{'selected_model':meta['selected_model'],'model_selection':'validation only',
              'interval_method':chosen['calibration'],'support_flags':'Range checks are simple diagnostics, not full out-of-distribution detection.',
              'abstention':'Predictions withheld where too few QA-passing training targets exist for a cell.',
              'retrospective_notice':'Training-period reconstruction is not out-of-sample validation; final metrics use only the locked test period.'})
    return report,reconstruction
