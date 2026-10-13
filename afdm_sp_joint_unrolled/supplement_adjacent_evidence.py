"""Read immutable adjacent-study arrays and verify them before any analysis."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.supplement_scope import validate_history


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def array_references(value):
    if isinstance(value, dict):
        if set(value) == {'array', 'shape', 'dtype', 'sha256'}:
            yield value
        else:
            for item in value.values():
                yield from array_references(item)
    elif isinstance(value, list):
        for item in value:
            yield from array_references(item)


def load_raw(raw, root, index=None):
    """Verify file and every array, then restore the collector's nested value."""
    path = Path(raw['file']['path']).resolve()
    path.relative_to(Path(root).resolve())
    if path.stat().st_size != raw['file']['bytes'] or file_sha(path) != raw['file']['sha256']:
        raise ValueError('raw file size/hash changed: ' + str(path))
    references = list(array_references(raw['metadata']))
    names = [item['array'] for item in references]
    if not references or len(set(names)) != len(names):
        raise ValueError('empty or repeated raw array references')
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != set(names):
            raise ValueError('raw array inventory differs')
        arrays = {}
        for ref in references:
            value = archive[ref['array']]
            if (list(value.shape) != ref['shape'] or str(value.dtype) != ref['dtype']
                    or value.dtype.hasobject or not np.isfinite(value).all()
                    or array_hash(value) != ref['sha256']):
                raise ValueError('raw dtype/shape/content differs: ' + ref['array'])
            arrays[ref['array']] = value

    def restore(value):
        if isinstance(value, dict):
            if set(value) == {'array', 'shape', 'dtype', 'sha256'}:
                return arrays[value['array']]
            if set(value) == {'complex_real', 'complex_imag'}:
                return complex(value['complex_real'], value['complex_imag'])
            return {key: restore(item) for key, item in value.items()}
        if isinstance(value, list):
            return [restore(item) for item in value]
        return value

    if index is not None:
        index.append(dict(path=str(path), bytes=path.stat().st_size,
            sha256=raw['file']['sha256'], arrays=references))
    return restore(raw['metadata'])


def validate_input(raw, frame):
    observed, truth = raw['observed'], raw['truth']
    if set(observed) != {'y', 'pilot', 'sigma2', 'constellation'}:
        raise ValueError('observed data boundary contains undeclared fields')
    actual = {name: array_hash((observed if name in observed else truth)[name])
              for name in ('y', 'H', 'info', 'coded', 'noise', 'pilot', 'data')}
    if actual != frame['input_hashes']:
        raise ValueError('frame identity does not match its actual arrays')
    return {key: actual[key] for key in ('H', 'info', 'coded', 'pilot', 'data')}


def validate_errors(result, truth, scores):
    info, coded = truth['info'], truth['coded']
    if result['info_hat'].shape != info.shape or result['decoded'].shape != coded.shape:
        raise ValueError('error-vector denominator differs')
    error = result['info_hat'] != info
    code_error = result['decoded'] != coded
    if (not np.array_equal(error, result['info_error_vector'])
            or not np.array_equal(code_error, result['code_error_vector'])
            or int(error.sum()) != scores['coded_bit_errors']
            or int(error.any()) != scores['FER']):
        raise ValueError('external error score or saved vector differs')
    return dict(bit_errors=int(error.sum()), bits=int(error.size),
        frame_error=int(error.any()), codeword_errors=int(code_error.sum()),
        codeword_bits=int(code_error.size))


def audit_development(root, out):
    """Audit all 256 I1 records; this entry never opens confirmation labels."""
    root, out = Path(root), Path(out)
    batch = root / 'development-i1-gpu'
    run = json.loads((batch / 'run.json').read_text())
    closure = json.loads((batch / 'complete.json').read_text())
    if ((root / 'development-i1-gpu.exit').read_text().strip() != '0'
            or closure['completed_F'] != 256 or closure['attempted_F'] != 256
            or run['data_range'] != [192, 320] or run['snrs'] != [7, 8]
            or run['arms'] != ['I1'] or run['purpose'] != 'development'):
        raise ValueError('development collection is incomplete or outside the design')
    manifest_path = root / 'development-i1-admission-v1.json'
    if file_sha(manifest_path) != run['manifest_sha256']:
        raise ValueError('development manifest content changed')
    manifest = json.loads(manifest_path.read_text())
    validate_history(manifest)
    expected = {f'b{block:06d}-s{snr}' for block in range(192, 320) for snr in (7, 8)}
    if {path.name for path in batch.glob('b*-s*')} != expected:
        raise ValueError('development cell inventory differs')
    index, records, stable, states = [], [], {}, 0
    started = time.time()
    for block in range(192, 320):
        for snr in (7, 8):
            cell = batch / f'b{block:06d}-s{snr}'
            input_meta = json.loads((cell / 'input.json').read_text())
            frame = input_meta['frame']
            if (frame['block'], frame['snr_db'], frame['split'], frame['family']) != (block, snr, 'design', None):
                raise ValueError('development data identity differs')
            inputs = load_raw(input_meta['raw'], root, index)
            exogenous = validate_input(inputs, frame)
            if block in stable and exogenous != stable[block]:
                raise ValueError('cross-SNR exogenous pairing differs')
            stable[block] = exogenous
            metadata = json.loads((cell / 'I1-r0.json').read_text())
            if (metadata['identity'] != dict(block=block, snr_db=snr, arm='I1', repeat=0)
                    or metadata['input_hashes'] != frame['input_hashes']
                    or metadata['rng_before'] != metadata['rng_after']):
                raise ValueError('I1 identity, pairing or RNG changed')
            values = load_raw(metadata['raw'], root, index)
            result = values['result']
            errors = validate_errors(result, inputs['truth'], metadata['scores'])
            if result['source_sha256'] != manifest['source_manifest']:
                raise ValueError('I1 receiver source differs from admission')
            captured = values['bp_input_states']
            expected_iterations = [3, 7] if 192 <= block < 224 or 256 <= block < 288 else []
            if [state['outer_iter'] for state in captured] != expected_iterations:
                raise ValueError('local states differ from the blind sampling rule')
            states += len(captured)
            operators = {}
            for item in metadata['profile']:
                if item['status'] != 'complete':
                    raise ValueError('failed profiled operator')
                row = operators.setdefault(item['operator'], dict(seconds=0., calls=0))
                row['seconds'] += item['seconds']
                row['calls'] += 1
            records.append(dict(block=block, snr_db=snr,
                partition='fit' if block < 256 else 'heldout', **errors,
                seconds=metadata['seconds'], CPU_seconds=metadata['CPU_seconds'],
                transfer_seconds=result['transfer_seconds'], profile=operators,
                active_atoms=len(result['support']),
                final_graph_edges=int(np.count_nonzero(np.abs(result['H'].astype(np.complex128)) >= 1e-4)),
                physical_paths=int(inputs['truth']['params']['taps']),
                precision=dict(input_y=str(inputs['observed']['y'].dtype),
                    estimated_H=str(result['H'].dtype), terminal_mu=str(result['mu'].dtype),
                    terminal_var=str(result['var'].dtype),
                    saved_BP_H=sorted({str(state['H'].dtype) for state in captured})),
                input_meta_sha256=file_sha(cell / 'input.json'),
                result_meta_sha256=file_sha(cell / 'I1-r0.json')))
    if states != 256:
        raise ValueError('expected exactly 256 prelisted BP-input states')
    report = dict(schema='adjacent-development-audit-v1', status='raw_integrity_passed',
        completed_F=256, attempted_F=256, raw_files=len(index),
        raw_arrays=sum(len(item['arrays']) for item in index), local_states=states,
        blocks=128, snrs=[7, 8], fit_blocks=[192, 256], heldout_blocks=[256, 320],
        audit_seconds=time.time() - started, observed_at_unix=time.time(),
        run_sha256=file_sha(batch / 'run.json'), complete_sha256=file_sha(batch / 'complete.json'),
        records=records,
        precision_note='Frozen mixed precision: outer C64/F32; Torch BP C128/F64; host input C128. The source-v1 run.json generic C128/F64 label is incomplete, not a precision change.',
        timing_note='Concurrent inclusive instrumented times; nested operators must not be summed; not COST-02.',
        confirmation_outcomes='not opened')
    out.mkdir(exist_ok=False)
    publish_json(out / 'audit.json', report)
    with gzip.open(out / 'array-index.json.gz', 'xt') as handle:
        json.dump(index, handle, separators=(',', ':'), allow_nan=False)
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    audit_development(args.root, args.out)
