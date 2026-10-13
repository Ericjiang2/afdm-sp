"""Read-only prospective TF/CSTATE analysis after the observed Git seal.

All source/config/seal and Git-object checks run before a truth artifact is
opened. Scientific non-passage is a completed result; broken evidence is an
integrity failure with no primary pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.sparse import csr_matrix


HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
AUDIT = EXPERIMENTS/'tf_production_gap_audit_20260922'
sys.path[:0] = [str(AUDIT), str(HERE)]
import audit_io  # noqa: E402
import paired_statistics as stats  # noqa: E402

CELLS = (600, 650, 700)
ARMS = ('TF', 'TF_CSTATE')
FRAMES_PER_CELL = 1024
DEADLINE = .5
STAGES = ('message_handling','y_transform','geometry_setup',
          'structural_field_build','structural_scoring',
          'structural_selection_trace','structural_refit_refresh',
          'structural_fallback_direct','local_refinement',
          'geometry_finalization','geometry_wrapper_overhead',
          'wrapper_validation','channel_construction','tf','ldpc',
          'checkpoint_write','raw_serialization_hash')


def distribution(values):
    """All observed times, including zero work, without dropping failures."""
    x = np.asarray(values, float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError('invalid complete latency sample')
    return dict(count=int(len(x)), mean_seconds=float(x.mean()),
                median_seconds=float(np.median(x)),
                p90_seconds=float(np.percentile(x, 90)),
                p95_seconds=float(np.percentile(x, 95)),
                max_seconds=float(x.max()))


def paired_latency(tf_seconds, combined_seconds):
    tf, combined = np.asarray(tf_seconds, float), np.asarray(combined_seconds, float)
    if (tf.ndim != 1 or tf.shape != combined.shape or not len(tf)
            or not np.isfinite(tf).all() or not np.isfinite(combined).all()
            or np.any(tf <= 0) or np.any(combined <= 0)):
        raise ValueError('invalid paired complete latency sample')
    delta = combined-tf
    ratio = combined/tf
    return dict(tf=distribution(tf), combined=distribution(combined),
                paired_delta_seconds=distribution_signed(delta),
                paired_ratio=distribution_ratio(ratio),
                ratio_of_means=float(combined.mean()/tf.mean()))


def _summary(x):
    return dict(count=int(len(x)), mean=float(x.mean()), median=float(np.median(x)),
                p90=float(np.percentile(x, 90)), p95=float(np.percentile(x, 95)),
                minimum=float(x.min()), maximum=float(x.max()))


def distribution_signed(values):
    x = np.asarray(values, float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
        raise ValueError('invalid signed latency sample')
    result = _summary(x)
    return {key+'_seconds' if key not in ('count',) else key:value
            for key, value in result.items()}


def distribution_ratio(values):
    x = np.asarray(values, float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.any(x <= 0):
        raise ValueError('invalid paired ratio sample')
    return _summary(x)


def latest_ready(checkpoints, deadline=DEADLINE):
    """A later late decision cannot erase an already ready checkpoint."""
    if not np.isfinite(deadline) or deadline < 0:
        raise ValueError('invalid deadline')
    eligible = [(float(cp['decision_ready_seconds']), index, cp)
                for index, cp in enumerate(checkpoints)
                if float(cp['decision_ready_seconds']) <= deadline]
    if any(not np.isfinite(float(cp['decision_ready_seconds'])) or
           float(cp['decision_ready_seconds']) < 0 for cp in checkpoints):
        raise ValueError('invalid checkpoint decision readiness')
    return None if not eligible else max(eligible)[2]


def paired_counts(rows, tf_key, combined_key):
    """Complete paired correctness table; unready deadline counts wrong."""
    result = dict(both_correct=0, tf_only_correct=0,
                  combined_only_correct=0, neither_correct=0)
    for row in rows:
        tf, combined = row[tf_key], row[combined_key]
        if type(tf) is not bool or type(combined) is not bool:
            raise ValueError('paired correctness must be explicit booleans')
        key = ('both_correct' if tf and combined else
               'tf_only_correct' if tf else
               'combined_only_correct' if combined else 'neither_correct')
        result[key] += 1
    return result


def recount(decoded, truth_info, truth_coded, H, free_cols):
    bits = np.asarray(decoded)
    info, coded = np.asarray(truth_info), np.asarray(truth_coded)
    if (bits.ndim != 1 or bits.shape != coded.shape or
            info.shape != (len(free_cols),) or
            not np.isin(bits, (0, 1)).all() or
            not np.isin(info, (0, 1)).all() or
            not np.isin(coded, (0, 1)).all()):
        raise ValueError('invalid saved codeword or truth bit shape')
    bits = bits.astype(np.int32)
    return dict(info_errors=int(np.count_nonzero(bits[free_cols] != info)),
                coded_errors=int(np.count_nonzero(bits != coded)),
                syndrome_weight=int(np.count_nonzero((H @ bits) % 2)))


def error_flags(counted):
    """Keep codeword, information-word and syndrome distinctions explicit."""
    info, coded, syndrome = (counted[name] for name in
                              ('info_errors', 'coded_errors', 'syndrome_weight'))
    if min(info, coded, syndrome) < 0:
        raise ValueError('negative recount error count')
    return dict(undetected=bool(syndrome == 0 and info > 0),
                syndrome_zero_coded_wrong=bool(syndrome == 0 and coded > 0),
                info_correct_coded_wrong=bool(info == 0 and coded > 0))


def _git_committed_seal(evidence_git, commit, observed_seal, relative_path):
    """Verify the actual independent Git object, not an asserted receipt."""
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('seal commit must be a full lowercase Git SHA')
    relative = Path(relative_path)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('invalid registered observed seal repository path')
    completed = subprocess.run(['git', '-C', str(evidence_git), 'show',
                                f'{commit}:{relative.as_posix()}'],
                               capture_output=True, check=False)
    if completed.returncode:
        raise ValueError('independent evidence Git object is unavailable')
    actual = observed_seal.read_bytes()
    if completed.stdout != actual:
        raise ValueError('committed observed seal bytes differ from actual seal')
    meta = subprocess.run(['git', '-C', str(evidence_git), 'show', '-s',
                           '--format=%H%n%cI', commit], capture_output=True,
                          check=False, text=True)
    if meta.returncode:
        raise ValueError('independent evidence Git commit metadata unavailable')
    lines = meta.stdout.strip().splitlines()
    if len(lines) != 2 or lines[0] != commit or not lines[1]:
        raise ValueError('independent evidence Git commit metadata differs')
    return dict(commit=commit, committed_path=relative.as_posix(),
                committed_at=lines[1],
                seal_sha256=hashlib.sha256(actual).hexdigest(),
                committed_blob_sha1=hashlib.sha1(
                    b'blob '+str(len(actual)).encode()+b'\0'+actual).hexdigest())


def _git_blob(evidence_git, commit, relative_path):
    result = subprocess.run(['git', '-C', str(evidence_git), 'show',
                             f'{commit}:{relative_path}'],
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f'independent Git object unavailable: {relative_path}')
    return result.stdout


def _git_committed_truth_seal(evidence_git, seal_commit, truth_root):
    """Bind the truth inventory to the same immutable observed-seal commit."""
    committed = _git_blob(evidence_git, seal_commit, 'population_truth_seal.json')
    disk = (truth_root/'truth_seal.json').read_bytes()
    if committed != disk:
        raise ValueError('committed population truth seal bytes differ from disk')
    return hashlib.sha256(committed).hexdigest()


def _git_time(evidence_git, commit):
    result = subprocess.run(['git', '-C', str(evidence_git), 'show', '-s',
                             '--format=%H%n%ct', commit], capture_output=True,
                            check=False, text=True)
    fields = result.stdout.strip().splitlines()
    if result.returncode or len(fields) != 2 or fields[0] != commit or not fields[1].isdigit():
        raise ValueError('independent Git commit time unavailable')
    return int(fields[1])


def _git_registration(evidence_git, prereg_commit, seal_commit, registration,
                      population_created_epoch, receiver_created_epoch):
    """Require registration bytes in an ancestral commit before generation."""
    if any(not isinstance(value, str) or len(value) != 40 or
           any(c not in '0123456789abcdef' for c in value)
           for value in (prereg_commit, seal_commit)):
        raise ValueError('registered Git commit identity is invalid')
    relation = subprocess.run(['git', '-C', str(evidence_git), 'merge-base',
                               '--is-ancestor', prereg_commit, seal_commit],
                              capture_output=True, check=False)
    if relation.returncode:
        raise ValueError('seal commit is not descended from preregistration')
    registered_files = {'registration.json':registration,
                        'PROTOCOL.md':registration.parent/'PROTOCOL.md',
                        'random_namespace.json':registration.parent/'random_namespace.json',
                        'local_git_binding.json':registration.parent/'local_git_binding.json'}
    for name, local in registered_files.items():
        actual = local.read_bytes()
        path = f'registration/{name}'
        if (_git_blob(evidence_git, prereg_commit, path) != actual or
                _git_blob(evidence_git, seal_commit, path) != actual):
            raise ValueError(f'preregistered Git blob differs: {name}')
    before = _git_time(evidence_git, prereg_commit)
    after = _git_time(evidence_git, seal_commit)
    if (before > population_created_epoch or before > receiver_created_epoch
            or after < receiver_created_epoch or after < before):
        raise ValueError('independent Git commit times violate preregistered order')
    return dict(preregistration_commit=prereg_commit,
                preregistration_commit_epoch=before,
                seal_commit_epoch=after)


def _read_ledger(path, expected_keys, key_fields):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    keys = [tuple(row[field] for field in key_fields) for row in rows]
    if len(rows) != len(expected_keys) or keys != expected_keys or len(set(keys)) != len(keys):
        raise ValueError(f'fixed ledger allocation/order differs: {path}')
    return rows


def _truth_inventory(root, observed_seal_hash, registration_hash):
    """Truth bytes remain unopened until all observed/Git checks have passed."""
    seal = json.loads((root/'truth_seal.json').read_text())
    actual = {str(path.relative_to(root)):audit_io.sha256(path)
              for path in root.rglob('*') if path.is_file() and path.name != 'truth_seal.json'}
    if (seal.get('schema') != 'tf-cstate-prospective/1' or seal.get('status') != 'pass'
            or seal.get('observations') != 3072
            or seal.get('registration_sha256') != registration_hash
            or seal.get('observed_seal_sha256') != observed_seal_hash
            or seal.get('files') != actual):
        raise ValueError('prospective truth inventory or observed binding differs')
    expected = [(snr, frame) for snr in CELLS for frame in range(FRAMES_PER_CELL)]
    rows = _read_ledger(root/'ledger.jsonl', expected, ('snr_centi_db', 'frame'))
    for row in rows:
        if actual.get(row['truth_path']) != row['truth_sha256']:
            raise ValueError('prospective truth artifact ledger hash differs')
    return rows, audit_io.sha256(root/'truth_seal.json')


def _code_cache(baseline, registration):
    cache = (baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled'
             /'e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    if audit_io.sha256(cache) != registration['ldpc_cache_sha256']:
        raise ValueError('prospective frozen LDPC cache differs')
    with np.load(cache, allow_pickle=False) as archive:
        code = {name:np.asarray(archive[name]).copy() for name in ('H', 'G', 'free_cols')}
    if (code['H'].shape != (1026, 2048) or code['G'].shape != (2048, 1024)
            or code['free_cols'].shape != (1024,)
            or hashlib.sha256(np.ascontiguousarray(code['G']).tobytes()).hexdigest()
               != registration['code_g_sha256']):
        raise ValueError('prospective actual H/G/free-code identity differs')
    code['H'] = csr_matrix(code['H'].astype(np.int32))
    return code


def summarize_cell(rows, *, primary=False):
    """One complete 1024-pair cell; only 6.5 dB may be primary."""
    if len(rows) != FRAMES_PER_CELL:
        raise ValueError('prospective cell is not the complete 1024 pairs')
    table = paired_counts(rows, 'tf_correct', 'combined_correct')
    inference = stats.paired_statistics(n=FRAMES_PER_CELL,
        **table, integrity_valid=True)
    deadline_table = paired_counts(rows, 'tf_deadline_correct',
                                   'combined_deadline_correct')
    timing = {}
    for name, subset in (('all', rows),
                         ('trigger', [r for r in rows if r['trigger']]),
                         ('nontrigger', [r for r in rows if not r['trigger']])):
        timing[name] = (dict(count=0, latency=None) if not subset else
                        dict(count=len(subset), latency=paired_latency(
                            [r['tf_latency_seconds'] for r in subset],
                            [r['combined_latency_seconds'] for r in subset])))
    return dict(n=FRAMES_PER_CELL, primary_cell=primary,
        paired_table=table, paired_inference=inference if primary else None,
        descriptive_delta_hat=inference['delta_hat'],
        descriptive_tf_fer=inference['frozen_tf_fer'],
        descriptive_combined_fer=inference['combined_fer'],
        trigger_count=sum(r['trigger'] for r in rows),
        trigger_fraction=sum(r['trigger'] for r in rows)/FRAMES_PER_CELL,
        rescue_count=sum(r['trigger'] and not r['tf_correct'] and r['combined_correct']
                         for r in rows),
        harm_count=sum(r['tf_correct'] and not r['combined_correct'] for r in rows),
        remaining_triggered_failure_count=sum(
            r['trigger'] and not r['combined_correct'] for r in rows),
        both_wrong_count=sum(not r['tf_correct'] and not r['combined_correct']
                             for r in rows),
        undetected_tf_count=sum(r['tf_undetected'] for r in rows),
        undetected_combined_count=sum(r['combined_undetected'] for r in rows),
        syndrome_zero_coded_wrong_tf_count=sum(
            r['tf_syndrome_zero_coded_wrong'] for r in rows),
        syndrome_zero_coded_wrong_combined_count=sum(
            r['combined_syndrome_zero_coded_wrong'] for r in rows),
        info_correct_coded_wrong_tf_count=sum(
            r['tf_info_correct_coded_wrong'] for r in rows),
        info_correct_coded_wrong_combined_count=sum(
            r['combined_info_correct_coded_wrong'] for r in rows),
        coded_frame_errors_tf=sum(r['tf_coded_errors'] > 0 for r in rows),
        coded_frame_errors_combined=sum(r['combined_coded_errors'] > 0 for r in rows),
        info_bit_errors_tf=sum(r['tf_info_errors'] for r in rows),
        info_bit_errors_combined=sum(r['combined_info_errors'] for r in rows),
        info_ber_tf=sum(r['tf_info_errors'] for r in rows)/(FRAMES_PER_CELL*1024),
        info_ber_combined=sum(r['combined_info_errors'] for r in rows)/(FRAMES_PER_CELL*1024),
        coded_bit_errors_tf=sum(r['tf_coded_errors'] for r in rows),
        coded_bit_errors_combined=sum(r['combined_coded_errors'] for r in rows),
        coded_ber_tf=sum(r['tf_coded_errors'] for r in rows)/(FRAMES_PER_CELL*2048),
        coded_ber_combined=sum(r['combined_coded_errors'] for r in rows)/
                           (FRAMES_PER_CELL*2048),
        deadline_0p5=dict(table=deadline_table,
            tf_system_failure_count=sum(not r['tf_deadline_correct'] for r in rows),
            combined_system_failure_count=sum(not r['combined_deadline_correct'] for r in rows),
            tf_missing_count=sum(r['tf_deadline_missing'] for r in rows),
            combined_missing_count=sum(r['combined_deadline_missing'] for r in rows),
            tf_ready_decoded_error_count=sum(r['tf_deadline_ready_wrong'] for r in rows),
            combined_ready_decoded_error_count=sum(r['combined_deadline_ready_wrong'] for r in rows)),
        latency=timing,
        compact_fallback_count=sum(r['combined_fallback'] for r in rows))


def stage_summary(rows):
    """Seventeen exclusive CSTATE stages, including zero-work nontriggers."""
    result = {}
    for name, subset in (('all', rows),
                         ('trigger', [r for r in rows if r['trigger']]),
                         ('nontrigger', [r for r in rows if not r['trigger']])):
        if not subset:
            result[name] = dict(count=0, stages=None)
            continue
        stages = {}
        for stage in STAGES:
            values = [r['combined_stages'][stage] for r in subset]
            times = distribution(values)
            total = sum(r['combined_added_branch_seconds'] for r in subset)
            stages[stage] = dict(**times,
                share_of_complete_branch=float(sum(values)/total) if total else None)
        result[name] = dict(count=len(subset), stages=stages)
    return result


def _bound(args):
    """Finish all observed/source/Git checks before reading any truth payload."""
    import generate_population as generator
    import run_prospective as runner

    evidence = audit_io.attach(args.source, args.baseline)
    registration = generator.validate_registration(args.registration,
        args.source, args.baseline, evidence)
    population_seal = generator.verify_population_seal(args.population_observed)
    receiver_seal = runner.verify_observed_seal(args.observed)
    registration_sha = audit_io.sha256(args.registration)
    population_hash = audit_io.sha256(args.population_observed/'observed_seal.json')
    observed_hash = audit_io.sha256(args.observed/'observed_seal.json')
    population_manifest = json.loads((args.population_observed/'manifest.json').read_text())
    receiver_manifest = json.loads((args.observed/'manifest.json').read_text())
    if (population_manifest.get('schema') != generator.SCHEMA
            or population_manifest.get('kind') != 'observed'
            or population_manifest.get('registration_sha256') != registration_sha
            or population_manifest.get('protocol_sha256') != registration['protocol_sha256']
            or population_manifest.get('source_hashes') != registration['registration_source_hashes']
            or population_seal.get('registration_sha256') != registration_sha
            or receiver_manifest.get('schema') != generator.SCHEMA
            or receiver_manifest.get('kind') != 'receiver_observed'
            or receiver_manifest.get('registration_sha256') != registration_sha
            or receiver_manifest.get('registration_commit') != population_manifest.get('registration_commit')
            or receiver_manifest.get('population_observed_seal_sha256') != population_hash
            or receiver_manifest.get('population_manifest_sha256') !=
               audit_io.sha256(args.population_observed/'manifest.json')
            or receiver_manifest.get('population_ledger_sha256') !=
               audit_io.sha256(args.population_observed/'ledger.jsonl')
            or receiver_manifest.get('protocol_sha256') != registration['protocol_sha256']
            or receiver_manifest.get('source_hashes') != registration['registration_source_hashes']
            or receiver_manifest.get('source_hashes_sha256') !=
               evidence.canonical_hash(registration['registration_source_hashes'])
            or receiver_manifest.get('receiver_config') != runner.FROZEN_CONFIG
            or receiver_manifest.get('receiver_config_sha256') !=
               evidence.canonical_hash(runner.FROZEN_CONFIG)
            or receiver_manifest.get('expected_calls') != 6144
            or receiver_manifest.get('expected_observations') != 3072
            or receiver_seal.get('registration_sha256') != registration_sha
            or receiver_seal.get('population_observed_seal_sha256') != population_hash
            or receiver_seal.get('receiver_calls') != 6144):
        raise ValueError('prospective observed source/config/seal binding differs')
    if tuple(receiver_manifest.get('arms', ())) != ARMS:
        raise ValueError('prospective arm identity differs')
    git_seal = _git_committed_seal(args.evidence_git, args.seal_commit,
        args.observed/'observed_seal.json', 'observed/observed_seal.json')
    git_registration = _git_registration(args.evidence_git,
        population_manifest['registration_commit'], args.seal_commit,
        args.registration, population_manifest['created_epoch'],
        receiver_manifest['created_epoch'])
    local_binding = json.loads((args.registration.parent/'local_git_binding.json').read_text())
    registered_bytes = args.registration.read_bytes()
    registered_blob = hashlib.sha1(b'blob '+str(len(registered_bytes)).encode()+
                                   b'\0'+registered_bytes).hexdigest()
    if (set(local_binding) != {'git_commit','committed_path','registration_sha256',
                              'committed_blob_sha1','verification'}
            or local_binding['verification'] !=
               'actual local git show byte equality and git rev-parse object identity'
            or local_binding['registration_sha256'] != registration_sha
            or local_binding['committed_blob_sha1'] != registered_blob
            or not isinstance(local_binding['git_commit'], str)
            or len(local_binding['git_commit']) != 40
            or any(c not in '0123456789abcdef' for c in local_binding['git_commit'])
            or not isinstance(local_binding['committed_path'], str)
            or not local_binding['committed_path']
            or Path(local_binding['committed_path']).is_absolute()
            or '..' in Path(local_binding['committed_path']).parts):
        raise ValueError('local preregistration Git-show receipt differs')
    code = _code_cache(args.baseline, registration)
    expected_observations = [(snr, frame) for snr in CELLS
                             for frame in range(FRAMES_PER_CELL)]
    population_rows = _read_ledger(args.population_observed/'ledger.jsonl',
        expected_observations, ('snr_centi_db', 'frame'))
    receiver_rows = _read_ledger(args.observed/'ledger.jsonl',
        [(row['observation_id'], arm) for row, arm in
         runner.arm_schedule(population_rows)], ('observation_id', 'arm'))
    paired_rows = _read_ledger(args.observed/'paired_audit.jsonl',
        [(row['observation_id'],) for row in population_rows], ('observation_id',))
    if any(not row.get('native_decoded_identical') for row in paired_rows):
        raise ValueError('prospective paired native evidence differs')
    # First truth-root access: the inventory must equal the committed Git blob
    # before any truth payload or ledger is opened.
    committed_truth_seal_hash = _git_committed_truth_seal(
        args.evidence_git, args.seal_commit, args.truth_root)
    truth_rows, truth_seal_hash = _truth_inventory(args.truth_root,
        population_hash, registration_sha)
    truth_manifest = json.loads((args.truth_root/'manifest.json').read_text())
    if (truth_manifest.get('kind') != 'truth'
            or truth_manifest.get('registration_sha256') != registration_sha
            or truth_manifest.get('registration_commit') !=
               population_manifest['registration_commit']
            or truth_manifest.get('observed_manifest_sha256') !=
               audit_io.sha256(args.population_observed/'manifest.json')):
        raise ValueError('prospective truth manifest differs from committed observed population')
    return dict(evidence=evidence, registration=registration, code=code,
        population_rows=population_rows, receiver_rows=receiver_rows,
        truth_rows=truth_rows, git_seal=git_seal,
        git_registration=git_registration, local_binding=local_binding,
        population_seal_sha256=population_hash,
        receiver_seal_sha256=observed_hash,
        truth_seal_sha256=truth_seal_hash,
        committed_truth_seal_sha256=committed_truth_seal_hash,
        registration_sha256=registration_sha,
        receiver_manifest=receiver_manifest)


def _check_timing(row):
    values = [row[name] for name in (
        'input_load_seconds','before_native_bookkeeping_seconds',
        'native_two_rounds_seconds','native_checkpoint_write_seconds',
        'before_trigger_bookkeeping_seconds','trigger_seconds',
        'before_branch_bookkeeping_seconds','post_trigger_output_seconds',
        'branch_decision_seconds','branch_complete_seconds',
        'raw_serialization_hash_seconds',
        'before_decision_record_bookkeeping_seconds',
        'decision_record_write_seconds','complete_latency_seconds')]
    if any(not np.isfinite(value) or value < 0 for value in values):
        raise ValueError('prospective receiver timing is negative or nonfinite')
    stage = row['branch_exclusive_stages']
    if set(stage) != set(STAGES) or any(not np.isfinite(value) or value < 0
                                       for value in stage.values()):
        raise ValueError('prospective 17-stage inventory differs')
    if row['triggered']:
        if row['branch_decision_seconds'] > row['branch_complete_seconds']:
            raise ValueError('prospective branch decision clock exceeds complete branch')
        if not np.isclose(sum(stage.values()), row['branch_complete_seconds'],
                          rtol=0, atol=1e-7):
            raise ValueError('prospective triggered branch clock differs')
    elif row['branch_complete_seconds'] != 0 or any(stage.values()):
        raise ValueError('prospective nontrigger performed a registered branch')
    total = sum(row[name] for name in (
        'input_load_seconds','before_native_bookkeeping_seconds',
        'native_two_rounds_seconds','before_trigger_bookkeeping_seconds',
        'trigger_seconds','before_branch_bookkeeping_seconds',
        'post_trigger_output_seconds',
        'before_decision_record_bookkeeping_seconds',
        'decision_record_write_seconds'))
    if not np.isclose(total, row['complete_latency_seconds'], rtol=0, atol=1e-7):
        raise ValueError('prospective complete receiver timing does not reconcile')
    if any(row['checkpoints'][i]['decision_ready_seconds'] >
           row['checkpoints'][i]['artifact_ready_seconds'] for i in range(len(row['checkpoints']))):
        raise ValueError('prospective checkpoint artifact preceded decision')
    if (row['ledger_append_included_in_latency'] is not False
            or row['final_decision_ready_seconds'] > row['complete_latency_seconds']):
        raise ValueError('prospective decision/ledger timing scope differs')


def _arm_recount(args, bound, population, truth, row):
    evidence, code = bound['evidence'], bound['code']
    stem = population['observation_id']
    arm = row['arm']
    if (row['status'] != 'ok' or not row['receiver_started']
            or row['observation_id'] != stem
            or row['snr_centi_db'] != population['snr_centi_db']
            or row['frame'] != population['frame']
            or row['input_sha256'] != population['observation_sha256']
            or row['observation_hash'] != population['observation_hash']
            or row['stream_ids'] != population['stream_ids']
            or row['source_hashes_sha256'] !=
               bound['receiver_manifest']['source_hashes_sha256']
            or row['receiver_config_sha256'] !=
               bound['receiver_manifest']['receiver_config_sha256']):
        raise ValueError(f'prospective receiver row identity differs: {stem}/{arm}')
    _check_timing(row)
    raw = audit_io.load_bound(evidence, args.observed/row['raw_path'], row['raw_sha256'])
    decision = json.loads((args.observed/row['decision_record_path']).read_text())
    if audit_io.sha256(args.observed/row['decision_record_path']) != row['decision_record_sha256']:
        raise ValueError('prospective decision record artifact hash differs')
    if (raw['observation_id'] != stem or raw['arm'] != arm
            or raw['input_sha256'] != population['observation_sha256']
            or raw['stream_ids'] != population['stream_ids']
            or raw['triggered'] != row['triggered']
            or raw['baseline_syndrome_weight'] != row['baseline_syndrome_weight']
            or decision['observation_id'] != stem or decision['arm'] != arm
            or decision['input_sha256'] != population['observation_sha256']
            or decision['stream_ids'] != population['stream_ids']
            or decision['checkpoints'] != row['checkpoints']
            or decision['raw_path'] != row['raw_path']
            or decision['raw_sha256'] != row['raw_sha256']
            or decision['branch_exclusive_stages'] != row['branch_exclusive_stages']):
        raise ValueError('prospective raw/decision identity differs')
    coded = np.asarray(truth['coded'], np.uint8)
    info = np.asarray(truth['info'], np.uint8)
    cp_results, bits = [], []
    if len(row['checkpoints']) not in (2, 3):
        raise ValueError('prospective checkpoint count differs')
    for index, cp in enumerate(row['checkpoints']):
        payload = audit_io.load_bound(evidence, args.observed/cp['path'],
                                      cp['artifact_sha256'])
        decoded = np.asarray(payload['decoded'])
        if decoded.dtype != np.uint8 or decoded.shape != (2048,):
            raise ValueError('prospective saved decoder vector shape/dtype differs')
        counted = recount(decoded, info, coded, code['H'], code['free_cols'])
        if (cp['round'] != index or counted['syndrome_weight'] != cp['syndrome_weight']
                or not np.array_equal(payload['event']['snapshot']['decoded'], decoded)
                or {key:value for key,value in payload['event'].items()
                    if key != 'snapshot'} != cp['event']):
            raise ValueError('prospective checkpoint bits/syndrome differ')
        bits.append(decoded)
        cp_results.append(dict(round=index,
            decision_ready_seconds=float(cp['decision_ready_seconds']), **counted))
    if (not np.array_equal(bits[0], raw['baseline_arrays']['r0_decoded'])
            or not np.array_equal(bits[1], raw['baseline_arrays']['r1_decoded'])
            or not np.array_equal(bits[1], raw['native_decoder']['decoded'])
            or not np.array_equal(bits[-1], raw['final_decoded'])):
        raise ValueError('prospective raw/native/checkpoint decoded bits differ')
    expected_trigger = arm == 'TF_CSTATE' and cp_results[1]['syndrome_weight'] != 0
    if row['triggered'] != expected_trigger or len(row['checkpoints']) != (3 if expected_trigger else 2):
        raise ValueError('prospective observed-only trigger differs')
    if expected_trigger:
        if (raw['geometry_result'] is None or raw['branch_inputs'] is None
                or raw['branch_detector'] is None or raw['branch_decoder'] is None
                or not np.array_equal(raw['branch_decoder']['decoded'], bits[-1])):
            raise ValueError('prospective triggered branch evidence differs')
        from messages import moments
        app = np.clip(raw['baseline_arrays']['r1_app'], -20, 20)
        check = np.clip(raw['baseline_arrays']['r1_check'], -20, 20)
        mu, variance, _ = moments(app, .5)
        if (not np.array_equal(raw['branch_inputs']['app_input'], app)
                or not np.array_equal(raw['branch_inputs']['check_prior'], check)
                or not np.array_equal(raw['branch_inputs']['ce_mu'], mu)
                or not np.array_equal(raw['branch_inputs']['ce_variance'], variance)):
            raise ValueError('prospective branch APP/check inputs differ from native state')
    elif (raw['geometry_result'] is not None or raw['branch_inputs'] is not None
          or raw['branch_detector'] is not None or raw['branch_decoder'] is not None):
        raise ValueError('prospective nontrigger contains branch evidence')
    final = cp_results[-1]
    final_hash = hashlib.sha256(np.ascontiguousarray(bits[-1]).tobytes()).hexdigest()
    if (final_hash != row['final_decoded_sha256']
            or final_hash != decision['final_decoded_sha256']
            or final['syndrome_weight'] != row['final_syndrome_weight']
            or final['syndrome_weight'] != decision['final_syndrome_weight']
            or row['baseline_syndrome_weight'] != cp_results[1]['syndrome_weight']
            or decision['baseline_syndrome_weight'] != cp_results[1]['syndrome_weight']
            or row['final_decision_ready_seconds'] !=
               row['checkpoints'][-1]['decision_ready_seconds']
            or decision['final_decision_ready_seconds'] !=
               row['final_decision_ready_seconds']):
        raise ValueError('prospective final decision/ledger recount differs')
    ready = latest_ready(cp_results)
    fallback = (bool(raw['geometry_result']['diagnostics']['numerical_fallback'])
                if expected_trigger else False)
    final_flags = error_flags(final)
    record = dict(observation_id=stem, snr_centi_db=population['snr_centi_db'],
        frame=population['frame'], arm=arm,
        triggered=bool(row['triggered']),
        baseline_syndrome_weight=cp_results[1]['syndrome_weight'],
        final_info_errors=final['info_errors'],
        final_coded_errors=final['coded_errors'],
        final_syndrome_weight=final['syndrome_weight'],
        final_correct=bool(final['info_errors']==0),
        final_undetected=final_flags['undetected'],
        syndrome_zero_coded_wrong=final_flags['syndrome_zero_coded_wrong'],
        info_correct_coded_wrong=final_flags['info_correct_coded_wrong'],
        complete_latency_seconds=float(row['complete_latency_seconds']),
        final_decision_ready_seconds=float(row['final_decision_ready_seconds']),
        deadline_missing=ready is None,
        deadline_ready_round=None if ready is None else int(ready['round']),
        deadline_ready_wrong=bool(ready is not None and ready['info_errors']>0),
        deadline_correct=bool(ready is not None and ready['info_errors']==0),
        deadline_system_failure=bool(ready is None or ready['info_errors']>0),
        numerical_fallback=fallback,
        branch_complete_seconds=float(row['branch_complete_seconds']),
        branch_decision_seconds=float(row['branch_decision_seconds']),
        branch_exclusive_stages=row['branch_exclusive_stages'],
        checkpoint_info_errors=[item['info_errors'] for item in cp_results],
        checkpoint_coded_errors=[item['coded_errors'] for item in cp_results],
        checkpoint_syndrome_weights=[item['syndrome_weight'] for item in cp_results])
    return record, bits[:2]


def _report(summary, stage_costs):
    primary = summary['cells']['650']['paired_inference']
    lines = [
        '# Prospective frozen TF versus TF+CSTATE', '',
        'Independent new observations; 1,024 complete pairs per SNR. '
        'Only 6.5 dB is the preregistered primary confirmation cell.', '',
        f"Evidence integrity: **{summary['evidence_integrity']}**. "
        f"Primary decision: **{primary['primary_status']}**.", '',
        '| SNR (dB) | TF info FER [95% CP] | TF+CSTATE info FER [95% CP] | '
        'h (TF only correct) | r (CSTATE only correct) | Δ̂ combined−TF |',
        '|---:|---:|---:|---:|---:|---:|']
    for snr in CELLS:
        cell = summary['cells'][str(snr)]
        table = cell['paired_table']
        lines.append(f"| {snr/100:g} | "
            f"{cell['descriptive_tf_fer']['estimate']:.6f} "
            f"[{cell['descriptive_tf_fer']['lower_95']:.6f}, "
            f"{cell['descriptive_tf_fer']['upper_95']:.6f}] | "
            f"{cell['descriptive_combined_fer']['estimate']:.6f} "
            f"[{cell['descriptive_combined_fer']['lower_95']:.6f}, "
            f"{cell['descriptive_combined_fer']['upper_95']:.6f}] | "
            f"{table['tf_only_correct']} | {table['combined_only_correct']} | "
            f"{cell['descriptive_delta_hat']:.6f} |")
    lines += ['',
        'At 6.5 dB the complete paired 2×2 table is '
        f"both correct={primary['table']['both_correct']}, "
        f"TF only correct={primary['table']['tf_only_correct']}, "
        f"TF+CSTATE only correct={primary['table']['combined_only_correct']}, "
        f"neither correct={primary['table']['neither_correct']}.",
        f"The conservative one-sided 95% upper bound for Δ is "
        f"{primary['primary_upper_95']:.8f}; the frozen gate requires it to be "
        'strictly below zero and integrity valid.',
        f"The auxiliary exact conditional McNemar one-sided p-value is "
        f"{primary['auxiliary_exact_conditional_mcnemar_one_sided_p']:.8g}; "
        'it does not replace the primary bound.', '',
        '| SNR (dB) | Triggered (fraction) | Rescued | Harmed | Remaining triggered failures | '
        'Both wrong (all frames) | '
        'Undetected TF / combined | 0.5 s system failures TF / combined | '
        'Missing TF / combined | Compact fallbacks |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for snr in CELLS:
        cell = summary['cells'][str(snr)]
        deadline = cell['deadline_0p5']
        lines.append(f"| {snr/100:g} | {cell['trigger_count']} "
            f"({cell['trigger_fraction']:.4f}) | "
            f"{cell['rescue_count']} | {cell['harm_count']} | "
            f"{cell['remaining_triggered_failure_count']} | "
            f"{cell['both_wrong_count']} | "
            f"{cell['undetected_tf_count']} / {cell['undetected_combined_count']} | "
            f"{deadline['tf_system_failure_count']} / "
            f"{deadline['combined_system_failure_count']} | "
            f"{deadline['tf_missing_count']} / {deadline['combined_missing_count']} | "
            f"{cell['compact_fallback_count']} |")
    lines += ['',
        '| SNR (dB) | 0.5 s both correct | TF only correct | '
        'Combined only correct | Neither correct | Ready decoded errors TF / combined |',
        '|---:|---:|---:|---:|---:|---:|']
    for snr in CELLS:
        deadline = summary['cells'][str(snr)]['deadline_0p5']
        table = deadline['table']
        lines.append(f"| {snr/100:g} | {table['both_correct']} | "
            f"{table['tf_only_correct']} | {table['combined_only_correct']} | "
            f"{table['neither_correct']} | "
            f"{deadline['tf_ready_decoded_error_count']} / "
            f"{deadline['combined_ready_decoded_error_count']} |")
    lines += ['',
        '| SNR (dB) | Zero syndrome but coded word wrong TF / combined | '
        'Information word correct but other coded bits wrong TF / combined |',
        '|---:|---:|---:|']
    for snr in CELLS:
        cell = summary['cells'][str(snr)]
        lines.append(f"| {snr/100:g} | "
            f"{cell['syndrome_zero_coded_wrong_tf_count']} / "
            f"{cell['syndrome_zero_coded_wrong_combined_count']} | "
            f"{cell['info_correct_coded_wrong_tf_count']} / "
            f"{cell['info_correct_coded_wrong_combined_count']} |")
    lines += ['',
        '| SNR (dB) | TF info bit errors / BER | Combined info bit errors / BER | '
        'TF coded bit errors / BER | Combined coded bit errors / BER |',
        '|---:|---:|---:|---:|---:|']
    for snr in CELLS:
        cell = summary['cells'][str(snr)]
        lines.append(f"| {snr/100:g} | {cell['info_bit_errors_tf']} / "
            f"{cell['info_ber_tf']:.8f} | {cell['info_bit_errors_combined']} / "
            f"{cell['info_ber_combined']:.8f} | {cell['coded_bit_errors_tf']} / "
            f"{cell['coded_ber_tf']:.8f} | {cell['coded_bit_errors_combined']} / "
            f"{cell['coded_ber_combined']:.8f} |")
    lines += ['',
        'A missing or unready 0.5 s decision is a system deadline failure on the '
        'full 1,024-pair denominator, not a fabricated bit error. Ready-only decoded '
        'error counts and checkpoint identities are in summary.json and CSV.', '',
        'Complete receiver latency includes input load, native replay, trigger, '
        'conditional CSTATE, raw serialization, and durable decision write. '
        'The final ledger append and paired audit are outside the receiver clock.', '',
        '| SNR (dB) | Cohort | TF mean / p95 (s) | Combined mean / p95 (s) | '
        'Paired Δ mean / p95 (s) | Mean paired ratio | Ratio of means |',
        '|---:|---|---:|---:|---:|---:|---:|']
    for snr in CELLS:
        for cohort in ('all','trigger','nontrigger'):
            item = summary['cells'][str(snr)]['latency'][cohort]
            if item['latency'] is None:
                lines.append(f'| {snr/100:g} | {cohort} (n=0) | — | — | — | — | — |')
                continue
            latency = item['latency']
            tf, combined = latency['tf'], latency['combined']
            delta = latency['paired_delta_seconds']
            lines.append(f"| {snr/100:g} | {cohort} (n={item['count']}) | "
                f"{tf['mean_seconds']:.4f} / {tf['p95_seconds']:.4f} | "
                f"{combined['mean_seconds']:.4f} / {combined['p95_seconds']:.4f} | "
                f"{delta['mean_seconds']:.4f} / {delta['p95_seconds']:.4f} | "
                f"{latency['paired_ratio']['mean']:.4f} | "
                f"{latency['ratio_of_means']:.4f} |")
    lines += ['',
        'Full complete-receiver latency distributions follow. Each five-number '
        'cell is mean / median / p90 / p95 / maximum. Paired Δ is combined minus '
        'TF; paired ratio is combined divided by TF.', '',
        '| SNR (dB) | Cohort | Quantity | Mean / median / p90 / p95 / max |',
        '|---:|---|---|---:|']
    for snr in CELLS:
        for cohort in ('all', 'trigger', 'nontrigger'):
            group = summary['cells'][str(snr)]['latency'][cohort]
            if group['latency'] is None:
                continue
            latency = group['latency']
            for label, item, keys in (
                    ('TF seconds', latency['tf'],
                     ('mean_seconds','median_seconds','p90_seconds',
                      'p95_seconds','max_seconds')),
                    ('Combined seconds', latency['combined'],
                     ('mean_seconds','median_seconds','p90_seconds',
                      'p95_seconds','max_seconds')),
                    ('Paired Δ seconds', latency['paired_delta_seconds'],
                     ('mean_seconds','median_seconds','p90_seconds',
                      'p95_seconds','maximum_seconds')),
                    ('Paired ratio', latency['paired_ratio'],
                     ('mean','median','p90','p95','maximum'))):
                values = [item[key] for key in keys]
                lines.append(f"| {snr/100:g} | {cohort} (n={group['count']}) | "
                    f"{label} | {' / '.join(f'{x:.4f}' for x in values)} |")
    lines += ['',
        'The 17 exclusive CSTATE stages are below. Each stage includes zero '
        'work for nontriggered frames; stage share divides by total complete '
        'branch time within the stated cohort.', '',
        '| SNR (dB) | Cohort | Stage | Mean (s) | Median (s) | p90 (s) | '
        'p95 (s) | Max (s) | Share |',
        '|---:|---|---|---:|---:|---:|---:|---:|---:|']
    for snr in CELLS:
        for cohort in ('all', 'trigger', 'nontrigger'):
            group = stage_costs[str(snr)][cohort]
            if group['stages'] is None:
                continue
            for stage in STAGES:
                item = group['stages'][stage]
                share = item['share_of_complete_branch']
                lines.append(f"| {snr/100:g} | {cohort} (n={group['count']}) | "
                    f"{stage} | {item['mean_seconds']:.6f} | "
                    f"{item['median_seconds']:.6f} | {item['p90_seconds']:.6f} | "
                    f"{item['p95_seconds']:.6f} | {item['max_seconds']:.6f} | "
                    f"{'—' if share is None else f'{share:.4f}'} |")
    lines += ['', 'Per-frame stage values are in stage_times.csv; all 3,072 pairs '
        'and 6,144 arm decisions are preserved in frame_outcomes.csv and '
        'arm_outcomes.csv.', '',
        f"Observed seal Git commit: `{summary['git_seal']['commit']}` "
        f"({summary['git_seal']['committed_at']}).",
        f"Observed seal SHA256: `{summary['git_seal']['seal_sha256']}`. "
        'The committed observed and truth seal bytes and preregistration blobs '
        'were checked with Git in the independent evidence repository before '
        'truth payloads were read.', '',
        f"Committed truth seal SHA256: `{summary['committed_truth_seal_sha256']}`.", '',
        'The 6 and 7 dB comparisons, codeword errors, syndromes, undetected '
        'decisions, 0.5 s outcomes, and timing are descriptive. No further '
        'parameter search or population claim is inferred from them.', '']
    return '\n'.join(lines)


def analyze(args):
    for name in ('registration','population_observed','truth_root','observed',
                 'source','baseline','evidence_git','out'):
        setattr(args, name, getattr(args, name).resolve())
    if args.out.exists():
        raise FileExistsError('prospective analysis output already exists')
    for protected in (args.population_observed, args.truth_root, args.observed,
                      args.source, args.baseline, args.evidence_git):
        if args.out == protected or protected in args.out.parents:
            raise ValueError('analysis output would alter a protected input tree')
    args.out.mkdir(parents=True)
    stage = 'observed_and_git_integrity'
    try:
        bound = _bound(args)
        stage = 'truth_recount'
        import generate_population as generator

        evidence, code = bound['evidence'], bound['code']
        population = bound['population_rows']
        truth_rows = bound['truth_rows']
        receiver = {(row['observation_id'],row['arm']):row
                    for row in bound['receiver_rows']}
        arm_rows, frame_rows, stage_rows = [], [], []
        for pop, saved_truth in zip(population, truth_rows):
            stem = pop['observation_id']
            if (saved_truth['observation_id'] != stem
                    or saved_truth['observation_hash'] != pop['observation_hash']
                    or saved_truth['stream_ids'] != pop['stream_ids']):
                raise ValueError(f'prospective truth/observation ledger binding differs: {stem}')
            observed_payload = audit_io.load_bound(evidence,
                args.population_observed/pop['observation_path'], pop['observation_sha256'])
            if (observed_payload['observation_id'] != stem
                    or observed_payload['stream_ids'] != pop['stream_ids']
                    or observed_payload['observation_hash'] != pop['observation_hash']
                    or generator.observation_hash(observed_payload['observation']) !=
                       pop['observation_hash']):
                raise ValueError(f'prospective observed input hash differs: {stem}')
            truth = audit_io.load_bound(evidence,
                args.truth_root/saved_truth['truth_path'], saved_truth['truth_sha256'])
            if (truth['observation_hash'] != pop['observation_hash']
                    or truth['stream_ids'] != pop['stream_ids']):
                raise ValueError(f'prospective truth payload identity differs: {stem}')
            coded = np.asarray(truth['coded'])
            info = np.asarray(truth['info'])
            if (coded.dtype != np.uint8 or info.dtype != np.uint8
                    or coded.shape != (2048,) or info.shape != (1024,)
                    or recount(coded, info, coded, code['H'],
                               code['free_cols']) !=
                       dict(info_errors=0, coded_errors=0, syndrome_weight=0)):
                raise ValueError(f'prospective truth code identity differs: {stem}')
            per_arm = {}
            native = {}
            for arm in ARMS:
                record, native_bits = _arm_recount(args, bound, pop,
                    truth, receiver[(stem,arm)])
                arm_rows.append(record)
                per_arm[arm] = record
                native[arm] = native_bits
            if any(not np.array_equal(a, b) for a,b in
                   zip(native['TF'], native['TF_CSTATE'])):
                raise ValueError(f'prospective paired native decoded state differs: {stem}')
            tf, combined = per_arm['TF'], per_arm['TF_CSTATE']
            if tf['baseline_syndrome_weight'] != combined['baseline_syndrome_weight']:
                raise ValueError(f'prospective paired observed trigger differs: {stem}')
            trigger = combined['baseline_syndrome_weight'] != 0
            frame = dict(observation_id=stem, snr_centi_db=pop['snr_centi_db'],
                frame=pop['frame'], trigger=trigger,
                baseline_syndrome_weight=combined['baseline_syndrome_weight'],
                tf_correct=tf['final_correct'],
                combined_correct=combined['final_correct'],
                tf_info_errors=tf['final_info_errors'],
                combined_info_errors=combined['final_info_errors'],
                tf_coded_errors=tf['final_coded_errors'],
                combined_coded_errors=combined['final_coded_errors'],
                tf_final_syndrome_weight=tf['final_syndrome_weight'],
                combined_final_syndrome_weight=combined['final_syndrome_weight'],
                tf_undetected=tf['final_undetected'],
                combined_undetected=combined['final_undetected'],
                tf_syndrome_zero_coded_wrong=tf['syndrome_zero_coded_wrong'],
                combined_syndrome_zero_coded_wrong=combined['syndrome_zero_coded_wrong'],
                tf_info_correct_coded_wrong=tf['info_correct_coded_wrong'],
                combined_info_correct_coded_wrong=combined['info_correct_coded_wrong'],
                rescue=bool(trigger and not tf['final_correct'] and combined['final_correct']),
                harm=bool(tf['final_correct'] and not combined['final_correct']),
                remaining_triggered_failure=bool(
                    trigger and not combined['final_correct']),
                both_wrong=bool(not tf['final_correct'] and not combined['final_correct']),
                tf_latency_seconds=tf['complete_latency_seconds'],
                combined_latency_seconds=combined['complete_latency_seconds'],
                paired_latency_delta_seconds=combined['complete_latency_seconds']-
                    tf['complete_latency_seconds'],
                paired_latency_ratio=combined['complete_latency_seconds']/
                    tf['complete_latency_seconds'],
                tf_deadline_correct=tf['deadline_correct'],
                combined_deadline_correct=combined['deadline_correct'],
                tf_deadline_missing=tf['deadline_missing'],
                combined_deadline_missing=combined['deadline_missing'],
                tf_deadline_ready_wrong=tf['deadline_ready_wrong'],
                combined_deadline_ready_wrong=combined['deadline_ready_wrong'],
                tf_deadline_ready_round=tf['deadline_ready_round'],
                combined_deadline_ready_round=combined['deadline_ready_round'],
                combined_fallback=combined['numerical_fallback'],
                combined_added_branch_seconds=combined['branch_complete_seconds'],
                combined_stages=combined['branch_exclusive_stages'])
            frame_rows.append(frame)
            stage_rows.append(dict(observation_id=stem,
                snr_centi_db=pop['snr_centi_db'], trigger=trigger,
                complete_branch_seconds=combined['branch_complete_seconds'],
                **{stage:combined['branch_exclusive_stages'][stage] for stage in STAGES}))
        if len(arm_rows) != 6144 or len(frame_rows) != 3072:
            raise ValueError('prospective complete recount allocation differs')
        cells = {str(snr):summarize_cell([r for r in frame_rows
                            if r['snr_centi_db']==snr], primary=snr==650)
                 for snr in CELLS}
        stage_costs = {str(snr):stage_summary([r for r in frame_rows
                                             if r['snr_centi_db']==snr])
                       for snr in CELLS}
        summary = dict(status='complete', evidence_integrity='pass',
            scope='independent prospective 1024 paired frames each at 6, 6.5, 7 dB; 6.5 dB sole primary',
            cells=cells, git_seal=bound['git_seal'],
            git_registration=bound['git_registration'],
            local_registration_binding=dict(
                scope='main-session local Git-show receipt; independently checked registration bytes in remote evidence Git',
                registration_sha256=bound['local_binding']['registration_sha256'],
                local_git_commit=bound['local_binding']['git_commit']),
            observed_seal_sha256=bound['receiver_seal_sha256'],
            population_observed_seal_sha256=bound['population_seal_sha256'],
            truth_seal_sha256=bound['truth_seal_sha256'],
            committed_truth_seal_sha256=bound['committed_truth_seal_sha256'],
            receiver_calls_recounted=6144, observations_recounted=3072,
            checkpoints_recounted=sum(3 if r['triggered'] else 2 for r in arm_rows),
            primary_pass=cells['650']['paired_inference']['primary_pass'])
        audit_io.write_csv(args.out/'arm_outcomes.csv', arm_rows)
        audit_io.write_csv(args.out/'frame_outcomes.csv', frame_rows)
        audit_io.write_csv(args.out/'stage_times.csv', stage_rows)
        audit_io.write_json(args.out/'stage_summary.json', stage_costs)
        audit_io.write_json(args.out/'summary.json', summary)
        (args.out/'RESULTS.md').write_text(_report(summary, stage_costs))
        audit_io.write_json(args.out/'receipt.json', dict(status='complete',
            evidence_integrity='pass', primary_pass=summary['primary_pass'],
            observed_seal_sha256=bound['receiver_seal_sha256'],
            seal_commit=args.seal_commit,
            preregistration_commit=bound['git_registration']['preregistration_commit'],
            registration_sha256=bound['registration_sha256'],
            truth_seal_sha256=bound['truth_seal_sha256'],
            committed_truth_seal_sha256=bound['committed_truth_seal_sha256'],
            analysis_source_sha256=audit_io.sha256(Path(__file__)),
            statistics_source_sha256=audit_io.sha256(HERE/'paired_statistics.py'),
            files={p.name:audit_io.sha256(p) for p in args.out.iterdir() if p.is_file()}))
        return summary
    except BaseException as error:
        audit_io.write_json(args.out/'integrity_failure.json', dict(
            status='fail', evidence_integrity='fail', primary_pass=False,
            failed_stage=stage, exception_type=type(error).__name__, reason=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence-git','registration','population-observed','truth-root',
                 'observed','source','baseline','out'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--seal-commit', required=True)
    result = analyze(parser.parse_args())
    primary = result['cells']['650']['paired_inference']
    print(json.dumps(dict(status=result['status'], integrity=result['evidence_integrity'],
                          primary_pass=primary['primary_pass'],
                          primary_upper_95=primary['primary_upper_95'])))


if __name__ == '__main__':
    main()
