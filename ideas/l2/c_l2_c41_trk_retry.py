"""L2 runner c, card I-20261122-c41: parity-driven retry inside tracking.  Setting of c31 / c34 (frame 1 at RHO1 supplies its
estimated geometry; frame 2 at RHO2).  Frame-2 configs: warm (inherited geometry), cold, warm12 / cold12 (same with slot cap 12).
lad2 = warm -> cold; lad4 = warm -> cold -> warm12 -> cold12 (first whose final codeword passes parity, else warm).
Fair reference on frame 1 itself: f1 (plain), f1_ens3 (c30 ladder 8 -> 12 -> 16).  Parity only, no truth at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
from c_l2_c33_split import capped
SNRS, WORKERS, SCEN = m_.SNRS, 5, ('U', 'G'); RHO1, RHO2, K1, K2, DRIFT = w.RHO1, w.RHO2, w.K1, w.K2, w.DRIFT
FRAMES = range(*(int(x) for x in os.environ.get('C41_FRAMES', '49960,50160').split(',')))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b2 = st.inputs(ctx, frame, s_, RHO2); b1 = st.inputs(ctx, frame + w.OFF, s_, RHO1); rows = []
    for snr in SNRS:
        raw2, obs2, t2 = st.observed(ctx, b2, RHO2, snr); raw1, obs1, t1 = st.observed(ctx, b1, RHO1, snr); rng = np.random.default_rng([20261122, 31, frame, snr, 0 if s_ == 'U' else 1])
        l2, k2, g2 = np.asarray(t2['l_i']).astype(int), np.asarray(t2['k_real'], float), np.asarray(t2['g_i'], complex)
        o1 = w.resynth(C, raw1, obs1, t1, l2, k2 - rng.uniform(-DRIFT, DRIFT, len(l2)), np.abs(g2) * np.exp(2j * np.pi * rng.random(len(l2))))
        e1, f1, a1, _ = w.run(C, o1, t1, K1); geom = (a1['r1_delays'], a1['r1_dopplers']); F1 = [(e1, f1)] + [capped(C, c, lambda: w.run(C, o1, t1, K1)[:2]) for c in (12, 16)]
        R = dict(warm=w.run(C, obs2, t2, K2, geom)[:2], cold=w.run(C, obs2, t2, K2)[:2], warm12=capped(C, 12, lambda: w.run(C, obs2, t2, K2, geom)[:2]), cold12=capped(C, 12, lambda: w.run(C, obs2, t2, K2)[:2]))
        pick = lambda order, T: next((T[c][0] for c in order if not T[c][1]), T[order[0]][0]); err = {k: v[0] for k, v in R.items()}
        err.update(lad2=pick(('warm', 'cold'), R), lad4=pick(('warm', 'cold', 'warm12', 'cold12'), R), cold_ens2=pick(('cold', 'cold12'), R), f1=e1, f1_ens3=pick((0, 1, 2), F1))
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, fsyn={k: v[1] for k, v in R.items()}, f1_fsyn=[x[1] for x in F1]))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c41'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    und = int(sum(1 for r in rows for k in r['fsyn'] if r['err'][k] > 0 and not r['fsyn'][k]))
    res = dict(n=n, rho1=RHO1, rho2=RHO2, K1=K1, K2=K2, snrs=SNRS, drift=DRIFT, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               undetected=und, f1_ens3_minus={k: ci(F['f1_ens3'] - F[k]) for k in ('warm', 'lad2', 'lad4')}, f1_minus={k: ci(F['f1'] - F[k]) for k in ('warm', 'lad2', 'lad4')}, warm_minus={k: ci(F['warm'] - F[k]) for k in ('lad2', 'lad4')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
