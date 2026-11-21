#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-c06 (2026-11-21, runner l): integer versus fractional path delays, paired, full receiver.
Reuses l2_batch7_wideband (band-limited periodic interpolation, zero time scaling) and l2_batch3 / stageA; no receiver code is touched.
  python l2_batch9_fracdelay.py run --out out13 ; python l2_batch9_fracdelay.py read --out out13
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, WORKERS, stageA, scale_of  # noqa: E402
from l2_batch7_wideband import to_time, to_daft, wide_path  # noqa: E402
CFG = dict(frames=[45000, 45600], scenario='U', rho=250, ctrl_snrs=[350, 400, 450, 500], exp_snrs=[400, 500, 600])


def job(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    base = stage3.inputs(ctx, frame, CFG['scenario'], CFG['rho']); sig = None; rec = dict(frame=frame)
    for snr in sorted(set(CFG['ctrl_snrs']) | set(CFG['exp_snrs'])):
        raw, obs, truth = stage3.observed(ctx, base, CFG['rho'], snr)
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'])
        if sig is None:
            x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / scale_of(raw, obs); tsig = to_time(x, c1, c2)
            l = np.asarray(truth['l_i'], int); k = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
            off = np.random.default_rng([SEED, frame, 93]).uniform(-0.5, 0.5, len(l))
            ci = sum(gi * wide_path(tsig, float(li), ki, 0.0) for li, ki, gi in zip(l, k, g))
            ce = sum(gi * wide_path(tsig, float(li) + oi, ki, 0.0) for li, ki, gi, oi in zip(l, k, g, off))
            sig = (to_daft(ci, c1, c2), to_daft(ce, c1, c2))
            rec['gate'] = float(np.linalg.norm(sig[0] + w - obs['y']) / np.linalg.norm(obs['y'])); pw = np.abs(g) ** 2
            rec['main_tap_share'] = float(np.sum(pw * np.sinc(off) ** 2) / pw.sum())
        for name, y, snrs in (('ctrl', sig[0], CFG['ctrl_snrs']), ('exp', sig[1], CFG['exp_snrs'])):
            if snr in snrs:
                o = dict(obs, y=y + w); dec, arr, syn, _ = stageA.f0(C, o); r = b3.score_f0(C, o, truth, dec, arr, syn, True)
                rec[f'{name}_{snr}'] = int(r['errors'] > 0); rec[f'{name}_{snr}_f0'] = int(r['f0_errors'] > 0)
    return [rec]


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / 'rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read(out):
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'rows.jsonl.gz', 'rt')]; n = len(rows); rng = np.random.default_rng(SEED)
    res = dict(_argv=sys.argv, _config=CFG, frames=n, gate_max=max(r['gate'] for r in rows), main_tap_share_mean=float(np.mean([r['main_tap_share'] for r in rows])),
               fail={k: int(sum(r[k] for r in rows)) for k in sorted(rows[0]) if k.startswith(('ctrl_', 'exp_'))})
    def cmp(a, b):
        d = np.array([r[a] - r[b] for r in rows]); bs = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]
        return dict(point=float(d.mean()), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    res['exp500_minus_ctrl450'] = cmp('exp_500', 'ctrl_450'); res['exp500_minus_ctrl400'] = cmp('exp_500', 'ctrl_400'); res['exp600_minus_ctrl500'] = cmp('exp_600', 'ctrl_500')
    res['exp400_minus_ctrl350'] = cmp('exp_400', 'ctrl_350'); res['exp600_minus_ctrl400'] = cmp('exp_600', 'ctrl_400'); res['exp600_minus_ctrl350'] = cmp('exp_600', 'ctrl_350')
    res['loss_gt_0p5'] = bool(res['exp500_minus_ctrl450']['ci95'][0] > 0); res['loss_lt_0p5'] = bool(res['exp500_minus_ctrl450']['ci95'][1] < 0)
    res['loss_gt_1'] = bool(res['exp500_minus_ctrl400']['ci95'][0] > 0 or res['exp600_minus_ctrl500']['ci95'][0] > 0)
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('time', 'run', 'read')); ap.add_argument('--out', required=True); a = ap.parse_args()
    if a.mode == 'time':
        t0 = time.process_time(); r = [job(f)[0] for f in (45000, 45001)]; print(json.dumps(r)); print('cpu per frame', (time.process_time() - t0) / 2)
    else:
        dict(run=run, read=read)[a.mode](a.out)
