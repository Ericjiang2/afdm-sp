#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l09, stage 1 (2026-11-21, runner l): zero receiver, perfect channel knowledge.
Time-domain channel built explicitly from the paths; bases AFDM / single carrier / OFDM; P1 frames and a 4-ray same-delay cluster variant.
Imports l2_batch3 setup only.   python l2_l09_cluster.py out9/l09_cluster.json"""
import json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED  # noqa: E402
H1, H2, H3 = 0.3073, 0.8935, 1.1064
J = lambda s: (1 - 2 ** (-H1 * np.asarray(s, float) ** (2 * H2))) ** H3
SNRS = np.arange(0.0, 9.01, 0.25); VS = (1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.05, 0.0); FRAMES = (41000, 41060); RAYS, NU_MAX = 4, 2.0
VARIANT = sys.argv[2] if len(sys.argv) > 2 else 'base'
CHANNELS = ('tap1x8', 'tap2x8') if VARIANT == 'extreme' else ('p1', 'cluster')


def h_time(n, c1, l, nu, g):
    H = np.zeros((n, n), complex); idx = np.arange(n)
    for li, ni, gi in zip(l, nu, g):
        cp = np.where(idx < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (idx - li))), 1.0)
        H[idx, (idx - li) % n] += gi * cp * np.exp(2j * np.pi * idx * ni / n)
    return H


def tables(Ht, A, F):
    lam, V = np.linalg.eigh(Ht.conj().T @ Ht); lam = np.clip(lam, 0, None)
    W = dict(afdm=np.abs(A @ V) ** 2, sc=np.abs(V) ** 2, ofdm=np.abs(F @ V) ** 2); out = {}
    for name, w in W.items():
        tab = np.zeros((len(SNRS), len(VS)))
        for i, snr in enumerate(SNRS):
            s2 = 10 ** (-snr / 10)
            for j, v in enumerate(VS):
                s = w @ (lam / (s2 + v * lam)); gam = s / np.maximum(1 - v * s, 1e-12)
                tab[i, j] = float(np.mean(J(2 * np.sqrt(gam))))
        out[name] = tab.tolist()
    out['diag_cv'] = {k: float(np.std(w @ lam) / np.mean(w @ lam)) for k, w in W.items()}      # flatness of diag(G) per basis
    return out


def job(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, 'U', 100), 100, 500)
    Hd = np.asarray(raw['H'], complex); n = Hd.shape[0]; idx = np.arange(n); c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    F = np.fft.fft(np.eye(n), axis=0) / np.sqrt(n)
    A = np.exp(2j * np.pi * c2 * idx ** 2)[:, None] * F * np.exp(2j * np.pi * c1 * idx ** 2)[None, :]
    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    Ht = h_time(n, c1, l, nu, g); g1 = float(np.linalg.norm(A @ Ht @ A.conj().T - Hd) / np.linalg.norm(Hd))
    rng = np.random.default_rng([SEED, frame, 91]); l2, nu2, g2 = [], [], []
    for li, gi in zip(l, g):
        ph = rng.uniform(0, 2 * np.pi, RAYS); th = rng.uniform(0, 2 * np.pi, RAYS)
        l2 += [li] * RAYS; nu2 += list(NU_MAX * np.cos(th)); g2 += list(abs(gi) / np.sqrt(RAYS) * np.exp(1j * ph))
    if VARIANT == 'extreme':                    # batch 12: tap1x8 and tap2x8 (see PREDICTIONS_batch12.md)
        rng = np.random.default_rng([SEED, frame, 92]); top = np.argsort(-np.abs(g))[:2]; out = dict(frame=frame, g1=g1)
        for name, taps in (('tap1x8', top[:1]), ('tap2x8', top)):
            pw = np.abs(g[taps]) ** 2; pw = pw / pw.sum(); le, ne, ge = [], [], []
            for li, pi in zip(l[taps], pw):
                ph = rng.uniform(0, 2 * np.pi, 8); th = rng.uniform(0, 2 * np.pi, 8)
                le += [li] * 8; ne += list(NU_MAX * np.cos(th)); ge += list(np.sqrt(pi / 8) * np.exp(1j * ph))
            out[name] = tables(h_time(n, c1, le, ne, ge), A, F)
        return out
    return dict(frame=frame, g1=g1, p1=tables(Ht, A, F), cluster=tables(h_time(n, c1, l2, nu2, g2), A, F))


def main():
    with get_context('spawn').Pool(8) as pool:
        rows = pool.map(job, list(range(*FRAMES)))
    res = dict(_argv=sys.argv, _config=dict(frames=FRAMES, scenario='U', snrs=SNRS.tolist(), vs=VS, rays=RAYS, nu_max=NU_MAX, seed=SEED),
               G1_max=max(r['g1'] for r in rows))
    res['_config']['variant'] = VARIANT; res['_config']['channels'] = CHANNELS
    for ch in CHANNELS:
        res[ch] = {b: np.mean([r[ch][b] for r in rows], axis=0).tolist() for b in ('afdm', 'sc', 'ofdm')}
        res[ch]['diag_cv'] = {b: float(np.mean([r[ch]['diag_cv'][b] for r in rows])) for b in ('afdm', 'sc', 'ofdm')}
    Path(sys.argv[1]).write_text(json.dumps(res)); print('G1_max', res['G1_max'], {ch: res[ch]['diag_cv'] for ch in CHANNELS})


if __name__ == '__main__':
    main()
