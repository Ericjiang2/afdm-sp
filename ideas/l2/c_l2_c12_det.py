"""L2 runner c, card I-20261122-c12 (PREDICTIONS_c20261122_c12.md): inner schedule of the bilinear scalar detector
(damping, iteration count, gain mode) inside F0, learned on training frames, tested on unseen frames.  A1 untouched.
  C12_RHO=250 C12_SNRS=450,500 python c_l2_c12_det.py train|test --out out_c12"""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
import c_l2_c08_iface as m
RHO = int(os.environ.get('C12_RHO', 250)); SNRS = tuple(int(x) for x in os.environ.get('C12_SNRS', '450,500').split(','))
SCEN, WORKERS = ('U', 'G'), 5
TRAIN = range(41460, 41560); TEST = range(*(int(x) for x in os.environ.get('C12_TEST', '42560,42760').split(',')))
BASE = dict(damping=.3, iterations=20, gain_mode='joint')
GRID = dict(damping=(.15, .5, .8), iterations=(8, 40), gain_mode=('point', 'fixed'))


def settings():
    out = {'base': dict(BASE)}
    for k, vs in GRID.items():
        for v in vs:
            out[f'{k}={v}'] = dict(BASE, **{k: v})
    return out


def arm(C, obs, truth, th):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; osj = nat.scalar_joint

    def sj(*a, **k):
        k.update(th); return osj(*a, **k)
    nat.scalar_joint = sj
    try:
        d, arrays, syndrome, _ = st.e1.f0_state(ctx, obs)
    finally:
        nat.scalar_joint = osj
    if syndrome:
        d = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth))


def job(args):
    frame, s_, S = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err={nm: arm(C, obs, truth, th) for nm, th in S.items()}))
    return rows


def run(out, tag, frames, S):
    with get_context('spawn').Pool(WORKERS) as p, open(out / f'rows_{tag}.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s, S) for f in frames for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    return [json.loads(x) for x in open(out / f'rows_{tag}.jsonl')]


def fer(rows, nm):
    return np.array([r['err'][nm] > 0 for r in rows], float)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--out', default='out_c12'); a = ap.parse_args()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    if a.cmd == 'train':
        S = settings(); rows = run(out, 'train', TRAIN, S); tab = {nm: float(fer(rows, nm).mean()) for nm in S}; th = dict(BASE)
        for k in GRID:
            best = min([f'{k}={v}' for v in GRID[k]], key=lambda nm: tab[nm])
            if tab[best] < tab['base']:
                th[k] = S[best][k]
        genie = float(np.min([fer(rows, nm) for nm in S], 0).mean())
        json.dump(dict(n=len(rows), rho=RHO, snrs=SNRS, table=tab, learned=th, genie_any_setting=genie), open(out / 'train_summary.json', 'w'), indent=1)
        print(json.dumps(dict(table=tab, learned=th, genie=genie)))
    else:
        th = json.load(open(out / 'train_summary.json'))['learned']; rows = run(out, 'test', TEST, dict(base=BASE, learned=th))
        A, B = fer(rows, 'base'), fer(rows, 'learned'); rng = np.random.default_rng(20261122); idx = rng.integers(0, len(rows), (2000, len(rows)))
        res = dict(n=len(rows), rho=RHO, snrs=SNRS, learned=th, fer_base=float(A.mean()), fer_learned=float(B.mean()), diff=float((A - B).mean()),
                   ci=np.percentile((A[idx] - B[idx]).mean(1), [2.5, 97.5]).tolist())
        json.dump(res, open(out / 'test_summary.json', 'w'), indent=1); print(json.dumps(res))
