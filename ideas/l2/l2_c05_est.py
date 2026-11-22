"""L2 runner c batch 3 (PREDICTIONS_c20261122_batch3.md): c05 (estimated delays) and c06 (drop paths whose pilot and
fused Doppler disagree), same receiver injection as l2_c02_fused.py.
  python l2_c05_est.py run --out out_c20261122b3 --snrs 350,400 --frames 41260,41460"""
import argparse, json
from multiprocessing import get_context
from pathlib import Path
import numpy as np
import l2_c02_fused as B
from l2_c02_fused import stageA, stageA2, daft, spec, estimates, RHO, SCEN, WORKERS

DROP = .5      # c06: |pilot - fused| > DROP bin -> path left out of round 0


def arm(C, obs, truth, l, nu):
    st, ctx = C['stage3'], C['ctx']
    pert = dict(truth, l_i=list(map(int, l)), k_real=list(map(float, nu)), g_i=[1.] * len(l))
    dec, arrays, syndrome, _ = stageA2.f0_true(C, obs, pert, 'ls')
    if syndrome:
        br = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1'); return int(st.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    return int(st.e1.gd.score(ctx, dec['decoded'], truth))


def job(args):
    frame, s_, snrs = args; C = stageA.setup(); st, ctx = C['stage3'], C['ctx']; c1, c2 = ctx.system.c1, ctx.system.c2
    base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in snrs:
        raw, obs, truth = st.observed(ctx, base, RHO, snr)
        y = np.asarray(raw['y']); n = len(y); l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float)
        r = daft(y, c1, c2, True); pt = daft(np.asarray(raw['pilot']), c1, c2, True); k = np.arange(n)
        cpp = lambda kk, ll: np.where(kk < ll, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (kk - ll))), 1.)
        pk = np.array([np.max(np.abs(spec(r * np.conj(cpp(k, d) * pt[(k - d) % n]), n)[1])) for d in range(C['lmax'] + 1)])
        lh = np.sort(np.argsort(-pk)[:8])
        ep, ef = estimates(r, pt, l, n, c1); eph, efh = estimates(r, pt, lh, n, c1); keep = np.abs(ep - ef) <= DROP
        rec = dict(frame=frame, scenario=s_, snr=snr, err=dict(
            fused=arm(C, obs, truth, l, ef), fused_drop=arm(C, obs, truth, l[keep], ef[keep]),
            pilot_est=arm(C, obs, truth, lh, eph), fused_est=arm(C, obs, truth, lh, efh)),
            dropped=int((~keep).sum()), missed=[int(x) for x in l if x not in lh])
        rows.append(rec)
    return rows


def pair(rows, a, b, rng):
    A = np.array([r['err'][a] > 0 for r in rows], float); Bv = np.array([r['err'][b] > 0 for r in rows], float)
    idx = rng.integers(0, len(rows), (2000, len(rows))); d = (A[idx] - Bv[idx]).mean(1)
    return dict(fer_a=A.mean(), fer_b=Bv.mean(), diff=float((A - Bv).mean()), ci=np.percentile(d, [2.5, 97.5]).tolist())


def read(out):
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; rng = np.random.default_rng(20261122)
    res = dict(n=len(rows), c05=pair(rows, 'pilot_est', 'fused_est', rng), c06=pair(rows, 'fused', 'fused_drop', rng),
               mean_dropped=float(np.mean([r['dropped'] for r in rows])), mean_missed=float(np.mean([len(r['missed']) for r in rows])))
    for snr in sorted({r['snr'] for r in rows}):
        res[f'fer_{snr}'] = {a: float(np.mean([x['err'][a] > 0 for x in rows if x['snr'] == snr])) for a in rows[0]['err']}
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--out', default='out_c20261122b3')
    ap.add_argument('--snrs', default='350,400'); ap.add_argument('--frames', default='41260,41460'); a = ap.parse_args()
    snrs = tuple(int(x) for x in a.snrs.split(',')); frames = range(*map(int, a.frames.split(',')))
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    if a.cmd == 'run':
        with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
            for rows in p.imap_unordered(job, [(f, s, snrs) for f in frames for s in SCEN]):
                for r in rows:
                    print(json.dumps(r), file=fh, flush=True)
    read(out)
