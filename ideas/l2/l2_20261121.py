#!/usr/bin/env python3
"""Idea-funnel L2 checks, round 2026-11-21 (runner l), for cards I-20261121-08, -02 and -10.
Source: experiments/data_pilot_fer_20261121/stageA.py, stageA2.py, stageA3.py (setup, f0, f0_true, z_paths,
support_stats are imported, not copied).  Not callable from those scripts because their one_arm fixes the round-0
gains ('true' | 'ls'), the detector gain mode ('joint') and the pilot (ZC root 7); here these are the arms.

  python l2_20261121.py smoke --out out     gates + CPU cost on a few keys
  python l2_20261121.py c08   --out out     card 08: gain-only vs Doppler-only round-0 error at matched per-path channel-error power
  python l2_20261121.py c02   --out out     card 02: true round-0 channel, detector gain mode joint vs fixed, low rho
  python l2_20261121.py c10   --out out     card 10: same frame, noise and data with the superimposed pilot sequence swapped
  python l2_20261121.py read  --out out     summaries -> out/summary.json
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'experiments' / 'data_pilot_fer_20261121'))
import stageA, stageA2, stageA3  # noqa: E402
from stageA import SCENARIOS, setup, support_stats  # noqa: E402
from stageA2 import f0_true  # noqa: E402

SEED, WORKERS = 20261121, 12
CFG = dict(
    c08=dict(frames=[41000, 41100], rhos=[100], snrs=[300, 400, 500], sigmas_millibin=[100, 200],
             modes=['joint', 'fixed']),
    c02=dict(frames=[41000, 41040], rhos=[50, 75, 100], snrs=[300, 400, 500, 600, 800, 1200], modes=['joint', 'fixed']),
    c10=dict(frames=[41000, 41060], rhos=[100, 150, 200], snrs=[400, 500, 600], pilots=['zc7', 'rand', 'imp']),
)


def ramp_power(delta, n):
    """Mean |exp(j 2 pi delta (k - (n-1)/2) / n) - 1|^2: per-unit-gain channel-error power of a Doppler error delta (bins)
    after the gain is re-referenced to the frame centre (zero-mean phase ramp)."""
    k = np.arange(n) - (n - 1) / 2
    return float(np.mean(np.abs(np.exp(2j * np.pi * delta * k / n) - 1) ** 2))


def perturb(truth, kind, sigma, z, phi, n):
    """Round-0 channel for one arm.  dop: Doppler + sigma z, gain rotated so the error is a zero-mean ramp.
    gain: true Doppler, gain error of the same per-path power as dop, random direction phi.  Returns (truth', NMSE)."""
    nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    if kind == 'ref':
        return dict(truth), 0.0
    d = sigma * z
    E = np.array([ramp_power(x, n) for x in d])
    if kind == 'dop':
        pert = dict(truth, k_real=nu + d, g_i=g * np.exp(-1j * np.pi * d * (n - 1) / n))
    elif kind == 'gain':
        pert = dict(truth, g_i=g * (1 + np.sqrt(E) * np.exp(1j * phi)))
    else:
        raise ValueError(kind)
    return pert, float(np.sum(np.abs(g) ** 2 * E) / np.sum(np.abs(g) ** 2))


def f0_mode(C, obs, pert, gain_mode):
    """stageA2.f0_true with the detector gain mode overridden for this call only."""
    native = C['ctx'].native
    orig = native.receive
    if gain_mode != 'joint':
        native.receive = lambda *a, **kw: orig(*a, **dict(kw, gain_mode=gain_mode))
    try:
        return f0_true(C, obs, pert, 'true')
    finally:
        native.receive = orig


def score_f0(C, obs, truth, dec, arrays, syndrome, branch):
    ctx, stage3 = C['ctx'], C['stage3']
    s2 = float(obs['sigma2'])
    rec = dict(syndrome=int(syndrome),
               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    if branch:
        if syndrome:
            br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
            rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
        else:
            rec['errors'] = rec['f0_errors']
    return rec


def gain_stats(arrays, truth):
    """Round-0 detector output gains against the true gains (paths matched by delay)."""
    l = [int(x) for x in np.asarray(truth['l_i'])]; g = np.asarray(truth['g_i'], complex)
    if sorted(int(d) for d in arrays['r0_delays']) != sorted(l):
        return dict(rot_deg=None, cos=None, ratio=None)
    gt = g[[l.index(int(d)) for d in arrays['r0_delays']]]; gd_ = np.asarray(arrays['r0_gains'], complex)
    ip = np.vdot(gt, gd_)
    return dict(rot_deg=float(np.degrees(np.angle(ip))), cos=float(abs(ip) / np.linalg.norm(gd_) / np.linalg.norm(gt)),
                ratio=float(np.linalg.norm(gd_) / np.linalg.norm(gt)))


def inject_arm(C, obs, truth, kind, sigma, mode, z, phi, branch):
    n = len(obs['y'])
    pert, nmse = perturb(truth, kind, sigma, z, phi, n)
    dec, arrays, syndrome, _ = f0_mode(C, obs, pert, mode)
    rec = score_f0(C, obs, truth, dec, arrays, syndrome, branch)
    rec.update(nmse=nmse, gain=gain_stats(arrays, truth))
    return rec


def seeds(frame, s_, n):
    z = stageA3.z_paths(frame, s_, n)
    phi = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 8]).uniform(0, 2 * np.pi, n)
    return z, phi


def key_c08(C, base, s_, rho, snr, frame, cfg):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    z, phi = seeds(frame, s_, len(truth['l_i'])); arms = {}
    for mode in cfg['modes']:
        arms[f'ref|{mode}'] = inject_arm(C, obs, truth, 'ref', 0, mode, z, phi, mode == 'joint')
        for s in cfg['sigmas_millibin']:
            for kind in ('dop', 'gain'):
                arms[f'{kind}{s:03d}|{mode}'] = inject_arm(C, obs, truth, kind, s / 1000, mode, z, phi, mode == 'joint')
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, arms=arms)


def key_c02(C, base, s_, rho, snr, frame, cfg):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    z, phi = seeds(frame, s_, len(truth['l_i']))
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame,
                arms={f'ref|{m}': inject_arm(C, obs, truth, 'ref', 0, m, z, phi, False) for m in cfg['modes']})


def pilot_seq(name, n):
    if name == 'zc7':
        return None
    if name == 'rand':
        return np.exp(2j * np.pi * np.random.default_rng([SEED, 10]).uniform(size=n))
    if name == 'imp':
        p = np.zeros(n, complex); p[n // 2] = np.sqrt(n)
        return p
    raise ValueError(name)


def swap_pilot(raw, obs, seq):
    """Same channel, data and noise; pilot replaced by sqrt(rho) * seq (same pilot power).  Exact by linearity."""
    if seq is None:
        return obs
    p0 = np.asarray(obs['pilot'], complex)
    p1 = np.sqrt(np.vdot(p0, p0).real / np.vdot(seq, seq).real) * seq
    return dict(obs, y=np.asarray(obs['y'], complex) + np.asarray(raw['H']) @ (p1 - p0), pilot=p1)


def key_c10(C, base, s_, rho, snr, frame, cfg):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    arms = {}
    for name in cfg['pilots']:
        o = swap_pilot(raw, obs, pilot_seq(name, len(obs['y'])))
        dec, arrays, syndrome, _ = stageA.f0(C, o)
        arms[name] = score_f0(C, o, truth, dec, arrays, syndrome, True)
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, arms=arms)


KEYFN = dict(c08=key_c08, c02=key_c02, c10=key_c10)


def frame_job(job):
    mode, frame = job
    C = setup(); cfg = CFG[mode]; rows = []
    for s_ in SCENARIOS:
        for rho in cfg['rhos']:
            base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
            for snr in cfg['snrs']:
                rows.append(KEYFN[mode](C, base, s_, rho, snr, frame, cfg))
    return rows


def run(mode, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    path = out / f'{mode}_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    cfg = CFG[mode]; frames = list(range(*cfg['frames'])); t0 = time.time(); n = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(frame_job, [(mode, f) for f in frames]):
            for r in rows:
                print(json.dumps(r), file=fh); n += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / f'{mode}_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(cfg, seed=SEED, workers=WORKERS,
        scenarios=SCENARIOS), keys=n, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}')
    print(mode, 'keys', n, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3), 'wall', round(time.time() - t0))


def stage_rows(name, shard='rows_shard000.jsonl.gz'):
    rows = {}
    with gzip.open(HERE.parents[1] / 'experiments' / 'data_pilot_fer_20261121' / 'out' / name / shard, 'rt') as fh:
        for line in fh:
            r = json.loads(line); rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    return rows


def smoke(out):
    """G1 ref|joint reproduces stage A2 'full'; G2 ref|fixed keeps the injected gains; G3 zc7 reproduces stage A 'base';
    G4 pilot swap: H(p1-p0) from raw['H'] equals the path model; G5 rho = 75 inputs exist.  Then CPU cost per key."""
    from physical import regressors
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    a2, a = stage_rows('stageA2'), stage_rows('stageA')
    keys = [k for k in a2 if k[1] == 100 and k[2] in (400, 600) and k in a][:4]
    res = []
    for s_, rho, snr, frame in keys:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        z, phi = seeds(frame, s_, len(truth['l_i']))
        r = inject_arm(C, obs, truth, 'ref', 0, 'joint', z, phi, True); b = a2[(s_, rho, snr, frame)]['arms']['full']
        g1 = all(r[k] == b[k] for k in ('syndrome', 'f0_errors', 'errors'))
        rf = inject_arm(C, obs, truth, 'ref', 0, 'fixed', z, phi, False)
        g2 = rf['gain']['cos'] is not None and rf['gain']['cos'] > 1 - 1e-9 and abs(rf['gain']['ratio'] - 1) < 1e-9
        dec, arrays, syn, _ = stageA.f0(C, obs); rz = score_f0(C, obs, truth, dec, arrays, syn, True)
        b0 = a[(s_, rho, snr, frame)]['arms']['base']
        g3 = all(rz[k] == b0[k] for k in ('syndrome', 'f0_errors', 'errors'))
        seq = pilot_seq('rand', len(obs['y'])); o = swap_pilot(raw, obs, seq)
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
        model = regressors(o['pilot'] - obs['pilot'], l, nu, ctx.system.c1, ctx.system.c2) @ g
        diff = o['y'] - obs['y']
        g4 = float(np.linalg.norm(model - diff) / np.linalg.norm(diff))
        pd, nm = perturb(truth, 'dop', .2, z, phi, len(obs['y'])); pg, nm2 = perturb(truth, 'gain', .2, z, phi, len(obs['y']))
        res.append(dict(key=[s_, rho, snr, frame], G1=bool(g1), G2=bool(g2), G3=bool(g3), G4_rel=g4, nmse_s200=nm,
                        pilot_power_ratio=float(np.vdot(o['pilot'], o['pilot']).real / np.vdot(obs['pilot'], obs['pilot']).real)))
    base = stage3.inputs(ctx, 41000, 'U', 75); stage3.observed(ctx, base, 75, 600)
    cost = {}
    for mode in ('c08', 'c02', 'c10'):
        cfg = CFG[mode]; t = time.process_time(); k = 0
        for snr in cfg['snrs'][:2]:
            base = stage3.inputs(ctx, 41099, 'G', cfg['rhos'][0]); KEYFN[mode](C, base, 'G', cfg['rhos'][0], snr, 41099, cfg); k += 1
        per = (time.process_time() - t) / k
        nkeys = (cfg['frames'][1] - cfg['frames'][0]) * len(SCENARIOS) * len(cfg['rhos']) * len(cfg['snrs'])
        cost[mode] = dict(cpu_seconds_per_key=per, keys=nkeys, projected_core_hours=per * nkeys / 3600)
    o_ = dict(_argv=sys.argv, gates=res, G5_rho75=True, cost=cost,
              ok=all(x['G1'] and x['G2'] and x['G3'] and x['G4_rel'] < 1e-8 for x in res))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / 'smoke.json').write_text(json.dumps(o_, indent=1)); print(json.dumps(o_, indent=1))


def load_rows(out, mode):
    with gzip.open(Path(out) / f'{mode}_rows.jsonl.gz', 'rt') as fh:
        return [json.loads(l) for l in fh]


def rate(xs):
    xs = list(xs)
    return [int(sum(xs)), len(xs)]


def read(out):
    res = dict(_argv=sys.argv, _config=dict(CFG, seed=SEED))
    for mode in ('c08', 'c02', 'c10'):
        if not (Path(out) / f'{mode}_rows.jsonl.gz').exists():
            continue
        rows = load_rows(out, mode); tab = {}
        for rho in sorted({r['rho'] for r in rows}):
            for snr in sorted({r['snr'] for r in rows}):
                sel = [r for r in rows if r['rho'] == rho and r['snr'] == snr]
                cell = {}
                for arm in sel[0]['arms']:
                    A = [r['arms'][arm] for r in sel]
                    c = dict(r0_fail=rate(a['r0_errors'] > 0 for a in A), f0_fail=rate(a['f0_errors'] > 0 for a in A))
                    if 'errors' in A[0]:
                        c['final_fail'] = rate(a['errors'] > 0 for a in A)
                    if 'nmse' in A[0]:
                        c['nmse_db_mean'] = None if A[0]['nmse'] == 0 else float(10 * np.log10(np.mean([a['nmse'] for a in A])))
                        rot = [a['gain']['rot_deg'] for a in A if a['gain']['rot_deg'] is not None]
                        c['gain_rot_absdeg_median'] = float(np.median(np.abs(rot))) if rot else None
                        c['gain_rot_gt45'] = rate(abs(x) > 45 for x in rot)
                        c['gain_ratio_median'] = float(np.median([a['gain']['ratio'] for a in A if a['gain']['ratio'] is not None])) if rot else None
                    if mode == 'c10':
                        c['r0_support_right'] = rate(a['r0']['support_right'] for a in A)
                        c['r0_missing_power_mean'] = float(np.mean([a['r0']['missing_power'] for a in A]))
                        e = [a['r0']['doppler_err'] for a in A if a['r0']['doppler_err'] is not None]
                        c['r0_doppler_err_mean'] = float(np.mean(e)) if e else None
                    cell[arm] = c
                tab[f'rho{rho}_snr{snr}'] = cell
        res[mode] = tab
        if mode == 'c08':   # paired discordance, dop vs gain at the same sigma and mode (F0 failure), all SNR pooled
            pairs = {}
            for s in CFG['c08']['sigmas_millibin']:
                for m in CFG['c08']['modes']:
                    d = [(r['arms'][f'dop{s:03d}|{m}']['f0_errors'] > 0, r['arms'][f'gain{s:03d}|{m}']['f0_errors'] > 0) for r in rows]
                    pairs[f's{s:03d}|{m}'] = dict(dop_only_fail=sum(a and not b for a, b in d), gain_only_fail=sum(b and not a for a, b in d),
                                                  both=sum(a and b for a, b in d), neither=sum(not a and not b for a, b in d))
            res['c08_pairs_f0'] = pairs
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'c08', 'c02', 'c10', 'read'))
    ap.add_argument('--out', required=True); a = ap.parse_args()
    if a.mode == 'smoke':
        smoke(a.out)
    elif a.mode == 'read':
        read(a.out)
    else:
        run(a.mode, a.out)
