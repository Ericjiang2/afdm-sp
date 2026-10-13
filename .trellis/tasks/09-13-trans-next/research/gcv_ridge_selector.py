"""Classical conditional GCV control; not calibrated SP feedback risk."""
import numpy as np


def select_ridge(A, y, previous):
    A = np.asarray(A, dtype=np.complex128)
    y = np.asarray(y, dtype=np.complex128)
    previous = np.asarray(previous, dtype=np.complex128)
    if (A.ndim != 2 or not 0 < A.shape[1] < A.shape[0]
            or y.shape != (A.shape[0],) or previous.shape != (A.shape[1],)
            or any(not np.isfinite(v).all() for v in (A,y,previous))):
        raise ValueError('finite tall design and matching observed vectors required')
    n, p = A.shape
    scale = float(np.vdot(A,A).real/p)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('positive finite design energy required')
    residual = y-A@previous
    U, singular, Vh = np.linalg.svd(A, full_matrices=False)
    rotated = U.conj().T@residual
    rows = []; deltas = []
    for exponent in range(-3,4):
        regularization = scale*10.**exponent
        fraction = singular**2/(singular**2+regularization)
        delta = Vh.conj().T@(singular/(singular**2+regularization)*rotated)
        remaining = residual-A@delta
        freedom = float(fraction.sum())
        score = float(np.vdot(remaining,remaining).real/n/(1-freedom/n)**2)
        if not np.isfinite(score) or not np.isfinite(delta).all():
            raise ValueError('nonfinite spectral ridge result')
        rows.append(dict(exponent=exponent,regularization=regularization,
                         degrees_of_freedom=freedom,score=score,no_update=False))
        deltas.append(delta)
    rows.append(dict(exponent=None,regularization=None,degrees_of_freedom=0.,
                     score=float(np.vdot(residual,residual).real/n),no_update=True))
    deltas.append(np.zeros(p,dtype=np.complex128))
    selected = min(range(len(rows)),key=lambda i:(rows[i]['score'],-i))
    return dict(candidates=rows,candidate_deltas=np.stack(deltas),selected_index=selected,
                selected_regularization=rows[selected]['regularization'],
                no_update=rows[selected]['no_update'],delta=deltas[selected],
                singular_values=singular,scale=scale,SVD_calls=1,spectral_ridge_candidates=7)
