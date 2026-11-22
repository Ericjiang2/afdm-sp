#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 step 2 for card I-20261122-l09 (2026-11-22, runner l, claude-fable-5.2), asked by the
gate: the 16 path positions are no longer given.  They are found from the collided preamble (both users send the same
256-sample preamble at the same time), then the data segment splits the found paths between the two users.
Source: l2_r3_collide.py (draw, spectral imported; its trial() gives the receiver the true positions and uses a cyclic
data block, so the packet model and the scoring are rewritten here) and l2_r3_marker.py (estimate imported).
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch14.md.
  python l2_r3_collide2.py smoke|run|read --out out_r3b14
"""
import argparse, json, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r3_collide as col  # noqa: E402
import l2_r3_marker as mk  # noqa: E402

SEED, WORKERS, N, NP, LW = 20261122, 8, 1024, 256, 160          # LW: delay search window and prefix length
CFG = dict(trials=400, kappa=12.0, max_paths=24,
           cells=[(8.0, 0.0, 0.0), (8.0, 3.0, 0.0), (8.0, 0.0, 1.0), (8.0, 3.0, 1.0), (8.0, 0.0, 2.5), (6.0, 0.0, 0.0), (10.0, 0.0, 0.0), (8.0, 6.0, 0.0)])


def synth(l, nu, g, truth, s2, rng):
    pre = np.exp(2j * np.pi * rng.uniform(size=NP))
    qpsk = lambda: (rng.choice([-1, 1], N) + 1j * rng.choice([-1, 1], N)) / np.sqrt(2)
    s = [np.r_[pre, np.r_[x[-LW:], x]] for x in (qpsk(), qpsk())]
    T = NP + LW + N + LW; t = np.arange(T); y = np.zeros(T, complex)
    for li, vi, gi, u in zip(l, nu, g, truth):
        out = np.zeros(T, complex); out[li:li + len(s[u])] = s[u]; y += gi * out * np.exp(2j * np.pi * vi * t / N)
    return y + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T)), pre, t


def metric(r, pre):
    return np.array([abs(np.vdot(pre, r[c:c + NP])) ** 2 for c in range(LW + 1)])


def acquire(y, pre, t, mode):
    """Delays from the preamble window.  'batch': every delay whose metric exceeds kappa x median, one pass.
    'clean': strongest delay, fit its Doppler and gain, subtract, repeat until the maximum drops below kappa x median.
    Then one joint Doppler / gain fit of all found paths on the preamble window."""
    tw = np.arange(0, NP + LW); yw = y[tw]
    def rep(c):
        u = np.zeros(len(tw), complex); u[c:c + NP] = pre; return u
    if mode == 'batch':
        m = metric(y, pre); ls = list(np.argsort(-m)[:CFG['max_paths']]); ls = [int(c) for c in ls if m[c] > CFG['kappa'] * np.median(m)]
    else:
        r = yw.copy(); ls = []
        while len(ls) < CFG['max_paths']:
            m = metric(np.r_[r, np.zeros(NP)], pre)
            if ls:
                m[np.array(ls)] = 0
            c = int(np.argmax(m))
            if m[c] < CFG['kappa'] * np.median(m[m > 0]):
                break
            U1 = rep(c)[None, :]; v1, g1 = mk.estimate(r, U1, tw, mk.CFG['grid'], 1)
            r = r - g1[0] * U1[0] * np.exp(2j * np.pi * v1[0] * tw / N); ls.append(c)
    if not ls:
        ls = [int(np.argmax(metric(y, pre)))]
    ls = np.array(sorted(ls), int); U = np.array([rep(c) for c in ls])
    nh, gh = mk.estimate(yw, U, tw, mk.CFG['grid'], 3)
    return ls, nh, gh


def split(y, t, ls, nh, sh, rng):
    t0 = NP + LW; n = np.arange(N); K = len(ls)
    if K < 2:
        return {k: np.zeros(K, int) for k in ('par', 'par_abs', 'absM', 'kmeans')}
    Z = np.array([y[t0 + c + n] * np.exp(-2j * np.pi * v * (t0 + c + n) / N) for c, v in zip(ls, nh)])
    M = (Z @ Z.conj().T) / N; np.fill_diagonal(M, 0)
    P2 = np.outer(np.abs(sh) ** 2, np.abs(sh) ** 2)
    W = 2 * np.real(M * np.outer(sh.conj(), sh)) - P2; np.fill_diagonal(W, 0)                 # card: Re((2M - s s^H) o conj(s) s^T)
    Wa = 2 * np.abs(M) * np.outer(np.abs(sh), np.abs(sh)) - P2; np.fill_diagonal(Wa, 0)       # same, phases of M and s dropped
    A = np.abs(M) / np.sqrt(np.outer(np.abs(sh), np.abs(sh)) + 1e-12)
    out = dict(par=col.spectral(W), par_abs=col.spectral(Wa), absM=col.spectral(A - np.mean(A[~np.eye(K, dtype=bool)])))
    X = np.c_[(ls - ls.mean()) / (ls.std() + 1e-9), (nh - nh.mean()) / (nh.std() + 1e-9)]; best = None
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
    out['kmeans'] = best[1]
    return out


def score(ls, lab, l, truth, g):
    p = np.abs(g) ** 2; pos = {int(c): i for i, c in enumerate(l)}
    idx = [pos.get(int(c), -1) for c in ls]; hit = [i for i in idx if i >= 0]
    missed = 1 - p[hit].sum() / p.sum() if hit else 1.0
    a = sum(p[i] for i, lb in zip(idx, lab) if i >= 0 and lb != truth[i]) / p.sum(); b = sum(p[i] for i, lb in zip(idx, lab) if i >= 0 and lb == truth[i]) / p.sum()
    return float(min(a, b)), float(missed)


def trial(rng, snr_db, dp_db, eta):
    l, nu, g, truth = col.draw(rng, eta, dp_db); s2 = 10 ** (-snr_db / 10); p = np.abs(g) ** 2
    y, pre, t = synth(l, nu, g, truth, s2, rng); res = {}
    for mode in ('clean', 'batch'):
        ls, nh, gh = acquire(y, pre, t, mode); labs = split(y, t, ls, nh, gh, rng)
        pos = {int(c): i for i, c in enumerate(l)}; hit = [(k, pos[int(c)]) for k, c in enumerate(ls) if int(c) in pos]
        nu_err = float(np.sum([p[i] * abs(nh[k] - nu[i]) for k, i in hit]) / max(np.sum([p[i] for _, i in hit]), 1e-12))
        res[mode] = dict(n=int(len(ls)), false=int(len(ls) - len(hit)), nu_mae_w=nu_err)
        for name, lab in labs.items():
            mis, missed = score(ls, lab, l, truth, g); res[mode][name] = mis; res[mode]['missed'] = missed
    # reference: true delays given, Doppler and gains still estimated from the preamble; and fully true positions + exact gains
    tw = np.arange(0, NP + LW); U = np.zeros((len(l), len(tw)), complex)
    for i, c in enumerate(l):
        U[i, c:c + NP] = pre
    nh, gh = mk.estimate(y[tw], U, tw, mk.CFG['grid'], 3); labs = split(y, t, np.asarray(l), nh, gh, rng)
    res['true_delays'] = {k: score(l, v, l, truth, g)[0] for k, v in labs.items()}
    labs = split(y, t, np.asarray(l), nu, g, rng); res['oracle'] = dict(par=score(l, labs['par'], l, truth, g)[0])
    return res


def cell(args):
    snr, dp, eta = args; rng = np.random.default_rng([SEED, 14, int(snr * 10), int(dp * 10), int(eta * 10)])
    return dict(cell=list(args), rows=[trial(rng, snr, dp, eta) for _ in range(CFG['trials'])])


def run(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        cells = pool.map(cell, [tuple(c) for c in CFG['cells']])
    (out / 'collide2_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, N=N, NP=NP, LW=LW, seed=SEED), cells=cells, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def read(out):
    R = json.loads((out / 'collide2_rows.json').read_text()); res = dict(table={}, criterion={})
    for c in R['cells']:
        key = '|'.join(str(x) for x in c['cell']); rows = c['rows']; tab = {}
        for mode in ('clean', 'batch'):
            tab[mode] = dict(n_mean=float(np.mean([r[mode]['n'] for r in rows])), false_mean=float(np.mean([r[mode]['false'] for r in rows])),
                             missed_median=float(np.median([r[mode]['missed'] for r in rows])), nu_mae_w=float(np.mean([r[mode]['nu_mae_w'] for r in rows])),
                             **{f'wrong_{k}_median': float(np.median([r[mode][k] + r[mode]['missed'] for r in rows])) for k in ('par', 'par_abs', 'absM', 'kmeans')},
                             **{f'mis_{k}_median': float(np.median([r[mode][k] for r in rows])) for k in ('par', 'par_abs', 'absM', 'kmeans')})
        tab['true_delays'] = {k: float(np.median([r['true_delays'][k] for r in rows])) for k in ('par', 'par_abs', 'absM', 'kmeans')}
        tab['oracle_par'] = float(np.median([r['oracle']['par'] for r in rows])); res['table'][key] = tab
    ok, dead = True, False
    for key in ('8.0|0.0|0.0', '8.0|3.0|0.0', '8.0|0.0|1.0', '8.0|3.0|1.0'):
        t = res['table'][key]; best = min((t[m][f'wrong_{k}_median'], m, k) for m in ('clean', 'batch') for k in ('par', 'par_abs'))
        km = t[best[1]]['mis_kmeans_median']; mine = t[best[1]][f'mis_{best[2]}_median']
        passed = bool(best[0] <= 0.10 and mine <= km / 3)
        res['criterion'][key] = dict(best_wrong=best[0], arm=f'{best[1]}/{best[2]}', mis=mine, mis_kmeans=km, passed=passed)
        ok = ok and passed; dead = dead or best[0] > 0.20
    res['verdict'] = 'PASS' if ok else 'KILL' if dead else 'UNDETERMINED'
    (out / 'collide2_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', default='out_r3b14'); a = ap.parse_args()
    if a.mode == 'smoke':
        rng = np.random.default_rng(3); t0 = time.process_time(); rows = [trial(rng, 8.0, 0.0, 0.0) for _ in range(12)]; print('cpu/trial', (time.process_time() - t0) / 12)
        for m in ('clean', 'batch'):
            print(m, {k: round(float(np.median([r[m][k] for r in rows])), 3) for k in ('n', 'false', 'missed', 'nu_mae_w', 'par', 'par_abs', 'absM', 'kmeans')})
        print('true_delays', {k: round(float(np.median([r['true_delays'][k] for r in rows])), 3) for k in ('par', 'par_abs', 'absM', 'kmeans')}, 'oracle', round(float(np.median([r['oracle']['par'] for r in rows])), 4))
    else:
        dict(run=run, read=read)[a.mode](HERE / a.out)
