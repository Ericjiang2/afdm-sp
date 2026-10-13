"""Selected independent development cohort; the original 84 comparisons stay immutable."""
import argparse
import importlib.util
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

from experiments.afdm_method_advantage import analysis as saved
from experiments.afdm_method_advantage.protocol import ARTIFACT, ROOT, dump, run

CONFIG_PATH = ARTIFACT/'SUPPLEMENT_CONFIG.json'
STUDY_PATH = Path(__file__).with_name('study.py')
METHODS_PATH = Path(__file__).with_name('methods.py')
STAGES = dict(null='supplementary_null_v1', alt='supplementary_alt_v1', summary='supplement_summary_v1')
REFERENCE_FILES = dict(calibration_reference='calibration.json', primary_metrics_reference='metrics.json',
                       primary_costs_reference='costs.json')


def validate_config(config, primary):
    if config['schema'] != 'method-advantage-supplement/1' or config['repeats'] != [256]:
        raise ValueError('registered supplement schema and R=256 required')
    if type(config['evaluation_groups']) is not int or config['evaluation_groups'] <= 0:
        raise ValueError('positive independent evaluation group count required')
    for field in ('methods', 'method_config', 'null_points', 'calibration_groups', 'alpha', 'failure_policy'):
        if config[field] != primary[field]:
            raise ValueError(f'supplement changed the frozen primary {field}')
    if config['seed'] == primary['seed']:
        raise ValueError('supplement requires a distinct registered seed')
    if (not config['seed'] or any(type(value) is not int or value < 0 for value in config['seed'])
            or not config['selection']):
        raise ValueError('explicit selection and nonnegative seed integers required')
    points = config['evaluation_points']
    if len(points) != 2 or points[0]['role'] != 'selected_fresh_null' or points[1]['role'] != 'selected_finite_separation':
        raise ValueError('exactly the registered selected null/alternative pair is required')
    for point in points:
        for name in ('mu', 'tau', 'sigma2', 'delta'):
            saved.finite(point[name], 'selected point '+name)
        if point['tau'] <= 0 or point['sigma2'] <= 0:
            raise ValueError('positive selected-point scales required')
    if points[0]['delta'] != 0 or points[1]['delta'] <= 0 or any(points[0][key] != points[1][key] for key in ('mu', 'tau', 'sigma2')):
        raise ValueError('selected null and alternative must differ only in separation/role')
    if saved.point_key(points[0]) not in {saved.point_key(point) for point in config['null_points']}:
        raise ValueError('selected fresh null is not on the original public calibration grid')
    comparison = config['comparison']
    if (comparison['candidate'] != 'moment_score' or comparison['baselines'] != ['moment_j', 'full_score']
            or comparison['family_size'] != 2):
        raise ValueError('supplement has exactly two registered paired hypotheses')
    for field in ('confidence', 'minimum_power_gain', 'noninferiority_margin',
                  'minimum_useful_power_lower', 'null_wilson_upper_limit'):
        if not 0 < saved.finite(comparison[field], field) < 1:
            raise ValueError('comparison probabilities and margins must be in (0,1)')
    if saved.finite(comparison['minimum_cost_ratio'], 'minimum cost ratio') <= 1:
        raise ValueError('registered cost ratio must exceed one')
    if config['new_confirmation_stream'] or config['receiver_calls'] != 0 or config['decoder_calls'] != 0:
        raise ValueError('supplement remains local development only')


def bind_reference(config):
    folder = ARTIFACT/'summary_v1'
    for field, name in REFERENCE_FILES.items():
        if (ROOT/config[field]).resolve() != (folder/name).resolve():
            raise ValueError('supplement references must identify the unchanged original summary')
    registration = saved.read_json(folder/'registration.json')
    attempt = saved.read_json(folder/'attempt.json')
    if attempt['status'] != 'complete' or registration['config']['mode'] != 'analysis':
        raise ValueError('original summary must be complete before selecting a supplement')
    validate_config(config, registration['config']['frozen_config'])
    names = ['registration.json', 'attempt.json', 'results.json', *REFERENCE_FILES.values()]
    binding = dict(path=str(folder.relative_to(ROOT)), stage=folder.name,
        metadata_sha256={name:saved.sha(folder/name) for name in names}, artifact_sha256=attempt['artifact_sha256'])
    verify_reference(binding)
    return binding


def verify_reference(binding):
    folder = ROOT/binding['path']
    for name, digest in binding['metadata_sha256'].items():
        if saved.sha(folder/name) != digest:
            raise ValueError('bound primary reference changed: '+name)
    attempt = saved.read_json(folder/'attempt.json')
    if attempt['status'] != 'complete' or attempt['artifact_sha256'] != binding['artifact_sha256']:
        raise ValueError('bound primary completion manifest changed')
    actual = {path.resolve() for path in folder.rglob('*') if path.is_file() and path.name != 'attempt.json'}
    if actual != {(ROOT/name).resolve() for name in binding['artifact_sha256']}:
        raise ValueError('primary reference artifact inventory changed')
    for name, digest in binding['artifact_sha256'].items():
        if saved.sha(ROOT/name) != digest:
            raise ValueError('bound primary artifact changed: '+name)
    return dict(metadata=len(binding['metadata_sha256']), artifacts=len(binding['artifact_sha256']))


def read_calibration(config, reference):
    folder = ROOT/reference['path']
    thresholds, costs = {}, {}
    for filename, target in (('calibration.json', thresholds), ('costs.json', costs)):
        for row in saved.read_json(folder/filename):
            key = row['repeats'], row['method']
            if key in target:
                raise ValueError('duplicate original calibration/cost row')
            target[key] = row
    selected_thresholds, selected_costs = {}, {}
    for method in config['methods']:
        key = (256, method)
        threshold, cost = thresholds[key], costs[key]
        grid = threshold['null_grid']
        if len(grid) != len(config['null_points']):
            raise ValueError('original threshold does not cover the full public null grid')
        for condition, row in enumerate(grid):
            if (row['condition'] != condition or row['point'] != config['null_points'][condition]
                    or row['groups'] != config['calibration_groups']
                    or row['order_index_one_based'] != math.ceil((row['groups']+1)*(1-config['alpha']))
                    or row['comparison'] != 'strictly greater'):
                raise ValueError('original calibration allocation/rank rule changed')
        finite = all(row['finite_threshold'] for row in grid)
        expected = max(row['threshold'] for row in grid) if finite else None
        if (threshold['finite_threshold'] != finite or threshold['threshold'] != expected
                or threshold['failed'] != sum(row['failed'] for row in grid)):
            raise ValueError('original robust threshold/failure aggregate is inconsistent')
        if cost['calibration_groups'] != len(grid)*config['calibration_groups']:
            raise ValueError('old calibration cost workload changed')
        for name in ('calibration_path_seconds', 'calibration_setup_seconds', 'calibration_seconds'):
            saved.finite(cost[name], name, True)
        if not math.isclose(cost['calibration_seconds'], cost['calibration_path_seconds']+cost['calibration_setup_seconds'], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError('old calibration path/setup accounting is inconsistent')
        selected_thresholds[key], selected_costs[key] = threshold, cost
    return selected_thresholds, selected_costs


def implementation_hashes():
    return {str(path.relative_to(ROOT)):saved.sha(path) for path in (STUDY_PATH, METHODS_PATH)}


def bind_cohort(config, reference):
    bindings = []
    implementation = implementation_hashes()
    groups, repeat = config['evaluation_groups'], config['repeats'][0]
    for condition, phase in enumerate(('null', 'alt')):
        folder = ARTIFACT/STAGES[phase]
        registration, attempt = saved.read_json(folder/'registration.json'), saved.read_json(folder/'attempt.json')
        specification = registration['config']
        if (attempt['status'] != 'complete' or specification['mode'] != 'evaluation'
                or specification['cohort'] != 'selected_supplement' or specification['phase'] != phase
                or specification['condition'] != condition or specification['frozen_config'] != config
                or specification['reference_binding'] != reference or specification['implementation_sha256'] != implementation):
            raise ValueError('incomplete/mismatched supplementary source; no fallback to a primary stage')
        for name, digest in implementation.items():
            if registration['source_sha256'].get(name) != digest:
                raise ValueError('supplementary study/method implementation was not source-bound')
        result = saved.read_json(folder/'results.json')
        if (result['mode'] != 'evaluation' or result['condition'] != condition
                or result['points'] != [config['evaluation_points'][condition]] or result['groups'] != groups
                or result['records'] != groups or result['new_observations'] != groups*repeat
                or specification['new_observations'] != groups*repeat
                or attempt['reserved_new_observations'] != groups*repeat):
            raise ValueError('supplementary source has incomplete or changed group/observation allocation')
        names = ['registration.json', 'attempt.json', 'results.json', 'generation.json', saved.records_path(folder).name]
        bindings.append(dict(path=str(folder.relative_to(ROOT)), stage=folder.name, mode='evaluation', condition=condition,
            git_head=registration['git_head'], metadata_sha256={name:saved.sha(folder/name) for name in names},
            artifact_sha256=attempt['artifact_sha256']))
    saved.verify_inputs(bindings)
    return bindings


def study_instance(phase):
    if phase not in ('null', 'alt'):
        raise ValueError('study execution is restricted to the registered two new cohorts')
    spec = importlib.util.spec_from_file_location('_method_advantage_supplement_study', STUDY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CONFIG_PATH = CONFIG_PATH
    module.ARGS = SimpleNamespace(mode='evaluation', condition=0 if phase == 'null' else 1, replay_qualification=None)
    return module


def saved_r_diagnostics(records, method):
    if method not in ('moment_score', 'full_score'):
        return None
    values = [row['r_hat'][method] for row in records if row['r_hat'][method] is not None]
    return dict(available=len(values), missing=len(records)-len(values),
        unconstrained=saved.numeric_summary([row['unconstrained'] for row in values]),
        one_sided=saved.numeric_summary([row['one_sided'] for row in values]),
        fitted_delta_branch_radius=saved.numeric_summary([row['fitted_delta_branch_radius'] for row in values]),
        r_branch_max=saved.numeric_summary([row['r_branch_max'] for row in values]),
        outside_fitted_local_branch=sum(row['outside_fitted_local_branch'] for row in values),
        unconstrained_below_zero=sum(row['unconstrained_below_zero'] for row in values),
        scope='saved local-coordinate diagnostics; no physical separation estimate or finite-separation accuracy claim')


def cost_analysis(datasets, calibration_costs, config):
    groups, denominator = config['evaluation_groups'], 2*config['evaluation_groups']
    totals, per_point, actual = {}, {}, []
    for method in config['methods']:
        old = calibration_costs[256, method]
        paths = [saved.path_cost(datasets['evaluation', condition], 256, method, groups) for condition in (0, 1)]
        calibration = old['calibration_seconds']
        evaluation = math.fsum(path['standalone_seconds'] for path in paths)
        totals[256, method] = dict(method=method, repeats=256, evaluation_groups=denominator,
            calibration_groups=old['calibration_groups'], calibration_seconds=calibration,
            calibration_path_seconds=old['calibration_path_seconds'], calibration_setup_seconds=old['calibration_setup_seconds'],
            calibration_amortized_seconds=calibration/denominator, evaluation_seconds=evaluation,
            fixed_workload_seconds=calibration+evaluation, fixed_workload_amortized_seconds=(calibration+evaluation)/denominator,
            scope='old complete calibration charged again as a standalone method cost over this fixed supplementary workload; no new calibration execution')
        for condition, path in enumerate(paths):
            per_point[condition, 256, method] = dict(**path,
                calibration_allocation_denominator=denominator, calibration_allocation_seconds_per_group=calibration/denominator,
                complete_amortized_seconds_per_group=path['amortized_seconds_per_group']+calibration/denominator)
    for condition in (0, 1):
        dataset = datasets['evaluation', condition]
        rows, attempt = list(dataset['records'].values()), dataset['attempt']
        actual.append(dict(condition=condition, stage=dataset['binding']['stage'], generation_seconds=dataset['generation']['seconds'],
            actual_joint_setup_seconds=math.fsum(row['costs']['setup_seconds'] for row in rows),
            actual_joint_inference_seconds=math.fsum(row['costs']['joint_complete_seconds'] for row in rows),
            caller_complete_seconds=math.fsum(row['complete_seconds'] for row in rows),
            shared_json_conversion_seconds=math.fsum(row['costs']['shared_result_conversion_seconds'] for row in rows),
            wall_seconds=attempt['wall_seconds'], cpu_seconds=attempt['cpu_seconds'],
            reserved_wall_seconds=attempt['reserved_wall_seconds'], reserved_new_observations=attempt['reserved_new_observations']))
    return totals, per_point, actual


def compare(metrics, decisions, thresholds, costs, config):
    specification, output = config['comparison'], []
    candidate = specification['candidate']
    useful = metrics[1, 256, candidate]['clopper_pearson']['lower'] > specification['minimum_useful_power_lower']
    for baseline in specification['baselines']:
        c, b = decisions[1, 256, candidate], decisions[1, 256, baseline]
        paired = saved.paired_interval(c['rejected'], b['rejected'], specification['family_size'], specification['confidence'])
        null = [metrics[0, 256, method] for method in (candidate, baseline)]
        null_ok = all(row['wilson']['upper'] <= specification['null_wilson_upper_limit'] for row in null)
        failures = dict(candidate_alternative=int(c['failed'].sum()), baseline_alternative=int(b['failed'].sum()),
            candidate_calibration=thresholds[256, candidate]['failed'], baseline_calibration=thresholds[256, baseline]['failed'],
            fresh_null=sum(row['statistic_failures'] for row in null))
        no_failures = not any(failures.values())
        finite_thresholds = all(thresholds[256, method]['finite_threshold'] for method in (candidate, baseline))
        cc = costs[1, 256, candidate]['complete_amortized_seconds_per_group']
        bc = costs[1, 256, baseline]['complete_amortized_seconds_per_group']
        ratio = bc/cc if cc > 0 else None
        power = paired['difference'] >= specification['minimum_power_gain'] and paired['lower'] > 0
        noninferior = paired['lower'] > -specification['noninferiority_margin']
        fast = ratio is not None and ratio >= specification['minimum_cost_ratio']
        output.append(dict(candidate=candidate, baseline=baseline, repeats=256, condition=1,
            hypothesis='power_gain' if baseline == 'moment_j' else 'useful_cost_noninferiority', paired=paired,
            failure_difference_bounds=saved.failure_difference_bounds(c['rejected'], b['rejected'], c['failed'], b['failed']),
            failures=failures, no_failures=no_failures, finite_thresholds=finite_thresholds, null_gate_passed=null_ok,
            null_checks=[dict(method=row['method'], wilson_upper=row['wilson']['upper'], failures=row['statistic_failures']) for row in null],
            useful_power_passed=bool(useful), useful_power_cp=metrics[1, 256, candidate]['clopper_pearson'],
            power_numeric_criterion=bool(power), noninferiority_passed=bool(noninferior), cost_ratio_passed=bool(fast),
            candidate_amortized_seconds=cc, baseline_amortized_seconds=bc, cost_ratio=ratio,
            power_advantage=bool(baseline == 'moment_j' and power and null_ok and no_failures and finite_thresholds),
            useful_cost_advantage=bool(baseline == 'full_score' and noninferior and fast and useful and null_ok and no_failures and finite_thresholds),
            interval_scope='paired bounds simultaneous over the two selected hypotheses; rate CP/Wilson intervals are pointwise conditional on the old calibration library',
            selection=config['selection'], cost_scope='fixed local algorithm workload including own fit, setup and old full calibration; not deployment latency'))
    return output


def report(config, metrics, comparisons, totals):
    lines = ['# 独立开发补充验证', '', config['selection'], '',
        '这两组新数据只验证主结果后选定的同一 null/备择；旧 84 比较及其原始数据保持不变。',
        '阈值原样复用旧公共 8 点校准；新 null 数据只评估误报，不能调整阈值。', '',
        '| 条件 | 方法 | 拒绝/组数 | 比率 | 95% CP 下界 | 95% Wilson 上界 | 失败 |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for row in metrics.values():
        lines.append(f"| {row['condition']} | {row['method']} | {row['rejections']}/{row['groups']} | {row['rate']:.6g} | {row['clopper_pearson']['lower']:.6g} | {row['wilson']['upper']:.6g} | {row['statistic_failures']} |")
    lines += ['', '| 对照 | 配对点差 | 家族 2 下界 | 成本倍率 | null 门槛 | 有用功效门槛 | 注册优势 |',
        '| --- | ---: | ---: | ---: | --- | --- | --- |']
    for row in comparisons:
        lines.append(f"| {row['baseline']} | {row['paired']['difference']:.6g} | {row['paired']['lower']:.6g} | {row['cost_ratio']} | {row['null_gate_passed']} | {row['useful_power_passed']} | {row['power_advantage'] or row['useful_cost_advantage']} |")
    lines += ['', f"配对差使用 2 项比较的四尾 Bonferroni–CP（每尾 {(1-config['comparison']['confidence'])/8:.6g}）。",
        '有用功效使用双侧 95% CP 下界（每尾 .025）>.80；null 使用点位 95% Wilson 上界≤.10。这些区间的覆盖范围分别标注，不把全部门槛统称为同时 95%。',
        f"旧完整校准成本按本轮 {2*config['evaluation_groups']} 个评价组固定摊销；各方法承担自身拟合/统计路径和一次冷 setup，C2 无 NullFamily setup。", '',
        '| 方法 | 旧校准秒 | 新评价路径含 setup 秒 | 固定工作量秒/评价组 |',
        '| --- | ---: | ---: | ---: |']
    for row in totals.values():
        lines.append(f"| {row['method']} | {row['calibration_seconds']:.9g} | {row['evaluation_seconds']:.9g} | {row['fixed_workload_amortized_seconds']:.9g} |")
    lines += ['', 'standalone 路径不能相加为真实联合运行费用。真实联合计时、JSON 转换与 wall/CPU 在 actual_stage_costs.json 另列。',
        '失败评价作非拒绝并保留分母；未知失败结果上下界另列，含失败的参与方法不宣称优势。',
        'δ=.12 属有限分离压力测试，保存 signed/one-sided r 与分支标记，不作物理分离估计或 LAN 精度保证。',
        '本补充是选定点的本地 N4 开发证据，不是未选择复制、生产确认、连续 nuisance 保证或全备择最优性证明。', '']
    return '\n'.join(lines)


def calculate(output):
    specification = saved.read_json(output/'registration.json')['config']
    config, reference = specification['frozen_config'], specification['reference_binding']
    if saved.sha(CONFIG_PATH) != specification['supplement_config_sha256'] or saved.read_json(CONFIG_PATH) != config:
        raise ValueError('supplement configuration changed after registration')
    verify_reference(reference)
    if bind_reference(config) != reference:
        raise ValueError('old threshold/cost reference changed after registration')
    if specification['phase'] != 'summary':
        result = study_instance(specification['phase']).calculate(output)
        verify_reference(reference)
        return dict(**result, cohort='selected_supplement', phase=specification['phase'], selection=config['selection'])
    bindings = specification['source_bindings']
    if bind_cohort(config, reference) != bindings:
        raise ValueError('supplementary source bindings changed after registration')
    before = saved.verify_inputs(bindings)
    datasets = saved.load_records(bindings, config)
    thresholds, old_costs = read_calibration(config, reference)
    metrics, decisions = saved.rates(datasets, thresholds, config)
    totals, costs, actual = cost_analysis(datasets, old_costs, config)
    tail = (1-config['comparison']['confidence'])/2
    for key, row in metrics.items():
        row['clopper_pearson'] = dict(**saved.cp_bounds(row['rejections'], row['groups'], tail),
            confidence=config['comparison']['confidence'], tail_probability=tail, interval='two-sided exact pointwise')
        row['cost'] = costs[key]
        records = list(datasets['evaluation', row['condition']]['records'].values())
        row['saved_r_diagnostics'] = saved_r_diagnostics(records, row['method'])
        row['selected_point_on_original_grid'] = saved.point_key(row['point']) in {saved.point_key(point) for point in config['null_points']}
        row['finite_grid_theorem_applies'] = False
        row['selection_scope'] = 'selected after primary results; report fresh empirical null size, not a new unconditional adaptive-selection theorem'
    comparisons = compare(metrics, decisions, thresholds, costs, config)
    dump(output/'calibration.json', list(thresholds.values()))
    dump(output/'metrics.json', list(metrics.values()))
    dump(output/'comparisons.json', comparisons)
    dump(output/'costs.json', list(totals.values()))
    dump(output/'actual_stage_costs.json', actual)
    dump(output/'input_bindings.json', dict(reference_binding=reference, source_bindings=bindings, selection=config['selection']))
    shape = (2, len(config['methods']), config['evaluation_groups'])
    rejected, failed = np.empty(shape, bool), np.empty(shape, bool)
    for condition in (0, 1):
        for index, method in enumerate(config['methods']):
            rejected[condition, index] = decisions[condition, 256, method]['rejected']
            failed[condition, index] = decisions[condition, 256, method]['failed']
    np.savez_compressed(output/'decisions.npz', rejected=rejected, failed=failed, methods=np.asarray(config['methods']), repeats=np.array([256]))
    (output/'SUPPLEMENT_RESULTS.md').write_text(report(config, metrics, comparisons, totals))
    after = saved.verify_inputs(bindings)
    verify_reference(reference)
    if before != after or bind_cohort(config, reference) != bindings:
        raise ValueError('supplementary inputs changed during analysis')
    dump(output/'input_hash_counts.json', after)
    return dict(schema='method-advantage-supplement-analysis/1', mode='supplement_analysis', phase='summary',
        new_observations=0, new_scientific_nodes=0, new_scientific_rules=0, receiver_calls=0, decoder_calls=0,
        new_confirmation_stream=False, comparison_rows=len(comparisons), family_size=2, metric_rows=len(metrics),
        power_advantages=sum(row['power_advantage'] for row in comparisons),
        useful_cost_advantages=sum(row['useful_cost_advantage'] for row in comparisons),
        failed_method_groups=int(failed.sum()), source_hashes_unchanged=True, input_hash_counts=after,
        primary_84_comparisons_unchanged=True, selection=config['selection'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=list(STAGES), required=True)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--wall-seconds', type=int, default=120)
    args = parser.parse_args()
    if args.stage != STAGES[args.phase]:
        raise ValueError('phase must use its unique preregistered supplementary stage name')
    config = saved.read_json(CONFIG_PATH)
    reference = bind_reference(config)
    sources = [Path(__file__), Path(__file__).with_name('test_supplement.py'), CONFIG_PATH, STUDY_PATH, METHODS_PATH]
    sources.extend(ROOT/reference['path']/name for name in reference['metadata_sha256'])
    specification = dict(seed=config['seed'], phase=args.phase, frozen_config=config, cohort='selected_supplement',
        reference_binding=reference, supplement_config_sha256=saved.sha(CONFIG_PATH), implementation_sha256=implementation_hashes(),
        receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)
    if args.phase == 'summary':
        bindings = bind_cohort(config, reference)
        specification.update(mode='supplement_analysis', new_observations=0, source_bindings=bindings)
        for binding in bindings:
            sources.extend(ROOT/binding['path']/name for name in ('registration.json', 'attempt.json', 'generation.json', 'results.json'))
    else:
        engine = study_instance(args.phase)
        engine.frozen_components()
        sources.extend(engine.project_source_paths())
        specification.update(mode='evaluation', condition=0 if args.phase == 'null' else 1,
            new_observations=config['evaluation_groups']*256)
    sources.extend(saved.loaded_project_sources(sys.modules))
    run(args.stage, specification, sources, calculate, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
