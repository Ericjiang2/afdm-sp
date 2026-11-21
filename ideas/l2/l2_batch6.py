#!/usr/bin/env python3
"""Idea-funnel L2 check, batch 6 (2026-11-21, runner l): same receiver, same frames, chirp rate c1 = project value vs c1 = 0
(DAFT with c1 = 0 is the DFT, i.e. OFDM with the same superimposed pilot), under the project's Doppler law and under a
near-common Doppler law (strongest path's Doppler + .02 bin spread, card c25's premise).  The observation is rebuilt from the
path model with the chosen c1 (same delays, gains, data, noise).  Imports l2_batch3 / stageA; only the rebuild is new.
  python l2_batch6.py run --out out8 ; python l2_batch6.py read --out out8
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, WORKERS, stageA, score_f0, scale_of  # noqa: E402
from l2_20261121 import stageA3  # noqa: E402
CFG = dict(frames=[41000, 41100], scenario='U', rho=250, snrs=[500, 600], spread=0.02)


def job(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; out = []
    from physical import regressors
    c1p, c2 = float(ctx.system.c1), ctx.system.c2; s_ = CFG['scenario']; rho = CFG['rho']
    for snr in CFG['snrs']:
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, rho), rho, snr)
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
        x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / scale_of(raw, obs)
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'])
        rel = float(np.linalg.norm(regressors(x, l, nu, c1p, c2) @ g + w - obs['y']) / np.linalg.norm(obs['y']))
        z = stageA3.z_paths(frame, s_, len(l)); nc = float(nu[np.argmax(np.abs(g))])
        laws = dict(orig=nu, common=np.clip(nc + CFG['spread'] * z, -2.0, 2.0)); rec = dict(frame=frame, snr=snr, recon_rel=rel, arms={})
        for law, nu2 in laws.items():
            for name, c1 in (('afdm', c1p), ('ofdm', 0.0)):
                o = dict(obs, y=regressors(x, l, nu2, c1, c2) @ g + w); t2 = dict(truth, k_real=nu2)
                ctx.system.c1 = c1
                try:
                    dec, arr, syn, _ = stageA.f0(C, o); r = score_f0(C, o, t2, dec, arr, syn, True)
                    rec['arms'][f'{law}|{name}'] = dict(r0=r['r0_errors'], f0=r['f0_errors'], fin=r['errors'], right=bool(r['r0']['support_right']))
                except Exception as e:                       # report, do not hide
                    rec['arms'][f'{law}|{name}'] = dict(error=repr(e)[:200])
                finally:
                    ctx.system.c1 = c1p
        out.append(rec)
    return out


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / 'rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); n = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); n += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=n,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', n, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read(out):
    rows = [json.loads(l) for l in gzip.open(Path(out) / 'rows.jsonl.gz', 'rt')]; tab = {}
    errs = sorted({a['error'] for r in rows for a in r['arms'].values() if 'error' in a})
    for snr in CFG['snrs']:
        sel = [r for r in rows if r['snr'] == snr]
        for arm in sel[0]['arms']:
            A = [r['arms'][arm] for r in sel if 'error' not in r['arms'][arm]]
            tab[f'snr{snr}_{arm}'] = dict(n=len(A), r0_fail=sum(a['r0'] > 0 for a in A), f0_fail=sum(a['f0'] > 0 for a in A),
                                          final_fail=sum(a['fin'] > 0 for a in A), r0_support_right=sum(a['right'] for a in A))
    res = dict(_argv=sys.argv, _config=CFG, max_recon_rel=max(r['recon_rel'] for r in rows), errors=errs, table=tab)
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print('max recon rel', res['max_recon_rel'], 'errors', errs)
    for k, v in tab.items():
        print(k, v)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('run', 'read')); ap.add_argument('--out', required=True); a = ap.parse_args()
    read(a.out) if a.mode == 'read' else run(a.out)
