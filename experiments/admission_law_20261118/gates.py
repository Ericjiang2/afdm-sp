# Source: sigma2_dd_20261118/qualify.py (G1 reader/comparator); select only N and both arms, which the original cannot do.
"""Run only synthetic or explicitly bounded historical qualification."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
SLOT = HERE.parent / 'slot_mismatch_20261019'

CAP = 8
G1_FRAMES = (10000, 10001, 10998, 10999)
SNRS = tuple(range(450, 801, 50))
G1_CELL = ('G', .3)
FROZEN_COMMIT = '9b633ce9df020158d51621600d7b6eab3b65395d'
ENV_FIELDS = ('hostname', 'machine', 'numpy', 'scipy', 'torch', 'torch_num_threads', 'torch_num_interop_threads')
SMOKE_KEYS = tuple((scenario, rho, snr, 7800 + i)
                   for i, (scenario, rho, snr) in enumerate(
                       (s, r, n) for s in ('G', 'U') for r in (.3, .5) for n in (450, 500, 550)))
WORKERS = 4
TARGET_COUNT = 8106


def load(frozen_slot):
    sys.path.insert(0, str(frozen_slot))
    import qualify_v2 as q

    return q, *q.load()


def read_reference(archive, frozen_slot, study):
    q, ctx = study[:2]
    config = json.loads((archive / 'RUN_CONFIG.json').read_text())['_config']
    completion = json.loads((archive / 'main_receipt.json').read_text())
    if config['commit'] != FROZEN_COMMIT or completion['_config']['commit'] != FROZEN_COMMIT:
        raise ValueError('Wrong frozen archive commit')
    if completion['completed_shards'] != 200 or completion['reason'] is not None:
        raise ValueError('Incomplete slot-mismatch main run')
    for name, digest in config['own_sha256'].items():
        if hashlib.sha256((frozen_slot / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Frozen slot-mismatch source mismatch: {name}')
    if config['source_md5'] != ctx.source_md5 or config['source_paths'] != ctx.source_paths:
        raise ValueError('Frozen loaded source hashes or paths differ')
    if config['codelay_source_sha256'] != q.CODELAY_SHA:
        raise ValueError('Frozen CODELAY source differs')
    for name in ENV_FIELDS:
        if config['environment'][name] != ctx.environment[name]:
            raise ValueError(f'Frozen runtime differs at {name}')
    manifest = (archive / 'REMOTE_ROWS_MD5.txt').read_bytes()
    entries = {name: digest for digest, name in map(str.split, manifest.decode().splitlines())}
    records, shards = {}, {}
    for frame in G1_FRAMES:
        shard = (frame - config['frame_range'][0]) // config['frames_per_shard']
        name = f'rows_shard{shard:03d}.jsonl.gz'
        if name in shards:
            continue
        path = archive / name
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        if digest != entries[name]:
            raise ValueError(f'Archive MD5 mismatch: {path}')
        shards[name] = digest
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                # Frozen main_v2 writes family first with compact separators.
                if not line.startswith('{"family":"N",'):
                    continue
                row = json.loads(line)
                f, snr = row['frame'], row['snr_centi_db']
                if f in G1_FRAMES and (row['scenario'], row['rho']) == G1_CELL:
                    key = (f, snr)
                    if key in records:
                        raise ValueError(f'Duplicate N reference key: {key}')
                    cap = row['s'][str(CAP)]
                    records[key] = dict(f0=cap['f0'], **{name: cap['arms'].get(name) for name in ('A1c', 'A2')})
    expected = {(i, s) for i in G1_FRAMES for s in SNRS}
    if set(records) != expected:
        raise ValueError('Unexpected N reference key coverage')
    return records, dict(manifest_sha256=hashlib.sha256(manifest).hexdigest(), shard_md5=shards)


def compare_fields(actual, expected):
    if actual is None or expected is None:
        return [] if actual is expected else ['branch_presence']
    # Same round-trip JSON comparison as sigma2-dd G1, including sign of zero.
    return sorted(name for name in actual.keys() | expected.keys()
                  if name not in actual or name not in expected
                  or json.dumps(actual[name], sort_keys=True) != json.dumps(expected[name], sort_keys=True))


def g1(study, archive, frozen_slot):
    from main_v2 import cap_record
    from replay import observed_kernel, summarize_unit

    q, ctx, variant, full, closed, _ = study
    reference, provenance = read_reference(archive, frozen_slot, study)
    scenario, rho = G1_CELL
    rows = []
    for frame in G1_FRAMES:
        base, diag = q.sm.p1ctx.base(ctx, scenario, rho, frame)
        for snr in SNRS:
            _, actual, truth = q.sm.gd.observe(ctx, base, diag, rho, snr)
            obs, _ = q.observe_only(actual, unknown=True)
            observations = dict(A2={}, A1c={})
            observed_full = observed_kernel(full, observations['A2'])
            observed_closed = observed_kernel(closed, observations['A1c'])
            nominated = q.sm.n_nominated(ctx, variant, obs)
            saved = cap_record(q, ctx, variant, observed_full, observed_closed, obs, truth, CAP, nominated)
            parity = {}
            if saved['triggered']:
                logs = {name: data['log'] for name, data in observations.items()}
                traces = {name: data['trace'] for name, data in observations.items()}
                summary = summarize_unit(logs, traces, truth, len(obs['y']))
                json.dumps(summary, allow_nan=False)
                parity = {name: data['first_only_parity'] for name, data in observations.items()}
            got = dict(f0=saved['f0'], **{name: saved['arms'].get(name) for name in ('A1c', 'A2')})
            mismatches = {name: compare_fields(got[name], reference[frame, snr][name]) for name in got}
            rows.append(dict(frame=frame, snr_centi_db=snr, receiver_exact=not any(mismatches.values()),
                             mismatches=mismatches, first_only_parity=parity))
    triggers = sum(bool(row['first_only_parity']) for row in rows)
    passed = triggers and all(row['receiver_exact'] and all(row['first_only_parity'].values()) for row in rows)
    return dict(status='PASS' if passed else 'FAIL', keys=len(rows), triggered=triggers,
                per_key=rows, **provenance)


def improvement(b, Q):
    return np.vdot(b, np.linalg.solve(Q, b)).real


def g2(study):
    from physical import daft
    from replay import first_exchange

    _, _, _, full, closed, _ = study
    n = 12
    samples = np.arange(n)
    x_time = (1.0 + (samples % 3) * .25) * np.exp(.6j * samples) / np.sqrt(n)
    x = daft(x_time, 0., 0.)
    v = np.linspace(.007, .026, n)
    u, ridge = float(v.sum()), .13
    E = float(np.vdot(x_time, x_time).real)
    T = E + u + ridge

    def response(delay, doppler):
        return np.roll(x_time, delay) * np.exp(2j * np.pi * doppler * samples / n)

    anchor_nu = .125
    anchor = response(0, anchor_nu)
    Y = (.53 + .37j) * anchor + (.13 - .24j) * response(1, -.125)
    rows = []
    for name, kernel, mode in (('A2', full, 'diag'), ('A1c', closed, 'full')):
        paths = [kernel.Path(0, anchor_nu), kernel.Path(1, -.125)]
        report, _ = first_exchange(kernel, Y, x, v, paths, c1=0., c2=0., ridge=ridge,
                                   max_delay=1, doppler_min=-.5, doppler_max=.5, grid_step=.5,
                                   gamma_mode=mode, strategy='compact')
        h = complex(*report['h_tilde'][0])
        for nu in (0., .5):
            logged = next(p for p in report['slots'][1]['P'] if p['delay'] == 0 and p['doppler'] == nu)
            candidate = response(0, nu)
            kappa = np.vdot(anchor, candidate) / E
            D = np.mean(np.exp(2j * np.pi * (nu-anchor_nu) * samples / n))
            B = np.column_stack([anchor, candidate])
            Q = B.conj().T @ B + (u + ridge) * np.eye(2)
            if mode == 'full':
                Q[0, 1] += u * D
                Q[1, 0] += u * D.conjugate()
            model_b = T * h * np.array([1., kappa.conjugate()])
            measured_b = B.conj().T @ Y
            expected_model = improvement(model_b, Q) - abs(model_b[0]) ** 2 / Q[0, 0].real
            expected_gain = improvement(measured_b, Q) - abs(measured_b[0]) ** 2 / Q[0, 0].real
            rows.append(dict(arm=name, doppler=nu, modeled_abs_error=float(abs(logged['modeled_gain'] - expected_model)),
                             measured_abs_error=float(abs(logged['measured_gain'] - expected_gain))))
    model_error = max(row['modeled_abs_error'] for row in rows)
    measured_error = max(row['measured_abs_error'] for row in rows)
    return dict(status='PASS' if max(model_error, measured_error) <= 1e-12 else 'FAIL',
                modeled_max_abs_error=model_error, measured_max_abs_error=measured_error, comparisons=rows)


def g3():
    from replay import model_outputs, subset_checks

    P = dict(anchor_count=1, abs_D=.90, abs_kappa_minus_D=.05, other_coherence=.15)
    N = dict(entering_coherence=.15)
    expected_checks = dict(E_positive=True, u_positive=True, lambda_positive=True, K_A2_positive=True,
                           K_A1c_positive=True, legal_P=True, legal_N=True, one_surviving_anchor=True,
                           D_ge_090=True, kappa_minus_D_le_005=True, P_other_coherence_le_015=True,
                           N_entering_coherence_le_015=True)
    cases = [
        (1., 1., 1., 1., 1., P, N, ()),
        (3., .2, .4, 1., 4., dict(P, abs_D=1.), N, ()),
        (2., .1, .01, .5, .25, dict(P, other_coherence=0.), N, ()),
        (1., 1., 1., 1., 1., dict(P, abs_kappa_minus_D=0.), N, ()),
        (1., 1., 1., 1., 1., P, dict(N, entering_coherence=0.), ()),
        (0., 0., 0., 0., 0., P, N, ('E_positive', 'u_positive', 'lambda_positive', 'K_A2_positive', 'K_A1c_positive')),
        (1., 1., 1., 1., 1., None, None, ('legal_P', 'legal_N', 'one_surviving_anchor', 'D_ge_090',
                                         'kappa_minus_D_le_005', 'P_other_coherence_le_015', 'N_entering_coherence_le_015')),
        (1., 1., 1., 1., 1., dict(P, anchor_count=2), N, ('one_surviving_anchor',)),
        (1., 1., 1., 1., 1., dict(P, abs_D=.899, abs_kappa_minus_D=.051), N, ('D_ge_090', 'kappa_minus_D_le_005')),
        (1., 1., 1., 1., 1., dict(P, other_coherence=.151), dict(N, entering_coherence=.151),
         ('P_other_coherence_le_015', 'N_entering_coherence_le_015')),
    ]
    rows = []
    for i, (*inputs, failures) in enumerate(cases, 1):
        checks = subset_checks(*inputs)
        expected = dict(expected_checks, **dict.fromkeys(failures, False))
        rows.append(dict(case=i, expected=expected, checks=checks, match=checks == expected))
    passed = sum(all(row['checks'].values()) for row in rows)
    decisions = []
    for p, n, o, expected in ((2., 1., .5, 'P'), (1., 2., .5, 'N'), (1., 1., 0., 'O'),
                              (1e-8, -1., -1., 'O'), (None, None, None, 'O')):
        maxima = {key: dict(net_gain=gain) if gain is not None else None
                  for key, gain in zip(('P', 'N', 'O'), (p, n, o))}
        result = model_outputs(maxima, 1.)
        decisions.append(dict(expected=expected, actual=result['predicted_class']))
    exact = all(row['expected'] == row['actual'] for row in decisions)
    return dict(status='PASS' if passed == 5 and exact and all(row['match'] for row in rows) else 'FAIL',
                subset_passes=passed, subset_failures=len(rows)-passed, cases=rows, decision_cases=decisions)


def init_smoke(frozen_slot):
    global smoke_study
    smoke_study = load(frozen_slot)


def smoke_unit(key):
    from replay import first_exchange_from_f0

    study = smoke_study
    q, ctx, variant = study[:3]
    scenario, rho, snr, frame = key
    start = time.process_time()
    obs, truth = q.sm.make_unit(ctx, scenario, rho, snr, frame)
    _, arrays, syndrome, _ = q.sm.f0_state(ctx, variant, obs, CAP)
    f0_seconds = time.process_time() - start
    payload = None
    branch_seconds = 0.
    if syndrome:
        start = time.process_time()
        unit = first_exchange_from_f0(study, obs, arrays, truth)
        unit.update(family='M', scenario=scenario, rho=rho, snr_centi_db=snr, frame=frame, cap=CAP)
        payload = (json.dumps(unit, separators=(',', ':'), allow_nan=False) + '\n').encode()
        branch_seconds = time.process_time() - start
    return dict(key=key, f0_cpu_seconds=f0_seconds, first_exchange_cpu_seconds=branch_seconds,
                triggered=bool(syndrome)), payload


def smoke(out, frozen_slot):
    start = time.perf_counter()
    rows = []
    payload_path = out.with_name('smoke_historical.jsonl.gz')
    zip_cpu_seconds = 0.
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn'),
                             initializer=init_smoke, initargs=(frozen_slot,)) as pool, gzip.open(payload_path, 'xb') as handle:
        for row, data in pool.map(smoke_unit, SMOKE_KEYS):
            rows.append(row)
            if data is not None:
                zip_start = time.process_time()
                handle.write(data)
                zip_cpu_seconds += time.process_time() - zip_start
    triggers = sum(row['triggered'] for row in rows)
    if not triggers:
        return dict(status='FAIL', keys=len(rows), triggered=triggers, per_key=rows)
    f0 = sum(row['f0_cpu_seconds'] for row in rows if row['triggered']) / triggers
    branches = (sum(row['first_exchange_cpu_seconds'] for row in rows) + zip_cpu_seconds) / triggers
    estimate = TARGET_COUNT * (f0 + branches) / 3600
    allowance = 1.3 * estimate
    return dict(status='PASS', keys=len(rows), triggered=triggers, per_key=rows,
                average_triggered_generation_observe_f0_cpu_seconds=f0,
                average_triggered_exchange_logging_cpu_seconds=branches,
                projection_count=TARGET_COUNT, core_hours=estimate, core_hours_plus_30pct=allowance,
                suggested_core_hour_cap=math.ceil(allowance), wall_seconds=time.perf_counter()-start,
                historical_payload=str(payload_path), historical_payload_bytes=payload_path.stat().st_size,
                historical_payload_md5=hashlib.md5(payload_path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('g1', 'g2', 'g3', 'smoke'))
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--frozen-slot', type=Path, default=SLOT)
    parser.add_argument('--archive', type=Path, default=SLOT / 'out' / 'main_20261118')
    args = parser.parse_args()
    config = dict(mode=args.mode, own_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in sorted(HERE.glob('*.py'))})
    if args.mode != 'g3':
        # The frozen inventory enumerates modules already imported from this
        # checkout. Load the receiver before importing any observation code.
        study = load(args.frozen_slot)
        q, ctx = study[:2]
        config.update(environment=ctx.environment, source_md5=ctx.source_md5, source_paths=ctx.source_paths,
                      codelay_sha256=q.CODELAY_SHA, frozen_slot=str(args.frozen_slot))
    sys.path.insert(0, str(HERE.parent / 'sigma2_dd_20261118'))
    from receipts import write_receipt

    if args.mode == 'g1':
        config.update(frozen_commit=FROZEN_COMMIT, family='N', frame=G1_FRAMES, cap=CAP, cell=G1_CELL,
                      snr_centi_db=SNRS, archive=str(args.archive), comparison='exact round-trip JSON')
        try:
            result = g1(study, args.archive, args.frozen_slot)
        except Exception as error:
            write_receipt(args.out, config, dict(status='ERROR', error_type=type(error).__name__, error=str(error)))
            raise
    elif args.mode == 'g2':
        config.update(tolerance=1e-12)
        result = g2(study)
    elif args.mode == 'g3':
        result = g3()
    else:
        config.update(family='M', cap=CAP, keys=SMOKE_KEYS, workers=WORKERS)
        result = smoke(args.out, args.frozen_slot)
    write_receipt(args.out, config, result)
    print(args.mode, result['status'], flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
