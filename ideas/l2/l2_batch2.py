#!/usr/bin/env python3
"""Idea-funnel L2 checks, batch 2 (2026-11-21, runner l), for cards I-20261121-c01 and I-20261121-l04.
Source: experiments/data_pilot_fer_20261121/stageA.py / stageA2.py / stageA3.py and ideas/l2/l2_20261121.py (imported).
New file because these arms do not exist there: clipped / tail-only Doppler errors, per-path round-0 logging, and
re-observation of one channel with fresh noise and another frame's codeword.

  python l2_batch2.py smoke --out out2
  python l2_batch2.py c01i  --out out2    c01 intervention: sigma .2 Gaussian Doppler error, all / clipped at .25 / tail only (LS gains)
  python l2_batch2.py c01o  --out out2    c01 observational: per-path round-0 Doppler error of the pilot estimator (true delays)
  python l2_batch2.py l04   --out out2    l04: failed frames re-sent with fresh noise, same codeword vs another codeword
  python l2_batch2.py read  --out out2
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_20261121 as b1  # noqa: E402
from l2_20261121 import SCENARIOS, SEED, WORKERS, setup, stageA, stageA3, f0_true, score_f0, stage_rows  # noqa: E402

CFG = dict(
    c01i=dict(frames=[41000, 41100], rhos=[100], snrs=[400, 500, 600], sigma=0.2, clip=0.25),
    c01o=dict(frames=[41000, 41150], rhos=[100, 150], snrs=[400, 500, 600]),
    l04=dict(rho=100, snr=1200, repeats=8, frame_offset=5000),
)


def arm_ls(C, obs, truth, err):
    pert = dict(truth, k_real=np.asarray(truth['k_real'], float) + err)
    dec, arrays, syndrome, _ = f0_true(C, obs, pert, 'ls')
    return score_f0(C, obs, truth, dec, arrays, syndrome, True)


def key_c01i(C, base, s_, rho, snr, frame, cfg):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    e = cfg['sigma'] * stageA3.z_paths(frame, s_, len(truth['l_i'])); c = cfg['clip']
    g = np.abs(np.asarray(truth['g_i'])) ** 2
    arms = dict(all=arm_ls(C, obs, truth, e), clip=arm_ls(C, obs, truth, np.clip(e, -c, c)),
                tail=arm_ls(C, obs, truth, np.where(np.abs(e) > c, e, 0.0)))
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, n_tail=int(np.sum(np.abs(e) > c)),
                tail_power=float(g[np.abs(e) > c].sum() / g.sum()), arms=arms)


def key_c01o(C, base, s_, rho, snr, frame, cfg):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    dec, arrays, syndrome, _ = stageA.f0(C, obs, stageA.genie_inject(C, obs, truth))
    rec = score_f0(C, obs, truth, dec, arrays, syndrome, True)
    l = [int(x) for x in np.asarray(truth['l_i'])]; nu = np.asarray(truth['k_real'], float)
    g = np.abs(np.asarray(truth['g_i'])) ** 2; s2 = float(obs['sigma2'])
    d0 = [int(x) for x in arrays['r0_delays']]; k0 = np.asarray(arrays['r0_dopplers'], float)
    err = [float(k0[d0.index(li)] - nu[i]) if li in d0 else None for i, li in enumerate(l)]
    rec.update(err=err, power=[float(x) for x in g], relevant=[bool(x >= stageA.TAU * s2) for x in g])
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, arm=rec)


KEYFN = dict(c01i=key_c01i, c01o=key_c01o)


def frame_job(job):
    mode, frame = job
    C = setup(); cfg = CFG[mode]; rows = []
    for s_ in SCENARIOS:
        for rho in cfg['rhos']:
            base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
            for snr in cfg['snrs']:
                rows.append(KEYFN[mode](C, base, s_, rho, snr, frame, cfg))
    return rows


def reobserve(obs, raw, data, noise):
    y = np.asarray(raw['H']) @ (np.asarray(obs['pilot'], complex) + data) + np.sqrt(float(obs['sigma2'])) * noise
    return dict(obs, y=y)


def l04_job(job):
    s_, frame = job
    C = setup(); cfg = CFG['l04']; stage3, ctx = C['stage3'], C['ctx']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, cfg['rho']), cfg['rho'], cfg['snr'])
    # obs is raw divided by scale = sqrt(2 (1 - rho)) (frozen internal convention); data must be scaled the same way
    scale = float(np.linalg.norm(raw['pilot']) / np.linalg.norm(obs['pilot']))
    n = len(obs['y']); d0 = np.asarray(raw['data'], complex) / scale
    recon = np.asarray(raw['H']) @ (np.asarray(obs['pilot'], complex) + d0) + np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'])
    rel = float(np.linalg.norm(recon - obs['y']) / np.linalg.norm(obs['y']))
    assert rel < 1e-9, rel

    def run(o, t):
        dec, arrays, syn, _ = stageA.f0(C, o)
        return score_f0(C, o, t, dec, arrays, syn, True)
    orig = run(obs, truth); reps = []
    for j in range(cfg['repeats']):
        rng = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 40, j])
        noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
        f2 = frame + cfg['frame_offset'] * (j + 1)
        raw2, _, truth2 = stage3.observed(ctx, stage3.inputs(ctx, f2, s_, cfg['rho']), cfg['rho'], cfg['snr'])
        tb = dict(truth, info=truth2['info'])
        a = run(reobserve(obs, raw, d0, noise), truth)
        b = run(reobserve(obs, raw, np.asarray(raw2['data'], complex) / scale, noise), tb)
        reps.append(dict(j=j, A=dict(errors=a['errors'], f0_errors=a['f0_errors'], support_right=a['r0']['support_right']),
                         B=dict(errors=b['errors'], f0_errors=b['f0_errors'], support_right=b['r0']['support_right'])))
    return dict(scenario=s_, frame=frame, recon_rel=rel, noise_power=float(np.mean(np.abs(np.asarray(raw['noise'])) ** 2)),
                orig=dict(errors=orig['errors'], f0_errors=orig['f0_errors']), reps=reps)


def failed_frames():
    cfg = CFG['l04']; out = []
    d = HERE.parents[1] / 'experiments' / 'data_pilot_fer_20261121' / 'out' / 'stageA'
    for p in sorted(d.glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                if r['rho'] == cfg['rho'] and r['snr'] == cfg['snr'] and r['arms']['base']['errors'] > 0:
                    out.append((r['scenario'], r['frame']))
    return sorted(out)


def run(mode, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / f'{mode}_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    jobs = failed_frames() if mode == 'l04' else [(mode, f) for f in range(*CFG[mode]['frames'])]
    fn = l04_job if mode == 'l04' else frame_job
    t0 = time.time(); n = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(fn, jobs):
            for r in (rows if isinstance(rows, list) else [rows]):
                print(json.dumps(r), file=fh); n += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / f'{mode}_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG[mode], seed=SEED, workers=WORKERS),
        rows=n, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print(mode, 'rows', n, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def smoke(out):
    """G1: the 'all' arm reproduces stage A3 's200' rows.  G2: an l04 job reconstructs y and reproduces the stage A failure."""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    a3 = stage_rows('stageA3'); keys = [k for k in a3 if k[1] == 100 and k[2] in (400, 600)][:3]; g1 = []
    t = time.process_time()
    for s_, rho, snr, frame in keys:
        r = key_c01i(C, stage3.inputs(ctx, frame, s_, rho), s_, rho, snr, frame, CFG['c01i'])
        b = a3[(s_, rho, snr, frame)]['arms']['s200']
        g1.append(all(r['arms']['all'][k] == b[k] for k in ('syndrome', 'f0_errors', 'errors')))
    per_i = (time.process_time() - t) / len(keys); t = time.process_time()
    key_c01o(C, stage3.inputs(ctx, 41000, 'U', 100), 'U', 100, 500, 41000, CFG['c01o']); per_o = time.process_time() - t
    ff = failed_frames(); t = time.process_time(); j = l04_job(ff[0]); per_l = time.process_time() - t
    o = dict(_argv=sys.argv, G1=all(g1), failed_frames=ff, G2_recon_rel=j['recon_rel'], G2_orig_fails=j['orig']['errors'] > 0,
             noise_power=j['noise_power'], cpu=dict(c01i_per_key=per_i, c01o_per_key=per_o, l04_per_frame=per_l),
             projected_core_hours=dict(c01i=per_i * 600 / 3600, c01o=per_o * 1800 / 3600, l04=per_l * len(ff) / 3600))
    Path(out).mkdir(parents=True, exist_ok=True); (Path(out) / 'smoke.json').write_text(json.dumps(o, indent=1)); print(json.dumps(o, indent=1))


def load(out, mode):
    with gzip.open(Path(out) / f'{mode}_rows.jsonl.gz', 'rt') as fh:
        return [json.loads(l) for l in fh]


def auc(score, label):
    s = np.asarray(score, float); y = np.asarray(label, bool)
    if y.all() or not y.any():
        return None
    r = np.argsort(np.argsort(s)) + 1.0
    for v in np.unique(s):
        m = s == v; r[m] = r[m].mean()
    return float((r[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum()))


def read(out):
    res = dict(_argv=sys.argv, _config=CFG)
    if (Path(out) / 'c01i_rows.jsonl.gz').exists():
        rows = load(out, 'c01i'); tab = {}
        for snr in sorted({r['snr'] for r in rows}):
            sel = [r for r in rows if r['snr'] == snr]
            tab[str(snr)] = {a: dict(r0_fail=sum(r['arms'][a]['r0_errors'] > 0 for r in sel), f0_fail=sum(r['arms'][a]['f0_errors'] > 0 for r in sel),
                                     final_fail=sum(r['arms'][a]['errors'] > 0 for r in sel), n=len(sel)) for a in ('all', 'clip', 'tail')}
            tab[str(snr)]['frames_with_tail'] = sum(r['n_tail'] > 0 for r in sel)
        res['c01i'] = tab
    if (Path(out) / 'c01o_rows.jsonl.gz').exists():
        rows = load(out, 'c01o'); tab = {}
        for rho in sorted({r['rho'] for r in rows}):
            for snr in sorted({r['snr'] for r in rows}):
                sel = [r['arm'] for r in rows if r['rho'] == rho and r['snr'] == snr]
                e = np.array([abs(x) for a in sel for x, rel in zip(a['err'], a['relevant']) if rel and x is not None])
                mx = [max([abs(x) for x, rel in zip(a['err'], a['relevant']) if rel and x is not None] or [0.0]) for a in sel]
                fail = [a['f0_errors'] > 0 for a in sel]; mean = [a['r0']['doppler_err'] or 0.0 for a in sel]
                has = [m > 0.25 for m in mx]
                tab[f'rho{rho}_snr{snr}'] = dict(n=len(sel), paths=int(e.size), share_gt025=float(np.mean(e > 0.25)), share_gt05=float(np.mean(e > 0.5)),
                    abs_err_median=float(np.median(e)), abs_err_p90=float(np.percentile(e, 90)), abs_err_rms=float(np.sqrt(np.mean(e ** 2))),
                    frames_with_gt025=int(sum(has)), f0_fail=int(sum(fail)),
                    f0_fail_given_gt025=[int(sum(f for f, h in zip(fail, has) if h)), int(sum(has))],
                    f0_fail_given_none=[int(sum(f for f, h in zip(fail, has) if not h)), int(len(has) - sum(has))],
                    auc_max_abs=auc(mx, fail), auc_weighted_mean=auc(mean, fail))
        res['c01o'] = tab
    if (Path(out) / 'l04_rows.jsonl.gz').exists():
        rows = load(out, 'l04'); per = []
        for r in rows:
            a = [x['A']['errors'] > 0 for x in r['reps']]; b = [x['B']['errors'] > 0 for x in r['reps']]
            per.append(dict(scenario=r['scenario'], frame=r['frame'], orig_fail=r['orig']['errors'] > 0, A_fail=int(sum(a)), B_fail=int(sum(b)),
                            n_plus=int(sum(x and not y for x, y in zip(a, b))), n_minus=int(sum(y and not x for x, y in zip(a, b))), reps=len(a)))
        tot = sum(p['reps'] for p in per)
        res['l04'] = dict(frames=per, A_fail_rate=sum(p['A_fail'] for p in per) / tot, B_fail_rate=sum(p['B_fail'] for p in per) / tot,
                          n_plus=sum(p['n_plus'] for p in per), n_minus=sum(p['n_minus'] for p in per), pairs=tot,
                          first_repeat=dict(n_plus=sum(r['reps'][0]['A']['errors'] > 0 and r['reps'][0]['B']['errors'] == 0 for r in rows),
                                            n_minus=sum(r['reps'][0]['B']['errors'] > 0 and r['reps'][0]['A']['errors'] == 0 for r in rows),
                                            A_fail=sum(r['reps'][0]['A']['errors'] > 0 for r in rows), frames=len(rows)))
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'c01i', 'c01o', 'l04', 'read'))
    ap.add_argument('--out', required=True); a = ap.parse_args()
    dict(smoke=smoke, read=read).get(a.mode, lambda o: run(a.mode, o))(a.out)
