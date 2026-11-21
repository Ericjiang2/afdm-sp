"""Paired MIXED8 arms over the archived receiver's observation and scoring paths."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import process_time

import numpy as np

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent/'doublet_conflict_20261119'
P1 = HERE.parent/'gamma0_exchange_20261120'
SBL = HERE.parent/'tf_e3_sbl_20261017'
ARMS = ('F0', 'CD', 'Z', 'H', 'S', 'A2g', 'Z-sel', 'TRUE_GEOMETRY')
SOURCE_SHA256 = {
    REFERENCE/'mixed8_receiver.py': '2b25faaeac5e9aec0eab5f0f14b626ab7e75165e86bb93f52abc4e651f0078b6',
    REFERENCE/'phase1_pins.json': '1d3ccb5bfd76983df24f67707f172de899df3a04a0477cf77ba92417370a1266',
    P1/'paired.py': '1e7a53887097cbd7214e175b63451b1a5cc546c43e9ad322167b050ffe6c5c71',
    P1/'phase1.py': 'e8ac9ba19675f8bcac957a8d5f9fb59e9c9a898c53011ba7d422e6f169914a03',
    SBL/'sbl_rx.py': 'b43d7a455c9a26b5d300246e934a1bec50f4379097ab756232d29219244ffadd',
}

sys.path[:0] = [str(REFERENCE), str(P1)]
import paired as p1  # noqa: E402


def context():
    for path, expected in SOURCE_SHA256.items():
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen source mismatch: {path}')
    import mixed8_receiver as ref
    if Path(ref.__file__).resolve() != REFERENCE/'mixed8_receiver.py':
        raise ValueError('Wrong MIXED8 receiver imported')
    provenance = REFERENCE/'phase1_pins.json'
    pins = json.loads(provenance.read_bytes())
    for name, digest in pins['frozen_source_md5'].items():
        p1.verify_file(HERE.parents[1]/name, digest)
    ctx, full, cd, checked = ref.context()
    actual_paths = ref.source_files()
    for name, path in actual_paths.items():
        if name not in pins['frozen_source_md5'] or Path(path).resolve() != HERE.parents[1]/name:
            raise ValueError(f'Loaded MIXED8 dependency differs: {name}')
    full_e2, guarded = ref.screen.e2.load_kernels()
    assert Path(full_e2.__file__).resolve() == Path(full.__file__).resolve()
    sys.path.insert(0, str(SBL))
    import sbl_rx
    if Path(sbl_rx.__file__).resolve() != SBL/'sbl_rx.py':
        raise ValueError('Wrong frozen hard decision slicer imported')
    source = dict(source_checks=checked, frozen_source_md5=pins['frozen_source_md5'],
                  bound_source_sha256={str(p.relative_to(HERE.parent)): h for p, h in SOURCE_SHA256.items()},
                  actual_source_paths=actual_paths, rng=pins['rng'], environment=ctx.environment)
    return (ref, ctx, full, cd, guarded, sbl_rx.hard_decision), source


def close_singletons(true_delays, atoms):
    counts = Counter(true_delays)
    groups = {}
    for delay, doppler in atoms:
        if counts[delay] == 1:
            groups.setdefault(delay, []).append(doppler)
    return sum(any(b - a <= .25 for a, b in zip(nus, nus[1:]))
               for nus in map(sorted, groups.values()))


def record(ref, ctx, decoder, truth, delays, dopplers, gains, n, *, result=None):
    row = ref._record(ctx, decoder, truth, delays, dopplers, n, result=result)
    return dict(row, gains=p1.gains_record(gains),
                syndrome=int(ctx.hd.syndrome_weight(ctx, decoder['decoded'])),
                edits=[] if result is None else [{k: e[k] for k in ('slot', 'old', 'new')} for e in result.edits],
                singleton_phantom_le_025=close_singletons(truth['l_i'], row['atoms']))


def one(loaded, frame, snr, *, arms=ARMS, contexts=None):
    """Evaluate a paired frame. The Phase 1 entry point supplies the allowlists."""
    ref, ctx, full, cd, guarded, slicer = loaded
    e2 = ref.screen.e2
    stage = ref.cstate.stage3
    started = process_time()
    msg = e2.ch.cluster_message(ctx, ref.screen.SEED, ref.screen.RHO, frame)
    raw, diag = ref.screen.physical_frame(ctx, frame, ref.SCENARIO, msg)
    obs, truth, closure = ref._observe(ctx, raw, diag, snr)
    decoder, arrays, syndrome, _ = e2.e1d.f0_state(ctx, obs)
    n = len(obs['y'])
    if not 0 < len(arrays['r1_delays']) <= ref.screen.SLOTS:
        raise AssertionError('F0 exceeded the frozen eight-slot capacity')
    f0 = record(ref, ctx, decoder, truth, arrays['r1_delays'], arrays['r1_dopplers'],
                arrays['r1_gains'], n)
    rows = {'F0': f0}
    timing = {'shared': process_time() - started}
    kernels = p1.kernels(full, cd, slicer, obs, ctx, arrays)
    for arm in arms:
        if arm == 'F0':
            continue
        stamp = process_time()
        if arm == 'TRUE_GEOMETRY':
            # This is the same fixed-geometry intervention called by hd.run_a2.
            # Keep its fitted final gains from the native receiver arrays.
            oracle = ctx.wrappers.run_true_geometry(obs, ctx.system, ctx.code, ctx.native,
                                                    delays=truth['l_i'], dopplers=truth['k_real'])
            item = record(ref, ctx, oracle.decoder, truth, oracle.arrays['r1_delays'],
                          oracle.arrays['r1_dopplers'], oracle.arrays['r1_gains'], n)
            if item['atoms'] != list(map(list, zip(truth['l_i'], truth['k_real'], strict=True))):
                raise AssertionError('TRUE_GEOMETRY changed its fixed paths')
        elif not syndrome:
            item = f0
        else:
            branch_ctx = (contexts or {}).get(arm, ctx)
            if arm in ('S', 'A2g'):
                branch = e2.run_branch(branch_ctx, guarded, obs, arrays, 'A2' if arm == 'S' else 'A2g')
            else:
                if arm == 'Z-sel':
                    route = p1.fixed_support(cd, [cd.Path(*p) for p in rows['Z']['atoms']])
                    spec = 'A1'
                else:
                    route, spec = kernels[arm]
                branch = e2.e1d.run_branch(branch_ctx, route, obs, arrays, spec)
            result = branch['result']
            delays = [p.delay for p in result.paths]
            dopplers = [p.doppler for p in result.paths]
            item = record(ref, ctx, branch['decoder'], truth, delays, dopplers, result.gains, n, result=result)
            item['detector_gains'] = p1.gains_record(branch['detector']['gains'])
            if arm == 'Z-sel':
                assert item['atoms'] == rows['Z']['atoms'] and not item['edits']
                item.update({field: rows['Z'][field] for field in ('first_edit_type', 'decision', 'edits')},
                            support_source='Z')
            if arm == 'A2g' and not e2.guard_holds(delays, dopplers, n, 'all'):
                raise AssertionError('A2g accepted a repeated delay')
        timing[arm] = process_time() - stamp
        rows[arm] = item

    row = dict(scenario=ref.SCENARIO, frame=frame, snr_db=snr, syndrome=int(syndrome),
               closure=closure, entering_slots=len(arrays['r1_delays']),
               info_sha=ctx.array_hash(raw['info']), noise_sha=ctx.array_hash(raw['noise']),
               doublet_separations=[float(np.ptp(truth['k_real'][truth['l_i'] == d])) for d in (6, 22)],
               inputs=stage.input_record(raw, obs), truth=stage.truth_record(obs, truth), arms=rows)
    return row, timing
