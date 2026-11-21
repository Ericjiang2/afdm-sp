"""Data-as-pilot test (RULES.md): can the lag-Doppler autocorrelation of the received time signal detect
decoding-relevant weak paths in the real P1 / AFDM / ZC setting? No receiver or decoder calls.

  python calc.py --out out/result.json            # frozen run
  python calc.py --smoke --out out/smoke.json     # code check only (strongest-pair peak location, y rebuild)
"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / 'experiments' / 'tcom_reference_frame_20261015'))
sys.path.insert(0, str(PROJECT / 'experiments' / 'sp_afdm_frozen_20260920' / 'src'))
import p1_driver  # noqa: E402
from physical import daft, regressors  # noqa: E402

RHOS = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50)
FRAMES = range(30000, 30400)
SNR = 5.0
PAD = 4                      # Doppler-difference grid of 1/PAD bin
FMAX = 6.0                   # |nu_i - nu_j| < 5 in P1
TAU = 0.2                    # relevant iff g >= TAU * sigma2_internal
BUDGET = 8                   # common false-candidate budget (distinct competitor peaks), both arms


def local_peaks(M):
    """Values of 2-D local maxima (3 x (2*PAD+1) neighbourhood, edges padded with -inf)."""
    a, b = 1, PAD
    P = np.pad(M, ((a, a), (b, b)), constant_values=-np.inf)
    nb = np.max([P[a + i:a + i + M.shape[0], b + j:b + j + M.shape[1]]
                 for i in range(-a, a + 1) for j in range(-b, b + 1) if (i, j) != (0, 0)], axis=0)
    return M >= nb


def captured(peak, competitor_peak_values):
    """Strict: above every competitor. Budget: fewer than BUDGET distinct competitor peaks above it."""
    above = int(np.sum(competitor_peak_values >= peak))
    return above == 0, above < BUDGET


def ac_arm(y, s, l, nu, strongest, weak, lmax):
    r = daft(y, s.c1, s.c2, inverse=True)
    n = len(r)
    q = np.stack([r * np.conj(np.roll(r, d)) for d in range(1, lmax + 1)])  # q_d[n] = r_n r*_{n-d}
    spec = np.fft.fft(q, n=PAD * n, axis=1)
    f = np.fft.fftfreq(PAD * n, d=1.0 / n)
    keep = np.abs(f) <= FMAX
    f, P = f[keep], np.abs(spec[:, keep]) ** 2

    def cell(i, j):  # folded (lag index, f) of pair l_i - l_j
        d = l[i] - l[j]
        return (d - 1, nu[i] - nu[j]) if d > 0 else (-d - 1, nu[j] - nu[i])

    anchor = np.zeros_like(P, dtype=bool)   # cells read as candidates relative to the anchor
    every_pair = np.zeros_like(P, dtype=bool)
    for i in range(len(l)):
        for j in range(len(l)):
            if i == j or l[i] == l[j]:
                continue
            k, ff = cell(i, j)
            every_pair[k, np.abs(f - ff) <= 1.0] = True
            if strongest in (i, j):
                anchor[k, np.abs(f - ff) <= 1.0] = True
    peaks = local_peaks(P)
    comp_budget = P[peaks & ~anchor]          # non-anchor real pairs count as competitors
    strict_max = P[~every_pair].max()         # descriptive (toy rule): real pairs excused
    res, used = [], set()
    for w in weak:
        if l[w] == l[strongest]:
            res.append((False, False, False)); continue
        k, ff = cell(w, strongest)
        sel = np.where(np.abs(f - ff) <= 0.5)[0]
        pk = float(P[k, sel].max()); key = (k, int(sel[np.argmax(P[k, sel])]) // (2 * PAD))
        _, bud = captured(pk, comp_budget)
        if key in used:                       # one resolved peak credits at most one path
            bud = False
        used.add(key)
        res.append((bool(pk > strict_max), bool(bud), bool(captured(pk, comp_budget)[0])))
    return res


def mf_arm(y, U, dl, l, nu, weak, lmax):
    z = np.abs(U.conj().T @ y) ** 2
    Z = z.reshape(lmax + 1, 5)
    on = np.isin(np.arange(lmax + 1), l)[:, None].repeat(5, 1)
    a, b = 1, 1
    P = np.pad(Z, ((a, a), (b, b)), constant_values=-np.inf)
    nb = np.max([P[a + i:a + i + Z.shape[0], b + j:b + j + Z.shape[1]]
                 for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)], axis=0)
    comp = Z[(Z >= nb) & ~on]
    strict_max = Z[~on].max()
    kk = np.clip(np.rint(nu), -2, 2).astype(int)
    res = []
    for w in weak:
        v = Z[l[w], kk[w] + 2]
        res.append((bool(v > strict_max), bool(captured(v, comp)[1])))
    return res


def build(raw, s, p, rng=None):
    """Rebuild y = H(pilot + data) + noise; with rng, give each path its own independent data waveform."""
    l = np.asarray(p['l_i'], int); nu = np.asarray(p['k_real'], float); h = np.asarray(p['g_i'])
    noise = np.sqrt(raw['sigma2']) * raw['noise']
    if rng is None:
        return regressors(raw['pilot'] + raw['data'], l, nu, s.c1, s.c2) @ h + noise
    amp = np.abs(raw['data'])
    y = regressors(raw['pilot'], l, nu, s.c1, s.c2) @ h + noise
    for i in range(len(l)):
        d = amp * (rng.choice([-1, 1], len(amp)) + 1j * rng.choice([-1, 1], len(amp))) / np.sqrt(2)
        y = y + h[i] * regressors(d, l[i:i + 1], nu[i:i + 1], s.c1, s.c2)[:, 0]
    return y


def frame_eval(ctx, sf, scen, rho, frame, U, dl, lmax, control=False):
    raw, _ = p1_driver.generate(ctx, scen, rho, SNR, frame, sf)
    s = ctx.system; p = raw['params']
    l = np.asarray(p['l_i'], int); nu = np.asarray(p['k_real'], float); g = np.abs(np.asarray(p['g_i'])) ** 2
    y = build(raw, s, p)
    if not np.allclose(y, raw['y'], atol=1e-9):
        raise AssertionError('y rebuild differs from the generator')
    strongest = int(np.argmax(g))
    weak = [w for w in range(len(l)) if w != strongest and g[w] >= TAU * float(raw['sigma2'])]
    out = dict(ac=ac_arm(y, s, l, nu, strongest, weak, lmax), mf=mf_arm(y, U, dl, l, nu, weak, lmax),
               codelay=[bool(l[w] == l[strongest]) for w in weak])
    if control:
        yc = build(raw, s, p, rng=np.random.default_rng([frame, 20261121]))
        out['ac_ctrl'] = ac_arm(yc, s, l, nu, strongest, weak, lmax)
    return out, (l, nu, g)

_CTX = None


def cell_rows(cell):
    """One (scenario, rho) cell in its own process; the frozen context is built once per process."""
    global _CTX
    if _CTX is None:
        ctx = p1_driver.load_context(); s = ctx.system; lmax = int(s.l_max_cap)
        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
        _CTX = (ctx, p1_driver.make_seed_fn(), U / np.linalg.norm(U, axis=0, keepdims=True), dl, lmax)
    ctx, sf, U, dl, lmax = _CTX
    scen, rho = cell
    rows = []
    for frame in FRAMES:
        o, _ = frame_eval(ctx, sf, scen, rho, frame, U, dl, lmax, control=(rho == 0.15))
        for k in range(len(o['mf'])):
            rows.append(dict(frame=frame, ac_strict=o['ac'][k][0], ac=o['ac'][k][1], mf_strict=o['mf'][k][0],
                             mf=o['mf'][k][1], codelay=o['codelay'][k],
                             ac_ctrl=o['ac_ctrl'][k][1] if 'ac_ctrl' in o else None))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    ctx = p1_driver.load_context(); s = ctx.system; sf = p1_driver.make_seed_fn()
    lmax = int(s.l_max_cap)
    dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
    U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
    U = U / np.linalg.norm(U, axis=0, keepdims=True)
    if a.smoke:
        ok = []
        for frame in (29990, 29991, 29992, 29993):
            o, _ = frame_eval(ctx, sf, 'U', 0.15, frame, U, dl, lmax, control=True)
            ok.append(len(o['ac']) == len(o['mf']) == len(o['ac_ctrl']))
        Path(a.out).write_text(json.dumps(dict(shapes_ok=ok)))
        print('SMOKE', ok)
        return
    cells = [(scen, rho) for scen in ('U', 'G') for rho in RHOS]
    with get_context('spawn').Pool(len(cells)) as pool:
        res = dict(zip([f'{c[0]}/{c[1]}' for c in cells], pool.map(cell_rows, cells)))

    def mean(rows, key, cond=lambda x: True):
        v = [x[key] for x in rows if cond(x)]
        return (float(np.mean(v)) if v else None), len(v)

    def frame_ci(rows, key, cond=lambda x: True, B=2000):
        fr = sorted({x['frame'] for x in rows}); by = {f: [x for x in rows if x['frame'] == f and cond(x)] for f in fr}
        rng = np.random.default_rng(20261121); est = []
        for _ in range(B):
            pick = [x for f in rng.choice(fr, len(fr)) for x in by[f]]
            if pick:
                est.append(np.mean([x[key] for x in pick]))
        return [float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))]

    summary = {}
    for rho in RHOS:
        rows = res[f'U/{rho}'] + res[f'G/{rho}']
        ent = dict(n_weak=len(rows))
        for key in ('ac', 'mf', 'ac_strict', 'mf_strict'):
            ent[key] = mean(rows, key)[0]
        ent['either'] = float(np.mean([x['ac'] or x['mf'] for x in rows]))
        ent['ac_given_mf_miss'], ent['n_mf_miss'] = mean(rows, 'ac', lambda x: not x['mf'])
        ent['codelay_share'] = mean(rows, 'codelay')[0]
        if rho == 0.15:
            ent['ac_ci'] = frame_ci(rows, 'ac')
            ent['ac_given_mf_miss_ci'] = frame_ci(rows, 'ac', lambda x: not x['mf'])
            ent['ac_ctrl'] = mean(rows, 'ac_ctrl')[0]
            ent['ac_minus_ctrl'] = ent['ac'] - ent['ac_ctrl']
        summary[str(rho)] = ent
    s15 = summary['0.15']
    r1 = 'PASS' if s15['ac'] >= .70 else 'FAIL' if s15['ac'] < .50 else 'INCONCLUSIVE'
    c = s15['ac_given_mf_miss']
    r2 = None if c is None else ('COMPLEMENT' if c >= .50 else 'NO' if c < .25 else 'INCONCLUSIVE')
    r3 = 'ATTRIBUTED' if (s15['ac_minus_ctrl'] >= .30 and s15['ac_ctrl'] < .30) else (
        'NOT_ATTRIBUTED' if s15['ac_minus_ctrl'] < .10 else 'INCONCLUSIVE')
    out = dict(_argv=sys.argv, rules='RULES.md', frames=[FRAMES.start, FRAMES.stop - 1], snr=SNR, pad=PAD, tau=TAU,
               budget=BUDGET, summary=summary, R1=r1, R2=r2 if r1 != 'FAIL' else f'{r2} (descriptive; R1 FAIL stops)',
               R3=r3)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(R1=out['R1'], R2=out['R2'], R3=r3, s15=s15), indent=1))


if __name__ == '__main__':
    main()
