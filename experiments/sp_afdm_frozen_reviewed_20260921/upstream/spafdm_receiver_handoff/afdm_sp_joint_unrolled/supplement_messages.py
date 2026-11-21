"""Observed-only decoder message consumers, not a new full receiver or cost allocation."""
import math
import time
import numpy as np
from .e1_ldpc import decode_soft_messages
from .budgeted_support_diagnostics import array_hash


def vector(value):
    raw=np.asarray(value)
    if raw.ndim!=1 or not raw.size or raw.size%2 or np.iscomplexobj(raw) or not np.isfinite(raw).all():
        raise ValueError('finite real even-length I-then-Q message required')
    return raw.astype(float)


def entropy(llr):
    x=vector(llr);p=(1+np.tanh(x/2))/2
    terms=np.zeros_like(p)
    for v in (p,1-p):
        good=v>0;terms[good]-=v[good]*np.log2(v[good])
    return float(terms.mean())


def decoder_messages(code,incoming_llr,*,maxiter=50):
    incoming=vector(incoming_llr);started=time.perf_counter()
    value=decode_soft_messages(code,incoming,maxiter)
    value['metadata']=dict(truth_access='none',bit_order='all I bits then all Q bits',
        semantics='log P(bit0)/P(bit1)',seconds=time.perf_counter()-started,
        hashes={k:array_hash(value[k]) for k in ('incoming_llr','raw_app','raw_check_extrinsic')},
        entropy_bits={k:entropy(value[k]) for k in ('incoming_llr','raw_app','raw_check_extrinsic')},
        approximation='loopy BP or early termination need not equal exact code posterior')
    return value


def consume(value,*,kind,clip=20.,damping=1.,previous=None,control='legal',sham_seed=None,amplitude=.5):
    """Detector receives check messages; CE receives shared-observation APP moments."""
    if kind not in ('detector_code_prior','CE_posterior_moments'):raise ValueError('unknown message consumer')
    if control not in ('legal','zero','fixed_sham','disabled'):raise ValueError('oracle forbidden on legal interface')
    if not math.isfinite(clip) or not 0<clip<=100 or not math.isfinite(damping) or not 0<=damping<=1:
        raise ValueError('finite clip(0,100] and damping[0,1] required')
    if not math.isfinite(amplitude) or amplitude<=0:raise ValueError('positive finite component amplitude required')
    started=time.perf_counter();key='raw_check_extrinsic' if kind=='detector_code_prior' else 'raw_app'
    raw=vector(value[key]);incoming=vector(value['incoming_llr'])
    if raw.shape!=incoming.shape:raise ValueError('message shapes differ')
    if control in ('zero','fixed_sham') and kind!='detector_code_prior':
        raise ValueError('zero/sham are extrinsic controls, never zero or shuffle CE APP')
    if control=='disabled':
        return dict(enabled=False,kind=kind,control=control,truth_access='none',seconds=time.perf_counter()-started)
    if control=='zero':working=np.zeros_like(raw)
    elif control=='fixed_sham':
        if type(sham_seed) is not int or not 0<=sham_seed<2**32:raise ValueError('explicit fixed sham seed required')
        working=raw[np.random.default_rng(sham_seed).permutation(raw.size)]
    else:
        if sham_seed is not None:raise ValueError('sham seed only for sham control')
        working=raw.copy()
    old=np.zeros_like(raw) if previous is None else vector(previous)
    if old.shape!=raw.shape:raise ValueError('previous message shape differs')
    if control=='zero':delivered=np.zeros_like(raw)
    else:delivered=np.clip((1-damping)*np.clip(old,-clip,clip)+damping*np.clip(working,-clip,clip),-clip,clip)
    result=dict(enabled=True,kind=kind,control=control,llr=delivered,
        source_message=key,raw_sha256=array_hash(raw),delivered_sha256=array_hash(delivered),
        incoming_sha256=array_hash(incoming),entropy_bits=entropy(delivered),clip=clip,damping=damping,
        sham_seed=sham_seed,truth_access='none',seconds=time.perf_counter()-started)
    if kind=='CE_posterior_moments':
        n=raw.size//2;mean=amplitude*(np.tanh(delivered[:n]/2)+1j*np.tanh(delivered[n:]/2))
        result.update(mu=mean,var=np.maximum(0,2*amplitude**2-np.abs(mean)**2),
            approximation='factorized marginal moments for same-observation approximate EM; not independent extrinsic likelihood')
    result['seconds']=time.perf_counter()-started
    return result


def oracle_symbols(symbols,*,tag):
    if tag not in ('I2','I2realloc'):raise ValueError('explicit oracle diagnostic arm tag required')
    value=np.asarray(symbols)
    if value.ndim!=1 or not value.size or not np.iscomplexobj(value) or not np.isfinite(value).all():
        raise ValueError('finite complex oracle symbols required')
    return dict(mu=value.copy(),var=np.zeros(value.size),truth_access='true_symbols_oracle',arm=tag,
        kind='oracle_CE_symbols',sha256=array_hash(value),legal_receiver_input=False)
