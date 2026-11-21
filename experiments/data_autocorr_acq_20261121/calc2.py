"""Step 2 of the data-as-pilot test (RULES2.md): replace the true anchor by the pilot-estimated one and resolve the
before/after mirror with the pilot. Reuses calc.py (build, local_peaks, BUDGET, FRAMES, SNR, TAU, PAD, FMAX).
No receiver or decoder calls.
  python calc2.py --out out/result2.json     |     python calc2.py --smoke --out out/smoke2.json
"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np

import calc
from calc import BUDGET, FMAX, FRAMES, PAD, SNR, TAU, build, local_peaks, p1_driver, regressors, daft

RHOS = (0.05, 0.10, 0.15, 0.20, 0.30)


def column(z5, l, nu):
    """Pilot-MF value at (delay l, nearest integer Doppler in [-2, 2]); -inf outside the delay range."""
    if not 0 <= l < z5.shape[0]:
        return -np.inf
    return z5[l, int(np.clip(np.rint(nu), -2, 2)) + 2]


def frame_eval(ctx, sf, scen, rho, frame, U, lmax):
    raw, _ = p1_driver.generate(ctx, scen, rho, SNR, frame, sf)
    s = ctx.system; p = raw['params']
    l = np.asarray(p['l_i'], int); nu = np.asarray(p['k_real'], float); g = np.abs(np.asarray(p['g_i'])) ** 2
    y = build(raw, s, p)
    if not np.allclose(y, raw['y'], atol=1e-9):
        raise AssertionError('y rebuild differs from the generator')
    strongest = int(np.argmax(g))
    weak = [w for w in range(len(l)) if w != strongest and g[w] >= TAU * float(raw['sigma2'])]
    # Pilot MF over the F0 integer dictionary; anchor = its largest column.
    z5 = (np.abs(U.conj().T @ y) ** 2).reshape(lmax + 1, 5)
    c = int(np.argmax(z5)); la, ka = c // 5, c % 5 - 2
    hit = np.where(l == la)[0]
    a = int(hit[0]) if len(hit) else None
    # Pilot-MF budget capture (same rule as calc.mf_arm) for the "missed by pilot" population.
    mf = [m[1] for m in calc.mf_arm(y, U, None, l, nu, weak, lmax)]
    rows = []
    if a is None:
        for k, w in enumerate(weak):
            rows.append(dict(frame=frame, anchor_ok=False, rec=False, cap=False, mirror=None, mf=mf[k]))
        return rows
    # Autocorrelation map (same statistic as calc.ac_arm).
    r = daft(y, s.c1, s.c2, inverse=True); n = len(r)
    q = np.stack([r * np.conj(np.roll(r, d)) for d in range(1, lmax + 1)])
    spec = np.fft.fft(q, n=PAD * n, axis=1); f = np.fft.fftfreq(PAD * n, d=1.0 / n)
    keep = np.abs(f) <= FMAX; f, P = f[keep], np.abs(spec[:, keep]) ** 2

    def cell(i, j):
        d = l[i] - l[j]
        return (d - 1, nu[i] - nu[j]) if d > 0 else (-d - 1, nu[j] - nu[i])

    anchor_cells = np.zeros_like(P, dtype=bool)
    for j in range(len(l)):
        if j != a and l[j] != l[a]:
            k, ff = cell(j, a)
            anchor_cells[k, np.abs(f - ff) <= 1.0] = True
    comp = P[local_peaks(P) & ~anchor_cells]
    used = set()
    for k_w, w in enumerate(weak):
        if w == a or l[w] == l[a]:
            rows.append(dict(frame=frame, anchor_ok=True, rec=w == a, cap=w == a, mirror=None, mf=mf[k_w])); continue
        kk, ff = cell(w, a)
        sel = np.where(np.abs(f - ff) <= 0.5)[0]
        j = int(sel[np.argmax(P[kk, sel])]); pk = float(P[kk, j]); key = (kk, j // (2 * PAD))
        cap = int(np.sum(comp >= pk)) < BUDGET and key not in used
        used.add(key)
        d, fo = kk + 1, float(f[j])          # observed folded lag and frequency of the peak
        after = column(z5, la + d, ka + fo)  # candidate: w after the anchor
        before = column(z5, la - d, ka - fo)  # mirror: w before the anchor
        chosen = la + d if after >= before else la - d
        mirror = bool(chosen == l[w])
        rows.append(dict(frame=frame, anchor_ok=True, cap=bool(cap), mirror=mirror, rec=bool(cap and mirror), mf=mf[k_w]))
    return rows


_CTX = None


def cell_rows(cell_key):
    global _CTX
    if _CTX is None:
        ctx = p1_driver.load_context(); s = ctx.system; lmax = int(s.l_max_cap)
        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
        _CTX = (ctx, p1_driver.make_seed_fn(), U / np.linalg.norm(U, axis=0, keepdims=True), lmax)
    ctx, sf, U, lmax = _CTX
    scen, rho = cell_key
    out = []
    for frame in FRAMES:
        out += frame_eval(ctx, sf, scen, rho, frame, U, lmax)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    if a.smoke:
        global FRAMES
        calc.FRAMES = FRAMES = range(29990, 29994)
        rows = cell_rows(('U', 0.15))
        Path(a.out).write_text(json.dumps(dict(n=len(rows), keys=sorted(rows[0]) if rows else None)))
        print('SMOKE', len(rows), sorted(rows[0]) if rows else None)
        return
    cells = [(s_, r_) for s_ in ('U', 'G') for r_ in RHOS]
    with get_context('spawn').Pool(len(cells)) as pool:
        res = dict(zip([f'{c[0]}/{c[1]}' for c in cells], pool.map(cell_rows, cells)))
    summary = {}
    for rho in RHOS:
        rows = res[f'U/{rho}'] + res[f'G/{rho}']
        frames = {}
        for x in rows:
            frames.setdefault(x['frame'], []).append(x)
        miss = [x for x in rows if not x['mf']]
        capd = [x for x in rows if x['cap'] and x['mirror'] is not None]
        summary[str(rho)] = dict(
            n_weak=len(rows), anchor_ok_frames=float(np.mean([v[0]['anchor_ok'] for v in frames.values()])),
            cap=float(np.mean([x['cap'] for x in rows])), rec=float(np.mean([x['rec'] for x in rows])),
            mirror_given_cap=float(np.mean([x['mirror'] for x in capd])) if capd else None,
            mf=float(np.mean([x['mf'] for x in rows])), n_mf_miss=len(miss),
            rec_given_mf_miss=float(np.mean([x['rec'] for x in miss])) if miss else None,
            union=float(np.mean([x['rec'] or x['mf'] for x in rows])))
    s15 = summary['0.15']
    r4 = 'PASS' if s15['anchor_ok_frames'] >= .95 else 'FAIL' if s15['anchor_ok_frames'] < .85 else 'INCONCLUSIVE'
    c = s15['rec_given_mf_miss']
    r5 = 'PASS' if c >= .50 else 'FAIL' if c < .25 else 'INCONCLUSIVE'
    out = dict(_argv=sys.argv, rules='RULES2.md', summary=summary, R4=r4, R5=r5)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
