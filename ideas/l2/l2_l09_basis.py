#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l09, stage 1 on P1 (2026-11-21, runner l): zero receiver, perfect channel knowledge.
Per-symbol soft-cancellation LMMSE SINR under three unitary symbol bases on the project's true channels.  Imports l2_batch3 setup only.
  python l2_l09_basis.py out9/l09_basis.json"""
import json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup  # noqa: E402
H1, H2, H3 = 0.3073, 0.8935, 1.1064
J = lambda s: (1 - 2 ** (-H1 * np.asarray(s, float) ** (2 * H2))) ** H3
SNRS = np.arange(0.0, 8.01, 0.25); VS = (1.0, 0.5, 0.2, 0.05, 0.0)
TRAPZ = getattr(np, 'trapezoid', None) or np.trapz      # deinlab's numpy predates np.trapezoid


def job(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    from physical import daft
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, 'U', 100), 100, 500)
    H = np.asarray(raw['H'], complex); n = H.shape[0]
    A = np.stack([daft(e, ctx.system.c1, ctx.system.c2) for e in np.eye(n, dtype=complex)], axis=1)      # DAFT matrix, x_daft = A x_time
    assert np.allclose(A.conj().T @ A, np.eye(n), atol=1e-9)
    lam, V = np.linalg.eigh(H.conj().T @ H); lam = np.clip(lam, 0, None)                                   # Gram in the DAFT basis
    Vt = A.conj().T @ V                                                                                     # eigenvectors in the time basis
    W = dict(afdm=np.abs(V) ** 2, sc=np.abs(Vt) ** 2, ofdm=np.abs(np.fft.fft(Vt, axis=0) / np.sqrt(n)) ** 2)
    out = {}
    for name, w in W.items():
        tab = np.zeros((len(SNRS), len(VS)))
        for i, snr in enumerate(SNRS):
            s2 = 10 ** (-snr / 10)
            for j, v in enumerate(VS):
                s = w @ (lam / (s2 + v * lam)); g = s / np.maximum(1 - v * s, 1e-12)
                tab[i, j] = float(np.mean(J(2 * np.sqrt(g))))
        out[name] = tab.tolist()
    return out


def main():
    with get_context('spawn').Pool(8) as pool:
        rows = pool.map(job, list(range(41000, 41060)))
    res = dict(_argv=sys.argv, _config=dict(frames=[41000, 41060], scenario='U', snrs=SNRS.tolist(), vs=VS))
    for name in ('afdm', 'sc', 'ofdm'):
        T = np.mean([r[name] for r in rows], axis=0); i4 = int(np.argmin(np.abs(SNRS - 4.0)))
        thr = float(np.interp(0.57, T[:, 0], SNRS))
        order = np.argsort(VS); area = float(TRAPZ(T[i4][order], np.array(VS)[order]))
        res[name] = dict(threshold_db_v1=thr, I_at_4dB={str(v): float(T[i4, j]) for j, v in enumerate(VS)}, area_at_4dB=area)
    res['afdm_minus_sc_db'] = res['afdm']['threshold_db_v1'] - res['sc']['threshold_db_v1']
    res['ofdm_minus_afdm_db'] = res['ofdm']['threshold_db_v1'] - res['afdm']['threshold_db_v1']
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True); Path(sys.argv[1]).write_text(json.dumps(res, indent=1)); print(json.dumps(res))


if __name__ == '__main__':
    main()
