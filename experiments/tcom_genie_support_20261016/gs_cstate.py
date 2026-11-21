#!/usr/bin/env python
"""Amendment A1 (post hoc, protocol.md): GS+C = GS-set, then the CSTATE20 branch iff the GS-set final syndrome != 0.

--mode run   per (scenario, rho, snr, frame) one JSONL row: GS+C FER, decoded_sha256, triggered, final geometry, NMSE.
             A1-G1 is asserted on every row: the re-run GS-set decoded_sha256 equals the main-run row (--ref-rows).
--mode gate  A1-G2: the same continuation helper on production F0 state reproduces the P1 ledger B (frames given by --frames).
The branch is run_validation._branch (ctx.branch) exactly as in p1_driver.f0_family; nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_driver as gd  # noqa: E402
from gs_driver import crb, p1ctx  # noqa: E402

PROJECT = HERE.parents[1]
P1_ROWS = PROJECT / 'experiments' / 'tcom_reference_frame_20261015' / 'out' / 'p1'


def continue_cstate(ctx, obs, decoder, arrays):
    """B's rule: CSTATE20 branch from the given two-round state iff its final syndrome != 0."""
    syn = int(ctx.hd.syndrome_weight(ctx, decoder['decoded']))
    if syn == 0:
        return decoder, None, syn
    br = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
    return br['decoder'], br, syn


def gsc_row(ctx, obs, truth, n, ref_sha):
    delays = gd.genie_delays(truth, 'GS-set')
    log = []
    t0 = time.perf_counter()
    res = gd.run_gs(ctx, obs, ctx.arms.make_a1_refine(delays, log))
    gs_sha = gd.bits_sha(res.decoder['decoded'])
    assert gs_sha == ref_sha, 'A1-G1: re-run GS-set differs from the main run'
    final, br, syn = continue_cstate(ctx, obs, res.decoder, res.arrays)
    seconds = time.perf_counter() - t0
    a = res.arrays
    if br is None:
        d, nu, g = a['r1_delays'], a['r1_dopplers'], a['r1_gains']
    else:
        d = [p.delay for p in br['result'].paths]
        nu = [p.doppler for p in br['result'].paths]
        g = br['detector']['gains']
    truth_p = dict(delays=np.asarray(truth['l_i'], int), dopplers=np.asarray(truth['k_real'], float),
                   gains=np.asarray(truth['g_i'], complex))
    dec = final['decoded']
    return dict(fer=int(gd.score(ctx, dec, truth) > 0), info_errors=gd.score(ctx, dec, truth),
                syndrome=int(ctx.hd.syndrome_weight(ctx, dec)), decoded_sha256=gd.bits_sha(dec), triggered=br is not None,
                gs_syndrome=syn, gs_sha256=gs_sha, seconds=seconds, final_delays=[int(x) for x in d],
                true_set_kept=bool(set(int(x) for x in d) == set(int(x) for x in truth['l_i'])),
                nmse=crb.channel_nmse(gd.paths(d, nu, g), truth_p, n))


def load_ref(ref_dir, frames):
    want = set(frames)
    out = {}
    for p in sorted(Path(ref_dir).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if r['frame'] in want:
                    out[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r['arms']['GS-set']['decoded_sha256']
    return out


def run_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    ref = load_ref(args.ref_rows, frames)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    if not cfg_path.exists():
        own = {f: hashlib.md5((HERE / f).read_bytes()).hexdigest() for f in ('gs_cstate.py', 'gs_driver.py')}
        cfg = dict(vars(args), out=str(args.out), ref_rows=str(args.ref_rows), amendment='A1 post hoc GS+CSTATE20',
                   branch='run_validation._branch CSTATE20 iff GS-set final syndrome != 0',
                   source_md5={**ctx.source_md5, **own}, environment=ctx.environment)
        cfg_path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started = time.perf_counter()
    with jsonl.open('a') as handle:
        for frame in frames:
            for scenario in gd.SCENARIOS:
                for rho in (0.3, 0.5):
                    rho_pm = int(round(rho * 1000))
                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
                    if not todo:
                        continue
                    raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
                    for snr in todo:
                        raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                        k = (scenario, rho_pm, snr, frame)
                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr),
                                   snr_db=snr / 100, frame=int(frame), sigma2=float(raw['sigma2']),
                                   **{'GS+C': gsc_row(ctx, obs, truth, len(raw['y']), ref[k])})
                        handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
                        handle.flush()
                        os.fsync(handle.fileno())
                        r = row['GS+C']
                        print(f"[{time.perf_counter() - started:8.1f}s] {k} fer={r['fer']} trig={r['triggered']}", flush=True)
    print(f'shard {args.shard}/{args.nshard} done in {time.perf_counter() - started:.1f}s', flush=True)


def gate_mode(args):
    ctx = p1ctx.load()
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    want = set(frames)
    ledger = {}
    for p in sorted(Path(args.p1_rows).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if r['frame'] in want:
                    ledger[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r['arms']['B']['decoded_sha256']
    res = []
    for frame in frames:
        for scenario in gd.SCENARIOS:
            for rho in (0.3, 0.5):
                raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
                for snr in (450, 500, 550, 600, 650, 700, 750, 800):
                    _, obs, _ = gd.observe(ctx, raw_base, diag_base, rho, snr)
                    dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
                                                         ce_mode='soft', gain_mode='joint')
                    final, br, _ = continue_cstate(ctx, obs, dec0, arrays)
                    k = (scenario, int(round(rho * 1000)), snr, frame)
                    res.append(dict(key=list(k), triggered=br is not None,
                                    match=bool(k in ledger and gd.bits_sha(final['decoded']) == ledger[k])))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f'a1g2_shard{args.shard:03d}.json').write_text(json.dumps(res) + '\n')
    print(f"A1-G2 shard {args.shard}: {sum(x['match'] for x in res)}/{len(res)} match, {sum(x['triggered'] for x in res)} triggered")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('run', 'gate'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--ref-rows', type=Path, default=HERE / 'out' / 'main')
    p.add_argument('--p1-rows', type=Path, default=P1_ROWS)
    p.add_argument('--snr-list', default=gd.DEFAULT_SNR)
    p.add_argument('--frames', type=int, required=True)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    return p.parse_args(argv)


if __name__ == '__main__':
    a = parse_args()
    run_mode(a, sys.argv[1:]) if a.mode == 'run' else gate_mode(a)
