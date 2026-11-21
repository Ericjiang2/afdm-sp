"""MIXED8 receiver and synthetic covariance checks."""
# Observation setup from frozen screen.py::read_base; the wrapper keeps decoded bits and omits the unused TRUE_CHANNEL call because read_base returns only error counts for all references.

from pathlib import Path
import sys
import time

import numpy as np

EXPERIMENTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENTS / 'cstate_sparse_doublet_screen_20261118'))
sys.path.insert(0, str(EXPERIMENTS / 'unified_cov_prospective_20261119'))
import screen  # noqa: E402
import cstate  # noqa: E402

ARMS = ('F0', 'A2', 'CD', 'U', 'TRUE_GEOMETRY')
SNR_GRID = (6, 7, 8, 9, 10, 12)
OLD_FRAMES = range(100, 196)
SMOKE_FRAMES = range(200, 208)
MAIN_FRAMES = range(1000, 1600)
MAIN_SNR_DB = 7
TAU = cstate.TAU
SCENARIO = 'MIXED8'


def context():
    ctx, full, cd, stage3_checks = cstate.context()
    screen_checks = screen.e2.check_frozen_md5(ctx)
    if any(entry['status'] != 'ok' for entry in screen_checks.values()):
        raise AssertionError('E-2 source inventory did not pass')
    return ctx, full, cd, {'E1_STAGE3': stage3_checks, 'E2_SCREEN': screen_checks}


def source_files():
    full, guarded = screen.e2.load_kernels()
    paths = [Path(module.__file__).resolve() for module in
             (screen, cstate, sys.modules[cstate.low_projector.__module__], cstate.stage3,
              cstate.stage3.codelay, screen.e2, screen.e2.e1d, screen.e2.ch, screen.e2.e2_lib,
              screen.e2.cg, full, guarded)]
    return {str(path.relative_to(EXPERIMENTS.parent)): str(path) for path in paths}


def _observe(ctx, raw, diag, snr):
    frame = screen.e2.ch.at_snr(raw, snr)
    obs = ctx.hd.observe(frame, screen.RHO, snr)
    truth = ctx.hd.truth_from_raw(frame, diag)
    n = len(obs['y'])
    channel = ctx.Channel(n, ctx.system.c1, ctx.system.c2,
                          truth['l_i'], truth['k_real'], truth['g_i'])
    scale = np.sqrt(2 * (1 - screen.RHO))
    estimate = channel.apply(obs['pilot'] + raw['data'] / scale)
    reference = obs['y'] - np.sqrt(frame['sigma2']) * raw['noise'] / scale
    closure = float(np.linalg.norm(estimate - reference) / np.linalg.norm(reference))
    if not np.isfinite(closure) or closure > 1e-9:
        raise AssertionError(f'Normalized truth response does not close: {closure}')
    return obs, truth, closure


def _metrics(truth, delays, dopplers, n):
    metrics = screen.support_metrics(truth, delays, dopplers, n)
    flags = {f"{doublet['separation']:.2f}": doublet['atoms'] >= 2
             for doublet in metrics['doublets']}
    if flags.keys() != {'0.35', '0.75'}:
        raise AssertionError(f'Expected both MIXED8 truth doublets, got {flags}')
    return dict(metrics, doublet_two_atoms=flags)


def _record(ctx, decoded, truth, delays, dopplers, n, *, result=None):
    decision = (cstate._geometry_record(result) if result is not None
                else dict(first_edit_type=None, decision=[], state=None))
    decision['atom_count'] = len(delays)
    bits = decoded['decoded']
    return dict(info_errors=int(screen.e2.gd.score(ctx, bits, truth)),
                decoded_sha=screen.e2.gd.bits_sha(bits),
                atoms=[[int(delay), float(doppler)]
                       for delay, doppler in zip(delays, dopplers, strict=True)],
                **decision, **_metrics(truth, delays, dopplers, n))


def one(ctx, full, cd, frame, snr, *, arms=ARMS, tau=TAU, check_scores=False, main=False):
    """Enforce the cohort and arm contract before generating a frame."""
    if main:
        if frame not in MAIN_FRAMES or snr != MAIN_SNR_DB or arms != ARMS or tau != TAU or check_scores:
            raise ValueError('Main run requires the frozen frame, SNR, arms, and cutoff')
    else:
        if frame not in OLD_FRAMES and frame not in SMOKE_FRAMES:
            raise ValueError(f'Frame {frame} is outside the Phase 1 allowlist')
        if frame in OLD_FRAMES and 'U' in arms:
            raise ValueError('U is forbidden on old evaluation frames at every cutoff')
        if set(arms) - {*ARMS, 'SCREEN_CD'} or snr not in SNR_GRID:
            raise ValueError(f'Unsupported Phase 1 arms or SNR: {arms}, {snr}')

    start = time.process_time()
    e2 = screen.e2
    msg = e2.ch.cluster_message(ctx, screen.SEED, screen.RHO, frame)
    raw, diag = screen.physical_frame(ctx, frame, SCENARIO, msg)
    obs, truth, closure = _observe(ctx, raw, diag, snr)
    n = len(obs['y'])
    stamp = time.process_time()
    decoded, arrays, syndrome, _ = e2.e1d.f0_state(ctx, obs)
    delays, dopplers = arrays['r1_delays'], arrays['r1_dopplers']
    if not 0 < len(delays) <= screen.SLOTS:
        raise AssertionError(f'F0 exceeded the {screen.SLOTS}-slot capacity: {len(delays)}')
    f0 = _record(ctx, decoded, truth, delays, dopplers, n)
    rows = {'F0': dict(f0, seconds=time.process_time() - stamp)}
    census = cstate._empty_census()

    for arm in arms:
        if arm == 'F0':
            continue
        stamp = time.process_time()
        if arm == 'TRUE_GEOMETRY':
            reference = ctx.hd.run_a2(ctx, obs, truth)[0]
            record = _record(ctx, reference, truth, truth['l_i'], truth['k_real'], n)
        elif not syndrome:
            rows[arm] = dict(f0, seconds=0.)
            continue
        else:
            if arm in ('A2', 'SCREEN_CD'):
                _, guarded = e2.load_kernels()
                route = guarded if arm == 'A2' else screen.codelay_kernel(guarded)
                branch = e2.run_branch(ctx, route, obs, arrays, 'A2' if arm == 'A2' else 'A1')
            else:
                route = cstate.unified_route(full, cd, tau, check_scores=check_scores) if arm == 'U' else cd
                branch = e2.e1d.run_branch(ctx, route, obs, arrays, 'A1')
            result = branch['result']
            record = _record(ctx, branch['decoder'], truth, [p.delay for p in result.paths],
                             [p.doppler for p in result.paths], n, result=result)
            if arm == 'U' and 'projector_census' in result.diagnostics:
                census = result.diagnostics['projector_census']
        rows[arm] = dict(record, seconds=time.process_time() - stamp)

    decision_differs = (rows['U']['decision'] != rows['CD']['decision']
                        if 'U' in rows and 'CD' in rows else None)
    return dict(scenario=SCENARIO, frame=frame, snr_db=snr, syndrome=int(syndrome),
                closure=closure, entering_slots=len(delays),
                info_sha=ctx.array_hash(raw['info']), noise_sha=ctx.array_hash(raw['noise']),
                doublet_separations=[float(np.ptp(truth['k_real'][truth['l_i'] == delay]))
                                     for delay in (6, 22)],
                inputs=cstate.stage3.input_record(raw, obs), truth=cstate.stage3.truth_record(obs, truth),
                arms=rows, census=dict(census, decisions_differ=decision_differs),
                seconds=time.process_time() - start)


def synthetic_gate(full, cd):
    covariance = cstate.synthetic_gate(full, cd)
    n = 64
    truth = dict(l_i=np.array([6, 6, 22, 22, 31]), k_real=np.array([0., .35, 0., .75, 0.]),
                 g_i=np.array([1., 1j, 1., 1j, 1.]))
    exact = _metrics(truth, truth['l_i'], truth['k_real'], n)
    partial = _metrics(truth, [6, 6, 22, 31, 31], [0., .35, 0., 0., .25], n)
    absent = _metrics(truth, [31], [0.], n)
    assert exact['doublet_two_atoms'] == {'0.35': True, '0.75': True}
    assert exact['doublet_energy_missed'] < 1e-20
    assert partial['doublet_two_atoms'] == {'0.35': True, '0.75': False}
    assert partial['singleton_phantom'] == partial['close_phantom'] == 1
    assert 0 < partial['doublet_energy_missed'] < partial['doublet_energy_total']
    assert absent['doublet_two_atoms'] == {'0.35': False, '0.75': False}
    assert absent['doublet_energy_missed'] == absent['doublet_energy_total']
    return dict(pass_=True, tau0_bit_identity=True, covariance=covariance,
                census={'exact': exact, 'partial': partial, 'absent': absent})
