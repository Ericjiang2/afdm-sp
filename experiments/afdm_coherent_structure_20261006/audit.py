"""Independent saved-Y audit; no generator, fitting, or production statistic calls.

Run the registered full audit on SSH. --self-test uses tiny deterministic arrays
only. Numerical agreement tolerances are fixed here before inspecting any raw Y.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile

import numpy as np
from scipy.special import betaincinv

from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol

RTOL, ATOL = 5e-10, 5e-11
RAW_KEYS = {'Y', 'seed', 'theta', 'gram', 'weights', 'dopplers', 'H', 'gains', 'pdp_index'}


def compare(saved, expected, label):
    """Expected dictionaries are explicit audited projections of saved records."""
    if isinstance(expected, dict):
        if not isinstance(saved, dict):
            raise AssertionError(f'{label}: expected dictionary')
        for key, value in expected.items():
            if key not in saved:
                raise AssertionError(f'{label}: missing {key}')
            compare(saved[key], value, f'{label}.{key}')
    elif isinstance(expected, (list, tuple)):
        if not isinstance(saved, (list, tuple)) or len(saved) != len(expected):
            raise AssertionError(f'{label}: list shape differs')
        for index, (left, right) in enumerate(zip(saved, expected)):
            compare(left, right, f'{label}[{index}]')
    elif isinstance(expected, float):
        if not isinstance(saved, (int, float)) or not math.isclose(saved, expected, rel_tol=RTOL, abs_tol=ATOL):
            raise AssertionError(f'{label}: {saved!r} != {expected!r}')
    elif saved != expected:
        raise AssertionError(f'{label}: {saved!r} != {expected!r}')


def recompute(y):
    """Independent covariance/Cholesky Q and centered-moment U, using only Y."""
    y = np.asarray(y, dtype=np.complex128)
    if y.ndim != 2 or y.shape[1] != 4 or len(y) < 3:
        raise ValueError('audit requires N4 Y with T>=3')
    result = dict(T=len(y), status='failed', failure=None, Q=None, U=None,
                  mean=None, covariance=None, rank=None, eigenvalues=None, ddof=1)
    if not np.isfinite(y).all():
        result['failure'] = 'nonfinite_observation'
        return result
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            energy = np.square(np.abs(y))
            contrasts = np.column_stack((energy[:, 0]-energy[:, 1], energy[:, 2]-energy[:, 3]))
            mean = np.mean(contrasts, axis=0)
            covariance = np.cov(contrasts, rowvar=False, ddof=1)
            eigenvalues = np.linalg.eigvalsh(covariance)
            rank = int(np.linalg.matrix_rank(covariance))
            result.update(U=float(mean@mean-np.trace(covariance)/len(y)),
                          mean=mean.tolist(), covariance=covariance.tolist(), rank=rank,
                          eigenvalues=eigenvalues.tolist())
            if rank != 2 or eigenvalues[0] <= 0:
                result['failure'] = 'nonpositive_or_rank_deficient_covariance'
                return result
            whitened = np.linalg.solve(np.linalg.cholesky(covariance), mean)
            value = float(len(y)*(whitened@whitened))
            if not np.isfinite(value) or value < 0:
                result['failure'] = 'invalid_quadratic_statistic'
                return result
            result.update(status='ok', Q=value)
    except (FloatingPointError, np.linalg.LinAlgError) as error:
        result['failure'] = type(error).__name__+': '+str(error)
    return result


def interval(successes, total, alpha):
    if not 0 <= successes <= total or total < 1 or not 0 < alpha < 1:
        raise ValueError('invalid independent binomial interval')
    lower = 0. if successes == 0 else float(betaincinv(successes, total-successes+1, alpha/2))
    upper = 1. if successes == total else float(betaincinv(successes+1, total-successes, 1-alpha/2))
    return [lower, upper]


def rates(statistics, threshold, alpha):
    total = len(statistics)
    failures = sum(row['status'] != 'ok' for row in statistics)
    rejects = sum(row['status'] == 'ok' and row['Q'] > threshold for row in statistics)
    available = [row['U'] for row in statistics if row['U'] is not None and np.isfinite(row['U'])]
    return dict(groups=total, rejects=rejects, failures=failures,
                rejection_rate_bounds=[rejects/total, (rejects+failures)/total],
                confidence_interval=[interval(rejects, total, alpha)[0],
                                     interval(rejects+failures, total, alpha)[1]],
                confidence_alpha=alpha,
                U=dict(available=len(available), unavailable=total-len(available),
                       mean=float(np.mean(available)) if available else None,
                       standard_deviation=float(np.std(available, ddof=1)) if len(available) > 1 else None))


def file_key(path):
    path = path.resolve()
    return str(path.relative_to(protocol.ROOT)) if path.is_relative_to(protocol.ROOT) else str(path)


def bound_bytes(path, attempt):
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if attempt['artifact_sha256'].get(file_key(path)) != digest:
        raise ValueError(f'unbound or corrupted artifact: {path}')
    return payload, digest


def load_stage(root, stage, config, phase, condition):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', stage):
        raise ValueError('unsafe input stage name')
    folder = root/'execution'/stage
    attempt_path = folder/'attempt.json'
    attempt = json.loads(attempt_path.read_text())
    compare(attempt, dict(status='complete', exit_code=0), str(attempt_path))
    loaded, paths = {}, [attempt_path]
    names = ['registration', 'results'] + ([] if phase == 'summary' else ['records'])
    for name in names:
        path = folder/(name+'.json')
        loaded[name] = json.loads(bound_bytes(path, attempt)[0])
        paths.append(path)
    compare(loaded['registration']['config'], dict(study=config, phase=phase, condition=condition), stage)
    return dict(folder=folder, attempt=attempt, paths=paths, **loaded)


def audit_cohort(stage, config, phase, condition, inventory, group_results):
    records = stage['records']
    modes = [config['calibration']['mode']] if phase == 'calibration' else config['evaluation']['modes']
    expected_ids = [(mode, group) for mode in modes for group in range(config[phase]['groups'])]
    if [(row['mode'], row['group']) for row in records] != expected_ids:
        raise ValueError('missing, duplicated, or reordered raw groups')
    point = config[phase]['conditions'][condition]
    tmax = max(config['prefixes'])
    output = {mode: {str(t): [] for t in config['prefixes']} for mode in modes}
    failures = channels = replays = 0
    for record in records:
        mode, group = record['mode'], record['group']
        name = f'{mode}_{group:05d}.npz'
        seed = [*config['seed'], 1 if phase == 'calibration' else 2,
                condition, 1 if mode == 'coherent' else 2, group]
        count = 1 if mode == 'coherent' else tmax
        compare(record, dict(condition=condition, point=point, raw_file=name, seed=seed,
                             actual_observations=tmax, unique_channels=count,
                             latent_only_replayed_channels=tmax if mode == 'iid' else 0), name)
        if set(record['statistics']) != {str(t) for t in config['prefixes']}:
            raise ValueError('saved group prefixes differ from registration')
        path = stage['folder']/name
        payload, digest = bound_bytes(path, stage['attempt'])
        compare(record['raw_sha256'], digest, name+'.sha256')
        inventory.append(dict(path=str(path), sha256=digest, md5=hashlib.md5(payload).hexdigest(),
                              bytes=len(payload)))
        with np.load(io.BytesIO(payload), allow_pickle=False) as raw:
            if set(raw.files) != RAW_KEYS:
                raise ValueError(f'{name}: raw schema differs')
            if (raw['Y'].shape != (tmax, 4) or raw['Y'].dtype != np.dtype('complex128')
                    or raw['H'].shape != (count, 4) or raw['gains'].shape != (count, 2)
                    or raw['pdp_index'].shape != (count,) or raw['gram'].shape != (2, 2)
                    or raw['weights'].shape != (12, 2) or raw['dopplers'].shape != (2,)):
                raise ValueError(f'{name}: raw dimensions differ')
            compare(raw['seed'].tolist(), seed, name+'.seed')
            compare(raw['theta'].tolist(), [point['delta'], point['mu'], math.log(point['tau']),
                                           math.log(point['noise'])], name+'.theta')
            compare(raw['dopplers'].tolist(), [point['mu']-point['delta'], point['mu']+point['delta']],
                    name+'.dopplers')
            statistics = {}
            for t in config['prefixes']:
                value = recompute(raw['Y'][:t])
                compare(record['statistics'][str(t)], value, f'{name}.T{t}')
                statistics[str(t)] = value
                output[mode][str(t)].append(value)
                failures += value['status'] != 'ok'
        group_results.append(dict(phase=phase, condition=condition, mode=mode, group=group,
                                  raw_sha256=digest, statistics=statistics))
        channels += count
        replays += tmax if mode == 'iid' else 0
    compare(stage['registration']['config'], dict(new_observations=len(records)*tmax,
            new_geometry_probes=0, receiver_calls=0, decoder_calls=0, new_confirmation_stream=False), 'allocation')
    compare(stage['results'], dict(groups=len(records), statistic_failures=failures,
            new_observations=len(records)*tmax, unique_channels=channels,
            latent_only_replayed_channels=replays, generator_calls=len(records),
            geometry_probes=0, receiver_calls=0, decoder_calls=0), 'accounting')
    return output


def calculate(output, config, stages, summary):
    inventory, group_results = [], []
    calibration = [audit_cohort(stage, config, 'calibration', index, inventory, group_results)
                   for index, stage in enumerate(stages['calibration'])]
    cutoffs = {}
    for t in config['prefixes']:
        rows = []
        for index, cohort in enumerate(calibration):
            values = cohort[config['calibration']['mode']][str(t)]
            if any(row['status'] != 'ok' for row in values):
                raise ValueError('calibration failure: no admitted threshold')
            rank = math.ceil((len(values)+1)*(1-config['alpha']))
            if not 1 <= rank <= len(values):
                raise ValueError('unavailable finite calibration threshold')
            rows.append(dict(condition=index, rank_one_based=rank, groups=len(values),
                             threshold=sorted(row['Q'] for row in values)[rank-1]))
        cutoffs[str(t)] = dict(threshold=max(row['threshold'] for row in rows), by_condition=rows)
    points, differences = [], []
    for index, stage in enumerate(stages['evaluation']):
        saved_calibration = json.loads(bound_bytes(stage['folder']/'calibration_used.json', stage['attempt'])[0])
        compare(saved_calibration['thresholds'], cutoffs, 'evaluation.calibration_used')
        cohort = audit_cohort(stage, config, 'evaluation', index, inventory, group_results)
        point = config['evaluation']['conditions'][index]
        for t in config['prefixes']:
            threshold = cutoffs[str(t)]['threshold']
            reports = {mode: rates(cohort[mode][str(t)], threshold, config['confidence_alpha'])
                       for mode in config['evaluation']['modes']}
            points.append(dict(condition=index, point=point, T=t, threshold=threshold,
                               quantity='size' if point['delta'] == 0 else 'power', modes=reports))
            if point['delta'] > 0:
                adjusted = config['confidence_alpha']/(2*config['comparison_family_size'])
                simultaneous = {mode: rates(cohort[mode][str(t)], threshold, adjusted)
                                for mode in config['evaluation']['modes']}
                coherent, iid = simultaneous['coherent'], simultaneous['iid']
                differences.append(dict(condition=index, T=t, point=point,
                    coherent_minus_iid_rate_bounds=[coherent['rejection_rate_bounds'][0]-iid['rejection_rate_bounds'][1],
                                                   coherent['rejection_rate_bounds'][1]-iid['rejection_rate_bounds'][0]],
                    simultaneous_confidence_interval=[coherent['confidence_interval'][0]-iid['confidence_interval'][1],
                                                      coherent['confidence_interval'][1]-iid['confidence_interval'][0]],
                    modes=simultaneous, family_size=config['comparison_family_size']))
    expected = dict(thresholds=cutoffs, point_results=points, differences=differences,
                    new_observations=0, geometry_probes=0, receiver_calls=0, decoder_calls=0)
    compare(summary['results'], expected, 'summary')
    compare(summary['registration']['config'], dict(new_observations=0, new_geometry_probes=0), 'summary.allocation')
    failures = sum(value['status'] != 'ok' for row in group_results for value in row['statistics'].values())
    dump(output/'raw_inventory.json', inventory)
    dump(output/'recomputed_groups.json', group_results)
    dump(output/'recomputed_summary.json', expected)
    return dict(verdict='PASS', audited_raw_groups=len(inventory), audited_prefix_statistics=len(group_results)*len(config['prefixes']),
                source_observations=sum(config[phase]['groups']*len(config[phase]['conditions'])*max(config['prefixes'])*
                                        (1 if phase == 'calibration' else len(config['evaluation']['modes']))
                                        for phase in ('calibration', 'evaluation')),
                statistic_failures=failures, superiority_claim_admissible=failures == 0,
                numerical_tolerance=dict(rtol=RTOL, atol=ATOL), new_observations=0, geometry_probes=0,
                receiver_calls=0, decoder_calls=0,
                scope='independent saved-Y Q/U, thresholds, group counts and binomial CI; no latent replay or new Y')


def self_test():
    powers = np.array([[4, 1, 2, 1], [2, 1, 5, 1], [1, 3, 1, 2], [4, 2, 3, 1]], float)
    compare(recompute(np.sqrt(powers)), dict(status='ok', Q=282/133, U=1.), 'rational fixture')
    compare(recompute(np.ones((4, 4))), dict(status='failed', rank=0, Q=None, U=0.), 'singular fixture')
    compare(recompute(np.full((4, 4), np.nan)), dict(status='failed', failure='nonfinite_observation'), 'invalid fixture')
    compare(interval(0, 4, .05), [0., 1-.025**.25], 'CP lower boundary')
    compare(interval(4, 4, .05), [.025**.25, 1.], 'CP upper boundary')
    report = rates([dict(status='ok', Q=2., U=1.), dict(status='failed', Q=None, U=None)], 1., .05)
    compare(report, dict(groups=2, rejects=1, failures=1, rejection_rate_bounds=[.5, 1.]), 'failure denominator')
    try:
        compare(dict(Q=2.), dict(Q=1.), 'deliberate corruption')
    except AssertionError:
        pass
    else:
        raise AssertionError('corruption was not rejected')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'bound.bin'
        path.write_bytes(b'fixture')
        attempt = dict(artifact_sha256={file_key(path): hashlib.sha256(b'fixture').hexdigest()})
        bound_bytes(path, attempt)
        path.write_bytes(b'corrupt')
        try:
            bound_bytes(path, attempt)
        except ValueError:
            pass
        else:
            raise AssertionError('raw byte corruption was not rejected')
    print('PASS: eight deterministic audit contracts; zero generated observations')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--summary-stage')
    parser.add_argument('--stage', default='raw_audit_v1')
    parser.add_argument('--wall-seconds', type=int, default=1200)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.artifact_root is None or not args.artifact_root.is_absolute() or args.config is None or not args.summary_stage:
        parser.error('registered audit requires absolute --artifact-root, --config and --summary-stage')
    config = json.loads(args.config.read_text())
    if config['schema'] != 'coherent-structure-study/1':
        raise ValueError('unsupported study schema')
    comparisons = sum(point['delta'] > 0 for point in config['evaluation']['conditions'])*len(config['prefixes'])
    if config['comparison_family_size'] != comparisons:
        raise ValueError('comparison family differs from frozen grid')
    stages = {phase: [load_stage(args.artifact_root, name, config, phase, index)
                      for index, name in enumerate(config[phase+'_stages'])]
              for phase in ('calibration', 'evaluation')}
    summary = load_stage(args.artifact_root, args.summary_stage, config, 'summary', None)
    sources = [args.config.resolve(), *summary['paths']]
    for cohort in stages.values():
        for stage in cohort:
            sources.extend(stage['paths'])
    registration = dict(study=config, phase='independent_raw_audit', seed=config['seed'],
                        new_observations=0, new_geometry_probes=0, receiver_calls=0, decoder_calls=0,
                        new_confirmation_stream=False, summary_stage=args.summary_stage,
                        numerical_tolerance=dict(rtol=RTOL, atol=ATOL))

    def callback(output):
        return calculate(output, config, stages, summary)

    protocol.run(args.stage, registration, sources, callback,
                 artifact_root=args.artifact_root, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
