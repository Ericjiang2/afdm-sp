"""Stronger classical reliable-basis OSD order1; no geometry/truth nomination."""
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'acquisition'))
from candidates import binary_matrix,reliable_basis,PhysicalScore

GRID=(16,32,64,128,256,512,1024)


def acquire_osd1(h,llr,channel,y,pilot,sigma2,*,scale,k=None,full=False,gain_precision=0.):
    """Anchor plus k distinct single free-bit flips in reliability order.

    full=True emits the entire order1 list (1025 on the actual 1024-dim code).
    k is a frozen candidate count, not per-frame truth or runtime adaptation.
    Complete module timing includes GF2, all generation, physical scores and
    selection. This is not equal candidate count to global_v2 list16.
    """
    origin=time.perf_counter()
    h=binary_matrix(h)
    if h.shape[1]!=2*channel.n:raise ValueError('I-then-Q parity dimension differs')
    if type(full) is not bool or (not full and (type(k) is not int or k<1)):raise ValueError('positive fixed k or full order1 required')
    physical=PhysicalScore(channel,y,pilot,sigma2,scale,gain_precision)
    t=time.perf_counter();basis=reliable_basis(h,llr);basis_seconds=time.perf_counter()-t
    free=basis['free'];dimension=len(free)
    if full:
        if k is not None:raise ValueError('full order1 must not also specify k')
        count=dimension
    else:
        if k>dimension:raise ValueError('k exceeds code dimension')
        count=k
    moves=np.lexsort((free,abs(np.asarray(llr)[free])))[:count]
    candidates=[];scores=[];gains=[];patterns=[]
    for move in [None,*moves.tolist()]:
        word=basis['anchor'].copy()
        if move is not None:word^=basis['generator'][:,move]
        value,gain=physical(word)
        candidates.append(word);scores.append(value);gains.append(gain);patterns.append([] if move is None else [move])
    selected=min(range(len(scores)),key=lambda i:(scores[i],patterns[i]))
    return dict(decoded=candidates[selected].copy(),gains=gains[selected].copy(),candidates=np.asarray(candidates),scores=np.asarray(scores),selected=selected,patterns=patterns,anchor=basis['anchor'],free=free,moves=moves,
        method='osd1_full' if full else 'osd1_budget',mechanism_version='strong_osd1_v1',k=count,full_order1=full,
        counts=dict(physical_scores=physical.calls,unique_candidates=len(candidates),regressor_calls=physical.calls,geometry_prescreens=0,channel_apply_calls=0,channel_adjoint_calls=0,jacobian_regressor_calls=0),
        timing=dict(total_seconds=time.perf_counter()-origin,basis_seconds=basis_seconds,physical_score_seconds=physical.seconds),
        scope='anchor plus reliable-order single free flips; same exact fixed-Doppler gain-profile scorer; no truth access; unequal list sizes disclosed')
