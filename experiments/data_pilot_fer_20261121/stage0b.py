"""Stage 0b (STAGE0B_RULES.md): multi-anchor scoring of absolute-position hypotheses. A true weak path makes a peak
with every found strong path; score each (delay, Doppler) hypothesis by summing, over the F0 round-0 support paths,
the autocorrelation value at its pair cell. Same keys and scoring as stage 0. Reuses stage0.py.
  python stage0b.py --out out/stage0b.json   |   python stage0b.py --smoke --out out/stage0b_smoke.json
"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np

import stage0
from stage0 import K_NEW, RHOS, SNR, TAU, setup, summarize

NU_GRID = np.arange(-2.5, 2.5001, 0.25)


def autocorr(y, C):
    s, lmax, PAD = C['s'], C['lmax'], C['PAD']
    r = C['daft'](y, s.c1, s.c2, inverse=True); n = len(r)
    q = np.stack([r * np.conj(np.roll(r, d)) for d in range(1, lmax + 1)])
    spec = np.fft.fft(q, n=PAD * n, axis=1); f = np.fft.fftfreq(PAD * n, d=1.0 / n)
    keep = np.abs(f) <= C['FMAX']
    return f[keep], np.abs(spec[:, keep]) ** 2


def score_new(y, sup_l, sup_nu, C):
    """Score every (l, nu) not in the support by summed pair-cell values over the support paths; best nu per delay."""
    f, P = autocorr(y, C)
    lmax = C['lmax']
    scores = np.full(lmax + 1, -np.inf)
    for l in range(lmax + 1):
        if l in sup_l:
            continue
        best = -np.inf
        for nu in NU_GRID:
            tot = 0.0
            for lj, nj in zip(sup_l, sup_nu):
                d = l - lj
                if d == 0:
                    continue
                k, ff = (d - 1, nu - nj) if d > 0 else (-d - 1, nj - nu)
                sel = np.abs(f - ff) <= 0.5
                if sel.any():
                    tot += float(P[k, sel].max())
            best = max(best, tot)
        scores[l] = best
    order = [int(l) for l in np.argsort(-scores) if np.isfinite(scores[l])]
    return order[:K_NEW]


def cell_rows(cell):
    s_, rho = cell
    C = setup(); ctx = C['ctx']; stage3 = C['cstate'].stage3
    out = []
    for frame in stage0.FRAMES:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, SNR)
        _dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
        sup_l = [int(v) for v in arrays['r0_delays']]; sup_nu = [float(v) for v in arrays['r0_dopplers']]
        l = np.asarray(truth['l_i'], int); g = np.abs(np.asarray(truth['g_i'])) ** 2
        relevant = [int(l[i]) for i in range(len(l)) if g[i] >= TAU * float(obs['sigma2'])]
        new = score_new(obs['y'], sup_l, sup_nu, C)
        missed = [d for d in relevant if d not in sup_l]
        out.append(dict(frame=frame, scenario=s_, rho=rho, syndrome=int(syndrome), anchor_true=True,
                        missed=missed, recovered=[d for d in missed if d in new], new=new,
                        new_true=[c for c in new if c in set(l.tolist())],
                        new_top2_true=[c for c in new[:2] if c in set(l.tolist())]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    if a.smoke:
        stage0.FRAMES = range(7000, 7002)
        rows = cell_rows(('U', 100))
        print('SMOKE', len(rows), rows[0]['new'], rows[0]['missed'])
        return
    cells = [(s_, r) for s_ in ('U', 'G') for r in RHOS]
    with get_context('spawn').Pool(len(cells)) as pool:
        rows = [x for part in pool.map(cell_rows, cells) for x in part]
    by = {str(r): summarize([x for x in rows if x['rho'] == r]) for r in RHOS}
    pooled = summarize(rows)
    top2 = sum(len(x['new_top2_true']) for x in rows) / (2 * len(rows))
    ok = pooled['precision'] >= .50 and pooled['recall'] >= .60
    verdict = 'ADOPT' if ok else 'FALLBACK'
    out = dict(_argv=sys.argv, rules='STAGE0B_RULES.md', pooled=pooled, by_rho=by, top2_precision=top2, verdict=verdict)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
