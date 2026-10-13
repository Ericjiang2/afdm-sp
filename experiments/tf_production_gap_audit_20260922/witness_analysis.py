"""Read-only Part-B codeword/channel witnesses; no receiver calls.

CLI requires an A selection and B instrumented baseline replays.  Original
checkpoints remain the deployed baseline; replays supply previously unavailable
acquisition/refit metadata.  All truth use is confined to this offline runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

import audit_io
import metrics


def _read_manifest(run, source, baseline):
    evidence = audit_io.attach(source, baseline)
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    audit_io.verify_sources(manifest, source, baseline, evidence)
    return evidence, manifest, audit_io.sha256(manifest_path)


def _code(baseline, header):
    cache = (baseline / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled'
             / 'e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    with np.load(cache, allow_pickle=False) as saved:
        code = {key: np.asarray(saved[key]).copy() for key in ('H', 'G', 'free_cols')}
    digest = hashlib.sha256(np.ascontiguousarray(code['G']).tobytes()).hexdigest()
    if digest != header['code_g_sha256']:
        raise ValueError('actual LDPC generator differs from Part-B header')
    return code, cache


def _heavy_mapping_check(run, tf, evidence, pd):
    """Hash-bound stored-data cross-check on the original 6.5 dB audit frame 0."""
    inventory_path = run.parent / 'remote_inventory.json'
    inventory = json.loads(inventory_path.read_text())
    if inventory.get('status') != 'pass':
        raise ValueError('original heavy inventory is not complete')
    heavy_key, compact_key = 'run/heavy/s650_f0000_truth.npz', 'run/frames/s650_f0000_truth.npz'
    matching = {key:[entry for entry in inventory['entries'] if entry['path'] == key]
                for key in (heavy_key, compact_key)}
    if any(len(matches) != 1 for matches in matching.values()):
        raise ValueError('original inventory lacks heavy/compact mapping exemplar')
    entries = {key:matches[0] for key, matches in matching.items()}
    record = next((r for r in tf if r['snr_centi_db'] == 650 and r['frame'] == 0), None)
    if record is None or entries[compact_key]['sha256'] != record['frame_sha256']:
        raise ValueError('compact mapping exemplar differs from ledger/inventory')
    compact = audit_io.load_bound(evidence, run / 'frames/s650_f0000_truth.npz',
                                  record['frame_sha256'])
    heavy = audit_io.load_bound(evidence, run / 'heavy/s650_f0000_truth.npz',
                                entries[heavy_key]['sha256'])
    bits = _bits(compact['coded'])
    heavy_bits = np.asarray(heavy['coded'])
    if (heavy_bits.shape != bits.shape or not np.isin(heavy_bits, (0, 1)).all()
            or not np.array_equal(bits, heavy_bits)
            or not np.array_equal(_bits(compact['info']), np.asarray(heavy['info']))
            or not np.isclose(float(compact['unit_scale']), float(heavy['unit_scale']), atol=1e-12)
            or not np.allclose(_map(bits, pd), np.asarray(heavy['data']) / float(heavy['unit_scale']),
                               rtol=1e-12, atol=1e-12)):
        raise ValueError('stored-data QPSK mapping differs from compact coded bits')
    return dict(status='pass', scope='one original audit exemplar; selected compact truths omit data',
                inventory_sha256=audit_io.sha256(inventory_path),
                heavy_truth_sha256=entries[heavy_key]['sha256'],
                compact_truth_sha256=record['frame_sha256'],
                coded_bits_equal=True, mapped_data_equal=True)


def _bits(payload):
    return audit_io.unpack(payload)


def _valid(bits, H):
    return int(np.count_nonzero((H.astype(np.int32) @ bits.astype(np.int32)) % 2)) == 0


def _encode(info, G):
    return ((G.astype(np.int32) @ info.astype(np.int32)) % 2).astype(np.uint8)


def _map(bits, pd):
    from afdm_sp_joint_unrolled.e1_ldpc import qpsk_map
    return np.sqrt(pd) * qpsk_map(bits, scale=1)


def _channel(n, c1, c2, delays, dopplers, gains):
    from physical import Channel
    return Channel(n, c1, c2, delays, dopplers, gains)


def _time(y, c1, c2):
    from physical import daft
    return daft(y, c1, c2, True)


def _original(run, record, evidence):
    obs, checkpoints = _observed_original(run, record, evidence)
    stem = f"s{record['snr_centi_db']}_f{record['frame']:04d}"
    truth = audit_io.load_bound(evidence, run / 'frames' / f'{stem}_truth.npz', record['frame_sha256'])
    return obs, truth, checkpoints


def _observed_original(run, record, evidence):
    stem = f"s{record['snr_centi_db']}_f{record['frame']:04d}"
    obs = audit_io.load_bound(evidence, run / 'frames' / f'{stem}_input.npz', record['input_sha256'])
    checkpoints = [audit_io.load_bound(evidence, run / cp['path'], cp['artifact_sha256'])
                   for cp in record['checkpoints']]
    if len(checkpoints) != 2:
        raise ValueError(f'{stem} does not have exactly two frozen checkpoints')
    return obs, checkpoints


def _replay(b_output, observation_id, evidence, hashes):
    digest = hashes.get(observation_id)
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError(f'missing bound B baseline replay: {observation_id}')
    payload = audit_io.load_bound(evidence, b_output / 'baseline_replay' / f'{observation_id}.npz', digest)
    if set(payload) != {'decoder', 'arrays', 'timing', 'trace'}:
        raise ValueError(f'B replay payload differs for {observation_id}')
    trace = payload['trace']
    if trace.get('arm') != 'baseline_replay' or trace.get('acquisition') is None or len(trace.get('refits', [])) != 2:
        raise ValueError(f'B replay lacks acquisition/refit trace: {observation_id}')
    return payload


def _observable(obs, checkpoints, replay, parity_check, c1, c2):
    """Extract a label-free feature vector before accessing truth or error counts."""
    s0, s1 = (cp['snapshot'] for cp in checkpoints)
    decoded0, decoded1 = (_bits(cp['decoded']) for cp in checkpoints)
    app = np.asarray(s1['app'], float)
    y, pilot = np.asarray(obs['y']), np.asarray(obs['pilot'])
    n = len(y)
    H = _channel(n, c1, c2, s1['delays'], s1['dopplers'], s1['gains'])
    soft = np.asarray(s1['mu'])
    residual = y - H.apply(pilot + soft)
    sigma2 = float(obs['sigma2'])
    if sigma2 <= 0 or not np.isfinite(sigma2) or not np.isfinite(app).all():
        raise ValueError('invalid observed noise or final APP')
    refit = replay['trace']['refits'][-1]
    lohi = np.asarray(refit['bounds'], float)
    nu = np.asarray(s1['dopplers'], float)
    if lohi.shape != (len(nu), 2):
        raise ValueError('replay refit bounds differ from saved geometry')
    boundary = np.minimum(nu - lohi[:, 0], lohi[:, 1] - nu)
    if np.any(boundary < -0.005):
        raise ValueError('saved Doppler falls outside replay refit bounds')
    syndrome = int(np.count_nonzero((parity_check.astype(np.int32) @ decoded1.astype(np.int32)) % 2))
    return dict(syndrome_weight=syndrome,
                app_abs_mean=float(np.mean(abs(app))), app_abs_min=float(np.min(abs(app))),
                app_abs_below2_fraction=float(np.mean(abs(app) < 2)),
                round_disagreement=int(np.count_nonzero(decoded0 != decoded1)),
                observed_residual_power=float(np.vdot(residual, residual).real),
                observed_residual_over_noise=float(np.vdot(residual, residual).real / (n * sigma2)),
                refit_min_boundary_distance=float(np.min(boundary)),
                refit_boundary_hit=bool(np.any(boundary <= .002)),
                fitted_path_count=len(nu),
                data_precision_floor_count=sum(int(t['data_precision_floor']) for t in s1['inference_trace']),
                gain_precision_floor_count=sum(int(t['gain_precision_floor']) for t in s1['inference_trace']))


ARMS = ('J40R2', 'J20R3', 'true_geometry', 'true_H_TF20R2', 'true_H_EP8R2',
        'true_data_original_TF20R2', 'true_data_expanded_TF20R2')


def _arm_slug(arm):
    return arm.lower()


def _bound_b_ledger(b_output, receipt, selected):
    ledger = b_output / 'ledger.jsonl'
    digest = audit_io.sha256(ledger)
    if digest != receipt.get('ledger_sha256') or digest != receipt.get('files', {}).get('ledger.jsonl'):
        raise ValueError('B ledger is not bound by receipt')
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    ids = {x['observation_id'] for x in selected}
    required = {'baseline_replay', *ARMS}
    keys = [(r.get('observation_id'), r.get('arm')) for r in records]
    if (len(records) != 512 or len(set(keys)) != 512
            or set(keys) != {(observation_id, arm) for observation_id in ids for arm in required}):
        raise ValueError('B ledger intervention allocation differs')
    by_key = {}
    for row in records:
        if row.get('status') != 'ok' or not isinstance(row.get('info_errors'), int) or row['info_errors'] < 0:
            raise ValueError('B ledger lacks a successful scored intervention')
        if row['arm'] in ARMS:
            baseline_error = bool(row.get('baseline_error'))
            if bool(row.get('rescue')) != bool(baseline_error and row['info_errors'] == 0):
                raise ValueError('B rescue flag differs from scored errors')
            if bool(row.get('harm')) != bool(not baseline_error and row['info_errors'] > 0):
                raise ValueError('B harm flag differs from scored errors')
        by_key[(row['observation_id'], row['arm'])] = row
    return by_key


def _feature_bins(features):
    """Frozen descriptive cut points; none is a learned decision threshold."""
    syndrome = features['syndrome_weight']
    confidence = features['app_abs_mean']
    low_fraction = features['app_abs_below2_fraction']
    residual = features['observed_residual_over_noise']
    disagreement = features['round_disagreement']
    paths = features['fitted_path_count']
    return dict(syndrome_bin='0' if syndrome == 0 else '1-4' if syndrome <= 4 else '5-20' if syndrome <= 20 else '>20',
                app_mean_bin='<2' if confidence < 2 else '2-5' if confidence < 5 else '>=5',
                app_below2_fraction_bin='<0.1' if low_fraction < .1 else '0.1-0.5' if low_fraction < .5 else '>=0.5',
                residual_noise_bin='<1' if residual < 1 else '1-2' if residual < 2 else '>=2',
                disagreement_bin='0' if disagreement == 0 else '1-10' if disagreement <= 10 else '>10',
                boundary_bin='hit' if features['refit_boundary_hit'] else 'clear',
                fitted_p_bin='<=4' if paths <= 4 else '5-8' if paths <= 8 else '>8')


def _recoverability_rows(selected, observable, b_ledger):
    rows = []
    for item in selected:
        observation_id = item['observation_id']
        baseline_error = bool(item['baseline_error'])
        features = observable[observation_id]
        row = dict(observation_id=observation_id, frame=item['frame'],
                   baseline_error=baseline_error, baseline_group='selected_failure' if baseline_error else 'selected_success',
                   **features, **_feature_bins(features))
        replay = b_ledger[(observation_id, 'baseline_replay')]
        if (bool(replay.get('baseline_error')) != baseline_error
                or bool(replay['info_errors']) != baseline_error):
            raise ValueError('B baseline replay group differs from A selection')
        row['baseline_replay_info_errors'] = replay['info_errors']
        for arm in ARMS:
            result = b_ledger[(observation_id, arm)]
            if bool(result.get('baseline_error')) != baseline_error:
                raise ValueError('B arm group differs from A selection')
            slug = _arm_slug(arm)
            row[f'{slug}_info_errors'] = result['info_errors']
            row[f'{slug}_error'] = bool(result['info_errors'] > 0)
            row[f'{slug}_rescue'] = bool(result['rescue'])
            row[f'{slug}_harm'] = bool(result['harm'])
        rows.append(row)
    return rows


def _group_features(rows):
    if not rows:
        return dict(count=0, feature_means=None)
    fields = ('syndrome_weight', 'app_abs_mean', 'app_abs_below2_fraction',
              'observed_residual_over_noise', 'round_disagreement',
              'refit_min_boundary_distance', 'fitted_path_count')
    return dict(count=len(rows), feature_means={key:float(np.mean([r[key] for r in rows])) for key in fields})


def _recoverability_summary(rows):
    """Within-selected descriptive concentration, never a population estimate."""
    failures = [r for r in rows if r['baseline_error']]
    successes = [r for r in rows if not r['baseline_error']]
    if len(failures) != 32 or len(successes) != 32:
        raise ValueError('recoverability needs exactly 32 failure/success controls')
    bin_fields = ('syndrome_bin', 'app_mean_bin', 'app_below2_fraction_bin',
                  'residual_noise_bin', 'disagreement_bin', 'boundary_bin', 'fitted_p_bin')
    by_arm = {}
    focus = []
    for arm in ARMS:
        slug = _arm_slug(arm)
        rescued = [r for r in failures if r[f'{slug}_rescue']]
        unrecovered = [r for r in failures if not r[f'{slug}_rescue']]
        harmed = [r for r in successes if r[f'{slug}_harm']]
        preserved = [r for r in successes if not r[f'{slug}_harm']]
        bins = {}
        for field in bin_fields:
            bins[field] = {}
            for value in sorted({r[field] for r in rows}):
                f = [r for r in failures if r[field] == value]
                c = [r for r in successes if r[field] == value]
                rescued_count = sum(bool(r[f'{slug}_rescue']) for r in f)
                harmed_count = sum(bool(r[f'{slug}_harm']) for r in c)
                bins[field][value] = dict(selected_failures=len(f), rescued=rescued_count,
                    unrecovered=len(f)-rescued_count, selected_success_controls=len(c),
                    harmed_controls=harmed_count, preserved_controls=len(c)-harmed_count,
                    selected_rescue_fraction=rescued_count / len(f) if f else None)
                if len(f) >= 4 and rescued_count >= 2:
                    focus.append(dict(arm=arm, feature_bin=field, bin=value,
                                      selected_failures=len(f), rescued=rescued_count,
                                      selected_rescue_fraction=rescued_count/len(f),
                                      contrast_to_arm=float(rescued_count/len(f)-len(rescued)/32)))
        by_arm[arm] = dict(rescued_failures=_group_features(rescued),
                           unrecovered_failures=_group_features(unrecovered),
                           selected_success_controls=_group_features(successes),
                           harmed_controls=_group_features(harmed),
                           preserved_controls=_group_features(preserved), bins=bins)
    focus.sort(key=lambda r:(-r['contrast_to_arm'], -r['rescued'], r['arm'], r['feature_bin'], r['bin']))
    return dict(scope='fixed selected 32 failures and 32 successful controls at 6.5dB',
                by_arm=by_arm, investigation_focus=focus[:10],
                interpretation='Descriptive concentration for deciding which observable states to inspect; no deployed trigger, classifier, population rescue probability, or causal claim.')


def _pilot_gain(Y, pilot, delays, dopplers, c1, c2, sigma2, pd):
    """Observed-data, pilot+zero-data soft ridge initialization at fixed geometry."""
    from physical import projected_variance
    B = metrics.response_matrix(pilot, delays, dopplers, c1, c2)
    gamma = projected_variance(np.full(len(Y), pd), delays, dopplers, c1)
    Q = B.conj().T @ B + gamma + sigma2 * np.eye(len(delays))
    h = np.linalg.solve(Q, B.conj().T @ Y)
    if not np.isfinite(h).all():
        raise FloatingPointError('nonfinite pilot/moment gain initialization')
    return h, gamma


def _operator_projection(working, truth, pilot, data_moments):
    from twofft import TimePathOps
    n = truth.n
    combined = _channel(n, truth.c1, truth.c2,
                        np.r_[working.delays, truth.delays],
                        np.r_[working.dopplers, truth.dopplers],
                        np.ones(working.p + truth.p, complex))
    R = TimePathOps(combined).R
    p = working.p
    A, cross = R[:p, :p], R[:p, p:]
    U, s, Vh = np.linalg.svd(A)
    tol = max(A.shape) * np.finfo(float).eps * s[0]
    rank = int(np.count_nonzero(s > tol))
    if rank == 0:
        raise ValueError('zero working physical operator span')
    right = cross @ truth.gains
    fitted = Vh.conj().T[:, :rank] @ ((U.conj().T @ right)[:rank] / s[:rank])
    projected = _channel(n, truth.c1, truth.c2, working.delays, working.dopplers, fitted)
    covariance = data_moments['covariance']
    mean = data_moments['mean']
    projected_gap = metrics.operator_mismatch(projected, truth, pilot,
                                              data_covariance=covariance, data_mean=mean)
    actual_gap = metrics.operator_mismatch(working, truth, pilot,
                                           data_covariance=covariance, data_mean=mean)
    true_power = float(n * np.vdot(truth.gains, R[p:, p:] @ truth.gains).real)
    if true_power <= 0:
        raise ValueError('zero true physical operator power')
    missing = ~np.isin(truth.delays, working.delays)
    missing_power = float(n * np.vdot(truth.gains[missing],
                    R[p:, p:][np.ix_(missing, missing)] @ truth.gains[missing]).real)
    return dict(operator_projection_rank=rank, operator_projection_columns=p,
                projected_mismatch_fraction=projected_gap['operator_frobenius_squared'] / true_power,
                actual_mismatch_fraction=actual_gap['operator_frobenius_squared'] / true_power,
                missing_distinct_delay_energy_fraction=missing_power / true_power,
                sp_weighted_mismatch=actual_gap['sp_weighted_mismatch'],
                true_operator_power=true_power,
                projected_gains=fitted, operator_gram=R)


def _initial_containment(acquisition, truth_delays, truth_dopplers):
    l0 = np.asarray(acquisition['delays'], int)
    nu0 = np.asarray(acquisition['dopplers'], float)
    if l0.shape != nu0.shape:
        raise ValueError('initial acquisition dimension mismatch')
    covered = np.array([any(l0 == l) for l in truth_delays])
    within = np.array([any((l0 == l) & (abs(nu0 - nu) <= .75 + 1e-12))
                       for l, nu in zip(truth_delays, truth_dopplers)])
    return dict(acquisition_path_count=len(l0), acquisition_distinct_delay_count=len(np.unique(l0)),
                true_paths_with_acquired_delay=int(np.count_nonzero(covered)),
                true_paths_in_acquisition_nominal_window=int(np.count_nonzero(within)))


def _first_refit_containment(refit, truth_delays, truth_dopplers):
    """Maximum one-to-one true-path coverage by actual first-refit slots/bounds."""
    delays = np.asarray(refit['selected_delays'], int)
    bounds = np.asarray(refit['bounds'], float)
    truth_delays = np.asarray(truth_delays, int)
    truth_dopplers = np.asarray(truth_dopplers, float)
    if (delays.ndim != 1 or not len(delays) or bounds.shape != (len(delays), 2)
            or truth_delays.shape != truth_dopplers.shape or not len(truth_delays)
            or not np.isfinite(bounds).all() or np.any(bounds[:, 0] > bounds[:, 1])):
        raise ValueError('invalid first-refit slots or bounds')
    delay_slots = sum(min(np.count_nonzero(delays == d), np.count_nonzero(truth_delays == d))
                      for d in np.unique(truth_delays))
    edges = [np.flatnonzero((delays == d) & (bounds[:, 0] - 1e-12 <= nu)
                           & (nu <= bounds[:, 1] + 1e-12)).tolist()
             for d, nu in zip(truth_delays, truth_dopplers)]
    owner = [-1] * len(delays)

    def augment(path, seen):
        for slot in edges[path]:
            if slot in seen:
                continue
            seen.add(slot)
            if owner[slot] < 0 or augment(owner[slot], seen):
                owner[slot] = path
                return True
        return False

    window_slots = sum(int(augment(path, set())) for path in range(len(truth_delays)))
    return dict(first_refit_selected_path_count=len(delays),
                first_refit_selected_distinct_delay_count=len(np.unique(delays)),
                first_refit_true_paths_with_selected_delay_slots=int(delay_slots),
                first_refit_true_paths_in_local_window=int(window_slots),
                first_refit_true_path_window_coverage_fraction=window_slots / len(truth_delays))


def _fixed_scores(Y, pilot, candidates, geometry, sigma2, ridge_lambda):
    out = {}
    for name, symbols in candidates.items():
        B = metrics.response_matrix(pilot + symbols, geometry.delays, geometry.dopplers,
                                    geometry.c1, geometry.c2)
        out[name] = metrics.score_geometry(Y, B, sigma2,
                       conditional_gains=geometry.gains, ridge_lambda=ridge_lambda)
    return out


def _broad_scores(Y, pilot, candidates, working, sigma2, ridge_lambda):
    bounds = metrics.final_refit_bounds(working.dopplers, expanded=True)
    starts = np.array([working.dopplers,
                       np.full(working.p, -2.), np.zeros(working.p),
                       np.full(working.p, 2.)])
    runs, costs = {}, []
    for name, symbols in candidates.items():
        x = pilot + symbols
        runs[name] = {}
        for objective in ('profile', 'marginal'):
            started = time.perf_counter()
            runs[name][objective] = metrics.search_geometry(Y, x, working.delays,
                starts, bounds, working.c1, working.c2, sigma2,
                objective=objective, ridge_lambda=ridge_lambda, passes=2, maxiter=16)
            costs.append(dict(candidate=name, objective=objective,
                              seconds=time.perf_counter() - started,
                              candidate_evaluations=runs[name][objective]['evaluations'],
                              start_count=runs[name][objective]['starts_count'],
                              coordinate_passes=runs[name][objective]['coordinate_passes']))
    baseline = runs['baseline']['profile']
    plug = _channel(working.n, working.c1, working.c2, working.delays,
                    baseline['dopplers'], working.gains)
    # The conditional comparator broadens Doppler only; saved working gains
    # remain fixed even though the broad baseline profile has fitted gains.
    conditional = _fixed_scores(Y, pilot, candidates, plug, sigma2, ridge_lambda)
    return runs, conditional, costs


def _score_row(prefix, scored, baseline_name='baseline', truth_name='truth'):
    b, t = scored[baseline_name], scored[truth_name]
    row = {}
    for key in ('conditional_score', 'profile_score', 'ridge_score', 'marginal_score', 'profile_rank'):
        if key in b and key in t:
            row[f'{prefix}_{key}_baseline'] = float(b[key]) if key != 'profile_rank' else int(b[key])
            row[f'{prefix}_{key}_truth'] = float(t[key]) if key != 'profile_rank' else int(t[key])
            if key != 'profile_rank':
                row[f'{prefix}_{key}_error_minus_truth'] = float(b[key] - t[key])
    return row


def _first32_selection(selection, tf):
    expected = audit_io.selected_records(tf)
    actual = selection.get('observations')
    if not isinstance(actual, list) or len(actual) != 64:
        raise ValueError('A selection is not 32 failures plus 32 successes')
    by_frame = {(r['snr_centi_db'], r['frame']): r for r in expected}
    if len({(r['baseline_record']['snr_centi_db'], r['frame']) for r in actual}) != 64:
        raise ValueError('duplicate selected observation')
    for row in actual:
        record = row['baseline_record']
        key = (record['snr_centi_db'], record['frame'])
        if key not in by_frame or record != by_frame[key] or row['frame'] != record['frame']:
            raise ValueError('selection record differs from frozen ledger')
        if row['observation_id'] != f"s650_f{record['frame']:04d}":
            raise ValueError('selection ID differs')
    return sorted(actual, key=lambda x: x['frame'])


def analyze(run, source, baseline, selection_path, b_output, out):
    run, source, baseline = Path(run), Path(source), Path(baseline)
    selection_path, b_output, out = Path(selection_path), Path(b_output), Path(out)
    if out.exists():
        raise FileExistsError('C output already exists; preserve prior evidence')
    evidence, manifest, manifest_hash = _read_manifest(run, source, baseline)
    _, tf = audit_io.read_records(run)
    selection = json.loads(selection_path.read_text())
    selected = _first32_selection(selection, tf)
    receipt = json.loads((b_output / 'receipt.json').read_text())
    b_manifest_path = b_output / 'manifest.json'
    if audit_io.sha256(b_manifest_path) != receipt.get('files', {}).get('manifest.json'):
        raise ValueError('B manifest is not bound by its receipt')
    b_manifest = json.loads(b_manifest_path.read_text())
    if (receipt.get('status') != 'pass' or receipt.get('receiver_calls') != 512
            or b_manifest.get('selection_sha256') != audit_io.sha256(selection_path)
            or b_manifest.get('original_manifest_sha256') != manifest_hash
            or b_manifest.get('audit_source_hashes', {}).get('metrics.py') != audit_io.sha256(Path(metrics.__file__))):
        raise ValueError('B receipt or source/selection identity differs')
    replay_hashes = receipt.get('baseline_replay_hashes')
    if not isinstance(replay_hashes, dict) or set(replay_hashes) != {x['observation_id'] for x in selected}:
        raise ValueError('B receipt does not bind exactly 64 baseline replays')
    b_ledger = _bound_b_ledger(b_output, receipt, selected)
    header = json.loads((run / 'context_header.json').read_text())
    code, code_cache = _code(baseline, header)
    n = header['system']['n_total']
    c1, c2 = header['system']['c1'], header['system']['c2']
    rho = header['system']['rho']
    pd = 1 - rho
    if n != 1024 or pd != .5 or code['G'].shape[0] != 2 * n:
        raise ValueError('unexpected Part-B physical/code domain')
    mapping_check = _heavy_mapping_check(run, tf, evidence, pd)
    # e1_ldpc G has coded-bit rows, information-bit columns.  Repeated rows
    # induce a few exact QPSK symbol correlations, retained sparsely.
    code_moments = metrics.exact_code_moments(code['G'], pd)
    success = [x for x in selected if not x['baseline_error']]
    failures = [x for x in selected if x['baseline_error']]
    if len(failures) != 32 or len(success) != 32:
        raise ValueError('selection class counts differ')
    # Features are fully extracted from observations/checkpoints/replay before
    # any truth artifact is opened for C witnesses or labels are joined.
    observable = {}
    for item in selected:
        obs0, cps0 = _observed_original(run, item['baseline_record'], evidence)
        replay0 = _replay(b_output, item['observation_id'], evidence, replay_hashes)
        observable[item['observation_id']] = _observable(obs0, cps0, replay0, code['H'], c1, c2)
    recoverability = _recoverability_rows(selected, observable, b_ledger)
    recoverability_summary = _recoverability_summary(recoverability)
    out.mkdir(parents=True)
    (out / 'raw').mkdir()
    rows, controls = [], []
    stage, fit_records = [], []
    for pair_index, (bad, good) in enumerate(zip(failures, success)):
        fid = bad['observation_id']
        t0 = time.perf_counter()
        record = bad['baseline_record']
        obs, truth, cps = _original(run, record, evidence)
        replay = _replay(b_output, fid, evidence, replay_hashes)
        features = observable[fid]
        final = cps[-1]['snapshot']
        raw = _bits(cps[-1]['decoded'])
        true_bits = _bits(truth['coded'])
        info = _bits(truth['info'])
        if not np.array_equal(true_bits[code['free_cols']], info) or not _valid(true_bits, code['H']):
            raise ValueError(f'true word/code identity broken: {fid}')
        if not np.isclose(float(truth['unit_scale']), np.sqrt(2 * pd), atol=1e-12):
            raise ValueError(f'saved unit scale differs: {fid}')
        syndrome = int(np.count_nonzero((code['H'].astype(np.int32) @ raw.astype(np.int32)) % 2))
        legal = _encode(raw[code['free_cols']], code['G'])
        if not _valid(legal, code['H']):
            raise ValueError('reencoded candidate is not a codeword')
        candidate_bits = raw if syndrome == 0 else legal
        raw_valid = syndrome == 0
        y, pilot = np.asarray(obs['y']), np.asarray(obs['pilot'])
        sigma2 = float(obs['sigma2'])
        Y = _time(y, c1, c2)
        working = _channel(n, c1, c2, final['delays'], final['dopplers'], final['gains'])
        h_true_init, gamma = _pilot_gain(Y, pilot, truth['l_i'], truth['k_real'], c1, c2, sigma2, pd)
        true_init = _channel(n, c1, c2, truth['l_i'], truth['k_real'], h_true_init)
        true_physical = _channel(n, c1, c2, truth['l_i'], truth['k_real'], truth['g_i'])
        candidates = {'baseline': _map(candidate_bits, pd), 'truth': _map(true_bits, pd)}
        work_scores = _fixed_scores(Y, pilot, candidates, working, sigma2, sigma2 * working.p)
        truth_scores = _fixed_scores(Y, pilot, candidates, true_init, sigma2, sigma2 * true_init.p)
        fixed_seconds = time.perf_counter() - t0
        t1 = time.perf_counter()
        broad, broad_cond, fit_costs = _broad_scores(Y, pilot, candidates, working, sigma2,
                                                      sigma2 * working.p)
        broad_seconds = time.perf_counter() - t1
        fit_records.extend(dict(observation_id=fid, **cost, receiver_calls=0) for cost in fit_costs)
        t2 = time.perf_counter()
        operator = _operator_projection(working, true_physical, pilot, code_moments)
        containment = _initial_containment(replay['trace']['acquisition'],
                                           true_physical.delays, true_physical.dopplers)
        first_refit_containment = _first_refit_containment(replay['trace']['refits'][0],
                                            true_physical.delays, true_physical.dopplers)
        B, dB = metrics.response_matrix(pilot + candidates['baseline'],
                working.delays, working.dopplers, c1, c2, derivative=True)
        contrast = _time(working.apply(candidates['truth'] - candidates['baseline']), c1, c2)
        tangent = metrics.real_tangent_projection(contrast, B, dB, working.gains)
        iso = metrics.isotropic_real_controls(contrast, B, dB, working.gains,
                                             count=32, seed=20260922 + pair_index)
        operator_seconds = time.perf_counter() - t2
        t3 = time.perf_counter()
        gobs, gtruth, gcps = _original(run, good['baseline_record'], evidence)
        gfinal = gcps[-1]['snapshot']
        gchan = _channel(n, c1, c2, gfinal['delays'], gfinal['dopplers'], gfinal['gains'])
        gtrue_bits = _bits(gtruth['coded'])
        transplanted = metrics.transplant_legal_error_contrast(true_bits, candidate_bits,
                gtrue_bits, is_legal=lambda b: _valid(b, code['H']),
                bits_to_symbols=lambda b: _map(b, pd), success_channel=gchan)
        gB, gdB = metrics.response_matrix(np.asarray(gobs['pilot']) + _map(transplanted['bits'], pd),
                    gchan.delays, gchan.dopplers, c1, c2, derivative=True)
        matched = metrics.real_tangent_projection(transplanted['contrast_time'], gB, gdB, gchan.gains)
        control_seconds = time.perf_counter() - t3
        scores = {**_score_row('working', work_scores), **_score_row('true_geometry', truth_scores),
                  **_score_row('broad_plugin', broad_cond)}
        for objective in ('profile', 'marginal'):
            b, t = broad['baseline'][objective], broad['truth'][objective]
            scores[f'broad_{objective}_baseline'] = b['score']
            scores[f'broad_{objective}_truth'] = t['score']
            scores[f'broad_{objective}_error_minus_truth'] = b['score'] - t['score']
            scores[f'broad_{objective}_evaluations'] = b['evaluations'] + t['evaluations']
        row = dict(observation_id=fid, frame=bad['frame'], matched_success_id=good['observation_id'],
                   raw_syndrome_weight=syndrome, raw_valid=raw_valid,
                   raw_equals_truth=bool(np.array_equal(raw, true_bits)),
                   reencoded_equals_raw=bool(np.array_equal(legal, raw)),
                   candidate_equals_truth=bool(np.array_equal(candidate_bits, true_bits)),
                   candidate_source='raw_valid' if raw_valid else 'reencoded_information',
                   mapped_symbol_source='derived_from_saved_coded_bits',
                   selected_truth_data_available=False,
                   true_conditional_gain_source='observed_pilot_zero_data_soft_ridge',
                   broad_conditional_gain_source='saved_working_gains',
                   working_path_count=working.p, true_path_count=true_physical.p,
                   same_y_geometry_plugin=True, gaussian_gain_prior_physical_law_mismatch=True,
                   exact_code_covariance_offdiagonal_count=code_moments['covariance_offdiagonal_count'],
                   **features, **scores, **{k:v for k,v in operator.items() if not isinstance(v, np.ndarray)},
                   **containment, **first_refit_containment,
                   nuisance_projection_fraction=tangent['projection_fraction'],
                   nuisance_rank=tangent['tangent_rank'])
        row['syndrome_weight'] = syndrome
        rows.append(row)
        controls.append(dict(observation_id=fid, matched_success_id=good['observation_id'],
                             hamming_weight=transplanted['hamming_weight'],
                             failure_projection_fraction=tangent['projection_fraction'],
                             matched_success_projection_fraction=matched['projection_fraction'],
                             matched_success_rank=matched['tangent_rank'],
                             isotropic_projection_mean=float(iso.mean()),
                             isotropic_projection_median=float(np.median(iso)),
                             isotropic_projection_max=float(iso.max()), isotropic_count=len(iso)))
        raw_payload = dict(raw_bits=raw, reencoded_bits=legal, candidate_bits=candidate_bits,
            truth_bits=true_bits, working_scores=work_scores, true_geometry_scores=truth_scores,
            broad_search=broad, broad_conditional=broad_cond,
            true_geometry_pilot_gains=h_true_init, true_geometry_pilot_gamma=gamma,
            operator=operator, tangent=tangent, isotropic_fractions=iso,
            matched_success_bits=transplanted['bits'], matched_tangent=matched)
        evidence.save_artifact(out / 'raw' / f'{fid}.npz', raw_payload,
             {'kind':'tf_production_gap_c_witness','observation_id':fid,
              'original_manifest_sha256':manifest_hash,
              'selection_sha256':audit_io.sha256(selection_path),
              'b_replay_sha256':replay_hashes[fid]})
        stage.append(dict(observation_id=fid, fixed_scoring_seconds=fixed_seconds,
                          broad_search_seconds=broad_seconds, operator_nuisance_seconds=operator_seconds,
                          matched_control_seconds=control_seconds,
                          fixed_geometry_score_evaluations=4,
                          broad_plugin_score_evaluations=2,
                          true_geometry_pilot_gain_solves=1,
                          operator_projection_solves=1,
                          profile_candidate_evaluations=sum(broad[name]['profile']['evaluations'] for name in candidates),
                          marginal_candidate_evaluations=sum(broad[name]['marginal']['evaluations'] for name in candidates),
                          receiver_calls=0))
    audit_io.write_csv(out / 'witness_metrics.csv', rows)
    audit_io.write_csv(out / 'nuisance_controls.csv', controls)
    audit_io.write_csv(out / 'fit_costs.csv', stage)
    audit_io.write_csv(out / 'candidate_fit_costs.csv', fit_records)
    audit_io.write_csv(out / 'observable_recoverability.csv', recoverability)
    audit_io.write_json(out / 'observable_recoverability_summary.json', recoverability_summary)
    summary = dict(scope='32 selected failures at 6.5dB; descriptive same-y witnesses only',
                   witness_count=len(rows), matched_controls=len(controls),
                   observable_frames=len(recoverability),
                   receiver_calls_added=0,
                   profile_candidate_evaluations=sum(x['profile_candidate_evaluations'] for x in stage),
                   marginal_candidate_evaluations=sum(x['marginal_candidate_evaluations'] for x in stage),
                   raw_invalid_count=sum(not x['raw_valid'] for x in rows),
                   working_profile_truth_preferred=sum(x['working_profile_score_error_minus_truth'] > 0 for x in rows),
                   broad_profile_truth_preferred=sum(x['broad_profile_error_minus_truth'] > 0 for x in rows),
                   gaussian_prior_note='CN(0,I/P) score prior differs from normalized physical gain generation',
                   conditional_true_geometry_note='baseline gains estimated from observed pilot with zero data mean, uniform Pd variance, and sigma2 ridge; true gains never initialize a score',
                   exact_code_covariance_note='SP mismatch uses generator-derived sparse covariance; pilot gain initialization retains the declared receiver uniform-variance surrogate',
                   mapped_symbol_evidence='selected compact truth has coded bits and unit_scale but no stored data; hash-bound original heavy frame0 confirms source QPSK mapping',
                   broad_conditional_note='baseline broad-profile Dopplers with unchanged saved working gains',
                   broad_search_note='four deterministic starts and two bounded coordinate passes per candidate/objective; local finite search')
    audit_io.write_json(out / 'summary.json', summary)
    audit_io.write_json(out / 'receipt.json', dict(status='pass', receiver_calls_added=0,
        original_run=str(run), original_manifest_sha256=manifest_hash,
        original_ledger_sha256=audit_io.sha256(run / 'ledger.jsonl'),
        selection_sha256=audit_io.sha256(selection_path),
        b_receipt_sha256=audit_io.sha256(b_output / 'receipt.json'),
        b_ledger_sha256=receipt['ledger_sha256'],
        source_hashes=manifest['source_hashes'], baseline_source_hashes=manifest['baseline_source_hashes'],
        metrics_sha256=audit_io.sha256(Path(metrics.__file__)),
        witness_source_sha256=audit_io.sha256(Path(__file__)),
        code_cache_sha256=audit_io.sha256(code_cache),
        stored_data_mapping_check=mapping_check,
        code_moments=dict(zero_mean=code_moments['zero_mean'],
            scalar_covariance=code_moments['scalar_covariance'],
            duplicate_generator_row_groups=code_moments['duplicate_generator_row_groups'],
            covariance_offdiagonal_count=code_moments['covariance_offdiagonal_count']),
        files={p.relative_to(out).as_posix():audit_io.sha256(p)
               for p in out.rglob('*') if p.is_file() and p.name != 'receipt.json'}))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'source', 'baseline', 'selection', 'b-output', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    analyze(args.run, args.source, args.baseline, args.selection, args.b_output, args.out)


if __name__ == '__main__':
    main()
