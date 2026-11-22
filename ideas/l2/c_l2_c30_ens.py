"""L2 runner c, card I-20261122-c30: parity-selected diversity over the main-chain slot cap.  Run cap 8; if the FINAL codeword
(after A1) still fails parity, rerun the whole chain with cap 12; if that fails too, cap 16.  Output = first config whose final
codeword passes parity, else the cap-8 output.  Selection uses the syndrome only (no truth).  K = detector noise factor (c11)."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); K = float(os.environ.get('C30_K', 1)); CAPS = (8, 12, 16)
FRAMES = range(*(int(x) for x in os.environ.get('C30_FRAMES', '47360,47660').split(',')))

def chain(C, obs, truth, cap):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; otr = nat.time_refine
    def tr(*a, **k):
        k['max_paths'] = cap; return otr(*a, **k)
    nat.time_refine = tr
    try: d, arr, syn, _ = st.e1.f0_state(ctx, dict(obs, sigma2=float(obs['sigma2']) * K))
    finally: nat.time_refine = otr
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(st.e1.hd.syndrome_weight(ctx, d['decoded']) > 0) if hasattr(st.e1, 'hd') else int(ctx.hd.syndrome_weight(ctx, d['decoded']) > 0)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); R = {c: chain(C, obs, truth, c) for c in CAPS}; ens = {}
        for nm, order in (('ens2', (8, 12)), ('ens3', (8, 12, 16)), ('ens12_8', (12, 8))):
            ens[nm] = next((R[c][0] for c in order if not R[c][1]), R[order[0]][0])
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err={**{f'cap{c}': R[c][0] for c in CAPS}, **ens}, fsyn={f'cap{c}': R[c][1] for c in CAPS}))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c30'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        print(job((41003, 'G'))); sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    best = min(('cap8', 'cap12', 'cap16'), key=lambda k: F[k].mean())
    res = dict(n=n, rho=RHO, snrs=SNRS, K=K, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               undetected={f'cap{c}': int(sum(r['err'][f'cap{c}'] > 0 and not r['fsyn'][f'cap{c}'] for r in rows)) for c in CAPS}, false_alarm={f'cap{c}': int(sum(r['err'][f'cap{c}'] == 0 and r['fsyn'][f'cap{c}'] for r in rows)) for c in CAPS},
               best_single=best, cap8_minus={k: ci(F['cap8'] - F[k]) for k in F if k != 'cap8'}, best_single_minus={k: ci(F[best] - F[k]) for k in ('ens2', 'ens3', 'ens12_8')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
