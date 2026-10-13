"""Paired channel-cluster bootstrap with simultaneous max-|t| intervals."""
import numpy as np


def cluster_intervals(values,seed=(20260914,125851,91),draws=20000):
    values=np.asarray(values,dtype=float)
    if values.ndim!=2 or values.shape[0]<2 or not np.isfinite(values).all():
        raise ValueError('finite independent-channel by comparison matrix required')
    n,p=values.shape
    rng=np.random.default_rng(seed)
    samples=rng.integers(n,size=(draws,n))
    weights=np.zeros((draws,n),float)
    np.add.at(weights,(np.arange(draws)[:,None],samples),1)
    mean=values.mean(0);se=values.std(0,ddof=1)/np.sqrt(n)
    boot=weights@values/n
    variance=np.maximum((weights@(values*values)/n-boot*boot)/(n-1),0)
    boot_se=np.sqrt(variance)
    centered=boot-mean
    t=np.zeros_like(boot)
    np.divide(abs(centered),boot_se,out=t,where=boot_se>0)
    t[(boot_se==0)&(abs(centered)>1e-14*np.maximum(1.,abs(mean)))]=np.inf
    active=se>0
    critical=float(np.quantile(np.max(t[:,active],axis=1),.95)) if active.any() else None
    output=[]
    for j in range(p):
        usable=bool(active[j] and critical is not None and np.isfinite(critical))
        output.append(dict(mean=float(mean[j]),standard_error=float(se[j]),
            percentile_95=np.quantile(boot[:,j],[.025,.975]).tolist(),
            simultaneous_95=[float(mean[j]-critical*se[j]),float(mean[j]+critical*se[j])] if usable else None,
            inference_usable=usable,degenerate_resamples=int(np.count_nonzero(boot_se[:,j]==0))))
    return dict(channels=n,comparisons=p,draws=draws,seed=list(seed),
        critical_value=critical if critical is not None and np.isfinite(critical) else None,
        method='paired channel bootstrap-t; maximum absolute studentized statistic',rows=output)
