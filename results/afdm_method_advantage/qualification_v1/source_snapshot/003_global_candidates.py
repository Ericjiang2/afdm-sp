"""v2: globally nominate legal basis directions using observed residual influence.

Independent module; v1 sources remain unchanged. The only search intervention is
which 12 free directions are reachable. Both v2 controls use the same bounded
best-first search with nuisance-projected local previews and gain-profile final
scores; residual/projected switches nomination only, isolating that mechanism.
"""
import heapq
import time
import numpy as np
from candidates import binary_matrix,reliable_basis,symbols,PhysicalScore
from profile_geometry import ProfileGeometry,channel_jacobian,realify


def nominate(basis,llr,channel,y,pilot,sigma2,scale,nuisance_precision,mode,branching):
    """One apply, one adjoint, G.T bit-gradient; no per-basis physical enumeration."""
    if mode not in ('residual','projected'):raise ValueError('unknown nomination mode')
    anchor=basis['anchor'];g=basis['generator'];free=basis['free'];n=channel.n
    x=np.asarray(pilot)+symbols(anchor,scale)
    j=channel_jacobian(channel,x)
    geometry=ProfileGeometry(j,sigma2/2,nuisance_precision*np.eye(j.shape[1]))
    r=realify(channel.apply(x)-np.asarray(y))
    w=geometry.apply(r) if mode=='projected' else 2*r/sigma2
    adj=channel.adjoint(w[:n]+1j*w[n:])
    signs=1-2*anchor.astype(float)
    bit_gradient=-np.sqrt(2)*scale*np.r_[signs[:n]*adj.real,signs[n:]*adj.imag]
    influence=g.T@bit_gradient
    order=np.lexsort((free,influence))
    return order[:branching],influence,geometry


def acquire_global(h,llr,channel,y,pilot,sigma2,*,scale,mode='geometry',list_size=16,
                   branching=12,max_depth=3,gain_precision=0.,nuisance_precision=.1,
                   known_channel=False):
    """Same call shape as v1: mode osd→residual, geometry→projected nomination.

    known_channel is deliberately not supported in v2; use v1 for that contract.
    Nomination is once at the common anchor. Queue preview/scoring are identical
    across v2 modes. All actual work and calls are counted, including adjoint.
    """
    start=time.perf_counter()
    if mode not in ('osd','geometry') or known_channel:raise ValueError('v2 mode/known-channel scope invalid')
    if any(type(v) is not int or v<1 for v in (list_size,branching,max_depth)):raise ValueError('invalid integer budgets')
    if not np.isfinite(nuisance_precision) or nuisance_precision<0:raise ValueError('invalid nuisance precision')
    h=binary_matrix(h)
    if h.shape[1]!=2*channel.n:raise ValueError('I-then-Q code dimension mismatch')
    physical=PhysicalScore(channel,y,pilot,sigma2,scale,gain_precision)
    t=time.perf_counter();basis=reliable_basis(h,llr);basis_seconds=time.perf_counter()-t
    anchor,g,free=basis['anchor'],basis['generator'],basis['free']
    nomination_mode='residual' if mode=='osd' else 'projected'
    t=time.perf_counter()
    moves,influence,geometry=nominate(basis,llr,channel,y,pilot,sigma2,scale,nuisance_precision,nomination_mode,branching)
    nomination_seconds=time.perf_counter()-t
    previews=[];preview_seconds=0.
    def make_word(pattern):
        word=anchor.copy()
        for p in pattern:word^=g[:,p]
        return word
    def priority(pattern,word):
        nonlocal preview_seconds
        begin=time.perf_counter()
        r=realify(channel.apply(np.asarray(pilot)+symbols(word,scale))-np.asarray(y))
        value=float(.5*geometry.value(r));preview_seconds+=time.perf_counter()-begin
        previews.append(dict(pattern=list(pattern),surrogate=value))
        return value
    heap=[(priority((),anchor),(),anchor)];seen={()}
    candidates=[];scores=[];gains=[];patterns=[]
    while heap and len(candidates)<list_size:
        _,pattern,word=heapq.heappop(heap)
        value,gain=physical(word)
        candidates.append(word);scores.append(value);gains.append(gain);patterns.append(list(pattern))
        if len(candidates)>=list_size or len(pattern)>=max_depth:continue
        for p in moves:
            if int(p) in pattern:continue
            child=tuple(sorted((*pattern,int(p))))
            if child in seen:continue
            seen.add(child);candidate=make_word(child)
            heapq.heappush(heap,(priority(child,candidate),child,candidate))
    winner=min(range(len(scores)),key=lambda i:(scores[i],patterns[i]))
    return dict(decoded=candidates[winner].copy(),gains=gains[winner].copy(),candidates=np.asarray(candidates),scores=np.asarray(scores),selected=winner,patterns=patterns,previews=previews,anchor=anchor,free=free,moves=moves,nomination_influence=influence,nomination_mode=nomination_mode,mechanism_version='global_v2',
        counts=dict(physical_scores=physical.calls,geometry_prescreens=len(previews),unique_candidates=len(candidates),channel_apply_calls=len(previews)+1,channel_adjoint_calls=1,regressor_calls=physical.calls,jacobian_regressor_calls=2,basis_influence_matvecs=1),
        timing=dict(total_seconds=time.perf_counter()-start,basis_seconds=basis_seconds,nomination_seconds=nomination_seconds,prescreen_seconds=preview_seconds,physical_score_seconds=physical.seconds),
        scope='global first-order direction nomination; fixed anchor projected previews and fixed-Doppler gain-profile scores; no truth input',mode=mode)
