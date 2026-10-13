"""Independent, read-only recount of one sealed prospective receiver campaign.

This module loads saved artifacts and truth only after verifying the actual
observed-seal Git object. It never imports a receiver, geometry optimizer, or
the primary statistical implementation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.optimize import brentq
from scipy.stats import binom


HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(EXPERIMENTS / 'tf_production_gap_audit_20260922'))
from audit_io import attach, sha256  # noqa: E402


CELLS = (600, 650, 700)
FRAMES = 1024
ARMS = ('TF', 'TF_CSTATE')
SCHEMA = 'tf-cstate-prospective/1'
STAGES = ('message_handling', 'y_transform', 'geometry_setup',
          'structural_field_build', 'structural_scoring',
          'structural_selection_trace', 'structural_refit_refresh',
          'structural_fallback_direct', 'local_refinement',
          'geometry_finalization', 'geometry_wrapper_overhead',
          'wrapper_validation', 'channel_construction', 'tf', 'ldpc',
          'checkpoint_write', 'raw_serialization_hash')
DEADLINE = .5


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text())


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def relative(root, name):
    candidate = Path(name)
    require(not candidate.is_absolute() and candidate.parts and
            '..' not in candidate.parts, f'unsafe artifact path: {name}')
    result = (root / candidate).resolve()
    require(result.is_relative_to(root.resolve()), f'artifact escapes root: {name}')
    return result


def git_bytes(repo, commit, path):
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit),
            'Git commit must be a full lowercase SHA')
    result = subprocess.run(['git', '-C', str(repo), 'show', f'{commit}:{path}'],
                            capture_output=True, check=False)
    require(result.returncode == 0, f'missing registered Git object: {path}')
    return result.stdout


def pretruth_gate(args):
    """Complete source, allocation and actual Git seal checks before truth I/O."""
    registration = read_json(args.registration)
    require(registration.get('schema') == SCHEMA and
            registration.get('status') == 'locked', 'registration not locked')
    manifest = read_json(args.observed / 'manifest.json')
    population = read_json(args.population_observed / 'manifest.json')
    prereg = manifest.get('registration_commit')
    require(prereg == args.registration_commit,
            'receiver registration commit differs from declared Git commit')
    require(prereg == population.get('registration_commit'),
            'population and receiver registration commits differ')
    require(manifest.get('registration_sha256') ==
            population.get('registration_sha256') == sha256(args.registration),
            'registration hash differs')
    require(manifest.get('protocol_sha256') ==
            population.get('protocol_sha256') == registration['protocol_sha256'],
            'protocol hash differs')
    for filename, registered_hash in (
            ('PROTOCOL.md', registration['protocol_sha256']),
            ('random_namespace.json', registration['random_namespace_sha256'])):
        require(sha256(args.registration.parent / filename) == registered_hash,
                f'registered {filename} hash differs')
    namespace = read_json(args.registration.parent / 'random_namespace.json')
    require(registration.get('cells') ==
            [{'snr_centi_db': snr, 'frames': FRAMES} for snr in CELLS] and
            registration.get('streams', {}).get('entropy_hex') ==
            namespace.get('entropy_hex') and
            registration.get('streams', {}).get('algorithm') ==
            'numpy.SeedSequence(8 entropy uint32 words, CSTA domain, snr_centi_db, frame, component)',
            'prospective allocation or random-stream rule differs')
    for name in ('registration.json', 'PROTOCOL.md', 'random_namespace.json',
                 'local_git_binding.json'):
        local = args.registration.parent / name
        expected = local.read_bytes()
        require(git_bytes(args.evidence_git, prereg, f'registration/{name}') == expected,
                f'preregistered Git bytes differ: {name}')
        require(git_bytes(args.evidence_git, args.seal_commit,
                          f'registration/{name}') == expected,
                f'seal commit changed registration: {name}')
    relation = subprocess.run(['git', '-C', str(args.evidence_git), 'merge-base',
                               '--is-ancestor', prereg, args.seal_commit],
                              capture_output=True, check=False)
    require(relation.returncode == 0, 'seal commit does not descend from registration')
    for name, digest in registration['registration_source_hashes'].items():
        require(sha256(relative(EXPERIMENTS, name)) == digest,
                f'registered source changed: {name}')
    evidence = attach(args.source, args.baseline)
    require(evidence.source_hashes(args.source) ==
            registration['native_source_hashes'] and
            evidence.source_hashes(args.baseline) ==
            registration['baseline_source_hashes'],
            'frozen native/baseline source hash inventory differs')
    require(registration['original_manifest_sha256'] ==
            'de69da6d945cd56f84eb69cc5df814088885c9d28b9375015599c99abefab7d9',
            'original TF study identity differs')
    require(manifest.get('source_hashes') ==
            population.get('source_hashes') ==
            registration['registration_source_hashes'], 'source manifest differs')
    require(manifest.get('receiver_config') == registration['receiver_config'] and
            manifest.get('receiver_config_sha256') ==
            evidence.canonical_hash(registration['receiver_config']) and
            manifest.get('source_hashes_sha256') ==
            evidence.canonical_hash(registration['registration_source_hashes']),
            'receiver configuration/source manifest hash differs')
    observed_seal_path = args.observed / 'observed_seal.json'
    seal_bytes = observed_seal_path.read_bytes()
    require(git_bytes(args.evidence_git, args.seal_commit,
                      'observed/observed_seal.json') == seal_bytes,
            'actual Git observed seal differs')
    seal_hash = hashlib.sha256(seal_bytes).hexdigest()
    require(git_bytes(args.evidence_git, args.seal_commit,
                      'population_truth_seal.json') ==
            (args.truth_root / 'truth_seal.json').read_bytes(),
            'committed truth inventory bytes differ')
    require(manifest.get('schema') == population.get('schema') == SCHEMA,
            'prospective manifest schema differs')
    require(manifest.get('population_observed_seal_sha256') ==
            sha256(args.population_observed / 'observed_seal.json'),
            'receiver population seal binding differs')
    for root, seal_name, count in ((args.population_observed,
                                   'observed_seal.json', 3072),
                                  (args.observed, 'observed_seal.json', 6144)):
        seal = read_json(root / seal_name)
        require(seal.get('schema') == SCHEMA and seal.get('status') == 'pass',
                f'observed seal not valid: {root}')
        require(seal.get('observations' if count == 3072 else 'receiver_calls') == count,
                f'observed seal allocation differs: {root}')
        actual = {str(path.relative_to(root)): sha256(path)
                  for path in root.rglob('*')
                  if path.is_file() and path.name != seal_name}
        require(actual == seal.get('files'), f'observed artifact seal differs: {root}')
    generation = read_json(args.population_observed / 'generation_receipt.json')
    require(generation.get('status') == 'pass' and
            generation.get('observations') == 3072 and
            generation.get('cells') == registration['cells'] and
            generation.get('registration_sha256') == sha256(args.registration) and
            generation.get('registration_commit') == prereg and
            generation.get('protocol_sha256') == registration['protocol_sha256'] and
            generation.get('random_namespace_sha256') ==
            registration['random_namespace_sha256'] and
            generation.get('source_hashes_sha256') ==
            evidence.canonical_hash(registration['registration_source_hashes']) and
            generation.get('observed_ledger_sha256') ==
            sha256(args.population_observed / 'ledger.jsonl') and
            np.isfinite(generation.get('generation_seconds', np.nan)) and
            generation['generation_seconds'] >= 0,
            'generation receipt identity/timing differs')
    return registration, manifest, population, seal_hash


def inverse_cp_upper(k, n):
    """Solve a binomial CDF equation, independently of Beta-quantile code."""
    require(0 <= k <= n and n > 0, 'invalid upper-bound count')
    if k == n:
        return 1.0
    return float(brentq(lambda p: binom.cdf(k, n, p) - .025, 0., 1.,
                        xtol=1e-14))


def inverse_cp_lower(k, n):
    require(0 <= k <= n and n > 0, 'invalid lower-bound count')
    if k == 0:
        return 0.0
    return float(brentq(lambda p: binom.sf(k - 1, n, p) - .025, 0., 1.,
                        xtol=1e-14))


def bit_recount(decoded, info, coded, parity_rows, parity_cols, free_cols, rows):
    bits = np.asarray(decoded)
    info, coded = np.asarray(info), np.asarray(coded)
    require(bits.shape == coded.shape == (2048,) and info.shape == (1024,) and
            np.isin(bits, (0, 1)).all() and np.isin(info, (0, 1)).all() and
            np.isin(coded, (0, 1)).all(), 'invalid decoded/truth bit vector')
    syndrome = np.bincount(parity_rows[bits[parity_cols].astype(bool)],
                           minlength=rows) % 2
    return dict(info_errors=int(np.count_nonzero(bits[free_cols] != info)),
                coded_errors=int(np.count_nonzero(bits != coded)),
                syndrome_weight=int(np.count_nonzero(syndrome)))


def latest_ready(checkpoints, deadline=DEADLINE):
    require(np.isfinite(deadline) and deadline >= 0, 'invalid deadline')
    ready = []
    for index, cp in enumerate(checkpoints):
        seconds = float(cp['decision_ready_seconds'])
        require(np.isfinite(seconds) and seconds >= 0,
                'invalid checkpoint decision readiness')
        if seconds <= deadline:
            ready.append((seconds, index, cp))
    return max(ready)[2] if ready else None


def paired_table(tf, combined):
    require(len(tf) == len(combined) and all(type(x) is bool for x in tf + combined),
            'paired flags must be complete booleans')
    return dict(both_correct=sum(a and b for a, b in zip(tf, combined)),
                tf_only_correct=sum(a and not b for a, b in zip(tf, combined)),
                combined_only_correct=sum(not a and b for a, b in zip(tf, combined)),
                neither_correct=sum(not a and not b for a, b in zip(tf, combined)))


def time_summary(values):
    values = np.asarray(values, dtype=float)
    require(values.ndim == 1 and len(values) and np.isfinite(values).all(),
            'invalid timing population')
    return dict(count=int(len(values)), mean_seconds=float(np.mean(values)),
                median_seconds=float(np.median(values)),
                p90_seconds=float(np.percentile(values, 90)),
                p95_seconds=float(np.percentile(values, 95)),
                max_seconds=float(np.max(values)))


def check_clock(row):
    """Recompose exclusive branch and inclusive wrapper clocks exactly once."""
    s = row['branch_exclusive_stages']
    require(set(s) == set(STAGES) and
            all(np.isfinite(v) and v >= 0 for v in s.values()),
            'exclusive stage inventory differs')
    branch = sum(s.values())
    if row['triggered']:
        require(abs(branch - row['branch_complete_seconds']) <= 1e-7 and
                abs(branch - s['checkpoint_write'] - s['raw_serialization_hash'] -
                    row['branch_decision_seconds']) <= 1e-7,
                'CSTATE complete/decision branch clocks differ')
    else:
        require(branch == row['branch_complete_seconds'] ==
                row['branch_decision_seconds'] == 0, 'untriggered branch work differs')
    components = ('input_load_seconds', 'before_native_bookkeeping_seconds',
                  'native_two_rounds_seconds', 'before_trigger_bookkeeping_seconds',
                  'trigger_seconds', 'before_branch_bookkeeping_seconds',
                  'post_trigger_output_seconds',
                  'before_decision_record_bookkeeping_seconds',
                  'decision_record_write_seconds')
    require(all(np.isfinite(row[k]) and row[k] >= 0 for k in components) and
            abs(sum(row[k] for k in components) -
                row['complete_latency_seconds']) <= 1e-7,
            'complete receiver clock differs')
    require(row['native_checkpoint_write_seconds'] <=
            row['native_two_rounds_seconds'] and
            row['raw_artifact_ready_seconds'] <= row['complete_latency_seconds'] and
            row['ledger_append_included_in_latency'] is False,
            'nested/output clock differs')


def observation_hash(observation):
    """Rebuild the frozen dtype/shape/byte observation identity."""
    parts = []
    for name in ('y', 'pilot', 'sigma2'):
        array = np.asarray(observation[name])
        digest = hashlib.sha256()
        digest.update(str(array.dtype).encode())
        digest.update(json.dumps(array.shape).encode())
        digest.update(np.ascontiguousarray(array).tobytes())
        parts.append(digest.hexdigest())
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()


def expected_stream_ids(entropy, snr, frame):
    words = np.frombuffer(bytes.fromhex(entropy), dtype='<u4')
    prefix = [int(x) for x in words] + [0x43535441, snr, frame]
    return {name: hashlib.sha256(json.dumps(prefix + [component],
            separators=(',', ':')).encode()).hexdigest()
            for name, component in (('channel', 1), ('message', 2), ('noise', 3))}


def artifact(evidence, root, path, digest):
    filename = relative(root, path)
    require(sha256(filename) == digest, f'artifact digest differs: {path}')
    return evidence.load_artifact(filename)[0]


def compare_native(a, b):
    left, right = a['baseline_arrays'], b['baseline_arrays']
    require(set(left) == set(right), 'paired native state inventory differs')
    largest = 0.
    for key in left:
        x, y = left[key], right[key]
        if isinstance(x, np.ndarray):
            require(np.asarray(x).shape == np.asarray(y).shape,
                    f'paired native state shape differs: {key}')
            if key.endswith('decoded'):
                require(np.array_equal(x, y), f'paired native bits differ: {key}')
            else:
                require(np.allclose(x, y, rtol=1e-12, atol=1e-12),
                        f'paired native state differs: {key}')
                if np.issubdtype(np.asarray(x).dtype, np.number):
                    largest = max(largest, float(np.max(np.abs(
                        np.asarray(x, dtype=np.complex128) -
                        np.asarray(y, dtype=np.complex128)))))
        else:
            require(x == y, f'paired native value differs: {key}')
    return largest


def counts_from_rows(rows):
    tf = [row['TF']['final']['info_errors'] == 0 for row in rows]
    combined = [row['TF_CSTATE']['final']['info_errors'] == 0 for row in rows]
    tf_deadline = [not row['TF']['deadline_error'] for row in rows]
    combined_deadline = [not row['TF_CSTATE']['deadline_error'] for row in rows]
    table = paired_table(tf, combined)
    deadline_table = paired_table(tf_deadline, combined_deadline)
    triggered = [row for row in rows if row['triggered']]
    return dict(n=len(rows), paired=table, deadline_paired=deadline_table,
                tf_fer=(table['combined_only_correct'] + table['neither_correct']) / len(rows),
                combined_fer=(table['tf_only_correct'] + table['neither_correct']) / len(rows),
                triggers=len(triggered),
                rescues=sum(row['TF']['final']['info_errors'] > 0 and
                            row['TF_CSTATE']['final']['info_errors'] == 0
                            for row in triggered),
                harms=table['tf_only_correct'],
                remaining_triggered_failures=sum(
                    row['TF_CSTATE']['final']['info_errors'] > 0 for row in triggered),
                both_wrong=sum(row['TF']['final']['info_errors'] > 0 and
                               row['TF_CSTATE']['final']['info_errors'] > 0
                               for row in rows),
                info_bit_errors={arm:sum(row[arm]['final']['info_errors'] for row in rows)
                                 for arm in ARMS},
                coded_bit_errors={arm:sum(row[arm]['final']['coded_errors'] for row in rows)
                                  for arm in ARMS},
                valid_but_wrong={arm:sum(row[arm]['final']['syndrome_weight'] == 0 and
                                          row[arm]['final']['info_errors'] > 0 for row in rows)
                                 for arm in ARMS},
                syndrome_zero_coded_wrong={arm:sum(
                    row[arm]['final']['syndrome_weight'] == 0 and
                    row[arm]['final']['coded_errors'] > 0 for row in rows)
                    for arm in ARMS},
                info_correct_coded_wrong={arm:sum(
                    row[arm]['final']['info_errors'] == 0 and
                    row[arm]['final']['coded_errors'] > 0 for row in rows)
                    for arm in ARMS},
                deadline_missing={arm:sum(row[arm]['deadline_missing'] for row in rows)
                                  for arm in ARMS},
                deadline_ready_wrong={arm:sum(row[arm]['deadline_ready_wrong'] for row in rows)
                                      for arm in ARMS},
                fallback_counts={arm:sum(row[arm]['fallback'] for row in rows)
                                 for arm in ARMS},
                latency={arm:time_summary([row[arm]['complete_latency_seconds']
                                           for row in rows]) for arm in ARMS})


def _inventory(root, seal_name, *, expected_observations, registration_hash,
               observed_seal_hash):
    seal = read_json(root / seal_name)
    require(seal.get('schema') == SCHEMA and seal.get('status') == 'pass' and
            seal.get('observations') == expected_observations and
            seal.get('registration_sha256') == registration_hash and
            seal.get('observed_seal_sha256') == observed_seal_hash,
            'truth seal identity differs')
    actual = {str(path.relative_to(root)): sha256(path)
              for path in root.rglob('*')
              if path.is_file() and path.name != seal_name}
    require(actual == seal.get('files'), 'truth artifact inventory differs')
    return actual


def _allocation(population_rows, truth_rows, receiver_rows, pair_rows):
    coordinates = [(snr, frame) for snr in CELLS for frame in range(FRAMES)]
    require([(r['snr_centi_db'], r['frame']) for r in population_rows] ==
            coordinates, 'population allocation/order differs')
    require([(r['snr_centi_db'], r['frame']) for r in truth_rows] ==
            coordinates, 'truth allocation/order differs')
    expected = [(f's{snr}_f{frame:04d}', arm)
                for index, (snr, frame) in enumerate(coordinates)
                for arm in (ARMS if index % 2 == 0 else ARMS[::-1])]
    require([(r['observation_id'], r['arm']) for r in receiver_rows] == expected and
            len(set(expected)) == 6144 and
            all(r['status'] == 'ok' and r['receiver_started']
                for r in receiver_rows), 'receiver allocation/status differs')
    require([r['observation_id'] for r in pair_rows] ==
            [f's{snr}_f{frame:04d}' for snr, frame in coordinates],
            'paired native audit allocation differs')


def _cache(baseline, registration):
    cache = (baseline / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled'
             / 'e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    require(sha256(cache) == registration['ldpc_cache_sha256'],
            'actual LDPC cache hash differs')
    with np.load(cache, allow_pickle=False) as saved:
        H, G, free = (np.asarray(saved[key]).copy()
                      for key in ('H', 'G', 'free_cols'))
    require(H.shape == (1026, 2048) and G.shape == (2048, 1024) and
            free.shape == (1024,) and np.isin(H, (0, 1)).all() and
            len(set(free.tolist())) == len(free) and
            np.all((0 <= free) & (free < 2048)) and
            hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() ==
            registration['code_g_sha256'], 'actual H/G/free-code identity differs')
    return (*np.nonzero(H), free, H.shape[0])


def _check_decision_record(row, decision, raw, checkpoints):
    for key in ('observation_id', 'arm', 'input_sha256', 'stream_ids',
                'triggered', 'baseline_syndrome_weight',
                'final_syndrome_weight', 'final_decoded_sha256',
                'final_decision_ready_seconds', 'checkpoints', 'raw_path',
                'raw_sha256', 'branch_exclusive_stages',
                'source_hashes_sha256', 'receiver_config_sha256'):
        require(decision[key] == row[key], f'decision record/ledger differs: {key}')
    final_bits = np.asarray(checkpoints[-1]['decoded'])
    digest = hashlib.sha256(final_bits.tobytes()).hexdigest()
    require(digest == row['final_decoded_sha256'] and
            np.array_equal(final_bits, raw['final_decoded']) and
            np.array_equal(final_bits,
                           raw['branch_decoder']['decoded'] if row['triggered']
                           else raw['native_decoder']['decoded']),
            'final raw/checkpoint decision bits differ')


def _row(evidence, observed, row, info, coded, parity):
    require(row['arm'] in ARMS and row['receiver_config_sha256'] and
            row['source_hashes_sha256'], 'receiver source/config identity absent')
    raw = artifact(evidence, observed, row['raw_path'], row['raw_sha256'])
    decision_path = relative(observed, row['decision_record_path'])
    require(sha256(decision_path) == row['decision_record_sha256'],
            'decision record hash differs')
    decision = read_json(decision_path)
    require(raw['observation_id'] == row['observation_id'] and
            raw['arm'] == row['arm'] and
            raw['input_sha256'] == row['input_sha256'] and
            raw['stream_ids'] == row['stream_ids'],
            'raw observation/stream identity differs')
    require(len(row['checkpoints']) in (2, 3) and
            [cp['round'] for cp in row['checkpoints']] ==
            list(range(len(row['checkpoints']))), 'checkpoint sequence differs')
    checkpoint_payloads = []
    recounts = []
    parity_rows, parity_cols, free_cols, H_rows = parity
    for cp_row in row['checkpoints']:
        cp = artifact(evidence, observed, cp_row['path'], cp_row['artifact_sha256'])
        require(np.asarray(cp['decoded']).dtype == np.uint8 and
                {key: value for key, value in cp['event'].items()
                 if key != 'snapshot'} == cp_row['event'],
                'checkpoint event/dtype differs')
        tally = bit_recount(cp['decoded'], info, coded, parity_rows,
                            parity_cols, free_cols, H_rows)
        require(tally['syndrome_weight'] == cp_row['syndrome_weight'],
                'checkpoint syndrome recount differs')
        require(cp['event']['round'] == cp_row['round'] and
                np.array_equal(cp['event']['snapshot']['decoded'],
                               cp['decoded']) and
                0 <= cp_row['decision_ready_seconds'] <=
                cp_row['artifact_ready_seconds'] <=
                row['complete_latency_seconds'],
                'checkpoint event/ready clock differs')
        checkpoint_payloads.append(cp)
        recounts.append(tally)
    require(np.array_equal(checkpoint_payloads[0]['decoded'],
                           raw['baseline_arrays']['r0_decoded']) and
            np.array_equal(checkpoint_payloads[1]['decoded'],
                           raw['baseline_arrays']['r1_decoded']) and
            np.array_equal(checkpoint_payloads[1]['decoded'],
                           raw['native_decoder']['decoded']),
            'raw native-prefix decoded bits differ')
    baseline_syndrome = recounts[1]['syndrome_weight']
    triggered = row['arm'] == 'TF_CSTATE' and baseline_syndrome != 0
    require(row['triggered'] is triggered and raw['triggered'] is triggered and
            len(recounts) == (3 if triggered else 2) and
            row['baseline_syndrome_weight'] ==
            raw['baseline_syndrome_weight'] == baseline_syndrome and
            row['final_syndrome_weight'] == recounts[-1]['syndrome_weight'],
            'observed trigger/final syndrome differs')
    if triggered:
        require(raw['geometry_result'] is not None and
                raw['branch_detector'] is not None and
                raw['branch_decoder'] is not None and
                raw['branch_inputs'] is not None,
                'triggered structural evidence is missing')
        diagnostics = raw['geometry_result']['diagnostics']
        fallback = bool(diagnostics['numerical_fallback'])
        require(fallback == bool(diagnostics['fallback_reason']),
                'numerical fallback reason differs')
        kernel_timing = diagnostics['stage_timing']
        exclusive = kernel_timing['exclusive_seconds']
        require(set(exclusive).issubset(STAGES) and
                all(abs(value - row['branch_exclusive_stages'][name]) <= 1e-7
                    for name, value in exclusive.items()) and
                abs(sum(exclusive.values()) -
                    kernel_timing['total_seconds']) <= 1e-7 and
                abs(raw['geometry_result']['elapsed_seconds'] -
                    kernel_timing['total_seconds']) <= 1e-7,
                'nested geometry stage clocks differ')
        discarded = float(kernel_timing['discarded_compact_seconds'])
        require(np.isfinite(discarded) and discarded >= 0 and
                discarded <= kernel_timing['total_seconds'] + 1e-7 and
                (fallback or discarded == 0) and
                raw['geometry_result']['evaluations']['fallback_calls'] ==
                int(fallback), 'discarded/fallback work accounting differs')
    else:
        require(all(raw[key] is None for key in
                    ('geometry_result', 'branch_detector', 'branch_decoder',
                     'branch_inputs')), 'untriggered structural work present')
        fallback = False
    _check_decision_record(row, decision, raw, checkpoint_payloads)
    check_clock(row)
    latest = latest_ready(row['checkpoints'])
    latest_tally = None if latest is None else recounts[latest['round']]
    return raw, dict(final=recounts[-1], checkpoint_recounts=recounts,
                     deadline_round=None if latest is None else latest['round'],
                     deadline_missing=latest is None,
                     deadline_ready_wrong=bool(latest_tally is not None and
                                               latest_tally['info_errors'] > 0),
                     deadline_error=bool(latest_tally is None or
                                         latest_tally['info_errors'] > 0),
                     fallback=fallback,
                     complete_latency_seconds=row['complete_latency_seconds'])


def _close(actual, expected, label, *, atol=1e-10):
    require(np.isfinite(actual) and np.isfinite(expected) and
            abs(actual - expected) <= atol, f'analysis differs: {label}')


def _csv_bool(value, label):
    require(value in ('True', 'False'), f'analysis boolean differs: {label}')
    return value == 'True'


def _compare_csv(args, per_cell, by_key):
    frames = list(csv.DictReader((args.analysis / 'frame_outcomes.csv').open()))
    arms = list(csv.DictReader((args.analysis / 'arm_outcomes.csv').open()))
    stages = list(csv.DictReader((args.analysis / 'stage_times.csv').open()))
    ordered = [row for snr in CELLS for row in per_cell[snr]]
    require(len(frames) == len(stages) == len(ordered) == 3072 and
            len(arms) == 6144, 'analysis CSV allocation differs')
    for index, (frame, stage, actual) in enumerate(zip(frames, stages, ordered)):
        stem, snr = actual['observation_id'], CELLS[index // FRAMES]
        require(frame['observation_id'] == stage['observation_id'] == stem and
                int(frame['snr_centi_db']) == int(stage['snr_centi_db']) == snr and
                _csv_bool(frame['trigger'], 'frame trigger') is actual['triggered'] and
                _csv_bool(stage['trigger'], 'stage trigger') is actual['triggered'],
                'analysis frame/stage identity differs')
        tf_correct = actual['TF']['final']['info_errors'] == 0
        combined_correct = actual['TF_CSTATE']['final']['info_errors'] == 0
        for name, expected in (
                ('rescue', actual['triggered'] and not tf_correct and combined_correct),
                ('harm', tf_correct and not combined_correct),
                ('remaining_triggered_failure', actual['triggered'] and
                 not combined_correct),
                ('both_wrong', not tf_correct and not combined_correct),
                ('combined_fallback', actual['TF_CSTATE']['fallback'])):
            require(_csv_bool(frame[name], name) is expected,
                    f'analysis frame classification differs: {stem}/{name}')
        for arm, prefix in (('TF', 'tf'), ('TF_CSTATE', 'combined')):
            row = actual[arm]
            for key, expected in (
                    ('correct', row['final']['info_errors'] == 0),
                    ('undetected', row['final']['syndrome_weight'] == 0 and
                     row['final']['info_errors'] > 0),
                    ('syndrome_zero_coded_wrong',
                     row['final']['syndrome_weight'] == 0 and
                     row['final']['coded_errors'] > 0),
                    ('info_correct_coded_wrong',
                     row['final']['info_errors'] == 0 and
                     row['final']['coded_errors'] > 0),
                    ('deadline_correct', not row['deadline_error']),
                    ('deadline_missing', row['deadline_missing']),
                    ('deadline_ready_wrong', row['deadline_ready_wrong'])):
                require(_csv_bool(frame[f'{prefix}_{key}'], key) is expected,
                        f'analysis frame outcome differs: {stem}/{arm}/{key}')
            for key, expected in (('info_errors', row['final']['info_errors']),
                                  ('coded_errors', row['final']['coded_errors']),
                                  ('final_syndrome_weight',
                                   row['final']['syndrome_weight'])):
                require(int(frame[f'{prefix}_{key}']) == expected,
                        f'analysis error count differs: {stem}/{arm}/{key}')
            ready_round = frame[f'{prefix}_deadline_ready_round']
            require((ready_round == '' if row['deadline_round'] is None else
                     int(ready_round) == row['deadline_round']),
                    f'analysis deadline round differs: {stem}/{arm}')
            _close(float(frame[f'{prefix}_latency_seconds']),
                   row['complete_latency_seconds'], f'{stem}/{arm}/latency')
            arm_csv = arms[2 * index + (0 if arm == 'TF' else 1)]
            require(arm_csv['observation_id'] == stem and arm_csv['arm'] == arm and
                    int(arm_csv['final_info_errors']) ==
                    row['final']['info_errors'] and
                    int(arm_csv['final_coded_errors']) ==
                    row['final']['coded_errors'] and
                    int(arm_csv['final_syndrome_weight']) ==
                    row['final']['syndrome_weight'] and
                    _csv_bool(arm_csv['deadline_missing'], 'arm missing') is
                    row['deadline_missing'] and
                    _csv_bool(arm_csv['deadline_system_failure'], 'arm failure') is
                    row['deadline_error'] and
                    _csv_bool(arm_csv['syndrome_zero_coded_wrong'],
                        'arm syndrome-zero coded-wrong') is
                    (row['final']['syndrome_weight'] == 0 and
                     row['final']['coded_errors'] > 0) and
                    _csv_bool(arm_csv['info_correct_coded_wrong'],
                        'arm info-correct coded-wrong') is
                    (row['final']['info_errors'] == 0 and
                     row['final']['coded_errors'] > 0),
                    f'analysis arm outcome differs: {stem}/{arm}')
            require(json.loads(arm_csv['checkpoint_info_errors']) ==
                    [c['info_errors'] for c in row['checkpoint_recounts']] and
                    json.loads(arm_csv['checkpoint_coded_errors']) ==
                    [c['coded_errors'] for c in row['checkpoint_recounts']] and
                    json.loads(arm_csv['checkpoint_syndrome_weights']) ==
                    [c['syndrome_weight'] for c in row['checkpoint_recounts']],
                    f'analysis per-checkpoint recount differs: {stem}/{arm}')
        combined_row = by_key[stem, 'TF_CSTATE']
        _close(float(stage['complete_branch_seconds']),
               combined_row['branch_complete_seconds'], f'{stem}/stage complete')
        for name in STAGES:
            _close(float(stage[name]),
                   combined_row['branch_exclusive_stages'][name],
                   f'{stem}/stage {name}')


def _compare_summary(args, per_cell, by_key, computed,
                     upper_h, lower_r, upper_delta):
    summary = read_json(args.analysis / 'summary.json')
    receipt = read_json(args.analysis / 'receipt.json')
    stage_summary = read_json(args.analysis / 'stage_summary.json')
    require(summary.get('status') == receipt.get('status') == 'complete' and
            summary.get('evidence_integrity') ==
            receipt.get('evidence_integrity') == 'pass' and
            receipt.get('observed_seal_sha256') ==
            sha256(args.observed / 'observed_seal.json') and
            receipt.get('seal_commit') == args.seal_commit and
            receipt.get('preregistration_commit') == args.registration_commit and
            receipt.get('registration_sha256') == sha256(args.registration) and
            receipt.get('truth_seal_sha256') ==
            sha256(args.truth_root / 'truth_seal.json') and
            summary.get('truth_seal_sha256') ==
            receipt.get('truth_seal_sha256') and
            summary.get('git_seal', {}).get('commit') == args.seal_commit and
            summary.get('git_registration', {}).get('preregistration_commit') ==
            args.registration_commit,
            'analysis receipt identity/status differs')
    for name, expected_hash in receipt['files'].items():
        require(sha256(relative(args.analysis, name)) == expected_hash,
                f'analysis output hash differs: {name}')
    for snr in CELLS:
        key = str(snr)
        expected, saved = computed[key], summary['cells'][key]
        require(saved['n'] == 1024 and saved['paired_table'] == expected['paired'] and
                saved['trigger_count'] == expected['triggers'] and
                saved['rescue_count'] == expected['rescues'] and
                saved['harm_count'] == expected['harms'] and
                saved['remaining_triggered_failure_count'] ==
                expected['remaining_triggered_failures'] and
                saved['both_wrong_count'] == expected['both_wrong'] and
                saved['undetected_tf_count'] == expected['valid_but_wrong']['TF'] and
                saved['undetected_combined_count'] ==
                expected['valid_but_wrong']['TF_CSTATE'] and
                saved['syndrome_zero_coded_wrong_tf_count'] ==
                expected['syndrome_zero_coded_wrong']['TF'] and
                saved['syndrome_zero_coded_wrong_combined_count'] ==
                expected['syndrome_zero_coded_wrong']['TF_CSTATE'] and
                saved['info_correct_coded_wrong_tf_count'] ==
                expected['info_correct_coded_wrong']['TF'] and
                saved['info_correct_coded_wrong_combined_count'] ==
                expected['info_correct_coded_wrong']['TF_CSTATE'] and
                saved['compact_fallback_count'] ==
                expected['fallback_counts']['TF_CSTATE'],
                f'analysis cell counts differ: {snr}')
        _close(saved['trigger_fraction'], expected['triggers'] / FRAMES,
               f'{snr}/trigger fraction')
        _close(saved['descriptive_tf_fer']['estimate'], expected['tf_fer'],
               f'{snr}/TF FER')
        _close(saved['descriptive_combined_fer']['estimate'],
               expected['combined_fer'], f'{snr}/combined FER')
        require(saved['deadline_0p5']['table'] == expected['deadline_paired'],
                f'analysis deadline paired table differs: {snr}')
        for arm, prefix in (('TF', 'tf'), ('TF_CSTATE', 'combined')):
            for suffix, amount in (
                    ('missing_count', expected['deadline_missing'][arm]),
                    ('ready_decoded_error_count',
                     expected['deadline_ready_wrong'][arm]),
                    ('system_failure_count',
                     expected['deadline_missing'][arm] +
                     expected['deadline_ready_wrong'][arm])):
                require(saved['deadline_0p5'][f'{prefix}_{suffix}'] == amount,
                        f'analysis deadline count differs: {snr}/{arm}/{suffix}')
            require(saved[f'coded_bit_errors_{prefix}'] ==
                    expected['coded_bit_errors'][arm],
                    f'analysis coded errors differ: {snr}/{arm}')
            require(saved[f'info_bit_errors_{prefix}'] ==
                    expected['info_bit_errors'][arm],
                    f'analysis info errors differ: {snr}/{arm}')
            _close(saved[f'info_ber_{prefix}'],
                   expected['info_bit_errors'][arm] / (FRAMES * 1024),
                   f'{snr}/{arm}/info BER')
            _close(saved[f'coded_ber_{prefix}'],
                   expected['coded_bit_errors'][arm] / (FRAMES * 2048),
                   f'{snr}/{arm}/coded BER')
        for cohort in ('all', 'trigger', 'nontrigger'):
            subset = [row for row in per_cell[snr]
                      if cohort == 'all' or row['triggered'] == (cohort == 'trigger')]
            saved_cohort = saved['latency'][cohort]
            saved_stages = stage_summary[key][cohort]
            require(saved_cohort['count'] == saved_stages['count'] == len(subset),
                    f'analysis cohort denominator differs: {snr}/{cohort}')
            if not subset:
                require(saved_cohort['latency'] is None and
                        saved_stages['stages'] is None,
                        f'empty cohort must have null statistics: {snr}/{cohort}')
                continue
            tf_times = np.array([row['TF']['complete_latency_seconds']
                                 for row in subset])
            combined_times = np.array([row['TF_CSTATE']['complete_latency_seconds']
                                       for row in subset])
            lat = saved_cohort['latency']
            for name, values in (('tf', tf_times), ('combined', combined_times)):
                actual = time_summary(values)
                for metric, value in actual.items():
                    if metric == 'count':
                        require(lat[name][metric] == value,
                                f'latency count differs: {snr}/{cohort}/{name}')
                    else:
                        _close(lat[name][metric], value,
                               f'{snr}/{cohort}/{name}/{metric}')
            for label, values, suffix in (
                    ('paired_delta_seconds', combined_times - tf_times, '_seconds'),
                    ('paired_ratio', combined_times / tf_times, '')):
                actual = time_summary(values)
                for target, metric in (('mean', 'mean_seconds'),
                                       ('median', 'median_seconds'),
                                       ('p90', 'p90_seconds'),
                                       ('p95', 'p95_seconds'),
                                       ('maximum', 'max_seconds')):
                    _close(lat[label][target + suffix], actual[metric],
                           f'{snr}/{cohort}/{label}/{target}')
                _close(lat[label]['minimum' + suffix], float(np.min(values)),
                       f'{snr}/{cohort}/{label}/minimum')
            _close(lat['ratio_of_means'],
                   float(np.mean(combined_times) / np.mean(tf_times)),
                   f'{snr}/{cohort}/ratio of means')
            complete = sum(by_key[row['observation_id'], 'TF_CSTATE'][
                'branch_complete_seconds'] for row in subset)
            for stage in STAGES:
                values = np.asarray([by_key[row['observation_id'],
                    'TF_CSTATE']['branch_exclusive_stages'][stage]
                    for row in subset], dtype=float)
                actual = time_summary(values)
                saved_stage = saved_stages['stages'][stage]
                require(saved_stage['count'] == actual['count'],
                        f'stage count differs: {snr}/{cohort}/{stage}')
                for metric in ('mean_seconds', 'median_seconds', 'p90_seconds',
                               'p95_seconds', 'max_seconds'):
                    _close(saved_stage[metric], actual[metric],
                           f'{snr}/{cohort}/{stage}/{metric}')
                share = None if complete == 0 else float(np.sum(values) / complete)
                if share is None:
                    require(saved_stage['share_of_complete_branch'] is None,
                            f'zero stage share differs: {snr}/{cohort}/{stage}')
                else:
                    _close(saved_stage['share_of_complete_branch'], share,
                           f'{snr}/{cohort}/{stage}/share')
    primary = summary['cells']['650']['paired_inference']
    require(primary['table'] == computed['650']['paired'] and
            primary['primary_pass'] is (upper_delta < 0) and
            summary['primary_pass'] is (upper_delta < 0) and
            receipt['primary_pass'] is (upper_delta < 0),
            'analysis primary pass/table differs')
    for key, value in (('primary_upper_95', upper_delta),
                       ('delta_hat', (computed['650']['paired']['tf_only_correct'] -
                                      computed['650']['paired']['combined_only_correct']) /
                                      FRAMES)):
        _close(primary[key], value, f'primary {key}')
    _close(primary['primary_components']['h_upper_one_sided_97p5'], upper_h,
           'primary upper h')
    _close(primary['primary_components']['r_lower_one_sided_97p5'], lower_r,
           'primary lower r')
    require(summary['receiver_calls_recounted'] == 6144 and
            summary['observations_recounted'] == 3072 and
            summary['checkpoints_recounted'] ==
            sum(len(row['checkpoints']) for row in by_key.values()),
            'analysis sample/checkpoint denominators differ')
    return summary, receipt


def verify(args):
    args.out = args.out.resolve()
    for protected in (args.registration.parent, args.population_observed,
                      args.truth_root, args.observed, args.analysis,
                      args.source, args.baseline, args.evidence_git):
        protected = protected.resolve()
        require(args.out != protected and protected not in args.out.parents,
                'verification output would modify a protected input')
    require(not args.out.exists(), 'verification output already exists')
    args.out.mkdir(parents=True)
    try:
        registration, manifest, population_manifest, seal_hash = pretruth_gate(args)
        registration_hash = sha256(args.registration)
        truth_files = _inventory(args.truth_root, 'truth_seal.json',
                                 expected_observations=3072,
                                 registration_hash=registration_hash,
                                 observed_seal_hash=sha256(
                                     args.population_observed / 'observed_seal.json'))
        require(read_json(args.population_observed / 'generation_receipt.json')
                ['truth_ledger_sha256'] ==
                sha256(args.truth_root / 'ledger.jsonl'),
                'generation truth-ledger receipt differs')
        population_rows = read_jsonl(args.population_observed / 'ledger.jsonl')
        truth_rows = read_jsonl(args.truth_root / 'ledger.jsonl')
        receiver_rows = read_jsonl(args.observed / 'ledger.jsonl')
        pair_rows = read_jsonl(args.observed / 'paired_audit.jsonl')
        _allocation(population_rows, truth_rows, receiver_rows, pair_rows)
        require(len(truth_files) == 3074, 'truth file allocation differs')
        parity = _cache(args.baseline, registration)
        evidence = attach(args.source, args.baseline)
        entropy = registration['streams']['entropy_hex']
        require(len(entropy) == 64, 'registered entropy size differs')
        by_key = {(row['observation_id'], row['arm']): row
                  for row in receiver_rows}
        per_cell = {snr: [] for snr in CELLS}
        stream_set = set()
        cp_count = 0
        for population, truth_row, pair in zip(population_rows, truth_rows, pair_rows):
            stem = population['observation_id']
            snr, frame = population['snr_centi_db'], population['frame']
            require(stem == truth_row['observation_id'] ==
                    pair['observation_id'] == f's{snr}_f{frame:04d}',
                    'paired observation identity differs')
            streams = expected_stream_ids(entropy, snr, frame)
            require(population['stream_ids'] == truth_row['stream_ids'] == streams,
                    'fresh stream identity differs')
            for value in streams.values():
                require(value not in stream_set, 'fresh stream ID collision')
                stream_set.add(value)
            observed_input = artifact(evidence, args.population_observed,
                                      population['observation_path'],
                                      population['observation_sha256'])
            obs = observed_input['observation']
            require(set(obs) == {'y', 'pilot', 'sigma2'} and
                    observed_input['observation_id'] == stem and
                    observed_input['stream_ids'] == streams,
                    'observed input identity differs')
            input_hash = observation_hash(obs)
            require(input_hash == population['observation_hash'] ==
                    truth_row['observation_hash'] ==
                    observed_input['observation_hash'],
                    'fresh observation bytes/hash differ')
            truth = artifact(evidence, args.truth_root,
                             truth_row['truth_path'], truth_row['truth_sha256'])
            require(truth['observation_hash'] == input_hash and
                    truth['stream_ids'] == streams,
                    'truth/observed identity differs')
            info, coded = np.asarray(truth['info']), np.asarray(truth['coded'])
            require(info.dtype == coded.dtype == np.uint8 and
                    info.shape == (1024,) and coded.shape == (2048,) and
                    np.array_equal(coded[parity[2]], info) and
                    bit_recount(coded, info, coded, *parity)['syndrome_weight'] == 0,
                    'truth codeword identity differs')
            arm_rows = {}
            arm_raw = {}
            for arm in ARMS:
                row = by_key[stem, arm]
                require(row['input_sha256'] == population['observation_sha256'] and
                        row['observation_hash'] == input_hash and
                        row['stream_ids'] == streams and
                        row['source_hashes_sha256'] ==
                        manifest['source_hashes_sha256'] and
                        row['receiver_config_sha256'] ==
                        manifest['receiver_config_sha256'],
                        'receiver observed/source/config binding differs')
                arm_raw[arm], arm_rows[arm] = _row(evidence, args.observed,
                                                   row, info, coded, parity)
                cp_count += len(row['checkpoints'])
            native_difference = compare_native(arm_raw['TF'],
                                               arm_raw['TF_CSTATE'])
            require(pair['first_arm'] == (ARMS if
                    (CELLS.index(snr) * FRAMES + frame) % 2 == 0
                    else ARMS[::-1])[0] and
                    pair['second_arm'] != pair['first_arm'] and
                    pair['first_input_sha256'] ==
                    pair['second_input_sha256'] ==
                    population['observation_sha256'] and
                    pair['native_decoded_identical'] is True and
                    abs(pair['max_native_continuous_difference'] -
                        native_difference) <= 1e-12 and
                    native_difference <= 1e-12,
                    'paired native audit differs')
            require(arm_rows['TF']['checkpoint_recounts'][:2] ==
                    arm_rows['TF_CSTATE']['checkpoint_recounts'][:2],
                    'paired native checkpoint recount differs')
            trigger = arm_rows['TF']['checkpoint_recounts'][1]['syndrome_weight'] > 0
            require(trigger == by_key[stem, 'TF_CSTATE']['triggered'],
                    'paired trigger differs')
            per_cell[snr].append(dict(observation_id=stem, triggered=trigger,
                                      **arm_rows))
        require(cp_count == 12288 + sum(row['triggered']
                                         for row in receiver_rows),
                'checkpoint total differs')
        computed = {str(snr): counts_from_rows(per_cell[snr]) for snr in CELLS}
        primary = computed['650']['paired']
        h, r = primary['tf_only_correct'], primary['combined_only_correct']
        upper_h, lower_r = inverse_cp_upper(h, FRAMES), inverse_cp_lower(r, FRAMES)
        upper_delta = upper_h - lower_r
        expected_pass = upper_delta < 0
        _compare_csv(args, per_cell, by_key)
        analysis_summary, analysis_receipt = _compare_summary(
            args, per_cell, by_key, computed, upper_h, lower_r, upper_delta)
        require(analysis_summary['observed_seal_sha256'] == seal_hash and
                analysis_receipt['observed_seal_sha256'] == seal_hash,
                'analyzer observed seal binding differs')
        result = dict(status='pass', schema=SCHEMA,
            registration_commit=args.registration_commit,
            seal_commit=args.seal_commit, observed_seal_sha256=seal_hash,
            registration_sha256=registration_hash,
            population_observed_seal_sha256=sha256(
                args.population_observed / 'observed_seal.json'),
            committed_truth_seal_sha256=sha256(
                args.truth_root / 'truth_seal.json'),
            population_observations=3072, receiver_calls=6144,
            checkpoints_recounted=cp_count, paired_native_checks=3072,
            unique_stream_ids=len(stream_set), cells=computed,
            primary_650=dict(h=h, r=r, h_upper=upper_h, r_lower=lower_r,
                             delta_hat=(h-r)/FRAMES, upper_95=upper_delta,
                             pass_confirmation=expected_pass),
            analysis_receipt_sha256=sha256(args.analysis / 'receipt.json'),
            independent_method='binomial CDF/SF inversion; sparse integer parity')
        (args.out / 'receipt.json').write_text(json.dumps(result, indent=2,
            allow_nan=False) + '\n')
        return result
    except Exception as error:
        (args.out / 'receipt.json').write_text(json.dumps(dict(
            status='fail', reason=str(error), seal_commit=args.seal_commit),
            indent=2) + '\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('evidence-git', 'registration', 'population-observed',
                 'truth-root', 'observed', 'analysis', 'source', 'baseline', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--seal-commit', required=True)
    parser.add_argument('--registration-commit', required=True)
    verify(parser.parse_args())
