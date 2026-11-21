#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l09 (2026-11-21, runner l), asked by the gate: finite-length paired comparison of three symbol bases
under perfect channel knowledge.  New code: a soft-cancellation LMMSE turbo loop around the project's LDPC decoder; setup imported from l2_batch3.
  python l2_l09_coded.py smoke|run|read --out out9
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, WORKERS, scale_of  # noqa: E402
CFG = dict(frames=[41000, 41200], scenario='U', rho=100, snrs=[200, 250, 300, 350], rounds=10, dec_iters=50, pd=0.5)


def turbo(C, H, y, s2, truth):
    from messages import moments
    ctx = C['ctx']; dec_fn = ctx.native.decoder_messages; gd = C['stage3'].e1.gd; n = H.shape[1]; a = np.sqrt(CFG['pd'] / 2)
    prior = np.zeros(2 * n); err = None; used = 0
    for r in range(CFG['rounds']):
        mu, v, _ = moments(np.clip(prior, -20, 20), CFG['pd']); used = r + 1
        Fm = np.linalg.solve((H * v[None, :]) @ H.conj().T + s2 * np.eye(n), H)
        s = np.real(np.sum(H.conj() * Fm, axis=0)); z = mu + (Fm.conj().T @ (y - H @ mu)) / s; eta = np.maximum(1 / s - v, 1e-9)
        llr = np.concatenate([4 * a * z.real / eta, 4 * a * z.imag / eta])
        dec = dec_fn(ctx.code, np.clip(llr, -20, 20), maxiter=CFG['dec_iters']); err = int(gd.score(ctx, dec['decoded'], truth))
        if bool(dec['decode_ok']):
            break
        prior = np.asarray(dec['raw_check_extrinsic'], float)
    return err, used


def job(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; out = []
    base = stage3.inputs(ctx, frame, CFG['scenario'], CFG['rho']); mats = None
    for snr in CFG['snrs']:
        raw, obs, truth = stage3.observed(ctx, base, CFG['rho'], snr)
        if mats is None:
            Hd = np.asarray(raw['H'], complex); n = Hd.shape[0]; idx = np.arange(n); c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
            F = np.fft.fft(np.eye(n), axis=0) / np.sqrt(n)
            A = np.exp(2j * np.pi * c2 * idx ** 2)[:, None] * F * np.exp(2j * np.pi * c1 * idx ** 2)[None, :]
            Ht = A.conj().T @ Hd @ A; mats = dict(afdm=(Hd, np.eye(n)), sc=(Ht, A.conj().T), ofdm=(F @ Ht @ F.conj().T, F @ A.conj().T))
        d = np.asarray(raw['data'], complex) / scale_of(raw, obs); s2 = float(obs['sigma2']); w = np.sqrt(s2) * np.asarray(raw['noise'])
        rec = dict(frame=frame, snr=snr)
        for name, (H, T) in mats.items():
            e, used = turbo(C, H, H @ d + T @ w, s2, truth); rec[name] = e; rec[name + '_rounds'] = used
        out.append(rec)
    return out


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / 'l09_coded_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'l09_coded_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read(out):
    rows = [json.loads(x) for x in gzip.open(Path(out) / 'l09_coded_rows.jsonl.gz', 'rt')]; rng = np.random.default_rng(SEED); res = dict(_argv=sys.argv, _config=CFG, per_snr={})
    for snr in CFG['snrs']:
        s = [r for r in rows if r['snr'] == snr]
        res['per_snr'][str(snr)] = dict(n=len(s), **{b: int(sum(r[b] > 0 for r in s)) for b in ('afdm', 'sc', 'ofdm')},
            sc_only=int(sum(r['sc'] > 0 and r['afdm'] == 0 for r in s)), afdm_only=int(sum(r['afdm'] > 0 and r['sc'] == 0 for r in s)),
            ofdm_only=int(sum(r['ofdm'] > 0 and r['afdm'] == 0 for r in s)), afdm_only_vs_ofdm=int(sum(r['afdm'] > 0 and r['ofdm'] == 0 for r in s)),
            mean_rounds={b: float(np.mean([r[b + '_rounds'] for r in s])) for b in ('afdm', 'sc', 'ofdm')})
    frames = sorted({r['frame'] for r in rows}); by = {f: [r for r in rows if r['frame'] == f] for f in frames}
    def diff(b, fs):
        rr = [r for f in fs for r in by[f]]; return float(np.mean([(r[b] > 0) - (r['afdm'] > 0) for r in rr]))
    for b in ('sc', 'ofdm'):
        bs = [diff(b, [frames[i] for i in rng.integers(0, len(frames), len(frames))]) for _ in range(2000)]
        res[b + '_minus_afdm'] = dict(point=diff(b, frames), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    k = res['sc_minus_afdm']; res['supported'] = bool(abs(k['point']) <= 0.03 and k['ci95'][0] >= -0.06 and k['ci95'][1] <= 0.06); res['refuted'] = bool(k['ci95'][0] > 0.03)
    (Path(out) / 'l09_coded_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', required=True); a = ap.parse_args()
    if a.mode == 'smoke':
        t0 = time.process_time(); r = job(41000); print(json.dumps(r)); print('cpu per frame', time.process_time() - t0)
    else:
        dict(run=run, read=read)[a.mode](a.out)
