#!/usr/bin/env python3
"""Idea-funnel L2 check, batch 5 (2026-11-21, runner l), for card I-20261121-c29 (asked by the cross-model gate):
how does a pooled (common) round-0 Doppler estimate behave as the Doppler spread between paths grows?
Same delays, gains, data and noise as the stage-A frame; only the path Dopplers are replaced by nu_c + s z_i
(nu_c = Doppler of the strongest path, z_i ~ N(0,1) fixed per frame) and the observation is rebuilt from the path model.
Arms (true delays in both, as in stage A4): per = the existing per-path pilot estimator; com = one Doppler for all paths
(pilot LS residual minimised over a grid), then pilot LS gains.  Imports l2_batch3 / stageA; the grid search is the only new code.
  python l2_batch5.py c29 --out out6 ; python l2_batch5.py read --out out6
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, WORKERS, stageA, score_f0, scale_of  # noqa: E402
from l2_batch2 import f0_true  # noqa: E402
from l2_20261121 import stageA3  # noqa: E402

CFG = dict(frames=[41000, 41100], scenario='U', rhos=[100, 150], snr=500, spreads=[0.0, 0.02, 0.05, 0.1, 0.3])


def job(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; out = []
    from physical import regressors
    c1, c2 = ctx.system.c1, ctx.system.c2; s_ = CFG['scenario']
    for rho in CFG['rhos']:
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, rho), rho, CFG['snr'])
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
        x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / scale_of(raw, obs)
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'])
        rel = float(np.linalg.norm(regressors(x, l, nu, c1, c2) @ g + w - obs['y']) / np.linalg.norm(obs['y']))
        assert rel < 1e-8, rel
        pw = np.abs(g) ** 2; z = stageA3.z_paths(frame, s_, len(l)); nc = float(nu[np.argmax(pw)])
        for s in CFG['spreads']:
            nu2 = np.clip(nc + s * z, -2.0, 2.0); t2 = dict(truth, k_real=nu2)
            o = dict(obs, y=regressors(x, l, nu2, c1, c2) @ g + w)
            dec, arr, syn, _ = stageA.f0(C, o, stageA.genie_inject(C, o, t2)); per = score_f0(C, o, t2, dec, arr, syn, True)

            def resid(v):
                A = regressors(np.asarray(o['pilot'], complex), l, np.full(len(l), v), c1, c2)
                return float(np.linalg.norm(o['y'] - A @ np.linalg.lstsq(A, o['y'], rcond=None)[0]))
            grid = np.arange(-2.5, 2.5001, 0.05); v0 = grid[int(np.argmin([resid(v) for v in grid]))]
            fine = np.arange(v0 - 0.05, v0 + 0.0501, 0.005); vh = float(fine[int(np.argmin([resid(v) for v in fine]))])
            dec, arr, syn, _ = f0_true(C, o, dict(t2, k_real=np.full(len(l), vh)), 'ls'); com = score_f0(C, o, t2, dec, arr, syn, True)
            out.append(dict(frame=frame, rho=rho, spread=s, recon_rel=rel, com_hat_err=abs(vh - nc),
                            per=dict(dop=per['r0']['doppler_err'], r0=per['r0_errors'], f0=per['f0_errors'], fin=per['errors']),
                            com=dict(dop=float(np.sum(pw * np.abs(vh - nu2)) / pw.sum()), r0=com['r0_errors'], f0=com['f0_errors'], fin=com['errors'])))
    return out


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / 'c29_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); n = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); n += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'c29_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=n,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('c29 rows', n, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read(out):
    rows = [json.loads(l) for l in gzip.open(Path(out) / 'c29_rows.jsonl.gz', 'rt')]; tab = {}
    for rho in CFG['rhos']:
        for s in CFG['spreads']:
            sel = [r for r in rows if r['rho'] == rho and r['spread'] == s]
            tab[f'rho{rho}_s{s}'] = dict(n=len(sel), per_dop=float(np.mean([r['per']['dop'] for r in sel if r['per']['dop'] is not None])),
                com_dop=float(np.mean([r['com']['dop'] for r in sel])), com_hat_err_median=float(np.median([r['com_hat_err'] for r in sel])),
                per_fail=[sum(r['per'][k] > 0 for r in sel) for k in ('r0', 'f0', 'fin')], com_fail=[sum(r['com'][k] > 0 for r in sel) for k in ('r0', 'f0', 'fin')])
    res = dict(_argv=sys.argv, _config=CFG, max_recon_rel=max(r['recon_rel'] for r in rows), table=tab)
    (Path(out) / 'c29_summary.json').write_text(json.dumps(res, indent=1))
    print('max recon rel', res['max_recon_rel'])
    for k, v in tab.items():
        print(k, 'n', v['n'], 'dop per %.3f com %.3f (common-hat median err %.3f) | fail r0/f0/final per %s com %s' % (v['per_dop'], v['com_dop'], v['com_hat_err_median'], v['per_fail'], v['com_fail']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('c29', 'read')); ap.add_argument('--out', required=True); a = ap.parse_args()
    read(a.out) if a.mode == 'read' else run(a.out)
