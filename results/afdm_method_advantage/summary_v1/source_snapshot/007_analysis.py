"""Bound saved-study analysis: no sampling, nuisance fitting, or score evaluation."""
import argparse
import gzip
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import special, stats

from experiments.afdm_efficient_information.audit import loaded_project_sources, sha
from experiments.afdm_method_advantage.protocol import ROOT, ARTIFACT, dump, run

CONFIG_PATH = ARTIFACT/'METHOD_CONFIG.json'
FIT_FOR_METHOD = dict(full_score='mle', full_raw='mle', moment_score='m14',
                      moment_raw='m14', moment_j='m14', second_moment=None)
PRIMARY_ROLES = {'within_branch', 'finite_separation', 'original_weak_signal'}


def read_json(path):
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def records_path(folder):
    candidates = [Path(folder)/name for name in ('records.json', 'records.json.gz')]
    present = [path for path in candidates if path.exists()]
    if len(present) != 1 or not present[0].is_file():
        raise ValueError(f'exactly one records.json or records.json.gz is required: {folder}')
    return present[0]


def finite(value, label, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: a finite number is required')
    if nonnegative and value < 0:
        raise ValueError(f'{label}: negative value')
    return float(value)


def wilson(successes, total, confidence=.95):
    if type(total) is not int or type(successes) is not int or total <= 0 or not 0 <= successes <= total or not 0 < confidence < 1:
        raise ValueError('valid binomial count and confidence required')
    z = float(special.ndtri((1+confidence)/2))
    p, denominator = successes/total, 1+z*z/total
    center = (p+z*z/(2*total))/denominator
    half = z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/denominator
    return dict(lower=max(0., center-half), upper=min(1., center+half), confidence=confidence)


def cp_bounds(successes, total, tail):
    if type(total) is not int or type(successes) is not int or total <= 0 or not 0 <= successes <= total or not 0 < tail < .5:
        raise ValueError('valid binomial count and one-tail error required')
    lower = 0. if successes == 0 else float(stats.beta.ppf(tail, successes, total-successes+1))
    upper = 1. if successes == total else float(stats.beta.ppf(1-tail, successes+1, total-successes))
    return dict(lower=lower, upper=upper)


def paired_interval(candidate, baseline, family_size=84, confidence=.95):
    candidate, baseline = np.asarray(candidate, bool), np.asarray(baseline, bool)
    if candidate.ndim != 1 or candidate.shape != baseline.shape or not len(candidate) or type(family_size) is not int or family_size < 1:
        raise ValueError('aligned nonempty paired decisions and positive family size required')
    plus = int(np.sum(candidate & ~baseline))
    minus = int(np.sum(~candidate & baseline))
    total = len(candidate)
    tail = (1-confidence)/(4*family_size)
    positive, negative = cp_bounds(plus, total, tail), cp_bounds(minus, total, tail)
    return dict(groups=total, discordant_plus=plus, discordant_minus=minus,
                concordant=total-plus-minus, difference=(plus-minus)/total,
                lower=positive['lower']-negative['upper'], upper=positive['upper']-negative['lower'],
                plus_probability=positive, minus_probability=negative, tail_probability=tail,
                family_size=family_size, simultaneous_confidence=confidence,
                construction='four Clopper-Pearson tails per paired comparison; Bonferroni over the registered family')


def rank_threshold(values, alpha):
    """None calibration values are declared failures ranked as positive infinity."""
    if not values or not 0 < alpha < 1:
        raise ValueError('nonempty calibration and alpha in (0,1) required')
    numbers = [math.inf if value is None else finite(value, 'calibration statistic') for value in values]
    k = math.ceil((len(numbers)+1)*(1-alpha))
    threshold = sorted(numbers)[k-1] if k <= len(numbers) else math.inf
    return dict(groups=len(numbers), order_index_one_based=k, failed=sum(value is None for value in values),
                threshold=None if math.isinf(threshold) else threshold,
                finite_threshold=bool(math.isfinite(threshold)), comparison='strictly greater',
                failure_sort_value='positive infinity, encoded as null with finite_threshold=false')


def apply_threshold(values, threshold):
    failed = np.asarray([value is None for value in values], bool)
    rejected = np.zeros(len(values), bool)
    if threshold['finite_threshold']:
        cutoff = finite(threshold['threshold'], 'frozen threshold')
        for index, value in enumerate(values):
            if value is not None:
                rejected[index] = finite(value, 'evaluation statistic') > cutoff
    else:
        for value in values:
            if value is not None:
                finite(value, 'evaluation statistic')
    return rejected, failed


def failure_difference_bounds(candidate, baseline, candidate_failed, baseline_failed):
    c, b = np.asarray(candidate, int), np.asarray(baseline, int)
    cf, bf = np.asarray(candidate_failed, int), np.asarray(baseline_failed, int)
    if c.shape != b.shape or c.shape != cf.shape or c.shape != bf.shape or not len(c):
        raise ValueError('aligned paired failure outcomes required')
    return dict(lower=float(np.mean(c-b-bf)), upper=float(np.mean(c+cf-b)),
                scope='deterministic bounds if every failed method could return either decision; not a confidence interval')


def validate_config(config):
    repeats, methods = config['repeats'], config['methods']
    if not repeats or len(set(repeats)) != len(repeats) or any(type(r) is not int or r <= 0 for r in repeats):
        raise ValueError('unique positive registered repeat counts required')
    if len(set(methods)) != len(methods) or any(method not in FIT_FOR_METHOD for method in methods):
        raise ValueError('unknown or duplicate registered method')
    for field in ('calibration_groups', 'evaluation_groups'):
        if type(config[field]) is not int or config[field] <= 0:
            raise ValueError('positive registered group count required')
    if not 0 < config['alpha'] < 1:
        raise ValueError('invalid alpha')
    for population in ('null_points', 'evaluation_points'):
        points = config[population]
        if not points or len({point_key(point) for point in points}) != len(points):
            raise ValueError('nonempty unique scientific points required')
        for point in points:
            for name in ('mu', 'tau', 'sigma2', 'delta'):
                finite(point[name], 'scientific point '+name)
            if point['tau'] <= 0 or point['sigma2'] <= 0 or point['delta'] < 0:
                raise ValueError('positive scales and nonnegative separation required')
    for point in config['null_points']:
        if point['delta'] != 0 or point['role'] != 'grid_null':
            raise ValueError('calibration consists only of the public null grid')
    primary = []
    for index, point in enumerate(config['evaluation_points']):
        if point['role'] in ('grid_null', 'off_grid_null'):
            if point['delta'] != 0:
                raise ValueError('a null role must have zero separation')
        elif point['role'] in PRIMARY_ROLES and point['delta'] > 0:
            primary.append(index)
        else:
            raise ValueError('unregistered evaluation role; offgrid additions must be explicit null stress points')
    comparison = config['comparison']
    if (not comparison['baselines'] or len(set(comparison['baselines'])) != len(comparison['baselines'])
            or comparison['primary_candidate'] in comparison['baselines']):
        raise ValueError('unique baselines distinct from candidate required')
    if not 0 < comparison['confidence'] < 1:
        raise ValueError('invalid comparison confidence')
    if comparison['primary_candidate'] not in methods or any(x not in methods for x in comparison['baselines']):
        raise ValueError('comparison methods are absent')
    expected = len(primary)*len(repeats)*len(comparison['baselines'])
    if comparison['family_size'] != expected:
        raise ValueError(f'family size must cover every nonnull point/R/baseline: expected {expected}')
    grid_keys = {point_key(point) for point in config['null_points']}
    observed_grid = [point_key(point) for point in config['evaluation_points'] if point['role'] == 'grid_null']
    if len(observed_grid) != len(grid_keys) or set(observed_grid) != grid_keys:
        raise ValueError('every calibration null point needs exactly one independent grid-null evaluation')
    return primary


def point_key(point):
    return tuple(point[name] for name in ('mu', 'tau', 'sigma2', 'delta'))


def compatible_config(source, current):
    for key in ('seed', 'repeats', 'calibration_groups', 'evaluation_groups', 'alpha',
                'null_points', 'methods', 'method_config', 'comparison'):
        if source[key] != current[key]:
            raise ValueError(f'source stage changed the frozen configuration field {key}')
    previous = source['evaluation_points']
    if previous != current['evaluation_points'][:len(previous)]:
        raise ValueError('evaluation point updates may only append explicit offgrid null stress points')
    for point in current['evaluation_points'][len(previous):]:
        if point['role'] != 'off_grid_null' or point['delta'] != 0:
            raise ValueError('unregistered post-source alternative extension')


def discover_inputs(artifact, config, excluded_stage=None):
    """Enumerate metadata, never infer scientific membership from a filename."""
    validate_config(config)
    bindings, excluded, seen = [], [], set()
    for folder in sorted(Path(artifact).iterdir()):
        if not folder.is_dir() or folder.name == excluded_stage:
            continue
        if not any((folder/name).exists() for name in ('registration.json', 'attempt.json', 'results.json')):
            continue
        if not (folder/'registration.json').exists() or not (folder/'attempt.json').exists():
            raise ValueError(f'incomplete stage metadata: {folder.name}')
        registration, attempt = read_json(folder/'registration.json'), read_json(folder/'attempt.json')
        mode = registration['config'].get('mode')
        metadata_hashes = {name:sha(folder/name) for name in ('registration.json', 'attempt.json')}
        if mode not in ('calibration', 'evaluation'):
            excluded.append(dict(stage=folder.name, mode=mode, status=attempt['status'],
                                 reason='explicitly not a calibration/evaluation input; never counted as evaluation',
                                 metadata_sha256=metadata_hashes,
                                 reserved_new_observations=attempt.get('reserved_new_observations'),
                                 reserved_wall_seconds=attempt.get('reserved_wall_seconds')))
            continue
        if attempt['status'] != 'complete':
            raise ValueError(f'failed or incomplete {mode} source cannot be silently skipped: {folder.name}')
        if not (folder/'results.json').exists():
            raise ValueError(f'completed study lacks results: {folder.name}')
        result = read_json(folder/'results.json')
        condition = result['condition']
        if result['mode'] != mode or condition != registration['config']['condition']:
            raise ValueError('study results disagree with registered mode/condition')
        key = (mode, condition)
        if key in seen:
            raise ValueError(f'duplicate completed scientific condition: {key}')
        seen.add(key)
        compatible_config(registration['config']['frozen_config'], config)
        point_list = config['null_points' if mode == 'calibration' else 'evaluation_points']
        if type(condition) is not int or not 0 <= condition < len(point_list):
            raise ValueError('source condition outside frozen grid')
        groups = config[mode+'_groups']
        if result['points'] != [point_list[condition]] or result['groups'] != groups:
            raise ValueError('source point/group allocation differs from frozen configuration')
        if result['records'] != groups*len(config['repeats']):
            raise ValueError('source record allocation is incomplete')
        expected_observations = groups*max(config['repeats'])
        if (result['new_observations'] != expected_observations
                or attempt['reserved_new_observations'] != expected_observations
                or registration['config']['new_observations'] != expected_observations):
            raise ValueError('source observation allocation changed')
        for name in (records_path(folder).name, 'generation.json', 'results.json'):
            metadata_hashes[name] = sha(folder/name)
        bindings.append(dict(path=str(folder.relative_to(ROOT)), stage=folder.name, mode=mode, condition=condition,
                             git_head=registration['git_head'], metadata_sha256=metadata_hashes,
                             artifact_sha256=attempt['artifact_sha256']))
    expected = {(mode, i) for mode, points in [('calibration', config['null_points']), ('evaluation', config['evaluation_points'])]
                for i in range(len(points))}
    if seen != expected:
        raise ValueError(f'scientific stage coverage mismatch; missing={sorted(expected-seen)}, extra={sorted(seen-expected)}')
    return bindings, excluded


def verify_inputs(bindings):
    counts = dict(stages=0, metadata=0, artifacts=0, observations_archives=0)
    for binding in bindings:
        folder = ROOT/binding['path']
        for name, expected in binding['metadata_sha256'].items():
            if sha(folder/name) != expected:
                raise ValueError(f'bound source metadata/records changed: {folder.name}/{name}')
            counts['metadata'] += 1
        attempt = read_json(folder/'attempt.json')
        if attempt['status'] != 'complete' or attempt['artifact_sha256'] != binding['artifact_sha256']:
            raise ValueError('source completion/artifact manifest changed')
        actual = {path.resolve() for path in folder.rglob('*') if path.is_file() and path.name != 'attempt.json'}
        expected_files = {(ROOT/name).resolve() for name in binding['artifact_sha256']}
        if actual != expected_files:
            raise ValueError(f'full source artifact inventory changed: {folder.name}')
        archives = [path for path in actual if path.name.startswith('observations_') and path.suffix == '.npz']
        if archives != [folder.resolve()/'observations_00.npz']:
            raise ValueError('source must bind exactly one saved observation archive')
        for name, expected in binding['artifact_sha256'].items():
            path = ROOT/name
            if sha(path) != expected:
                raise ValueError(f'bound source artifact changed: {name}')
            counts['artifacts'] += 1
            if path.name.startswith('observations_') and path.suffix == '.npz':
                counts['observations_archives'] += 1
        counts['stages'] += 1
    return counts


def load_records(bindings, config):
    datasets = {}
    for binding in bindings:
        folder, mode, condition = ROOT/binding['path'], binding['mode'], binding['condition']
        record_file = records_path(folder)
        if record_file.name not in binding['metadata_sha256']:
            raise ValueError('selected records file is not bound to the source registration')
        records, generation = read_json(record_file), read_json(folder/'generation.json')
        point = config['null_points' if mode == 'calibration' else 'evaluation_points'][condition]
        if len(generation) != 1 or generation[0]['point'] != point:
            raise ValueError('generation metadata changed or combines scientific populations')
        split_id = 1 if mode == 'calibration' else 2
        if generation[0]['seed'] != [*config['seed'], split_id, condition, 0]:
            raise ValueError('source split/condition seed differs from frozen generation protocol')
        finite(generation[0]['seconds'], 'generation cost', True)
        groups, repeats = config[mode+'_groups'], config['repeats']
        mapping = {}
        for record in records:
            key = (record['group'], record['repeats'])
            if (type(record['group']) is not int or type(record['repeats']) is not int
                    or record['local_condition'] != 0 or key in mapping):
                raise ValueError('duplicate group/R or mixed local condition')
            if record['observations'] != record['repeats']:
                raise ValueError('record observation count differs from R')
            for method in config['methods']:
                if method not in record['statistics']:
                    raise ValueError('missing method statistic')
                value = record['statistics'][method]
                fit_name = FIT_FOR_METHOD[method]
                if value is not None:
                    finite(value, 'saved statistic')
                    if fit_name and not record['fits'][fit_name]['success']:
                        raise ValueError('failed fit returned an unqualified finite statistic')
                else:
                    owner = 'full_score' if fit_name == 'mle' else 'moment_score'
                    kind = 'optimizer_failed' if fit_name and not record['fits'][fit_name]['success'] else 'tangent_unavailable'
                    permitted = fit_name is not None and (method != 'moment_j' or kind == 'optimizer_failed')
                    evidence = any(item['method'] == owner and item['kind'] == kind and item['reason']
                                   for item in record['failures'])
                    if not permitted or not evidence:
                        raise ValueError('missing statistic has no matching method failure evidence')
                finite(record['costs']['per_method_seconds'][method], 'method cost', True)
            for field in ('setup_seconds', 'setup_original_construction_seconds', 'joint_complete_seconds',
                          'shared_result_conversion_seconds'):
                finite(record['costs'][field], field, True)
            if type(record['costs']['setup_cache_hit']) is not bool or record['costs']['per_method_setup_included'] is not False:
                raise ValueError('saved cost schema must distinguish setup from the method path')
            finite(record['complete_seconds'], 'runner complete cost', True)
            mapping[key] = record
        expected = {(group, repeat) for group in range(groups) for repeat in repeats}
        if set(mapping) != expected or len(records) != len(expected):
            raise ValueError('records do not cover every registered independent group and R prefix exactly once')
        datasets[(mode, condition)] = dict(binding=binding, generation=generation[0], records=mapping,
                                          attempt=read_json(folder/'attempt.json'))
    return datasets


def values_for(dataset, repeat, method, groups):
    return [dataset['records'][group, repeat]['statistics'][method] for group in range(groups)]


def calibrate(datasets, config):
    result = {}
    for repeat in config['repeats']:
        for method in config['methods']:
            rows = []
            for condition, point in enumerate(config['null_points']):
                row = rank_threshold(values_for(datasets['calibration', condition], repeat, method,
                                                 config['calibration_groups']), config['alpha'])
                rows.append(dict(condition=condition, point=point, **row))
            qualified = all(row['finite_threshold'] for row in rows)
            threshold = max(row['threshold'] for row in rows) if qualified else None
            result[repeat, method] = dict(repeats=repeat, method=method, threshold=threshold,
                finite_threshold=qualified, failed=sum(row['failed'] for row in rows), null_grid=rows,
                calibration_groups=sum(row['groups'] for row in rows), comparison='strictly greater',
                failure_policy='calibration failures rank as positive infinity; evaluation failures do not reject',
                theorem_scope='unconditional exchangeability on the registered null grid only; not conditional-on-library or continuum coverage')
    return result


def numeric_summary(values):
    array = np.asarray(values, float)
    if not len(array):
        return None
    if not np.isfinite(array).all():
        raise ValueError('nonfinite analysis diagnostic')
    return dict(count=len(array), mean=np.mean(array, axis=0).tolist(),
                minimum=np.min(array, axis=0).tolist(), maximum=np.max(array, axis=0).tolist())


def fit_summary(records, method, point):
    name = FIT_FOR_METHOD[method]
    if name is None:
        pairs = [row['diagnostics']['second_moment']['fitted_variance_pairs'] for row in records]
        return dict(fit='two variance combinations only', fitted_variance_pairs=numeric_summary(pairs),
                    nuisance_rmse=None, failed_fits=0, boundary=0, nuisance_identifiable=False)
    fits = [row['fits'][name] for row in records]
    estimates = np.asarray([fit['theta'] for fit in fits], float)
    if estimates.shape != (len(records), 3) or not np.isfinite(estimates).all():
        raise ValueError('missing/nonfinite fitted nuisance diagnostic')
    truth = np.array([point['mu'], math.log(point['tau']), math.log(point['sigma2'])])
    physical = estimates.copy()
    physical[:, 1:] = np.exp(physical[:, 1:])
    physical_truth = np.array([point['mu'], point['tau'], point['sigma2']])
    success = np.asarray([fit['success'] for fit in fits], bool)
    def error_summary(array, reference, mask):
        if not np.any(mask):
            return None
        error = array[mask]-reference
        return dict(count=int(mask.sum()), bias=error.mean(axis=0).tolist(), rmse=np.sqrt(np.mean(error**2, axis=0)).tolist())
    return dict(fit=name, failed_fits=int((~success).sum()), boundary=sum(bool(fit['on_boundary']) for fit in fits),
        all_coordinate_errors=error_summary(estimates, truth, np.ones(len(fits), bool)),
        all_physical_errors=error_summary(physical, physical_truth, np.ones(len(fits), bool)),
        successful_coordinate_errors=error_summary(estimates, truth, success),
        successful_physical_errors=error_summary(physical, physical_truth, success),
        optimizer_evaluations=sum(fit['total_evaluations'] for fit in fits),
        scope='truth used only in downstream error calculation; failed-fit parameters retained; at nonzero separation null-fit error includes model mismatch')


def local_estimation(records, method, point):
    if method not in ('full_score', 'moment_score'):
        return None
    delta, mu = point['delta'], point['mu']
    limit = math.floor(67*(1+mu/6))
    same_branch = (math.floor(67*(1+(mu-delta)/6)) == limit
                   and math.floor(67*(1+(mu+delta)/6)) == limit)
    estimates = [row['r_hat'][method] for row in records if row['r_hat'][method] is not None]
    if any(estimate['local_only'] is not True for estimate in estimates):
        raise ValueError('saved one-step estimates lack the required local-only label')
    base = dict(available=len(estimates), missing=len(records)-len(estimates), true_branch_preserved=same_branch,
                physical_delta_estimation_claim=False)
    if delta <= 0 or not same_branch or point['role'] == 'finite_separation':
        return dict(**base, eligible=False, reason='relative true-r error is only interpreted for registered positive within-branch separations')
    true_r = delta*delta*math.log(1/(delta*delta))
    result = dict(**base, eligible=True, true_r=true_r,
                  scope='descriptive local-r error on available outputs only; no finite-delta efficiency or estimation-advantage certificate')
    for field in ('unconstrained', 'one_sided'):
        values = np.asarray([finite(item[field], 'saved local-r estimate') for item in estimates])
        result[field] = None if not len(values) else dict(mean=float(values.mean()), bias=float(np.mean(values-true_r)),
            rmse=float(np.sqrt(np.mean((values-true_r)**2))), relative_bias=float(np.mean(values/true_r-1)),
            relative_rmse=float(np.sqrt(np.mean((values/true_r-1)**2))), zero_fraction=float(np.mean(values == 0)))
    return result


def rates(datasets, thresholds, config):
    metrics, decisions = {}, {}
    groups = config['evaluation_groups']
    for condition, point in enumerate(config['evaluation_points']):
        for repeat in config['repeats']:
            records = [datasets['evaluation', condition]['records'][group, repeat] for group in range(groups)]
            for method in config['methods']:
                cutoff = thresholds[repeat, method]
                rejected, failed = apply_threshold([row['statistics'][method] for row in records], cutoff)
                count, failure_count = int(rejected.sum()), int(failed.sum())
                fit = fit_summary(records, method, point)
                key = (condition, repeat, method)
                decisions[key] = dict(rejected=rejected, failed=failed)
                metrics[key] = dict(condition=condition, point=point, repeats=repeat, method=method, groups=groups,
                    rejections=count, rate=count/groups, wilson=wilson(count, groups, config['comparison']['confidence']),
                    statistic_failures=failure_count, failed_fits=fit['failed_fits'], boundary=fit['boundary'],
                    executable_policy='a failed evaluation does not reject and stays in the denominator',
                    failure_bounds=dict(lower=count/groups, upper=(count+failure_count)/groups,
                                        scope='unknown decision on failures; deterministic, not a confidence interval'),
                    threshold=cutoff['threshold'], finite_threshold=cutoff['finite_threshold'],
                    calibration_failures=cutoff['failed'], fit_diagnostics=fit,
                    local_r_estimation=local_estimation(records, method, point),
                    finite_grid_theorem_applies=point['role'] == 'grid_null',
                    rate_interpretation='false-positive rate' if point['delta'] == 0 else 'power',
                    interval_scope='pointwise Wilson interval conditional on the fixed calibration library; no familywise or continuum claim')
    return metrics, decisions


def path_cost(dataset, repeat, method, groups):
    selected = [dataset['records'][group, repeat] for group in range(groups)]
    all_rows = list(dataset['records'].values())
    path = math.fsum(row['costs']['per_method_seconds'][method] for row in selected)
    uses_family = method != 'second_moment'
    cold = max((row['costs']['setup_seconds'] for row in all_rows if not row['costs']['setup_cache_hit']), default=0.)
    original = max(row['costs']['setup_original_construction_seconds'] for row in all_rows)
    cold = max(cold, original) if uses_family else 0.
    warm = math.fsum(row['costs']['setup_seconds'] for row in selected if row['costs']['setup_cache_hit']) if uses_family else 0.
    return dict(groups=groups, path_seconds=path, cold_setup_seconds=cold, warm_setup_seconds=warm,
                standalone_seconds=path+cold+warm, variable_seconds_per_group=(path+warm)/groups,
                amortized_seconds_per_group=(path+cold+warm)/groups,
                cold_first_group_seconds=selected[0]['costs']['per_method_seconds'][method]+cold,
                setup_scope='one reported cold construction charged to each standalone method/R path, even when the joint runner reused R64 setup for R256')


def cost_analysis(datasets, config):
    totals, per_point = {}, {}
    evaluation_groups = len(config['evaluation_points'])*config['evaluation_groups']
    for repeat in config['repeats']:
        for method in config['methods']:
            cal = [path_cost(datasets['calibration', i], repeat, method, config['calibration_groups'])
                   for i in range(len(config['null_points']))]
            evaluate = [path_cost(datasets['evaluation', i], repeat, method, config['evaluation_groups'])
                        for i in range(len(config['evaluation_points']))]
            calibration = math.fsum(row['standalone_seconds'] for row in cal)
            evaluation = math.fsum(row['standalone_seconds'] for row in evaluate)
            total = dict(repeats=repeat, method=method,
                calibration_groups=len(config['null_points'])*config['calibration_groups'], evaluation_groups=evaluation_groups,
                calibration_path_seconds=math.fsum(row['path_seconds'] for row in cal),
                calibration_setup_seconds=math.fsum(row['cold_setup_seconds']+row['warm_setup_seconds'] for row in cal),
                calibration_seconds=calibration, evaluation_path_seconds=math.fsum(row['path_seconds'] for row in evaluate),
                evaluation_setup_seconds=math.fsum(row['cold_setup_seconds']+row['warm_setup_seconds'] for row in evaluate),
                evaluation_seconds=evaluation, fixed_workload_seconds=calibration+evaluation,
                fixed_workload_amortized_seconds=(calibration+evaluation)/evaluation_groups,
                calibration_amortized_seconds=calibration/evaluation_groups,
                scope='standalone algorithm-path accounting over the frozen evaluation workload; not additive joint runtime or deployment latency')
            totals[repeat, method] = total
            for i, value in enumerate(evaluate):
                per_point[i, repeat, method] = dict(**value, calibration_allocation_seconds_per_group=calibration/evaluation_groups,
                    complete_amortized_seconds_per_group=value['amortized_seconds_per_group']+calibration/evaluation_groups,
                    calibration_allocation_denominator=evaluation_groups)
    actual = []
    for (mode, condition), dataset in sorted(datasets.items()):
        rows, attempt = list(dataset['records'].values()), dataset['attempt']
        actual.append(dict(mode=mode, condition=condition, stage=dataset['binding']['stage'],
            generation_seconds=dataset['generation']['seconds'],
            actual_joint_setup_seconds=math.fsum(row['costs']['setup_seconds'] for row in rows),
            actual_joint_inference_seconds=math.fsum(row['costs']['joint_complete_seconds'] for row in rows),
            caller_complete_seconds=math.fsum(row['complete_seconds'] for row in rows),
            shared_json_conversion_seconds=math.fsum(row['costs']['shared_result_conversion_seconds'] for row in rows),
            wall_seconds=attempt['wall_seconds'], cpu_seconds=attempt['cpu_seconds'],
            reserved_wall_seconds=attempt['reserved_wall_seconds'], reserved_new_observations=attempt['reserved_new_observations']))
    return totals, per_point, actual


def compare(metrics, decisions, thresholds, costs, config):
    primary = validate_config(config)
    specification = config['comparison']
    candidate = specification['primary_candidate']
    output = []
    for condition in primary:
        point = config['evaluation_points'][condition]
        related_null = [i for i, null in enumerate(config['evaluation_points'])
                        if null['role'] == 'grid_null' and null['sigma2'] == point['sigma2']]
        for repeat in config['repeats']:
            for baseline in specification['baselines']:
                c, b = decisions[condition, repeat, candidate], decisions[condition, repeat, baseline]
                interval = paired_interval(c['rejected'], b['rejected'], specification['family_size'], specification['confidence'])
                null_rows = [metrics[i, repeat, method] for i in related_null for method in (candidate, baseline)]
                null_ok = bool(null_rows) and all(row['wilson']['upper'] <= specification['null_wilson_upper_limit'] for row in null_rows)
                failures = dict(candidate_alternative=int(c['failed'].sum()), baseline_alternative=int(b['failed'].sum()),
                    candidate_calibration=thresholds[repeat, candidate]['failed'], baseline_calibration=thresholds[repeat, baseline]['failed'],
                    related_null_evaluation=sum(row['statistic_failures'] for row in null_rows))
                no_failures = not any(failures.values())
                candidate_cost = costs[condition, repeat, candidate]['complete_amortized_seconds_per_group']
                baseline_cost = costs[condition, repeat, baseline]['complete_amortized_seconds_per_group']
                ratio = baseline_cost/candidate_cost if candidate_cost > 0 else None
                power_candidate = (interval['difference'] >= specification['minimum_power_gain'] and interval['lower'] > 0)
                cost_candidate = (ratio is not None and ratio >= specification['minimum_cost_ratio']
                                  and interval['lower'] > -specification['noninferiority_margin'])
                output.append(dict(condition=condition, point=point, repeats=repeat, candidate=candidate, baseline=baseline,
                    paired=interval, failure_difference_bounds=failure_difference_bounds(c['rejected'], b['rejected'], c['failed'], b['failed']),
                    related_null_conditions=related_null, related_null_checks=[dict(condition=row['condition'], method=row['method'],
                        upper=row['wilson']['upper'], failures=row['statistic_failures']) for row in null_rows],
                    null_gate_passed=null_ok, no_failures=no_failures, failures=failures,
                    power_numeric_criterion=bool(power_candidate), power_advantage=bool(power_candidate and null_ok and no_failures),
                    cost_ratio=ratio, candidate_amortized_seconds=candidate_cost, baseline_amortized_seconds=baseline_cost,
                    cost_numeric_criterion=bool(cost_candidate), cost_advantage=bool(cost_candidate and null_ok and no_failures),
                    cost_scope='fixed-workload calibrated local algorithm paths, including fit and setup; not production latency',
                    interpretation='registered pointwise advantage criterion with simultaneous paired interval; no pooling of different populations'))
    if len(output) != specification['family_size']:
        raise ValueError('paired family coverage changed')
    return output


def cost_markdown(totals, actual, config):
    lines = ['# 固定工作量的算法计算成本', '',
        '本表只复用保存计时，不重采样、不重拟合。每方法路径费包含其拟合、构造和统计；校准不是免费步骤。',
        '同一实际运行共享的 MLE/GMM 不能重复相加为真实总耗时。下表是假定各方法独立使用时的路径账，非生产部署延迟。', '',
        '| R | 方法 | 校准路径秒 | 校准 setup 秒 | 评价路径秒 | 评价 setup 秒 | 含校准摊销秒/评价组 |',
        '| ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for (repeat, method), row in totals.items():
        lines.append(f"| {repeat} | {method} | {row['calibration_path_seconds']:.9g} | {row['calibration_setup_seconds']:.9g} | "
                     f"{row['evaluation_path_seconds']:.9g} | {row['evaluation_setup_seconds']:.9g} | {row['fixed_workload_amortized_seconds']:.9g} |")
    lines.extend(['', f"每 R 的校准工作量为 {len(config['null_points'])*config['calibration_groups']} 组；评价工作量为 "
                  f"{len(config['evaluation_points'])*config['evaluation_groups']} 组。校准全成本按后者固定分母摊销，不合并性能总体。",
        '每个源 stage 的冷构造对每条 standalone 方法/R 路径分别计一次，避免把先执行 R64 后 R256 的 warm cache 当作 R256 免费 setup。C2 无需 NullFamily 构造。',
        'JSON 转换、runner 序列化、实际联合调用与源 stage wall/CPU 另列 actual_stage_costs.json；未把共享开销任意分摊后声称通用端到端延迟。', '',
        f"源 stage 合计预约观测 {sum(row['reserved_new_observations'] for row in actual)}、预约秒 {sum(row['reserved_wall_seconds'] for row in actual):.9g}。",
        f"源 stage 实际 wall 合计 {sum(row['wall_seconds'] for row in actual):.9g} 秒、CPU 合计 {sum(row['cpu_seconds'] for row in actual):.9g} 秒。这些是来源费用，不是本 reader 的新增费用。", '',
        '成本优势只有在相关 null Wilson 门槛、无失败、配对功效非劣下界和至少两倍完整路径倍率同时通过时才标记；计时本身不提供生产/硬件泛化保证。', ''])
    return '\n'.join(lines)


def calculate(output):
    registration = read_json(output/'registration.json')['config']
    config, bindings = registration['frozen_config'], registration['source_bindings']
    if sha(CONFIG_PATH) != registration['method_config_sha256']:
        raise ValueError('METHOD_CONFIG changed after analysis registration')
    current, excluded = discover_inputs(ARTIFACT, config, excluded_stage=output.name)
    if current != bindings or excluded != registration['excluded_stages']:
        raise ValueError('source stage inventory changed after analysis registration')
    before = verify_inputs(bindings)
    datasets = load_records(bindings, config)
    thresholds = calibrate(datasets, config)
    metrics, decisions = rates(datasets, thresholds, config)
    totals, point_costs, actual = cost_analysis(datasets, config)
    comparisons = compare(metrics, decisions, thresholds, point_costs, config)
    for key, row in metrics.items():
        row['cost'] = point_costs[key]
    dump(output/'calibration.json', list(thresholds.values()))
    dump(output/'metrics.json', list(metrics.values()))
    dump(output/'comparisons.json', comparisons)
    dump(output/'costs.json', list(totals.values()))
    dump(output/'actual_stage_costs.json', actual)
    dump(output/'input_bindings.json', dict(source_bindings=bindings, excluded_stages=excluded))
    shape = (len(config['evaluation_points']), len(config['repeats']), len(config['methods']), config['evaluation_groups'])
    rejected, failed = np.empty(shape, bool), np.empty(shape, bool)
    for condition in range(shape[0]):
        for ri, repeat in enumerate(config['repeats']):
            for mi, method in enumerate(config['methods']):
                rejected[condition, ri, mi] = decisions[condition, repeat, method]['rejected']
                failed[condition, ri, mi] = decisions[condition, repeat, method]['failed']
    np.savez_compressed(output/'decisions.npz', rejected=rejected, failed=failed,
                        repeats=np.asarray(config['repeats']), methods=np.asarray(config['methods']))
    (output/'COST_RESULTS.md').write_text(cost_markdown(totals, actual, config))
    after = verify_inputs(bindings)
    if after != before:
        raise ValueError('source artifact checks changed during analysis')
    if discover_inputs(ARTIFACT, config, excluded_stage=output.name) != (bindings, excluded):
        raise ValueError('source stage inventory changed during analysis')
    dump(output/'input_hash_counts.json', after)
    return dict(schema='method-advantage-analysis/1', mode='analysis', new_observations=0,
        new_scientific_nodes=0, new_scientific_rules=0, receiver_calls=0, decoder_calls=0,
        calibration_rows=len(thresholds), metric_rows=len(metrics), comparison_rows=len(comparisons),
        family_size=config['comparison']['family_size'], source_hashes_unchanged=True, input_hash_counts=after,
        power_advantages=sum(row['power_advantage'] for row in comparisons),
        cost_advantages=sum(row['cost_advantage'] for row in comparisons),
        evaluation_failed_method_groups=int(failed.sum()),
        calibration_failed_method_groups=sum(row['failed'] for row in thresholds.values()),
        excluded_stages=excluded, scope='saved-data inference only; conservative simultaneous paired bounds and finite-grid calibration')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--wall-seconds', type=int, default=300)
    args = parser.parse_args()
    config = read_json(CONFIG_PATH)
    bindings, excluded = discover_inputs(ARTIFACT, config, excluded_stage=args.stage)
    sources = [*loaded_project_sources(sys.modules), Path(__file__).with_name('test_analysis.py'), CONFIG_PATH]
    for binding in bindings:
        # records/observations are hash-bound by the registration and complete
        # attempt manifest, but are not duplicated into another large snapshot.
        sources.extend(ROOT/binding['path']/name for name in ('registration.json', 'attempt.json', 'generation.json', 'results.json'))
    specification = dict(seed=config['seed'], mode='analysis', new_observations=0, frozen_config=config,
        source_bindings=bindings, excluded_stages=excluded, method_config_sha256=sha(CONFIG_PATH),
        receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)
    run(args.stage, specification, sources, calculate, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
