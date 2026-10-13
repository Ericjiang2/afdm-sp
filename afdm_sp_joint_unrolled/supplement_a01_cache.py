"""Immutable A-01 full-state lineage for estimator/terminal replay only."""
from pathlib import Path
import json

import numpy as np

from .budgeted_support_diagnostics import array_hash
from .direction_factorial import residual_ledger
from .e1_ldpc import extract_info
from .supplement_data import CAMPAIGN_ID, LIMITS
from .supplement_run import sha

SCHEMA = 'supplement-a01-cache-manifest-v1'
RELATIVE_REGEN_TOLERANCE = 1e-12


def file_binding(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def checked_path(binding):
    path = Path(binding['path'])
    if not path.is_absolute() or not path.is_file() or sha(path) != binding['sha256']:
        raise ValueError('A-01 cached file hash mismatch: ' + str(path))
    return path


def build_manifest(root, *, protocol_sha256, d1_sha256, recipe_id, checkpoint_sha256):
    """Hash all source states/cells without evaluating an estimator or decoder."""
    root = Path(root).resolve()
    frames = []
    bindings = dict(protocol_sha256=protocol_sha256, d1_sha256=d1_sha256,
                    recipe_id=recipe_id, checkpoint_sha256=checkpoint_sha256)
    for batch in sorted(root.glob('batch-*')):
        if not batch.is_dir():
            continue
        contract = json.loads((batch / 'contract.json').read_text())
        summary = json.loads((batch / 'summary.json').read_text())
        if (contract.get('campaign_id') != CAMPAIGN_ID or contract.get('stage') != 'A-01'
                or contract.get('split') != 'mechanism'
                or any(contract.get(k) != v for k, v in bindings.items())
                or summary.get('status') != 'complete' or summary.get('exitcode') != 0
                or summary.get('failures') or (batch / 'batch-failure.json').exists()
                or summary['calls_attempted'] != summary['calls_completed']):
            raise ValueError('invalid original A-01 batch: ' + str(batch))
        contract_binding = file_binding(batch / 'contract.json')
        summary_binding = file_binding(batch / 'summary.json')
        for block in range(contract['start'], contract['stop']):
            for snr in contract['snrs']:
                prefix = f'{snr}-{block:06d}'
                cells = {f'{arm}__{det}': file_binding(batch / f'cell-{prefix}-{arm}-{det}.json')
                         for arm in contract['arms'] for det in contract['detectors']}
                frames.append(dict(block=block, snr=snr, source_contract=contract_binding,
                    source_summary=summary_binding,
                    snapshot=file_binding(batch / f'snapshot-{prefix}.npz'),
                    normal=file_binding(batch / f'normal-full-{prefix}.json'), cells=cells))
    manifest = dict(schema=SCHEMA, campaign_id=CAMPAIGN_ID, source_root=str(root),
        frames=frames, **bindings,
        scope='retrospective hash binding; cached development states, no new independent F')
    _validate_identities(manifest)
    return manifest


def _validate_identities(manifest):
    seen = set()
    for row in manifest['frames']:
        key = (row['block'], row['snr'])
        if any(type(v) is not int for v in key) or key in seen:
            raise ValueError('duplicate or invalid A-01 cache identity')
        seen.add(key)
    expected = {(b, s) for b in range(LIMITS['mechanism']) for s in (7, 8, 9)}
    if seen != expected:
        raise ValueError('A-01 cache must contain exactly 768 original mechanism states')


def load_manifest(path, **expected):
    manifest = json.loads(Path(path).read_text())
    if (manifest.get('schema') != SCHEMA or manifest.get('campaign_id') != CAMPAIGN_ID
            or any(manifest.get(k) != v for k, v in expected.items())):
        raise ValueError('A-01 replay manifest binding mismatch')
    _validate_identities(manifest)
    root = Path(manifest['source_root']).resolve()
    for row in manifest['frames']:
        for binding in [row[k] for k in ('source_contract', 'source_summary', 'snapshot', 'normal')] + list(row['cells'].values()):
            if not Path(binding['path']).resolve().is_relative_to(root):
                raise ValueError('A-01 source path outside immutable run root')
    return manifest


def validate_snapshot(snapshot, frame, code):
    """Validate reconstructed geometry against the actual cached observations."""
    s = snapshot
    n = code['n'] // 2
    shapes = dict(Hhat=(n, n), Htrue=(n, n), y=(n,), pilot=(n,), data=(n,),
                  x_soft=(n,), noise=(n,), sigma2_thermal=(), sigma2_terminal=(),
                  constellation=(4,), info=(code['k'],), coded=(code['n'],),
                  decoded=(code['n'],))
    if any(k not in s or np.asarray(s[k]).shape != shape for k, shape in shapes.items()):
        raise ValueError('invalid cached A-01 state dimensions')
    if any(not np.isfinite(np.asarray(value)).all() for value in s.values()):
        raise ValueError('cached A-01 state must be finite')
    ids = np.asarray(s['support'])
    if (ids.ndim != 1 or ids.dtype.kind not in 'iu' or len(set(ids.tolist())) != len(ids)
            or np.any(ids < 0) or np.any(ids >= 515) or len(ids) > 40
            or np.asarray(s['gains']).shape != ids.shape):
        raise ValueError('invalid cached A-01 support/gain state')
    for key in ('sigma2_thermal', 'sigma2_terminal'):
        if np.iscomplexobj(s[key]) or s[key] <= 0:
            raise ValueError('cached scalar variance must be positive')
    for key in ('info', 'coded', 'decoded'):
        if np.any((s[key] != 0) & (s[key] != 1)):
            raise ValueError('cached bits must be binary')
    for key in ('data', 'noise', 'info', 'coded'):
        if not np.array_equal(s[key], frame._truth[key]):
            raise ValueError('cached exogenous ' + key + ' differs from frozen source')
    for key in ('pilot', 'constellation'):
        if not np.array_equal(s[key], frame.observed[key]):
            raise ValueError('cached exogenous ' + key + ' differs from frozen source')
    if not np.array_equal(s['sigma2_thermal'], frame.observed['sigma2']):
        raise ValueError('cached thermal scale differs from frozen source')
    relative = {}
    for key, expected in (('Htrue', frame._truth['H']), ('y', frame.observed['y'])):
        relative[key] = float(np.linalg.norm(s[key] - expected) / max(1., np.linalg.norm(expected)))
        if relative[key] > RELATIVE_REGEN_TOLERANCE:
            raise ValueError('cached observation/geometry reconstruction mismatch: ' + key)
    residual_ledger(s, s['Hhat'], s['Hhat'])
    return dict(exact_exogenous_arrays=True, regenerated_relative_errors=relative,
        regeneration_tolerance=RELATIVE_REGEN_TOLERANCE,
        actual_cached_input_hashes={k: array_hash(v) for k, v in s.items()},
        observation_policy='consume original cached arrays; regenerate omitted truth geometry only')


def read_state(record, frame, code):
    for key in ('source_contract', 'source_summary'):
        checked_path(record[key])
    path = checked_path(record['snapshot'])
    with np.load(path, allow_pickle=False) as arrays:
        snapshot = {k: arrays[k] for k in arrays.files}
    proof = validate_snapshot(snapshot, frame, code)
    normal = json.loads(checked_path(record['normal']).read_text())
    errors = int(np.count_nonzero(extract_info(code, snapshot['decoded']) != snapshot['info']))
    if (normal['block_id'] != record['block'] or normal['SNR'] != record['snr']
            or normal['coded_bit_errors'] != errors or normal['FER'] != int(errors > 0)
            or normal['support'] != snapshot['support'].tolist()):
        raise ValueError('original full result does not match saved A-01 state')
    old_cells = {}
    for name, binding in record['cells'].items():
        row = json.loads(checked_path(binding).read_text())
        if (row['block_id'] != record['block'] or row['SNR'] != record['snr']
                or name != f"{row['arm']}__{row['detector']}"
                or row['FER'] != int(row['info_errors'] > 0)):
            raise ValueError('invalid original A-01 terminal record')
        old_cells[name] = row
    return snapshot, proof, old_cells
