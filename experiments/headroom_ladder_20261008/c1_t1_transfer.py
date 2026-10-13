#!/usr/bin/env python
"""C1 T1: transfer curves of the FIXED LDPC code + decoder + soft-symbol mapping used by the C1 SP receiver, AWGN QPSK, no SP.
(task 10-08-doppler-cluster; research/c1-scalar-closure.md sections T-1 and T1.)

Receiver conventions reproduced (reviewed frozen src, byte-identical to the local sp_afdm_native_joint_20260921 / sp_afdm_frozen_20260920):
  decoder input  = clip(LLR, +-20)                                    native_twofft.py:24
  dec            = decoder_messages(code, llr, maxiter=50)            native_twofft.py:24  (receiver -> supplement_messages)
  detector prior = clip(dec['raw_check_extrinsic'], +-20)             native_twofft.py:25
  soft symbols   = moments(clip(dec['raw_app'], +-20), 1 - rho), rho=.5 -> pd = .5     native_twofft.py:26
  moments        : mu = E[d | LLR], v_rep = max(pd - |mu|^2, 0)       messages.py:14
  bit layout     : [all I bits, then all Q bits], L > 0 <-> bit 0, bit 1 <-> component < 0     e1_ldpc.qpsk_map / demap_llr
Simulation: random info -> encode -> d = sqrt(pd) qpsk_map(coded) (|d|^2 = pd) -> y = d + w, w ~ CN(0, pd/q) (data Es/N0 = q),
channel LLR = demap_llr(y, pd/q, sqrt(pd/2)) (exact QPSK/AWGN bit LLR, 4 a Re(y)/sigma^2), clipped +-20.
Frame f uses streams SeedSequence(entropy_words + [DOMAIN, f, component]) (component 2 = info bits, 3 = unit noise), NOT keyed by q
(common random numbers across q).  Coded stage A frames 0..nA-1 at every grid q; stage B frames nA..nA+nB-1 at the n_extra grid points
nearest the stage-A FER=.5 crossing.  Uncoded curves (channel LLR only) use frames 0..nU-1.

Modes: checks | run --stage A|B --shard i --nshard n | select | merge.   One process per shard, single thread (launch_c1t1.sh).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DOMAIN = 0x43315431  # "C1T1"
PD = 0.5  # = 1 - system.rho with the frozen rho = .5 shim
ENTROPY_HEX = hashlib.sha256(b'c1_t1_transfer_20261009').hexdigest()
ENTROPY_WORDS = [int(x) for x in np.frombuffer(bytes.fromhex(ENTROPY_HEX), dtype='<u4').astype(np.uint32)]
BOOT_SEED = 20261009
N_BOOT = 1000
STREAM_ALGORITHM = 'numpy.SeedSequence(8 entropy uint32 words of sha256(b"c1_t1_transfer_20261009"), DOMAIN, frame, component); not keyed by q'
SRC = ('chan', 'app', 'chk')  # channel LLR (uncoded), raw_app, raw_check_extrinsic
SRC_FIELDS = ('v', 'r', 'zr', 'zi', 'vrep')
COUNT_FIELDS = ('info_err', 'coded_err', 'iters', 'decode_ok')
K_INFO = 1024.  # code['k'], asserted in cmd_checks


def parse_list(text, cast):
    return [cast(x) for x in str(text).split(',') if str(x).strip() != '']


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('checks', 'run', 'select', 'merge'), required=True)
    p.add_argument('--stage', choices=('A', 'B'), default='A')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--q-coded-db', default='', help='comma list; default -1.0..4.0 step .2')
    p.add_argument('--q-unc-db', default='', help='comma list; default -10..12 step .5')
    p.add_argument('--frames-coded', type=int, default=3000)
    p.add_argument('--frames-unc', type=int, default=200)
    p.add_argument('--frames-extra', type=int, default=6000)
    p.add_argument('--n-extra', type=int, default=5)
    p.add_argument('--chunk', type=int, default=250, help='frames per task')
    return p.parse_args(argv)


def grids(args):
    def to_deci(text, lo, hi, step):
        if text:
            return [int(round(10 * float(x))) for x in text.split(',') if x.strip()]
        return list(range(lo, hi + 1, step))
    return to_deci(args.q_coded_db, -10, 40, 2), to_deci(args.q_unc_db, -100, 120, 5)  # deci-dB integers


def tasks_for(args, stage, selection=None):
    qc, qu = grids(args)
    out = []
    if stage == 'A':
        for q in qc:
            for f0 in range(0, args.frames_coded, args.chunk):
                out.append(('coded', q, f0, min(args.chunk, args.frames_coded - f0)))
        for q in qu:
            for f0 in range(0, args.frames_unc, args.chunk):
                out.append(('uncoded', q, f0, min(args.chunk, args.frames_unc - f0)))
    else:
        for q in selection:
            for f0 in range(args.frames_coded, args.frames_coded + args.frames_extra, args.chunk):
                out.append(('coded', q, f0, min(args.chunk, args.frames_coded + args.frames_extra - f0)))
    return out


def task_id(t):
    return f'{t[0]}_{t[1]:+04d}_{t[2]:06d}'


# ----------------------------------------------------------------------------- receiver binding
def bind(args):
    import driver as base
    ctx = base.load_context(args)
    from receiver import decoder_messages
    from messages import moments
    import messages
    import receiver
    from afdm_sp_joint_unrolled.e1_ldpc import demap_llr
    ctx.decoder_messages, ctx.moments, ctx.demap_llr = decoder_messages, moments, demap_llr
    ctx.sources['messages'] = base.sha256_file(messages.__file__)
    ctx.sources['receiver'] = base.sha256_file(receiver.__file__)
    ctx.sources['messages_path'] = messages.__file__
    ctx.sources['receiver_path'] = receiver.__file__
    ctx.sources['c1_t1_transfer.py'] = base.sha256_file(Path(__file__).resolve())
    return ctx


def frame_data(ctx, f, q_lin):
    code = ctx.code
    msg = np.random.default_rng(np.random.SeedSequence(ENTROPY_WORDS + [DOMAIN, f, 2]))
    noi = np.random.default_rng(np.random.SeedSequence(ENTROPY_WORDS + [DOMAIN, f, 3]))
    info = msg.integers(0, 2, size=code['k']).astype(np.uint8)
    coded = ctx.encode(code, info)
    d = np.sqrt(PD) * ctx.qpsk_map(coded, scale=1)
    n = len(d)
    unit = (noi.standard_normal(n) + 1j * noi.standard_normal(n)) / np.sqrt(2.)
    sigma2 = PD / q_lin
    y = d + np.sqrt(sigma2) * unit
    llr = np.clip(ctx.demap_llr(y, sigma2, np.sqrt(PD / 2.), clip=1e9), -20., 20.)
    return info, coded, d, llr


def soft_stats(ctx, llr, d):
    mu, vv, _ = ctx.moments(np.clip(llr, -20., 20.), PD)
    e = d - mu
    z = np.mean(e * np.conj(mu))
    return (float(np.mean(np.abs(e) ** 2)), float(np.mean(np.abs(mu) ** 2)), float(z.real), float(z.imag), float(np.mean(vv)))


def run_task(ctx, t):
    kind, ideci, f0, nf = t
    q_lin = 10 ** (ideci / 100.)
    code = ctx.code
    cols = {f'{s}_{k}': [] for s in SRC for k in SRC_FIELDS}
    cols.update({k: [] for k in COUNT_FIELDS})
    cols.update(ll_chan=[], ll_app=[], absdiff_vrep=[])
    for f in range(f0, f0 + nf):
        info, coded, d, llr = frame_data(ctx, f, q_lin)
        cols['ll_chan'].append(ctx.arms.logloss_bits(llr, coded))
        st = soft_stats(ctx, llr, d)
        for k, v in zip(SRC_FIELDS, st):
            cols[f'chan_{k}'].append(v)
        if kind == 'coded':
            dec = ctx.decoder_messages(code, llr, maxiter=50)
            app = np.clip(dec['raw_app'], -20., 20.)
            chk = np.clip(dec['raw_check_extrinsic'], -20., 20.)
            for s, L in (('app', app), ('chk', chk)):
                for k, v in zip(SRC_FIELDS, soft_stats(ctx, L, d)):
                    cols[f'{s}_{k}'].append(v)
            hard = np.asarray(dec['decoded'])
            cols['info_err'].append(int(np.count_nonzero(ctx.extract_info(code, hard) != info)))
            cols['coded_err'].append(int(np.count_nonzero(hard != coded)))
            cols['iters'].append(int(dec['iterations']))
            cols['decode_ok'].append(int(bool(dec['decode_ok'])))
            cols['ll_app'].append(ctx.arms.logloss_bits(app, coded))
        else:
            for s in ('app', 'chk'):
                for k in SRC_FIELDS:
                    cols[f'{s}_{k}'].append(np.nan)
            for k in COUNT_FIELDS:
                cols[k].append(-1)
            cols['ll_app'].append(np.nan)
        cols['absdiff_vrep'].append(abs(cols['chan_vrep'][-1] - (PD - cols['chan_r'][-1])))
    arr = {k: np.asarray(v) for k, v in cols.items()}
    arr['frame'] = np.arange(f0, f0 + nf)
    return arr


def cmd_run(args):
    ctx = bind(args)
    sel = None
    if args.stage == 'B':
        sel = json.loads((args.out / 'stageB_selection.json').read_text())['selected_deci_db']
    tasks = tasks_for(args, args.stage, sel)
    parts = args.out / 'parts'
    parts.mkdir(parents=True, exist_ok=True)
    mine = [t for i, t in enumerate(tasks) if i % args.nshard == args.shard]
    t0 = time.time()
    for t in mine:
        path = parts / (task_id(t) + '.npz')
        if path.exists():
            continue
        t1 = time.time()
        arr = run_task(ctx, t)
        tmp = parts / (task_id(t) + '.tmp.npz')
        np.savez(tmp, **arr)
        os.replace(tmp, path)
        print(f'shard {args.shard} {task_id(t)} {len(arr["frame"])} frames {time.time() - t1:.1f}s', flush=True)
    meta = dict(_argv=sys.argv, _config=config_of(args), stage=args.stage, shard=args.shard, nshard=args.nshard,
                n_tasks=len(mine), seconds=time.time() - t0, sources=ctx.sources, code_g_sha256=ctx.header['code_g_sha256'])
    (parts / f'meta_{args.stage}_{args.shard:03d}.json').write_text(json.dumps(meta, indent=1, default=str))


def config_of(args):
    qc, qu = grids(args)
    return dict(pd=PD, q_coded_deci_db=qc, q_unc_deci_db=qu, frames_coded=args.frames_coded, frames_unc=args.frames_unc,
                frames_extra=args.frames_extra, n_extra=args.n_extra, chunk=args.chunk, maxiter=50, clip=20.,
                entropy_hex=ENTROPY_HEX, entropy_words=ENTROPY_WORDS, domain=DOMAIN, stream_algorithm=STREAM_ALGORITHM,
                boot_seed=BOOT_SEED, n_boot=N_BOOT, native_dir=args.native_dir, baseline_dir=args.baseline_dir,
                python=platform.python_version(), numpy=np.__version__)


# ----------------------------------------------------------------------------- statistics
def load_parts(out, kind):
    by = {}
    for p in sorted((out / 'parts').glob(f'{kind}_*.npz')):
        if '.tmp' in p.name:
            continue
        ideci = int(p.name.split('_')[1])
        z = np.load(p)
        by.setdefault(ideci, []).append({k: z[k] for k in z.files})
    res = {}
    for ideci, lst in by.items():
        lst.sort(key=lambda a: a['frame'][0])
        cat = {k: np.concatenate([a[k] for a in lst]) for k in lst[0]}
        fr = cat['frame']
        if not np.array_equal(fr, np.arange(fr[0], fr[0] + len(fr))) or fr[0] != 0:
            raise ValueError(f'frame coverage not contiguous from 0 for {kind} {ideci}')
        res[ideci] = cat
    return res


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def se(x):
    x = np.asarray(x, float)
    return float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else float('nan')


def boot_ratio(num, den, rng, b=N_BOOT):
    n = len(num)
    if n < 2:
        return (float('nan'), float('nan'))
    idx = rng.integers(0, n, size=(b, n))
    r = num[idx].mean(1) / den[idx].mean(1)
    return (float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5)))


def src_stats(c, s, rng, with_ci):
    v, r, zr, zi, vrep = (c[f'{s}_{k}'] for k in SRC_FIELDS)
    resid = PD - (v + r + 2 * zr)
    ratio = float(v.mean() / vrep.mean()) if vrep.mean() > 0 else float('nan')
    lo, hi = boot_ratio(v, vrep, rng) if with_ci and vrep.mean() > 0 else (float('nan'), float('nan'))
    return dict(v=float(v.mean()), v_se=se(v), r=float(r.mean()), z_re=float(zr.mean()), z_im=float(zi.mean()), z_re_se=se(zr),
                v_rep=float(vrep.mean()), v_rep_se=se(vrep), resid_mean=float(resid.mean()), resid_maxabs_frame=float(np.max(np.abs(resid))),
                calib=ratio, calib_lo=lo, calib_hi=hi, v_norm=float(v.mean() / PD), v_rep_norm=float(vrep.mean() / PD),
                r_norm=float(r.mean() / PD), z_re_norm=float(zr.mean() / PD), resid_norm=float(resid.mean() / PD),
                two_re_z_over_vrep=float(2 * zr.mean() / vrep.mean()) if vrep.mean() > 0 else float('nan'))


def split_stats(c, s, mask):
    n = int(mask.sum())
    if n == 0:
        return dict(n=0)
    v, r, zr, zi, vrep = (c[f'{s}_{k}'][mask] for k in SRC_FIELDS)
    return dict(n=n, v=float(v.mean()), v_se=se(v), r=float(r.mean()), z_re=float(zr.mean()), z_im=float(zi.mean()),
                v_rep=float(vrep.mean()), v_rep_se=se(vrep), v_norm=float(v.mean() / PD), v_rep_norm=float(vrep.mean() / PD),
                r_norm=float(r.mean() / PD), z_re_norm=float(zr.mean() / PD),
                calib=float(v.mean() / vrep.mean()) if vrep.mean() > 0 else float('nan'))


def gh_uncoded(q_lin):
    """Analytic exact-LLR QPSK/AWGN: L ~ N(2q, 4q) given b=0 (clipped +-20): M = 1 - E tanh^2(L/2) (= v/pd), J = 1 - E log2(1+e^-L)."""
    x, w = np.polynomial.hermite_e.hermegauss(200)
    L = np.clip(2 * q_lin + 2 * np.sqrt(q_lin) * x, -20., 20.)
    w = w / w.sum()
    return float(1 - np.sum(w * np.tanh(L / 2) ** 2)), float(1 - np.sum(w * np.logaddexp(0., -L) / np.log(2.)))


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def crossing(qdb, p, target, mode):
    f = np.asarray(p, float) if mode == 'linear' else logit(np.asarray(p, float))
    t = target if mode == 'linear' else float(logit(target))
    for i in range(len(qdb) - 1):
        a, b = f[i], f[i + 1]
        if a > t >= b:
            return float(qdb[i] + (a - t) / (a - b) * (qdb[i + 1] - qdb[i]))
    return float('nan')


def crossing_ci(qdb, k, n, target, mode, rng, b=2000):
    vals = []
    for _ in range(b):
        ps = rng.binomial(n, k / n) / n
        vals.append(crossing(qdb, ps, target, mode))
    vals = np.asarray(vals)
    ok = vals[np.isfinite(vals)]
    if len(ok) < 10:
        return (float('nan'), float('nan'), int(len(vals) - len(ok)))
    return (float(np.percentile(ok, 2.5)), float(np.percentile(ok, 97.5)), int(len(vals) - len(ok)))


# ----------------------------------------------------------------------------- select
def cmd_select(args):
    cod = load_parts(args.out, 'coded')
    qd = np.array(sorted(cod)) / 10.
    fer = np.array([np.mean(cod[k]['info_err'] > 0) for k in sorted(cod)])
    qstar = crossing(qd, fer, 0.5, 'linear')
    if not np.isfinite(qstar):
        raise ValueError('no FER=.5 crossing in stage A')
    order = np.argsort(np.abs(qd - qstar), kind='stable')[:args.n_extra]
    sel = sorted(int(round(qd[i] * 10)) for i in order)
    (args.out / 'stageB_selection.json').write_text(json.dumps(dict(
        _argv=sys.argv, rule='n_extra grid points nearest the stage-A linear-interpolated FER=.5 crossing',
        crossing_A_q_db=qstar, selected_deci_db=sel, selected_q_db=[s / 10 for s in sel],
        stageA_fer={f'{q:.1f}': float(f) for q, f in zip(qd, fer)}), indent=1))
    print('FER=.5 crossing (stage A)', qstar, 'selected dB', [s / 10 for s in sel])


# ----------------------------------------------------------------------------- merge
def cmd_merge(args):
    rng = np.random.default_rng(BOOT_SEED)
    cod, unc = load_parts(args.out, 'coded'), load_parts(args.out, 'uncoded')
    metas = [json.loads(p.read_text()) for p in sorted((args.out / 'parts').glob('meta_*.json'))]
    ck = json.loads((args.out / 'checks.json').read_text()) if (args.out / 'checks.json').exists() else None
    sel = json.loads((args.out / 'stageB_selection.json').read_text()) if (args.out / 'stageB_selection.json').exists() else None
    coded = []
    for ideci in sorted(cod):
        c = cod[ideci]
        n = len(c['frame'])
        failI = c['info_err'] > 0
        failC = c['coded_err'] > 0
        und = (c['decode_ok'] == 1) & failC
        rec = dict(q_db=ideci / 10., n_frames=n, FER=float(failI.mean()), FER_se=float(np.sqrt(failI.mean() * (1 - failI.mean()) / n)),
                   FER_wilson=wilson(int(failI.sum()), n), n_info_fail=int(failI.sum()),
                   FER_coded=float(failC.mean()), n_coded_fail=int(failC.sum()), n_coded_fail_info_ok=int((failC & ~failI).sum()),
                   BER_info=float(np.mean(c['info_err'] / K_INFO)), BER_coded=float(np.mean(c['coded_err'] / 2048.)),
                   iters_mean=float(c['iters'].mean()), iters_se=se(c['iters']), frac_maxiter=float(np.mean(c['iters'] >= 50)),
                   syndrome0_frac=float(c['decode_ok'].mean()), n_undetected=int(und.sum()),
                   n_correct=int((~failC).sum()), n_wrong=int(failC.sum()),
                   logloss_chan=float(c['ll_chan'].mean()), logloss_chan_se=se(c['ll_chan']),
                   logloss_app=float(c['ll_app'].mean()), logloss_app_se=se(c['ll_app']),
                   J_chan=float(1 - c['ll_chan'].mean()))
        for s in SRC:
            rec[s] = src_stats(c, s, rng, True)
            rec[s + '_correct'] = split_stats(c, s, ~failC)
            rec[s + '_wrong'] = split_stats(c, s, failC)
        coded.append(rec)
    unc_rec = []
    for ideci in sorted(unc):
        c = unc[ideci]
        q_lin = 10 ** (ideci / 100.)
        M_an, J_an = gh_uncoded(q_lin)
        s = src_stats(c, 'chan', rng, True)
        unc_rec.append(dict(q_db=ideci / 10., n_frames=len(c['frame']), chan=s, logloss_chan=float(c['ll_chan'].mean()),
                            logloss_chan_se=se(c['ll_chan']), J_unc=float(1 - c['ll_chan'].mean()), M_unc=s['v_norm'],
                            M_unc_analytic=M_an, J_unc_analytic=J_an))
    # crossings
    cross = {}
    if coded:
        qd = np.array([r['q_db'] for r in coded])
        kk = np.array([r['n_info_fail'] for r in coded])
        nn = np.array([r['n_frames'] for r in coded])
        fer = kk / nn
        for tgt in (0.5, 0.1):
            for mode in ('linear', 'logit'):
                est = crossing(qd, fer, tgt, mode)
                lo, hi, nfail = crossing_ci(qd, kk, nn, tgt, mode, rng)
                cross[f'FER{tgt}_{mode}'] = dict(q_db=est, ci95=[lo, hi], boot_nan=nfail,
                                                 note='per-point independent binomial bootstrap (ignores CRN correlation -> conservative)')
    columns = dict(
        coded=dict(q_db=[r['q_db'] for r in coded], FER=[r['FER'] for r in coded], BER_info=[r['BER_info'] for r in coded],
                   iters=[r['iters_mean'] for r in coded], M_chan=[r['chan']['v_norm'] for r in coded],
                   M_app=[r['app']['v_norm'] for r in coded], M_chk=[r['chk']['v_norm'] for r in coded],
                   v_wrong=[r['app_wrong'].get('v_norm') for r in coded], v_correct=[r['app_correct'].get('v_norm') for r in coded],
                   v_chk_wrong=[r['chk_wrong'].get('v_norm') for r in coded], v_chk_correct=[r['chk_correct'].get('v_norm') for r in coded],
                   n_wrong=[r['n_wrong'] for r in coded], n_correct=[r['n_correct'] for r in coded],
                   J_chan=[r['J_chan'] for r in coded]),
        uncoded=dict(q_db=[r['q_db'] for r in unc_rec], M_unc=[r['M_unc'] for r in unc_rec], J_unc=[r['J_unc'] for r in unc_rec],
                     M_unc_analytic=[r['M_unc_analytic'] for r in unc_rec], J_unc_analytic=[r['J_unc_analytic'] for r in unc_rec]),
        note='M_* = v / pd (normalised soft-symbol MSE); v_wrong/v_correct = M_app on frames with coded_err>0 / ==0 (None if no such frames)')
    out = dict(_argv=sys.argv, _config=metas[0]['_config'] if metas else None, _stage_argv=[m['_argv'] for m in metas],
               seeds=dict(entropy_hex=ENTROPY_HEX, domain=DOMAIN, stream_algorithm=STREAM_ALGORITHM, boot_seed=BOOT_SEED),
               code_g_sha256=metas[0]['code_g_sha256'] if metas else None, sources=metas[0]['sources'] if metas else None,
               checks=ck, stageB_selection=sel, crossings=cross, coded=coded, uncoded=unc_rec, columns=columns,
               shard_seconds=dict(sum=sum(m['seconds'] for m in metas), max=max(m['seconds'] for m in metas) if metas else 0))
    # per-frame npz (stays on the server: size)
    flat = {}
    for kind, d in (('coded', cod), ('uncoded', unc)):
        for ideci, c in d.items():
            for k, v in c.items():
                flat[f'{kind}_{ideci:+04d}_{k}'] = v
    np.savez_compressed(args.out / 'frames.npz', **flat)
    out['frames_npz'] = dict(path=str((args.out / 'frames.npz').resolve()), md5=hashlib.md5((args.out / 'frames.npz').read_bytes()).hexdigest())
    (args.out / 't1_transfer.json').write_text(json.dumps(clean(out), indent=1, allow_nan=False))
    write_md(args.out / 'T1_TRANSFER.md', out)
    print('merged', len(coded), 'coded points,', len(unc_rec), 'uncoded points')


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return 'nan'
    return f'{x:.{nd}f}'


def write_md(path, o):
    L = ['# C1 T1: fixed-code transfer curves on AWGN QPSK (no SP)', '',
         f'code G sha256 {o["code_g_sha256"]}; pd = {PD}; maxiter 50; clip +-20; seeds: {o["seeds"]["entropy_hex"][:16]}.. domain 0x{DOMAIN:08X}.',
         'v = E|d-m|^2, r = E|m|^2, z = E[(d-m) conj(m)], v_rep = E[max(pd-|m|^2,0)], calib = v / v_rep; `_n` = divided by pd.',
         'Identity: pd = v + r + 2 Re z holds algebraically for ANY m, so the closure residual is ~1e-16 by construction; the informative',
         'quantity is z: v_rep = pd - r, hence calib = v/v_rep = 1 - 2 Re z / v_rep (calibrated iff z = 0).', '']
    if o['checks']:
        L += ['## Convention / layout checks', '```', json.dumps({k: v for k, v in o['checks'].items() if k != 'sources'}, indent=1, default=str), '```', '']
    L += ['## Crossings (data Es/N0, dB)', '', '| target | interp | q_dB | 95% CI | boot NaN |', '|---|---|---|---|---|']
    for k, v in o['crossings'].items():
        t, m = k.replace('FER', '').split('_')
        L.append(f'| FER={t} | {m} | {fmt(v["q_db"], 3)} | [{fmt(v["ci95"][0], 3)}, {fmt(v["ci95"][1], 3)}] | {v["boot_nan"]} |')
    L += ['', '## Coded curves', '',
          '| q_dB | n | FER | FER se | BER_info | iters | undet | M_chan | M_app | M_chk | calib_app | calib_app 95% | calib_chk | calib_chk 95% | calib_chan | 2Rez/vrep app | resid_app | ll_chan | ll_app |',
          '|' + '---|' * 19]
    for r in o['coded']:
        a, k, c = r['app'], r['chk'], r['chan']
        L.append(f'| {r["q_db"]:.1f} | {r["n_frames"]} | {fmt(r["FER"])} | {fmt(r["FER_se"])} | {r["BER_info"]:.2e} | {fmt(r["iters_mean"], 2)} | {r["n_undetected"]} '
                 f'| {fmt(c["v_norm"])} | {fmt(a["v_norm"])} | {fmt(k["v_norm"])} | {fmt(a["calib"])} | [{fmt(a["calib_lo"])}, {fmt(a["calib_hi"])}] '
                 f'| {fmt(k["calib"])} | [{fmt(k["calib_lo"])}, {fmt(k["calib_hi"])}] | {fmt(c["calib"])} | {fmt(a["two_re_z_over_vrep"])} | {a["resid_maxabs_frame"]:.1e} '
                 f'| {fmt(r["logloss_chan"])} | {fmt(r["logloss_app"])} |')
    L += ['', '## Split by decoded outcome (correct: coded_err == 0), normalised by pd', '',
          '| q_dB | n_ok | n_bad | app v_n ok | app v_n bad | app calib ok | app calib bad | chk v_n ok | chk v_n bad | chk vrep_n ok | chk vrep_n bad | chk r_n ok | chk r_n bad | chk z_n ok | chk z_n bad | chk calib ok | chk calib bad |',
          '|' + '---|' * 17]
    for r in o['coded']:
        g = lambda s, m, key: fmt(r[s + m].get(key), 4)
        L.append(f'| {r["q_db"]:.1f} | {r["n_correct"]} | {r["n_wrong"]} | ' + ' | '.join([
            g('app', '_correct', 'v_norm'), g('app', '_wrong', 'v_norm'), g('app', '_correct', 'calib'), g('app', '_wrong', 'calib'),
            g('chk', '_correct', 'v_norm'), g('chk', '_wrong', 'v_norm'), g('chk', '_correct', 'v_rep_norm'), g('chk', '_wrong', 'v_rep_norm'),
            g('chk', '_correct', 'r_norm'), g('chk', '_wrong', 'r_norm'), g('chk', '_correct', 'z_re_norm'), g('chk', '_wrong', 'z_re_norm'),
            g('chk', '_correct', 'calib'), g('chk', '_wrong', 'calib')]) + ' |')
    L += ['', '## Uncoded (exact channel LLR, no decoding)', '',
          '| q_dB | n | M_unc (MC) | se | M analytic | J_unc (MC) | J analytic | calib | 2Rez/vrep |', '|' + '---|' * 9]
    for r in o['uncoded']:
        c = r['chan']
        L.append(f'| {r["q_db"]:.1f} | {r["n_frames"]} | {fmt(r["M_unc"], 5)} | {c["v_se"] / PD:.1e} | {fmt(r["M_unc_analytic"], 5)} '
                 f'| {fmt(r["J_unc"], 5)} | {fmt(r["J_unc_analytic"], 5)} | {fmt(c["calib"])} | {fmt(c["two_re_z_over_vrep"], 5)} |')
    L += ['', f'per-frame arrays: {o["frames_npz"]["path"]} md5 {o["frames_npz"]["md5"]} (server only)', '']
    path.write_text('\n'.join(L))


# ----------------------------------------------------------------------------- checks
def cmd_checks(args):
    from scipy.special import logsumexp
    ctx = bind(args)
    code = ctx.code
    out = dict(code_g_sha256=ctx.header['code_g_sha256'], k=int(code['k']), n=int(code['H'].shape[1]), m=int(code['H'].shape[0]),
               rate=float(code['k'] / code['H'].shape[1]))
    assert out['code_g_sha256'].startswith('bfd4247263adedc9') and out['n'] == 2048 and out['k'] == 1024
    # 1. encoder -> syndrome zero
    H = np.asarray(code['H']).astype(np.int64)
    synd = 0
    for f in range(20):
        info = np.random.default_rng(f).integers(0, 2, size=code['k']).astype(np.uint8)
        synd += int(((H @ ctx.encode(code, info).astype(np.int64)) % 2).sum())
    out['encode_syndrome_weight_20_words'] = synd
    assert synd == 0
    # 2. layout: very high SNR -> moments(clip(channel LLR)) == transmitted symbol (power pd)
    errs, d_err = [], []
    for f in range(5):
        info, coded, d, llr = frame_data(ctx, f, 10 ** 4.0)  # q = 40 dB
        mu, vv, _ = ctx.moments(llr, PD)
        errs.append(float(np.max(np.abs(mu - d))))
        d_err.append(float(np.max(np.abs(np.abs(d) ** 2 - PD))))
        assert np.array_equal((llr[:1024] < 0).astype(np.uint8), coded[:1024]) and np.array_equal((llr[1024:] < 0).astype(np.uint8), coded[1024:])
    out['layout_q40dB_max_abs_mu_minus_d'] = max(errs)
    out['layout_expected_tanh10_bound'] = float(np.sqrt(PD) * (1 - np.tanh(10.)) * 2)
    out['symbol_power_max_abs_dev'] = max(d_err)
    assert out['layout_q40dB_max_abs_mu_minus_d'] < 1e-6
    # 3. demap_llr vs closed form vs brute-force QPSK marginal (messages.marginal) at q = 2 dB (unclipped)
    from messages import marginal, alphabet
    q = 10 ** 0.2
    info, coded, d, _ = frame_data(ctx, 0, q)
    noi = np.random.default_rng(np.random.SeedSequence(ENTROPY_WORDS + [DOMAIN, 0, 3]))
    sigma2 = PD / q
    y = d + np.sqrt(sigma2) * (noi.standard_normal(len(d)) + 1j * noi.standard_normal(len(d))) / np.sqrt(2.)
    l_demap = ctx.demap_llr(y, sigma2, np.sqrt(PD / 2.), clip=1e9)
    a = np.sqrt(PD / 2.)
    l_closed = np.concatenate([4 * a * y.real / sigma2, 4 * a * y.imag / sigma2])
    alph, _ = alphabet(PD)
    lik = -np.abs(y[:, None] - alph[None, :]) ** 2 / sigma2
    l_brute = marginal(lik, np.zeros(2 * len(y)), PD)[1]
    out['demap_vs_closed_form_max_abs'] = float(np.max(np.abs(l_demap - l_closed)))
    out['demap_vs_bruteforce_marginal_max_abs'] = float(np.max(np.abs(l_demap - l_brute)))
    assert out['demap_vs_bruteforce_marginal_max_abs'] < 1e-8
    # 4. decoder at q = 40 dB: zero errors in 1 iteration, decoded == (raw_app < 0) == coded
    info, coded, d, llr = frame_data(ctx, 1, 10 ** 4.0)
    dec = ctx.decoder_messages(code, llr, maxiter=50)
    out['decoder_q40dB'] = dict(iterations=int(dec['iterations']), coded_errors=int(np.count_nonzero(dec['decoded'] != coded)),
                                app_sign_matches_decoded=bool(np.array_equal((dec['raw_app'] < 0).astype(np.uint8), dec['decoded'])))
    assert out['decoder_q40dB']['coded_errors'] == 0
    # 5. moments check: pd - |mu|^2 == vrep and identity pd = v + r + 2 Re z on one noisy frame
    info, coded, d, llr = frame_data(ctx, 2, 10 ** 0.2)
    v, r, zr, zi, vrep = soft_stats(ctx, llr, d)
    out['identity_residual_q2dB_chan'] = float(PD - (v + r + 2 * zr))
    out['vrep_minus_(pd_minus_r)_q2dB_chan'] = float(vrep - (PD - r))
    out['moments_module'] = ctx.sources['messages_path']
    out['receiver_module'] = ctx.sources['receiver_path']
    out['sources'] = ctx.sources
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'checks.json').write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != 'sources'}, indent=1, default=str))


def main(argv=None):
    args = parse_args(argv)
    args.out = args.out.resolve()
    {'checks': cmd_checks, 'run': cmd_run, 'select': cmd_select, 'merge': cmd_merge}[args.mode](args)


if __name__ == '__main__':
    main()
