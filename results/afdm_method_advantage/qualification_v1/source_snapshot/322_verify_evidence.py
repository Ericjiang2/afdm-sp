"""Offline recount of the frozen B campaign; never constructs a receiver.

The verifier reads only saved artifacts.  Its LDPC cache comes from the A
receipt and is checked against both that receipt and the original code header.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from audit_io import selected_records, sha256, unpack, write_json


ARMS = ('baseline_replay', 'J40R2', 'J20R3', 'true_geometry',
        'true_H_TF20R2', 'true_H_EP8R2', 'true_data_original_TF20R2',
        'true_data_expanded_TF20R2')
METADATA = '__evidence_metadata__'
ARRAY = '__evidence_array__'
TUPLE = '__evidence_tuple__'
REPLAY_KEYS = ('input_llr', 'app', 'check', 'delays', 'dopplers',
               'gains', 'mu', 'variance')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _within(root, relative):
    path = (root / relative).resolve()
    _require(path.is_relative_to(root.resolve()), f'path leaves evidence root: {relative}')
    return path


def _unpack_tree(tree, arrays, references):
    if isinstance(tree, dict):
        if set(tree) == {ARRAY}:
            key = tree[ARRAY]
            _require(isinstance(key, str) and key in arrays and key not in references,
                     'invalid or repeated evidence array reference')
            references.add(key)
            return arrays[key].copy()
        if set(tree) == {TUPLE}:
            return tuple(_unpack_tree(item, arrays, references) for item in tree[TUPLE])
        return {key: _unpack_tree(value, arrays, references) for key, value in tree.items()}
    if isinstance(tree, list):
        return [_unpack_tree(value, arrays, references) for value in tree]
    return tree


def _artifact(path, digest, expected_identity=None):
    _require(sha256(path) == digest, f'artifact hash differs: {path}')
    with np.load(path, allow_pickle=False) as archive:
        _require(METADATA in archive.files, f'missing evidence metadata: {path}')
        raw = np.asarray(archive[METADATA])
        _require(raw.dtype == np.uint8 and raw.ndim == 1,
                 f'invalid evidence metadata: {path}')
        envelope = json.loads(raw.tobytes().decode('utf-8'))
        _require(envelope.get('format_version') == 2, f'evidence format differs: {path}')
        if expected_identity is not None:
            _require(envelope.get('identity') == expected_identity,
                     f'evidence identity differs: {path}')
        arrays = {key: np.asarray(archive[key]) for key in archive.files if key != METADATA}
    references = set()
    payload = _unpack_tree(envelope['payload'], arrays, references)
    _require(references == set(arrays), f'evidence array inventory differs: {path}')
    return payload


def _bits(value, length, label):
    bits = np.asarray(value)
    _require(bits.shape == (length,) and np.issubdtype(bits.dtype, np.integer)
             and np.isin(bits, (0, 1)).all(), f'invalid {label} bit vector')
    return bits.astype(np.int32)


def _code(run, b_output):
    a_receipt_path = b_output.parent / 'A' / 'receipt.json'
    a_receipt = json.loads(a_receipt_path.read_text())
    declared = Path(a_receipt['ldpc_cache_path'])
    candidates = ([declared] if declared.is_absolute() else
                  [run.parents[2] / declared, Path.cwd() / declared])
    cache = next((path for path in candidates if path.is_file()), None)
    _require(cache is not None, f'A-bound LDPC cache is unavailable: {declared}')
    _require(sha256(cache) == a_receipt['ldpc_cache_sha256'],
             'A-bound LDPC cache hash differs')
    with np.load(cache, allow_pickle=False) as archive:
        H = np.asarray(archive['H'])
        G = np.asarray(archive['G'])
        free = np.asarray(archive['free_cols'])
    header = json.loads((run / 'context_header.json').read_text())
    _require(hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest()
             == header['code_g_sha256'], 'LDPC generator differs from original header')
    _require(H.ndim == 2 and H.shape[0] > 0 and H.shape[1] == 2048
             and G.shape == (2048, 1024) and free.shape == (1024,)
             and np.issubdtype(free.dtype, np.integer)
             and len(np.unique(free)) == 1024 and np.all((free >= 0) & (free < 2048)),
             'unexpected LDPC cache dimensions or information indices')
    return H.astype(np.int32), free.astype(np.intp), sha256(cache)


def _counts(decoded, truth, H, free):
    coded = _bits(unpack(truth['coded']), H.shape[1], 'true coded')
    info = _bits(unpack(truth['info']), len(free), 'true information')
    bits = _bits(decoded, H.shape[1], 'decoded')
    return dict(info_errors=int(np.count_nonzero(bits[free] != info)),
                coded_errors=int(np.count_nonzero(bits != coded)),
                syndrome_weight=int(np.count_nonzero((H @ bits) % 2)))


def _selection(run, b_output, manifest, a_receipt):
    selection_path = b_output.parent / 'A' / 'selection.json'
    _require(sha256(selection_path) == manifest['selection_sha256']
             == a_receipt['files']['selection.json'], 'A selection hash differs')
    _require(sha256(run / 'manifest.json') == manifest['original_manifest_sha256']
             == a_receipt['manifest_sha256'], 'original manifest hash differs')
    _require(sha256(run / 'ledger.jsonl') == a_receipt['ledger_sha256'],
             'original ledger hash differs')
    selection = json.loads(selection_path.read_text())['observations']
    original = [json.loads(line) for line in (run / 'ledger.jsonl').open()]
    tf = [row for row in original if row['arm'] == 'TF_J20_R2']
    expected = selected_records(tf)
    _require(len(selection) == 64 and
             [row['baseline_record'] for row in selection] == expected,
             'selected 32/32 baseline records differ from original ledger')
    return {row['observation_id']: row for row in selection}


def _replay_difference(run, record, payload, H, free, truth):
    largest = 0.0
    for checkpoint in record['checkpoints']:
        round_index = checkpoint['round']
        saved = _artifact(_within(run, checkpoint['path']), checkpoint['artifact_sha256'])
        saved_decoded = _bits(unpack(saved['decoded']), H.shape[1], 'original decoded')
        _require(_counts(saved_decoded, truth, H, free) ==
                 {key: checkpoint[key] for key in ('info_errors', 'coded_errors', 'syndrome_weight')},
                 'original baseline checkpoint recount differs')
        replay_decoded = _bits(payload['arrays'][f'r{round_index}_decoded'],
                               H.shape[1], 'replay decoded')
        _require(np.array_equal(replay_decoded, saved_decoded),
                 'baseline replay hard decision differs')
        for key in REPLAY_KEYS:
            actual = np.asarray(payload['arrays'][f'r{round_index}_{key}'])
            baseline = np.asarray(saved['snapshot'][key])
            _require(actual.shape == baseline.shape and np.isfinite(actual).all()
                     and np.isfinite(baseline).all(),
                     f'baseline replay array invalid: r{round_index}/{key}')
            difference = float(np.max(np.abs(actual - baseline)))
            largest = max(largest, difference)
            _require(difference == 0.0, f'baseline replay differs: r{round_index}/{key}')
    return largest


def verify(run, b_output, out):
    run, b_output, out = Path(run).resolve(), Path(b_output).resolve(), Path(out).resolve()
    _require(not out.is_relative_to(run) and not out.is_relative_to(b_output),
             'verification output must be outside frozen evidence roots')
    _require(not out.exists(), f'verification output already exists: {out}')
    receipt = json.loads((b_output / 'receipt.json').read_text())
    manifest = json.loads((b_output / 'manifest.json').read_text())
    _require(receipt['status'] == 'pass' and receipt['receiver_calls'] == 512
             and receipt['observations'] == 64 and receipt['newly_generated_observations'] == 0,
             'B receipt allocation or status differs')
    for name, digest in receipt['files'].items():
        _require(sha256(_within(b_output, name)) == digest,
                 f'B top-level receipt hash differs: {name}')
    ledger_path = b_output / 'ledger.jsonl'
    _require(sha256(ledger_path) == receipt['ledger_sha256'], 'B ledger hash differs')
    a_receipt = json.loads((b_output.parent / 'A' / 'receipt.json').read_text())
    selected = _selection(run, b_output, manifest, a_receipt)
    H, free, cache_hash = _code(run, b_output)
    rows = [json.loads(line) for line in ledger_path.open()]
    expected_keys = {(observation_id, arm) for observation_id in selected for arm in ARMS}
    keys = [(row.get('observation_id'), row.get('arm')) for row in rows]
    _require(len(rows) == 512 and len(set(keys)) == 512 and set(keys) == expected_keys,
             'B ledger does not contain exactly 64 by 8 attempts')
    truth_cache = {}
    checkpoint_count = 0
    replay_maximum = 0.0
    recounted = []
    for row in rows:
        observation_id, arm = row['observation_id'], row['arm']
        selected_row = selected[observation_id]
        record = selected_row['baseline_record']
        _require(row['status'] == 'ok' and row['frame'] == selected_row['frame']
                 and row['baseline_error'] == selected_row['baseline_error'],
                 f'B outcome group or status differs: {observation_id}/{arm}')
        if observation_id not in truth_cache:
            truth_cache[observation_id] = _artifact(
                run / 'frames' / f'{observation_id}_truth.npz', selected_row['truth_sha256'])
        truth = truth_cache[observation_id]
        identity = dict(schema='tf-production-gap-audit/1', observation_id=observation_id,
                        arm=arm, input_sha256=selected_row['input_sha256'])
        payload = _artifact(_within(b_output, row['path']), row['artifact_sha256'], identity)
        _require(set(payload) == {'decoder', 'arrays', 'timing', 'trace'},
                 f'B arm payload fields differ: {observation_id}/{arm}')
        checkpoints = row['checkpoints']
        expected_rounds = 3 if arm == 'J20R3' else 2
        _require(len(checkpoints) == expected_rounds and
                 [cp['round'] for cp in checkpoints] == list(range(expected_rounds)),
                 f'B checkpoint allocation differs: {observation_id}/{arm}')
        for checkpoint in checkpoints:
            round_index = checkpoint['round']
            saved = _artifact(_within(b_output, checkpoint['path']),
                              checkpoint['artifact_sha256'], dict(identity, round=round_index))
            _require(set(saved) == {'event', 'decoded'},
                     f'B checkpoint payload fields differ: {observation_id}/{arm}/r{round_index}')
            decoded = _bits(saved['decoded'], H.shape[1], 'checkpoint decoded')
            _require(np.array_equal(decoded, _bits(payload['arrays'][f'r{round_index}_decoded'],
                                                  H.shape[1], 'arm decoded')),
                     f'B arm/checkpoint decoded differ: {observation_id}/{arm}/r{round_index}')
            counts = _counts(decoded, truth, H, free)
            _require(counts == {key: checkpoint[key] for key in counts},
                     f'B checkpoint recount differs: {observation_id}/{arm}/r{round_index}')
            _require(saved['event']['round'] == round_index
                     and checkpoint['event'] == {key: value for key, value in saved['event'].items()
                                                 if key != 'snapshot'},
                     f'B checkpoint event differs: {observation_id}/{arm}/r{round_index}')
            checkpoint_count += 1
        final_bits = _bits(payload['decoder']['decoded'], H.shape[1], 'final decoded')
        _require(np.array_equal(final_bits, _bits(payload['arrays'][f'r{expected_rounds-1}_decoded'],
                                                H.shape[1], 'final arm decoded')),
                 f'B final decoded differs: {observation_id}/{arm}')
        final_counts = _counts(final_bits, truth, H, free)
        _require(final_counts == {key: row[key] for key in final_counts},
                 f'B final recount differs: {observation_id}/{arm}')
        rescue = bool(selected_row['baseline_error'] and final_counts['info_errors'] == 0)
        harm = bool(not selected_row['baseline_error'] and final_counts['info_errors'] > 0)
        _require(row['rescue'] == rescue and row['harm'] == harm,
                 f'B rescue/harm differs: {observation_id}/{arm}')
        if arm == 'baseline_replay':
            _require(receipt['baseline_replay_hashes'][observation_id] == row['artifact_sha256'],
                     f'B replay receipt hash differs: {observation_id}')
            difference = _replay_difference(run, record, payload, H, free, truth)
            _require(row['max_continuous_replay_difference'] == difference,
                     f'B replay difference ledger differs: {observation_id}')
            replay_maximum = max(replay_maximum, difference)
        recounted.append(dict(arm=arm, info_errors=final_counts['info_errors'],
                              baseline_error=selected_row['baseline_error'],
                              rescue=rescue, harm=harm,
                              complete_seconds=row['complete_seconds']))
    _require(checkpoint_count == 1088, 'B checkpoint count differs')
    _require(len(receipt['baseline_replay_hashes']) == 64 and replay_maximum == 0.0,
             'B baseline replay count or maximum differs')
    summary = {arm: dict(calls=sum(row['arm'] == arm for row in recounted),
                         rescues=sum(row['rescue'] for row in recounted if row['arm'] == arm),
                         harms=sum(row['harm'] for row in recounted if row['arm'] == arm),
                         remaining_selected_failures=sum(row['info_errors'] > 0 and row['baseline_error']
                                                         for row in recounted if row['arm'] == arm),
                         complete_seconds_total=sum(row['complete_seconds'] for row in recounted
                                                    if row['arm'] == arm)) for arm in ARMS}
    _require(summary == json.loads((b_output / 'summary.json').read_text()),
             'B summary recount differs')
    result = dict(status='pass', receiver_calls_added=0, receiver_calls_verified=512,
                  arm_artifacts_verified=512, checkpoints_verified=checkpoint_count,
                  original_baseline_checkpoints_verified=128,
                  selected_observations=64, baseline_replay_maximum_difference=replay_maximum,
                  ledger_sha256=receipt['ledger_sha256'], code_cache_sha256=cache_hash,
                  summary=summary)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--b-output', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run, args.b_output, args.out), indent=2))


if __name__ == '__main__':
    main()
