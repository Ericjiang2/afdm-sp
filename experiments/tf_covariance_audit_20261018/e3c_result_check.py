#!/usr/bin/env python3
"""Read-only verification of a COMPLETE frozen E3c run, independent of e3c_agg.

python e3c_result_check.py --self-test
python e3c_result_check.py --project-root /data/guoyikun/00inbox/AFDM-channel-estimation \
    --run-root experiments/tf_e3c_shrink_20261018/out/qualified_v3 \
    --out experiments/tf_covariance_audit_20261018/out/e3c-final-check

Only STATUS=complete campaigns are read. Point estimates/counts/calibration are
independently reduced from saved rows. CI verification deliberately reuses the
already reviewed sampling.py: this is numerical reproduction, not an independent
bootstrap algorithm. No receiver is imported or run. Per-key baseline_check
flags are checked recursively, not asserted as a new replay against E3b files.
Synthetic --self-test fixtures never represent receiver/scientific evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import unittest

import numpy as np

from sampling import bootstrap_means, interval

ARMS = ('diag-off', 'cov-off', 'cov+ridge', 'diag2', 'cov-oracle', 'diag-oracle')
BASELINES = ('diag-off', 'cov-off')
STAGES = ('sbl', 'fixed_refit')
SEED, N_BOOT = 20261018, 20000
ENTROPY = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
DOMAIN = '1413698118'
SHA = re.compile(r'^[0-9a-f]{64}$')


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path, decompressed=False):
    hasher = hashlib.sha256()
    opener = gzip.open if decompressed else open
    with opener(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


class Inventory:
    def __init__(self):
        self.before = {}

    def bind(self, path):
        path = Path(path).resolve()
        if str(path) not in self.before:
            self.before[str(path)] = file_hash(path)
        return path

    def json(self, path):
        return json.loads(self.bind(path).read_text())

    def preserve(self):
        changed = [p for p, sha in self.before.items() if file_hash(p) != sha]
        ensure(not changed, f'input/source changed during check: {changed[:3]}')
        return dict(before_equals_after=True, sha256=dict(sorted(self.before.items())))


def read_sha_manifest(path, inventory):
    inventory.bind(path)
    result = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        ensure(len(parts) == 2 and SHA.fullmatch(parts[0]), f'malformed SHA manifest: {path}')
        sha, name = parts[0], parts[1].lstrip('*')
        ensure(Path(name).name == name and name not in result, f'unsafe/duplicate manifest name: {name}')
        result[name] = sha
    ensure(bool(result), f'empty manifest: {path}')
    return result


def verify_raw_manifests(main, inventory):
    """Bind gzip bytes and their original decompressed SHA without materializing."""
    compressed = read_sha_manifest(main/'COMPRESSED_SHA256.txt', inventory)
    raw = read_sha_manifest(main/'RAW_SHA256.txt', inventory)
    gz_files = {p.name for p in main.glob('rows_shard*.jsonl.gz')}
    ensure(gz_files == set(compressed), 'compressed manifest does not cover exactly all gzip shards')
    config_names = {p.name for p in main.glob('config_shard*.json')}
    logical_rows = {name.removesuffix('.gz') for name in gz_files}
    ensure(set(raw) == logical_rows | config_names | {'summary.json'}, 'raw manifest coverage mismatch')
    ensure({p.name for p in main.glob('rows_shard*.jsonl')} <= logical_rows, 'unmanifested raw shard')
    for name in sorted(gz_files):
        path = inventory.bind(main/name)
        ensure(inventory.before[str(path)] == compressed[name], f'compressed SHA mismatch: {name}')
        raw_name = name.removesuffix('.gz')
        ensure(file_hash(path, decompressed=True) == raw[raw_name], f'decompressed/raw SHA mismatch: {name}')
        if (main/raw_name).exists():
            p = inventory.bind(main/raw_name)
            ensure(inventory.before[str(p)] == raw[raw_name], f'raw SHA mismatch: {raw_name}')
    for name in config_names | {'summary.json'}:
        p = inventory.bind(main/name)
        ensure(inventory.before[str(p)] == raw[name], f'raw manifest SHA mismatch: {name}')
    return sorted(main/name for name in gz_files)


def expected_keys():
    return set(itertools.product(('U', 'G'), (300,), range(600, 1101, 100), range(4000, 4100)))


def key(row):
    result = tuple(row[k] for k in ('scenario', 'rho_permille', 'snr_centi_db', 'frame'))
    ensure(isinstance(result[0], str) and all(type(x) is int for x in result[1:]), 'invalid key types')
    return result


def scalar_close(a, b, label):
    ensure(type(a) in (int, float) and type(b) in (int, float) and math.isfinite(a) and math.isfinite(b),
           f'{label}: expected finite numeric scalars')
    if type(a) is int and type(b) is int:
        ensure(a == b, f'{label}: {a} != {b}')
    else:
        ensure(math.isclose(a, b, rel_tol=2e-10, abs_tol=2e-12), f'{label}: {a} != {b}')


def finite_tree(value, path='row'):
    if isinstance(value, float):
        ensure(math.isfinite(value), f'{path}: nonfinite value')
    elif isinstance(value, dict):
        ensure('__remaining_length__' not in value, 'truncated schema fixture is not raw evidence')
        for name, child in value.items():
            finite_tree(child, f'{path}/{name}')
    elif isinstance(value, list):
        for i, child in enumerate(value):
            finite_tree(child, f'{path}/{i}')


def nonnegative_int(value, label):
    ensure(type(value) is int and value >= 0, f'{label}: expected nonnegative integer')


def decode_fields(value, label):
    errors, fer = value['info_errors'], value['fer']
    nonnegative_int(errors, label+'/info_errors')
    ensure(type(fer) is int and fer in (0, 1) and fer == (errors > 0), f'{label}: FER/info_errors mismatch')
    ensure(isinstance(value['decoded_sha256'], str) and SHA.fullmatch(value['decoded_sha256']), f'{label}: decoded hash')
    ensure(type(value['nmse']) in (int, float) and value['nmse'] >= 0, f'{label}: NMSE')


def check_calibration(cal, label):
    for name in ('n', 'n_sym_err', 'n_conf_sym_err', 'n_comp_err', 'n_conf_comp_err', 'n_conf'):
        nonnegative_int(cal[name], label+'/'+name)
    ensure(cal['n_conf_sym_err'] <= cal['n_sym_err'] <= cal['n'], label+': symbol-error count bounds')
    ensure(cal['n_conf_comp_err'] <= cal['n_comp_err'] <= 2*cal['n'], label+': component-error count bounds')
    ensure(cal['n_conf'] <= cal['n'] and cal['n_conf_sym_err'] <= cal['n_conf'], label+': confidence count bounds')
    ensure(len(cal['bins']) == 5, label+': need all five reliability bins')
    for b in cal['bins']:
        nonnegative_int(b['n'], label+'/bin/n')
        ensure(b['sum_v'] >= 0 and b['sum_err'] >= 0, label+': negative bin energy')
    ensure(sum(b['n'] for b in cal['bins']) == cal['n'], label+': reliability counts do not partition frame')
    for field in ('sum_v', 'sum_err'):
        ensure(cal[field] >= 0, label+': negative energy')
        scalar_close(math.fsum(b[field] for b in cal['bins']), cal[field], label+'/'+field+' bin closure')
    if cal['sum_v'] > 0:
        scalar_close(cal['kappa'], cal['sum_err']/cal['sum_v'], label+'/kappa')
    else:
        ensure(cal['kappa'] is None, label+': undefined kappa')


def check_row(row):
    finite_tree(row)
    label = str(key(row))
    ensure(row.get('status') == 'ok' and not row.get('smoke', False), label+': error or smoke row')
    ensure(row['rho'] == .3 and row['snr_db'] == row['snr_centi_db']/100, label+': labels')
    ensure(row['rng_entropy'] == ENTROPY and str(row['rng_domain']) == DOMAIN, label+': unexpected RNG domain')
    ensure(set(row['variants']) == set(ARMS), label+': incomplete six-arm matrix')
    checks = row['baseline_check']
    ensure(set(checks) == {'stage1', 'round1', 'candidates', 'variants', 'all'}, label+': baseline check schema')
    ensure(set(checks['variants']) == set(BASELINES), label+': baseline arm checks absent')
    leaves = [checks[k] for k in ('stage1', 'round1', 'candidates')]
    for arm in BASELINES:
        ensure(set(checks['variants'][arm]) == {'sha', 'atoms', 'atoms_ongrid', 'errors', 'nmse'}, label+': baseline check fields')
        leaves.extend(checks['variants'][arm].values())
    ensure(all(type(v) is bool for v in leaves) and all(leaves) and checks['all'] is True,
           label+': failed or inconsistent saved baseline check')
    for arm in ARMS:
        v = row['variants'][arm]
        decode_fields(v, label+'/'+arm)
        for field in ('n_atoms', 'n_pair'):
            nonnegative_int(v[field], label+'/'+arm+'/'+field)
        ensure(len(v['pairs']) == v['n_pair'] and len(v['atoms']) == v['n_atoms'] and len(v['atoms_ongrid']) == v['n_atoms'],
               label+': atom/pair counts inconsistent')
        ensure(type(v['sbl']['converged']) is bool, label+': convergence flag')
        f = v['refine']
        ensure(all(f.get(k) is True for k in ('monotone', 'value_recheck_equal', 'in_bounds', 'in_window')) and
               0 <= f['max_evals_coord'] <= 16, label+': refinement gate failed')
        ensure(0 <= v['gamma_check']['relative_error'] <= 1e-12, label+': Gamma closure failed')
        de = v['gamma_check']['diagonal_error']
        ensure(de is None or 0 <= de <= 1e-12, label+': Gamma diagonal failed')
        if arm in BASELINES:
            ensure(set(v['stages']) == set(STAGES), label+': missing/extra baseline stages')
            for stage in STAGES:
                s = v['stages'][stage]
                decode_fields(s, label+'/'+arm+'/'+stage)
                ensure(type(s['recomputed']) is bool, label+': stage origin missing')
                if stage == 'sbl':
                    ensure(s['recomputed'] is False and s['provenance'] == 'frozen E3 saved row', label+': main SBL origin differs')
                else:
                    ensure(s['recomputed'] is True and s['provenance'] == 'recomputed same key', label+': fixed refit origin differs')
                ensure(s['n_atoms'] == v['n_atoms'], label+': fixed geometry atom count differs')
    for name in ('noise_sha256', 'physical_gains_sha256', 'coded_sha256', 'info_sha256'):
        ensure(SHA.fullmatch(row['pairing'][name]), label+': invalid exogenous hash')
    check_calibration(row['calibration'], label+'/calibration')


def check_sources(project, identity, config, inventory):
    resolutions = config['frozen_source_resolution']
    ensure(identity and all(SHA.fullmatch(h) for h in identity.values()), 'invalid source identity')
    for relative, sha in identity.items():
        declared = Path(relative)
        ensure(not declared.is_absolute() and '..' not in declared.parts, 'unsafe source path')
        path = (Path(resolutions[relative]['actual_path']) if relative in resolutions else
                project/'experiments'/relative)
        p = inventory.bind(path)
        ensure(inventory.before[str(p)] == sha, f'frozen source SHA mismatch: {relative} via {p}')
        if relative in resolutions:
            r = resolutions[relative]
            ensure(r['sha256'] == sha and r['actual_md5'] == r['expected_md5'], f'bad frozen resolution: {relative}')


def read_complete_run(project, run_root, inventory, expected_commit):
    status = inventory.bind(run_root/'STATUS')
    ensure(status.read_text().strip() == 'complete', 'refusing incomplete/partial campaign')
    freeze = inventory.json(run_root/'FREEZE.json')
    gates = inventory.json(run_root/'gates.json')
    ensure(isinstance(freeze.get('git_commit'), str) and freeze['git_commit'].startswith(expected_commit), 'wrong freeze commit')
    identity = freeze['sources_sha256']
    ensure(gates['all_pass'] is True and gates['sources_sha256'] == identity, 'frozen gates/source identity failed')
    main = run_root/'main'
    files = verify_raw_manifests(main, inventory)
    ensure(files, 'no final raw shards')
    wanted = expected_keys()
    rows, declared_all, shared = {}, set(), {}
    for path in files:
        cfg_name = path.name.replace('rows_', 'config_').replace('.jsonl.gz', '.json')
        config_path = inventory.bind(main/cfg_name)
        envelope = inventory.json(config_path)
        c = envelope['_config']
        ensure(isinstance(envelope['_argv'], list) and bool(envelope['_argv']), 'missing invocation provenance')
        ensure(c['sources_sha256'] == identity and c['smoke'] is False and set(c['arms']) == set(ARMS), 'mixed config/source identity')
        ensure(c['rng'] == dict(domain=int(DOMAIN), entropy=ENTROPY), 'config RNG differs')
        declared_list = [tuple(k) for k in c['keys']]
        declared = set(declared_list)
        ensure(len(declared) == len(declared_list) and declared <= wanted and not declared & declared_all, 'duplicate/unexpected config keys')
        declared_all.update(declared)
        if not rows:
            check_sources(project, identity, c, inventory)
        observed = set()
        with gzip.open(path, 'rt') as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    k = key(row)
                    ensure(k in declared and k not in rows, f'duplicate/unexpected key {k}')
                    check_row(row)
                    ensure(row['config_sha256'] == inventory.before[str(config_path)] and
                           row['_config'] == dict(config_file=cfg_name, config_sha256=inventory.before[str(config_path)]),
                           'row/config hash mismatch')
                    ensure(row['power']['system_rho'] == c['system']['rho'] and row['power']['p_d'] == c['system']['p_d'], 'power coordinates/config differ')
                    cluster = (row['rng_entropy'], str(row['rng_domain']), row['frame'])
                    fingerprint = tuple(row['pairing'][name] for name in ('noise_sha256', 'physical_gains_sha256', 'coded_sha256', 'info_sha256'))
                    ensure(cluster not in shared or shared[cluster] == fingerprint, f'shared-frame exogenous hashes differ: {cluster}')
                    shared[cluster] = fingerprint
                    observed.add(k)
                    rows[k] = row
                except (ValueError, KeyError, TypeError) as error:
                    raise ValueError(f'{path}:{line_number}: {error}') from error
        ensure(observed == declared, f'incomplete shard: {path}')
    ensure(set(rows) == wanted and declared_all == wanted, f'incomplete final grid: {len(rows)}/1200')
    ensure(len(shared) == 100, f'expected 100 RNG-domain/frame clusters, got {len(shared)}')
    summary = inventory.json(main/'summary.json')
    ensure(summary['source_sha256'] == identity, 'summary source identity differs')
    return [rows[k] for k in sorted(rows)], summary, identity, freeze['git_commit']


def reduce_points(rows):
    """Independent count/sum reduction. No original aggregator is imported."""
    columns = {}
    counts = {}
    for arm in ARMS:
        variants = [r['variants'][arm] for r in rows]
        # FER is reconstructed from bit errors, independently of stored FER.
        columns[arm] = np.array([int(v['info_errors'] != 0) for v in variants], float)
        columns[arm+'/nmse'] = np.array([v['nmse'] for v in variants], float)
        counts[arm] = dict(continuous_failures=sum(v['info_errors'] > 0 for v in variants), n=len(rows))
        if arm in BASELINES:
            for stage in STAGES:
                stage_values = [v['stages'][stage] for v in variants]
                prefix = arm+'/'+stage+'/'
                columns[prefix+'fer'] = np.array([int(v['info_errors'] != 0) for v in stage_values], float)
                columns[prefix+'nmse'] = np.array([v['nmse'] for v in stage_values], float)
                counts[arm][stage+'_failures'] = sum(v['info_errors'] > 0 for v in stage_values)
    point = {name: math.fsum(values)/len(rows) for name, values in columns.items()}
    calibration = [r['calibration'] for r in rows]
    vtotal = math.fsum(c['sum_v'] for c in calibration)
    etotal = math.fsum(c['sum_err'] for c in calibration)
    nerr = sum(c['n_sym_err'] for c in calibration)
    reliability = []
    for index in range(5):
        bucket = [c['bins'][index] for c in calibration]
        n = sum(b['n'] for b in bucket)
        sv = math.fsum(b['sum_v'] for b in bucket)
        se = math.fsum(b['sum_err'] for b in bucket)
        reliability.append(dict(n=n, sum_v=sv, sum_err=se, mean_v=sv/n if n else None,
                                mean_error_energy=se/n if n else None))
    cal = dict(sum_v=vtotal, sum_err=etotal, kappa=etotal/vtotal if vtotal else None,
               confident_error_fraction=sum(c['n_conf_sym_err'] for c in calibration)/nerr if nerr else None,
               bins=reliability)
    census = {}
    for arm in ARMS:
        variants = [r['variants'][arm] for r in rows]
        census[arm] = dict(n_atoms=sum(v['n_atoms'] for v in variants), n_pair=sum(len(v['pairs']) for v in variants),
                           nonconverged_sbl=sum(v['sbl']['converged'] is False for v in variants),
                           same_delay_dn=[p['dnu'] for v in variants for p in v['pairs']])
    return columns, point, counts, cal, census


def classify(evaluable, lo, hi):
    if not evaluable:
        return 'not-evaluable'
    return 'recovered' if lo >= .8 else 'small' if hi <= .2 else 'unresolved'


def expected_summary(rows, n_boot=N_BOOT):
    columns, point, counts, calibration, census = reduce_points(rows)
    ids = [f"{r['rng_entropy']}:{r['rng_domain']}:{r['frame']}" for r in rows]
    # Shared numerical sampler is declared in the receipt. Contrast/ratio
    # assembly, raw validation and all point reductions here are independent.
    draws, n_clusters = bootstrap_means(columns, ids, n_boot=n_boot, seed=SEED)

    def difference(left, right):
        return dict(point=point[left]-point[right], **interval(draws[left]-draws[right]))

    metrics = {name: dict(point=point[name], **interval(draws[name])) for name in columns}
    gap_point = point['cov-off']-point['diag-off']
    gap_draws = draws['cov-off']-draws['diag-off']
    positive = gap_draws > 0
    failure_fraction = float(np.count_nonzero(~positive)/len(gap_draws))
    fractions = {}
    for name, target in [('Sh', 'cov+ridge'), ('Or', 'cov-oracle')]:
        ratio_draws = (draws['cov-off'][positive]-draws[target][positive])/gap_draws[positive]
        ci = interval(ratio_draws) if len(ratio_draws) else dict(ci_lo=None, ci_hi=None, ci_width=None, contains_0=None)
        evaluable = bool(gap_point > 0 and failure_fraction <= .01 and len(ratio_draws))
        fractions[name] = dict(point=(point['cov-off']-point[target])/gap_point if gap_point > 0 else None,
                               denominator_point=gap_point, denominator_nonpositive_fraction=failure_fraction,
                               evaluable=evaluable, failure_limit=.01, **ci,
                               classification=classify(evaluable, ci['ci_lo'], ci['ci_hi']))
    comparisons = {left+' - '+right: difference(left, right) for left, right in
                   [('cov+ridge', 'diag-off'), ('cov-oracle', 'diag-oracle'), ('cov+ridge', 'diag2'), ('cov-off', 'diag-off')]}
    fixed = {}
    for arm in BASELINES:
        fixed[arm] = {}
        for metric in ('fer', 'nmse'):
            sbl, refit = arm+'/sbl/'+metric, arm+'/fixed_refit/'+metric
            continuous = arm if metric == 'fer' else arm+'/nmse'
            fixed[arm][metric] = dict(refit_minus_sbl=difference(refit, sbl), continuous_minus_refit=difference(continuous, refit))
    return dict(n_keys=len(rows), n_clusters=n_clusters, n_boot=n_boot, seed=SEED, metrics=metrics,
                fractions=fractions, comparisons=comparisons, fixed_geometry=fixed, calibration=calibration,
                census=census, oracle_noninferior_1pp=bool(comparisons['cov-oracle - diag-oracle']['ci_hi'] <= .01)), counts


def check_numeric_tree(actual, expected, path='summary', coverage=None):
    """Every numeric/bool/null leaf of actual must have a reconstructed value.

    Explanatory strings/source hashes are separately checked at their boundaries;
    ratio classification strings are checked explicitly as scientific labels.
    """
    coverage = Counter() if coverage is None else coverage
    if isinstance(actual, dict):
        ensure(isinstance(expected, dict), path+': missing reconstructed object')
        ensure(set(expected) <= set(actual), path+': missing reconstructed summary fields '+str(sorted(set(expected)-set(actual))))
        for name, value in actual.items():
            if isinstance(value, str):
                if name == 'classification':
                    ensure(value == expected.get(name), path+': wrong fraction classification')
                continue
            ensure(name in expected, path+'/'+name+': unaccounted summary field')
            check_numeric_tree(value, expected[name], path+'/'+name, coverage)
    elif isinstance(actual, list):
        ensure(isinstance(expected, list) and len(actual) == len(expected), path+': list length differs')
        for i, (a, b) in enumerate(zip(actual, expected)):
            check_numeric_tree(a, b, path+f'/{i}', coverage)
    elif actual is None or type(actual) is bool:
        ensure(actual is expected, path+': bool/null mismatch')
        coverage['bool_or_null'] += 1
    elif type(actual) in (int, float):
        scalar_close(actual, expected, path)
        coverage['numeric'] += 1
    elif isinstance(actual, str):
        pass
    else:
        raise ValueError(path+': unsupported summary type')
    return coverage


def check_summary(rows, summary, identity, n_boot=N_BOOT):
    ensure(summary['status'] == 'draft' and summary['source_sha256'] == identity, 'summary status/source mismatch')
    expected, counts = expected_summary(rows, n_boot=n_boot)
    expected['source_sha256'] = identity
    expected['cells'] = {}
    cell_counts = {}
    for scenario in ('U', 'G'):
        for snr in range(600, 1101, 100):
            label = f'{scenario}/{snr}'
            subset = [r for r in rows if r['scenario'] == scenario and r['snr_centi_db'] == snr]
            ensure(bool(subset), f'empty cell {label}')
            expected['cells'][label], cell_counts[label] = expected_summary(subset, n_boot=n_boot)
    ensure(set(summary['cells']) == set(expected['cells']), 'missing/extra scenario/SNR summary cells')
    coverage = check_numeric_tree(summary, expected)
    # Missing summary output must fail too, not merely unknown numeric values.
    for actual, wanted in [(summary, expected)] + [(summary['cells'][k], v) for k, v in expected['cells'].items()]:
        for name in ('metrics', 'fractions', 'comparisons', 'fixed_geometry', 'calibration', 'census'):
            ensure(set(actual[name]) == set(wanted[name]), f'missing/extra {name} outputs')
    return dict(verified_leaf_counts=dict(coverage), failure_counts=counts, cell_failure_counts=cell_counts,
                n_clusters=expected['n_clusters'], fractions=expected['fractions'], calibration=expected['calibration'],
                stage_differences=expected['fixed_geometry'], mean_metrics={k: v['point'] for k, v in expected['metrics'].items()})


def check(project, run_root, expected_commit):
    inventory = Inventory()
    for name in ('e3c_result_check.py', 'sampling.py'):
        inventory.bind(Path(__file__).parent/name)
    rows, summary, identity, commit = read_complete_run(project, run_root, inventory, expected_commit)
    result = check_summary(rows, summary, identity)
    result.update(status='passed', evidence='saved-output recomputation; no receiver rerun',
                  n_rows=len(rows), error_rows=0, duplicate_rows=0, n_baseline_keys_checked=len(rows),
                  freeze_commit=commit, source_files=len(identity),
                  baseline_scope='Every saved per-key stage1/round1/candidate/variant check is true with all-field closure; not an independent E3b replay.',
                  ci_scope='Reuses reviewed sampling.py bootstrap (20000, seed 20261018); numerical reproduction, not an independent sampling algorithm.',
                  calibration_scope='Pools saved energy/count bins; does not reconstruct unavailable symbol arrays.',
                  source_and_input_preservation=inventory.preserve())
    return result


def markdown(receipt):
    lines = ['# E3c final saved-output check', '',
             f"Status: **{receipt['status']}**; {receipt['n_rows']} complete keys, {receipt['n_clusters']} frame clusters, zero error/duplicate rows.",
             f"Freeze: `{receipt['freeze_commit']}`. All input/source SHA256 hashes unchanged before/after.", '',
             '| arm | continuous failures | FER | SBL failures | fixed-refit failures |', '|---|---:|---:|---:|---:|']
    for arm, c in receipt['failure_counts'].items():
        lines.append(f"| {arm} | {c['continuous_failures']}/{c['n']} | {c['continuous_failures']/c['n']:.6f} | {c.get('sbl_failures', '—')} | {c.get('fixed_refit_failures', '—')} |")
    lines += ['', 'Every numeric/bool/null summary leaf, including all 12 scenario/SNR cells, was checked against reconstructed saved-row values.', '',
              receipt['ci_scope'], '', receipt['baseline_scope'], '', receipt['calibration_scope'],
              '', 'This receipt verifies saved evidence and does not certify a causal mechanism.']
    return '\n'.join(lines)+'\n'


def fixture(frame=4000, scenario='U', snr=600, fail=0):
    """Small synthetic row for contract tests only; never read as campaign input."""
    h = 'a'*64
    variants = {}
    for arm in ARMS:
        v = dict(info_errors=fail, fer=fail, decoded_sha256=h, nmse=.5 if fail else .25,
                 n_atoms=1, atoms=[{'delay': 0}], atoms_ongrid=[{'delay': 0}], n_pair=0, pairs=[],
                 sbl=dict(converged=True), gamma_check=dict(relative_error=0., diagonal_error=0.),
                 refine=dict(monotone=True, value_recheck_equal=True, in_bounds=True, in_window=True, max_evals_coord=16))
        if arm in BASELINES:
            v['stages'] = {stage: dict(info_errors=1-fail, fer=1-fail, decoded_sha256=h, nmse=.75,
                                      n_atoms=1, recomputed=(stage == 'fixed_refit'),
                                      provenance='recomputed same key' if stage == 'fixed_refit' else 'frozen E3 saved row') for stage in STAGES}
        variants[arm] = v
    return dict(scenario=scenario, rho_permille=300, snr_centi_db=snr, frame=frame, rho=.3, snr_db=snr/100,
                status='ok', rng_entropy=ENTROPY, rng_domain=DOMAIN, variants=variants,
                pairing={k: h for k in ('noise_sha256', 'physical_gains_sha256', 'coded_sha256', 'info_sha256')},
                baseline_check=dict(stage1=True, round1=True, candidates=True, all=True,
                                    variants={a: {k: True for k in ('sha', 'atoms', 'atoms_ongrid', 'errors', 'nmse')} for a in BASELINES}),
                calibration=dict(n=5, sum_v=5., sum_err=10., kappa=2., n_sym_err=2, n_conf_sym_err=1,
                                 n_comp_err=3, n_conf_comp_err=1, n_conf=1,
                                 bins=[dict(n=1, sum_v=1., sum_err=2.) for _ in range(5)]))


def write_fixture_campaign(project, transform=None):
    """Synthetic complete-grid reader fixture, NOT completed receiver evidence."""
    run = project/'campaign'
    main = run/'main'
    main.mkdir(parents=True)
    experiments = project/'experiments'
    experiments.mkdir()
    source = experiments/'fixture_source.py'
    source.write_text('# Synthetic provenance fixture only\n')
    identity = {'fixture_source.py': file_hash(source)}
    (run/'STATUS').write_text('complete\n')
    (run/'FREEZE.json').write_text(json.dumps(dict(git_commit='e1bfd013-synthetic', sources_sha256=identity)))
    (run/'gates.json').write_text(json.dumps(dict(all_pass=True, sources_sha256=identity)))
    keys = sorted(expected_keys())
    config = dict(sources_sha256=identity, smoke=False, arms=list(ARMS), rng=dict(domain=int(DOMAIN), entropy=ENTROPY),
                  keys=keys, frozen_source_resolution={}, system=dict(rho=.5, p_d=.5))
    config_path = main/'config_shard000.json'
    config_path.write_text(json.dumps(dict(_argv=['synthetic'], _config=config)))
    config_sha = file_hash(config_path)
    rows = []
    for sc, _, snr, frame in keys:
        row = fixture(frame, sc, snr, frame % 2)
        row.update(config_sha256=config_sha, _config=dict(config_file=config_path.name, config_sha256=config_sha),
                   power=dict(system_rho=.5, p_d=.5))
        rows.append(row)
    if transform is not None:
        rows = transform(rows)
    raw = b''.join((json.dumps(row)+'\n').encode() for row in rows)
    path = main/'rows_shard000.jsonl.gz'
    with gzip.open(path, 'wb') as handle:
        handle.write(raw)
    summary = main/'summary.json'
    summary.write_text(json.dumps(dict(source_sha256=identity)))
    raw_entries = [(hashlib.sha256(raw).hexdigest(), 'rows_shard000.jsonl'),
                   (config_sha, config_path.name), (file_hash(summary), summary.name)]
    (main/'RAW_SHA256.txt').write_text(''.join(f'{h}  {n}\n' for h, n in raw_entries))
    (main/'COMPRESSED_SHA256.txt').write_text(f'{file_hash(path)}  {path.name}\n')
    return run


class CheckerTests(unittest.TestCase):
    def test_independent_counts_stage_fer_and_pooled_calibration(self):
        rows = [fixture(fail=0), fixture(frame=4001, fail=1), fixture(frame=4002, fail=1)]
        rows[1]['calibration'].update(sum_v=10., sum_err=30., kappa=3., bins=[dict(n=1, sum_v=2., sum_err=6.) for _ in range(5)])
        _, points, counts, cal, census = reduce_points(rows)
        self.assertEqual(counts['diag-off']['continuous_failures'], 2)
        self.assertEqual(counts['diag-off']['sbl_failures'], 1)
        self.assertEqual(counts['diag-off']['fixed_refit_failures'], 1)
        self.assertEqual(points['diag-off'], 2/3)
        self.assertEqual(points['diag-off/sbl/fer'], 1/3)
        self.assertEqual(cal['kappa'], 50/20)
        self.assertEqual(cal['bins'][0]['sum_err'], 10.)
        self.assertEqual(cal['bins'][0]['n'], 3)
        self.assertEqual(census['diag-off']['n_atoms'], 3)

    def test_error_false_baseline_incomplete_stage_and_bit_fer_are_rejected(self):
        cases = []
        r = fixture(); r['status'] = 'error'; cases.append(r)
        r = fixture(); r['baseline_check']['variants']['diag-off']['sha'] = False; cases.append(r)
        r = fixture(); del r['variants']['diag-off']['stages']['sbl']; cases.append(r)
        r = fixture(); r['variants']['diag-off']['stages']['sbl']['fer'] = 0; cases.append(r)
        r = fixture(); r['variants']['cov+ridge']['fer'] = 1; cases.append(r)
        r = fixture(); r['variants']['cov-off']['nmse'] = float('nan'); cases.append(r)
        r = fixture(); r['calibration']['bins'][0]['sum_v'] = 2.; cases.append(r)
        for row in cases:
            with self.subTest(row=row), self.assertRaises(ValueError):
                check_row(row)
        check_row(fixture())

    def test_zero_and_positive_gap_ratios_and_shared_frame(self):
        rows = [fixture(frame=f, scenario=sc) for f in (4000, 4001) for sc in ('U', 'G')]
        zero, _ = expected_summary(rows, n_boot=100)
        self.assertEqual(zero['n_clusters'], 2)
        self.assertIsNone(zero['fractions']['Sh']['point'])
        self.assertFalse(zero['fractions']['Sh']['evaluable'])
        self.assertEqual(zero['fractions']['Sh']['denominator_nonpositive_fraction'], 1.)
        for r in rows:
            r['variants']['cov-off'].update(info_errors=1, fer=1)
        positive, _ = expected_summary(rows, n_boot=100)
        self.assertEqual(positive['fractions']['Sh']['point'], 1.)
        self.assertEqual(positive['fractions']['Or']['point'], 1.)
        self.assertTrue(positive['fractions']['Sh']['evaluable'])
        self.assertEqual(positive['fractions']['Sh']['classification'], 'recovered')

    def test_every_summary_number_must_be_reconstructed(self):
        wanted = dict(metric=dict(point=.5), count=2, flag=True, bins=[dict(n=1, value=None)])
        self.assertEqual(check_numeric_tree(wanted, wanted)['numeric'], 3)
        changed = copy.deepcopy(wanted); changed['metric']['point'] = .6
        with self.assertRaisesRegex(ValueError, 'summary/metric/point'):
            check_numeric_tree(changed, wanted)
        changed = copy.deepcopy(wanted); changed['invented'] = 1
        with self.assertRaisesRegex(ValueError, 'unaccounted'):
            check_numeric_tree(changed, wanted)
        changed = copy.deepcopy(wanted); del changed['metric']['point']
        with self.assertRaisesRegex(ValueError, 'missing reconstructed summary fields'):
            check_numeric_tree(changed, wanted)

    def test_gzip_only_validates_raw_and_compressed_bytes_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp)
            raw = b'{"one":1}\n'
            with gzip.open(main/'rows_shard000.jsonl.gz', 'wb') as handle:
                handle.write(raw)
            (main/'config_shard000.json').write_text('{}')
            (main/'summary.json').write_text('{}')
            raw_sha = hashlib.sha256(raw).hexdigest()
            entries = [(raw_sha, 'rows_shard000.jsonl')] + [(file_hash(main/name), name) for name in ('config_shard000.json', 'summary.json')]
            (main/'RAW_SHA256.txt').write_text(''.join(f'{h}  {n}\n' for h, n in entries))
            (main/'COMPRESSED_SHA256.txt').write_text(f"{file_hash(main/'rows_shard000.jsonl.gz')}  rows_shard000.jsonl.gz\n")
            self.assertEqual(len(verify_raw_manifests(main, Inventory())), 1)
            (main/'RAW_SHA256.txt').write_text((main/'RAW_SHA256.txt').read_text().replace(raw_sha, '0'*64))
            with self.assertRaisesRegex(ValueError, 'decompressed/raw SHA'):
                verify_raw_manifests(main, Inventory())
            (main/'RAW_SHA256.txt').write_text(''.join(f'{h}  {n}\n' for h, n in entries[:-1]))
            with self.assertRaisesRegex(ValueError, 'coverage'):
                verify_raw_manifests(main, Inventory())

    def test_changed_input_is_detected_and_partial_refused_before_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root/'source.py'; p.write_text('before')
            inventory = Inventory(); inventory.bind(p); p.write_text('after')
            with self.assertRaisesRegex(ValueError, 'changed during check'):
                inventory.preserve()
            (root/'STATUS').write_text('running\n')
            with self.assertRaisesRegex(ValueError, 'incomplete/partial'):
                read_complete_run(root, root, Inventory(), 'e1bfd013')

    def test_reader_rejects_duplicate_and_missing_keys_on_full_frozen_grid(self):
        for transform, message in [(lambda rows: rows+[rows[0]], 'duplicate/unexpected'),
                                   (lambda rows: rows[:-1], 'incomplete shard')]:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp)
                run = write_fixture_campaign(project, transform)
                with self.assertRaisesRegex(ValueError, message):
                    read_complete_run(project, run, Inventory(), 'e1bfd013')
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run = write_fixture_campaign(project)
            inventory = Inventory()
            rows, _, _, _ = read_complete_run(project, run, inventory, 'e1bfd013')
            self.assertEqual(len(rows), 1200)
            self.assertTrue(inventory.preserve()['before_equals_after'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--project-root', type=Path)
    parser.add_argument('--run-root', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--expected-commit', default='e1bfd013')
    args = parser.parse_args(argv)
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(CheckerTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    ensure(args.project_root and args.run_root and args.out, '--project-root/--run-root/--out required')
    project = args.project_root.resolve()
    run = (project/args.run_root).resolve() if not args.run_root.is_absolute() else args.run_root.resolve()
    out = (project/args.out).resolve() if not args.out.is_absolute() else args.out.resolve()
    audit = project/'experiments'/'tf_covariance_audit_20261018'
    ensure(out.is_relative_to(audit) and out != audit and not out.exists(), 'output must be a NEW directory under the audit tree')
    result = check(project, run, args.expected_commit)
    out.mkdir(parents=True, exist_ok=False)
    (out/'e3c_result_check.json').write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    (out/'e3c_result_check.md').write_text(markdown(result))
    print(json.dumps(dict(status=result['status'], rows=result['n_rows'], clusters=result['n_clusters'],
                          numeric_leaves=result['verified_leaf_counts'], receipt=str(out))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
