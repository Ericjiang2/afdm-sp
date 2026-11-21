#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l08 (child of c12), 2026-11-21, runner l.  Paired replay: per-path time scaling
(wideband Doppler) versus the best pure-shift fit of every path.  New code: band-limited periodic interpolation of the
transmitted time signal and the per-path pure-shift fit; everything else imported (l2_batch3 / stageA).
  python l2_batch7_wideband.py smoke --out out10 ; python l2_batch7_wideband.py run --out out10 ; python l2_batch7_wideband.py read --out out10
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, WORKERS, stageA, scale_of  # noqa: E402
CFG = dict(frames=[41000, 42000], scenario='U', rho=100, snr=400, v_common=2.0)
CFG2 = dict(corr=dict(frames=[42000, 43000], snr=400), nocorr=dict(frames=[42000, 42300], snr=800))      # batch 15: final errors of the full receiver


def parts(C, frame, snr=None):
    stage3, ctx = C['stage3'], C['ctx']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, CFG['scenario'], CFG['rho']), CFG['rho'], snr or CFG['snr'])
    x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / scale_of(raw, obs)
    w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'])
    return raw, obs, truth, x, w


def to_time(x, c1, c2):
    n = len(x); idx = np.arange(n)
    return np.exp(-2j * np.pi * c1 * idx ** 2) * np.fft.ifft(np.exp(-2j * np.pi * c2 * idx ** 2) * x) * np.sqrt(n)


def to_daft(t, c1, c2):
    n = len(t); idx = np.arange(n)
    return np.exp(2j * np.pi * c2 * idx ** 2) * np.fft.fft(np.exp(2j * np.pi * c1 * idx ** 2) * t) / np.sqrt(n)


def wide_path(tsig, l, k, a):
    """Time-domain waveform of one unit-gain path: s((1 + a)(n - N/2) + N/2 - l) exp(j 2 pi k n / N), s = periodic band-limited interpolation."""
    n = len(tsig); idx = np.arange(n); S = np.fft.fft(tsig) / n; kk = np.fft.fftfreq(n, 1.0 / n)
    t = (1 + a) * (idx - n / 2) + n / 2 - l
    return (np.exp(2j * np.pi * np.outer(t, kk) / n) @ S) * np.exp(2j * np.pi * idx * k / n)


def fit_shift(tsig, l, k0, wv):
    """Best pure shift at delay l: Doppler and complex gain maximising the match to wv (transmitted signal known)."""
    n = len(tsig); idx = np.arange(n); ref = tsig[(idx - l) % n]; e = np.vdot(ref, ref).real
    def corr(nu):
        return np.sum(np.conj(ref)[None, :] * wv[None, :] * np.exp(-2j * np.pi * np.outer(nu, idx) / n), axis=1)
    g1 = k0 + np.arange(-0.5, 0.5001, 0.01); c = np.abs(corr(g1)); nu = g1[int(np.argmax(c))]
    g2 = nu + np.arange(-0.01, 0.010001, 0.0005); c2 = corr(g2); j = int(np.argmax(np.abs(c2)))
    return float(g2[j]), complex(c2[j] / e)


def build(C, frame, arm, snr=None, vscale=1.0):
    ctx = C['ctx']; s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    raw, obs, truth, x, w = parts(C, frame, snr); n = len(x)
    l = np.asarray(truth['l_i'], int); k = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    kc = CFG['v_common'] / float(s.c_sound) * float(s.fc) / float(s.fs) * n if arm == 'corr' else 0.0
    kr = (k - kc) * vscale; a = kr * float(s.fs) / (float(s.fc) * n); tsig = to_time(x, c1, c2)
    wide = np.zeros(n, complex); narrow = np.zeros(n, complex); nu_hat = []; g_hat = []
    for li, ki, ai, gi in zip(l, kr, a, g):
        wv = wide_path(tsig, li, ki, ai); nh, gh = fit_shift(tsig, li, ki, wv)
        idx = np.arange(n); nv = gh * tsig[(idx - li) % n] * np.exp(2j * np.pi * idx * nh / n)
        wide += gi * wv; narrow += gi * nv; nu_hat.append(nh); g_hat.append(gh)
    pw = np.abs(g) ** 2
    info = dict(resid_db=float(10 * np.log10(np.vdot(wide - narrow, wide - narrow).real / np.vdot(narrow, narrow).real)),
                fit_shift_err=float(np.sum(pw * np.abs(np.array(nu_hat) - kr)) / pw.sum()), drift_samples_rms=float(np.sqrt(np.sum(pw * (a * n) ** 2) / pw.sum())),
                gain_loss=float(np.sum(pw * np.abs(g_hat)) / pw.sum()))
    info['truth_fit'] = dict(truth, k_real=np.array(nu_hat), g_i=g * np.array(g_hat))
    return obs, truth, to_daft(narrow, c1, c2) + w, to_daft(wide, c1, c2) + w, info


def job(frame):
    C = setup(); gd = C['stage3'].e1.gd; out = dict(frame=frame)
    for arm in ('corr', 'nocorr'):
        obs, truth, yc, ye, info = build(C, frame, arm); info.pop('truth_fit'); rec = dict(info)
        for name, y in (('ctrl', yc), ('exp', ye)):
            dec, arr, syn, _ = stageA.f0(C, dict(obs, y=y))
            rec[name] = int(gd.score(C['ctx'], dec['decoded'], truth) > 0); rec[name + '_r0'] = int(gd.score(C['ctx'], arr['r0_decoded'], truth) > 0)
        out[arm] = rec
    return [out]


def job2(key):
    arm, frame = key; C = setup()
    obs, truth, yc, ye, info = build(C, frame, arm, CFG2[arm]['snr']); tf = info.pop('truth_fit'); rec = dict(arm=arm, frame=frame, **info)
    for name, y in (('ctrl', yc), ('exp', ye)):
        o = dict(obs, y=y); dec, arr, syn, _ = stageA.f0(C, o); r = b3.score_f0(C, o, tf, dec, arr, syn, True)
        rec[name] = int(r['errors'] > 0); rec[name + '_f0'] = int(r['f0_errors'] > 0)
    return [rec]


CFG3 = dict(scales=[0.3, 0.6], frames=[43000, 43600], snr=400)      # batch 18: dose-response for card l10


def job3(key):
    sc, frame = key; C = setup()
    obs, truth, yc, ye, info = build(C, frame, 'corr', CFG3['snr'], sc); tf = info.pop('truth_fit'); rec = dict(scale=sc, frame=frame, **info)
    for name, y in (('ctrl', yc), ('exp', ye)):
        o = dict(obs, y=y); dec, arr, syn, _ = stageA.f0(C, o); r = b3.score_f0(C, o, tf, dec, arr, syn, True); rec[name] = int(r['errors'] > 0)
    return [rec]


def run3(out):
    out = Path(out); path = out / 'rows3.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    jobs = [(sc, f) for sc in CFG3['scales'] for f in range(*CFG3['frames'])]; t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job3, jobs):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'run3.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, batch18=CFG3, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read3(out):
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'rows3.jsonl.gz', 'rt')]; rng = np.random.default_rng(SEED); res = dict(_argv=sys.argv, _config=CFG3)
    for sc in CFG3['scales']:
        sel = [r for r in rows if r['scale'] == sc]; c = np.array([r['ctrl'] for r in sel]); e = np.array([r['exp'] for r in sel]); d = e - c; n = len(d)
        bs = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]; dr = np.array([r['drift_samples_rms'] for r in sel])
        res[f'scale{sc}'] = dict(frames=n, ctrl_fail=int(c.sum()), exp_fail=int(e.sum()), exp_only=int(((e == 1) & (c == 0)).sum()), ctrl_only=int(((c == 1) & (e == 0)).sum()),
            extra_fer=float(d.mean()), upper95_one_sided=float(np.percentile(bs, 95)), lower95_one_sided=float(np.percentile(bs, 5)),
            resid_db_median=float(np.median([r['resid_db'] for r in sel])), law_db_median=float(np.median(10 * np.log10(np.pi ** 2 / 36 * dr ** 2))), drift_samples_rms_median=float(np.median(dr)))
    (Path(out) / 'summary3.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


CFG4 = dict(frames=[44000, 44600], snr=400)      # batch 19: noise-equivalent controls asked by the gate


def job4(frame):
    C = setup(); obs, truth, yc, ye, info = build(C, frame, 'corr', CFG4['snr']); tf = info.pop('truth_fit'); n = len(yc)
    pres = float(np.vdot(ye - yc, ye - yc).real / n); rng = np.random.default_rng([SEED, frame, 77])
    e = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * np.sqrt(pres / 2); rec = dict(frame=frame, resid_power=pres, sigma2=float(obs['sigma2']), **info)
    for name, o in (('ctrl', dict(obs, y=yc)), ('exp', dict(obs, y=ye)), ('awgn', dict(obs, y=yc + e)), ('exp_s2', dict(obs, y=ye, sigma2=float(obs['sigma2']) + pres))):
        dec, arr, syn, _ = stageA.f0(C, o); rec[name] = int(b3.score_f0(C, o, tf, dec, arr, syn, True)['errors'] > 0)
    return [rec]


def run4(out):
    out = Path(out); path = out / 'rows4.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job4, list(range(*CFG4['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'run4.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, batch19=CFG4, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read4(out):
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'rows4.jsonl.gz', 'rt')]; rng = np.random.default_rng(SEED); n = len(rows)
    A = {k: np.array([r[k] for r in rows]) for k in ('ctrl', 'exp', 'awgn', 'exp_s2')}; res = dict(_argv=sys.argv, _config=CFG4, frames=n, fail={k: int(v.sum()) for k, v in A.items()})
    def ci(a, b):
        d = A[a] - A[b]; bs = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]
        return dict(point=float(d.mean()), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], a_only=int(((A[a] == 1) & (A[b] == 0)).sum()), b_only=int(((A[b] == 1) & (A[a] == 0)).sum()))
    res['exp_minus_ctrl'] = ci('exp', 'ctrl'); res['awgn_minus_ctrl'] = ci('awgn', 'ctrl'); res['exp_minus_awgn'] = ci('exp', 'awgn'); res['exp_s2_minus_exp'] = ci('exp_s2', 'exp')
    res['resid_over_noise_db_median'] = float(np.median([10 * np.log10(r['resid_power'] / r['sigma2']) for r in rows]))
    k = res['exp_minus_awgn']['ci95']; res['acts_as_noise'] = bool(k[0] >= -0.05 and k[1] <= 0.05); res['structure_matters'] = bool(k[0] > 0.03)
    res['telling_helps'] = bool(res['exp_s2_minus_exp']['ci95'][1] < -0.03)
    (Path(out) / 'summary4.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def run2(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / 'rows2.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    jobs = [(arm, f) for arm, c in CFG2.items() for f in range(*c['frames'])]; t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job2, jobs):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'run2.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, **{'batch15': CFG2}, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read2(out):
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'rows2.jsonl.gz', 'rt')]; rng = np.random.default_rng(SEED); res = dict(_argv=sys.argv, _config=CFG2)
    for arm in CFG2:
        sel = [r for r in rows if r['arm'] == arm]; c = np.array([r['ctrl'] for r in sel]); e = np.array([r['exp'] for r in sel]); d = e - c; n = len(d)
        bs = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]
        res[arm] = dict(frames=n, ctrl_fail=int(c.sum()), exp_fail=int(e.sum()), exp_only=int(((e == 1) & (c == 0)).sum()), ctrl_only=int(((c == 1) & (e == 0)).sum()),
                        extra_fer=float(d.mean()), upper95_one_sided=float(np.percentile(bs, 95)), lower95_one_sided=float(np.percentile(bs, 5)),
                        f0_ctrl_fail=int(sum(r['ctrl_f0'] for r in sel)), f0_exp_fail=int(sum(r['exp_f0'] for r in sel)),
                        resid_db_median=float(np.median([r['resid_db'] for r in sel])), drift_samples_rms_median=float(np.median([r['drift_samples_rms'] for r in sel])))
    k = res['corr']; fer = k['ctrl_fail'] / k['frames']
    res['saturated'] = bool(fer > 0.9 or fer < 0.1); res['card_rule_kill'] = bool((not res['saturated']) and k['upper95_one_sided'] < 0.03)
    (Path(out) / 'summary2.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def smoke(out):
    from physical import regressors
    C = setup(); ctx = C['ctx']; s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    raw, obs, truth, x, w = parts(C, 41000); n = len(x); tsig = to_time(x, c1, c2)
    l = np.asarray(truth['l_i'], int); k = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    R = regressors(x, l, k, c1, c2); g1 = max(float(np.linalg.norm(to_daft(wide_path(tsig, li, ki, 0.0), c1, c2) - R[:, i]) / np.linalg.norm(R[:, i])) for i, (li, ki) in enumerate(zip(l, k)))
    g2 = float(np.linalg.norm(R @ g + w - obs['y']) / np.linalg.norm(obs['y']))
    t = time.process_time(); r = job(41000)[0]; cpu = time.process_time() - t
    o = dict(_argv=sys.argv, G1=g1, G2=g2, system=dict(fc=float(s.fc), fs=float(s.fs), c_sound=float(s.c_sound), N=n, c1=c1, c2=c2,
             k_common=CFG['v_common'] / float(s.c_sound) * float(s.fc) / float(s.fs) * n), k_real=k.tolist(), frame41000=r, cpu_per_frame=cpu,
             projected_core_hours=cpu * (CFG['frames'][1] - CFG['frames'][0]) / 3600)
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
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'rows.jsonl.gz', 'rt')]; rng = np.random.default_rng(SEED); res = dict(_argv=sys.argv, _config=CFG, frames=len(rows))
    for arm in ('corr', 'nocorr'):
        c = np.array([r[arm]['ctrl'] for r in rows]); e = np.array([r[arm]['exp'] for r in rows]); d = e - c; n = len(d)
        bs = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]
        res[arm] = dict(ctrl_fail=int(c.sum()), exp_fail=int(e.sum()), exp_only=int(((e == 1) & (c == 0)).sum()), ctrl_only=int(((c == 1) & (e == 0)).sum()),
                        extra_fer=float(d.mean()), upper95_one_sided=float(np.percentile(bs, 95)), lower95_one_sided=float(np.percentile(bs, 5)),
                        r0_ctrl_fail=int(sum(r[arm]['ctrl_r0'] for r in rows)), r0_exp_fail=int(sum(r[arm]['exp_r0'] for r in rows)),
                        resid_db_median=float(np.median([r[arm]['resid_db'] for r in rows])), fit_shift_err_mean=float(np.mean([r[arm]['fit_shift_err'] for r in rows])),
                        drift_samples_rms_median=float(np.median([r[arm]['drift_samples_rms'] for r in rows])), gain_loss_mean=float(np.mean([r[arm]['gain_loss'] for r in rows])))
    res['card_rule_kill'] = bool(res['corr']['upper95_one_sided'] < 0.03)
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read', 'time2', 'run2', 'read2', 'run3', 'read3', 'run4', 'read4')); ap.add_argument('--out', required=True); a = ap.parse_args()
    if a.mode == 'time2':
        t0 = time.process_time(); r = [job2(('corr', f))[0] for f in (42000, 42001, 42002)] + [job2(('nocorr', 42000))[0]]; print(json.dumps(r)); print('cpu per corr frame', (time.process_time() - t0) / 4)
    else:
        dict(smoke=smoke, run=run, read=read, run2=run2, read2=read2, run3=run3, read3=read3, run4=run4, read4=read4)[a.mode](a.out)
