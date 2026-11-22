"""L2 runner c, card I-20261122-c08 (PREDICTIONS_c20261122_c08.md): scalar interface/schedule parameters of the
project F0 turbo loop, learned on training frames and tested on unseen frames.  Patches module globals of ctx.native
during F0 only (A1 branch untouched); repository code is not modified.
  python c_l2_c08_iface.py train --out out_c08   ;   python c_l2_c08_iface.py test --out out_c08"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
EXP = Path(__file__).resolve().parents[2] / 'experiments/data_pilot_fer_20261121'; sys.path.insert(0, str(EXP))
import stageA
RHO, SNRS, SCEN, WORKERS = 100, (550, 650), ('U', 'G'), 5
TRAIN, TEST = range(41460, 41560), range(41560, 41760)
BASE = dict(a0=1., a1=1., b0=1., c0=1., m0=50)
GRID = dict(a0=(.6, .8, 1.25), a1=(.6, .8, 1.25), b0=(.6, .8, 1.25), c0=(.6, .8, 1.25), m0=(5, 10, 20))


def settings():
    out = {'base': dict(BASE)}
    for k, vs in GRID.items():
        for v in vs:
            out[f'{k}={v}'] = dict(BASE, **{k: v})
    return out


def arm(C, obs, truth, th):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; od, om = nat.decoder_messages, nat.moments; s = dict(r=0, m=0)

    def dec(code, llr, maxiter=50):
        r = s['r']; s['r'] += 1
        if r == 0:
            d = dict(od(code, np.clip(th['a0'] * llr, -20, 20), maxiter=int(th['m0'])))
            d['raw_check_extrinsic'] = th['c0'] * np.asarray(d['raw_check_extrinsic']); return d
        return od(code, np.clip(th['a1'] * llr, -20, 20) if r == 1 else llr, maxiter=maxiter)

    def mom(app, pd):
        m = s['m']; s['m'] += 1
        return om(th['b0'] * app if m == 0 else app, pd)
    nat.decoder_messages, nat.moments = dec, mom
    try:
        d, arrays, syndrome, _ = st.e1.f0_state(ctx, obs)
    finally:
        nat.decoder_messages, nat.moments = od, om
    f0 = int(st.e1.gd.score(ctx, d['decoded'], truth))
    if syndrome:
        br = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1'); return f0, int(st.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    return f0, f0


def job(args):
    frame, s_, names = args; C = stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO)
    S = settings(); S.update(EXTRA); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); rec = dict(frame=frame, scenario=s_, snr=snr, f0={}, err={})
        for nm in names:
            rec['f0'][nm], rec['err'][nm] = arm(C, obs, truth, S[nm])
        rows.append(rec)
    return rows


EXTRA = {}


def run(out, tag, frames, names):
    with get_context('spawn').Pool(WORKERS, initializer=_init, initargs=(EXTRA,)) as p, open(out / f'rows_{tag}.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s, names) for f in frames for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)


def _init(extra):
    EXTRA.update(extra)


def fer(rows, nm, key='err'):
    return np.array([r[key][nm] > 0 for r in rows], float)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--out', default='out_c08'); a = ap.parse_args()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    if a.cmd == 'train':
        names = list(settings()); run(out, 'train', TRAIN, names)
        rows = [json.loads(x) for x in open(out / 'rows_train.jsonl')]
        tab = {nm: dict(fer=fer(rows, nm).mean(), f0=fer(rows, nm, 'f0').mean()) for nm in names}
        th = dict(BASE)
        for k in GRID:                                  # per coordinate: best value if it beats base on training FER
            best = min([f'{k}={v}' for v in GRID[k]], key=lambda nm: (tab[nm]['fer'], tab[nm]['f0']))
            if tab[best]['fer'] < tab['base']['fer']:
                th[k] = float(best.split('=')[1])
        genie = np.min([fer(rows, nm) for nm in names], 0).mean()
        json.dump(dict(n=len(rows), table=tab, learned=th, genie_any_setting=float(genie)), open(out / 'train_summary.json', 'w'), indent=1)
        print(json.dumps(dict(learned=th, base=tab['base'], genie=float(genie))))
    else:
        th = json.load(open(out / 'train_summary.json'))['learned']; EXTRA['learned'] = th
        run(out, 'test', TEST, ['base', 'learned'])
        rows = [json.loads(x) for x in open(out / 'rows_test.jsonl')]; A, B = fer(rows, 'base'), fer(rows, 'learned')
        rng = np.random.default_rng(20261122); idx = rng.integers(0, len(rows), (2000, len(rows)))
        res = dict(n=len(rows), learned=th, fer_base=A.mean(), fer_learned=B.mean(), diff=float((A - B).mean()),
                   ci=np.percentile((A[idx] - B[idx]).mean(1), [2.5, 97.5]).tolist(),
                   f0_base=fer(rows, 'base', 'f0').mean(), f0_learned=fer(rows, 'learned', 'f0').mean())
        json.dump(res, open(out / 'test_summary.json', 'w'), indent=1); print(json.dumps(res))
