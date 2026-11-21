#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l06 (2026-11-21, runner l): natural (not redrawn) channel draws, original receive window versus a window
aligned to the first path.  New code: the continuous-transmission time-domain observation (paths beyond the prefix, previous frame leaking in).
Channel draws call gen_fixed.one_attempt; receiver and frames are imported (l2_batch3 / stageA).
  python l2_batch8_window.py smoke|run|read --out out11
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, WORKERS, stageA, scale_of  # noqa: E402
from l2_batch7_wideband import to_time, to_daft  # noqa: E402
CFG = dict(frames=[41000, 41600], scenario='U', rho=300, snr=750, lcp=102, prev_offset=5000)


def draw(C, frame):
    gf = sys.modules.get('gen_fixed') or __import__('gen_fixed'); pd = sys.modules.get('p1_driver') or __import__('p1_driver')
    flags = pd.SCENARIOS[CFG['scenario']]; s = C['ctx'].system; rs = np.random.RandomState([SEED % 2 ** 32, frame])
    d = gf.one_attempt(s, rs, flags); l = np.asarray(gf.delay_bins(s, d['delay_idx_bar'], flags, clip=False), int)
    k = np.asarray(gf.doppler_k_real(s, d['doppler_a'], flags, None), float); g = np.asarray(d['gain_tap'], complex)
    cls = 'A' if l.max() <= CFG['lcp'] else ('T' if l.max() - l.min() <= CFG['lcp'] else 'W')
    return l, k, g, cls


def signal(C, frame):
    stage3, ctx = C['stage3'], C['ctx']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, CFG['scenario'], CFG['rho']), CFG['rho'], CFG['snr'])
    x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / scale_of(raw, obs)
    return obs, truth, x, np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'])


def observe(cur, prev, l, k, g, off):
    """Time-domain window starting `off` samples after the nominal frame start; stream = [previous frame | prefix | current frame]."""
    n = len(cur); idx = np.arange(n); y = np.zeros(n, complex)
    for li, ki, gi in zip(l, k, g):
        m = idx + off - li
        y += gi * np.exp(2j * np.pi * ki * (idx + off) / n) * np.where(m >= -CFG['lcp'], cur[m % n], prev[(n + m + CFG['lcp']) % n])
    return y


def final_errors(C, o, truth):
    stage3, ctx = C['stage3'], C['ctx']; dec, arr, syn, _ = stageA.f0(C, o)
    if syn:
        dec = stage3.e1.run_branch(ctx, C['cd'], o, arr, 'A1')['decoder']
    return int(stage3.e1.gd.score(ctx, dec['decoded'], truth))


def job(frame):
    C = setup(); s = C['ctx'].system; c1, c2 = float(s.c1), float(s.c2)
    l, k, g, cls = draw(C, frame); obs, truth, x, w = signal(C, frame); _, _, xp, _ = signal(C, frame + CFG['prev_offset'])
    cur, prev = to_time(x, c1, c2), to_time(xp, c1, c2); pw = np.abs(g) ** 2
    rec = dict(frame=frame, cls=cls, first=int(l.min()), last=int(l.max()), outside_power=float(pw[l > CFG['lcp']].sum()),
               outside_power_aligned=float(pw[l - l.min() > CFG['lcp']].sum()))
    rec['orig'] = int(final_errors(C, dict(obs, y=to_daft(observe(cur, prev, l, k, g, 0), c1, c2) + w), truth) > 0)
    if cls != 'A':
        rec['aligned'] = int(final_errors(C, dict(obs, y=to_daft(observe(cur, prev, l, k, g, int(l.min())), c1, c2) + w), truth) > 0)
    return [rec]


def smoke(out):
    from physical import regressors
    C = setup(); s = C['ctx'].system; c1, c2 = float(s.c1), float(s.c2); gate = None; counts = dict(A=0, T=0, W=0)
    for f in range(41000, 41060):
        l, k, g, cls = draw(C, f); counts[cls] += 1
        if cls == 'A' and gate is None:
            obs, truth, x, w = signal(C, f); _, _, xp, _ = signal(C, f + CFG['prev_offset'])
            ref = regressors(x, l, k, c1, c2) @ g; mine = to_daft(observe(to_time(x, c1, c2), to_time(xp, c1, c2), l, k, g, 0), c1, c2)
            gate = float(np.linalg.norm(mine - ref) / np.linalg.norm(ref))
    t0 = time.process_time(); r = [job(f)[0] for f in (41000, 41001, 41002, 41003)]; cpu = (time.process_time() - t0) / 4
    o = dict(_argv=sys.argv, G1=gate, class_counts_60=counts, rows=r, cpu_per_frame=cpu, lcp_system=int(s.l_max_cap), power_norm=float(np.sum(np.abs(draw(C, 41000)[2]) ** 2)))
    Path(out).mkdir(parents=True, exist_ok=True); (Path(out) / 'smoke.json').write_text(json.dumps(o, indent=1)); print(json.dumps(o, indent=1))


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
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'rows.jsonl.gz', 'rt')]; n = len(rows); res = dict(_argv=sys.argv, _config=CFG, draws=n, classes={})
    share = {}
    for c in 'ATW':
        s = [r for r in rows if r['cls'] == c]; share[c] = len(s) / n
        d = dict(n=len(s), share=share[c], orig_fail=int(sum(r['orig'] for r in s)))
        if c != 'A':
            d.update(aligned_fail=int(sum(r['aligned'] for r in s)), rescued=int(sum(r['orig'] and not r['aligned'] for r in s)),
                     worsened=int(sum(r['aligned'] and not r['orig'] for r in s)),
                     outside_power_median=float(np.median([r['outside_power'] for r in s])), outside_power_aligned_median=float(np.median([r['outside_power_aligned'] for r in s])))
        res['classes'][c] = d
    f = {c: res['classes'][c]['orig_fail'] / max(res['classes'][c]['n'], 1) for c in 'ATW'}
    fa = {c: res['classes'][c].get('aligned_fail', res['classes'][c]['orig_fail']) / max(res['classes'][c]['n'], 1) for c in 'ATW'}
    res['natural_fer_original_window'] = float(sum(share[c] * f[c] for c in 'ATW')); res['natural_fer_aligned_window'] = float(sum(share[c] * fa[c] for c in 'ATW'))
    res['card_rule_kill'] = bool(res['classes']['T']['rescued'] == 0)
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', required=True); a = ap.parse_args()
    dict(smoke=smoke, run=run, read=read)[a.mode](a.out)
