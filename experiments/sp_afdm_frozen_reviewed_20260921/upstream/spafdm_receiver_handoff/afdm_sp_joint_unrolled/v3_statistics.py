"""Evaluation-only exact residual decomposition; no noise estimator claim."""
import numpy as np


def residual_decomposition(y,H,Hhat,pilot,data,mean):
    arrays=[np.asarray(x) for x in (y,H,Hhat,pilot,data,mean)]
    if any(not np.isfinite(a).all() for a in arrays):raise ValueError('finite residual inputs required')
    y,H,Hhat,pilot,data,mean=arrays
    if H.shape!=(len(y),len(y)) or Hhat.shape!=H.shape or any(x.shape!=y.shape for x in (pilot,data,mean)):
        raise ValueError('residual model dimensions disagree')
    noise=y-H@(pilot+data)
    terms=dict(channel=(H-Hhat)@(pilot+mean),data=H@(data-mean),noise=noise)
    residual=y-Hhat@(pilot+mean)
    total=sum(terms.values())
    norm=max(np.linalg.norm(residual),np.linalg.norm(y),np.finfo(y.real.dtype).tiny)
    energy={name:float(np.vdot(a,a).real)/len(y) for name,a in terms.items()}
    names=list(terms)
    cross={f'{a}:{b}':float(2*np.vdot(terms[a],terms[b]).real)/len(y)
           for i,a in enumerate(names) for b in names[i+1:]}
    residual_ms=float(np.vdot(residual,residual).real)/len(y)
    return dict(component_mean_squares=energy,cross_terms=cross,residual_mean_square=residual_ms,
        relative_vector_closure=float(np.linalg.norm(residual-total)/norm),
        energy_closure=residual_ms-sum(energy.values())-sum(cross.values()),
        semantics='exact decomposition; residual mean square is not thermal variance')
