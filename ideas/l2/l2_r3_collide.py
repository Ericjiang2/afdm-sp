#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 step 1 for card I-20261122-l09 (2026-11-22, runner l, claude-fable-5.2).
Two users collide on the same preamble; the receiver knows the 16 path positions and a noisy sum gain per path, and must
decide which path belongs to which user from the data segment alone.  Partition stage only (no decoder).  New numpy code.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch8.md.
  python l2_r3_collide.py run|read --out out_r3b8
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SEED, N, P, LMAXD, NUMAX = 20261122, 1024, 8, 102, 1.62
CFG = dict(trials=400, snrs_db=[6.0, 8.0, 10.0], dps_db=[0.0, 3.0, 6.0], etas=[0.0, 1.0, 2.5], preamble_len=256)
T = np.arange(N)


def apply(x, l, nu):                       # delay l (cyclic), Doppler nu bins
    return np.roll(x, l) * np.exp(2j * np.pi * nu * T / N)


def unapply(y, l, nu):
    return np.roll(y * np.exp(-2j * np.pi * nu * T / N), -l)


def draw(rng, eta, dp_db):
    """Positions: user A delays uniform in [0, 102], Dopplers uniform in +-1.62; user B the same cloud shifted by
    eta/sqrt(2) cloud standard deviations in each of delay and Doppler (clipped), so eta is the centre separation in
    standardised units.  Distinct delays across the 16 paths."""
    sl, sn = LMAXD / np.sqrt(12), 2 * NUMAX / np.sqrt(12)
    while True:
        la = rng.integers(0, LMAXD + 1, P); lb = rng.integers(0, LMAXD + 1, P) + int(round(eta / np.sqrt(2) * sl))
        if len(set(la) | set(lb)) == 2 * P:
            break
    na = rng.uniform(-NUMAX, NUMAX, P); nb = rng.uniform(-NUMAX, NUMAX, P) + eta / np.sqrt(2) * sn
    ga = (rng.standard_normal(P) + 1j * rng.standard_normal(P)); ga /= np.linalg.norm(ga)
    gb = (rng.standard_normal(P) + 1j * rng.standard_normal(P)); gb *= 10 ** (-dp_db / 20) / np.linalg.norm(gb)
    return np.r_[la, lb], np.r_[na, nb], np.r_[ga, gb], np.r_[np.zeros(P, int), np.ones(P, int)]


def mismatch(lab, truth, g):
    p = np.abs(g) ** 2; a = np.sum(p[lab != truth]) / p.sum()
    return float(min(a, 1 - a))


def spectral(W):
    w, v = np.linalg.eigh((W + W.T) / 2); return (v[:, -1] > 0).astype(int)


def trial(rng, snr_db, dp_db, eta):
    l, nu, g, truth = draw(rng, eta, dp_db); K = len(l); s2 = 10 ** (-snr_db / 10)
    qpsk = lambda: (rng.choice([-1, 1], N) + 1j * rng.choice([-1, 1], N)) / np.sqrt(2)
    xa, xb = qpsk(), qpsk()
    rd = sum(g[r] * apply(xa if truth[r] == 0 else xb, l[r], nu[r]) for r in range(K))
    rd = rd + np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    shat = g + np.sqrt(s2 / CFG['preamble_len'] / 2) * (rng.standard_normal(K) + 1j * rng.standard_normal(K))
    Z = np.array([unapply(rd, l[r], nu[r]) for r in range(K)])
    M = (Z @ Z.conj().T) / N                                     # M[r, q] = sum_n z_r[n] conj(z_q[n]) = z_q^H z_r / N
    pw = float(np.vdot(rd, rd).real) / N
    for r in range(K):                                           # remove the white part: (|rd|^2/N) tr(T_q T_r^H)/N
        for q in range(K):
            if r != q and l[r] == l[q]:
                M[r, q] -= pw * np.mean(np.exp(2j * np.pi * (nu[q] - nu[r]) * T / N))
    np.fill_diagonal(M, 0)
    D = 2 * M - np.outer(shat, shat.conj()); np.fill_diagonal(D, 0)
    lab_par = spectral(np.real(D * np.outer(shat.conj(), shat)))                      # card's parallelogram matrix, sign pattern
    A = np.abs(M) / np.sqrt(np.outer(np.abs(shat), np.abs(shat)) + 1e-12)             # simplest use of the same data: |M| only
    lab_abs = spectral(A - np.mean(A[~np.eye(K, dtype=bool)]))
    X = np.c_[(l - l.mean()) / l.std(), (nu - nu.mean()) / nu.std()]                  # geometry baseline: 2-means, 8 restarts
    best = None
    for _ in range(8):
        c = X[rng.choice(K, 2, replace=False)]
        for _ in range(20):
            lab = np.argmin(((X[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
            if len(set(lab)) < 2:
                break
            c = np.array([X[lab == j].mean(0) for j in (0, 1)])
        cost = ((X - c[lab]) ** 2).sum()
        if best is None or cost < best[0]:
            best = (cost, lab)
    return dict(par=mismatch(lab_par, truth, g), absM=mismatch(lab_abs, truth, g), kmeans=mismatch(best[1], truth, g))


def gate(n=200):
    """Mean of Re(D[r,q] conj(s_r) s_q) / (|g_r|^2 |g_q|^2) over same-user and cross-user pairs: expected +1 and -1."""
    rng = np.random.default_rng([SEED, 99]); same, cross = [], []
    for _ in range(n):
        l, nu, g, truth = draw(rng, 0.0, 0.0); K = len(l)
        qpsk = lambda: (rng.choice([-1, 1], N) + 1j * rng.choice([-1, 1], N)) / np.sqrt(2)
        xa, xb = qpsk(), qpsk()
        rd = sum(g[r] * apply(xa if truth[r] == 0 else xb, l[r], nu[r]) for r in range(K))
        Z = np.array([unapply(rd, l[r], nu[r]) for r in range(K)]); M = (Z @ Z.conj().T) / N; np.fill_diagonal(M, 0)
        D = 2 * M - np.outer(g, g.conj()); W = np.real(D * np.outer(g.conj(), g)) / np.outer(np.abs(g) ** 2, np.abs(g) ** 2)
        for r in range(K):
            for q in range(r + 1, K):
                (same if truth[r] == truth[q] else cross).append(W[r, q] * np.abs(g[r]) ** 2 * np.abs(g[q]) ** 2)
    norm = np.mean([1.0])
    return dict(same_mean=float(np.mean(same)), cross_mean=float(np.mean(cross)))


def run(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time(); cells = {}
    for snr in CFG['snrs_db']:
        for dp in CFG['dps_db']:
            for eta in CFG['etas']:
                rng = np.random.default_rng([SEED, int(snr * 10), int(dp * 10), int(eta * 10)])
                rows = [trial(rng, snr, dp, eta) for _ in range(CFG['trials'])]
                cells[f'{snr}|{dp}|{eta}'] = {k: [r[k] for r in rows] for k in rows[0]}
    (out / 'collide_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=CFG, gate=gate(), cells=cells, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1), 's')


def read(out):
    R = json.loads((out / 'collide_rows.json').read_text()); res = dict(table={}, criterion={})
    for key, c in R['cells'].items():
        res['table'][key] = {k: dict(median=float(np.median(v)), mean=float(np.mean(v)), frac_below_5pct=float(np.mean(np.array(v) < 0.05))) for k, v in c.items()}
    ok = True
    for eta in (0.0, 1.0):
        for dp in (0.0, 3.0):
            t = res['table'][f'8.0|{dp}|{eta}']; passed = bool(t['par']['median'] <= 0.05 and t['par']['median'] <= t['kmeans']['median'] / 5)
            res['criterion'][f'8.0|{dp}|{eta}'] = dict(par_median=t['par']['median'], kmeans_median=t['kmeans']['median'], absM_median=t['absM']['median'], passed=passed); ok = ok and passed
    res['verdict_i'] = 'PASS' if ok else 'KILL'
    (out / 'collide_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('run', 'read')); ap.add_argument('--out', default='out_r3b8'); a = ap.parse_args()
    dict(run=run, read=read)[a.mode](HERE / a.out)
