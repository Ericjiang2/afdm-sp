"""Frozen stages for actual-channel dependence comparisons; heavy work via SSH."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.stats import beta

from experiments.afdm_efficient_information.prior_likelihood import ActualPrior
from experiments.afdm_shared_channel_20261004.production_prior import frozen_components
from experiments.afdm_shared_channel_20261004.common import dump
from . import geometry, protocol
from .core import c2, generate_group

SCHEMA = 'coherent-structure-study/1'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def positive_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f'{label} must be a positive integer')


def validate_config(config):
    if config['schema'] != SCHEMA:
        raise ValueError('unknown study schema')
    seed = config['seed']
    if not isinstance(seed, list) or not seed or any(isinstance(x, bool) or not isinstance(x, int)
            or not 0 <= x < 2**32 for x in seed):
        raise ValueError('seed must be a nonempty list of uint32 integers')
    ts = config['prefixes']
    if not ts or any(isinstance(t, bool) or not isinstance(t, int) or t < 3 for t in ts) or ts != sorted(set(ts)):
        raise ValueError('prefixes must be unique increasing integers >=3')
    for key in ('alpha', 'confidence_alpha'):
        if not 0 < config[key] < 1:
            raise ValueError(f'{key} must lie in (0,1)')
    positive_integer(config['comparison_family_size'], 'comparison family size')
    positive_integer(config['geometry']['probes'], 'geometry probe reservation')
    if config['calibration']['mode'] not in ('iid', 'coherent'):
        raise ValueError('unknown calibration mode')
    if config['evaluation']['modes'] != ['coherent', 'iid']:
        raise ValueError('evaluation modes must be coherent then iid')
    for phase in ('calibration', 'evaluation'):
        block = config[phase]
        positive_integer(block['groups'], phase+' groups')
        if not block['conditions'] or len(config[phase+'_stages']) != len(block['conditions']):
            raise ValueError('one frozen stage per condition required')
        for point in block['conditions']:
            if set(point) != {'mu', 'delta', 'tau', 'noise'} or not np.isfinite(list(point.values())).all():
                raise ValueError('each condition requires finite mu, delta, tau, noise')
            if (point['delta'] < 0 or point['tau'] <= 0 or point['noise'] <= 0
                    or not .22 <= point['mu']-point['delta'] <= point['mu']+point['delta'] <= .42):
                raise ValueError('conditions must stay in the actual positive three-atom branch')
            if phase == 'calibration' and point['delta'] != 0:
                raise ValueError('calibration must contain only null conditions')
    names = config['calibration_stages']+config['evaluation_stages']
    if len(set(names)) != len(names):
        raise ValueError('stage identities must be unique')
    comparisons = sum(p['delta'] > 0 for p in config['evaluation']['conditions'])*len(ts)
    if config['comparison_family_size'] != comparisons:
        raise ValueError('family size must equal positive-delta conditions times prefixes')
    return config


def read_saved(root, config, phase):
    """Read only the frozen stages, with immutable record/registration binding."""
    cohorts, inventory = [], []
    for index, stage in enumerate(config[phase+'_stages']):
        folder = Path(root)/'execution'/stage
        attempt_path, registration_path, records_path = [folder/name for name in
            ('attempt.json', 'registration.json', 'records.json')]
        attempt = json.loads(attempt_path.read_text())
        if attempt['status'] != 'complete':
            raise ValueError(f'incomplete input stage: {stage}')
        bound = attempt['artifact_sha256']
        for path in (registration_path, records_path):
            key = str(path.resolve())
            if path.resolve().is_relative_to(protocol.ROOT):
                key = str(path.resolve().relative_to(protocol.ROOT))
            if bound.get(key) != sha(path):
                raise ValueError(f'damaged or unbound input: {path}')
        registration = json.loads(registration_path.read_text())
        saved = registration['config']
        if saved['study'] != config or saved['phase'] != phase or saved['condition'] != index:
            raise ValueError('saved stage differs from frozen cohort')
        records = json.loads(records_path.read_text())
        modes = [config['calibration']['mode']] if phase == 'calibration' else config['evaluation']['modes']
        expected = [(mode, group) for mode in modes for group in range(config[phase]['groups'])]
        if [(r['mode'], r['group']) for r in records] != expected:
            raise ValueError('missing, duplicate, or reordered independent groups')
        for record in records:
            if set(record['statistics']) != {str(t) for t in config['prefixes']}:
                raise ValueError('missing or unexpected group prefix')
            raw = folder/record['raw_file']
            if raw.parent != folder or not raw.is_file():
                raise ValueError('missing or unsafe saved raw file')
            key = str(raw.resolve())
            if raw.resolve().is_relative_to(protocol.ROOT):
                key = str(raw.resolve().relative_to(protocol.ROOT))
            if bound.get(key) != record['raw_sha256']:
                raise ValueError('raw record and completed-attempt hash disagree')
        cohorts.append(records)
        inventory.extend([dict(path=str(p), sha256=sha(p)) for p in
                          (attempt_path, registration_path, records_path)])
    return cohorts, inventory


def thresholds(cohorts, config):
    result = {}
    for t in config['prefixes']:
        rows = []
        for condition, records in enumerate(cohorts):
            values = [r['statistics'][str(t)] for r in records]
            if any(r['status'] != 'ok' or r['Q'] is None or not np.isfinite(r['Q']) for r in values):
                raise ValueError('calibration failure retained; threshold unavailable for full cohort')
            rank = math.ceil((len(values)+1)*(1-config['alpha']))
            if rank > len(values):
                raise ValueError('insufficient calibration groups for finite conservative threshold')
            threshold = float(np.sort([r['Q'] for r in values])[rank-1])
            rows.append(dict(condition=condition, rank_one_based=rank, groups=len(values), threshold=threshold))
        result[str(t)] = dict(threshold=max(r['threshold'] for r in rows), by_condition=rows,
                              rejection='strict Q > threshold', scope='finite registered null grid only')
    return result


def group_diagnostic(raw, t):
    contrast = raw['conditional_contrast']
    if len(contrast) == 1:
        expected_u = float(contrast[0]@contrast[0])
    else:
        d = contrast[:t]
        total = d.sum(0)
        expected_u = float((total@total-np.sum(d*d))/(t*(t-1)))
    return dict(conditional_expected_U=expected_u,
                conditional_mean_contrast=(contrast[0] if len(contrast) == 1 else contrast[:t].mean(0)).tolist())


def observations(output, *, phase, condition, config, calibrated):
    block = config[phase]
    point = block['conditions'][condition]
    theta = np.array([point['delta'], point['mu'], np.log(point['tau']), np.log(point['noise'])])
    model = ActualPrior(n=4, model='g0', pdp='marginal', order=2, phases=4)
    modes = [block['mode']] if phase == 'calibration' else block['modes']
    tmax = max(config['prefixes'])
    records = []
    generated = channels = replayed = 0
    if calibrated is not None:
        dump(output/'calibration_used.json', calibrated)
    for mode in modes:
        for group in range(block['groups']):
            stem = f'{mode}_{group:05d}'
            seed = [*config['seed'], 1 if phase == 'calibration' else 2,
                    condition, 1 if mode == 'coherent' else 2, group]
            started = time.perf_counter()
            dump(output/(stem+'_started.json'), dict(mode=mode, group=group, seed=seed,
                 reserved_observations=tmax, completed_before=generated))
            # Unexpected generation/I/O failures stop the stage with start/raw evidence retained.
            raw = generate_group(model, theta, tmax, seed, mode)
            generated += tmax
            channels += 1 if mode == 'coherent' else tmax
            replayed += tmax if mode == 'iid' else 0
            generation_seconds = time.perf_counter()-started
            dump(output/(stem+'_generated.json'), dict(mode=mode, group=group,
                 cumulative_new_observations=generated, group_new_observations=tmax,
                 cumulative_unique_channels=channels, cumulative_latent_only_replays=replayed))
            raw_path = output/(stem+'.npz')
            with raw_path.open('xb') as handle:
                # Gaussian/PDP/contrast arrays are exactly replayable from seed,
                # the frozen prior, and saved H. Avoid redundant per-symbol data.
                stored = {key: value for key, value in raw.items()
                          if key not in ('gaussian', 'pdp', 'conditional_contrast')}
                np.savez_compressed(handle, **stored)
            stats, diagnostic = {}, {}
            method_started = time.perf_counter()
            for t in config['prefixes']:
                # A fresh C-contiguous observation prefix fixes the BLAS replay layout.
                stats[str(t)] = c2(np.ascontiguousarray(raw['Y'][:t]))
                diagnostic[str(t)] = group_diagnostic(raw, t)
            method_seconds = time.perf_counter()-method_started
            record = dict(mode=mode, group=group, seed=seed, condition=condition, point=point,
                          raw_file=raw_path.name, raw_sha256=sha(raw_path), statistics=stats,
                          external_diagnostics=diagnostic, actual_observations=tmax,
                          unique_channels=1 if mode == 'coherent' else tmax,
                          latent_only_replayed_channels=tmax if mode == 'iid' else 0,
                          generation_seconds=generation_seconds,
                          statistics_and_diagnostics_seconds=method_seconds,
                          complete_group_seconds=time.perf_counter()-started,
                          timing_scope='generation, raw storage/hash, C2 and external diagnostics; excludes final JSON write')
            dump(output/(stem+'_record.json'), record)
            records.append(record)
    dump(output/'records.json', records)
    failures = sum(s['status'] != 'ok' for r in records for s in r['statistics'].values())
    return dict(phase=phase, condition=condition, groups=len(records), statistic_failures=failures,
                new_observations=generated, unique_channels=channels, latent_only_replayed_channels=replayed,
                generator_calls=len(records), receiver_calls=0, decoder_calls=0, geometry_probes=0,
                accounting='prefix reuse creates no new observations; iid latent replay creates no new observations',
                dependence='independent mode seeds and independent groups; no shared-Y pairing')


def cp_interval(successes, total, alpha):
    if total <= 0 or not 0 <= successes <= total or not 0 < alpha < 1:
        raise ValueError('invalid binomial interval inputs')
    lower = 0. if successes == 0 else float(beta.ppf(alpha/2, successes, total-successes+1))
    upper = 1. if successes == total else float(beta.ppf(1-alpha/2, successes+1, total-successes))
    return [lower, upper]


def proportion(records, t, threshold, alpha):
    values = [r['statistics'][str(t)] for r in records]
    failures = sum(s['status'] != 'ok' for s in values)
    success = sum(s['status'] == 'ok' and s['Q'] > threshold for s in values)
    # Failed decisions remain unknown; worst-case endpoints use the full denominator.
    interval = [cp_interval(success, len(values), alpha)[0],
                cp_interval(success+failures, len(values), alpha)[1]]
    us = [s['U'] for s in values if s['U'] is not None and np.isfinite(s['U'])]
    u_summary = dict(available=len(us), unavailable=len(values)-len(us),
                     mean=float(np.mean(us)) if us else None,
                     standard_deviation=float(np.std(us, ddof=1)) if len(us) > 1 else None,
                     scope='descriptive independent-group U summary; no additional comparison family')
    return dict(groups=len(values), rejects=int(success), failures=failures,
                rejection_rate_bounds=[success/len(values), (success+failures)/len(values)],
                confidence_interval=interval, confidence_alpha=alpha, U=u_summary,
                complete_group_seconds=float(sum(r['complete_group_seconds'] for r in records)))


def summarize(output, root, config):
    calibration, inventory = read_saved(root, config, 'calibration')
    cutoff = thresholds(calibration, config)
    evaluation, more_inventory = read_saved(root, config, 'evaluation')
    inventory += more_inventory
    dump(output/'input_inventory.json', inventory)
    rows, differences = [], []
    for condition, records in enumerate(evaluation):
        point = config['evaluation']['conditions'][condition]
        for t in config['prefixes']:
            threshold = cutoff[str(t)]['threshold']
            by_mode = {mode: [r for r in records if r['mode'] == mode] for mode in ('coherent', 'iid')}
            reports = {mode: proportion(rr, t, threshold, config['confidence_alpha'])
                       for mode, rr in by_mode.items()}
            rows.append(dict(condition=condition, point=point, T=t, threshold=threshold,
                             quantity='size' if point['delta'] == 0 else 'power', modes=reports))
            if point['delta'] > 0:
                adjusted = config['confidence_alpha']/(2*config['comparison_family_size'])
                simultaneous = {mode: proportion(rr, t, threshold, adjusted)
                                for mode, rr in by_mode.items()}
                c, i = simultaneous['coherent'], simultaneous['iid']
                interval = [c['confidence_interval'][0]-i['confidence_interval'][1],
                            c['confidence_interval'][1]-i['confidence_interval'][0]]
                differences.append(dict(condition=condition, T=t, point=point,
                    coherent_minus_iid_rate_bounds=[c['rejection_rate_bounds'][0]-i['rejection_rate_bounds'][1],
                                                   c['rejection_rate_bounds'][1]-i['rejection_rate_bounds'][0]],
                    simultaneous_confidence_interval=interval, modes=simultaneous,
                    method='two independent binomial CP intervals; Bonferroni over 2 modes x 12 comparisons',
                    family_size=config['comparison_family_size']))
    return dict(thresholds=cutoff, point_results=rows, differences=differences,
                confidence_scope='conditional on the independent calibration library; finite registered grid',
                calibration_scope='conservative order statistic; shared null power-array law for both modes',
                dependence='independent seeds between modes; groups, not individual symbols, are uncertainty units',
                input_inventory=inventory, new_observations=0, geometry_probes=0,
                receiver_calls=0, decoder_calls=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True, choices=['geometry', 'calibration', 'evaluation', 'summary'])
    parser.add_argument('--stage', required=True)
    parser.add_argument('--condition', type=int)
    parser.add_argument('--artifact-root', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--wall-seconds', type=int, default=600)
    args = parser.parse_args()
    config = validate_config(json.loads(args.config.read_text()))
    if not args.artifact_root.is_absolute():
        raise ValueError('artifact root must be absolute')
    if args.phase in ('calibration', 'evaluation'):
        if args.condition is None or not 0 <= args.condition < len(config[args.phase]['conditions']):
            raise ValueError('valid condition index required for sampling phase')
        if args.stage != config[args.phase+'_stages'][args.condition]:
            raise ValueError('sampling stage must match its frozen identity')
    elif args.condition is not None:
        raise ValueError('geometry/summary have no condition index')
    # Import the real numerical dependency graph before admission freezes pools.
    frozen_components()
    sources = [args.config.resolve()]
    calibrated = None
    if args.phase == 'evaluation':
        cohorts, inventory = read_saved(args.artifact_root, config, 'calibration')
        calibrated = dict(cohorts=cohorts, input_inventory=inventory)
        sources += [Path(row['path']) for row in inventory]
    elif args.phase == 'summary':
        for phase in ('calibration', 'evaluation'):
            _, inventory = read_saved(args.artifact_root, config, phase)
            sources += [Path(row['path']) for row in inventory]
    allocation = 0
    if args.phase in ('calibration', 'evaluation'):
        modes = 1 if args.phase == 'calibration' else len(config['evaluation']['modes'])
        allocation = config[args.phase]['groups']*modes*max(config['prefixes'])
    registered = dict(study=config, phase=args.phase, condition=args.condition,
                      seed=config['seed'], new_observations=allocation,
                      new_geometry_probes=config['geometry']['probes'] if args.phase == 'geometry' else 0,
                      receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)

    def calculate(output):
        if args.phase == 'geometry':
            return geometry.calculate(output)
        if args.phase == 'summary':
            return summarize(output, args.artifact_root, config)
        calibration_result = None
        if calibrated is not None:
            calibration_result = dict(thresholds=thresholds(calibrated['cohorts'], config),
                                      input_inventory=calibrated['input_inventory'])
        return observations(output, phase=args.phase, condition=args.condition,
                            config=config, calibrated=calibration_result)

    protocol.run(args.stage, registered, sources, calculate,
                 artifact_root=args.artifact_root, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
