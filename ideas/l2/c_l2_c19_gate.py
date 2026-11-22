"""L2 runner c, card I-20261122-c19: a three-weight log-linear gate picks the per-frame noise factor from two blind features of the
plain first pass: ks = 1/(syndrome LLR scale) and r = residual power / sigma2.   k = snap(exp(w0 + w1*log ks + w2*log r)) on GRID.
train: every row gets the outcome for every k in GRID (both rho given by C19_RHOS).  fit: lattice search of (w0,w1,w2) minimising
pooled training FER.  test: unseen frames, one gate for all rho.  F0 only; A1 untouched; no truth at run time."""
import argparse, itertools, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m
import c_l2_c13_blind as b13
import c_l2_c16_resid as b16
WORKERS, SCEN = 5, ('U', 'G'); GRID = (1., 1.5, 2., 2.5, 3.2, 4.)
CASES = ((100, (550, 650)), (250, (450, 500)))
TRAIN = range(41460, 41560); TEST = range(*(int(x) for x in os.environ.get('C19_TEST', '43960,44160').split(',')))
snap = lambda k: GRID[int(np.argmin([abs(np.log(k / g)) for g in GRID]))]
gate = lambda w, ks, r: snap(float(np.exp(w[0] + w[1] * np.log(ks) + w[2] * np.log(max(r, 1e-3)))))

def feats(C, obs, truth):
    d, arr, syn, s = b13.f0(C, obs, 'none'); e1 = b13.finish(C, obs, truth, d, arr, syn)
    return e1, float(np.clip(1 / s[0], 1., 10.)), float(b16.resid_factor(C['ctx'], obs, arr)[1])

def job(args):
    frame, s_, rho, snrs, w = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, rho); rows = []
    for snr in snrs:
        raw, obs, truth = st.observed(ctx, base, rho, snr); e1, ks, r = feats(C, obs, truth); run = lambda k: e1 if k == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k)[:3])
        if w is None: err = {f'{k:g}': run(k) for k in GRID}
        else:
            kg = gate(w, ks, r); err = dict(base=e1, gate=run(kg), synd=run(ks), sig250=run(2.5))
        rows.append(dict(frame=frame, scenario=s_, rho=rho, snr=snr, err=err, ks=ks, r=r, **({} if w is None else dict(kg=kg))))
    return rows

def fit(rows):
    best = None
    for w in itertools.product(np.arange(-.4, 1.01, .2), np.arange(0, 2.01, .25), np.arange(0, 3.01, .5)):
        f = [np.mean([r['err'][f'{gate(w, r["ks"], r["r"]):g}'] > 0 for r in rows if r['rho'] == rho]) for rho, _ in CASES]
        sc = (round(float(np.mean(f)), 6), abs(w[0]) + abs(w[1]) + abs(w[2]))
        if best is None or sc < best[0]: best = (sc, [float(x) for x in w], [float(x) for x in f])
    return best

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--out', default='out_c19'); a = ap.parse_args(); out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    if a.cmd == 'smoke':
        print(job((41000, 'U', 100, (550,), None))); print(job((41000, 'U', 100, (550,), (0., 1., 0.)))); sys.exit()
    w = None if a.cmd == 'train' else json.load(open(out / 'train_summary.json'))['w']; fr = TRAIN if a.cmd == 'train' else TEST
    with get_context('spawn').Pool(WORKERS) as p, open(out / f'rows_{a.cmd}.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s, rho, snrs, w) for rho, snrs in CASES for f in fr for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / f'rows_{a.cmd}.jsonl')]
    if a.cmd == 'train':
        sc, w, f = fit(rows)
        res = dict(n=len(rows), w=w, gate_fer_by_rho=f, fixed_k_fer={str(rho): {f'{k:g}': float(np.mean([r['err'][f'{k:g}'] > 0 for r in rows if r['rho'] == rho])) for k in GRID} for rho, _ in CASES},
                   genie_any_k={str(rho): float(np.mean([min(r['err'].values()) > 0 for r in rows if r['rho'] == rho])) for rho, _ in CASES})
    else:
        res = dict(w=w)
        for rho, _ in CASES:
            R = [r for r in rows if r['rho'] == rho]; n = len(R); F = {nm: np.array([r['err'][nm] > 0 for r in R], float) for nm in R[0]['err']}
            rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
            res[str(rho)] = dict(n=n, fer={k: float(v.mean()) for k, v in F.items()}, gate_minus_sig250=ci(F['gate'] - F['sig250']), gate_minus_base=ci(F['gate'] - F['base']),
                                 gate_minus_synd=ci(F['gate'] - F['synd']), kg_hist={f'{g:g}': int(sum(r['kg'] == g for r in R)) for g in GRID})
    json.dump(res, open(out / f'{a.cmd}_summary.json', 'w'), indent=1); print(json.dumps(res))
