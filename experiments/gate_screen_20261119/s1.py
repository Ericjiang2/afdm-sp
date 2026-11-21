"""Replay MIXED8 entering states and score the two archived truth doublets."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from gate import floor_pair, pair_contrast
from soft_replay import soft_app

EXPERIMENTS = Path(__file__).resolve().parents[1]
SOURCE = EXPERIMENTS / 'doublet_conflict_20261119'
ARCHIVE = SOURCE / 'out/main_20261119'
ROWS_MD5 = '3fb82ceaba80cac43c307b19f95c489e'
CONFIG_SHA256 = '02dc557e6d2e7023ecc56b39c02b8f2bc57f0cfce5decff503a1330f65d45cb4'
FRAMES = range(1000, 1600)
SNR_DB = 7
RHO = .5
SCENARIO = 'MIXED8'
GAPS = {'0.35', '0.75'}


def load_archive():
    """Read the frozen trigger labels and retain only inputs to this screen."""
    rows_path = ARCHIVE / 'rows.jsonl'
    raw = rows_path.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()
    if md5 != ROWS_MD5:
        raise ValueError(f'Archived MIXED8 rows mismatch: {rows_path} md5={md5}')
    config_bytes = (ARCHIVE / 'config.json').read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != CONFIG_SHA256:
        raise ValueError('MIXED8 archive configuration differs from the original run')
    cfg = json.loads(config_bytes)['_config']
    if (cfg['scenario'], cfg['rho'], cfg['snr_db'], cfg['fresh_inclusive_block']) != (
            SCENARIO, RHO, SNR_DB, [FRAMES.start, FRAMES.stop - 1]):
        raise ValueError('Archived MIXED8 configuration has a different cohort')
    rows = {}
    seen = set()
    for line in raw.splitlines():
        row = json.loads(line)
        frame = row['frame']
        if (type(frame) is not int or frame not in FRAMES or frame in seen
                or row['scenario'] != SCENARIO or row['snr_db'] != SNR_DB
                or any(row[key] != cfg[key] for key in ('freeze_commit', 'launch_commit'))):
            raise ValueError(f'Invalid or duplicate archived MIXED8 frame {frame}')
        seen.add(frame)
        syndrome = row['syndrome']
        if type(syndrome) is not int or syndrome < 0:
            raise ValueError(f'Invalid archived trigger indicator on frame {frame}')
        if syndrome:
            atoms = row['arms']['F0']['atoms']
            if len(atoms) != row['entering_slots']:
                raise ValueError(f'Archived entering support size mismatch on frame {frame}')
            rows[frame] = dict(
                frame=frame, atoms=atoms, y_sha=row['inputs']['y'], pilot_sha=row['inputs']['pilot'],
                truth_delays=row['truth']['delays'], truth_dopplers=row['truth']['dopplers'])
    if seen != set(FRAMES) or len(rows) < 20:
        raise ValueError(f'Expected {len(FRAMES)} archived MIXED8 frames and at least 20 triggers')
    provenance = dict(
        archive_rows=str(rows_path), archive_rows_md5=md5,
        archive_config_sha256=CONFIG_SHA256,
        freeze_commit=cfg['freeze_commit'], launch_commit=cfg['launch_commit'],
        receiver_sha256=cfg['sha256']['experiments/doublet_conflict_20261119/mixed8_receiver.py'],
        frozen_source_md5=cfg['frozen_source_md5'], loaded_source_checks=cfg['loaded_source_checks'],
        seed=cfg['seed'], rho=RHO, snr_db=SNR_DB, scenario=SCENARIO,
        archived_frame_count=len(seen), triggered_frame_count=len(rows))
    return [rows[frame] for frame in sorted(rows)], provenance


def make_context(provenance):
    sys.path.insert(0, str(SOURCE))
    import mixed8_receiver as receiver

    src = Path(receiver.__file__).resolve()
    if (src != SOURCE / 'mixed8_receiver.py'
            or hashlib.sha256(src.read_bytes()).hexdigest() != provenance['receiver_sha256']):
        raise ValueError(f'Unexpected MIXED8 receiver source: {src}')
    for rel, expected in provenance['frozen_source_md5'].items():
        if hashlib.md5((EXPERIMENTS.parent / rel).read_bytes()).hexdigest() != expected:
            raise ValueError(f'MIXED8 dependency differs from archive: {rel}')
    ctx, full, _, checks = receiver.context()
    if checks != provenance['loaded_source_checks']:
        raise ValueError('Loaded MIXED8 source inventory differs from archive')
    for rel, actual in receiver.source_files().items():
        if rel not in provenance['frozen_source_md5'] or Path(actual) != EXPERIMENTS.parent / rel:
            raise ValueError(f'Unexpected loaded MIXED8 dependency: {actual}')
    if dict(entropy=receiver.screen.ENTROPY, domain=receiver.screen.DOMAIN) != provenance['seed']:
        raise ValueError('Loaded MIXED8 RNG identity differs from archive')
    return receiver, ctx, full


def _f0_soft_state(ctx, obs):
    # From frozen native_twofft.receive: reuse its front/CE/detector/moments;
    # keep soft feedback only, since receive also returns hard decoded bits.
    native, system = ctx.native, ctx.system
    y, pilot, sigma2 = obs['y'], obs['pilot'], obs['sigma2']
    state = native.pilot_front(obs, system, ctx.code)
    for index in range(2):
        channel, _ = native.time_refine(
            y, pilot, state['mu'], state['v'], state['delays'], state['dopplers'], state['gains'],
            system.c1, system.c2, sigma2, mode='soft', max_paths=8, rounds=2)
        detector = native.scalar_joint(
            y, pilot, channel, sigma2, pd=1 - system.rho, prior=state['prior'],
            iterations=20, gain_mode='joint')
        # The archived trigger means the last round reached all 50 sweeps.
        app, check = soft_app(native, ctx.code, np.clip(detector['extrinsic'], -20, 20),
                              50, early_stop=(index == 0))
        mu, v, _ = native.moments(np.clip(app, -20, 20), 1 - system.rho)
        state = dict(prior=np.clip(check, -20, 20), mu=mu, v=v, delays=channel.delays,
                     dopplers=channel.dopplers, gains=detector['gains'])
    return state['delays'], state['dopplers'], pilot + state['mu'], state['v']


def run_frame(context, row):
    receiver, ctx, full = context
    from physical import daft, dkernel

    frame = row['frame']
    screen = receiver.screen
    ch = screen.e2.ch
    msg = ch.cluster_message(ctx, screen.SEED, RHO, frame)
    raw, _ = screen.physical_frame(ctx, frame, SCENARIO, msg)
    obs = ctx.hd.observe(ch.at_snr(raw, SNR_DB), RHO, SNR_DB)
    digest = receiver.cstate.stage3.digest
    if digest(obs['y']) != row['y_sha'] or digest(obs['pilot']) != row['pilot_sha']:
        raise ValueError(f'Observed input hash mismatch on MIXED8 frame {frame}')
    delays, dopplers, mean_af, v = _f0_soft_state(ctx, obs)
    archive_delays, archive_dopplers = zip(*row['atoms'], strict=True)
    for got, expected, dtype in ((delays, archive_delays, '<i8'),
                                 (dopplers, archive_dopplers, '<f8')):
        if np.asarray(got, dtype=dtype).tobytes() != np.asarray(expected, dtype=dtype).tobytes():
            raise ValueError(f'Entering support differs bytewise on MIXED8 frame {frame}')

    # Truth starts here, after the observation-only F0 state is constructed.
    true_delays = np.asarray(row['truth_delays'])
    true_dopplers = np.asarray(row['truth_dopplers'])
    c1, c2 = ctx.system.c1, ctx.system.c2
    mean_time = daft(mean_af, c1, c2, inverse=True)
    ridge = float(obs['sigma2'])
    u, n = float(v.sum()), len(v)
    results = {}
    for delay in (6, 22):
        pair = true_dopplers[true_delays == delay]
        if len(pair) != 2:
            raise ValueError(f'Expected two archived Dopplers at delay {delay} on frame {frame}')
        gap = f'{np.ptp(pair):.2f}'
        paths = [full.Path(delay, float(doppler)) for doppler in pair]
        dictionary = full._responses(mean_time, paths, c1, c2)
        kernel = dkernel(pair[None, :] - pair[:, None], n)
        results[gap] = (delay, floor_pair(dictionary.conj().T @ dictionary, u * kernel, ridge,
                                        pair_contrast(kernel)))
    if results.keys() != GAPS:
        raise ValueError(f'Unexpected archived doublet separations on frame {frame}')
    (narrow_delay, narrow_floored), (control_delay, control_floored) = results['0.35'], results['0.75']
    return dict(frame=frame, narrow_delay=narrow_delay, narrow_floored=bool(narrow_floored),
                control_delay=control_delay, control_floored=bool(control_floored),
                support_bit_identical=True)
