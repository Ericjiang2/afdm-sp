"""Strict frame records for the direction campaign; truth stays in offline audit."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


REQUIRED_FIELDS = {
    'run_id', 'split', 'block_id', 'channel_seed', 'data_seed', 'noise_seed',
    'code_id', 'interleaver_id', 'SNR', 'rho', 'P_phys', 'generator_id', 'truncation_id',
    'source_sha256', 'config_sha256', 'prior_sha256', 'device', 'dtype',
    'library_versions', 'deterministic_flags', 'raw_y_hash', 'pilot_hash', 'H_true_hash',
    'truth_access_level', 'arm_id', 'H_cancel_source', 'H_data_source', 'H_cov_source',
    'sigma_source', 'sigma_value', 'pilot_cancellation_identity_check',
    'S_initial', 'S_submitted', 'K_nominal', 'K_effective', 'physical_group_count',
    'graph_edges_each_stage', 'raw_bit_errors', 'coded_bit_errors', 'FER',
    'hard_output_hash', 'decoder_status', 'channel_error', 'posterior_audit',
    'pilot_residual', 'data_residual', 'message_confidence', 'call_type',
    'elapsed_seconds', 'peak_gpu_bytes', 'failure', 'retry_of', 'snapshot',
    'input_hashes', 'protocol_sha256', 'rng_words',
}


def confidence_groups(llr,coded):
    """Fixed confidence bins, frozen before design data; offline bit error audit."""
    edges=(0.,math.log(3),math.log(9),math.log(99),math.inf)
    rows=[dict(lower_abs_llr=edges[i],upper_abs_llr=edges[i+1] if i<3 else None,
               bits=0,errors=0) for i in range(4)]
    if len(llr)!=len(coded):raise ValueError('LLR/truth lengths differ')
    for value,bit in zip(llr,coded):
        if not math.isfinite(float(value)) or bit not in (0,1):
            raise ValueError('invalid offline confidence input')
        index=next(i for i in range(4) if abs(value)<edges[i+1])
        rows[index]['bits']+=1
        rows[index]['errors']+=int((value<0)!=bool(bit))
    return dict(rule='absolute LLR bins with hard confidence .5/.75/.9/.99; lower-inclusive',
                bins=rows,scope='offline calibration diagnostic; not selection thresholds')


def validate_record(record, *, expected_inputs=None, deployable=False):
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        raise ValueError(f'missing frame audit fields: {sorted(missing)}')
    if record['split'] not in ('engineering', 'design', 'mechanism', 'confirm', 'counterexample', 'timing'):
        raise ValueError('legacy or unknown split cannot enter direction results')
    if record['truth_access_level'] not in ('none', 'geometry_oracle', 'data_oracle', 'CSI_oracle'):
        raise ValueError('unknown truth access level')
    if deployable and record['truth_access_level'] != 'none':
        raise ValueError('truth-bearing arm cannot enter deployable registry')
    if type(record['block_id']) is not int or record['block_id'] < 0:
        raise ValueError('invalid independent block identity')
    if record['call_type'] not in ('full', 'terminal', 'CE'):
        raise ValueError('call type must be accounted separately')
    for key in ('S_initial', 'S_submitted'):
        ids = record[key]
        if (not isinstance(ids, list) or any(type(i) is not int or not 0 <= i < 515 for i in ids)
                or len(set(ids)) != len(ids) or len(ids) > 40):
            raise ValueError(f'invalid capacity/atom IDs: {key}')
    if record['K_nominal'] != len(record['S_submitted']):
        raise ValueError('nominal support count mismatch')
    if not 0 <= record['K_effective'] <= record['K_nominal']:
        raise ValueError('effective support exceeds nominal support')
    for key in ('raw_bit_errors', 'coded_bit_errors'):
        if type(record[key]) is not int or record[key] < 0:
            raise ValueError(f'invalid error count: {key}')
    if record['FER'] not in (0, 1):
        raise ValueError('FER must be a binary per-frame event')
    for key, source in (('raw_y_hash','y'),('pilot_hash','pilot'),('H_true_hash','H')):
        if record[key] != record['input_hashes'][source]:
            raise ValueError('top-level hash disagrees with exogenous input record')
    if record['FER'] != int(record['coded_bit_errors'] > 0):
        raise ValueError('FER must match decoded information-bit errors')
    if expected_inputs is not None and record['input_hashes'] != expected_inputs:
        raise ValueError('unpaired exogenous frame inputs')
    if record['elapsed_seconds'] < 0 or record['peak_gpu_bytes'] < 0 or record['sigma_value'] <= 0:
        raise ValueError('invalid cost or variance')
    json.dumps(record, allow_nan=False)
    return record


def publish_snapshot(path, arrays):
    """Immutable evidence; not a receiver input capability."""
    import numpy as np
    path = Path(path)
    if any(np.asarray(a).dtype.hasobject for a in arrays.values()):
        raise ValueError('snapshot must not contain pickled object arrays')
    with path.open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope': 'offline evidence with truth; observed receiver does not receive this path'}


def validate_pair(rows):
    if not rows:
        raise ValueError('empty paired comparison')
    first = rows[0]
    for row in rows:
        validate_record(row, expected_inputs=first['input_hashes'])
        if (row['split'], row['block_id'], row['SNR'], row['protocol_sha256']) != (
                first['split'], first['block_id'], first['SNR'], first['protocol_sha256']):
            raise ValueError('mixed paired comparison identity')
    if len({r['arm_id'] for r in rows}) != len(rows):
        raise ValueError('duplicate arm in paired comparison')
