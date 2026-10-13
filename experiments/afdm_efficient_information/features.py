"""Nested observed polynomial features, with exact Gaussian-control expectations."""
import time
from itertools import combinations,combinations_with_replacement

import numpy as np


LEVELS=('energy','old_T','powers','phase')


def canonical_phase(y_time):
    """O(MN) orbit representative, first argmax tie, with the zero orbit explicit."""
    y=np.asarray(y_time,complex)
    if y.ndim!=2 or not np.isfinite(y).all():
        raise ValueError('finite observation rows required')
    anchor=np.argmax(abs(y),axis=1)
    pivot=y[np.arange(len(y)),anchor]
    nonzero=abs(pivot)>0
    multiplier=np.ones(len(y),complex)
    multiplier[nonzero]=pivot[nonzero].conj()/abs(pivot[nonzero])
    return y*multiplier[:,None],anchor


def feature_catalog(n):
    """Real/imag parts of balanced complex monomials; each degree at most four."""
    if not isinstance(n,(int,np.integer)) or n<4:
        raise ValueError('N>=4 required for the nested feature definition')
    # A feature is a sparse linear combination of E prod r[a] prod r[b]*.
    def term(a,b,c=1.): return (tuple(a),tuple(b),complex(c))
    catalog=[('mean_power',[term([i],[i],1/n) for i in range(n)])]
    boundaries={'energy':len(catalog)}
    catalog.append(('mean_power_squared',[term([i,i],[i,i],1/n) for i in range(n)]))
    a=max(1,n//4); b=max(a+1,n//2); c=min(n-1,max(b+1,3*n//4))
    for j in (b,c):
        catalog.append((f'T0_{a}_{j}',[term([0,a],[0,a]),term([0,j],[0,j],-1)]))
    boundaries['old_T']=len(catalog)
    for i in range(n): catalog.append((f'power_{i}',[term([i],[i])]))
    for i,j in combinations_with_replacement(range(n),2): catalog.append((f'power_pair_{i}_{j}',[term([i,j],[i,j])]))
    boundaries['powers']=len(catalog)
    for i,j in combinations(range(n),2):
        for label,coeff in [('real',1),('imag',-1j)]:
            catalog.append((f'coherence_{i}_{j}_{label}',[term([i],[j],coeff)]))
            catalog.append((f'coherence_square_{i}_{j}_{label}',[term([i,i],[j,j],coeff)]))
            for k in range(n): catalog.append((f'weighted_coherence_{i}_{j}_{k}_{label}',[term([i,k],[j,k],coeff)]))
    boundaries['phase']=len(catalog)
    return catalog,boundaries


def observed_features(y_time):
    """Time-domain observations only; no teacher parameter or distribution label."""
    y=np.asarray(y_time,complex)
    if y.ndim!=2 or not np.isfinite(y).all():
        raise ValueError('finite time-domain observation rows required')
    start=time.perf_counter(); catalog,bounds=feature_catalog(y.shape[1]); result=[]; products=0
    for _,terms in catalog:
        value=np.zeros(len(y),complex)
        for a,b,c in terms:
            value+=c*np.prod(y[:,a],axis=1)*np.prod(y[:,b].conj(),axis=1)
            products+=len(y)*(len(a)+len(b))
        result.append(value.real)
    array=np.column_stack(result)
    output={level:array[:,:bounds[level]] for level in LEVELS}
    gauge,gauge_anchor=canonical_phase(y)
    output['gauge']=np.column_stack((gauge.real,gauge.imag))
    return output,dict(seconds=time.perf_counter()-start,
        dimensions=bounds,balanced_monomial_factor_multiplications=products,observations=len(y),
        gauge_real_dimensions=2*y.shape[1],gauge_complex_multiplications=int(y.size),
        coordinate='physical time; any required inverse DAFT must be counted by caller',truth_inputs=0)


def expected_features(covariances,weights):
    """Finite QPSK mixture of proper Gaussians, exact mean of every feature."""
    k=np.asarray(covariances,complex); weights=np.asarray(weights,float)
    if k.ndim!=3 or k.shape[1]!=k.shape[2] or weights.shape!=(len(k),) or not np.isfinite(k).all() or np.any(weights<0) or not np.isclose(weights.sum(),1.):
        raise ValueError('matching proper-Gaussian covariance mixture and normalized weights required')
    catalog,bounds=feature_catalog(k.shape[1]); values=[]
    for _,terms in catalog:
        total=0j
        for a,b,c in terms:
            if len(a)==1:
                moment=k[:,a[0],b[0]]
            else:
                moment=k[:,a[0],b[0]]*k[:,a[1],b[1]]+k[:,a[0],b[1]]*k[:,a[1],b[0]]
            total+=c*(weights @ moment)
        values.append(total.real)
    result=np.array(values)
    return {level:result[:bounds[level]] for level in LEVELS}


def sufficient_outer(y):
    y=np.asarray(y,complex)
    if y.ndim!=2 or not np.isfinite(y).all():
        raise ValueError('finite observed rows required')
    return y[:,:,None]*y[:,None,:].conj()
