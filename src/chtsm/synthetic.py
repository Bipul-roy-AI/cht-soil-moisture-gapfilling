"""Explicitly fictional fixture, never Bangladesh observations or research evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import validate_frame,export_config_id


def make_fixture(config_path,seed=2025,cells=4):
    config=json.loads(Path(config_path).read_text());config['synthetic']=True
    config['seeds']=[42];config['minimum_cell_training_targets']=15
    days=pd.date_range(config['study_start'],pd.Timestamp(config['study_end_exclusive'])-pd.Timedelta(days=1))
    rng=np.random.default_rng(seed);records=[]
    for i in range(cells):
        rain=rng.gamma(.6,8,len(days));season=np.sin(2*np.pi*days.dayofyear.to_numpy()/365.25)
        raw_vv=-12+.04*rain+rng.normal(0,.6,len(days));raw_vh=raw_vv-6+rng.normal(0,.25,len(days))
        sm=np.clip(.28+.055*season+.0025*rain+.018*i+rng.normal(0,.01,len(days)),.05,.7)
        qa=np.where(rng.random(len(days))<.08,1,0);present=(rng.random(len(days))>.45).astype(int)
        for k,date in enumerate(days):
            row=dict(date=date,cell_id=f'FICTIONAL_CELL_{i}',lon=91.8+i*.08,lat=22.1+i*.08,
                     sm_raw=sm[k] if present[k] else np.nan,sm_qa=int(qa[k]) if present[k] else 255,target_present=int(present[k]),
                     rain_1d_mm=rain[k],rain_3d_mm=rain[max(0,k-2):k+1].sum(),
                     rain_7d_mm=rain[max(0,k-6):k+1].sum(),rain_14d_mm=rain[max(0,k-13):k+1].sum(),
                     temp_3d_c=25+3*season[k],era5_sm_prev=sm[max(k-1,0)]+rng.normal(0,.02),
                     evi=.4+.05*season[k],evi_age_days=24,evi_valid_fraction=.8,
                     doy_sin=np.sin(2*np.pi*date.dayofyear/365.25),doy_cos=np.cos(2*np.pi*date.dayofyear/365.25),
                     elevation_m=50+i*80,slope_deg=3+i*6,forest_fraction=.1+i*.25,
                     raw_vv_db=raw_vv[k],raw_vh_db=raw_vh[k],raw_vh_vv_db=raw_vh[k]-raw_vv[k],
                     rtc_vv_db=raw_vv[k]-.1*i,rtc_vh_db=raw_vh[k]-.1*i,rtc_vh_vv_db=raw_vh[k]-raw_vv[k],
                     sar_age_days=6,sar_count=2,sar_valid_fraction=.85,
                     smap_collection=config['smap_collection'],grid_id='FICTIONAL_GRID_NOT_REAL',
                     smap_image_id='FICTIONAL',s1_image_ids='FICTIONAL',evi_image_ids='FICTIONAL',
                     boundary_source='FICTIONAL_NO_OBSERVATIONS',feature_version='chtsm-v2',
                     export_config_id=export_config_id(config),export_code_id='FICTIONAL_EXPORTER',synthetic=True)
            records.append(row)
    frame=validate_frame(pd.DataFrame(records),config,allow_synthetic=True)
    return frame,config
