"""Phase-only high-order ambiguity potential; no observation inputs or RNG."""
import numpy as np


def evaluate(phase):
    phase = np.asarray(phase)
    if phase.ndim != 1 or len(phase) < 8 or len(phase) % 4 or not np.isfinite(phase).all() or np.iscomplexobj(phase):
        raise ValueError('finite real phase vector of length N>=8 divisible by four required')
    n = len(phase)
    j, k = np.arange(n), np.arange(1, n)
    w = np.exp(1j*phase)
    shifted = (j[None, :]-k[:, None]) % n
    q = w[None, :]*w[shifted].conj()
    character = np.exp(8j*np.pi*j[:, None]*np.arange(n//4)[None, :]/n)
    ambiguity = q@character/n
    squared = abs(ambiguity)**2
    total = float(np.sum(squared**8))
    if not np.isfinite(total) or total <= 0:
        raise FloatingPointError('invalid positive high-order potential')
    loss = total**(1/8)
    weighted = squared**7*ambiguity.conj()/total**(7/8)
    contributions = q*(weighted@character.T)
    forward = (j[None, :]+k[:, None]) % n
    gradient = -2*np.imag(contributions-contributions[np.arange(n-1)[:, None], forward]).sum(axis=0)/n
    Q = float(np.sum(squared[np.array([n//4, n//2, 3*n//4])-1, 0]))
    if not np.isfinite(gradient).all():
        raise FloatingPointError('nonfinite phase derivative')
    return dict(loss=loss, gradient=gradient, mu=float(np.sqrt(squared.max())),
                Q=Q, energy=float(squared.sum()))
