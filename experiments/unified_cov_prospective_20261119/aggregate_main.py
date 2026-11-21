"""Validate complete frozen main rows and write paired physical-frame readouts."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

import verdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcom_reference_frame_20261015'))
import p1_agg
from p1_agg import HIGH, LOW, crossing

FRAMES = range(4400, 4600)
S_GRID = {300: tuple(range(600, 1101, 100))}
C_GRID = {300: (500, 550, *S_GRID[300]), 500: (500, 550, 600, 650, *S_GRID[300][1:])}
S_ARMS = ('R0', 'R1', 'S-lo', 'S-hi', 'S-isolo', 'U2')
C_ARMS = ('F0', *verdict.ADMISSION_ARMS)
SPECTRAL = ('U', 'C-hi', 'C-lo')
MARGIN, V5_PRIMARY = .005, 'fer'
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
FINGERPRINTS = ('scored_trials', 'nonempty_scored_trials', 'valid_trials', 'nonempty_trials')
FROZEN_CROSSING_SHA = 'd28d8b2ff29dcc66982d583636d66dba55609da42319550f24b883d2aa6477a1'


def expected_keys(grid):
    return {(s, rho, snr, frame) for s in ('U', 'G') for rho, snrs in grid.items()
            for snr in snrs for frame in FRAMES}


def check(condition, detail):
    if not condition:
        raise ValueError(detail)


def digest(value, length=64):
    return isinstance(value, str) and re.fullmatch(rf'[0-9a-f]{{{length}}}', value) is not None


def whole(value, lower=0):
    return type(value) is int and value >= lower


def finite(value, lower=None):
    return type(value) in (float, int) and math.isfinite(value) and (lower is None or value >= lower)


def verify_hash_group(row, fields, key):
    hashes = tuple(row[name] for name in fields)
    check(all(map(digest, hashes)), f'Invalid exogenous hashes at {key}: {fields}')
    return hashes


def match_once(inventory, group, fingerprint):
    check(inventory.setdefault(group, fingerprint) == fingerprint, f'Exogenous draw differs for {group}')


def errors(record, field, hash_field, key):
    n = record[field]
    check(whole(n) and digest(record[hash_field]), f'Invalid errors or decoded SHA for {key}')
    return n


def validate_sbl(row, key, fingerprints):
    s, rho, _, frame = key
    check(row['family'] == 'P1' and tuple(row['key']) == key and set(row['variants']) == set(S_ARMS),
          f'Unexpected SBL row schema at {key}')
    check(row['rng_entropy'] == '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
          and row['rng_domain'] == str(0x54435246) and finite(row['sigma2'], 0) and row['sigma2'] > 0,
          f'SBL P1 stream or noise variance differs at {key}')
    common = verify_hash_group(row['pairing'], ('info_sha256', 'coded_sha256', 'noise_sha256'), key)
    match_once(fingerprints, ('sbl', frame), common)
    signal = verify_hash_group(row['input_sha256'], ('pilot', 'data_true'), key)
    physical = verify_hash_group(row['pairing'], ('physical_gains_sha256',), key)
    match_once(fingerprints, ('sbl', s, rho, frame), (*signal, *physical))
    for name, arm in row['variants'].items():
        label = key, name
        n = errors(arm, 'info_errors', 'decoded_sha256', label)
        fit = arm['sbl']
        check(arm['fer'] == int(n > 0) and finite(arm['nmse'], 0)
              and whole(arm['n_atoms'], 1) and len(arm['atoms']) == arm['n_atoms']
              and whole(arm['n_pair']) and len(arm['pairs']) == arm['n_pair']
              and fit['max_iter'] == 100 and whole(fit['iterations'], 1) and fit['iterations'] <= 100
              and type(fit['converged']) is bool and finite(fit['beta'], 0) and fit['beta'] > 0,
              f'Invalid SBL FER, NMSE, support or EM metrics at {label}')


def validate_cstate(row, key, fingerprints):
    s, rho, _, frame = key
    check(set(row['arms']) == set(C_ARMS) and whole(row['syndrome']), f'Unexpected CSTATE schema at {key}')
    common = verify_hash_group(row['inputs'], ('info', 'coded', 'noise'), key)
    match_once(fingerprints, ('cstate', frame), common)
    signal = verify_hash_group(row['inputs'], ('pilot', 'data'), key)
    check(finite(row['truth']['sigma2'], 0) and row['truth']['sigma2'] > 0, f'Invalid CSTATE noise at {key}')
    match_once(fingerprints, ('cstate', s, rho, frame), (*signal, row['truth']['delays'],
                                                       row['truth']['dopplers'], row['truth']['gains']))
    f0 = row['arms']['F0']
    for name, arm in row['arms'].items():
        errors(arm, 'errors', 'decoded_sha', (key, name))
        check(whole(arm['atom_count'], 1) and whole(arm['co_delay_pairs'])
              and arm['first_edit_type'] in (None, 'existing_delay', 'new_delay'),
              f'Invalid CSTATE support or edit type at {key} {name}')
        if not row['syndrome'] and name != 'F0':
            check(arm['seconds'] == 0 and all(arm[k] == f0[k] for k in f0 if k != 'seconds'),
                  f'Untriggered CSTATE arm differs from F0 at {key} {name}')
        if row['syndrome'] and name != 'F0':
            check(bool(arm['decision']) and (arm['first_edit_type'] is not None) == (arm['decision'][0][1] is not None),
                  f'Inconsistent triggered CSTATE edit at {key} {name}')
    census = row['census']
    differing = row['arms']['U']['decision'] != row['arms']['CD']['decision']
    truth_paths = list(zip(row['truth']['delays'], row['truth']['dopplers'], strict=True))
    is_close = any(l1 == l2 and abs(d1 - d2) < .5 for i, (l1, d1) in enumerate(truth_paths)
                   for l2, d2 in truth_paths[:i])
    check(census['decisions_differ'] is differing and census['true_close_codelay'] is (is_close if differing else None),
          f'CSTATE census disagrees with decoded decisions or truth at {key}')
    by_arm = census['by_arm']
    check(set(by_arm) == (set(SPECTRAL) if row['syndrome'] else set()), f'CSTATE census coverage at {key}')
    for name, item in by_arm.items():
        check(all(whole(item[field]) for field in FINGERPRINTS)
              and item['nonempty_trials'] <= min(item['valid_trials'], item['nonempty_scored_trials'])
              and max(item['nonempty_scored_trials'], item['valid_trials']) <= item['scored_trials']
              and item['checked_trials'] == 0,
              f'CSTATE exact-trial census differs at {key} {name}')
    unit = row['admission']
    check(finite(row['admission_seconds'], 0), f'Invalid V5-adm timing at {key}')
    if unit is not None:
        check(row['syndrome'] > 0 and f0['errors'] > 0 and set(unit['by_arm']) == set(verdict.ADMISSION_ARMS)
              and [unit['slot'], unit['phantom']] == row['arms']['A2']['decision'][0][0],
              f'Invalid V5-adm selected proposal at {key}')
        entering = {p['delay'] for p in unit['entering_paths']}
        for a, item in unit['by_arm'].items():
            check(finite(item['phantom_gain']) and finite(item['new_delay_gain'])
                  and item['new_delay']['delay'] not in entering
                  and item['preference'] is (item['phantom_gain'] > item['new_delay_gain']),
                  f'Invalid V5-adm preference at {key} {a}')


def read_inputs(out, commit):
    config = json.loads((out / 'config.json').read_text())
    cfg = config['_config']
    snapshot = cfg['snapshot_sha256']
    check(digest(commit, 40) and cfg['producing_commit'] == commit
          and (out / 'PRODUCING_COMMIT.txt').read_text().strip() == commit
          and cfg['mode'] == 'main' and digest(snapshot), 'Main producing commit, mode or source snapshot mismatch')
    for module, expected, source in (
        (verdict, cfg['frozen_sources_sha256']['verdict.py'], Path(__file__).with_name('verdict.py')),
        (p1_agg, FROZEN_CROSSING_SHA, Path(__file__).resolve().parents[1]/'tcom_reference_frame_20261015/p1_agg.py'),
    ):
        actual = Path(module.__file__).resolve()
        check(actual == source.resolve() and hashlib.sha256(actual.read_bytes()).hexdigest() == expected,
              f'Actual frozen analysis source differs: {actual}')
    attempts = {}
    allowed_shards = {f'rows_shard{i:03d}.jsonl' for i in range(cfg['workers'])}
    for path in sorted(out.glob('attempt_*.json')):
        attempt = json.loads(path.read_text())['_config']
        check(attempt['snapshot_sha256'] == snapshot and digest(attempt['producing_commit'], 40),
              f'Unexpected attempt snapshot or commit: {path.name}')
        for index in attempt['launched_shards']:
            filename = f'rows_shard{index:03d}.jsonl'
            check(filename in allowed_shards, f'Unexpected shard in {path.name}: {filename}')
            attempts.setdefault(filename, set()).add(attempt['producing_commit'])
    manifest = (out / 'REMOTE_ROWS_MD5.txt').read_bytes()
    entries = [line.split() for line in manifest.decode('ascii').splitlines()]
    wanted_names = {p.name for p in out.glob('rows_shard*.jsonl')}
    names = {name for _, name in entries}
    check(bool(entries) and all(re.fullmatch(r'rows_shard\d{3}\.jsonl', name) for name in names)
          and len(entries) == len(names) and names == wanted_names == allowed_shards, 'Main row manifest and shard inventory differ')
    rows = {'sbl': {}, 'cstate': {}}
    expected = dict(sbl=expected_keys(S_GRID), cstate=expected_keys(C_GRID))
    fingerprints = {}
    for checksum, filename in entries:
        blob = (out / filename).read_bytes()
        check(hashlib.md5(blob).hexdigest() == checksum, f'Row shard MD5 mismatch: {filename}')
        for line in blob.splitlines():
            record = json.loads(line)
            leg, key, row = record['leg'], tuple(record['key']), record['row']
            check(leg in expected and key in expected[leg] and key not in rows[leg]
                  and record['snapshot_sha256'] == snapshot and tuple(row[name] for name in KEY_FIELDS) == key
                  and record.get('launch_commit') in attempts.get(filename, ())
                  and (key[3] - FRAMES.start) % cfg['workers'] == int(filename[10:13])
                  and row.get('status') not in ('error', 'failed') and 'error' not in row,
                  f'Unexpected, duplicate, failed, or mixed-source row {leg} {key}: {filename}')
            validate = validate_sbl if leg == 'sbl' else validate_cstate
            validate(row, key, fingerprints)
            rows[leg][key] = row
    for leg, keys in expected.items():
        check(rows[leg].keys() == keys, f'Incomplete {leg} grid: {len(rows[leg])}/{len(keys)} keys')
    for key, sbl in rows['sbl'].items():
        c = rows['cstate'][key]
        check(sbl['sigma2'] == c['truth']['sigma2']
              and sbl['pairing']['info_sha256'] == c['inputs']['info']
              and sbl['pairing']['coded_sha256'] == c['inputs']['coded']
              and sbl['input_sha256']['pilot'] == c['inputs']['pilot']
              and sbl['input_sha256']['y'] == c['inputs']['y'], f'Paired receiver input mismatch at {key}')
    return rows, config, hashlib.md5(manifest).hexdigest()


def frame_means(columns, frames):
    boot, _ = verdict.bootstrap_means(columns, frames, n_boot=verdict.N_BOOT, seed=verdict.SEED)
    point = {name: np.mean(values) for name, values in columns.items()}
    return {name: verdict.linear_summary(point, boot, {name: 1}) for name in columns}


def proportions(numerators, denominators, frames):
    columns = {**{f'n:{name}': value for name, value in numerators.items()},
               **{f'd:{name}': value for name, value in denominators.items()}}
    boot, _ = verdict.bootstrap_means(columns, frames, n_boot=verdict.N_BOOT, seed=verdict.SEED)
    point = {name: np.mean(values) for name, values in columns.items()}
    return {name: dict(verdict.ratio_summary(point, boot, {f'n:{name}': 1}, {f'd:{name}': 1}),
                      numerator=int(sum(values)), denominator=int(sum(denominators[name])))
            for name, values in numerators.items()}


def diagnostics(srows, crows, sframes, cframes):
    s_cols = {}
    for arm in S_ARMS:
        results = [row['variants'][arm] for row in srows]
        for metric in ('n_atoms', 'n_pair', 'nmse'):
            s_cols[f'{arm}/{metric}'] = [r[metric] for r in results]
        for metric in ('beta', 'iterations', 'converged'):
            s_cols[f'{arm}/{metric}'] = [r['sbl'][metric] for r in results]
    s_means = frame_means(s_cols, sframes)
    s_summary = {arm: {k.split('/')[1]: v for k, v in s_means.items() if k.startswith(f'{arm}/')} for arm in S_ARMS}

    trigger = [row['syndrome'] > 0 for row in crows]
    c_cols = {f'{arm}/{field}': [r['arms'][arm][field] for r in crows]
              for arm in C_ARMS for field in ('atom_count', 'co_delay_pairs')}
    c_means = frame_means(c_cols, cframes)
    c_summary = {arm: {k.split('/')[1]: v for k, v in c_means.items() if k.startswith(f'{arm}/')} for arm in C_ARMS}
    edit_n, edit_d = {}, {}
    for arm in C_ARMS[1:]:
        edit = [r['arms'][arm]['first_edit_type'] for r in crows]
        accepted = [value is not None for value in edit]
        existing = [value == 'existing_delay' for value in edit]
        edit_n[f'{arm}/existing'] = edit_n[f'{arm}/P_among_triggers'] = existing
        edit_n[f'{arm}/new'] = [value == 'new_delay' for value in edit]
        edit_d[f'{arm}/existing'] = edit_d[f'{arm}/new'] = accepted
        edit_d[f'{arm}/P_among_triggers'] = trigger
    edit_props = proportions(edit_n, edit_d, cframes)
    edit_summary = {arm: {k.split('/')[1]: v for k, v in edit_props.items() if k.startswith(f'{arm}/')}
                    for arm in C_ARMS[1:]}
    for arm, share in edit_summary.items():
        share['triggered_without_accepted_edit'] = sum(trigger) - share['existing']['denominator']

    census_n, census_d = {}, {}
    for arm in SPECTRAL:
        col = [row['census']['by_arm'].get(arm, {}) for row in crows]
        for support_type, prefix in (('scored', 'scored_'), ('valid', '')):
            key = f'{arm}/{support_type}'
            census_n[key] = [r.get(f'nonempty_{prefix}trials', 0) for r in col]
            census_d[key] = [r.get(f'{support_type}_trials', 0) for r in col]
    different = [r['census']['decisions_differ'] for r in crows]
    close = [r['census']['true_close_codelay'] is True for r in crows]
    census_n['U_CD_different'] = different
    census_d['U_CD_different'] = [True] * len(crows)
    census_n['true_close_among_U_CD_different'] = close
    census_d['true_close_among_U_CD_different'] = different
    census = proportions(census_n, census_d, cframes)
    return dict(sbl=s_summary, cstate_support=c_summary, first_edit=edit_summary, projector_census=census,
                triggered_keys=sum(trigger))


def crossing_interval(low, high):
    bounds = []
    for values, q in ((low, .025), (high, .975)):
        rank = math.ceil(len(values) * q) - 1
        value = float(np.partition(values, rank)[rank])
        bounds.append(('+inf' if value > 0 else '-inf') if math.isinf(value) else value)
    return bounds


def cell_fer_and_crossings(rows):
    n = len(FRAMES)
    # Each draw uses the same frame weights for every arm, SNR and cell.
    weights = np.random.default_rng(verdict.SEED).multinomial(n, np.full(n, 1/n), size=verdict.N_BOOT).astype(float)
    cells = {}
    for s in ('U', 'G'):
        for rho, snrs in C_GRID.items():
            cell = dict(pooled={}, by_snr={str(snr): {} for snr in snrs}, crossings={})
            for arm in C_ARMS:
                matrix = np.array([[rows[s, rho, snr, frame]['arms'][arm]['errors'] > 0 for snr in snrs]
                                   for frame in FRAMES], dtype=float)
                point = matrix.mean(axis=0)
                boot = (weights @ matrix) / n
                cell['pooled'][arm] = dict(point=float(point.mean()), interval95=np.percentile(boot.mean(axis=1), [2.5, 97.5]).tolist(),
                                           failures=int(matrix.sum()), keys=matrix.size)
                intervals = np.percentile(boot, [2.5, 97.5], axis=0).T
                for j, snr in enumerate(snrs):
                    cell['by_snr'][str(snr)][arm] = dict(point=float(point[j]), interval95=intervals[j].tolist(),
                                                         failures=int(matrix[:, j].sum()), keys=n)
                roots, status = crossing(np.vstack((point, boot)), n, np.asarray(snrs) / 100)
                lower = np.where(status == LOW, -np.inf, roots)
                upper = np.where(status == HIGH, np.inf, roots)
                cell['crossings'][arm] = dict(point=crossing_interval(lower[:1], upper[:1]),
                    interval95=crossing_interval(lower[1:], upper[1:]),
                    left_censored_draws=int(np.count_nonzero(status[1:] == LOW)),
                    right_censored_draws=int(np.count_nonzero(status[1:] == HIGH)))
            cells[f'{s}_{rho}'] = cell
    return cells


def summarize(rows):
    srows = [rows['sbl'][key] for key in sorted(rows['sbl'])]
    crows = [rows['cstate'][key] for key in sorted(rows['cstate'])]
    sf, cf = ([r['frame'] for r in leg] for leg in (srows, crows))
    sfer = {arm: [r['variants'][arm]['info_errors'] > 0 for r in srows] for arm in S_ARMS}
    cfer = {arm: [r['arms'][arm]['errors'] > 0 for r in crows] for arm in C_ARMS}
    units = [(r['frame'], r['admission']['by_arm']) for r in crows if r['admission'] is not None]
    adm_frames = [f for f, _ in units]
    preferences = {arm: [data[arm]['preference'] for _, data in units] for arm in C_ARMS[1:]}
    mask = np.array([r['rho_permille'] == 300 and r['snr_centi_db'] in S_GRID[300] for r in crows])
    result = verdict.readout(sfer, sf, cfer, cf, margin=MARGIN, v5_primary=V5_PRIMARY,
                             cstate_common_mask=mask, adm_preferences=preferences, adm_frames=adm_frames)
    result.update(keys=dict(sbl=len(srows), cstate=len(crows)),
                  bootstrap=dict(draws=verdict.N_BOOT, seed=verdict.SEED),
                  whole_grid_fer_ci=dict(sbl=frame_means(sfer, sf), cstate=frame_means(cfer, cf)),
                  cstate_cells=cell_fer_and_crossings(rows['cstate']),
                  diagnostics=diagnostics(srows, crows, sf, cf))
    result['admission_preferences'] = frame_means(preferences, adm_frames) if units else {}
    result['common_grid']['G_B']['interval95'] = [result['metrics']['G_B'][k] for k in ('ci_lo', 'ci_hi')]
    common = [int(a) - int(b) for a, b, keep in zip(cfer['A2'], cfer['CD'], mask, strict=True) if keep]
    common_ci = frame_means({'A2_minus_CD': common}, np.asarray(cf)[mask])['A2_minus_CD']
    result['common_grid']['A2_minus_CD']['interval95'] = [common_ci[k] for k in ('ci_lo', 'ci_hi')]
    return result


def interval_text(bounds, scale=1., precision=3):
    def endpoint(x):
        return str(x) if isinstance(x, str) else f'{x * scale:.{precision}f}'
    return '[' + ', '.join(endpoint(x) for x in bounds) + ']'


def metric_text(entry, scale=1., precision=3):
    point = entry['point']
    if point is None:
        return 'NA'
    label = f'{point * scale:.{precision}f}'
    lo, hi = entry['ci_lo'], entry['ci_hi']
    if lo is not None and hi is not None:
        return f'{label} {interval_text((lo, hi), scale, precision)}'
    if hi is not None:
        return f'{label} [upper ≤ {hi * scale:.{precision}f}]'
    return f'{label} [CI unavailable]'


def markdown(result):
    m, v = result['metrics'], result['verdicts']
    lines = ['# Unified covariance prospective test', '',
             f"Frozen cohort, frames {FRAMES.start}–{FRAMES.stop - 1}. "
             f"SBL {result['keys']['sbl']:,} keys, CSTATE {result['keys']['cstate']:,} keys, "
             f"{result['diagnostics']['triggered_keys']:,} CSTATE triggers. "
             f"Paired physical-frame bootstrap, {verdict.N_BOOT:,} draws, seed {verdict.SEED}.", '',
             '## Frozen verdicts', '',
             '| Component | Estimate [95% CI] | Verdict |', '|---|---:|---|']
    for name, label in (('G_B', 'Premise 1, R1 − R0 (pp)'), ('A2_minus_CD', 'Premise 2, A2 − CD (pp)')):
        lines.append(f"| {label} | {metric_text(m[name], 100)} | {v['prerequisites'][name]} |")
    for name, label, decision, scale in (
        ('phi_lo', 'V1 φ_lo', 'lo', 1), ('phi_hi', 'V1 φ_hi', 'hi', 1),
        ('delta_lo', 'V1 S-isolo − S-lo (pp)', 'shape', 100), ('phi_U2', 'V2 φ_U2', 'V2', 1),
        ('delta_UC', 'V3 U − CD (pp)', 'V3', 100), ('delta_UA', 'V4 U − A2 (pp)', 'V4', 100),
        ('H', 'H, U2 − S-lo (pp), secondary', 'H', 100),
        ('delta_C_hi_CD', 'C-hi − CD companion (pp)', 'C_hi_vs_CD', 100),
    ):
        lines.append(f'| {label} | {metric_text(m[name], scale)} | {v[decision]} |')
    for arm in ('C-hi', 'C-lo'):
        lines.append(f"| V5 ψ_{arm} | {metric_text(m['psi'][arm])} | {v['V5'][arm]} |")
    lines += ['', f"V1 verdict **{v['V1']}**. V5 primary **{v['v5_primary'].upper()}**, "
              f"verdict **{v['v5_primary_verdict']}**. Non-inferiority margin **{MARGIN * 100:.3f} pp**.", '',
              '| Layer | Frozen verdict |', '|---|---|']
    for label, key in (('Spectral mechanism', 'spectral_mechanism'),
                       ('Operational compatibility', 'operational_compatibility'), ('Joint claim', 'joint_claim')):
        lines.append(f"| {label} | {v['layers'][key]} |")
    lines += ['', '### CSTATE non-inferiority methods', '',
              '| Comparison | Method | Discordant frame clusters | Candidate-only failure clusters | Reference-only failure clusters |',
              '|---|---|---:|---:|---:|']
    for label, key in (('U − CD', 'delta_UC'), ('C-hi − CD', 'delta_C_hi_CD')):
        row = m[key]
        lines.append(f"| {label} | {row['method']} | {row['discordant_frame_clusters']} | "
                     f"{row['candidate_only_failure_clusters']} | {row['reference_only_failure_clusters']} |")
    lines += ['', '### V5-adm, secondary', '',
              f"{m['admission']['n_units']:,} eligible units in {m['admission']['n_frame_clusters']} frame clusters. "
              f"Verdict **{v['V5_adm']['verdict']}**.", '',
              '| Arm | Phantom preference % [95% CI] | π [95% CI] | Split verdict |', '|---|---:|---:|---|']
    for arm in C_ARMS[1:]:
        rate = result['admission_preferences'].get(arm)
        ratio = m['admission']['pi'].get(arm)
        lines.append(f"| {arm} | {metric_text(rate, 100) if rate else 'NA'} | "
                     f"{metric_text(ratio) if ratio else '—'} | {v['V5_adm'].get(arm, '—')} |")
    lines += ['', '## Secondary readouts', '', '### Whole-grid FER and SBL contrasts', '',
              '| Leg | Arm | FER % [95% CI] |', '|---|---|---:|']
    for leg, arms in result['whole_grid_fer_ci'].items():
        for arm, entry in arms.items():
            lines.append(f'| {leg} | {arm} | {metric_text(entry, 100)} |')
    lines += ['', '| Contrast | Difference (pp) [95% CI] |', '|---|---:|']
    for name in ('S-lo_minus_R0', 'U2_minus_R0'):
        lines.append(f"| {name.replace('_minus_', ' − ')} | {metric_text(result['secondary'][name], 100)} |")
    lines += ['', 'Common subgrid, ρ = .3 and SNR 6–11 dB.', '',
              '| Crossover | Sign | Difference (pp) [95% CI] |', '|---|---|---:|']
    for key, label in (('G_B', 'R1 − R0'), ('A2_minus_CD', 'A2 − CD')):
        row = result['common_grid'][key]
        lines.append(f"| {label} | {row['sign']} | {row['point'] * 100:.3f} {interval_text(row['interval95'], 100)} |")
    lines += ['', '### SBL EM and output geometry', '',
              '| Arm | β | Iterations | Convergence % | Output atoms | Co-delay pairs | NMSE |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for arm, entry in result['diagnostics']['sbl'].items():
        columns = [metric_text(entry[name], 100 if name == 'converged' else 1)
                   for name in ('beta', 'iterations', 'converged', 'n_atoms', 'n_pair', 'nmse')]
        lines.append(f"| {arm} | {' | '.join(columns)} |")
    lines += ['', '### CSTATE output geometry and first edit', '',
              '| Arm | Output atoms | Output co-delay pairs |', '|---|---:|---:|']
    for arm, entry in result['diagnostics']['cstate_support'].items():
        lines.append(f"| {arm} | {metric_text(entry['atom_count'])} | {metric_text(entry['co_delay_pairs'])} |")
    lines += ['', 'Phantom class P uses the accepted first replacement on a delay held by a surviving atom.', '',
              '| Arm | Accepted first edits | No accepted edit among triggers | Existing-delay % of accepted | New-delay % of accepted | Phantom P % of triggers |',
              '|---|---:|---:|---:|---:|---:|']
    for arm, entry in result['diagnostics']['first_edit'].items():
        lines.append(f"| {arm} | {entry['existing']['denominator']:,} | {entry['triggered_without_accepted_edit']:,} | "
                     f"{metric_text(entry['existing'], 100)} | {metric_text(entry['new'], 100)} | "
                     f"{metric_text(entry['P_among_triggers'], 100)} |")
    lines += ['', '### CSTATE projector census', '',
              '| Diagnostic | Count / denominator | Percent [95% CI] |', '|---|---:|---:|']
    for key, entry in result['diagnostics']['projector_census'].items():
        labels = {'U_CD_different': 'U/CD different exchange decisions',
                  'true_close_among_U_CD_different': 'True co-delay pair within 0.5 bin among differing keys'}
        label = labels[key] if key in labels else f"{key.replace('/', ' ')} trials with nonempty Π_lo"
        lines.append(f"| {label} | {entry['numerator']:,} / {entry['denominator']:,} | {metric_text(entry, 100)} |")
    lines += ['', '### CSTATE cell FER and 10⁻² crossings', '',
              'FER entries are percentages with 95% CIs. Crossings are in dB, with infinite endpoints for censored draws.', '']
    for cell, entry in result['cstate_cells'].items():
        scenario, rho = cell.split('_')
        lines += [f'#### {scenario}, ρ = {int(rho) / 1000:.1f}', '',
                  '| SNR (dB) | ' + ' | '.join(C_ARMS) + ' |', '|---|' + '---:|' * len(C_ARMS)]
        for label, rates in [('Pooled', entry['pooled']), *[(f'{int(k)/100:g}', v) for k, v in entry['by_snr'].items()]]:
            fer = [f"{rates[a]['point'] * 100:.3f} {interval_text(rates[a]['interval95'], 100)}" for a in C_ARMS]
            lines.append(f"| {label} | {' | '.join(fer)} |")
        lines += ['', '| Arm | Crossing point bounds | 95% bounds | Left-censored draws | Right-censored draws |',
                  '|---|---:|---:|---:|---:|']
        for arm, row in entry['crossings'].items():
            lines.append(f"| {arm} | {interval_text(row['point'])} | {interval_text(row['interval95'])} | "
                         f"{row['left_censored_draws']:,} | {row['right_censored_draws']:,} |")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--producing-commit', required=True)
    args = p.parse_args()
    rows, receiver, manifest_md5 = read_inputs(args.out, args.producing_commit)
    result = summarize(rows)
    result.update(_argv=sys.argv, _config=dict(receiver['_config'], receiver_argv=receiver['_argv'],
                  rows_manifest_md5=manifest_md5, margin=MARGIN, v5_primary=V5_PRIMARY,
                  bootstrap_draws=verdict.N_BOOT, bootstrap_seed=verdict.SEED))
    report = markdown(result)
    with (args.out / 'results.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    with (args.out / 'RESULTS.md').open('x') as handle:
        handle.write(report)
    print(f"Verified {result['keys']['sbl']} SBL and {result['keys']['cstate']} CSTATE keys and wrote frozen verdicts",
          flush=True)


if __name__ == '__main__':
    main()
