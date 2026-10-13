"""Headroom-ladder helpers: arm A1 refine (genie delays + multiplicity) and scoring.

New file only.  Nothing under the frozen/reviewed trees is edited.  The refine
body below is a copy of ``twofft.time_refine`` (experiments/sp_afdm_native_joint_*/src)
with ONE change: the delay list is supplied (genie, repeats kept) instead of
being the collapsed unique acquired delays.  Doppler initialisation uses only
observed quantities (acquired Dopplers at the same delay, strongest gain
first); slots with no acquired path at their delay get a coarse scan.
"""
import numpy as np
from scipy.optimize import minimize_scalar

from physical import Channel, daft, dkernel

COARSE_GRID = np.arange(-3., 3. + 1e-9, .25)


def init_dopplers(delays, ls, ks, gs):
    """Return (nu, missing_mask): per genie slot, acquired Doppler at same delay by |g| desc."""
    delays = np.asarray(delays, int)
    ls = np.asarray(ls, int)
    ks = np.asarray(ks, float)
    gs = np.asarray(gs, complex)
    nu = np.full(len(delays), np.nan)
    for d in np.unique(delays):
        slots = np.flatnonzero(delays == d)
        cand = np.flatnonzero(ls == d)
        order = cand[np.argsort(-abs(gs[cand]), kind='stable')]
        m = min(len(slots), len(order))
        nu[slots[:m]] = ks[order[:m]]
    return nu, np.isnan(nu)


def refine_fixed_delays(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, *, delays,
                        mode='soft', rounds=2):
    """Variable-projection Doppler/gain refit on a GIVEN delay list (repeats allowed)."""
    n = len(y)
    l = np.asarray(delays, int)
    if l.ndim != 1 or not len(l) or np.any(l < 0) or np.any(l >= n):
        raise ValueError('invalid supplied delay list')
    nu, missing = init_dopplers(l, ls, ks, gs)
    k = np.arange(n)
    xt = daft(np.asarray(pilot) + mu, c1, c2, True)
    Y = daft(y, c1, c2, True)
    wrap = k[:, None] - l
    base = xt[wrap % n] * np.where(wrap < 0, np.exp(2j*np.pi*c1*(n*n + 2*n*wrap)), 1.)
    if mode not in ('mean', 'scalar', 'soft'):
        raise ValueError('mode')
    vv = np.zeros(n) if mode == 'mean' else np.full(n, np.mean(v)) if mode == 'scalar' else np.asarray(v)
    dl = l[None, :] - l[:, None]
    gv = np.exp(2j*np.pi*c1*(l[:, None]**2 - l[None, :]**2)) * np.fft.fft(vv)[dl % n]
    calls = 0

    def ev(nu):
        nonlocal calls
        calls += 1
        B = base * np.exp(2j*np.pi*k[:, None]*nu/n)
        G = gv * dkernel(nu[None, :] - nu[:, None] + 2*n*c1*dl, n)
        G = (G + G.conj().T) * .5
        Q = B.conj().T @ B + G + noise*np.eye(len(l))
        b = B.conj().T @ Y
        h = np.linalg.solve(Q, b)
        return float((np.vdot(Y, Y) - np.vdot(b, h)).real), h, G

    # Missing slots: sequential coarse scan on the same objective (others held).
    nu = np.where(missing, 0., nu)
    for j in np.flatnonzero(missing):
        values = []
        for z in COARSE_GRID:
            t = nu.copy()
            t[j] = z
            values.append(ev(t)[0])
        nu[j] = COARSE_GRID[int(np.argmin(values))]
    centers = nu.copy()
    val, h, G = ev(nu)
    history = [val]
    for _ in range(rounds):
        for j, z in enumerate(centers):
            lo = max(-3., z - .75)
            hi = min(3., z + .75)

            def f(z):
                t = nu.copy()
                t[j] = z
                return ev(t)[0]
            opt = minimize_scalar(f, bounds=(lo, hi), method='bounded',
                                  options={'xatol': .002, 'maxiter': 16})
            if opt.fun < val:
                nu[j] = opt.x
                val, h, G = ev(nu)
                history.append(val)
    val, h, G = ev(nu)
    if not np.isfinite(val) or not np.isfinite(h).all():
        raise FloatingPointError('nonfinite A1 refit')
    B = base * np.exp(2j*np.pi*k[:, None]*nu/n)
    Q = B.conj().T @ B + G + noise*np.eye(len(l))
    q_min = float(np.linalg.eigvalsh((Q + Q.conj().T) * .5)[0] / noise)
    return Channel(n, c1, c2, l, nu, h), dict(
        history=history, objective=val, gamma=G, evaluations=calls, fft_count=3,
        q_min_eig_over_noise=q_min, n_missing_slots=int(missing.sum()))


def make_a1_refine(genie_delays, log=None):
    """Closure usable as ``refine_override`` in tf_production_gap_audit interventions.

    ``log`` (list) receives one small dict per refit call (round 0, round 1).
    """
    delays = np.asarray(genie_delays, int).copy()

    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kwargs):
        if len(delays) > kwargs.get('max_paths', 8):
            raise ValueError('genie slots exceed the frozen max_paths cap')
        channel, detail = refine_fixed_delays(
            y, pilot, mu, v, ls, ks, gs, c1, c2, noise, delays=delays,
            mode=kwargs.get('mode', 'soft'), rounds=kwargs.get('rounds', 2))
        if log is not None:
            log.append(dict(n_missing_slots=detail['n_missing_slots'],
                            q_min_eig_over_noise=detail['q_min_eig_over_noise'],
                            objective=detail['objective'], evaluations=detail['evaluations']))
        return channel, detail
    return refine


def logloss_bits(llr, coded):
    """Mean over coded bits of log2(1+exp(-(1-2b)L)); L = log P(0)/P(1), I-then-Q order."""
    llr = np.asarray(llr, float)
    coded = np.asarray(coded)
    if llr.shape != coded.shape or llr.ndim != 1:
        raise ValueError('LLR/coded shape differs')
    s = 1. - 2.*coded.astype(float)
    return float(np.mean(np.logaddexp(0., -s*llr)) / np.log(2.))


def missed_energy(truth_l, truth_k, truth_g, fit_delays, n=1024):
    """Fraction of physical same-delay-coherent energy at delays absent from the fit."""
    lt = np.asarray(truth_l, int)
    kt = np.asarray(truth_k, float)
    gt = np.asarray(truth_g, complex)
    R = (lt[:, None] == lt[None, :]) * dkernel(kt[None, :] - kt[:, None], n)
    missing = ~np.isin(lt, np.asarray(fit_delays, int))
    total = float(np.vdot(gt, R @ gt).real)
    lost = float(np.vdot(gt[missing], R[np.ix_(missing, missing)] @ gt[missing]).real)
    underfit = any(np.count_nonzero(lt == d) > np.count_nonzero(np.asarray(fit_delays) == d)
                   for d in set(lt.tolist()) & set(np.asarray(fit_delays, int).tolist()))
    return lost / total, bool(underfit)
