"""Apply the frozen 18-endpoint cost design to fully audited 512-block data."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_json(path, expected):
    if sha(path) != expected:
        raise ValueError('bound cost input changed: '+str(path))
    return json.loads(Path(path).read_text())


def load_helpers(contract):
    modules = []
    for name in ('cost02-bootstrap-core-v1.py', 'cost02-formal-statistics-v1.py',
                 'analyze-cost02-formal-v1.py'):
        binding = contract['shared_helpers'][name]
        path = Path(binding['path'])
        if sha(path) != binding['sha256']:
            raise ValueError('frozen cost helper changed: '+name)
        spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def validate_design(contract):
    columns = [dict(index=i, snr_db=s, arm=a) for i, (s, a) in enumerate(
        (s, a) for s in (7, 8, 9) for a in ('I1', 'A2', 'B_star_1'))]
    if (contract['schema'] != 'adjacent-cost512-contract-v1' or contract['status'] != 'frozen'
            or contract['physical_N'] != 1024 or contract['n_per_snr'] != 512
            or contract['columns'] != columns or contract['new_F']['total'] != 4698
            or contract['ranges'] != dict(warmup=[1537, 1547], measurement=[1547, 2059])):
        raise ValueError('not the frozen three-arm 512-block cost design')
    expected = [(s, a, b, metric) for s in (7, 8, 9)
        for a, b in (('I1', 'A2'), ('B_star_1', 'A2'), ('I1', 'B_star_1'))
        for metric in ('mean', 'p95')]
    rows = contract['endpoints']
    if [(r['snr_db'], r['arm'], r['reference'], r['metric']) for r in rows] != expected:
        raise ValueError('cost endpoint inventory differs')
    for row in rows:
        arm, reference = columns[row['arm_column']], columns[row['reference_column']]
        if ((arm['snr_db'], arm['arm']) != (row['snr_db'], row['arm'])
                or (reference['snr_db'], reference['arm']) != (row['snr_db'], row['reference'])
                or row['exact_alias'] or not row['confirmatory_gate'] or row['original_threshold'] != 1.1):
            raise ValueError('cost endpoint mapping or threshold differs')
    settings = contract['statistical_settings']
    if (settings['endpoint_count'] != 18 or settings['n_per_snr'] != 512
            or settings['block_lengths'] != [8, 16, 32] or settings['total_resamples'] != 600000
            or settings['draws_per_seed'] != 100000 or settings['seeds_per_length'] != 2):
        raise ValueError('cost bootstrap size differs from frozen scope')
    return [(r['metric'], r['arm_column'], r['reference_column']) for r in rows]


def validate_matrix(x, blocks):
    if (x.shape != (512, 9) or not np.isfinite(x).all() or not (x > 0).all()
            or not np.array_equal(blocks, np.arange(1547, 2059))):
        raise ValueError('incomplete, invalid or unregistered chronological cost matrix')


def comparison_decisions(endpoints):
    decisions = {}
    expected = {(s, m) for s in (7, 8, 9) for m in ('mean', 'p95')}
    for arm, reference in (('I1', 'A2'), ('B_star_1', 'A2'), ('I1', 'B_star_1')):
        rows = [r for r in endpoints if (r['arm'], r['reference']) == (arm, reference)]
        if len(rows) != 6 or {(r['snr_db'], r['metric']) for r in rows} != expected:
            raise ValueError('incomplete three-SNR cost comparison')
        status = 'COST_PASS'
        if any(not r['valid_for_cost_decision'] for r in rows):
            status = 'INCONCLUSIVE'
        elif any(r['status'] != 'COST_PASS' for r in rows):
            status = 'COST_BOUND_EXCEEDS_LIMIT'
        decisions[arm+'_over_'+reference] = dict(status=status, cost_pass=status == 'COST_PASS',
            endpoint_ids=[r['id'] for r in rows],
            scope='Reduced three-arm cost rule only; no FER or legacy full-scope acceptance.')
    return decisions


def load_cost_inputs(args, contract):
    audit = checked_json(args.audit, args.audit_sha256)
    if (audit['schema'] != 'adjacent-reference-audit-v1' or audit['kind'] != 'cost-measurement'
            or audit['status'] != 'raw_integrity_passed' or audit['n_independent_blocks'] != 512
            or audit['attempted_F'] != 4608 or audit['completed_F'] != 4608
            or audit['columns'] != contract['columns'] or len(audit['records']) != 4608):
        raise ValueError('not a completed and raw-audited 512-block measurement')
    guards = {args.contract: args.contract_sha256, args.audit: args.audit_sha256}
    admission = args.root/'cost512-admission-v1.json'
    manifest = json.loads(admission.read_text())
    if manifest['cost_contract'] != dict(path=str(args.contract), sha256=args.contract_sha256):
        raise ValueError('cost producer was admitted under a different statistical contract')
    guards[admission] = sha(admission)
    for batch in ('cost-warmup', 'cost-measurement'):
        run = json.loads((args.root/batch/'run.json').read_text())
        if run['manifest_sha256'] != guards[admission] or run['cost_contract_sha256'] != args.contract_sha256:
            raise ValueError('warmup and measurement admission bindings differ')
    for stem in ('cost-warmup', 'cost-measurement', 'cost-warmup-audit-v1', 'cost-measurement-audit-v1'):
        if (args.root/(stem+'.exit')).read_text().strip() != '0':
            raise ValueError('cost producer or raw auditor did not exit successfully: '+stem)
    warm_path = args.root/'cost-warmup-audit-v1/audit.json'
    warm = json.loads(warm_path.read_text())
    if (warm['kind'] != 'cost-warmup' or warm['status'] != 'raw_integrity_passed'
            or warm['attempted_F'] != 90 or warm['completed_F'] != 90):
        raise ValueError('all 90 warmup calls must be audited too')
    guards[warm_path] = sha(warm_path)
    for report, path in ((audit, args.audit), (warm, warm_path)):
        lock = path.parent/'output-lock.json'
        if sha(lock) != report['output_lock_sha256']:
            raise ValueError('raw output lock changed after audit')
        guards[lock] = report['output_lock_sha256']
    compact = Path(audit['compact']['path'])
    if compact != args.audit.parent/'compact.npz' or sha(compact) != audit['compact']['sha256']:
        raise ValueError('audited compact matrix differs')
    guards[compact] = audit['compact']['sha256']
    with np.load(compact, allow_pickle=False) as data:
        x, blocks = data['seconds'].copy(), data['blocks'].copy()
    validate_matrix(x, blocks)
    return audit, warm, x, guards


def cost_metadata(root, audit, warm):
    """Validate timer order and recover setup, memory and out-of-timer overhead."""
    from afdm_sp_joint_unrolled.supplement_data import campaign_rng
    from supplement_adjacent_cost_run import validate_telemetry
    bindings = {}
    for name in ('cost-warmup-audit-v1', 'cost-measurement-audit-v1'):
        lock = json.loads((root/name/'output-lock.json').read_text())
        bindings.update({r['path']: r['sha256'] for r in lock['files']})
    def read_metadata(path):
        return checked_json(path, bindings[str(path)])
    run = read_metadata(root/'cost-measurement/run.json')
    warm_run = read_metadata(root/'cost-warmup/run.json')
    if (sha(root/'cost-measurement/run.json') != audit['run_sha256']
            or sha(root/'cost-warmup/run.json') != warm['run_sha256']
            or (run['pid'], run['start_ticks']) != (warm_run['pid'], warm_run['start_ticks'])
            or run['setup_reused_from'] != 'cost-warmup'
            or not run['warmup_and_measurement_share_receiver_instances']):
        raise ValueError('warmup did not share the measured collector and receiver instances')
    memory = {str(c['index']): [] for c in audit['columns']}
    generation = raw_io = receiver_seconds = 0.
    last_end = None
    groups = []
    rows = {(r['block'], r['snr_db'], r['arm']): r for r in audit['records']}
    for block in range(1547, 2059):
        expected_order = campaign_rng('timing', block, 'order', family='F_C').permutation(
            ['I1', 'A2', 'B_star_1']).tolist()
        for snr in (7, 8, 9):
            cell = root/'cost-measurement'/f'b{block:06d}-s{snr}'
            meta = read_metadata(cell/'input.json')
            if meta['order'] != expected_order:
                raise ValueError('stored order differs from prospective random interleaving')
            generation += meta['generation_seconds']
            raw_io += meta['raw_save_seconds']
            starts, ends = [], []
            for arm in expected_order:
                row = rows[block, snr, arm]
                path = cell/(arm+'-r0.json')
                original = checked_json(path, row['meta_sha256'])
                if sha(cell/'input.json') != row['input_meta_sha256']:
                    raise ValueError('input metadata changed after audit')
                start = original['start_monotonic_seconds']
                if last_end is not None and start < last_end:
                    raise ValueError('receiver timer intervals overlap or are not chronological')
                last_end = start+original['seconds']
                starts.append(start)
                ends.append(last_end)
                receiver_seconds += original['seconds']
                raw_io += original['raw_save_seconds']
                column = 3*(snr-7)+['I1', 'A2', 'B_star_1'].index(arm)
                memory[str(column)].append({k: original[k] for k in ('peak_cuda_bytes',
                    'incremental_peak_cuda_bytes', 'cuda_allocated_before', 'peak_rss_kib')})
            groups.append(dict(block=block, snr_db=snr, start=starts[0], end=ends[-1], order=expected_order))
    snapshots = []
    for batch in ('cost-warmup', 'cost-measurement'):
        paths = sorted((root/batch).glob('telemetry-*.json'))
        if len(paths) != (10 if batch == 'cost-warmup' else 513):
            raise ValueError('incomplete cost boundary telemetry')
        for path in paths:
            state = read_metadata(path)
            validate_telemetry(state, run['pid'])
            snapshots.append(state)
    closures = {name: read_metadata(root/name/'complete.json')
                for name in ('cost-warmup', 'cost-measurement')}
    return dict(setup=warm_run, closures=closures,
        measured_receiver_seconds=receiver_seconds, measured_generation_seconds=generation,
        measured_raw_serialization_seconds=raw_io,
        measured_other_overhead_seconds=closures['cost-measurement']['elapsed_seconds']-receiver_seconds-generation-raw_io,
        memory={k: {name: max(row[name] for row in values) for name in values[0]}
                for k, values in memory.items()}, chronological_groups=groups,
        telemetry=dict(samples=len(snapshots), scope='Block boundaries only, not continuous monitoring.',
            temperature_C=[min(r['temperature_C'] for r in snapshots), max(r['temperature_C'] for r in snapshots)],
            SM_MHz=[min(r['SM_MHz'] for r in snapshots), max(r['SM_MHz'] for r in snapshots)],
            memory_MHz=[min(r['memory_MHz'] for r in snapshots), max(r['memory_MHz'] for r in snapshots)],
            maximum_load_average=max(r['load_average'][0] for r in snapshots),
            minimum_disk_free_bytes=min(r['disk_free_bytes'] for r in snapshots)),
        memory_scope='GPU peak includes cached models and allocation already present; RSS is cumulative process peak, not isolated per-arm working set.',
        setup_scope='Shared synchronized setup separately measured; per-arm build times use the original setup adapter. Offline calibration/training provenance must be reported separately, not zero.')


def analyze_matrix(contract, x, helpers):
    """Shared arithmetic path; callers distinguish synthetic tests from measured data."""
    core, statistics, runner = helpers
    settings = contract['statistical_settings']
    mapped = validate_design(contract)
    started = time.time()
    point = core.log_ratios(x.mean(axis=0)[None, :], np.quantile(x, .95, axis=0)[None, :], mapped)[0]
    ensembles = []
    for length in settings['block_lengths']:
        ensembles.append(runner.run_length(x, mapped, point, settings, length, core))
        print(json.dumps(dict(event='cost512_bootstrap_length_complete', block_length=length,
            draws=settings['draws_per_length'], elapsed_seconds=time.time()-started)), flush=True)
    columns = [dict(c, **statistics.column_diagnostic(x[:, c['index']], settings, core)) for c in contract['columns']]
    endpoints = []
    for i, (row, mapping) in enumerate(zip(contract['endpoints'], mapped)):
        endpoint = dict(row, point_ratio=float(np.exp(point[i])))
        diagnostic = statistics.endpoint_diagnostic(x, mapping, endpoint, columns, settings, core)
        evidence = []
        for value in ensembles:
            def select(ensemble):
                return {k: ensemble['statistics'][k][i] for k in statistics.ENSEMBLE_FIELDS}
            evidence.append(dict(block_length=value['block_length'], pooled=select(value['pooled']),
                                 splits=[select(split) for split in value['splits']]))
        endpoints.append(statistics.endpoint_decision(endpoint, diagnostic, evidence, settings))
    return dict(columns=columns, endpoints=endpoints, ensembles=ensembles,
                comparisons=comparison_decisions(endpoints))


def execute(args):
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('cost analysis requires one numerical CPU thread and no visible GPU')
    started = time.time()
    contract = checked_json(args.contract, args.contract_sha256)
    if not started < args.deadline_unix <= contract['deadline']['global_deadline_unix']:
        raise ValueError('invalid cost statistics deadline')
    def stop(_signal, _frame):
        raise TimeoutError('cost statistics deadline reached')
    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, args.deadline_unix-started)
    mapped = validate_design(contract)
    core, statistics, runner = load_helpers(contract)
    settings = contract['statistical_settings']
    rank_evidence = statistics.rank_verification(settings, core)
    audit, warm, x, guards = load_cost_inputs(args, contract)
    metadata = cost_metadata(args.root, audit, warm)
    analyzed = analyze_matrix(contract, x, (core, statistics, runner))
    for path, expected in guards.items():
        if sha(path) != expected:
            raise ValueError('cost analysis input changed during statistics: '+str(path))
    load_helpers(contract)
    result = dict(schema='adjacent-cost512-statistics-result-v1', status='COMPLETE',
        contract_sha256=args.contract_sha256, audit_sha256=args.audit_sha256,
        n_independent_exogenous_blocks=512, endpoint_count=18, bootstrap_resamples=600000,
        settings=settings, rank_probability_verification=rank_evidence,
        **analyzed, metadata=metadata, new_receiver_calls=dict(F=0, E=0, T=0),
        legacy_qualification=contract['legacy_contract'], limitations=contract['limitations'],
        started_at_unix=started, finished_at_unix=time.time(), elapsed_seconds=time.time()-started,
        script_sha256=sha(__file__))
    with args.out.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(status='COMPLETE', path=str(args.out), sha256=sha(args.out),
        comparisons=result['comparisons'], elapsed_seconds=result['elapsed_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'contract', 'audit', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--audit-sha256', required=True)
    parser.add_argument('--deadline-unix', type=float, required=True)
    args = parser.parse_args()
    for path in (args.root, args.contract, args.audit, args.out):
        if not path.resolve().is_relative_to('/data/guoyikun'):
            parser.error('cost analysis files must remain below /data/guoyikun')
    execute(args)
