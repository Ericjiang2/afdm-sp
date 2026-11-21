"""Replay archived unified-SBL keys through data-aided candidate selection."""

from hashlib import md5, sha256
import json
from pathlib import Path
import sys

import numpy as np

from gate import compare_block, hermitian
from soft_replay import soft_app

EXPERIMENTS = Path(__file__).resolve().parents[1]
UNIFIED = EXPERIMENTS / 'unified_cov_prospective_20261119'
ARCHIVE = UNIFIED / 'out/main_20261119'
SNRS = (600, 700, 800, 900, 1000, 1100)
FRAMES = range(4400, 4600)
SAMPLE_SEED = 20261119
CONFIG_SHA256 = 'c4c600a1a36ada3b1c546293fd21a6644dc0359c4835145535ac3f69891b6e5c'
ROWS_MANIFEST_SHA256 = 'e227a7dd13ea02a94d413f3b1992e7025c7aba3d839fef0b8ee356eafef86370'


def load_archive():
    if (ARCHIVE / 'STATUS').read_text().strip() != 'DONE':
        raise RuntimeError('S2 requires a completed archive')
    config_bytes = (ARCHIVE / 'config.json').read_bytes()
    manifest = (ARCHIVE / 'REMOTE_ROWS_MD5.txt').read_bytes()
    if (sha256(config_bytes).hexdigest() != CONFIG_SHA256
            or sha256(manifest).hexdigest() != ROWS_MANIFEST_SHA256):
        raise RuntimeError('S2 archived config or row manifest differs from commit 5de89fa1')
    config = json.loads(config_bytes)['_config']
    shards = {}
    eligible = {}
    for line in manifest.decode().splitlines():
        digest, name = line.split()
        path = ARCHIVE / name
        raw = path.read_bytes()
        if md5(raw).hexdigest() != digest:
            raise RuntimeError(f'S2 archive checksum mismatch: {path}')
        shards[name] = digest
        for line in raw.splitlines():
            entry = json.loads(line)
            if entry['leg'] != 'sbl':
                continue
            key = tuple(entry['key'])
            row = entry['row']
            if (entry['snapshot_sha256'] != config['snapshot_sha256']
                    or entry['launch_commit'] != config['producing_commit']
                    or tuple(row['key']) != key or key in eligible):
                raise RuntimeError(f'Unexpected archived S2 identity: {key}')
            # Retain only the initialization inputs, fingerprints and schedule.
            eligible[key] = dict(
                sigma2=row['sigma2'], ldpc_sweeps=row['round1']['ldpc_iters'], sum_v=row['sum_v'],
                inputs={name: row['input_sha256'][name] for name in ('y', 'pilot', 'soft_mean', 'app_v')},
                candidate_sha=row['candidates_sha256'], candidates=row['n_candidates_stage2'],
                s_lo_rank=row['census']['projector_rank'],
                rng=(row['rng_entropy'], row['rng_domain']),
            )
    if set(eligible) != {(scenario, 300, snr, frame) for scenario in ('G', 'U')
                         for snr in SNRS for frame in FRAMES}:
        raise RuntimeError('S2 archive does not cover the frozen 2400-key grid')
    rng = np.random.default_rng(SAMPLE_SEED)
    selected = []
    for i, snr in enumerate(SNRS):
        pool = sorted(key for key in eligible if key[2] == snr)
        count = 34 if i < 2 else 33
        selected.extend((pool[j], eligible[pool[j]]) for j in sorted(rng.choice(len(pool), count, replace=False)))
    provenance = dict(archive=str(ARCHIVE), config_sha256=CONFIG_SHA256, manifest_sha256=ROWS_MANIFEST_SHA256,
                      archive_producing_commit=config['producing_commit'], rows_md5=shards,
                      archive_snapshot=config['snapshot_sha256'], selection_seed=SAMPLE_SEED, eligible_keys=len(eligible),
                      source_identity=config['sources']['spectral_sources_sha256'])
    return selected, provenance


def make_context(provenance):
    sys.path.insert(0, str(EXPERIMENTS / 'tf_e3c_shrink_20261018'))
    import e3c_driver as e3c
    from messages import moments
    from physical import daft, dkernel

    ctx = e3c.p1ctx.load()
    if e3c.source_identity(ctx) != provenance['source_identity']:
        raise RuntimeError('S2 loaded E-3c sources differ from the archive')
    grid = e3c.sbl.full_grid(int(ctx.system.l_max_cap))
    return ctx, e3c, moments, daft, dkernel, grid, e3c.e3d.PilotCache()


def run_key(context, item):
    ctx, e3c, moments, daft, dkernel, grid, cache = context
    key, archived = item
    scenario, rho, snr, frame = key
    e3d, sbl = e3c.e3d, e3c.sbl
    raw, diag = e3c.p1ctx.base(ctx, scenario, rho / 1000, frame)
    raw_at_snr, _ = ctx.reuse_at_snr(raw, diag, snr / 100)
    obs = ctx.hd.observe(raw_at_snr, rho / 1000, snr / 100)
    # Follow the frozen spectral_receiver.process_key preparation, stopping
    # before the data-aided EM fit. The archived BP sweep count fixes APP timing.
    system = ctx.system
    n, c1, c2 = len(obs['y']), system.c1, system.c2
    pd, sigma2 = 1 - system.rho, float(obs['sigma2'])
    delays_g, dopplers_g = grid
    y = daft(obs['y'], c1, c2, True)
    bp = cache.columns(obs['pilot'], c1, c2, delays_g, dopplers_g)
    cand1 = sbl.screen(bp, y, sbl.N_SCREEN)
    stage1 = sbl.sbl_em(bp[:, cand1], y, beta0=1 / (sigma2 + pd), Gamma=None)
    g1, gains, _ = sbl.select_output(cand1[stage1['idx']], stage1['mu'])
    channel = e3d.make_channel(ctx, n, delays_g[g1], dopplers_g[g1], gains)
    det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, sigma2, pd=pd, prior=None,
                                  iterations=20, damping=.3, gain_mode='fixed')
    app, _ = soft_app(ctx.native, ctx.code, np.clip(det['extrinsic'], -20, 20), archived['ldpc_sweeps'])
    mu, v, _ = moments(np.clip(app, -20, 20), pd)
    xt = e3d.self_xt(obs['pilot'] + mu, c1, c2)
    bs = sbl.columns(xt, delays_g, dopplers_g, c1, c2)
    top2 = sbl.screen(bs, y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(delay) for delay in delays_g[g1]), delays_g)
    inputs = {name: e3c.array_sha(value) for name, value in
              dict(y=obs['y'], pilot=obs['pilot'], soft_mean=mu, app_v=v).items()}
    u = float(np.sum(v))
    if (inputs != archived['inputs'] or e3c.array_sha(cand2) != archived['candidate_sha']
            or len(cand2) != archived['candidates'] or sigma2 != archived['sigma2'] or u != archived['sum_v']
            or archived['rng'] != (e3c.p1ctx.p1_driver.ENTROPY_HEX, str(e3c.p1ctx.p1_driver.DOMAIN))):
        raise RuntimeError(f'S2 state or grid replay differs from archive: {key}')

    delays, dopplers = delays_g[cand2], dopplers_g[cand2]
    blocks = []
    for delay in np.unique(delays):
        members = delays == delay
        nu = dopplers[members]
        b = bs[:, cand2[members]]
        d = hermitian(dkernel(nu[None, :] - nu[:, None], n))
        gate_rank, lo_rank, overlap_trace = compare_block(b.conj().T @ b, d, u, sigma2 + u / n)
        blocks.append(dict(delay=int(delay), atoms=len(nu), gate_rank=gate_rank,
                           s_lo_rank=lo_rank, overlap_trace=overlap_trace))
    if sum(block['s_lo_rank'] for block in blocks) != archived['s_lo_rank']:
        raise RuntimeError(f'S2 summed projector rank differs from archived S-lo: {key}')
    return dict(key=key, verified=True, blocks=blocks)
