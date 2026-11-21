"""Zero-cost toy (2026-11-20, Claude): does the chirp, not the co-delay rank, make one variance number enough?

Exploratory readout for the 16-QAM line design note. Not the frozen receiver: LMMSE per-symbol error variance
stands in for decoder reliability, the channel is a generic P-path draw on the frozen grid (N=1024, L=102,
nu in [-3,3]), and only the true support is scored. Question: with the same channel and the same v-generating
detector, how far is h^H Gamma_F h from the scalar u*||h||^2 as a1 = 2*N*c1 moves from OFDM (0) to AFDM (5, 7)?

h^H Gamma_F h = sum_n v_n ||g_n||^2, with g_n the n-th column of G = sum_i h_i U_i (Prop 1 definitions), so the
ratio R = that / (u ||h||^2) is 1 whenever the per-symbol channel energy ||g_n||^2 is flat in n.
"""

import json
import sys
from pathlib import Path

import numpy as np

N, L, NU, P = 1024, 102, 3.0, 8
A1S = (0, 1, 3, 5, 7)
SNRS_DB = (0, 6, 12)
DRAWS = 20
SEED = 20261120


def synthesis(a1):
    """A^H = Lambda_c1^* F^H with c2 = 0 (c2 cancels in every quantity below)."""
    t = np.arange(N)
    c1 = a1 / (2 * N)
    fh = np.exp(2j * np.pi * np.outer(t, t) / N) / np.sqrt(N)
    return np.exp(-2j * np.pi * c1 * t**2)[:, None] * fh


def channel(rng):
    delays = rng.choice(L + 1, size=P, replace=False)
    dopplers = rng.uniform(-NU, NU, size=P)
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P)
    return delays, dopplers, gains


def path_operator(ah, delay, doppler):
    """U_i = M_nu S_l A^H; plain cyclic shift is exact on the frozen grid (a1 N even)."""
    s = np.arange(N)
    return np.exp(2j * np.pi * doppler * s / N)[:, None] * np.roll(ah, delay, axis=0)


def readout(a1, rng_state):
    rng = np.random.default_rng(rng_state)
    ah = synthesis(a1)
    rows = []
    for draw in range(DRAWS):
        delays, dopplers, gains = channel(rng)
        ops = [path_operator(ah, l, nu) for l, nu in zip(delays, dopplers)]
        g = sum(h * op for h, op in zip(gains, ops))
        col_energy = np.sum(np.abs(g) ** 2, axis=0)
        gram = g.conj().T @ g
        h2 = float(np.sum(np.abs(gains) ** 2))
        # Column-wise overlaps (U_i^H U_j)_nn; Gamma_F entry is their v-weighted sum.
        overlaps = [np.sum(ops[i].conj() * ops[j], axis=0) for i in range(P) for j in range(i + 1, P)]
        for snr_db in SNRS_DB:
            sigma2 = h2 * 10 ** (-snr_db / 10)  # unit-energy symbols, SNR on received power
            v = np.real(np.diag(np.linalg.inv(gram / sigma2 + np.eye(N))))
            u = v.sum()
            cross = [abs(np.sum(v * w)) / u for w in overlaps]
            rows.append(dict(a1=a1, draw=draw, snr_db=snr_db,
                             gain_cv=float(col_energy.std() / col_energy.mean()),
                             v_cv=float(v.std() / v.mean()),
                             corr_gain_v=float(np.corrcoef(col_energy, v)[0, 1]),
                             R=float(np.sum(v * col_energy) / (u * h2)),
                             max_cross_over_u=float(max(cross))))
    return rows


def summarize(rows):
    out = {}
    for a1 in A1S:
        for snr_db in SNRS_DB:
            sel = [r for r in rows if r['a1'] == a1 and r['snr_db'] == snr_db]
            key = f'a1={a1},snr={snr_db}dB'
            out[key] = {k: [float(np.median([r[k] for r in sel])), float(np.min([r[k] for r in sel])),
                            float(np.max([r[k] for r in sel]))]
                        for k in ('gain_cv', 'v_cv', 'corr_gain_v', 'R', 'max_cross_over_u')}
    return out


def main():
    rows = []
    for a1 in A1S:
        rows += readout(a1, SEED)  # same channel draws for every a1
    summary = summarize(rows)
    result = dict(_argv=sys.argv, _config=dict(N=N, L=L, NU=NU, P=P, A1S=A1S, SNRS_DB=SNRS_DB, DRAWS=DRAWS,
                                               SEED=SEED, detector='LMMSE per-symbol MSE, unit-energy prior'),
                  summary_median_min_max=summary, rows=rows)
    path = Path(__file__).with_suffix('.json')
    path.write_text(json.dumps(result, indent=1))
    for key, stats in summary.items():
        print(key, {k: [round(x, 3) for x in s] for k, s in stats.items()})


if __name__ == '__main__':
    main()
