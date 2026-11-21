#!/usr/bin/env python
"""SBL-side detector clue, pilot 5 (predictions P11-P13 in research-assets/prediction-ledger.md).

The E-3 on-grid data-aided SBL pipeline is imported unchanged (tf_e3_sbl_20261017/e3_driver.process_key, variants L-diag and L-cov).  The only addition is a
tee on e3_driver.detect_decode: the E-3 detector (scalar_joint gain_mode fixed) runs exactly as before and feeds the pipeline, and the SAME channel (atoms, SBL
gains) and prior (round-1 check) are also fed to scalar_joint with gain_mode='joint' (iterations 20 and damping .3 unchanged) + the E-3 LDPC call.  Round 1
(prior None) is left to E-3.  So the SBL runs once per key and variant.

Modes:  gate    the tee-wrapped pipeline reproduces the saved E-3 L-diag / L-cov decisions (decoded sha, info_errors, fer, atoms, pairs) on saved rho .3 keys at 7 and 8 dB
        pilot5  the slice: P1 stream, rho .3, scenarios U and G, SNR 7.0 and 8.0 dB, frames 9100..9299 (one row per key; row = the E-3 row + row['joint'])
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from pathlib import Path
import sys
import time
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E3_DIR = EXPERIMENTS / 'tf_e3_sbl_20261017'
sys.path.insert(0, str(E3_DIR))
import e3_driver as e3d  # noqa: E402  (frozen E-3 driver, imported read-only; also sets up the frozen math modules and the P1 context)

gd, sbl, p1ctx = e3d.gd, e3d.sbl, e3d.p1ctx

VARIANTS = ('L-diag', 'L-cov')
FRAMES = (9100, 9300)                                  # P1-stream free (frame_audit.py, 2026-10-19)
GRID = {'U_300': [7.0, 8.0], 'G_300': [7.0, 8.0], 'U_500': [], 'G_500': []}   # E-3 cell convention; rho .5 cells empty = not run
E3_ROWS = E3_DIR / 'out' / 'main'
GATE_SNR, GATE_PER_BUCKET = (700, 800), 6              # gate: saved rho .3 keys at 7 and 8 dB, <= 6 per (scenario, SNR) = 24 keys


# ----------------------------------------------------------------------------- the tee and one key
def tee_detector(orig, captured):
    """E-3's detect_decode unchanged, plus (round 2 only) the joint-gain detector on the same channel and prior; its LDPC output is appended to ``captured``."""
    def detect_decode(ctx, obs, channel, prior):
        out = orig(ctx, obs, channel, prior)
        if prior is not None:
            try:
                det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - ctx.system.rho, prior=prior, iterations=20, damping=.3,
                                              gain_mode='joint')
                captured.append(ctx.native.decoder_messages(ctx.code, np.clip(det['extrinsic'], -20, 20), maxiter=50))
            except (FloatingPointError, np.linalg.LinAlgError) as exc:   # recorded as a failed detector, counted in the report
                captured.append(dict(error=repr(exc)))
        return out
    return detect_decode


def process_key(ctx, cache, grid, obs, data_af, truth, meta):
    captured = []
    with mock.patch.object(e3d, 'detect_decode', tee_detector(e3d.detect_decode, captured)):
        row = e3d.process_key(ctx, cache, grid, obs, data_af, truth, meta, VARIANTS)
    if len(captured) != len(VARIANTS):
        raise AssertionError(f'expected {len(VARIANTS)} round-2 detector calls, got {len(captured)}')
    row['joint'] = {}
    for name, dec in zip(VARIANTS, captured):
        if 'error' in dec:
            row['joint'][name] = dict(status='error', error=dec['error'])
            continue
        err = gd.score(ctx, dec['decoded'], truth)
        row['joint'][name] = dict(status='ok', info_errors=int(err), fer=int(err > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, dec['decoded'])),
                                  decoded_sha256=gd.bits_sha(dec['decoded']), ldpc_iters=int(dec['iterations']))
    return row


def write_config(out, shard, argv, args, ctx, extra=None):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    own = {n: e3d.e3_lib.md5_file(HERE / n) for n in ('sj_driver.py', 'sj_agg.py', 'launch_sj.sh') if (HERE / n).exists()}
    cfg = dict(vars(args), out=str(args.out), variants=VARIANTS, grid_by_cell=GRID, frames_allowed=FRAMES, hyper=sbl.HYPER,
               family_P1=dict(entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN),
               receiver='E-3 e3_driver.process_key (unchanged) with detect_decode teed: fixed (E-3) and joint (same channel/prior, gain_mode joint, iterations 20, damping .3)',
               frozen_md5_check=e3d.check_frozen_md5(ctx), e3_own_md5=e3d.own_md5(), own_md5=own, source_md5=ctx.source_md5, environment=ctx.environment, **(extra or {}))
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- pilot
def pilot_mode(args, argv):
    lo, hi = FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'frames must lie in [{lo}, {hi})')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    cache, grid = e3d.PilotCache(), sbl.full_grid(int(ctx.system.l_max_cap))
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started, n_rows = time.perf_counter(), 0
    with jsonl.open('a') as handle:
        for frame in list(range(f_lo, f_hi))[args.shard::args.nshard]:
            for meta, obs, data_af, truth in e3d.cells_of_frame(ctx, frame, GRID, None):
                if e3d.key_of(meta) in done:
                    continue
                row = process_key(ctx, cache, grid, obs, data_af, truth, meta)
                e3d.write_row(handle, row)
                n_rows += 1
                print(f"[{time.perf_counter() - started:8.1f}s] {e3d.key_of(meta)} " + ' '.join(
                    f"{v}: fixed={row['variants'][v]['info_errors']} joint={row['joint'][v].get('info_errors', 'ERR')} atoms={row['variants'][v]['n_atoms']} pair={row['variants'][v]['n_pair']}"
                    for v in VARIANTS), flush=True)
    print(f'pilot5 shard {args.shard}/{args.nshard} done: {n_rows} keys in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- gate
def saved_units(rows_dir):
    """Saved E-3 main keys, rho .3, SNR 7 and 8 dB: first-seen in (frame, scenario, SNR) order, <= GATE_PER_BUCKET per (scenario, SNR)."""
    rows = {}
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl.gz'))):
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if r.get('status') != 'error' and r['rho_permille'] == 300 and r['snr_centi_db'] in GATE_SNR:
                    rows[e3d.key_of(r)] = r
    buckets, units = {}, []
    for k in sorted(rows, key=lambda k: (k[3], k[0], k[2])):
        b = (k[0], k[2])
        if buckets.get(b, 0) < GATE_PER_BUCKET:
            buckets[b] = buckets.get(b, 0) + 1
            units.append((k, rows[k]))
    return units


def gate_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    cache, grid = e3d.PilotCache(), sbl.full_grid(int(ctx.system.l_max_cap))
    recs, started = [], time.perf_counter()
    for k, saved in saved_units(args.e3_rows)[args.shard::args.nshard]:
        sc, rho_pm, snr, frame = k
        raw_base, diag_base = p1ctx.base(ctx, sc, rho_pm / 1000, frame)
        meta, obs, data_af, truth = e3d.observe_key(ctx, raw_base, diag_base, sc, rho_pm, snr, frame)
        row = process_key(ctx, cache, grid, obs, data_af, truth, meta)
        rec = dict(key=list(k))
        for v in VARIANTS:
            mine, old = row['variants'][v], saved['variants'][v]
            rec[v] = {f: mine[f] == old[f] for f in ('decoded_sha256', 'info_errors', 'fer', 'n_atoms', 'n_pair', 'atoms')}
        recs.append(rec)
        print(f'[{time.perf_counter() - started:8.1f}s] {rec}', flush=True)
    g = dict(units=len(recs), **{f'{v}_{f}_match': sum(r[v][f] for r in recs) for v in VARIANTS for f in recs[0][VARIANTS[0]]})
    g['pass_'] = bool(g['units'] >= 20 and all(x == g['units'] for kk, x in g.items() if kk.endswith('_match')))
    (out / f'gate_shard{args.shard:03d}.json').write_text(json.dumps(dict(gate=g, records=recs), indent=1) + '\n')
    print(json.dumps(g, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('gate', 'pilot5'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--e3-rows', type=Path, default=E3_ROWS)
    p.add_argument('--frame-offset', type=int, default=FRAMES[0])
    p.add_argument('--frames', type=int, default=FRAMES[1] - FRAMES[0])
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    return p.parse_args(argv)


if __name__ == '__main__':
    A = parse_args()
    {'gate': lambda: gate_mode(A, sys.argv[1:]), 'pilot5': lambda: pilot_mode(A, sys.argv[1:])}[A.mode]()
