"""Bounded two-sample bridge distances from frozen evaluation log ratios."""
import argparse
import math
from pathlib import Path
import sys

import numpy as np

from experiments.afdm_efficient_information.audit import (
    audit_hashes, loaded_project_sources, read_json, sha,
)
from experiments.afdm_collision_resolution.protocol import ROOT, ARTIFACT, MISSION, dump, run

CONFIG_PATH = ARTIFACT/'DISTANCE_CONFIG.json'
PROTECTED = MISSION/'protected_baseline.json'


def bridge_values(log_ratio):
    """TV and unhalved Hellinger-squared bridge functions, without cosh overflow."""
    log_ratio = np.asarray(log_ratio, float)
    if not np.isfinite(log_ratio).all():
        raise ValueError('finite saved log likelihood ratios required')
    magnitude = abs(log_ratio)/2
    exponential = np.exp(-magnitude)
    one_minus = -np.expm1(-magnitude)
    return dict(tv=abs(np.tanh(log_ratio/2)),
                hellinger_squared=2*one_minus**2/(1+exponential**2))


def sample_summary(values):
    values = np.asarray(values, float)
    if values.ndim != 1 or len(values)<2 or not np.isfinite(values).all():
        raise ValueError('at least two independent finite evaluation groups required')
    mean = float(values.mean())
    variance = float(np.sum((values-mean)**2)/(len(values)-1))
    return dict(groups=len(values), mean=mean, sample_variance=variance,
                standard_error=math.sqrt(variance/len(values)))


def hoeffding_interval(estimate, count0, count1, bound, failure_probability):
    if (min(count0, count1)<1 or bound<=0 or not math.isfinite(bound)
            or not 0<failure_probability<1 or not 0<=estimate<=bound):
        raise ValueError('valid bounded stratified estimate and failure probability required')
    radius = bound*math.sqrt((1/count0+1/count1)*math.log(2/failure_probability)/8)
    return dict(lower=max(0., estimate-radius), upper=min(bound, estimate+radius),
                radius=radius, failure_probability=failure_probability,
                formula='b*sqrt((1/n0+1/n1)*log(2/delta)/8)')


def stratified_summary(values0, values1, bound, alpha, comparisons):
    first, second = sample_summary(values0), sample_summary(values1)
    if (isinstance(comparisons, bool) or not isinstance(comparisons, int) or comparisons<1
            or np.any(np.asarray(values0)<0) or np.any(np.asarray(values0)>bound)
            or np.any(np.asarray(values1)<0) or np.any(np.asarray(values1)>bound)):
        raise ValueError('bounded bridge values and positive comparison count required')
    estimate = (first['mean']+second['mean'])/2
    se = math.sqrt(first['sample_variance']/first['groups']+second['sample_variance']/second['groups'])/2
    return dict(null=first, alternative=second, group_weights=[.5, .5], estimate=estimate,
        standard_error=se, range=[0., bound],
        pointwise=hoeffding_interval(estimate, first['groups'], second['groups'], bound, alpha),
        simultaneous=hoeffding_interval(estimate, first['groups'], second['groups'], bound, alpha/comparisons),
        simultaneous_comparisons=comparisons, standard_error_scope='diagnostic sample SE; concentration intervals use only boundedness')


def tensor_hellinger(single_frame_squared, repeats):
    values = np.asarray(single_frame_squared, float)
    if (isinstance(repeats, bool) or not isinstance(repeats, int) or repeats<1
            or not np.isfinite(values).all() or np.any(values<0) or np.any(values>2)):
        raise ValueError('Hellinger squared in [0,2] and a positive integer R required')
    result = np.full(values.shape, 2., float)
    interior = values<2
    result[interior] = -2*np.expm1(repeats*np.log1p(-values[interior]/2))
    return result.item() if result.ndim == 0 else result


def uniform_log_ratio_bias_bound(epsilon):
    """Both bridges are 1/2-Lipschitz; no observed refinement error is a certificate."""
    if epsilon is None:
        return None
    if not np.isfinite(epsilon) or epsilon<0:
        raise ValueError('nonnegative certified uniform log-ratio error required')
    return dict(tv=min(1., epsilon/2), hellinger_squared=min(2., epsilon/2))


def verify_bindings(config):
    folder = ROOT/config['source_stage_path']
    for name, digest in config['bound_records'].items():
        if sha(folder/name) != digest:
            raise ValueError(f'bound source record changed: {name}')
    if sha(PROTECTED) != config['protected_manifest_sha256']:
        raise ValueError('protected baseline manifest changed')
    registration, attempt = read_json(folder/'registration.json'), read_json(folder/'attempt.json')
    if registration['git_head'] != config['source_git_head'] or attempt['status'] != 'complete':
        raise ValueError('completed source stage at the frozen commit required')
    for name, digest in config['consumed_artifacts'].items():
        path = folder/name
        recorded = attempt['artifact_sha256'][str(path.relative_to(ROOT))]
        if digest != recorded or sha(path) != digest:
            raise ValueError(f'bound evaluation artifact changed: {name}')
    return folder


def calculate(output):
    config = read_json(CONFIG_PATH)
    folder = verify_bindings(config)
    before = audit_hashes([folder], protected=PROTECTED)
    records = read_json(folder/'oracle_pairs.json')
    source_config = read_json(folder/'registration.json')['config']
    source_metadata = {row['family']:row for row in read_json(folder/'input_audit.json')}
    rows, projections, visited = [], [], set()
    for family, definition in config['families'].items():
        with np.load(folder/f'oracle_{family}.npz', allow_pickle=False) as archive:
            raw = {name:archive[name].copy() for name in ('pair_indices', 'repeats', 'candidates',
                'evaluation_null_llr', 'evaluation_alt_llr')}
        pairs, repeats, candidates = raw['pair_indices'], raw['repeats'], raw['candidates']
        if list(map(int, repeats)) != definition['repeats'] or len(pairs) != definition['pairs']:
            raise ValueError('source family dimensions differ from registered coverage')
        null_llr, alt_llr = raw['evaluation_null_llr'], raw['evaluation_alt_llr']
        expected_shape = (len(repeats), len(pairs), definition['evaluation_groups'])
        if null_llr.shape != expected_shape or alt_llr.shape != expected_shape:
            raise ValueError('source evaluation denominator or pair grid changed')
        values = {role:bridge_values(llr) for role, llr in [('null', null_llr), ('alternative', alt_llr)]}
        payload = dict(pair_indices=pairs, repeats=repeats, candidates=candidates)
        payload.update({role+'_'+metric:array for role, maps in values.items() for metric, array in maps.items()})
        np.savez_compressed(output/f'bridge_{family}.npz', **payload)
        family_rows = {}
        for ri, repeat in enumerate(repeats):
            for pi, (null, alt) in enumerate(pairs):
                key = (family, pi, int(repeat))
                if key in visited:
                    raise ValueError('duplicate input pair/R key')
                visited.add(key)
                matching = [row for row in records if (row['family'], row['pair_id'], row['repeats']) == key]
                if len(matching) != 1:
                    raise ValueError('exactly one source report per evaluation pair/R required')
                original = matching[0]
                if (original['null_condition'] != int(null) or original['alt_condition'] != int(alt)
                        or original['false_alarm']['groups'] != definition['evaluation_groups']
                        or original['power']['groups'] != definition['evaluation_groups']):
                    raise ValueError('source report IDs or denominators disagree with saved evaluation LLR')
                if (candidates[null, 0] >= candidates[alt, 0]
                        or not np.array_equal(candidates[null, 1:], candidates[alt, 1:])):
                    raise ValueError('null/alternative pair must have identical nuisance and increasing interest')
                metrics = {metric:stratified_summary(values['null'][metric][ri, pi],
                    values['alternative'][metric][ri, pi], bound, config['interval_failure_probability'],
                    config['simultaneous_comparisons']) for metric, bound in [('tv', 1.), ('hellinger_squared', 2.)]}
                row = dict(family=family, pair_id=pi, repeats=int(repeat), null_condition=int(null), alt_condition=int(alt),
                    null_theta=candidates[null].tolist(), alternative_theta=candidates[alt].tolist(),
                    reference_method=source_config['inputs'][family]['reference_method'],
                    reference_qualification=source_metadata[family]['reference_qualification'],
                    distance_target=definition['distance_target'], interval_target=definition['interval_target'],
                    null_negative_llr=sample_summary(-null_llr[ri, pi]), alternative_llr=sample_summary(alt_llr[ri, pi]),
                    llr_mean_scope='unbounded empirical KL diagnostics only; sample SE is not a concentration certificate',
                    uniform_log_ratio_error_certificate=None, proxy_bias_certificate=None,
                    **metrics)
                rows.append(row)
                family_rows[pi, int(repeat)] = row
        for pi in range(len(pairs)):
            first = family_rows[pi, 1]['hellinger_squared']
            for repeat in config['projection_repeats']:
                projection = dict(family=family, pair_id=pi, repeats=repeat,
                    plugin_hellinger_squared=tensor_hellinger(first['estimate'], repeat),
                    projected_pointwise=tensor_hellinger([first['pointwise']['lower'], first['pointwise']['upper']], repeat).tolist(),
                    projected_simultaneous=tensor_hellinger([first['simultaneous']['lower'], first['simultaneous']['upper']], repeat).tolist(),
                    observed_original_R=repeat in definition['repeats'],
                    scope=('exact-iid-law identity conditional on exact single-frame Hellinger target; finite precision not certified'
                           if family == 'control' else 'algebraic proxy extrapolation; no true-distance or repeated-proxy coverage guarantee'),
                    no_new_experiment=True, calibrated_detection_guarantee=False)
                if repeat in definition['repeats']:
                    direct = family_rows[pi, repeat]['hellinger_squared']
                    projection['direct_estimate'] = direct['estimate']
                    projection['direct_simultaneous'] = [direct['simultaneous']['lower'], direct['simultaneous']['upper']]
                    projection['direct_minus_plugin'] = direct['estimate']-projection['plugin_hellinger_squared']
                    projection['comparison_scope'] = 'shared source data and R-prefixes; discrepancy is not an independent replication test'
                projections.append(projection)
    if len(rows) != config['expected_rows'] or len(records) != config['expected_rows']:
        raise ValueError('complete registered 112-row coverage required')
    if len(projections) != config['expected_projection_rows']:
        raise ValueError('complete registered single-frame propagation grid required')
    if config['simultaneous_comparisons'] != 2*len(rows):
        raise ValueError('familywise budget must cover every pair/R and both metrics')
    dump(output/'distance_cases.json', rows)
    dump(output/'repetition_projection.json', projections)
    after = audit_hashes([verify_bindings(config)], protected=PROTECTED)
    if before != after:
        raise ValueError('source files or recorded costs changed during reader')
    dump(output/'input_audit.json', before)
    return dict(schema='collision-distance/1', cases=len(rows), projections=len(projections),
        new_observations=0, new_scientific_nodes=0, new_scientific_rules=0, receiver_calls=0, decoder_calls=0,
        interval_failure_probability=config['interval_failure_probability'], simultaneous_comparisons=config['simultaneous_comparisons'],
        statistical_interval='weighted two-sample Hoeffding; Bonferroni across all pair/R/metric rows',
        independent_group_scope='independent within each P0/P1 sample; no independence claimed across pairs or R',
        actual_distance_certified=False, empirical_optimal_power_certified=False, source_hashes_unchanged=True,
        failures=0, input_hash_counts=before['counts'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    config = read_json(CONFIG_PATH)
    folder = ROOT/config['source_stage_path']
    sources = [Path(__file__), Path(__file__).with_name('test_distance_reader.py'),
        Path(__file__).with_name('DISTANCE.md'), CONFIG_PATH, PROTECTED,
        folder/'registration.json', folder/'attempt.json']
    sources.extend(loaded_project_sources(sys.modules))
    run(args.stage, config, sources, calculate, wall_seconds=config['wall_seconds'])


if __name__ == '__main__':
    main()
