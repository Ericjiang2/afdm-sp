"""Offline analysis of sealed LOCAL20/GLOBAL20 geometry reopening evidence.

Truth enters only after the observed run is sealed.  Rank and deadline helpers
are pure so the producer schema can be checked before any analysis write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np


ARMS = ('LOCAL20', 'GLOBAL20')
DEADLINES = (0.5, 1.0)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def rank_score_grid(scores, valid, candidate_delays, candidate_dopplers):
    """Exact 1-based ranks under (score, slot, delay, Doppler) tie order.

    Invalid slot/atom pairs have rank zero.  All valid pairs are ranked from
    the complete score grid, regardless of whether they entered a stored topK.
    """
    score = np.asarray(scores, float)
    mask = np.asarray(valid, bool)
    delays = np.asarray(candidate_delays)
    dopplers = np.asarray(candidate_dopplers, float)
    if (score.ndim != 2 or not score.shape[0] or not score.shape[1]
            or mask.shape != score.shape or delays.shape != (score.shape[1],)
            or dopplers.shape != delays.shape
            or not np.issubdtype(delays.dtype, np.integer)
            or not np.isfinite(dopplers).all() or not np.isfinite(score[mask]).all()
            or len(set(zip(delays.tolist(), dopplers.tolist()))) != len(delays)):
        raise ValueError('invalid complete global score grid')
    slot_index, atom_index = np.nonzero(mask)
    if not len(slot_index):
        raise ValueError('global trace has no valid slot/atom score')
    values = score[slot_index, atom_index]
    order = np.lexsort((dopplers[atom_index], delays[atom_index], slot_index, values))
    ranks = np.zeros(score.shape, dtype=int)
    ranks[slot_index[order], atom_index[order]] = np.arange(1, len(order)+1)
    return ranks


def nearest_grid_atom(true_delay, true_doppler, candidate_delays, candidate_dopplers):
    """Same integer delay, closest grid Doppler; exact ties choose lower nu."""
    delays = np.asarray(candidate_delays)
    dopplers = np.asarray(candidate_dopplers, float)
    same = np.flatnonzero(delays == true_delay)
    if not len(same):
        return None
    order = np.lexsort((dopplers[same], abs(dopplers[same] - true_doppler)))
    return int(same[order[0]])


def truth_rank_rows(scores, valid, candidate_delays, candidate_dopplers,
                    true_delays, true_dopplers, true_gains, *,
                    observation_id, global_step):
    """Retain one row per physical true path, including duplicate delays."""
    ltrue = np.asarray(true_delays)
    nutrue = np.asarray(true_dopplers, float)
    gains = np.asarray(true_gains, complex)
    if (ltrue.ndim != 1 or not len(ltrue) or not np.issubdtype(ltrue.dtype, np.integer)
            or ltrue.shape != nutrue.shape or ltrue.shape != gains.shape
            or not np.isfinite(nutrue).all() or not np.isfinite(gains).all()):
        raise ValueError('invalid physical truth paths')
    ranks = rank_score_grid(scores, valid, candidate_delays, candidate_dopplers)
    rows = []
    for path_index, (delay, nu, gain) in enumerate(zip(ltrue, nutrue, gains)):
        atom = nearest_grid_atom(delay, nu, candidate_delays, candidate_dopplers)
        slot_ranks = [int(value) if value else None for value in ranks[:, atom]] if atom is not None else [None]*ranks.shape[0]
        available = [value for value in slot_ranks if value is not None]
        best = min(available) if available else None
        rows.append(dict(observation_id=observation_id, global_step=int(global_step),
            true_path_index=path_index, true_delay=int(delay), true_doppler=float(nu),
            true_nominal_gain_energy=float(abs(gain)**2),
            nearest_grid_candidate_index=atom,
            nearest_grid_doppler=float(candidate_dopplers[atom]) if atom is not None else None,
            nearest_grid_doppler_error=float(abs(candidate_dopplers[atom]-nu)) if atom is not None else None,
            rank_by_replacement_slot=slot_ranks, best_global_rank=best,
            in_top1=bool(best is not None and best <= 1),
            in_top10=bool(best is not None and best <= 10),
            in_top20=bool(best is not None and best <= 20),
            outside_top20=bool(best is not None and best > 20),
            missing_or_all_slots_masked=best is None))
    return rows


def add_geometry_proximity(rows, entering_paths, accepted, *, grid_step=.25):
    """Annotate ranks with physical coverage before and after the accepted edit.

    A same-delay distance is left absent for a missing delay; no distinct-delay
    atom is treated as a nearby Doppler representation of the true path.
    """
    if not np.isfinite(grid_step) or grid_step <= 0:
        raise ValueError('invalid declared grid step')
    entering = [(int(path['delay']), float(path['doppler'])) for path in entering_paths]
    replacement = None if accepted is None else accepted['new']
    for row in rows:
        distances = [abs(nu-row['true_doppler']) for delay, nu in entering
                     if delay == row['true_delay']]
        minimum = min(distances) if distances else None
        row['entering_same_delay_min_doppler_distance'] = minimum
        row['entering_same_delay_path_count'] = len(distances)
        row['entering_same_delay_exact_atom'] = bool(minimum is not None and minimum <= 1e-6)
        row['entering_same_delay_within_half_grid_step'] = bool(
            minimum is not None and minimum <= grid_step/2)
        row['accepted_new_delay'] = None if replacement is None else int(replacement['delay'])
        row['accepted_new_doppler'] = None if replacement is None else float(replacement['doppler'])
        row['accepted_new_same_delay_doppler_distance'] = (
            abs(float(replacement['doppler'])-row['true_doppler'])
            if replacement is not None and int(replacement['delay']) == row['true_delay'] else None)
    return rows


def latest_available(decisions, deadline):
    """Use the latest ready decision; later missed work cannot erase fallback."""
    if not np.isfinite(deadline) or deadline < 0:
        raise ValueError('invalid deadline')
    latest = None
    for ordinal, decision in enumerate(decisions):
        ready = float(decision['ready_seconds'])
        if not np.isfinite(ready) or ready < 0:
            raise ValueError('invalid decision readiness')
        if ready <= deadline and (latest is None or (ready, ordinal) >= latest[0]):
            latest = (ready, ordinal), decision
    return None if latest is None else latest[1]


def paired_2x2(rows, *, local_key='LOCAL20_correct', global_key='GLOBAL20_correct'):
    """Complete paired correctness table; n01 is GLOBAL-only correct."""
    counts = {'neither_correct':0, 'global_only_correct':0,
              'local_only_correct':0, 'both_correct':0}
    for row in rows:
        local, global_ = bool(row[local_key]), bool(row[global_key])
        key = ('both_correct' if local and global_ else
               'local_only_correct' if local else
               'global_only_correct' if global_ else 'neither_correct')
        counts[key] += 1
    counts['net_global_extra_correct'] = counts['global_only_correct'] - counts['local_only_correct']
    counts['total'] = len(rows)
    return counts


def cost_summary(values):
    x = np.asarray(values, float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError('invalid measured cost sample')
    return dict(count=len(x), mean_seconds=float(np.mean(x)),
                p95_seconds=float(np.percentile(x, 95)), max_seconds=float(np.max(x)))


def observation_hash(observation):
    """Original Part-B observation_hash contract, including dtype and shape."""
    parts = []
    for name in ('y', 'pilot', 'sigma2'):
        value = np.asarray(observation[name])
        digest = hashlib.sha256()
        digest.update(str(value.dtype).encode())
        digest.update(json.dumps(value.shape).encode())
        digest.update(np.ascontiguousarray(value).tobytes())
        parts.append(digest.hexdigest())
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()


def recount(decoded, true_coded, true_info, parity_check, free_cols):
    bits = np.asarray(decoded)
    coded = np.asarray(true_coded)
    info = np.asarray(true_info)
    if (bits.shape != coded.shape or bits.ndim != 1 or not np.isin(bits, (0, 1)).all()
            or not np.isin(coded, (0, 1)).all() or info.shape != (len(free_cols),)):
        raise ValueError('invalid codeword recount inputs')
    bits = bits.astype(np.int32)
    syndrome = int(np.count_nonzero((parity_check.astype(np.int32) @ bits) % 2))
    information_errors = int(np.count_nonzero(bits[free_cols] != info))
    return dict(info_errors=information_errors,
                coded_errors=int(np.count_nonzero(bits != coded)),
                syndrome_weight=syndrome,
                correct=information_errors == 0,
                valid_but_wrong=bool(syndrome == 0 and information_errors > 0))


def check_observed_branch_inputs(raw, rho):
    """Bind branch APP/check inputs to observed native replay, before truth use."""
    from messages import moments

    baseline = raw['baseline_arrays']
    app = np.clip(baseline['r1_app'], -20, 20)
    prior = np.clip(baseline['r1_check'], -20, 20)
    if not np.array_equal(raw['app_input'], app) or not np.array_equal(raw['check_prior'], prior):
        raise ValueError('branch APP/check inputs differ from native replay')
    mu, variance, _ = moments(app, 1-rho)
    if (not np.array_equal(raw['ce_mu'], mu)
            or not np.array_equal(raw['ce_variance'], variance)
            or not np.array_equal(raw['native_round2_detector_mu'], baseline['r1_mu'])
            or not np.array_equal(raw['native_round2_detector_variance'], baseline['r1_variance'])):
        raise ValueError('branch moments differ from native APP/replay state')


def check_checkpoint_bits(original, replay, raw):
    """Require byte-level decoder decisions, not matching error summaries."""
    if (len(original) != 2 or len(replay) != 3
            or not all(np.array_equal(a, b) for a, b in zip(replay[:2], original))
            or not np.array_equal(replay[2], raw['decoder']['decoded'])
            or not np.array_equal(replay[0], raw['baseline_arrays']['r0_decoded'])
            or not np.array_equal(replay[1], raw['baseline_arrays']['r1_decoded'])):
        raise ValueError('native replay, raw decoder, or saved checkpoint bits differ')


def _check_seal_binding(value, binding_path, seal_path):
    """Verify the main-session Git-show receipt against the sealed bytes.

    The remote analysis does not claim to independently possess the Git object.
    """
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('seal commit must be an explicit full Git SHA')
    binding = json.loads(binding_path.read_text())
    content = seal_path.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    committed_path = binding.get('committed_path')
    if (set(binding) != {'git_commit', 'committed_path', 'observed_seal_sha256', 'committed_blob_sha1'}
            or binding['git_commit'] != value
            or not isinstance(committed_path, str) or not committed_path
            or Path(committed_path).is_absolute() or '..' in Path(committed_path).parts
            or binding['observed_seal_sha256'] != hashlib.sha256(content).hexdigest()
            or binding['committed_blob_sha1'] != blob):
        raise ValueError('main-session Git-show seal binding differs from observed bytes')
    return dict(binding_sha256=sha256(binding_path), committed_path=committed_path,
                committed_blob_sha1=blob)


def _bound_observed(observed_root, original_run, source, baseline,
                    a_receipt, qualification, seal_commit, seal_binding):
    """Verify every observed byte and source identity before any truth read."""
    experiments = Path(__file__).resolve().parents[1]
    audit_dir = experiments / 'tf_production_gap_audit_20260922'
    sys.path[:0] = [str(audit_dir), str(Path(__file__).resolve().parent)]
    import audit_io
    import run_reopening

    seal = run_reopening.verify_seal(observed_root)
    seal_hash = sha256(observed_root / 'observed_seal.json')
    binding = _check_seal_binding(seal_commit, seal_binding, observed_root / 'observed_seal.json')
    observed_manifest = json.loads((observed_root / 'manifest.json').read_text())
    original_manifest = json.loads((original_run / 'manifest.json').read_text())
    evidence = audit_io.attach(source, baseline)
    audit_io.verify_sources(original_manifest, source, baseline, evidence)
    original_manifest_hash = sha256(original_run / 'manifest.json')
    receipt = json.loads(a_receipt.read_text())
    qualified = json.loads(qualification.read_text())
    if (observed_manifest.get('schema') != 'tf-geometry-reopen/1'
            or seal.get('schema') != observed_manifest['schema']
            or observed_manifest.get('expected_calls') != 150
            or observed_manifest.get('max_delay') != 102
            or observed_manifest.get('common_config_sha256') != evidence.canonical_hash(observed_manifest.get('common_config'))
            or observed_manifest.get('common_config', {}).get('arm_max_edits') != {'LOCAL20':0, 'GLOBAL20':2}
            or observed_manifest.get('common_config', {}).get('geometry', {}).get('top_k') != 20
            or observed_manifest.get('original_manifest_sha256') != original_manifest_hash
            or observed_manifest.get('original_ledger_sha256') != sha256(original_run / 'ledger.jsonl')
            or observed_manifest.get('original_context_header_sha256') != sha256(original_run / 'context_header.json')
            or observed_manifest.get('a_receipt_sha256') != sha256(a_receipt)
            or observed_manifest.get('qualification_sha256') != sha256(qualification)
            or observed_manifest.get('selection_sha256') != sha256(observed_root / 'selection.json')
            or observed_manifest.get('frozen_source_hashes') != original_manifest['source_hashes']
            or observed_manifest.get('frozen_baseline_hashes') != original_manifest['baseline_source_hashes']
            or receipt.get('status') != 'pass'
            or receipt.get('manifest_sha256') != original_manifest_hash
            or receipt.get('ledger_sha256') != sha256(original_run / 'ledger.jsonl')
            or qualified.get('status') != 'pass'
            or qualified.get('original_manifest_sha256') != original_manifest_hash):
        raise ValueError('observed manifest or original source identity differs')
    for relative, digest in observed_manifest['code_hashes'].items():
        path = experiments / relative
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f'observed numerical code changed: {relative}')
    cache = (baseline / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled'
             / 'e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    if (sha256(cache) != observed_manifest['cache_sha256']
            or sha256(cache) != receipt['ldpc_cache_sha256']):
        raise ValueError('frozen code cache changed')
    with np.load(cache, allow_pickle=False) as saved:
        code = {key:np.asarray(saved[key]).copy() for key in ('H', 'G', 'free_cols')}
    header = json.loads((original_run / 'context_header.json').read_text())
    if (hashlib.sha256(np.ascontiguousarray(code['G']).tobytes()).hexdigest()
            != header['code_g_sha256']):
        raise ValueError('actual code generator differs from original header')
    return audit_io, evidence, code, observed_manifest, seal_hash, original_manifest_hash, binding


def _selected_original(observed_root, original_run, audit_io, evidence, code):
    selection = json.loads((observed_root / 'selection.json').read_text())
    if (not isinstance(selection, list) or len(selection) != 75
            or sum(row['kind'] == 'trigger' for row in selection) != 43
            or sum(row['kind'] == 'control' for row in selection) != 32):
        raise ValueError('sealed selection differs from 43/32')
    ledger = [json.loads(line) for line in (original_run / 'ledger.jsonl').read_text().splitlines()]
    tf = {f"s650_f{row['frame']:04d}":row for row in ledger
          if row['arm'] == 'TF_J20_R2' and row['snr_centi_db'] == 650}
    if len(tf) != 1024:
        raise ValueError('original 6.5 dB TF cell incomplete')
    expected_triggers = {key for key, row in tf.items()
                         if row['checkpoints'][-1]['syndrome_weight'] > 0}
    expected_controls = sorted(key for key, row in tf.items()
                               if row['checkpoints'][-1]['syndrome_weight'] == 0)[:32]
    if len(expected_triggers) != 43 or {s['observation_id'] for s in selection if s['kind']=='trigger'} != expected_triggers:
        raise ValueError('sealed trigger membership differs from original saved syndrome')
    if [s['observation_id'] for s in selection if s['kind']=='control'] != expected_controls:
        raise ValueError('sealed forced-control membership differs')
    out = {}
    for item in selection:
        stem = item['observation_id']
        row = tf[stem]
        if (item['input_sha256'] != row['input_sha256']
                or item['original_checkpoint_sha256'] != [cp['artifact_sha256'] for cp in row['checkpoints']]
                or item['final_syndrome_weight'] != row['checkpoints'][-1]['syndrome_weight']):
            raise ValueError(f'sealed/original record identity differs: {stem}')
        obs = audit_io.load_bound(evidence, original_run / 'frames' / f'{stem}_input.npz', row['input_sha256'])
        truth = audit_io.load_bound(evidence, original_run / 'frames' / f'{stem}_truth.npz', row['frame_sha256'])
        if (truth['input_hash'] != observation_hash(obs)
                or truth['input_hash'] != row['input_hash']):
            raise ValueError(f'original truth/input hash binding differs: {stem}')
        coded, info = audit_io.unpack(truth['coded']), audit_io.unpack(truth['info'])
        if (not np.array_equal(coded[code['free_cols']], info)
                or recount(coded, coded, info, code['H'], code['free_cols'])['syndrome_weight'] != 0):
            raise ValueError(f'original truth code identity differs: {stem}')
        out[stem] = dict(selection=item, record=row, observation=obs,
                         truth=truth, coded=coded, info=info)
    return out


def _old_23(prior_b, original_manifest_hash, triggers):
    receipt = json.loads((prior_b / 'receipt.json').read_text())
    manifest = json.loads((prior_b / 'manifest.json').read_text())
    ledger_path = prior_b / 'ledger.jsonl'
    if (receipt.get('status') != 'pass' or receipt.get('receiver_calls') != 512
            or receipt.get('ledger_sha256') != sha256(ledger_path)
            or receipt.get('files', {}).get('ledger.jsonl') != sha256(ledger_path)
            or manifest.get('original_manifest_sha256') != original_manifest_hash):
        raise ValueError('prior B evidence identity differs')
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    by_key = {(row['observation_id'], row['arm']):row for row in rows}
    if len(rows) != 512 or len(by_key) != 512:
        raise ValueError('prior B attempt allocation differs')
    selected = {row['observation_id'] for row in rows if row['arm'] == 'baseline_replay'
                and row['baseline_error']}
    old = {stem for stem in selected
           if by_key[(stem, 'J40R2')]['info_errors'] > 0
           and by_key[(stem, 'J20R3')]['info_errors'] > 0}
    if len(old) != 23 or not old <= triggers:
        raise ValueError('prior B missed-both witness set differs from declared 23')
    return old, sha256(ledger_path)


def _check_trace(trace):
    ranks = rank_score_grid(trace['scores'], trace['valid'],
                            trace['candidate_delays'], trace['candidate_dopplers'])
    top = trace['top_k']
    expected = min(20, int(np.count_nonzero(trace['valid'])))
    if len(top) != expected or [entry['rank'] for entry in top] != list(range(1, expected+1)):
        raise ValueError('global top20 trace count differs from full score grid')
    for entry in top:
        slot = int(entry['slot'])
        replacement = entry['replacement']
        indices = np.flatnonzero((np.asarray(trace['candidate_delays']) == replacement['delay'])
                                 & (np.asarray(trace['candidate_dopplers']) == replacement['doppler']))
        if (len(indices) != 1 or ranks[slot, indices[0]] != entry['rank']
                or not np.isclose(trace['scores'][slot, indices[0]], entry['frozen_score'], rtol=0, atol=1e-10)):
            raise ValueError('stored top20 is inconsistent with complete global grid')
    return ranks


def global_trace_tables(observation_id, kind, trace):
    """Flatten a sealed full-grid step and its retained top20 for review CSVs."""
    _check_trace(trace)
    entering = trace['entering_paths']
    gains = np.asarray(trace['entering_gains'], complex)
    if gains.shape != (len(entering),) or not np.isfinite(gains).all():
        raise ValueError('global entering geometry/gains differ')
    accepted, selected = trace['accepted'], trace['selected']
    step = dict(observation_id=observation_id, kind=kind,
        global_step=int(trace['step']), entering_paths=entering,
        entering_gains_real=gains.real.tolist(), entering_gains_imag=gains.imag.tolist(),
        entering_objective=float(trace['entering_objective']),
        best_candidate=selected, accepted_replacement=accepted,
        after_global_objective=float(accepted['direct_score'] if accepted is not None
                                     else trace['entering_objective']),
        candidate_columns=int(trace['candidate_columns']),
        slot_tests=int(trace['slot_tests']),
        valid_slot_tests=int(trace['valid_slot_tests']),
        duplicate_rejections=int(trace['duplicate_rejections']),
        elapsed_seconds=float(trace['elapsed_seconds']))
    top = [dict(observation_id=observation_id, kind=kind,
                global_step=int(trace['step']), rank=int(item['rank']),
                slot=int(item['slot']), replacement_delay=int(item['replacement']['delay']),
                replacement_doppler=float(item['replacement']['doppler']),
                full_candidate_geometry=item['paths'],
                frozen_score=float(item['frozen_score'])) for item in trace['top_k']]
    return step, top


def _channel(n, c1, c2, paths, gains):
    from physical import Channel
    return Channel(n, c1, c2, [p['delay'] for p in paths],
                   [p['doppler'] for p in paths], gains)


def _artifact(evidence, root, path, digest):
    if sha256(root / path) != digest:
        raise ValueError(f'sealed artifact hash differs: {path}')
    return evidence.load_artifact(root / path)[0]


def analyze(observed_root, seal_commit, seal_binding, original_run, source, baseline,
            a_receipt, qualification, prior_b, out):
    observed_root, original_run, source, baseline = map(Path, (observed_root, original_run, source, baseline))
    seal_binding, a_receipt, qualification, prior_b, out = map(Path, (seal_binding, a_receipt, qualification, prior_b, out))
    if out.exists():
        raise FileExistsError('offline analysis output already exists')
    audit_io, evidence, code, observed_manifest, seal_hash, original_manifest_hash, binding = _bound_observed(
        observed_root, original_run, source, baseline, a_receipt, qualification, seal_commit, seal_binding)
    selected = _selected_original(observed_root, original_run, audit_io, evidence, code)
    triggers = {stem for stem, item in selected.items() if item['selection']['kind'] == 'trigger'}
    old23, old_b_hash = _old_23(prior_b, original_manifest_hash, triggers)
    audit_dir = Path(__file__).resolve().parents[1] / 'tf_production_gap_audit_20260922'
    sys.path.insert(0, str(audit_dir))
    import metrics
    if observed_manifest.get('arms') != list(ARMS):
        raise ValueError('sealed arm set differs')
    pd = .5
    moments = metrics.exact_code_moments(code['G'], pd)
    header = json.loads((original_run / 'context_header.json').read_text())
    c1, c2 = float(header['system']['c1']), float(header['system']['c2'])
    n = int(header['system']['n_total'])
    rho = float(header['system']['rho'])
    ledger = [json.loads(line) for line in (observed_root / 'ledger.jsonl').read_text().splitlines()]
    by_key = {(row['observation_id'], row['arm']):row for row in ledger}
    if len(by_key) != 150 or set(by_key) != {(stem, arm) for stem in selected for arm in ARMS}:
        raise ValueError('sealed ledger key set differs')
    arm_rows, rank_rows, mismatch_rows = [], [], []
    global_steps, global_top20 = [], []
    for stem, item in selected.items():
        truth, obs = item['truth'], item['observation']
        true_channel = _channel(n, c1, c2,
            [dict(delay=int(l), doppler=float(k)) for l, k in zip(truth['l_i'], truth['k_real'])],
            truth['g_i'])
        original_checkpoints = []
        original_decoded = []
        for cp in item['record']['checkpoints']:
            payload = _artifact(evidence, original_run, cp['path'], cp['artifact_sha256'])
            original_decoded.append(audit_io.unpack(payload['decoded']))
            original_checkpoints.append(dict(round=int(cp['round']), ready_seconds=float(cp['ready']),
                **recount(original_decoded[-1], item['coded'], item['info'],
                          code['H'], code['free_cols'])))
        if (original_checkpoints[-1]['syndrome_weight'] != item['selection']['final_syndrome_weight']
                or original_checkpoints[-1]['correct'] != (item['selection']['kind'] == 'control')):
            raise ValueError('original selection/truth recount differs')
        for arm in ARMS:
            row = by_key[(stem, arm)]
            if (row['status'] != 'ok' or row['kind'] != item['selection']['kind']
                    or row['input_sha256'] != item['record']['input_sha256']
                    or len(row['checkpoints']) != 3):
                raise ValueError(f'sealed call identity/status differs: {stem}/{arm}')
            raw = _artifact(evidence, observed_root, row['raw_path'], row['raw_sha256'])
            if raw['observation_id'] != stem or raw['arm'] != arm:
                raise ValueError('sealed raw arm identity differs')
            check_observed_branch_inputs(raw, rho)
            checkpoint_results = []
            checkpoint_decoded = []
            for cp in row['checkpoints']:
                payload = _artifact(evidence, observed_root, cp['path'], cp['artifact_sha256'])
                decoded = np.asarray(payload['decoded'])
                checkpoint_decoded.append(decoded)
                count = recount(decoded, item['coded'], item['info'], code['H'], code['free_cols'])
                if count['syndrome_weight'] != cp['syndrome_weight']:
                    raise ValueError('sealed checkpoint syndrome differs from raw bits')
                checkpoint_results.append(dict(round=int(cp['round']),
                    ready_seconds=float(cp['decision_ready_seconds']), **count))
            if [cp['round'] for cp in checkpoint_results] != [0, 1, 2]:
                raise ValueError('sealed checkpoint round sequence differs')
            check_checkpoint_bits(original_decoded, checkpoint_decoded, raw)
            final = checkpoint_results[-1]
            arm_record = dict(observation_id=stem, kind=item['selection']['kind'], arm=arm,
                original_final_correct=original_checkpoints[-1]['correct'],
                original_final_info_errors=original_checkpoints[-1]['info_errors'],
                original_final_syndrome_weight=original_checkpoints[-1]['syndrome_weight'],
                original_round_ready_seconds=[cp['ready_seconds'] for cp in original_checkpoints],
                replay_round_ready_seconds=[cp['ready_seconds'] for cp in checkpoint_results[:2]],
                third_ready_seconds=final['ready_seconds'],
                final_info_errors=final['info_errors'], final_coded_errors=final['coded_errors'],
                final_syndrome_weight=final['syndrome_weight'], final_correct=final['correct'],
                final_valid_but_wrong=final['valid_but_wrong'],
                rescue=bool(not original_checkpoints[-1]['correct'] and final['correct']),
                harm=bool(original_checkpoints[-1]['correct'] and not final['correct']),
                forced_control_harm=bool(item['selection']['kind']=='control'
                                         and original_checkpoints[-1]['correct'] and not final['correct']),
                old23_member=stem in old23,
                branch_decision_seconds=float(row['branch_seconds']),
                added_complete_branch_seconds=float(row['added_complete_branch_seconds']),
                setup_seconds=float(row['setup_seconds']),
                wrapper_seconds=float(row['wrapper_seconds']),
                replay_ready_seconds=float(row['replay_ready_seconds']))
            if (not all(np.isfinite(arm_record[name]) and arm_record[name] >= 0
                        for name in ('branch_decision_seconds', 'added_complete_branch_seconds',
                                     'setup_seconds', 'wrapper_seconds', 'replay_ready_seconds'))
                    or arm_record['added_complete_branch_seconds'] < arm_record['branch_decision_seconds']
                    or arm_record['wrapper_seconds'] < arm_record['added_complete_branch_seconds']
                    or not np.isclose(arm_record['added_complete_branch_seconds'],
                        float(row['raw_artifact_ready_seconds'])-arm_record['replay_ready_seconds'],
                        rtol=0, atol=1e-7)):
                raise ValueError('sealed branch timing is inconsistent')
            for deadline in DEADLINES:
                latest = latest_available(checkpoint_results, deadline)
                historical = latest_available(original_checkpoints, deadline)
                suffix = '0500ms' if deadline == .5 else '1000ms'
                arm_record[f'wrapper_{suffix}_available_round'] = None if latest is None else latest['round']
                arm_record[f'wrapper_{suffix}_correct'] = None if latest is None else latest['correct']
                arm_record[f'wrapper_{suffix}_info_errors'] = None if latest is None else latest['info_errors']
                arm_record[f'wrapper_{suffix}_ready_seconds'] = None if latest is None else latest['ready_seconds']
                arm_record[f'historical_{suffix}_available_round'] = None if historical is None else historical['round']
                arm_record[f'historical_{suffix}_correct'] = None if historical is None else historical['correct']
                arm_record[f'historical_{suffix}_info_errors'] = None if historical is None else historical['info_errors']
            arm_rows.append(arm_record)
            geom = raw['geometry_result']
            if arm == 'GLOBAL20':
                for step in geom['global_trace']:
                    step_row, top_rows = global_trace_tables(stem, item['selection']['kind'], step)
                    global_steps.append(step_row)
                    global_top20.extend(top_rows)
                    ranks = truth_rank_rows(step['scores'], step['valid'],
                        step['candidate_delays'], step['candidate_dopplers'],
                        truth['l_i'], truth['k_real'], truth['g_i'],
                        observation_id=stem, global_step=step['step'])
                    rank_rows.extend(add_geometry_proximity(ranks, step['entering_paths'],
                        step['accepted'], grid_step=observed_manifest['common_config']['geometry']['grid_step']))
            elif geom['global_trace']:
                raise ValueError('LOCAL20 unexpectedly searched global geometry')
            path_sets = (
                ('starting_inference', raw['initial_paths'], raw['initial_inference_gains']),
                ('reopened_geometry', geom['paths'], geom['gains']),
                ('final_native', geom['paths'], raw['detector']['gains']))
            for stage, paths, gains in path_sets:
                fit = _channel(n, c1, c2, paths, gains)
                mismatch = metrics.operator_mismatch(fit, true_channel, obs['pilot'],
                    data_covariance=moments['covariance'], data_mean=moments['mean'])
                mismatch_rows.append(dict(observation_id=stem, kind=item['selection']['kind'],
                    arm=arm, stage=stage,
                    operator_frobenius_squared=mismatch['operator_frobenius_squared'],
                    sp_weighted_mismatch=mismatch['sp_weighted_mismatch'],
                    pilot_mismatch=mismatch['pilot_mismatch'],
                    data_mismatch=mismatch['data_mismatch']))
    by_arm = {(row['observation_id'], row['arm']):row for row in arm_rows}
    paired = []
    for stem, item in selected.items():
        local, global_ = (by_arm[(stem, arm)] for arm in ARMS)
        paired.append(dict(observation_id=stem, kind=item['selection']['kind'],
            original_correct=local['original_final_correct'],
            LOCAL20_correct=local['final_correct'], GLOBAL20_correct=global_['final_correct'],
            LOCAL20_valid_but_wrong=local['final_valid_but_wrong'],
            GLOBAL20_valid_but_wrong=global_['final_valid_but_wrong'],
            old23_member=stem in old23))
    triggered = [row for row in paired if row['kind']=='trigger']
    controls = [row for row in paired if row['kind']=='control']
    table = paired_2x2(triggered)
    global_old_rescues = sum(row['old23_member'] and row['GLOBAL20_correct'] for row in triggered)
    triggered_costs = {arm:dict(added_complete_branch=cost_summary([r['added_complete_branch_seconds'] for r in arm_rows
                                                   if r['arm']==arm and r['kind']=='trigger']),
                                branch_decision=cost_summary([r['branch_decision_seconds'] for r in arm_rows
                                                   if r['arm']==arm and r['kind']=='trigger']),
                                wrapper=cost_summary([r['wrapper_seconds'] for r in arm_rows
                                                    if r['arm']==arm and r['kind']=='trigger'])) for arm in ARMS}
    deadlines = {}
    for arm in ARMS:
        deadlines[arm] = {}
        for deadline, suffix in ((.5, '0500ms'), (1., '1000ms')):
            rows = [r for r in arm_rows if r['arm']==arm and r['kind']=='trigger']
            ready = [r for r in rows if r[f'wrapper_{suffix}_available_round'] is not None]
            historical = [r for r in rows if r[f'historical_{suffix}_available_round'] is not None]
            deadlines[arm][suffix] = dict(deadline_seconds=deadline,
                new_wrapper_ready_count=len(ready), new_wrapper_correct_count=sum(
                    r[f'wrapper_{suffix}_correct'] for r in ready),
                new_wrapper_error_count=len(ready)-sum(r[f'wrapper_{suffix}_correct'] for r in ready),
                new_wrapper_unready_count=len(rows)-len(ready),
                historical_original_ready_count=len(historical),
                historical_original_correct_count=sum(r[f'historical_{suffix}_correct'] for r in historical),
                historical_original_unready_count=len(rows)-len(historical))
    gate = dict(net_extra_correct_at_least5=table['net_global_extra_correct'] >= 5,
                old23_rescues_at_least5=global_old_rescues >= 5,
                mean_global_added_complete_branch_at_most_0p6s=triggered_costs['GLOBAL20']['added_complete_branch']['mean_seconds'] <= .6)
    summary = dict(scope='75 previously examined 6.5dB observations; diagnostic/development only',
        triggered_count=43, forced_control_count=32, paired_2x2=table,
        global_step_count=len(global_steps), retained_top20_rows=len(global_top20),
        arm_vs_original={arm:dict(rescues=sum(r['rescue'] for r in arm_rows if r['arm']==arm and r['kind']=='trigger'),
                                  harms=sum(r['harm'] for r in arm_rows if r['arm']==arm and r['kind']=='trigger'))
                         for arm in ARMS},
        old23_count=len(old23), global_old23_rescues=global_old_rescues,
        forced_control_harms={arm:dict(count=sum(r['forced_control_harm'] for r in arm_rows if r['arm']==arm),
            valid_but_wrong_ids=[r['observation_id'] for r in arm_rows if r['arm']==arm and r['kind']=='control'
                                 and r['final_valid_but_wrong'] and not r['original_final_info_errors']])
            for arm in ARMS},
        triggered_costs=triggered_costs, triggered_deadlines=deadlines, gates=gate,
        selected_source='saved baseline syndrome only; truth read after observed seal verification',
        no_population_confirmation=True)
    out.mkdir(parents=True)
    audit_io.write_csv(out / 'arm_outcomes.csv', arm_rows)
    audit_io.write_csv(out / 'paired_outcomes.csv', paired)
    audit_io.write_csv(out / 'truth_grid_ranks.csv', rank_rows)
    audit_io.write_csv(out / 'global_steps.csv', global_steps)
    audit_io.write_csv(out / 'global_top20.csv', global_top20)
    audit_io.write_csv(out / 'channel_mismatch.csv', mismatch_rows)
    audit_io.write_json(out / 'summary.json', summary)
    audit_io.write_json(out / 'receipt.json', dict(status='pass', observed_seal_sha256=seal_hash,
        seal_commit=seal_commit, seal_binding_sha256=binding['binding_sha256'],
        seal_committed_path=binding['committed_path'],
        seal_committed_blob_sha1=binding['committed_blob_sha1'],
        seal_binding_scope='main-session Git-show receipt; remote analysis checks binding and bytes, not Git object presence',
        observed_manifest_sha256=sha256(observed_root / 'manifest.json'),
        original_manifest_sha256=original_manifest_hash, prior_b_ledger_sha256=old_b_hash,
        analysis_source_sha256=sha256(Path(__file__)),
        metrics_source_sha256=sha256(audit_dir / 'metrics.py'),
        exact_code_covariance_offdiagonal_count=moments['covariance_offdiagonal_count'],
        files={p.name:sha256(p) for p in out.iterdir() if p.is_file()}))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observed-root', required=True, type=Path)
    parser.add_argument('--seal-commit', required=True)
    parser.add_argument('--seal-binding', required=True, type=Path)
    parser.add_argument('--original-run', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--a-receipt', required=True, type=Path)
    parser.add_argument('--qualification', required=True, type=Path)
    parser.add_argument('--prior-b', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    analyze(args.observed_root, args.seal_commit, args.seal_binding, args.original_run,
            args.source, args.baseline, args.a_receipt, args.qualification,
            args.prior_b, args.out)


if __name__ == '__main__':
    main()
