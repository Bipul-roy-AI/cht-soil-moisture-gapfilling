"""Scores over real target cells; block intervals preserve date clusters."""
import numpy as np
import pandas as pd


def scores(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float);v=np.isfinite(y)&np.isfinite(p);y=y[v];p=p[v]
    if not len(y):return {'n':0,'rmse':None,'bias':None,'mae':None,'ubrmse':None,'r2':None,'correlation':None}
    e=p-y;denom=((y-y.mean())**2).sum()
    return {'n':len(y),'rmse':float(np.sqrt(np.mean(e*e))),'bias':float(e.mean()),
            'mae':float(np.abs(e).mean()),'ubrmse':float(np.sqrt(np.mean((e-e.mean())**2))),
            'r2':float(1-(e*e).sum()/denom) if denom>0 else None,
            'correlation':float(np.corrcoef(y,p)[0,1]) if len(y)>1 and np.std(y)>0 and np.std(p)>0 else None}


def summarize(frame,prediction):
    d=frame[['cell_id','date','target_sm']].copy();d['prediction']=np.asarray(prediction)
    per_cell={str(k):scores(g.target_sm,g.prediction) for k,g in d.groupby('cell_id')}
    rmses=[m['rmse'] for m in per_cell.values() if m['rmse'] is not None]
    return {'micro':scores(d.target_sm,d.prediction),'macro_cell_rmse':float(np.mean(rmses)) if rmses else None,
            'cells_scored':len(rmses),'per_cell':per_cell}


def cluster_calibration(frame,prediction,alpha=.1):
    d=frame[['date','target_sm']].copy();d['error']=np.abs(d.target_sm-np.asarray(prediction))
    # Keep spatial dependence within a day; day-to-day exchangeability is not guaranteed.
    maxima=d.groupby('date').error.max().dropna().to_numpy()
    if len(maxima)<20:raise ValueError('Need >=20 calibration dates; this is a reporting guard, not a sufficiency guarantee')
    k=int(np.ceil((len(maxima)+1)*(1-alpha)))
    if k>len(maxima):raise ValueError('Too few calibration dates for requested tail probability')
    return {'radius':float(np.sort(maxima)[k-1]),'alpha':alpha,'dates':len(maxima),
            'method':'split calibration using maximum absolute error per date',
            'caveat':'Nominal daily simultaneous coverage requires exchangeable day clusters; temporal dependence/domain shift can violate it. Empirical coverage must be reported.'}


def block_interval(frame,prediction,block_days=14,repetitions=500,seed=2025):
    d=frame[['date','target_sm']].copy();d['prediction']=np.asarray(prediction)
    d=d.dropna();d['block']=((d.date-d.date.min()).dt.days//block_days).astype(int)
    d['sse']=(d.prediction-d.target_sm)**2
    blocks=d.groupby('block').agg(sse=('sse','sum'),n=('sse','size'))
    if len(blocks)<10:return {'rmse_95_interval':None,'reason':'Fewer than ten date blocks; report descriptive scores'}
    rng=np.random.default_rng(seed);indices=rng.integers(len(blocks),size=(repetitions,len(blocks)))
    est=np.sqrt(blocks.sse.to_numpy()[indices].sum(axis=1)/blocks.n.to_numpy()[indices].sum(axis=1))
    return {'rmse_95_interval':np.quantile(est,[.025,.975]).tolist(),'block_days':block_days,
            'method':'non-overlapping calendar-block percentile bootstrap',
            'caveat':'A conditional uncertainty diagnostic; validate block length and sensitivity. Does not include reference bias or novel missing conditions.'}


def paired_block_delta(frame,pred_a,pred_b,block_days=14,repetitions=500,seed=2025):
    """RMSE(A)-RMSE(B): negative favours A; resample the same dates for both."""
    d=frame[['date','target_sm']].copy();d['a']=pred_a;d['b']=pred_b;d=d.dropna()
    d['block']=((d.date-d.date.min()).dt.days//block_days).astype(int)
    d['a2']=(d.a-d.target_sm)**2;d['b2']=(d.b-d.target_sm)**2
    blocks=d.groupby('block').agg(a2=('a2','sum'),b2=('b2','sum'),n=('a2','size'))
    delta=scores(d.target_sm,d.a)['rmse']-scores(d.target_sm,d.b)['rmse']
    if len(blocks)<10:return {'rmse_delta_a_minus_b':delta,'interval':None}
    rng=np.random.default_rng(seed);indices=rng.integers(len(blocks),size=(repetitions,len(blocks)))
    count=blocks.n.to_numpy()[indices].sum(axis=1)
    values=np.sqrt(blocks.a2.to_numpy()[indices].sum(axis=1)/count)-np.sqrt(blocks.b2.to_numpy()[indices].sum(axis=1)/count)
    return {'rmse_delta_a_minus_b':delta,'interval':np.quantile(values,[.025,.975]).tolist(),
            'block_days':block_days,'caveat':'Paired calendar-block bootstrap; sensitivity and domain-shift limitations apply.'}
