"""Independent reader for saved oracle and identifiability supplements."""
import argparse
import math
from pathlib import Path
import sys

import numpy as np
from scipy.special import ndtri

from experiments.afdm_efficient_information.audit import (
    ARTIFACT, Checks, PROTECTED, audit_hashes, loaded_project_sources,
    read_json, read_npz, resolve, sha,
)
from experiments.afdm_efficient_information.protocol import dump, run


def prefix_sum(values, groups, maximum, repeats):
    values = np.asarray(values)
    if len(values) != groups*maximum or not 1<=repeats<=maximum:
        raise ValueError('complete source groups and valid repeats required')
    indices = np.arange(groups)[:, None]*maximum+np.arange(repeats)
    return values[indices].sum(axis=1)


def same_nuisance(candidates):
    candidates = np.asarray(candidates)
    return np.all(candidates[:, None, 1:] == candidates[None, :, 1:], axis=2)


def known_eta_pairs(candidates):
    candidates = np.asarray(candidates)
    allowed = same_nuisance(candidates)
    null = candidates[:, 0].min()
    return np.asarray([(a, b) for b in range(len(candidates)) if candidates[b, 0]>null
                       for a in range(len(candidates)) if candidates[a, 0] == null and allowed[a, b]], dtype=int)


def cutoff(values, alpha):
    values = np.asarray(values, float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or not 0<alpha<1:
        raise ValueError('finite nonempty calibration vector and valid alpha required')
    rank = math.ceil((len(values)+1)*(1-alpha))
    if rank>len(values):
        raise ValueError('calibration denominator cannot resolve alpha')
    return float(sorted(values)[rank-1]), rank


def interval(successes, count):
    if count<=0 or not 0<=successes<=count:
        raise ValueError('invalid Bernoulli denominator')
    z = float(ndtri(.975))
    denominator = count+z*z
    center = (successes+z*z/2)/denominator
    half = z*math.sqrt(successes*(1-successes/count)+z*z/4)/denominator
    return [max(0., center-half), min(1., center+half)]


def uncertainty(values):
    values = np.asarray(values, float)
    if values.ndim != 1 or len(values)<2 or not np.isfinite(values).all():
        raise ValueError('at least two finite independent values required')
    mean = float(values.mean())
    return mean, float(np.sqrt(np.sum((values-mean)**2)/(len(values)-1)/len(values)))


def ambiguity(objective, candidates, epsilon_multiplier=64):
    objective, candidates = np.asarray(objective, float), np.asarray(candidates, float)
    if (objective.ndim != 2 or candidates.ndim != 2 or objective.shape[1] != len(candidates)
            or not np.isfinite(objective).all() or not np.isfinite(candidates).all()):
        raise ValueError('finite candidate objectives required')
    minimum = objective.min(axis=1)
    tolerance = epsilon_multiplier*np.finfo(float).eps*np.maximum(1., abs(objective).max(axis=1))
    exact = objective == minimum[:, None]
    nearby = objective-minimum[:, None] <= tolerance[:, None]
    result = dict(exact_set=exact, tolerance_set=nearby, row_tolerance=tolerance,
                  selected_indices=objective.argmin(axis=1))
    for label, mask in [('exact', exact), ('tolerance', nearby)]:
        result[label+'_joint_counts'] = mask.sum(axis=1)
        result[label+'_interest_counts'] = np.asarray([len(set(candidates[row, 0])) for row in mask])
        result[label+'_nuisance_counts'] = np.asarray([len({tuple(x) for x in candidates[row, 1:]}) for row in mask])
        result[label+'_coordinate_counts'] = np.asarray([[len(set(candidates[row, j]))
            for j in range(candidates.shape[1])] for row in mask])
    return result


def equivalence(coefficient_rows, epsilon_multiplier=64):
    values = np.asarray(coefficient_rows, float)
    if values.ndim != 2 or not len(values) or not np.isfinite(values).all():
        raise ValueError('finite coefficient rows required')
    exact = np.all(values[:, None] == values[None, :], axis=2)
    tolerance = epsilon_multiplier*np.finfo(float).eps*np.maximum(1.,
        np.maximum(abs(values[:, None]), abs(values[None, :])))
    near = np.all(abs(values[:, None]-values[None, :])<=tolerance, axis=2)
    # First occurrence labels; numerical neighborhoods remain a separate matrix.
    representatives, labels = [], []
    for index in range(len(values)):
        matching = next((j for j, representative in enumerate(representatives) if exact[index, representative]), None)
        if matching is None:
            matching = len(representatives)
            representatives.append(index)
        labels.append(matching)
    return dict(exact_equal_matrix=exact, nearby_matrix=near, exact_class_ids=np.asarray(labels))


def paired_counts(oracle, method):
    oracle, method = np.asarray(oracle, bool), np.asarray(method, bool)
    if oracle.ndim != 1 or method.shape != oracle.shape or len(oracle)<2:
        raise ValueError('matching independent paired decisions required')
    table = np.array([[np.count_nonzero((oracle == a)&(method == b)) for b in (False, True)] for a in (False, True)])
    difference = oracle.astype(float)-method.astype(float)
    mean, se = uncertainty(difference)
    return dict(table=table, mean=mean, standard_error=se)


def numerical(checks, actual, expected, label):
    checks.close(actual, expected, label, atol=1e-12, rtol=1e-11)


def audit_bernoulli(values, record, checks, label):
    values = np.asarray(values, bool)
    count, groups = int(values.sum()), len(values)
    checks.equal(count, record['count'], label+'/count')
    checks.equal(groups, record['groups'], label+'/groups')
    numerical(checks, count/groups, record['rate'], label+'/rate')
    numerical(checks, interval(count, groups), record['wilson95'], label+'/wilson')


def audit_mean(values, record, checks, label):
    mean, se = uncertainty(values)
    numerical(checks, mean, record['mean'], label+'/mean')
    numerical(checks, se, record['standard_error'], label+'/se')


def indexed(rows, fields):
    result = {tuple(row[field] for field in fields):row for row in rows}
    if len(result) != len(rows):
        raise ValueError('duplicate supplemental report keys')
    return result


def audit_groups(actual, expected, checks, label):
    # NumPy array_equal returns False even for equal ragged lists. Candidate
    # classes/neighborhoods deliberately have different cardinalities.
    checks.equal(actual == expected, True, label)


def audit_structural(record, family, method, checks, label):
    coordinates = [0, 1] if family == 'control' and method == 'second_gaussian' else (
        [1] if family == 'control' and method in ('old_T', 'powers') else [])
    checks.equal(coordinates, record['coordinates'], label+'/structural_coordinates')
    checks.equal('inherited_analytic' if coordinates else 'not_established', record['status'], label+'/structural_status')


def audit_calibration(objectives, candidates, alpha, record, checks, label):
    rows = indexed(record['conditions'], ['condition'])
    checks.equal(sorted(key[0] for key in rows), list(range(len(candidates))), label+'/all_conditions')
    confidence, detection, errors = [], [], []
    null = candidates[:, 0] == candidates[:, 0].min()
    for condition, values in enumerate(objectives):
        row = rows[condition,]
        best = values.min(axis=1)
        threshold, rank = cutoff(values[:, condition]-best, alpha)
        confidence.append(threshold)
        numerical(checks, threshold, row['confidence_cutoff'], label+f'/c{condition}/confidence')
        errors.append(abs(threshold-row['confidence_cutoff']))
        checks.equal(rank, row['rank'], label+f'/c{condition}/rank')
        checks.equal(len(values), row['groups'], label+f'/c{condition}/groups')
        if null[condition]:
            threshold, _ = cutoff(values[:, null].min(axis=1)-best, alpha)
            detection.append(threshold)
            numerical(checks, threshold, row['null_cutoff'], label+f'/c{condition}/null')
            errors.append(abs(threshold-row['null_cutoff']))
        else:
            checks.equal(None, row['null_cutoff'], label+f'/c{condition}/not_null')
    for key, value in [('confidence_cutoff', max(confidence)), ('detection_cutoff', max(detection))]:
        numerical(checks, value, record[key], label+'/'+key)
        errors.append(abs(value-record[key]))
    return max(errors)


def audit_ambiguity(objective, candidates, source, record, saved, multiplier, checks, label):
    rebuilt = ambiguity(objective, candidates, multiplier)
    checks.equal(rebuilt['selected_indices'], source['indices'], label+'/original_argmin')
    checks.equal(source['indices'], saved['selected_indices'], label+'/selected_preserved')
    for key, value in rebuilt.items():
        checks.equal(value, saved[key], label+'/'+key)
    checks.equal(len(objective), record['groups'], label+'/denominator')
    checks.equal(True, record['selected_indices_unchanged'], label+'/unchanged')
    checks.equal(float(rebuilt['row_tolerance'].max()), record['maximum_row_tolerance'], label+'/maximum_tolerance')
    for level in ('exact', 'tolerance'):
        for kind in ('joint', 'interest', 'nuisance'):
            values = rebuilt[level+'_'+kind+'_counts']
            audit_bernoulli(values>1, record[level][kind+'_multiple'], checks, label+'/'+level+'/'+kind)
            distribution = [dict(candidates=int(value), groups=int(np.count_nonzero(values == value))) for value in sorted(set(values))]
            checks.equal(distribution, record[level][kind+'_count_distribution'], label+'/'+level+'/'+kind+'/distribution')
        for axis in range(candidates.shape[1]):
            audit_bernoulli(rebuilt[level+'_coordinate_counts'][:, axis]>1,
                record[level]['coordinate_multiple'][axis], checks, label+f'/{level}/axis{axis}')


def audit_family(folder, family, specification, config, tables, checks):
    source_folder = ARTIFACT/specification['stage']
    source_config = read_json(source_folder/'registration.json')['config']
    source_result = read_json(source_folder/'results.json')
    source_rows = indexed(read_json(source_folder/'cases.json'), ['method', 'repeats', 'condition'])
    with np.load(source_folder/specification['observations'], allow_pickle=False) as archive:
        candidates = archive['candidates'].copy()
        slices = {split:archive[split+'_slices'].copy() for split in ('calibration', 'evaluation')}
    with np.load(source_folder/'likelihoods.npz', allow_pickle=False) as archive:
        likelihood = archive[specification['likelihood_key']].copy()
    repeats, maximum = source_config['repeats'], max(source_config['repeats'])
    offset = int(slices['calibration'][0, 0])
    grouped = {}
    for split in slices:
        for repeat in repeats:
            grouped[split, repeat] = np.array([prefix_sum(likelihood[a-offset:b-offset],
                source_config[split+'_groups'], maximum, repeat) for a, b in slices[split]])
    oracle = read_npz(folder/f'oracle_{family}.npz')
    mle = read_npz(folder/f'known_eta_mle_{family}.npz')
    pairs = known_eta_pairs(candidates)
    allowed = same_nuisance(candidates)
    for name, saved in [('oracle', oracle), ('mle', mle)]:
        checks.equal(candidates, saved['candidates'], family+'/'+name+'/candidates')
        checks.equal(repeats, saved['repeats'], family+'/'+name+'/repeats')
    checks.equal(pairs, oracle['pair_indices'], family+'/pairs')
    checks.equal(allowed, mle['allowed_candidate_mask'], family+'/known_eta_mask')
    methods = source_result['methods']
    original = {}
    calibrations = read_json(source_folder/'calibration.json')
    maximum_objective_error, maximum_calibration_error = 0., 0.
    row_counts = dict(oracle_pairs=0, paired_decisions=0, known_eta_mle=0, paired_estimation=0, ambiguity=0, moment_equivalence=0)
    for repeat in repeats:
        for method in methods:
            calibration = read_npz(source_folder/f'calibration_{method}_R{repeat}.npz')['objectives']
            maximum_calibration_error = max(maximum_calibration_error, audit_calibration(calibration,
                candidates, source_config['alpha'], calibrations[f'{method}_R{repeat}'], checks, f'{family}/{method}/R{repeat}/calibration'))
            if method == specification['reference_method']:
                error = float(np.max(abs(calibration+2*grouped['calibration', repeat])))
                maximum_objective_error = max(maximum_objective_error, error)
                checks.close(calibration, -2*grouped['calibration', repeat], family+'/reference_calibration',
                             atol=config['saved_objective_absolute_tolerance'], rtol=0.)
            for condition in range(len(candidates)):
                label = f'{family}/{method}/R{repeat}/c{condition}'
                filename = f'evaluation_{method}_R{repeat}_c{condition:02d}.npz'
                raw = read_npz(source_folder/filename)
                original[method, repeat, condition] = dict(indices=raw['indices'], rejected=raw['rejected'])
                record = tables['ambiguity'][family, method, repeat, condition]
                saved = read_npz(folder/f'ambiguity_{family}_{method}_R{repeat}_c{condition:02d}.npz')
                audit_ambiguity(raw['objective'], candidates, raw, record, saved,
                    config['machine_epsilon_multiplier'], checks, label)
                checks.equal(filename, record['source_file'], label+'/source_file')
                checks.equal(candidates[condition], record['public_truth'], label+'/truth')
                checks.equal(specification['stage'], record['source_stage'], label+'/source_stage')
                audit_structural(record['structural_status'], family, method, checks, label)
                source_row = source_rows[method, repeat, condition]
                checks.equal(source_row['unidentifiable_coordinates'], record['original_unidentifiable_coordinates'], label+'/inherited_coordinates')
                checks.equal(int(raw['rejected'].sum()), source_row['rejections'], label+'/original_rejections')
                if not source_row['randomized_information_free_baseline']:
                    statistic = raw['objective'][:, candidates[:, 0] == candidates[:, 0].min()].min(axis=1)-raw['objective'].min(axis=1)
                    checks.equal(statistic>calibrations[f'{method}_R{repeat}']['detection_cutoff'], raw['rejected'], label+'/original_decisions')
                if method == specification['reference_method']:
                    reference = -2*grouped['evaluation', repeat][condition]
                    maximum_objective_error = max(maximum_objective_error, float(np.max(abs(raw['objective']-reference))))
                    checks.close(raw['objective'], reference, label+'/reference_objective', atol=config['saved_objective_absolute_tolerance'], rtol=0.)
                row_counts['ambiguity'] += 1
    for ri, repeat in enumerate(repeats):
        for pi, (null, alt) in enumerate(pairs):
            label = f'{family}/pair{pi}/R{repeat}'
            row = tables['oracle'][family, pi, repeat]
            llr = {}
            for role, condition, split, key in [('calibration', null, 'calibration', 'calibration_llr'),
                    ('null', null, 'evaluation', 'evaluation_null_llr'), ('alt', alt, 'evaluation', 'evaluation_alt_llr')]:
                density = grouped[split, repeat][condition]
                llr[role] = density[:, alt]-density[:, null]
                numerical(checks, llr[role], oracle[key][ri, pi], label+'/'+key)
            threshold, rank = cutoff(llr['calibration'], source_config['alpha'])
            for value, expected, suffix in [(rank, oracle['ranks'][ri, pi], 'raw_rank'), (rank, row['rank'], 'rank'),
                (null, row['null_condition'], 'null_id'), (alt, row['alt_condition'], 'alt_id'),
                (len(llr['calibration']), row['calibration_groups'], 'calibration_denominator')]:
                checks.equal(value, expected, label+'/'+suffix)
            numerical(checks, threshold, oracle['cutoffs'][ri, pi], label+'/raw_cutoff')
            numerical(checks, threshold, row['cutoff'], label+'/cutoff')
            numerical(checks, source_config['alpha'], row['alpha'], label+'/alpha')
            numerical(checks, (len(llr['calibration'])+1-rank)/(len(llr['calibration'])+1), row['calibration_marginal_error_bound'], label+'/rank_bound')
            checks.equal(candidates[null], row['null_theta'], label+'/null_theta')
            checks.equal(candidates[alt], row['alt_theta'], label+'/alt_theta')
            checks.equal(specification['reference_method'], row['reference_method'], label+'/reference_method')
            for role, condition, key in [('null', null, 'false_alarm'), ('alt', alt, 'power')]:
                rejected = llr[role]>threshold
                checks.equal(rejected, oracle[role+'_rejected'][ri, pi], label+'/'+role+'/raw_decisions')
                audit_bernoulli(rejected, row[key], checks, label+'/'+key)
                audit_mean(llr[role], row[role+'_llr'], checks, label+'/'+role+'/llr')
                for method in methods:
                    record = tables['paired'][family, pi, repeat, role, method]
                    old = original[method, repeat, int(condition)]['rejected']
                    paired = paired_counts(rejected, old)
                    for name, value in [('both_reject', paired['table'][1, 1]), ('oracle_only', paired['table'][1, 0]),
                                        ('original_only', paired['table'][0, 1]), ('neither', paired['table'][0, 0]), ('groups', len(old)),
                                        ('condition', condition), ('null_condition', null), ('alt_condition', alt)]:
                        checks.equal(value, record[name], label+'/'+role+'/'+method+'/'+name)
                    audit_bernoulli(rejected, record['oracle'], checks, label+'/'+role+'/'+method+'/oracle')
                    audit_bernoulli(old, record['original'], checks, label+'/'+role+'/'+method+'/original')
                    audit_mean(rejected.astype(float)-old.astype(float), record['oracle_minus_original'], checks, label+'/'+role+'/'+method+'/difference')
                    row_counts['paired_decisions'] += 1
            row_counts['oracle_pairs'] += 1
        for condition in range(len(candidates)):
            label = f'{family}/known_eta/R{repeat}/c{condition}'
            ids = np.flatnonzero(allowed[condition])
            likelihood_rows = grouped['evaluation', repeat][condition]
            selected = ids[np.argmax(likelihood_rows[:, ids], axis=1)]
            checks.equal(selected, mle['selected_indices'][ri, condition], label+'/selected')
            record = tables['mle'][family, repeat, condition]
            coordinate, truth = candidates[selected, 0], candidates[condition, 0]
            delta = np.sqrt(coordinate) if specification['interest'] == 'q' else coordinate
            true_delta = np.sqrt(truth) if specification['interest'] == 'q' else truth
            squared = (delta-true_delta)**2
            checks.equal(ids, record['allowed_candidate_ids'], label+'/allowed')
            checks.equal(len(selected), record['groups'], label+'/groups')
            checks.equal(candidates[condition], record['public_truth'], label+'/truth')
            for key, value in [('target_coordinate_rmse', np.sqrt(np.mean((coordinate-truth)**2))),
                    ('target_coordinate_bias', np.mean(coordinate-truth)), ('delta_rmse', np.sqrt(squared.mean())),
                    ('delta_bias', np.mean(delta-true_delta))]:
                numerical(checks, value, record[key], label+'/'+key)
            audit_mean(squared, record['delta_mse'], checks, label+'/delta_mse')
            boundary = (coordinate == candidates[ids, 0].min())|(coordinate == candidates[ids, 0].max())
            audit_bernoulli(boundary, record['interest_boundary'], checks, label+'/boundary')
            row_counts['known_eta_mle'] += 1
            for method in methods:
                paired = tables['mle_paired'][family, method, repeat, condition]
                source = source_rows[method, repeat, condition]
                numerical(checks, np.sqrt(squared.mean()), paired['oracle_delta_rmse'], label+'/'+method+'/oracle_rmse')
                checks.equal(source['target_identifiable'], paired['original_target_identifiable'], label+'/'+method+'/identified')
                if source['target_identifiable']:
                    old_values = candidates[original[method, repeat, condition]['indices'], 0]
                    if specification['interest'] == 'q':
                        old_values = np.sqrt(old_values)
                    old_squared = (old_values-true_delta)**2
                    numerical(checks, np.sqrt(old_squared.mean()), paired['original_delta_rmse'], label+'/'+method+'/original_rmse')
                    numerical(checks, np.sqrt(old_squared.mean()), source['half_gap_rmse'], label+'/'+method+'/source_rmse')
                    audit_mean(squared-old_squared, paired['oracle_minus_original_squared_error'], checks, label+'/'+method+'/paired_mse')
                else:
                    checks.equal(None, paired['original_delta_rmse'], label+'/'+method+'/undefined_rmse')
                    checks.equal(None, paired['oracle_minus_original_squared_error'], label+'/'+method+'/undefined_difference')
                row_counts['paired_estimation'] += 1
    for method in specification['moment_methods']:
        label = family+'/'+method+'/criterion'
        bank = read_npz(source_folder/f'bank_{method}.npz')
        means, precision = bank['means'], bank['inverse']
        weighted = np.einsum('ij,jk->ik', means, precision)
        coefficients = np.column_stack([weighted, np.einsum('ij,ij->i', means, weighted)])
        saved = read_npz(folder/f'moment_equivalence_{family}_{method}.npz')
        numerical(checks, coefficients, saved['coefficient_rows'], label+'/coefficients')
        # Exact equality is explicitly defined on stored floating coefficients,
        # after independent verification of their source-array contractions.
        rebuilt = equivalence(saved['coefficient_rows'], config['machine_epsilon_multiplier'])
        for key, value in rebuilt.items():
            checks.equal(value, saved[key], label+'/'+key)
        record = tables['equivalence'][family, method]
        classes = [np.flatnonzero(rebuilt['exact_class_ids'] == i).tolist() for i in range(int(rebuilt['exact_class_ids'].max())+1)]
        neighbors = [np.flatnonzero(row).tolist() for row in rebuilt['nearby_matrix']]
        audit_groups(classes, record['exact_classes'], checks, label+'/classes')
        audit_groups(neighbors, record['nearby_candidate_sets'], checks, label+'/neighbors')
        checks.equal(len(classes), record['exact_class_count'], label+'/class_count')
        audit_structural(record['structural_status'], family, method, checks, label)
        row_counts['moment_equivalence'] += 1
    return dict(family=family, rows=row_counts, pair_count=len(pairs), source_objective_maximum_error=maximum_objective_error,
                source_calibration_maximum_error=maximum_calibration_error)


def calculate(output, input_stage):
    folder = ARTIFACT/input_stage
    config = read_json(folder/'registration.json')['config']
    stages = [folder]
    stages.extend(ARTIFACT/spec['stage'] for spec in config['inputs'].values())
    before = audit_hashes(stages)
    checks = Checks()
    try:
        definitions = {
            'oracle':('oracle_pairs.json', ['family', 'pair_id', 'repeats']),
            'paired':('paired_cases.json', ['family', 'pair_id', 'repeats', 'role', 'method']),
            'mle':('known_eta_mle_cases.json', ['family', 'repeats', 'condition']),
            'mle_paired':('mle_paired_cases.json', ['family', 'method', 'repeats', 'condition']),
            'ambiguity':('ambiguity_cases.json', ['family', 'method', 'repeats', 'condition']),
            'equivalence':('moment_equivalence.json', ['family', 'method']),
        }
        tables = {key:indexed(read_json(folder/name), fields) for key, (name, fields) in definitions.items()}
        audits = indexed(read_json(folder/'input_audit.json'), ['family'])
        checks.equal(sorted(key[0] for key in audits), sorted(config['inputs']), 'all_input_families')
        for family, specification in config['inputs'].items():
            source = ARTIFACT/specification['stage']
            record = audits[family,]
            checks.equal(specification['stage'], record['stage'], family+'/bound_stage')
            checks.equal(specification['records'], record['bound_records'], family+'/bound_record_digests')
            for name in ('registration.json', 'attempt.json'):
                checks.equal(sha(source/name), specification['records'][name], family+'/'+name+'/binding')
            checks.equal(read_json(source/'registration.json')['git_head'], specification['records']['git_head'], family+'/bound_commit')
            for name, digest in record['checked_artifacts'].items():
                checks.equal(sha(resolve(name)), digest, family+'/checked_artifact/'+name)
            source_result = read_json(source/'results.json')
            qualification = (source_result['reference_qualification'] if family == 'actual' else
                             dict(independent_reference_max_error=source_result['independent_reference_max_error']))
            checks.equal(qualification, record['reference_qualification'], family+'/inherited_reference')
            checks.equal(len(read_json(source/'cases.json')), record['complete_original_rows'], family+'/original_row_count')
        reports = [audit_family(folder, family, specification, config, tables, checks)
                   for family, specification in config['inputs'].items()]
        for report in reports:
            checks.equal(report['pair_count'], audits[report['family'],]['pairs'], report['family']+'/input_pair_count')
        counts = {key:sum(report['rows'][key] for report in reports) for key in config['expected_rows']}
        checks.equal(counts, config['expected_rows'], 'complete_row_coverage')
        names = dict(oracle='oracle_pairs', paired='paired_decisions', mle='known_eta_mle',
                     mle_paired='paired_estimation', ambiguity='ambiguity', equivalence='moment_equivalence')
        for name, key in names.items():
            checks.equal(len(tables[name]), counts[key], name+'/no_missing_or_extra_rows')
        result = read_json(folder/'results.json')
        checks.equal('oracle-identifiability/1', result['schema'], 'input_schema')
        checks.equal(counts, result['rows'], 'reported_row_coverage')
        checks.equal(counts['ambiguity'], result['complete_original_evaluation_rows'], 'complete_original_rows')
        maximum_objective = max(report['source_objective_maximum_error'] for report in reports)
        maximum_calibration = max(report['source_calibration_maximum_error'] for report in reports)
        numerical(checks, maximum_objective, result['saved_objective_maximum_error'], 'maximum_source_objective_error')
        numerical(checks, maximum_calibration, result['original_calibration_maximum_error'], 'maximum_source_calibration_error')
        for key in ('new_observations', 'new_scientific_nodes', 'new_scientific_rules', 'receiver_calls', 'decoder_calls', 'failures'):
            checks.equal(0, result[key], 'input/'+key)
        after = audit_hashes(stages)
        checks.equal(before, after, 'input_hashes_unchanged')
        summary = dict(**checks.result(), input_stage=input_stage, families=reports, input_hashes=before,
            new_observations=0, new_scientific_nodes=0, new_scientific_rules=0,
            own_attempt_cost_separate=True, full_statistical_replay=True, new_integration=False)
        dump(output/'supplement_audit.json', summary)
        if checks.failures:
            raise AssertionError(f'{len(checks.failures)} independent supplement checks failed')
        return summary
    finally:
        dump(output/'checks.json', checks.result())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--input-stage', required=True)
    args = parser.parse_args()
    if Path(args.input_stage).name != args.input_stage:
        raise ValueError('input stage must be a single stage name')
    folder = ARTIFACT/args.input_stage
    registration = read_json(folder/'registration.json')
    sources = [Path(__file__), Path(__file__).with_name('test_supplement_audit.py'),
               Path(__file__).with_name('SUPPLEMENT_AUDIT.md'), PROTECTED,
               folder/'registration.json', folder/'attempt.json']
    sources.extend(loaded_project_sources(sys.modules))
    config = dict(seed=[20261005, 104835, 71], new_observations=0, new_scientific_nodes=0,
        new_scientific_rules=0, input_stage=args.input_stage,
        input_registration_sha256=sha(folder/'registration.json'), input_attempt_sha256=sha(folder/'attempt.json'),
        expected_rows=registration['config']['expected_rows'], receiver_calls=0, decoder_calls=0,
        full_statistical_replay=True, own_attempt_cost_separate=True)
    def callback(output):
        return calculate(output, args.input_stage)
    run(args.stage, config, sources, callback, wall_seconds=60)


if __name__ == '__main__':
    main()
