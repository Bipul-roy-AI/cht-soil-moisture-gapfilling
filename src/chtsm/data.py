"""Explicit observational units, split gates and immutable export snapshots."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

CLIMATE = ['rain_1d_mm','rain_3d_mm','rain_7d_mm','rain_14d_mm','temp_3d_c',
           'era5_sm_prev','evi','evi_age_days','evi_valid_fraction',
           'doy_sin','doy_cos','elevation_m','slope_deg','forest_fraction']
RAW = ['raw_vv_db','raw_vh_db','raw_vh_vv_db','sar_age_days','sar_count','sar_valid_fraction']
RTC = ['rtc_vv_db','rtc_vh_db','rtc_vh_vv_db','sar_age_days','sar_count','sar_valid_fraction']
FEATURE_GROUPS = {'climate': CLIMATE, 'climate_raw_sar': CLIMATE+RAW,
                  'climate_rtc_sar': CLIMATE+RTC}
FEATURES = list(dict.fromkeys(CLIMATE+RAW+RTC))
PROVENANCE = ['smap_collection','grid_id','smap_image_id','s1_image_ids','evi_image_ids',
              'boundary_source','feature_version','export_config_id','export_code_id','synthetic']
REQUIRED = ['date','cell_id','lon','lat','sm_raw','sm_qa','target_present']+FEATURES+PROVENANCE


def read_config(path):
    c = json.loads(Path(path).read_text())
    validate_config(c)
    return c


def export_config_id(config):
    keys=['study_start','study_end_exclusive','smap_collection','districts','orbit_pass',
          'relative_orbit','sar_window_days','evi_lookback_days','rtc_model','terrain_buffer_m',
          'landcover_reference_year','mode','export_nodata']
    return hashlib.sha256(json.dumps({k:config.get(k) for k in keys},sort_keys=True).encode()).hexdigest()[:20]


def validate_config(c):
    if c.get('schema_version') != 'chtsm-v2':
        raise ValueError('Use a chtsm-v2 configuration')
    splits = c.get('split_years', {})
    if set(splits) != {'train','val','calibration','test'} or not all(splits.values()):
        raise ValueError('Four non-empty year sets are required')
    if any(not isinstance(y,int) for years in splits.values() for y in years):
        raise ValueError('Split years must be integers')
    order = [splits[k] for k in ['train','val','calibration','test']]
    if any(max(a)>=min(b) for a,b in zip(order,order[1:])):
        raise ValueError('Split years must be disjoint and chronological')
    if not 0<c['alpha']<1:raise ValueError('alpha must lie between zero and one')
    if c.get('training_row_cap') is not None:
        raise ValueError('Row subsampling is disabled: explicitly design grouped sampling first')


def save_json(path, value):
    def clean(x):
        if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)):return [clean(v) for v in x]
        if isinstance(x,(np.integer,)):return int(x)
        if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
        return x
    Path(path).write_text(json.dumps(clean(value),indent=2,allow_nan=False)+'\n')


def frame_digest(df):
    cols=sorted(df.columns)
    canonical=df[cols].sort_values(['date','cell_id']).to_csv(index=False,date_format='%Y-%m-%d',float_format='%.12g')
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_exports(paths, config, allow_synthetic=False):
    """Load named export CSVs; never glob arbitrary legacy target/feature files."""
    validate_config(config)
    if not paths:raise ValueError('No export files supplied')
    frames=[]
    for p in paths:
        a=pd.read_csv(p,dtype={'cell_id':str,'grid_id':str})
        missing=set(REQUIRED)-set(a)
        if missing:raise ValueError(f'{Path(p).name}: missing v2 columns {sorted(missing)}')
        frames.append(a)
    return validate_frame(pd.concat(frames,ignore_index=True), config, allow_synthetic)


def validate_frame(df,config,allow_synthetic=False):
    validate_config(config);a=df.copy()
    missing=set(REQUIRED)-set(a)
    if missing:raise ValueError(f'Missing v2 columns: {sorted(missing)}')
    a['date']=pd.to_datetime(a.date,errors='raise').dt.normalize()
    if a[['date','cell_id']].isna().any().any() or (a.cell_id.astype(str).str.len()==0).any():
        raise ValueError('Missing observational unit')
    if a.duplicated(['date','cell_id']).any():raise ValueError('Duplicate cell/date targets or duplicated export parts')
    a['cell_id']=a.cell_id.astype(str)
    a['synthetic']=a.synthetic.astype(str).str.lower().map({'true':True,'false':False,'1':True,'0':False})
    if a.synthetic.isna().any():raise ValueError('synthetic must be an explicit boolean')
    if a.synthetic.nunique()!=1 or bool(a.synthetic.iloc[0])!=bool(config.get('synthetic',False)):
        raise ValueError('Mixed or incorrectly declared synthetic data')
    if a.synthetic.any() and not allow_synthetic:raise ValueError('Fictional fixtures require explicit opt-in')
    for col in FEATURES+['sm_raw','sm_qa','target_present','lon','lat']:
        a[col]=pd.to_numeric(a[col],errors='raise')
    # Temporary CSV nodata sentinels are decoded BEFORE feature fitting/analysis.
    a[FEATURES]=a[FEATURES].replace(config.get('export_nodata',-9999),np.nan)
    a['sm_raw']=a.sm_raw.replace(config.get('export_nodata',-9999),np.nan)
    if np.isinf(a[FEATURES+['sm_raw']].to_numpy()).any():raise ValueError('Infinite feature/target values')
    if not a.target_present.isin([0,1]).all():raise ValueError('target_present must be 0 or 1')
    if not a.sm_qa.isin([0,1,255]).all():raise ValueError('GEE simplified QA must be 0,1,255; not native HDF bitfields')
    if ((a.target_present==1)&a.sm_raw.isna()).any():raise ValueError('Present target lacks a value')
    if ((a.target_present==0)&a.sm_raw.notna()).any():raise ValueError('Absent target has an unexplained value')
    observed=a.sm_raw.dropna()
    if not observed.between(0,1).all():raise ValueError('Volumetric target outside [0,1]')
    if not a.lon.between(-180,180).all() or not a.lat.between(-90,90).all():raise ValueError('Invalid coordinates')
    if a.smap_collection.nunique()!=1 or a.smap_collection.iloc[0]!=config['smap_collection']:
        raise ValueError('Product version mismatch or silently stitched versions')
    if a.grid_id.nunique()!=1:raise ValueError('Mixed target grids')
    for col in ['feature_version','boundary_source','export_code_id','export_config_id']:
        if a[col].isna().any() or a[col].nunique()!=1:raise ValueError(f'Mixed/missing {col}')
    if a.export_config_id.iloc[0]!=export_config_id(config):raise ValueError('Export configuration changed: do not mix or silently relabel old exports')
    if a.feature_version.iloc[0]!='chtsm-v2':raise ValueError('Stale predictor export')
    for col in ['smap_collection','smap_image_id','s1_image_ids','evi_image_ids','grid_id']:
        if a[col].isna().any():raise ValueError(f'Missing provenance: {col}; use explicit NONE when unavailable')
    if ((a.target_present==1)&(a.smap_image_id=='NONE')).any():raise ValueError('Observed target has no image ID')
    for col in ['forest_fraction','evi_valid_fraction','sar_valid_fraction']:
        if not a[col].dropna().between(0,1.000001).all():raise ValueError(f'Invalid fraction: {col}')
    for col in ['rain_1d_mm','rain_3d_mm','rain_7d_mm','rain_14d_mm','sar_age_days','evi_age_days','sar_count']:
        if (a[col].dropna()<0).any():raise ValueError(f'Negative {col}')
    # A ratio in dB is a difference, not division of logarithmic band values.
    for prefix in ['raw','rtc']:
        v=a[[prefix+'_vh_vv_db',prefix+'_vh_db',prefix+'_vv_db']].dropna()
        if not np.allclose(v.iloc[:,0],v.iloc[:,1]-v.iloc[:,2],atol=1e-4):
            raise ValueError('Incorrect polarization ratio or inconsistent aggregation')
    # Static cell properties and grid coordinates must actually be stable.
    for col in ['lon','lat','forest_fraction','elevation_m','slope_deg']:
        if a.groupby('cell_id')[col].agg(lambda s:s.dropna().max()-s.dropna().min()).gt(1e-4).any():
            raise ValueError(f'{col} changes within a fixed target cell')
    a['target_sm']=a.sm_raw.where((a.target_present==1)&(a.sm_qa==0))
    a['missing_reason']=np.select([a.target_present==0,a.sm_qa!=0],
                                 ['not_present_or_nodata','retrieval_QA_rejected'],'usable_observation')
    year_map={year:key for key,years in config['split_years'].items() for year in years}
    a['split']=a.date.dt.year.map(year_map)
    if a.split.isna().any():raise ValueError('Dates outside declared experiment years')
    if (a.date<pd.Timestamp(config['study_start'])).any() or (a.date>=pd.Timestamp(config['study_end_exclusive'])).any():
        raise ValueError('Rows outside declared study interval')
    return a.sort_values(['date','cell_id']).reset_index(drop=True)


def audit_frame(df, config, require_complete=True):
    days=pd.date_range(config['study_start'],pd.Timestamp(config['study_end_exclusive'])-pd.Timedelta(days=1))
    cells=df.cell_id.unique();expected=len(days)*len(cells)
    complete=len(df)==expected and df.date.nunique()==len(days)
    if config.get('spatial_design'):
        expected=0;complete=True
        for split,years in config['split_years'].items():
            g=df[df.split==split];n_days=sum(d.year in years for d in days)
            expected+=n_days*g.cell_id.nunique()
            complete &= g.date.nunique()==n_days and len(g)==n_days*g.cell_id.nunique()
    if require_complete and not complete:
        raise ValueError(f'Incomplete cell/date export: {len(df)} rows vs {expected}; finish all monthly tasks first')
    units=df.groupby('date').agg(cells=('cell_id','count'),usable=('target_sm','count'))
    return {'rows':len(df),'cells':len(cells),'dates':df.date.nunique(),'complete_calendar':complete,
            'usable_targets':df.target_sm.notna().sum(),'missing_reasons':df.missing_reason.value_counts().to_dict(),
            'split_counts':df.groupby('split').agg(rows=('cell_id','count'),dates=('date','nunique'),usable=('target_sm','count')).to_dict('index'),
            'variable_observed_support':units.usable.nunique()>1,'snapshot_sha256':frame_digest(df),
            'notice':'Quality/coverage flags do not identify RFI causes; 9 km postings are not independent physical footprints.'}
