"""L2 runner c, card I-20261122-c33: cluster channel of c28 (2 companion rays per path, same delay, Doppler within +-.5 bin).
Second pass with a cluster-level basis, cheap version: take pass 1's main-chain geometry, split every path into a pair at Doppler
+-HALF bin (same delay), hand the 16 paths to the chain as the front-end output (gains by pilot least squares), slot cap 16.
Arms: p1 (unmodified chain, ref); rerun (pass 2 from pass 1's own 8 paths; control for 'a second pass'); split (always pass 2 with
the split basis); ens (p1 unless its final codeword fails parity, then split; fall back to p1 if split fails parity too)."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c28_cluster as c28
import c_l2_c31_warm as c31
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); HALF = float(os.environ.get('C33_HALF', .25))
BETAS = tuple(float(x) for x in os.environ.get('C33_BETAS', '0,.1,.3').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C33_FRAMES', '48360,48560').split(',')))

def capped(C, n, f):
    nat = C['ctx'].native; otr = nat.time_refine
    def tr(*a, **k):
        k['max_paths'] = n; return otr(*a, **k)
    nat.time_refine = tr
    try: return f()
    finally: nat.time_refine = otr

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = {}
        for beta in BETAS:
            o2 = obs if beta == 0 else c28.inject(C, raw, obs, truth, frame, s_, beta); t = f'b{beta:g}_'
            e1, f1, arr, _ = c31.run(C, o2, truth, 1.); l, k = np.asarray(arr['r1_delays']).astype(int), np.asarray(arr['r1_dopplers'], float)
            er, fr, _, _ = c31.run(C, o2, truth, 1., (l, k))
            es, fs, _, _ = capped(C, 16, lambda: c31.run(C, o2, truth, 1., (np.repeat(l, 2), np.clip(np.repeat(k, 2) + np.tile([-HALF, HALF], len(l)), -3, 3))))
            err.update({t + 'p1': e1, t + 'rerun': er, t + 'split': es, t + 'ens': e1 if not f1 else (es if not fs else e1), t + 'ens_rerun': e1 if not f1 else (er if not fr else e1)})
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c33'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, half=HALF, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               p1_minus={f'b{b:g}_{a_}': ci(F[f'b{b:g}_p1'] - F[f'b{b:g}_{a_}']) for b in BETAS for a_ in ('rerun', 'split', 'ens', 'ens_rerun')},
               ens_rerun_minus_ens={f'b{b:g}': ci(F[f'b{b:g}_ens_rerun'] - F[f'b{b:g}_ens']) for b in BETAS})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
