#!/usr/bin/env python3
"""Scalar-Gamma SBL replay: continuous point40 and reset/fixed20 from saved point20 gains."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
THREE = EXP / 'sbl_three_mode_20261020'
spec = importlib.util.spec_from_file_location('three_mode_reference', THREE / 'driver.py')
oldd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = oldd
spec.loader.exec_module(oldd)

spec = importlib.util.spec_from_file_location('three_aggregate', THREE / 'aggregate.py')
oldagg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oldagg)
e3d = oldd.e3d
FRAMES = range(9100, 9150)
GRID = oldd.GRID
OLD = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1')
OUT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run1')


def complex_array(saved):
    a = np.asarray(saved, float)
    if a.ndim != 2 or a.shape[1] != 2 or not np.isfinite(a).all():
        raise ValueError('saved complex vector invalid')
    return a[:, 0] + 1j*a[:, 1]


def load_old(directory, ctx):
    files = sorted(directory.glob('rows_shard*.jsonl*'))
    configs = sorted(directory.glob('config_shard*.json'))
    if len(files) != 12 or len(configs) != 12:
        raise ValueError('old raw/config shard coverage')
    identities = []
    for path in configs:
        cfg = json.loads(path.read_text())['_config']
        identities.append({k:cfg[k] for k in ('source_md5','e3_own_md5','frozen_md5_check','own_md5','old_rows_md5','family_P1')})
    if any(item != identities[0] for item in identities):
        raise ValueError('mixed old source identities')
    identity = identities[0]
    rows = []
    for path in files:
        with (gzip.open if path.suffix=='.gz' else open)(path,'rt') as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    if sum(bool(r.get('observer_parity')) for r in rows) != 1:
        raise ValueError('old observer parity gate')
    oldagg.validate(rows)
    hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    summary = json.loads((directory.parent / 'analysis_fix' / 'summary.json').read_text())
    if summary['raw_sha256'] != hashes or summary['n_keys'] != 200:
        raise ValueError('old raw hashes differ from accepted summary')
    old_cfg = json.loads((directory / 'config_shard000.json').read_text())['_config']
    # The two explicitly imported prior-experiment modules are absent from the
    # original driver's __main__ source inventory; bind them separately below.
    old_source_view = {k:v for k,v in ctx.source_md5.items() if k not in ('three_mode_reference','three_aggregate')}
    if (e3d.e3_lib.md5_file(Path(oldd.__file__)) != old_cfg['own_md5']['driver.py']
            or e3d.e3_lib.md5_file(Path(oldagg.__file__)) != old_cfg['own_md5']['aggregate.py']
            or e3d.own_md5() != identity['e3_own_md5']
            or old_source_view != identity['source_md5']):
        raise RuntimeError('old imported receiver source identity changed')
    frozen, actual_paths = oldd.source_identity(ctx)
    if frozen != identity['frozen_md5_check'] or actual_paths != old_cfg['frozen_actual_paths']:
        raise RuntimeError('old frozen imported paths/hashes changed')
    return {e3d.key_of(r): r for r in rows}, hashes, identity, frozen, actual_paths


def first_round_check(ctx, cache, grid, obs):
    """Exact E-3 process_key stage 1 and round 1; no stage-2 SBL is executed."""
    from physical import daft
    n, c1, c2 = len(obs['y']), ctx.system.c1, ctx.system.c2
    pd = 1 - ctx.system.rho
    delays_g, nus_g = grid
    Y = daft(obs['y'], c1, c2, True)
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = e3d.sbl.screen(Bp, Y, e3d.sbl.N_SCREEN)
    r1 = e3d.sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0/(float(obs['sigma2'])+pd), Gamma=None)
    g1_idx, g1_mu, _ = e3d.sbl.select_output(cand1[r1['idx']], r1['mu'])
    ch1 = e3d.make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    _, dec1, _, _ = e3d.detect_decode(ctx, obs, ch1, None)
    return np.clip(dec1['raw_check_extrinsic'], -20, 20)


def checked_plain(ctx, obs, channel, prior, mode, iterations, recorded):
    plain = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1-ctx.system.rho,
                                    prior=prior, iterations=iterations, damping=.3, gain_mode=mode)
    mismatch = e3d.e3_lib.deep_equal({k:v for k,v in recorded.items() if k!='states'}, plain)
    if mismatch:
        raise AssertionError(f'{mode}{iterations} observer parity: {mismatch[:3]}')


def score_arm(ctx, det, channel, truth, data_af, coded, detect_seconds):
    t0 = time.perf_counter()
    dec = ctx.native.decoder_messages(ctx.code, np.clip(det['extrinsic'], -20, 20), maxiter=50)
    decode_seconds = time.perf_counter()-t0
    err = e3d.gd.score(ctx, dec['decoded'], truth)
    path = dict(delays=channel.delays, dopplers=channel.dopplers, gains=det['gains'])
    return dict(info_errors=int(err), fer=int(err>0), decoded_sha256=e3d.gd.bits_sha(dec['decoded']),
                ldpc_iters=int(dec['iterations']), extrinsic_bit_logloss=oldd.bit_loss(det['extrinsic'], coded),
                nmse_final=float(e3d.crb.channel_nmse(path, e3d.truth_paths(truth), channel.n)),
                data_mse_final=float(np.mean(np.abs(det['mu']-data_af)**2)),
                symbol_variance_final=float(np.mean(det['variance'])),
                detect_seconds=detect_seconds, decode_seconds=decode_seconds)


def process_key(ctx, cache, grid, obs, data_af, truth, meta, old, gate=False):
    saved = old['three_mode']['L-diag']
    old_point = saved['modes']['point']
    support = saved['support']
    h0, h20 = complex_array(saved['h0']), complex_array(old_point['trajectory'][-1]['h'])
    if not np.array_equal(h0, complex_array(old_point['trajectory'][0]['h'])):
        raise AssertionError('saved initial gains inconsistent')
    coded = ctx.encode(ctx.code, truth['info'])
    if not np.array_equal(coded, truth['coded']):
        raise AssertionError('codeword reconstruction')
    prior = first_round_check(ctx, cache, grid, obs)
    if oldd.sha(prior) != saved['prior_sha256']:
        raise AssertionError(f'round-1 check prior mismatch: {e3d.key_of(meta)}')
    ch0 = e3d.make_channel(ctx, len(obs['y']), support['delays'], support['dopplers'], h0)
    ch20 = e3d.make_channel(ctx, len(obs['y']), support['delays'], support['dopplers'], h20)
    kw = dict(pd=1-ctx.system.rho, prior=prior, damping=.3, record_states=True)
    t0 = time.perf_counter()
    p40 = ctx.native.scalar_joint(obs['y'], obs['pilot'], ch0, obs['sigma2'], iterations=40, gain_mode='point', **kw)
    p40_seconds = time.perf_counter()-t0
    if len(p40['states']) != 40 or len(p40['trace']) != 40:
        raise AssertionError('point40 states incomplete')
    for i in range(20):
        if not np.array_equal(p40['states'][i]['h'], complex_array(old_point['trajectory'][i+1]['h'])):
            raise AssertionError(f'point40 gain prefix differs at {i}')
        if p40['trace'][i] != old_point['trajectory'][i+1]['scalar_trace']:
            raise AssertionError(f'point40 scalar prefix differs at {i}')
    if np.any(p40['gain_variance'] != 0) or any(s['vh'] != 0 for s in p40['states']):
        raise AssertionError('point40 gain variance nonzero')
    t0 = time.perf_counter()
    rf = ctx.native.scalar_joint(obs['y'], obs['pilot'], ch20, obs['sigma2'], iterations=20, gain_mode='fixed', **kw)
    rf_seconds = time.perf_counter()-t0
    if len(rf['states']) != 20 or any(not np.array_equal(s['h'], h20) for s in rf['states']):
        raise AssertionError('reset-fixed gains moved')
    if gate:
        checked_plain(ctx, obs, ch0, prior, 'point', 40, p40)
        checked_plain(ctx, obs, ch20, prior, 'fixed', 20, rf)
        point20 = ctx.native.scalar_joint(obs['y'], obs['pilot'], ch0, obs['sigma2'],
                                          pd=1-ctx.system.rho, prior=prior, iterations=20, damping=.3, gain_mode='point')
        dec = ctx.native.decoder_messages(ctx.code, np.clip(point20['extrinsic'], -20, 20), maxiter=50)
        if (e3d.gd.bits_sha(dec['decoded']) != old_point['decoded_sha256']
                or e3d.gd.score(ctx, dec['decoded'], truth) != old_point['info_errors']):
            raise AssertionError('real-gate point20 decoder mismatch')
    baseline = {}
    for name, record in (('fixed20', saved['modes']['fixed']), ('point20', old_point)):
        baseline[name] = {f:record[f] for f in ('info_errors','fer','decoded_sha256','extrinsic_bit_logloss')}
        baseline[name].update(nmse_final=record['trajectory'][-1]['channel_nmse'],
                              data_mse_final=record['trajectory'][-1]['data_mse'],
                              symbol_variance_final=record['trajectory'][-1]['symbol_variance'])
    return dict(meta, status='ok', old_three_mode_hash=hashlib.sha256(json.dumps(saved,sort_keys=True).encode()).hexdigest(),
                support=support, h0=oldd.pairs(h0), h20=oldd.pairs(h20), prior=prior.tolist(),
                input_sha256=dict(h0=oldd.sha(h0), h20=oldd.sha(h20), prior=oldd.sha(prior)),
                point40_prefix_match=True, observer_parity=bool(gate),
                baseline=baseline,
                arms=dict(P40=score_arm(ctx,p40,ch0,truth,data_af,coded,p40_seconds),
                          RF=score_arm(ctx,rf,ch20,truth,data_af,coded,rf_seconds)))


def run(args, argv):
    if args.nshard != 12 or not 0 <= args.shard < 12 or args.frame_offset != 9100 or args.frames != 50:
        raise ValueError('registered 12-shard cohort only')
    ctx = e3d.p1ctx.load()
    old, hashes, identity, frozen, paths = load_old(args.old_rows, ctx)
    args.out.mkdir(parents=True, exist_ok=True)
    cache, grid = e3d.PilotCache(), e3d.sbl.full_grid(int(ctx.system.l_max_cap))
    if args.gate_only:
        if args.shard != 0:
            raise ValueError('gate uses shard0')
        raw_base, diag_base = e3d.p1ctx.base(ctx, 'U', .3, 9100)
        meta, obs, data_af, truth = e3d.observe_key(ctx, raw_base, diag_base, 'U', 300, 700, 9100)
        row = process_key(ctx, cache, grid, obs, data_af, truth, meta, old[e3d.key_of(meta)], gate=True)
        (args.out/'gate.json').write_text(json.dumps(dict(passed=True, key=list(e3d.key_of(meta)),
             outcomes=row['arms'], old_raw_sha256=hashes, frozen_actual_paths=paths), allow_nan=False, indent=1)+'\n')
        print('gate passed', flush=True)
        return
    row_path = args.out/f'rows_shard{args.shard:03d}.jsonl'
    config_path = args.out/f'config_shard{args.shard:03d}.json'
    if row_path.exists() or config_path.exists():
        raise FileExistsError('shard output already exists')
    cfg = dict(_argv=argv, _config=dict(shard=args.shard,nshard=12,frames=[9100,9150],grid=GRID,
        old_rows=str(args.old_rows.resolve()),old_raw_sha256=hashes,old_identity=identity,
        frozen_md5_check=frozen,frozen_actual_paths=paths,source_md5=ctx.source_md5,
        own_md5={p.name:e3d.e3_lib.md5_file(p) for p in HERE.glob('*.py')},environment=ctx.environment))
    config_path.write_text(json.dumps(cfg,allow_nan=False,indent=1,default=str)+'\n')
    start = time.monotonic()
    with row_path.open('x') as handle:
        for frame in list(FRAMES)[args.shard::12]:
            for meta, obs, data_af, truth in e3d.cells_of_frame(ctx, frame, GRID, None):
                key = e3d.key_of(meta)
                try:
                    if time.monotonic()-start > args.deadline_seconds:
                        raise TimeoutError('shard deadline')
                    row = process_key(ctx, cache, grid, obs, data_af, truth, meta, old[key],
                                      gate=(args.shard==0 and frame==9100 and key[0]=='U' and key[2]==700))
                    e3d.write_row(handle,row)
                    print(f'{key} ok',flush=True)
                except Exception as exc:
                    e3d.write_row(handle,dict(meta,status='error',error=repr(exc),trace=traceback.format_exc()[-3000:]))
                    raise
    print(f'shard {args.shard}: {time.monotonic()-start:.1f}s',flush=True)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--old-rows',type=Path,default=OLD)
    p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--shard',type=int,required=True)
    p.add_argument('--nshard',type=int,default=12)
    p.add_argument('--frame-offset',type=int,default=9100)
    p.add_argument('--frames',type=int,default=50)
    p.add_argument('--deadline-seconds',type=float,default=800)
    p.add_argument('--gate-only',action='store_true')
    a=p.parse_args(argv)
    run(a,sys.argv[1:] if argv is None else argv)

if __name__=='__main__':
    main()
