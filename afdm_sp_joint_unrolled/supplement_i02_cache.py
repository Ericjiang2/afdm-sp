"""Content-bound I0 caches and retrospective I-02 lineage checks, with no F/E/T."""
import json
from pathlib import Path

import numpy as np

from .afdm_baselines import construct_sensing_matrix
from .budgeted_support_diagnostics import array_hash
from .direction_factorial import residual_ledger
from .e1_ldpc import extract_info
from .supplement_data import CAMPAIGN_ID
from .supplement_profile import score_errors
from .supplement_run import sha

SCHEMA = 'supplement-i02-recovery-manifest-v1'
ARMS = ('I02-baseline', 'I02-scalar', 'I02-diagonal', 'I02-lowrank')
RECIPE = 'B0-p2-s0.5'


def file_binding(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def checked_path(binding):
    path = Path(binding['path'])
    if (not path.is_absolute() or not path.is_file() or sha(path) != binding['sha256']
            or path.stat().st_size != binding['bytes']):
        raise ValueError('I-02 cached file hash/size mismatch: ' + str(path))
    return path


def validate_identities(frames):
    sequence = [(row['block'], row['snr']) for row in frames]
    expected = {(block, snr) for block in range(192) for snr in (7, 8, 9)}
    if (any(type(v) is not int for key in sequence for v in key)
            or len(sequence) != len(set(sequence)) or set(sequence) != expected):
        raise ValueError('I-02 recovery identity grid must be exactly 192 blocks at 7/8/9')


def build_manifest(audit_path, i02_root, *, protocol_sha256, checkpoint_sha256):
    audit = json.loads(Path(audit_path).read_text())
    if audit.get('status') != 'passed' or audit.get('F_audited') != 3456:
        raise ValueError('complete original I-01 raw audit required')
    inputs = audit['bindings']['files']
    if inputs['protocol'] != protocol_sha256 or inputs['checkpoint'] != checkpoint_sha256:
        raise ValueError('original I-01 input binding mismatch')
    frames, source_batches = [], []
    i02_rows = {}
    for batch in sorted(Path(i02_root).glob('batch-*')):
        contract = json.loads((batch / 'contract.json').read_text())
        summary = json.loads((batch / 'summary.json').read_text())
        if (contract.get('stage') != 'I-02' or contract.get('split') != 'design'
                or contract.get('recipe_id') != RECIPE or contract.get('arms') != list(ARMS)
                or contract.get('protocol_sha256') != protocol_sha256
                or contract.get('checkpoint_sha256') != checkpoint_sha256
                or summary.get('status') != 'complete' or summary.get('exitcode') != 0
                or summary.get('failures')
                or summary['calls_attempted'] != summary['calls_completed']):
            raise ValueError('invalid original I-02 batch')
        source_batches.extend(file_binding(batch / n) for n in ('contract.json', 'summary.json'))
        for block in range(contract['start'], contract['stop']):
            for snr in contract['snrs']:
                key = (block, snr)
                if key in i02_rows:
                    raise ValueError('overlapping original I-02 batches')
                i02_rows[key] = {arm: file_binding(batch / f'frame-{snr}-{block:03d}-{arm}.json')
                                 for arm in ARMS}
    if len(i02_rows) != 576:
        raise ValueError('missing original I-02 identities')
    for batch in audit['batches']:
        root = Path(batch['root'])
        for name in ('contract', 'summary'):
            binding = file_binding(root / (name + '.json'))
            if binding['sha256'] != batch[name + '_sha256']:
                raise ValueError('audited original I-01 batch changed')
            source_batches.append(binding)
        summary = json.loads((root / 'summary.json').read_text())
        record_map = {tuple(row['identity']): row for row in summary['records']}
        for proof in batch['proofs']:
            block, snr, arm = proof['identity']
            if arm != 'I0':
                continue
            binding = file_binding(record_map[(block, snr, arm)]['path'])
            if binding['sha256'] != proof['record_sha256']:
                raise ValueError('audited original I0 record changed')
            record = json.loads(checked_path(binding).read_text())
            terminal = file_binding(record['terminal']['path'])
            if terminal['sha256'] != proof['terminal_sha256']:
                raise ValueError('audited original I0 terminal changed')
            frames.append(dict(block=block, snr=snr, record=binding, terminal=terminal,
                               original_i02=i02_rows[(block, snr)]))
    frames.sort(key=lambda row: (row['block'], row['snr']))
    validate_identities(frames)
    return dict(schema=SCHEMA, campaign_id=CAMPAIGN_ID, frames=frames,
        source_batches=source_batches, original_audit=file_binding(audit_path),
        protocol_sha256=protocol_sha256, checkpoint_sha256=checkpoint_sha256,
        recipe_id=RECIPE, code_sha256=audit['code_sha256'],
        scope='retrospective cache binding; old missing producer-time evidence remains missing')


def load_inputs(row):
    record = json.loads(checked_path(row['record']).read_text())
    path = checked_path(row['terminal'])
    if record['terminal']['sha256'] != row['terminal']['sha256']:
        raise ValueError('original terminal producer hash mismatch')
    with np.load(path, allow_pickle=False) as archive:
        snapshot = {k: archive[k] for k in archive.files}
    old = {arm: json.loads(checked_path(binding).read_text())
           for arm, binding in row['original_i02'].items()}
    if record['identity'] != [row['block'], row['snr'], 'I0']:
        raise ValueError('cached record identity mismatch')
    return snapshot, record, old


def validate_lineage(snapshot, record, old, frame, system, code):
    """Only regenerate/hash sensing matrices. No fit, covariance or detector call."""
    s = snapshot
    block, snr, arm = record['identity']
    if (arm != 'I0' or record['baseline_recipe'] != RECIPE
            or record['truth_access_level'] != 'none' or record['decoder_checkpoint_records']
            or record['diagnostic_consumption_records']):
        raise ValueError('cache is not the original legal I0 state')
    if (any(not np.isfinite(v).all() for v in s.values())
            or s['H'].shape != (system.N_total, system.N_total)
            or code['n'] != 2*system.N_total
            or not np.array_equal(s['info_hat'], extract_info(code, s['decoded']))):
        raise ValueError('invalid original I0 terminal arrays')
    if frame.metadata['input_hashes'] != record['input_hashes']:
        changed = [k for k in record['input_hashes']
                   if record['input_hashes'][k] != frame.metadata['input_hashes'].get(k)]
        raise ValueError('regenerated exogenous hashes differ: ' + ','.join(changed))
    for key in ('y', 'pilot', 'info', 'coded'):
        if array_hash(s[key]) != record['input_hashes'][key]:
            raise ValueError('cached exogenous hash differs: ' + key)
    if (not np.array_equal(s['constellation'], frame.observed['constellation'])
            or not np.array_equal(s['sigma2_thermal'], frame.observed['sigma2'])):
        raise ValueError('cached public power/noise configuration differs')
    score = score_errors(s, s)
    if any(record.get(k) != v for k, v in score.items()):
        raise ValueError('original I0 errors differ from saved arrays')
    if any(old['I02-baseline'].get(k) != v for k, v in score.items()):
        raise ValueError('original I-02 baseline errors differ from audited I0')
    ids = np.asarray(s['support'])
    pilot, x_soft = [np.asarray(s[k], dtype=np.complex128) for k in ('pilot', 'x_soft')]
    def sensing(value):
        return construct_sensing_matrix(system.N_total, value, system.c1, system.c2,
                                         system.l_max_cap, system.k_max_cap)[:, ids]
    matrix_hashes = dict(A_sha256=array_hash(sensing(pilot + x_soft)),
                         P_sha256=array_hash(sensing(pilot)))
    for name, row in old.items():
        if (row['arm_id'] != name or row['block_id'] != block or row['SNR'] != snr
                or row['truth_access_level'] != 'none' or row['recipe_id'] != RECIPE):
            raise ValueError('original I-02 identity/provenance mismatch')
        if name == 'I02-baseline':
            continue
        diag = row['cancellation']
        for key, value in matrix_hashes.items():
            if diag[key] != value:
                raise ValueError('original I-02 ' + name + ' differs at ' + key)
        if (diag['support'] != ids.tolist()
                or diag['sigma_base'] != float(s['sigma2_terminal'])
                or diag['mode'] != name.removeprefix('I02-') or diag['truth_access'] != 'none'):
            raise ValueError('original I-02 cancellation support/noise/mode mismatch')
    diagnostic = dict(s, Htrue=frame._truth['H'], data=frame._truth['data'],
                      noise=frame._truth['noise'])
    ledger = residual_ledger(diagnostic, s['H'], s['H'])
    return dict(exogenous_hashes_match=True, matched_cancellation_modes=3,
        matrix_hashes=matrix_hashes, baseline_scores=score, residual_closure=ledger,
        cached_array_hashes={k: array_hash(v) for k, v in s.items()}, calls=dict(F=0, E=0, T=0),
        limitation='I-02 did not save H or decoded arrays; matching its hashes/counts is not bitwise terminal proof')
