"""Legal finite local candidate metrics, plus separately called external labels."""
import numpy as np

QPSK=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])


def hard_symbols(soft):
    soft=np.asarray(soft)
    if soft.ndim!=1 or not np.isfinite(soft).all():raise ValueError('finite soft vector required')
    return .5*(np.where(soft.real<0,-1.,1.)+1j*np.where(soft.imag<0,-1.,1.))


def candidates(public):
    if set(public)!={'H','z','anchor','sigma2','constellation'}:
        raise ValueError('candidate interface accepts only five legal state fields')
    h,z,anchor=map(np.asarray,(public['H'],public['z'],public['anchor']))
    sigma=public['sigma2'];n=len(anchor)
    if (h.shape!=(n,n) or z.shape!=(n,) or anchor.shape!=(n,) or not np.isfinite(sigma) or sigma<=0
            or not np.array_equal(public['constellation'],QPSK)
            or any(not np.isfinite(x).all() for x in (h,z,anchor))
            or not np.isin(anchor,QPSK).all()):
        raise ValueError('finite matched candidate geometry and registered QPSK required')
    residual=z-h@anchor
    correlation=h.conj().T@residual
    energy=np.sum(abs(h)**2,axis=0)
    delta=QPSK[None,:]-anchor[:,None]
    # Exact D(candidate)-D(anchor); common constants never affect rank/gap.
    metric=-2*np.real(correlation.conj()[:,None]*delta)+energy[:,None]*abs(delta)**2
    order=np.argsort(metric,axis=1,kind='stable')
    best=order[:,0]
    gap=metric[np.arange(n),order[:,1]]-metric[np.arange(n),best]
    risk=1/(1+np.exp(np.minimum(gap/sigma,700)))
    return dict(candidate_ids=np.arange(n*4).reshape(n,4),anchor=anchor.copy(),
        metrics_relative_to_anchor=metric,best=best,gap=gap,
        ambiguity_risk=float(risk.mean()),per_symbol_risk=risk,
        tie_count=int(np.count_nonzero(gap==0)),zero_column_count=int(np.count_nonzero(energy==0)),
        generation_failed=False,candidate_count=4*n,scope='one-coordinate full-vector candidates')


def stability(reference,current):
    if not np.array_equal(reference['anchor'],current['anchor']):raise ValueError('fixed candidate context required')
    delta=current['metrics_relative_to_anchor']-reference['metrics_relative_to_anchor']
    bound=np.max(abs(delta),axis=1)
    certified=(reference['gap']>0)&(bound<reference['gap']/2)
    changed=reference['best']!=current['best']
    if np.any(certified&changed):raise ValueError('finite candidate sufficient condition violated')
    return dict(centered_metric_change=delta,certificate=certified,winner_changed=changed,
        certified_fraction=float(certified.mean()),changed_fraction=float(changed.mean()))


def external_coverage(candidate,truth_data):
    truth=np.asarray(truth_data)
    if truth.shape!=candidate['anchor'].shape or not np.isin(truth,QPSK).all():
        raise ValueError('external truth must match the declared symbol model')
    mismatch=candidate['anchor']!=truth
    covered=(int(mismatch.sum())-mismatch.astype(int))==0
    truth_id=np.argmin(abs(truth[:,None]-QPSK[None,:]),axis=1)
    return dict(full_vector_in_local_set=covered,coverage_fraction=float(covered.mean()),
        truth_symbol_id=truth_id,anchor_symbol_errors=int(mismatch.sum()),
        label='ORACLE_COVERAGE_NOT_AVAILABLE_ONLINE')
