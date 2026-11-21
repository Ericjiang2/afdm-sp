#!/usr/bin/env python
"""CRB-reference driver (protocol.md sections 3-4, task 10-16-tcom-channel-crb).

Frames: P1 frames (same entropy/domain/generator, p1ctx).  Per (scenario, rho, snr, frame) one JSONL row with
  * the channel NMSE of F0-front, F0-pilot (r0 CE), F0-final (r1 detector gains; CE gains secondary) and B-final
    (CSTATE paths + detector gains when F0 fails; = F0-final otherwise),
  * the bounds MCRB, DA, PI (all frames) and GD (frames < --gd-frames), constrained (primary) and unconstrained,
  * F0/B FER and decoded_sha256 for the G6 match against the P1 ledger.
The receiver calls copy p1_driver.f0_family (same arguments, same order); nothing frozen is edited.
Run one process per shard, single thread (launch_crb.sh).
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
import scipy.linalg as sla

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crb  # noqa: E402
import p1ctx  # noqa: E402

SCENARIOS = ('U', 'G')
DEFAULT_RHO = '0.3,0.5'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'


def bits_sha(decoded):
    return hashlib.sha256(np.asarray(decoded, np.uint8).tobytes()).hexdigest()


def paths(delays, dopplers, gains):
    return dict(delays=[int(x) for x in np.asarray(delays)], dopplers=[float(x) for x in np.asarray(dopplers)],
                gains=np.asarray(gains, complex))


def run_receivers(ctx, obs):
    """F0 (TF_J20_R2) then the CSTATE20 branch iff F0's final syndrome != 0 -- as p1_driver.f0_family."""
    t0 = time.perf_counter()
    dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20, ce_mode='soft', gain_mode='joint')
    syn0 = ctx.hd.syndrome_weight(ctx, dec0['decoded'])
    triggered = syn0 != 0
    est = {'F0-pilot': paths(arrays['r0_delays'], arrays['r0_dopplers'], arrays['r0_ce_gains']),
           'F0-final': paths(arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains']),
           'F0-final-ce': paths(arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_ce_gains'])}
    final = dec0
    if triggered:
        br = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
        final = br['decoder']
        d = [p.delay for p in br['result'].paths]
        nu = [p.doppler for p in br['result'].paths]
        est['B-final'] = paths(d, nu, br['detector']['gains'])
        est['B-final-ce'] = paths(d, nu, br['result'].gains)
    else:
        est['B-final'], est['B-final-ce'] = est['F0-final'], est['F0-final-ce']
    seconds = time.perf_counter() - t0
    # implementation note I1 (report-only): unbiased pilot-only LS gains on F0's pilot-stage geometry
    l0, nu0 = np.asarray(arrays['r0_delays'], int), np.asarray(arrays['r0_dopplers'], float)
    a0 = ctx.Channel(len(obs['y']), ctx.system.c1, ctx.system.c2, l0, nu0, np.ones(len(l0))).regressors(obs['pilot'])
    est['F0-pilot-LS'] = paths(l0, nu0, np.linalg.lstsq(a0, obs['y'], rcond=None)[0])
    from receiver import pilot_front  # frozen baseline module; called after decoding, does not affect it
    s = pilot_front(obs, ctx.system, ctx.code)
    est['F0-front'] = paths(s['delays'], s['dopplers'], s['gains'])
    return dec0, final, bool(triggered), est, seconds


class FrameBounds:
    """SNR-independent pieces for one (scenario, rho, frame): B(x_p), B(x), K, U, ||H||^2, T and its derivatives."""

    def __init__(self, ctx, raw, truth, rho, offdiag):
        from physical import daft
        n = len(raw['y'])
        c1, c2 = ctx.system.c1, ctx.system.c2
        self.l = np.asarray(truth['l_i'], int)
        self.nu = np.asarray(truth['k_real'], float)
        self.g = np.asarray(truth['g_i'], complex)
        self.rho, self.n = float(rho), n
        ch = ctx.Channel(n, c1, c2, self.l, self.nu, np.ones(len(self.g)))
        regress = lambda u, d: ch.regressors(u, derivative=d)  # noqa: E731
        xp = np.asarray(raw['pilot'])
        self.b_p = crb.regressor_matrix(regress, xp, self.g)
        self.b_x = crb.regressor_matrix(regress, xp + np.asarray(raw['data']), self.g)
        self.b_pt = daft(self.b_p, c1, c2, True)
        self.K = crb.gram_K(self.l, self.nu, self.g, n)
        self.extra = crb.mcrb_offdiag_term(regress, self.g, offdiag, n)  # amendment A1: exact coded-data covariance
        self.frob = crb.frob2(self.l, self.nu, self.g, n)
        self.U = crb.constraint_basis(self.g)
        self.t_op = crb.time_operator(self.l, self.nu, self.g, n, c1)
        self.d_ops = crb.param_time_operators(self.l, self.nu, self.g, n, c1)
        self.truth = dict(delays=self.l, dopplers=self.nu, gains=self.g)

    def missed_energy(self, est_delays):
        miss = ~np.isin(self.l, np.asarray(est_delays, int))
        if not miss.any():
            return 0.
        return crb.frob2(self.l[miss], self.nu[miss], self.g[miss], self.n) / self.frob

    def at(self, sigma2, gd):
        out = {}
        out['mcrb'] = crb.bounds_pair(crb.fim_mcrb(self.b_p, self.K, self.rho, sigma2, self.extra), self.K, self.frob, self.U)
        out['da'] = crb.bounds_pair(crb.fim_da(self.b_x, sigma2), self.K, self.frob, self.U)
        t0 = time.perf_counter()
        cho = sla.cho_factor(crb.interference_cov(self.t_op, self.rho, sigma2), lower=True)
        j_pi = crb.fim_pi(self.b_pt, cho)
        out['pi'] = crb.bounds_pair(j_pi, self.K, self.frob, self.U)
        gd_seconds = None
        if gd:
            t1 = time.perf_counter()
            out['gd'] = crb.bounds_pair(j_pi + crb.fim_gd_cov(self.t_op, self.d_ops, cho, self.rho), self.K, self.frob, self.U)
            gd_seconds = time.perf_counter() - t1
        return out, gd_seconds, time.perf_counter() - t0


def score(ctx, decoded, truth):
    return int(np.count_nonzero(ctx.extract_info(ctx.code, np.asarray(decoded)) != truth['info']) > 0)


def parse_list(text, cast):
    return [cast(x) for x in str(text).split(',') if str(x).strip()]


def load_done(path):
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):
        path.write_bytes(data[:cut])
    return {(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
            for r in map(json.loads, data[:cut].decode().splitlines()) if r}


def run_shard(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rho_list = parse_list(args.rho_list, float)
    snr_cells = [int(round(float(x) * 100)) for x in parse_list(args.snr_list, str)]
    scenarios = parse_list(args.scenarios, str)
    config = dict(vars(args), out=str(args.out), entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN,
                  cond_limit=crb.COND_LIMIT, note_I1='F0-pilot-LS and missed-delay energy, report-only', amendment_A1='MCRB with the exact coded-data covariance from the generator matrix', receiver=p1ctx.p1_driver.RECEIVER_CONFIG['B'],
                  source_md5={**ctx.source_md5, **{f: hashlib.md5((HERE / f).read_bytes()).hexdigest()
                                                  for f in ('crb.py', 'crb_driver.py', 'p1ctx.py')}},
                  environment=ctx.environment)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    if not cfg_path.exists():
        cfg_path.write_text(json.dumps(dict(_argv=list(argv), _config=config), indent=1, default=str) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    G = np.asarray(ctx.code['G']).astype(np.uint8) % 2
    G = G.T if G.shape[0] != ctx.code['k'] else G
    offdiag = {rho: crb.coded_offdiag(G, 1024, rho) for rho in rho_list}
    started = time.perf_counter()
    with jsonl.open('a') as handle:
        for frame in frames:
            for scenario in scenarios:
                for rho in rho_list:
                    rho_pm = int(round(rho * 1000))
                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
                    if not todo:
                        continue
                    raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
                    tb = time.perf_counter()
                    fb = FrameBounds(ctx, raw_base, ctx.hd.truth_from_raw(raw_base, diag_base), rho, offdiag[rho])
                    setup_seconds = time.perf_counter() - tb
                    for snr_centi in todo:
                        raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
                        obs = ctx.hd.observe(raw, rho, snr_centi / 100)
                        truth = ctx.hd.truth_from_raw(raw, diag)
                        dec0, final, triggered, est, rx_seconds = run_receivers(ctx, obs)
                        tb = time.perf_counter()
                        bounds, gd_seconds, _ = fb.at(float(raw['sigma2']), frame < args.gd_frames)
                        nmse = {k: crb.channel_nmse(v, fb.truth, fb.n) for k, v in est.items()}
                        missed = {k: fb.missed_energy(v['delays']) for k, v in est.items()}  # I1, report-only
                        b_seconds = time.perf_counter() - tb + (setup_seconds if snr_centi == todo[0] else 0.)
                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr_centi),
                                   snr_db=snr_centi / 100, frame=int(frame), sigma2=float(raw['sigma2']),
                                   frob=fb.frob, n_paths=len(fb.g), distinct_delays=int(len(set(fb.l.tolist()))),
                                   F0=dict(fer=score(ctx, dec0['decoded'], truth), decoded_sha256=bits_sha(dec0['decoded'])),
                                   B=dict(fer=score(ctx, final['decoded'], truth), decoded_sha256=bits_sha(final['decoded']),
                                          triggered=triggered),
                                   nmse=nmse, missed_energy=missed, est_paths={k: len(v['gains']) for k, v in est.items()},
                                   bounds=bounds, seconds_receivers=rx_seconds, seconds_bounds=b_seconds,
                                   seconds_gd=gd_seconds)
                        handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
                        handle.flush()
                        os.fsync(handle.fileno())
                        print(f"[{time.perf_counter() - started:8.1f}s] {scenario} rho={rho} snr={snr_centi} frame={frame} "
                              f"F0:{row['F0']['fer']} B:{row['B']['fer']} nmseB={10 * np.log10(nmse['B-final']):.1f}dB "
                              f"mcrb={10 * np.log10(bounds['mcrb']['c']):.1f}dB", flush=True)
    print(f'shard {args.shard}/{args.nshard} done in {time.perf_counter() - started:.1f}s', flush=True)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scenarios', default=','.join(SCENARIOS))
    p.add_argument('--rho-list', default=DEFAULT_RHO)
    p.add_argument('--snr-list', default=DEFAULT_SNR)
    p.add_argument('--frames', type=int, required=True)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--gd-frames', type=int, default=100, help='GD bound only for frame ids below this (protocol E3)')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    return p.parse_args(argv)


if __name__ == '__main__':
    run_shard(parse_args(), sys.argv[1:])
