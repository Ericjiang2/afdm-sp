#!/usr/bin/env python
"""P2a part 2 driver: Zheng et al. 2025 Algorithm 1 ported to the P1 channels (protocol.md I4 + A2).

Frames: P1's frames (same gen_fixed scenario flags, same P1 entropy / domain / streams), so channel, noise and the n = 2048 LDPC codeword are identical to P1.
The only change is the pilot: a single DAFT-domain impulse at index 0 with energy rho N (total energy N, data sqrt(1 - rho) QPSK on all N symbols), propagated through
the same physical CPP operator (supplement_pilots.propagate_cpp) as P1.  One JSONL row per (scenario, rho, snr, frame).

Variants (zport_rx.ZPort, P = 8 known, i_m 20, gamma .1, epsilon .2): Zf01 / Zf09 = Z-faithful (integer grid, 515 atoms), Za01 / Za09 = Z-adapted (Doppler step .25 over [-3, 3],
2575 atoms, MP graph truncated to +-4 bins), Zo01 / Zo09 = Z-OMP (our adaptation, protocol A3: Z-adapted with successive atom selection + joint LS instead of top-P),
with delta_new .1 / .9 (eq. 29); Zt = Z-turbo (report-only, our modification: Za09 + one more MP round with the LDPC extrinsic LLRs as
symbol priors).  After MP the final symbol posteriors become bit LLRs (exact log-sum, clipped to +-20) and the P1 decoder (decoder_messages, maxiter 50) decodes once.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p1_driver as P  # noqa: E402
from zport_rx import ZPort  # noqa: E402

VARIANTS = ('Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09', 'Zt')
SPEC = dict(Zf01=('int', .1, 'top'), Zf09=('int', .9, 'top'), Za01=('frac', .1, 'top'), Za09=('frac', .9, 'top'),
            Zo01=('frac', .1, 'omp'), Zo09=('frac', .9, 'omp'))
DEFAULT_RHO = '0.3,0.5'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
RECEIVER_CONFIG = dict(
    pilot='single DAFT impulse at index 0, energy rho N, superimposed on sqrt(1 - rho) QPSK data (N = 1024, n = 2048 LDPC codeword of P1)',
    Zf='integer grid delays 0..102 x Doppler -2..2 (515 atoms), P = 8 known, top-P of the matched filter (= eq. 20 on the orthogonal grid), MP on the exact sparse H_eff',
    Zo='Z-OMP (our adaptation, A3): the Z-adapted grid / graph with successive selection (largest correlation with the pilot-domain residual, joint LS on the atoms selected so far, residual update) until P = 8',
    Za='Doppler step .25 over [-3, 3] x delays 0..102 (2575 atoms), top-P of the matched filter + joint LS on the selected atoms, MP on H_eff with each column truncated to +-4 bins; '
       'IC and pilot cancellation with the exact untruncated operator',
    delta='eq. (29) p = (1 - delta_new) p_old + delta_new p_tilde with delta_new in {.1, .9} (A2: both readings)',
    Zt='report-only: Za09 round 1, LDPC extrinsic (raw_check_extrinsic) as symbol prior, MP round 2 with the prior, decoder input = posterior LLR minus the prior LLR',
    decode='posterior -> bit LLR (exact log-sum over QPSK, clip 20) -> decoder_messages maxiter 50 -> extract_info')


def impulse_frame(ctx, raw, rho):
    """Port frame: x = A e_0 + data (DAFT domain), noiseless output through the physical CPP operator of the P1 frame."""
    s = ctx.system
    n = int(s.N_total)
    x = np.array(raw['data'], complex)
    x[0] += np.sqrt(rho * n)
    p = raw['params']
    wave = ctx.transform(x, s.c1, s.c2, inverse=True)
    yn = ctx.transform(ctx.propagate_cpp(wave, s.c1, p['l_i'], p['k_real'], p['g_i'], prefix_length=int(s.l_max_cap)), s.c1, s.c2)
    return x, yn


def decode(ctx, llr):
    from afdm_sp_joint_unrolled.supplement_messages import decoder_messages
    return decoder_messages(ctx.code, llr, maxiter=50)


def score(ctx, dec, raw):
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info
    decoded = np.asarray(dec['decoded'], np.uint8)
    info_errors = int(np.count_nonzero(extract_info(ctx.code, decoded) != raw['info']))
    return dict(info_errors=info_errors, fer=int(info_errors > 0), coded_errors=int(np.count_nonzero(decoded != raw['coded'])),
                decode_ok=bool(dec['decode_ok']), ldpc_iterations=int(dec['iterations']))


def variant_record(ctx, raw, res, dec, seconds, true_l):
    rec = score(ctx, dec, raw)
    rec.update(mp_iterations=int(res['iterations']), zeta_star=float(res['zeta_star']), seconds=float(seconds), edges=int(res['edges']),
               trunc_est=float(res['trunc_est']), n_true_delays_hit=int(len(set(int(l) for l in res['ls']) & set(int(l) for l in true_l))),
               n_distinct_selected_delays=int(len(set(int(l) for l in res['ls']))))
    return rec


def run_cell(ctx, zp, raw, y, rho, sigma2, variants):
    out, cache = {}, {}
    true_l = raw['params']['l_i']
    for name in variants:
        if name == 'Zt':
            continue
        grid, delta, select = SPEC[name]
        zp.delta = delta
        t0 = time.perf_counter()
        res = zp.run(y, rho, sigma2, grid, select=select)
        llr = ZPort.llr_from_posterior(res['p_j'])
        dec = decode(ctx, llr)
        sec = time.perf_counter() - t0
        out[name] = variant_record(ctx, raw, res, dec, sec, true_l)
        cache[name] = (res, dec, sec)
    if 'Zt' in variants:
        if 'Za09' in cache:
            res1, dec1, sec1 = cache['Za09']
        else:
            zp.delta = .9
            t0 = time.perf_counter()
            res1 = zp.run(y, rho, sigma2, 'frac')
            dec1 = decode(ctx, ZPort.llr_from_posterior(res1['p_j']))
            sec1 = time.perf_counter() - t0
        zp.delta = .9
        t0 = time.perf_counter()
        prior = ZPort.prior_from_llr(np.asarray(dec1['raw_check_extrinsic']))
        l_prior = ZPort.llr_from_posterior(prior)
        res2 = zp.run(y, rho, sigma2, 'frac', prior=prior)
        llr2 = np.clip(ZPort.llr_from_posterior(res2['p_j']) - l_prior, -20., 20.)
        dec2 = decode(ctx, llr2)
        sec2 = time.perf_counter() - t0
        rec = variant_record(ctx, raw, res2, dec2, sec1 + sec2, true_l)
        rec.update(round1_fer=score(ctx, dec1, raw)['fer'], round1_seconds=float(sec1), round2_seconds=float(sec2))
        out['Zt'] = rec
    return out


# ----------------------------------------------------------------------------- shard i/o
def cell_key(row):
    return (row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame'])


def load_done(path):
    path = Path(path)
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):
        path.write_bytes(data[:cut])
    return {cell_key(json.loads(x)) for x in data[:cut].decode().splitlines() if x.strip()}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--frames', type=int, default=1000)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--scenarios', default='U,G')
    p.add_argument('--rho-list', default=DEFAULT_RHO)
    p.add_argument('--snr-list', default=DEFAULT_SNR)
    p.add_argument('--variants', default=','.join(VARIANTS))
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--label', default='')
    return p.parse_args(argv)


def fingerprint(args, ctx, argv, zp):
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    config.update(ENTROPY_HEX=P.ENTROPY_HEX, DOMAIN=P.DOMAIN, stream_algorithm=P.STREAM_ALGORITHM,
                  scenario_flags={k: dict(fix_delay_cap=v.fix_delay_cap, fix_delay_grid=v.fix_delay_grid, doppler_law=v.doppler_law, fix_energy=v.fix_energy)
                                  for k, v in P.SCENARIOS.items()},
                  receiver=RECEIVER_CONFIG, zport=dict(N=zp.N, P=zp.P, gamma=zp.gamma, eps=zp.eps, i_max=zp.i_max, l_max=zp.l_max, alpha_max=zp.alpha_max,
                                                       band_frac=zp.band_frac, c1=zp.c1, c2=zp.c2),
                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, code_g_sha256=ctx.header['code_g_sha256'],
                  checkpoint_sha256=ctx.header.get('checkpoint_sha256'), environment=ctx.environment)
    return list(argv), config


def add_sources(ctx):
    for name in ('zport_rx', 'zport_driver'):
        path = HERE / f'{name}.py'
        ctx.source_md5[name] = P.md5_file(path)
        ctx.source_sha256[name] = P.sha256_file(path)
        ctx.source_paths[name] = str(path.relative_to(P.PROJECT))


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    scenarios = P.parse_list(args.scenarios, str)
    variants = P.parse_list(args.variants, str)
    if not set(variants) <= set(VARIANTS) or not set(scenarios) <= set(P.SCENARIOS):
        raise ValueError('unknown variant or scenario')
    rho_list = P.parse_list(args.rho_list, float)
    snr_cells = [int(round(float(x) * 100)) for x in P.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ctx = P.load_context()
    add_sources(ctx)
    zp = ZPort(ctx.system.c1, ctx.system.c2, N=int(ctx.system.N_total))
    _, config = fingerprint(args, ctx, argv, zp)
    jsonable = lambda v: json.loads(json.dumps(v, default=ctx.hd.to_jsonable))  # noqa: E731
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment', 'shard', 'out')}
    if cfg_path.exists():
        if json.loads(cfg_path.read_text()).get('_config_cmp') != jsonable(comparable):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        cfg_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable), indent=1, default=ctx.hd.to_jsonable, allow_nan=False) + '\n')
    seed_fn = P.make_seed_fn()
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    started = time.perf_counter()
    n_cells = 0
    with jsonl.open('a') as handle:
        for frame in frames:
            for scenario in scenarios:
                for rho in rho_list:
                    rho_pm = int(round(rho * 1000))
                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
                    if not todo:
                        continue
                    raw_base, diag_base = P.generate(ctx, scenario, rho, snr_cells[0] / 100, frame, seed_fn)
                    x, yn = impulse_frame(ctx, raw_base, rho)
                    truth = ctx.hd.truth_from_raw(raw_base, diag_base)
                    tf = P.truth_fields(ctx, truth, diag_base)
                    p = raw_base['params']
                    trunc_true = zp.truncated_fraction(p['l_i'], p['k_real'], p['g_i'], zp.band_frac)
                    for snr in todo:
                        sigma2 = 10 ** (-snr / 100 / 10)
                        y = yn + np.sqrt(sigma2) * raw_base['noise']
                        cell = run_cell(ctx, zp, raw_base, y, rho, sigma2, variants)
                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr), snr_db=snr / 100, frame=int(frame),
                                   label=args.label, trunc_true=trunc_true, variants=cell, **tf)
                        handle.write(json.dumps(row, sort_keys=True, allow_nan=False, default=ctx.hd.to_jsonable) + '\n')
                        handle.flush()
                        os.fsync(handle.fileno())
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] {scenario} rho={rho} snr={snr} frame={frame} '
                              + ' '.join(f"{k}:{v['info_errors']}" for k, v in cell.items()), flush=True)
    print(f'shard {args.shard}/{args.nshard} done: {n_cells} cells in {time.perf_counter() - started:.1f}s', flush=True)


if __name__ == '__main__':
    run_shard(parse_args(), sys.argv[1:])
