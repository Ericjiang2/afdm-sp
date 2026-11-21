#!/usr/bin/env python3
"""Independent read-only E1/E2(R,C)/E3/E3b saved-row recount.

Run in the frozen project tree containing the raw rows, never over schema samples:
  python recount.py --project-root /data/guoyikun/00inbox/AFDM-channel-estimation \
      --out experiments/tf_covariance_audit_20261018/out/recount-01

Raw JSONL is streamed into compact scalar records; old receiver/aggregator code
is not imported. SHA256 receipts bind every input before and after analysis.
An existing output directory is refused. No frozen evidence is written.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

from sampling import bootstrap_means, linear_summary, ratio_summary

E1 = 'tf_cstate_e1_20261017'
E2 = 'tf_cstate_e2_20261017'
E3 = 'tf_e3_sbl_20261017'
E3B = 'tf_e3b_offgrid_20261017'
ARMS1 = tuple(f'A{i}' for i in range(1, 8))
ARMS2 = ('A1', 'A2', 'A3', 'A1g', 'A2g', 'A2n', 'A5', 'A7')
ON = ('L-hard', 'L-diag', 'L-cov', 'L-genie')
OFF = ('hard-off', 'diag-off', 'cov-off', 'genie-off')
PAIRS1 = (('A1', 'A2'), ('A2', 'A5'), ('A1', 'A5'), ('A1', 'A3'),
          ('A2', 'A4'), ('A3', 'A6'), ('A6', 'A5'), ('A1', 'A7'))
PAIRS2 = (('A1', 'A2'), ('A2g', 'A2'), ('A1', 'A2g'), ('A1', 'A1g'),
          ('A2n', 'A2'), ('A2n', 'A2g'), ('A1', 'A3'), ('A1', 'A5'),
          ('A1', 'A7'), ('A1g', 'A2g'), ('A2', 'A5'))
SOURCE_ALIASES = {'sp_afdm_native_joint_20260921': 'sp_afdm_native_joint_reviewed_20260921',
                  'sp_afdm_frozen_20260920': 'sp_afdm_frozen_reviewed_20260921'}  # used only if the primary path is absent
HEX32 = re.compile(r'^[0-9a-f]{32}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


class Inputs:
    """Hash inventory and preservation check; only reads registered inputs."""
    def __init__(self):
        self.hashes = {}
        self.aliased = []

    def add(self, path):
        path = Path(path).resolve()
        if str(path) not in self.hashes:
            self.hashes[str(path)] = digest(path)
        return path

    def read_json(self, path):
        return json.loads(self.add(path).read_text())

    def finish(self):
        changed = [p for p, h in self.hashes.items() if digest(p) != h]
        require(not changed, f'input changed during recount: {changed[:3]}')
        return dict(algorithm='sha256', before_equals_after=True, files=dict(sorted(self.hashes.items())),
                    source_alias_resolved=sorted(set(self.aliased)))


def manifest_entries(path):
    entries = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split(maxsplit=1)
        require(len(parts) == 2 and HEX32.fullmatch(parts[0]), f'malformed MD5 manifest: {path}: {line}')
        entries.append((parts[0], parts[1].lstrip('*')))
    require(entries and len({n for _, n in entries}) == len(entries), f'empty/duplicate manifest: {path}')
    return entries


def verify_manifest(path, base, inputs, rows=False):
    inputs.add(path)
    files = []
    for md5, name in manifest_entries(path):
        named = Path(name)
        # Historical local receipts contain absolute deinlab paths. Relocate
        # only row basenames into this campaign's declared raw directory.
        if rows:
            # The run manifests also list each shard's config: verify and bind it, but do not read it as rows.
            is_config = re.fullmatch(r'config_shard\d+\.json', named.name)
            require(is_config or re.fullmatch(r'rows_shard\d+\.jsonl(?:\.gz)?', named.name), f'non-row entry: {name}')
            p = Path(base) / named.name
            if is_config:
                require(p.is_file() and digest(p, 'md5') == md5, f'config MD5 mismatch: {p}')
                inputs.add(p)
                continue
        else:
            require(not named.is_absolute() and '..' not in named.parts, f'non-relative source entry: {name}')
            p = Path(base) / named
            if named.parts[0] in SOURCE_ALIASES and not (p.is_file() and digest(p, 'md5') == md5):
                # Documented in the SOURCE_MD5.txt headers: deinlab runtime loads the same-byte *_reviewed_* copies
                # (the runtime import fingerprint, e.g. receiver 228411ca, equals the manifest); the deinlab copy under
                # the primary name is an older file that was not imported. The aliased copy must still match the MD5.
                p = Path(base) / SOURCE_ALIASES[named.parts[0]] / Path(*named.parts[1:])
                inputs.aliased.append(str(p))
        require(p.is_file(), f'missing manifest input: {p}')
        require(digest(p, 'md5') == md5, f'MD5 mismatch: {p}')
        inputs.add(p)
        files.append(p)
    require(len(set(files)) == len(files), f'duplicate resolved manifest paths: {path}')
    if rows:
        found = set(Path(base).glob('rows_shard*.jsonl*'))
        require(found == set(files), f'manifest/file coverage differs: {base}')
    return files


def source_receipt(project, experiment, config, inputs):
    exp = project / 'experiments' / experiment
    verify_manifest(exp / 'SOURCE_MD5.txt', project / 'experiments', inputs)
    if (exp / 'CODE_MD5.txt').exists():
        verify_manifest(exp / 'CODE_MD5.txt', exp, inputs)
    require(bool(config.get('own_md5')), f'{experiment}: missing own_md5')
    for name, md5 in config['own_md5'].items():
        p = exp / name
        require(digest(p, 'md5') == md5, f'own source MD5 mismatch: {p}')
        inputs.add(p)
    checks = config.get('frozen_md5_check', {})
    require(bool(checks), f'{experiment}: missing frozen source checks')
    for name, check in checks.items():
        require(check['status'] == 'ok' and check['expected'] == check['actual'], f'failed frozen source check: {name}')
    return dict(source_manifest=str(exp / 'SOURCE_MD5.txt'), own_files=len(config['own_md5']),
                frozen_checks=len(checks), runtime_module_fingerprints=config.get('source_md5'),
                runtime_module_note='Recorded import hashes retained; path-resolved frozen/source manifests checked independently.')


def key_of(row):
    key = tuple(row[k] for k in ('scenario', 'rho_permille', 'snr_centi_db', 'frame'))
    require(isinstance(key[0], str) and all(type(v) is int for v in key[1:]), f'invalid key types: {key}')
    return key


def finite_tree(value, path='row'):
    if isinstance(value, float):
        require(math.isfinite(value), f'nonfinite value: {path}')
    elif isinstance(value, dict):
        require('__remaining_length__' not in value, 'schema sample is not a raw observation')
        for k, v in value.items():
            finite_tree(v, f'{path}.{k}')
    elif isinstance(value, list):
        for i, v in enumerate(value):
            finite_tree(v, f'{path}[{i}]')


def decoded_record(record, label, *, has_fer=True, status=False):
    if status:
        require(record.get('status') == 'ok', f'{label}: failed arm')
    e = record['info_errors']
    require(type(e) is int and e >= 0, f'{label}: invalid information-bit errors')
    if has_fer:
        require(type(record['fer']) is int and record['fer'] in (0, 1) and record['fer'] == int(e > 0),
                f'{label}: FER inconsistent with information-bit errors')
    require(type(record['syndrome']) is int and record['syndrome'] >= 0, f'{label}: invalid syndrome')
    require(bool(HEX64.fullmatch(record['decoded_sha256'])), f'{label}: invalid decoded hash')
    return int(e == 0)


def fallback_flag(record, arm, key):
    """A5 (detector/LDPC rerun) and A7 (third F0 round) make no geometry call and record no fallback field."""
    if arm in ('A5', 'A7'):
        require('numerical_fallback' not in record, f'{key}/{arm}: unexpected geometry fallback field')
        return False
    return bool(record['numerical_fallback'])


def project_row(row, campaign):
    """Validate the real frozen schemas and retain scalars needed for inference."""
    finite_tree(row)
    k = key_of(row)
    require(row.get('status') != 'error' and not row.get('smoke', False), f'{k}: error/smoke row')
    require(row['rho'] == k[1]/1000 and row['snr_db'] == k[2]/100, f'{k}: physical label mismatch')
    if campaign.startswith('e2'):
        require(row['family'] == campaign[-1], f'{k}: wrong E2 family')
    elif campaign in ('e3', 'e3b'):
        require(row['family'] == 'P1', f'{k}: wrong RNG family')
    out = dict(key=k)
    if campaign in ('e1', 'e2_R', 'e2_C'):
        f0 = decoded_record(row['f0'], f'{k}/F0', has_fer=False)
        out['f0_success'] = f0
        trigger = row['f0']['syndrome'] != 0
        if campaign == 'e1':
            require(trigger and all(row.get(n) is True for n in ('g4a_ok', 'f0_matches_ledger', 'a1_matches_ledger', 'g5_ok')),
                    f'{k}: E1 ledger/gate mismatch')
            ledger = row['ledger']
            require(ledger['triggered'] and ledger['f0_sha'] == row['f0']['decoded_sha256'] and
                    ledger['f0_info_errors'] == row['f0']['info_errors'] and
                    ledger['f0_fer'] == int(not f0) and ledger['f0_syndrome'] == row['f0']['syndrome'],
                    f'{k}: inconsistent ledger F0')
            require(ledger['b_sha'] == row['arms']['A1']['decoded_sha256'] and
                    ledger['b_info_errors'] == row['arms']['A1']['info_errors'] and
                    ledger['b_fer'] == row['arms']['A1']['fer'], f'{k}: inconsistent ledger A1')
        else:
            require(type(row['triggered']) is bool and row['triggered'] == trigger, f'{k}: trigger/syndrome mismatch')
            if trigger:
                require(row.get('g5_ok') is True and row.get('guard_ok') is True, f'{k}: gate/guard failed')
        out['triggered'] = trigger
        arms = ARMS1 if campaign == 'e1' else ARMS2
        require(set(row['arms']) == (set(arms) if trigger else set()), f'{k}: missing/extra arm')
        out['values'] = {a: decoded_record(row['arms'][a], f'{k}/{a}', status=True) for a in arms} if trigger else None
        out['fallbacks'] = {a: fallback_flag(row['arms'][a], a, k) for a in arms} if trigger else {}
        return out
    arms = ON if campaign == 'e3' else OFF
    require(set(row['variants']) == set(arms), f'{k}: missing/extra variant')
    decoded_record(row['round1'], f'{k}/round1', has_fer=False)
    require(row.get('gamma_diag_rel_err', 0.) < 1e-10, f'{k}: Gamma diagonal invariant')
    out['values'] = {}
    out['nmse'] = {}
    for a in arms:
        x = row['variants'][a]
        decoded_record(x, f'{k}/{a}')
        require(type(x['n_pair']) is int and x['n_pair'] >= 0 and x['n_pair'] == len(x['pairs']), f'{k}/{a}: pair count mismatch')
        require(x['nmse'] > 0, f'{k}/{a}: nonpositive NMSE')
        out['values'][a] = int(x['fer'])
        out['values'][f'n_pair_{a}'] = x['n_pair']
        out['nmse'][a] = x['nmse']
    # These exact fields prove that the E3b row reuses the saved E3 receiver path.
    out['pairing'] = dict(stage1_atoms=row['stage1']['atoms'], round1_sha=row['round1']['decoded_sha256'],
                          n_candidates=row['n_candidates_stage2'],
                          atoms={a: row['variants'][a]['atoms' if campaign == 'e3' else 'atoms_ongrid'] for a in arms})
    if campaign == 'e3b':
        c = row['_config']
        out['config_ref'] = (c['config_file'], c['config_md5'])
    return out


def check_complete(records, expected):
    got = [r['key'] for r in records]
    require(len(set(got)) == len(got), 'duplicate observation key')
    missing, extra = expected-set(got), set(got)-expected
    require(not missing and not extra, f'incomplete key grid: missing={len(missing)} extra={len(extra)}; first={sorted(missing or extra)[:3]}')


def load_campaign(project, campaign, inputs):
    expname, sub = {'e1': (E1, 'main'), 'e2_R': (E2, 'main_R'), 'e2_C': (E2, 'main_C'),
                    'e3': (E3, 'main'), 'e3b': (E3B, 'main')}[campaign]
    exp = project / 'experiments' / expname
    base = exp / 'out' / sub
    files = verify_manifest(base / 'REMOTE_ROWS_MD5.txt', base, inputs, rows=True)
    configs = {}
    for p in sorted(base.glob('config_shard*.json')):
        configs[p.name] = inputs.read_json(p)['_config']
    require(bool(configs), f'{campaign}: missing configs')
    cfg = configs['config_shard000.json']
    source = source_receipt(project, expname, cfg, inputs)
    for name, c in configs.items():
        require(c['own_md5'] == cfg['own_md5'] and c['source_md5'] == cfg['source_md5'] and
                not c.get('smoke_only', False), f'{campaign}: inconsistent source config {name}')
    # E1/E2/E3 record only the config files, E3b also binds each row to one.
    expected = expected_keys(project, campaign, inputs)
    records = []
    for p in sorted(files):
        op = gzip.open if p.suffix == '.gz' else open
        with op(p, 'rt') as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    r = project_row(json.loads(line), campaign)
                    if campaign == 'e3b':
                        name, md5 = r.pop('config_ref')
                        require(name in configs and digest(base / name, 'md5') == md5, f'row/config MD5 mismatch: {name}')
                    records.append(r)
                except (ValueError, KeyError, TypeError) as error:
                    raise ValueError(f'{p}:{line_no}: {error}') from error
    check_complete(records, expected)
    records.sort(key=lambda r: r['key'])
    return records, dict(n_rows=len(records), n_expected=len(expected), n_shards=len(files),
                         raw_manifest=str(base / 'REMOTE_ROWS_MD5.txt'), source=source,
                         raw_before_sha256={str(p.resolve()): inputs.hashes[str(p.resolve())] for p in files})


def expected_keys(project, campaign, inputs):
    if campaign == 'e1':
        base = project / 'experiments' / E1 / 'out' / 'select'
        verify_manifest(base / 'REMOTE_KEYS_MD5.txt', base, inputs)
        keys = inputs.read_json(base / 'triggered_keys.json')['units']
        result = [key_of(k) for k in keys]
        require(len(set(result)) == len(result), 'duplicate selection keys')
        return set(result)
    if campaign == 'e2_R':
        return set(itertools.product(('U', 'G'), (300, 500), range(450, 801, 50), range(3000, 4000)))
    if campaign == 'e2_C':
        p = project / 'experiments' / E2 / 'out' / 'calibrate' / 'GRID.json'
        grid = inputs.read_json(p)
        return {('J4', round(float(rho)*1000), round(snr*100), f)
                for rho, cell in grid['rho'].items() if cell['status'] == 'OK'
                for snr in cell['grid_db'] for f in range(1000)}
    if campaign == 'e3':
        p = project / 'experiments' / E3 / 'out' / 'calibrate' / 'GRID.json'
        grid = inputs.read_json(p)
        return {(sc, int(rho), int(snr*100), f) for cell, v in grid['cells'].items() if v['status'] == 'OK'
                for sc, rho in [cell.split('_')] for snr in v['grid_db'] for f in range(4000, 4400)}
    if campaign == 'e3b':
        return set(itertools.product(('U', 'G'), (300,), range(600, 1101, 100), range(4000, 4200)))
    raise ValueError(f'unknown campaign: {campaign}')


def cluster_ids(records, campaign, corrected):
    if corrected:
        domain = 'E2CJ:1160921930' if campaign == 'e2_C' else 'P1:1413698118'
        return [f'{domain}|{r["key"][3]}' for r in records]
    # Frozen E3b used (scenario,frame); the others used (scenario,rho,frame).
    return [('|'.join(map(str, (r['key'][0], r['key'][3]))) if campaign == 'e3b' else
             '|'.join(map(str, (r['key'][0], r['key'][1], r['key'][3])))) for r in records]


def ratio_contract(campaign):
    if campaign in ('e1', 'e2_R', 'e2_C'):
        den = {'A1': 1, 'A5': -1}
        ratios = dict(F5=({'A1': 1, 'A5': -1}, {'A1': 1}),
                      F7=({'A1': 1, 'A7': -1}, {'A1': 1}),
                      S_Gamma=({'A1': 1, 'A2': -1}, den),
                      S_swap=({'A1': 1, 'A3': -1}, den))
        if campaign == 'e1':
            ratios.update(S_local=({'A3': 1, 'A6': -1}, den), S_refit=({'A6': 1, 'A5': -1}, den),
                          S_Gamma_noswap=({'A3': 1, 'A4': -1}, den))
        else:
            ratios.update(G=({'A2g': 1, 'A2': -1}, {'A1': 1, 'A2': -1}),
                          G_n=({'A2n': 1, 'A2': -1}, {'A1': 1, 'A2': -1}))
        return ratios
    if campaign == 'e3':
        return dict(R_ph=({'E_L-cov': 1}, {'E_L-diag': 1}))
    return {}


def inference(values, records, campaign, corrected, n_boot, seed):
    draws, m = bootstrap_means(values, cluster_ids(records, campaign, corrected), n_boot, seed)
    point = {k: float(np.mean(v)) for k, v in values.items()}
    if campaign == 'e1':
        contrasts = {f'{a}-{b}': {a: 1, b: -1} for a, b in PAIRS1}
    elif campaign.startswith('e2'):
        contrasts = {f'{a}-{b}': {a: 1, b: -1} for a, b in PAIRS2}
    elif campaign == 'e3':
        contrasts = {f'E_{a}': {f'E_{a}': 1} for a in ON[:-1]}
        contrasts.update(fer_diff_diag_minus_cov={'L-diag': 1, 'L-cov': -1},
                         fer_diff_hard_minus_cov={'L-hard': 1, 'L-cov': -1})
    else:
        contrasts = dict(A_on={'on_L-cov': 1, 'on_L-diag': -1},
                         A_off={'off_cov-off': 1, 'off_diag-off': -1},
                         Delta={'on_L-cov': 1, 'on_L-diag': -1, 'off_cov-off': -1, 'off_diag-off': 1})
        contrasts.update({f'{off}_minus_on': {f'off_{off}': 1, f'on_{on}': -1} for off, on in zip(OFF, ON)})
    if campaign == 'e1':
        contrasts['Delta_geo'] = {'A1': 1, 'A5': -1}
    # Means for each arm/metric use the very same paired bootstrap draws.
    means = {k: linear_summary(point, draws, {k: 1}) for k in values}
    diffs = {name: linear_summary(point, draws, weights) for name, weights in contrasts.items()}
    ratios = {name: ratio_summary(point, draws, num, den) for name, (num, den) in ratio_contract(campaign).items()}
    return dict(cluster_definition='RNG domain/frame' if corrected else 'frozen finer clusters',
                n_clusters=m, n_boot=n_boot, seed=seed, means=means, contrasts=diffs, ratios=ratios)


def mcnemar_descriptive(values, arms, success_metric):
    out = {}
    for a, b in itertools.combinations(arms, 2):
        x, y = np.asarray(values[a]), np.asarray(values[b])
        if not success_metric:
            x, y = 1-x, 1-y
        n10, n01 = int(np.sum((x == 1) & (y == 0))), int(np.sum((x == 0) & (y == 1)))
        n = n10+n01
        # lgamma is unnecessary here: Python big integers retain the exact tail
        # before conversion to a log probability (including huge discordance).
        lp = 0. if n == 0 else math.log10(sum(math.comb(n, i) for i in range(n10, n+1))) - n*math.log10(2)
        out[f'{a}>{b}'] = dict(b=n10, c=n01, discordant=n, log10_p_one_sided=lp)
    return dict(assumption='iid rows; violated by shared frames; descriptive historical statistic only', tests=out)


def close(actual, expected, label):
    if expected is None:
        require(actual is None, f'{label}: expected undefined')
    else:
        require(actual is not None and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12),
                f'{label}: recount {actual} != frozen {expected}')


def compare_frozen(result, old, campaign):
    """Compare independent means, contrasts, ratios AND legacy-bootstrap CIs."""
    q = result['legacy_bootstrap']
    checked = 0
    if campaign == 'e1':
        means = old['bootstrap']['rates_point']
        differences = old['bootstrap']['differences']
        ratios = old['bootstrap']['ratios']
    elif campaign.startswith('e2'):
        means = old['quantities']['rates_point']
        differences = old['quantities']['diff']
        ratios = old['quantities']['ratio']
    else:
        means = old['quantities']['point']
        if campaign == 'e3':
            means = {k.removeprefix('fer_'): v for k, v in means.items()}
            differences = {k: old['quantities'][k] for k in ('fer_diff_diag_minus_cov', 'fer_diff_hard_minus_cov')}
            differences.update({f'E_{a}': v for a, v in old['quantities']['E'].items()})
            ratios = {'R_ph': old['quantities']['R_ph']}
        else:
            differences = {k: old['quantities'][k] for k in ('A_on', 'A_off', 'Delta')}
            ratios = {}
    for k, v in means.items():
        close(q['means'][k]['point'], v, f'{campaign}/mean/{k}')
        checked += 1
    for family, items in [('contrasts', differences), ('ratios', ratios)]:
        for k, v in items.items():
            r = q[family][k]
            close(r['point'], v.get('point', v.get('diff')), f'{campaign}/{k}/point')
            checked += 1
            for bound in ('ci_lo', 'ci_hi'):
                close(r[bound], v[bound], f'{campaign}/{k}/{bound}')
                checked += 1
    return dict(all_match=True, scalar_comparisons=checked, tolerance='rel 1e-10 / abs 1e-12')


def campaign_analysis(records, campaign, old, n_boot, seed, on=None):
    units = [r for r in records if r.get('triggered', True)]
    require(bool(units), f'{campaign}: no estimable observations')
    if campaign == 'e3b':
        require(on is not None, 'E3b requires complete E3 pairing')
        for r in units:
            require(r['key'] in on, f'{r["key"]}: missing E3 partner')
            p, g = r['pairing'], on[r['key']]['pairing']
            require(all(p[k] == g[k] for k in ('stage1_atoms', 'round1_sha', 'n_candidates')) and
                    all(p['atoms'][off] == g['atoms'][arm] for off, arm in zip(OFF, ON)),
                    f'{r["key"]}: E3/E3b first stage or selected geometry differs')
        values = {f'off_{a}': np.array([r['values'][a] for r in units]) for a in OFF}
        values.update({f'on_{a}': np.array([on[r['key']]['values'][a] for r in units]) for a in ON})
        arms = list(values)
    else:
        arms = ARMS1 if campaign == 'e1' else ARMS2 if campaign.startswith('e2') else ON
        values = {a: np.array([r['values'][a] for r in units]) for a in arms}
        if campaign == 'e3':
            values.update({f'E_{a}': np.array([r['values'][f'n_pair_{a}']-r['values']['n_pair_L-genie'] for r in units]) for a in ON[:-1]})
    result = dict(n_rows=len(records), n_units=len(units),
                  estimand='conditional triggered-key success rate' if campaign in ('e1', 'e2_R', 'e2_C') else 'unconditional key FER and saved geometry metrics',
                  legacy_bootstrap=inference(values, units, campaign, False, n_boot, seed),
                  frame_bootstrap=inference(values, units, campaign, True, n_boot, seed),
                  frozen_verdict=old.get('final_verdict'),
                  iid_row_mcnemar_descriptive=mcnemar_descriptive(values, arms, campaign in ('e1', 'e2_R', 'e2_C')))
    if campaign in ('e1', 'e2_R', 'e2_C'):
        result['success_counts'] = {a: int(values[a].sum()) for a in arms}
        result['fallback_counts'] = {a: sum(r['fallbacks'][a] for r in units) for a in arms}
        expected = {a: old['per_arm'][a]['success'] for a in arms} if campaign == 'e1' else old['success']
        require(result['success_counts'] == expected, f'{campaign}: frozen success counts mismatch')
    else:
        nmse = {a: float(10*np.log10(np.median([r['nmse'][a] for r in units]))) for a in (OFF if campaign == 'e3b' else ON)}
        expected = old['nmse_db_median']['off'] if campaign == 'e3b' else old['nmse_db_median']
        for a, v in nmse.items():
            close(v, expected[a], f'{campaign}/median NMSE/{a}')
        result['nmse_db_median'] = nmse
    result['frozen_reproduction'] = compare_frozen(result, old, campaign)
    # CIs use the corrected clusters; no iid-row significance gate is reapplied.
    result['corrected_reading'] = dict(
        contrast_ci_excludes_zero={k: not v['contains_0'] for k, v in result['frame_bootstrap']['contrasts'].items()},
        ratio_evaluable={k: v['evaluable'] for k, v in result['frame_bootstrap']['ratios'].items()},
        note='Frozen verdict preserved; exact row McNemar is not a valid cluster significance gate. CI exclusion is descriptive, without multiplicity adjustment or causal certification.')
    return result


def render_md(report):
    lines = ['# Saved-row covariance audit (draft)', '',
             'Independent scalar recount; raw/source MD5 verified and SHA256 unchanged before/after. '
             'Primary inference resamples RNG-domain/frame jointly across scenario/rho/SNR. '
             'All arms share draws; row-weighted estimands retained. Exact row McNemar is descriptive under an iid-row assumption.', '',
             f"Bootstrap: {report['n_boot']} draws, seed {report['seed']}, percentile 95% CI. Frozen verdicts remain unchanged.", '']
    for name, r in report['campaigns'].items():
        old, new = r['legacy_bootstrap'], r['frame_bootstrap']
        lines += [f'## {name}', '', f"{r['n_rows']} complete rows; {r['n_units']} analysis units; clusters {old['n_clusters']} → {new['n_clusters']}; frozen reproduction: {r['frozen_reproduction']['all_match']}.", '',
                  '| contrast | point | old 95% CI | frame 95% CI |', '|---|---:|---|---|']
        for k, x in new['contrasts'].items():
            o = old['contrasts'][k]
            lines.append(f"| {k} | {x['point']:.6f} | [{o['ci_lo']:.6f}, {o['ci_hi']:.6f}] | [{x['ci_lo']:.6f}, {x['ci_hi']:.6f}] |")
        if new['ratios']:
            lines += ['', '| ratio | point | old CI | frame CI | bad denom fraction | evaluable |', '|---|---:|---|---|---:|---|']
            for k, x in new['ratios'].items():
                o = old['ratios'][k]
                fmt = lambda v: 'undefined' if v is None else f'{v:.6f}'
                lines.append(f"| {k} | {fmt(x['point'])} | [{fmt(o['ci_lo'])}, {fmt(o['ci_hi'])}] | [{fmt(x['ci_lo'])}, {fmt(x['ci_hi'])}] | {x['denominator_nonpositive_fraction']:.4f} | {x['evaluable']} |")
        lines += ['', f"Frozen verdict: {r['frozen_verdict']}. Corrected CIs do not certify a causal mechanism.", '']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    project = args.project_root.resolve()
    out = args.out.resolve()
    # Output is confined to the new audit tree. Existing output is never replaced.
    audit = project / 'experiments' / 'tf_covariance_audit_20261018'
    require(out.is_relative_to(audit) and out != audit and not out.exists(), 'output must be a NEW directory under experiments/tf_covariance_audit_20261018')
    report = dict(n_boot=20000, seed=20261017, campaigns={})
    e3_records = None
    for campaign, exp, summary in [('e1', E1, 'main/analysis/e1_summary.json'),
                                    ('e2_R', E2, 'analysis/e2_summary.json'),
                                    ('e2_C', E2, 'analysis/e2_summary.json'),
                                    ('e3', E3, 'analysis/e3_summary.json'),
                                    ('e3b', E3B, 'analysis/e3b_summary.json')]:
        inputs = Inputs()
        for code in ('recount.py', 'sampling.py'):
            inputs.add(Path(__file__).parent / code)
        old = inputs.read_json(project / 'experiments' / exp / 'out' / summary)
        if campaign.startswith('e2'):
            old = old[campaign[-1]]
        records, integrity = load_campaign(project, campaign, inputs)
        gates = inputs.read_json(project / 'experiments' / exp / 'out' / 'gate' / 'gates.json')
        require(gates['all_pass'] is True, f'{campaign}: frozen engineering gates failed')
        if campaign == 'e2_C':
            require(inputs.read_json(project / 'experiments' / exp / 'out' / 'gate' / 'cgates.json')['all_pass'] is True, 'E2 C engineering gates failed')
        if campaign == 'e3b':
            # Bind the already-validated E3 evidence used as on-grid partners.
            for path in report['campaigns']['e3']['input_receipt']['files']:
                inputs.add(path)
        result = campaign_analysis(records, campaign, old, report['n_boot'], report['seed'], on=e3_records)
        result['integrity'] = integrity
        result['input_receipt'] = inputs.finish()
        report['campaigns'][campaign] = result
        if campaign == 'e3':
            e3_records = {r['key']: r for r in records}
        print(f'{campaign}: complete {len(records)} rows; old reproduction passed; frame clusters={result["frame_bootstrap"]["n_clusters"]}', flush=True)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'recount.json').write_text(json.dumps(report, indent=1, allow_nan=False)+'\n')
    (out / 'recount.md').write_text(render_md(report))
    for campaign, result in report['campaigns'].items():
        (out / f'{campaign}_inputs_sha256.json').write_text(json.dumps(result['input_receipt'], indent=1, allow_nan=False)+'\n')
    print(f'written {out}/recount.json and recount.md', flush=True)


if __name__ == '__main__':
    main()
