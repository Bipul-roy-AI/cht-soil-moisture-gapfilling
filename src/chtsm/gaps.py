"""Retrospective hidden-observation experiments and guarded temporal baselines."""
import numpy as np
import pandas as pd
from .metrics import scores
from .models import load_frozen,predict_entry
from .data import save_json
from pathlib import Path


def hidden_mask(frame,length_days,seed=2025,fraction=.15):
    if length_days<1 or not 0<fraction<1:raise ValueError('Invalid gap experiment')
    rng=np.random.default_rng(seed);hidden=np.zeros(len(frame),bool)
    for cell,g in frame.groupby('cell_id'):
        known=g[g.target_sm.notna()]
        budget=max(1,int(np.ceil(len(known)*fraction)))
        candidates=rng.permutation(known.index.to_numpy());chosen=0
        for idx in candidates:
            if chosen>=budget:break
            start=frame.loc[idx,'date'];mask=(frame.cell_id==cell)&(frame.date>=start)&(frame.date<start+pd.Timedelta(days=length_days))
            newly=mask.to_numpy()&frame.target_sm.notna().to_numpy()&~hidden
            if newly.any():hidden|=mask.to_numpy();chosen+=int(newly.sum())
    return hidden


def temporal_predictions(frame,hidden,method):
    if len(hidden)!=len(frame):raise ValueError('Mask shape mismatch')
    result=np.full(len(frame),np.nan)
    for _,g in frame.groupby('cell_id'):
        y=g.target_sm.copy();y.loc[hidden[g.index.to_numpy()]]=np.nan
        s=pd.Series(y.to_numpy(),index=pd.DatetimeIndex(g.date))
        if method=='persistence':p=s.ffill()
        elif method=='linear_interpolation':p=s.interpolate(method='time',limit_area='inside')
        else:raise ValueError('Unknown temporal comparator')
        result[g.index]=p.to_numpy()
    return result


def run_gap_experiments(frame,directory,lengths=(1,3,7,14),seeds=(42,123,2025)):
    meta,entries=load_frozen(frame,directory);test=frame[frame.split=='test'].reset_index(drop=True)
    prediction={k:predict_entry(v,test) for k,v in entries.items()};results=[]
    for length in lengths:
        for seed in seeds:
            hidden=hidden_mask(test,length,seed);reference=hidden&test.target_sm.notna().to_numpy()
            temporal={m:temporal_predictions(test,hidden,m) for m in ['persistence','linear_interpolation']}
            # Compare all methods on identical recoverable reference coverage.
            common=reference.copy()
            for p in temporal.values():common&=np.isfinite(p)
            row={'requested_gap_days':length,'seed':seed,'hidden_known_targets':int(reference.sum()),
                 'common_scored_targets':int(common.sum()),
                 'notice':'Artificial masking of observed targets, not truth for naturally missing targets. Future retained observations are allowed only for retrospective interpolation.'}
            row['models']={k:scores(test.target_sm[common],p[common]) for k,p in {**prediction,**temporal}.items()}
            results.append(row)
    out=Path(directory)/'final_test'
    if not out.exists():raise ValueError('Run the locked evaluation before additional test analyses')
    target=out/'gap_experiments.json'
    if target.exists():raise ValueError('Gap-experiment results already exist')
    save_json(target,results);return results


def spatial_subset(frame,heldout_cells,buffer_km=35):
    """Joint place/year transfer: exclude nearby cells from all fitting partitions."""
    if not heldout_cells:raise ValueError('Explicitly choose held-out cells after inspecting the grid')
    cells=frame.groupby('cell_id')[['lat','lon']].first()
    if not set(heldout_cells)<=set(cells.index):raise ValueError('Unknown held-out cell IDs')
    coords=np.radians(cells[['lat','lon']].to_numpy());hold=np.radians(cells.loc[heldout_cells,['lat','lon']].to_numpy())
    delta=coords[:,None,:]-hold[None,:,:]
    hav=np.sin(delta[:,:,0]/2)**2+np.cos(coords[:,None,0])*np.cos(hold[None,:,0])*np.sin(delta[:,:,1]/2)**2
    distances=6371*2*np.arcsin(np.sqrt(np.clip(hav,0,1)))
    fitting=set(cells.index[distances.min(axis=1)>buffer_km])
    if len(fitting)<3:raise ValueError('Spatial buffer leaves fewer than three fitting cells; narrow spatial claims or redesign the domain')
    keep=((frame.split!='test')&frame.cell_id.isin(fitting))|((frame.split=='test')&frame.cell_id.isin(heldout_cells))
    return frame.loc[keep].reset_index(drop=True),{'heldout_cells':heldout_cells,'fitting_cells':sorted(fitting),
          'buffer_km':buffer_km,'notice':'Approximate centre-distance exclusion, not exact radiometer footprint independence. Calibration-domain transfer is unverified.'}
