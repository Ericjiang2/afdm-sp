"""Paired receiver arms over a single frozen Stage 3 F0 capture."""
from copy import copy
from hashlib import md5
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from time import process_time
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE3 = HERE.parent / 'cstate_codelay_sbl_stage3_20261118'
E1 = HERE.parent / 'tf_cstate_e1_20261017'
SBL = HERE.parent / 'tf_e3_sbl_20261017'
FROZEN = {
    STAGE3/'run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    STAGE3/'codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    E1/'e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    E1/'geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    E1/'geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    SBL/'sbl_rx.py': '7509783b3fbe80e596b642dcd098f89b',
}
ARMS = ('CD', 'Z', 'H', 'S', 'Z-sel')


def verify_file(path, expected):
    digest = md5()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(f'Frozen source or archive mismatch: {path} ({actual} != {expected})')
    return actual


def load():
    sources = {str(p.relative_to(HERE.parent)): verify_file(p, h) for p, h in FROZEN.items()}
    sys.path.insert(0, str(STAGE3))
    spec = spec_from_file_location('gamma0_stage3_reference', STAGE3/'run.py')
    stage = module_from_spec(spec)
    spec.loader.exec_module(stage)
    ctx, full, cd, checks = stage.context()
    for module, path in ((stage.codelay, STAGE3/'codelay.py'),
                         (stage.e1, E1/'e1_driver.py'),
                         (full, E1/'geometry_validation_variant.py')):
        if Path(module.__file__).resolve() != path.resolve():
            raise ValueError(f'Unexpected frozen import for {module.__name__}: {module.__file__}')
    sys.path.insert(0, str(SBL))
    import sbl_rx
    if Path(sbl_rx.__file__).resolve() != (SBL/'sbl_rx.py').resolve():
        raise ValueError(f'Unexpected frozen QPSK slicer import: {sbl_rx.__file__}')
    return stage, ctx, full, cd, sbl_rx.hard_decision, dict(
        bound_files=sources, stage3_checks=checks, p1_md5=ctx.source_md5,
        p1_paths=ctx.source_paths, environment=ctx.environment)


def zero_variance(route, *, hard_mean=None):
    def reopen(y, x, v, paths, **opts):
        if hard_mean is not None:
            x = hard_mean()
        return route.reopen_geometry(y, x, np.zeros_like(v), paths, **opts)

    return SimpleNamespace(Path=route.Path, reopen_geometry=reopen)


def kernels(full, cd, slicer, obs, ctx, arrays):
    from messages import moments

    def hard_mean():
        # Recover mu from APP so subtracting pilot from the already rounded
        # soft mean cannot turn a small negative component into a slicer tie.
        pd = 1 - ctx.system.rho
        mu, _, _ = moments(np.clip(arrays['r1_app'], -20, 20), pd)
        return obs['pilot'] + slicer(mu, pd)

    return {
        'CD': (cd, 'A1'),
        'Z': (zero_variance(cd), 'A1'),
        'H': (zero_variance(cd, hard_mean=hard_mean), 'A1'),
        'S': (full, 'A2'),
    }


def gains_record(gains):
    return [[float(g.real), float(g.imag)] for g in gains]


def capture(stage, ctx, obs, truth):
    dec, arrays, syndrome, _ = stage.e1.f0_state(ctx, obs)
    f0 = dict(**stage.decoded(ctx, dec, truth), syndrome=syndrome, edits=[],
              paths=[[int(delay), float(nu)] for delay, nu in
                     zip(arrays['r1_delays'], arrays['r1_dopplers'], strict=True)],
              gains=gains_record(arrays['r1_gains']))
    return f0, arrays


def run_arm(stage, ctx, obs, truth, arrays, kernel, spec):
    branch = stage.e1.run_branch(ctx, kernel, obs, arrays, spec)
    result = branch['result']
    detail = stage.path_records(branch)
    return dict(**stage.decoded(ctx, branch['decoder'], truth),
                syndrome=int(ctx.hd.syndrome_weight(ctx, branch['decoder']['decoded'])),
                gains=gains_record(result.gains),
                detector_gains=gains_record(branch['detector']['gains']), **detail)


def fixed_support(cd, selected_paths):
    def reopen(y, x, v, _paths, **opts):
        return cd.reopen_geometry(y, x, v, selected_paths, **{**opts, 'max_edits': 0, 'local_passes': 0})

    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen)


def one(stage, ctx, full, cd, slicer, base, key, *, arms=ARMS, contexts=None):
    """The phase-two row builder. Phase one callers supply only gate keys."""
    scenario, rho, snr, frame = key
    started = process_time()
    raw, obs, truth = stage.observed(ctx, base, rho, snr)
    f0, arrays = capture(stage, ctx, obs, truth)
    times = {'F0_and_observation': process_time() - started}
    records = {'F0': f0}
    selected = kernels(full, cd, slicer, obs, ctx, arrays)
    for name in arms:
        started = process_time()
        branch_ctx = ctx if contexts is None else contexts[name]
        if not f0['syndrome']:
            records[name] = f0
        elif name == 'Z-sel':
            paths = [cd.Path(*p) for p in records['Z']['paths']]
            kernel = fixed_support(cd, paths)
            refit = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, 'A1')
            if refit['paths'] != records['Z']['paths'] or refit['edits']:
                raise AssertionError('The CD gain refit changed Z support')
            records[name] = dict(refit, edits=records['Z']['edits'], support_source='Z')
        else:
            kernel, spec = selected[name]
            records[name] = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, spec)
        times[name] = process_time() - started
    row = dict(zip(stage.e1.KEY_FIELDS, key, strict=True), syndrome=f0['syndrome'],
               truth=stage.truth_record(obs, truth), inputs=stage.input_record(raw, obs),
               arms=records)
    times['row_overhead'] = process_time() - started - times[arms[-1]]
    return row, times


def detector_observer(stage, ctx):
    """Capture exactly the downstream arguments other than support and gains."""
    signatures = []

    def scalar_joint(y, pilot, channel, sigma2, **opts):
        signatures.append(dict(y=stage.digest(y), pilot=stage.digest(pilot), n=channel.n,
                               c1=channel.c1, c2=channel.c2, sigma2=sigma2,
                               **{**opts, 'prior': stage.digest(opts['prior'])}))
        return ctx.native.scalar_joint(y, pilot, channel, sigma2, **opts)

    observed = copy(ctx)
    observed.native = SimpleNamespace(scalar_joint=scalar_joint,
                                      decoder_messages=ctx.native.decoder_messages)
    return observed, signatures
