#!/usr/bin/env python
"""Idea-funnel local round 4, L2 batch 7 (card I-20261122-l40, Zheng half; criteria in PREDICTIONS_r4_batch7.md; runner l, claude-fable-5.2).
Zo01 (the only working Zheng-port variant in res-20261016-01) plus the coded second outer round that zport_driver implements for Za09 only ('Zt').
zport_driver / zport_rx imported unchanged; round 1 must reproduce the archived Zo01 rows; B comes from the archived P1 rows on the same keys.
  python l2_r4_zo01_turbo.py gate|run|read --out out_r4b7
"""
import argparse, glob, gzip, json, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
TRF = HERE.parents[1] / 'experiments' / 'tcom_reference_frame_20261015'
FRAMES, SCEN, RHOS, SNRS = range(0, 150), ('U', 'G'), (.3, .5), (600, 700, 800)
WORKERS, BOOT, SEED = 48, 2000, 20261126


def setup():
    sys.path.insert(0, str(TRF))
    import zport_driver as zd
    ctx = zd.P.load_context(); zd.add_sources(ctx)
    return zd, ctx, zd.ZPort(ctx.system.c1, ctx.system.c2, N=int(ctx.system.N_total)), zd.P.make_seed_fn()


def key_rows(zd, ctx, zp, seed_fn, frame, sc, rho, snrs):
    raw, diag = zd.P.generate(ctx, sc, rho, snrs[0] / 100, frame, seed_fn); x, yn = zd.impulse_frame(ctx, raw, rho)
    for snr in snrs:
        s2 = 10 ** (-snr / 100 / 10); y = yn + np.sqrt(s2) * raw['noise']; zp.delta = .1
        r1 = zp.run(y, rho, s2, 'frac', select='omp'); d1 = zd.decode(ctx, zd.ZPort.llr_from_posterior(r1['p_j']))
        prior = zd.ZPort.prior_from_llr(np.asarray(d1['raw_check_extrinsic'])); lp = zd.ZPort.llr_from_posterior(prior)
        r2 = zp.run(y, rho, s2, 'frac', prior=prior, select='omp')
        d2 = zd.decode(ctx, np.clip(zd.ZPort.llr_from_posterior(r2['p_j']) - lp, -20., 20.))
        a, b = zd.score(ctx, d1, raw), zd.score(ctx, d2, raw)
        yield dict(scenario=sc, rho_permille=int(round(rho * 1000)), snr_centi_db=snr, frame=frame, r1=dict(fer=a['fer'], info_errors=a['info_errors'], decode_ok=bool(a['decode_ok'])),
                   r2=dict(fer=b['fer'], info_errors=b['info_errors']))


def shard_job(job):
    idx, frames, out = job; zd, ctx, zp, seed_fn = setup(); n = 0
    with open(Path(out) / f'rows_shard{idx:03d}.jsonl', 'w') as fh:
        for f in frames:
            for sc in SCEN:
                for rho in RHOS:
                    for row in key_rows(zd, ctx, zp, seed_fn, f, sc, rho, SNRS):
                        print(json.dumps(row), file=fh, flush=True); n += 1
    return idx, n


def archived(d, keys, slim):
    out = {}
    for p in sorted(glob.glob(str(TRF / 'out' / d / 'rows_shard*.jsonl*'))):
        with (gzip.open(p, 'rt') if p.endswith('.gz') else open(p)) as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line); k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
                    if k in keys:
                        out[k] = slim(r)
    return out


def gate(out):
    zd, ctx, zp, seed_fn = setup(); recs = []
    keys = {(sc, 300, snr, f) for sc in SCEN for snr in (600, 800) for f in (0, 1)}
    old = archived('zport', keys, lambda r: r['variants']['Zo01']['info_errors'])
    for sc in SCEN:
        for f in (0, 1):
            for row in key_rows(zd, ctx, zp, seed_fn, f, sc, .3, (600, 800)):
                k = (sc, 300, row['snr_centi_db'], f); recs.append(dict(key=list(k), match=row['r1']['info_errors'] == old[k], r1=row['r1']['info_errors'], r2=row['r2']['info_errors']))
                print(recs[-1], flush=True)
    ok = len(recs) == 8 and all(r['match'] for r in recs)
    json.dump(dict(pass_=ok, records=recs), open(out / 'gate.json', 'w'), indent=1); print('GATE', 'PASS' if ok else 'FAIL')


def run(out):
    fr = list(FRAMES); jobs = [(i, fr[i::WORKERS], str(out)) for i in range(WORKERS)]; t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    json.dump(dict(_argv=sys.argv, _config=dict(frames=[0, 149], scenarios=SCEN, rhos=RHOS, snrs=SNRS, arm='Zo01 + coded second outer round (Zt logic)'),
                   keys=done, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), open(out / 'run.json', 'w'), indent=1)
    print('DONE', done, round((ch.ru_utime + ch.ru_stime) / 3600, 2), 'core-hours')


def read(out):
    N = {}
    for p in sorted(out.glob('rows_shard*.jsonl')):
        for line in open(p):
            r = json.loads(line); N[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    Z = archived('zport', set(N), lambda r: r['variants']['Zo01']['fer']); B = archived('p1', set(N), lambda r: r['arms']['B']['fer'])
    res = dict(keys=len(N), round1_matches_archive=float(np.mean([N[k]['r1']['fer'] == Z[k] for k in N])), table={}, pooled={})
    rng = np.random.default_rng(SEED); fr = sorted({k[3] for k in N})
    for rho in (300, 500):
        for snr in SNRS:
            ks = [k for k in N if k[1] == rho and k[2] == snr]
            res['table'][f'{rho}_{snr}'] = dict(n=len(ks), r1=float(np.mean([N[k]['r1']['fer'] for k in ks])), r2=float(np.mean([N[k]['r2']['fer'] for k in ks])),
                                                gated=float(np.mean([N[k]['r1']['fer'] if N[k]['r1']['decode_ok'] else N[k]['r2']['fer'] for k in ks])),
                                                r1_check_pass=float(np.mean([N[k]['r1']['decode_ok'] for k in ks])),
                                                B=float(np.mean([B[k] for k in ks])) if all(k in B for k in ks) else None)
        ks = [k for k in N if k[1] == rho and k[2] in (700, 800)]
        a = np.array([N[k]['r1']['fer'] for k in ks], float); b = np.array([N[k]['r2']['fer'] for k in ks], float)
        fi = {f: [i for i, k in enumerate(ks) if k[3] == f] for f in fr}; Bx = rng.integers(0, len(fr), (BOOT, len(fr)))
        per = np.array([[(a - b)[fi[f]].sum(), len(fi[f])] for f in fr]); s = per[Bx]
        res['pooled'][str(rho)] = dict(r1=float(a.mean()), r2=float(b.mean()), diff=float((a - b).mean()), ci95=np.percentile(s[:, :, 0].sum(1) / s[:, :, 1].sum(1), [2.5, 97.5]).tolist(),
                                       rescue=int(((a == 1) & (b == 0)).sum()), harm=int(((a == 0) & (b == 1)).sum()))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=('gate', 'run', 'read')); ap.add_argument('--out', default='out_r4b7'); a = ap.parse_args()
    out = HERE / a.out; out.mkdir(exist_ok=True); {'gate': gate, 'run': run, 'read': read}[a.cmd](out)
