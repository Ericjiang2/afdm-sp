"""Read sealed old observations; no receiver calls and no remote filesystem writes.

Run with stdin on the original host, stdout redirected by the local caller.
Thresholds are descriptive binning chosen before this extraction, not a gate.
Observed states are all bound/extracted before any truth is loaded.
"""
from pathlib import Path
import hashlib
import json
import os
import sys

import numpy as np


ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
OBS = ROOT / 'results/cstate_necessity_stageA_20260928/observed'
POP = ROOT / 'results/tf_cstate_prospective_20260923/population_observed'
TRUTH = ROOT / 'results/tf_cstate_prospective_20260923/population_truth'
sys.path.insert(0, str(ROOT / 'experiments/sp_afdm_frozen_reviewed_20260921/src'))
import evidence


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ledger(root):
    seal = json.loads((root / 'observed_seal.json').read_text())
    path = root / 'ledger.jsonl'
    assert seal['status'] == 'pass'
    assert seal['files']['ledger.jsonl'] == sha(path)
    return [json.loads(x) for x in path.read_text().splitlines()], seal


def bound(root, relative, digest, seal):
    relative = Path(relative)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert seal['files'][str(relative)] == digest
    path = root / relative
    assert sha(path) == digest
    return evidence.load_artifact(path)[0]


def proximity(delays, dopplers):
    delays, dopplers = np.asarray(delays), np.asarray(dopplers)
    distances = [float(abs(dopplers[i] - dopplers[j]))
                 for i in range(len(delays)) for j in range(i)
                 if delays[i] == delays[j]]
    return {'slots': len(delays), 'distinct_delays': len(np.unique(delays)),
            'same_delay_pair_count': len(distances),
            'same_delay_min_gap': min(distances, default=None),
            'pairs_gap_le_025': sum(x <= .25 for x in distances),
            'pairs_gap_le_05': sum(x <= .5 for x in distances),
            'pairs_gap_le_1': sum(x <= 1. for x in distances)}


def closure(gamma, gains):
    gamma, gains = np.asarray(gamma), np.asarray(gains)
    p = len(gains)
    s = float(np.trace(gamma).real / p)
    e = gamma - s * np.eye(p)
    denominator = max(np.linalg.norm(gamma), np.finfo(float).tiny)
    direction_denominator = max(s * np.linalg.norm(gains), np.finfo(float).tiny)
    return {'trace_mean_s': s,
            'nonscalar_fro_ratio': float(np.linalg.norm(e) / denominator),
            'directional_eh_over_sh': float(np.linalg.norm(e @ gains) / direction_denominator),
            'quadratic_eh_over_sh2': float(np.vdot(gains, e @ gains).real /
                                         max(s * np.vdot(gains, gains).real, np.finfo(float).tiny)),
            'hermitian_residual': float(np.linalg.norm(gamma - gamma.conj().T))}


def unpack(value):
    # This campaign stores uncompressed uint8 truth, unlike older Part-B artifacts.
    bits = np.asarray(value)
    assert bits.shape == (2048,) and bits.dtype == np.uint8
    assert np.isin(bits, (0, 1)).all()
    return bits


def main():
    rows, seal = ledger(OBS)
    population, population_seal = ledger(POP)
    population = {r['observation_id']: r for r in population if r['snr_centi_db'] == 650}
    by = {(r['observation_id'], r['arm']): r for r in rows}
    assert len(rows) == 4108 and len(by) == 4108 and len(population) == 1024
    extracted, decisions = [], {}
    for frame in range(1024):
        stem = f's650_f{frame:04d}'
        inp = population[stem]
        item = {'observation_id': stem, 'frame': frame,
                'input_sha256': inp['observation_sha256'],
                'observation_hash': inp['observation_hash'], 'arms': {}}
        decisions[stem] = {}
        for arm in ('A', 'C'):
            row = by[stem, arm]
            assert row['status'] == 'ok'
            assert row['input_sha256'] == inp['observation_sha256']
            assert row['observation_hash'] == inp['observation_hash']
            assert row['stream_ids'] == inp['stream_ids']
            raw = bound(OBS, row['raw_path'], row['raw_sha256'], seal)
            assert raw['observation_id'] == stem and raw['input_sha256'] == row['input_sha256']
            arrays = raw['baseline_arrays']
            entry = {'raw_sha256': row['raw_sha256'],
                     'native_syndrome': row['baseline_syndrome_weight'], 'rounds': {}}
            decisions[stem][arm] = {}
            for r in (0, 1):
                prefix = f'r{r}_'
                app = np.asarray(arrays[prefix + 'app'])
                entry['rounds'][str(r)] = {
                    'geometry': proximity(arrays[prefix+'delays'], arrays[prefix+'dopplers']),
                    'closure': closure(arrays[prefix+'ce_gamma'], arrays[prefix+'ce_gains']),
                    'min_abs_app': float(np.min(np.abs(app))),
                    'mean_abs_app': float(np.mean(np.abs(app))),
                    'low_confidence_app_bits_lt1': int(np.count_nonzero(abs(app) < 1.)),
                }
                decisions[stem][arm][str(r)] = {
                    'decoded': np.asarray(arrays[prefix+'decoded']).copy(),
                    'app_hard': (app < 0).astype(np.uint8)}
            item['arms'][arm] = entry
        extracted.append(item)

    # Old exposed labels join only after the full observed cohort was bound.
    truth_seal = json.loads((TRUTH / 'truth_seal.json').read_text())
    assert truth_seal['status'] == 'pass'
    assert truth_seal['files']['ledger.jsonl'] == sha(TRUTH / 'ledger.jsonl')
    truth_rows = [json.loads(x) for x in (TRUTH / 'ledger.jsonl').read_text().splitlines()]
    truth_by = {r['observation_id']: r for r in truth_rows if r['snr_centi_db'] == 650}
    assert len(truth_by) == 1024
    for item in extracted:
        stem = item['observation_id']
        row = truth_by[stem]
        assert row['observation_hash'] == item['observation_hash']
        assert row['stream_ids'] == population[stem]['stream_ids']
        truth = bound(TRUTH, row['truth_path'], row['truth_sha256'], truth_seal)
        item['truth_sha256'] = row['truth_sha256']
        item['physical_geometry'] = proximity(truth['l_i'], truth['k_real'])
        coded = unpack(truth['coded'])
        for arm in ('A', 'C'):
            for r in ('0', '1'):
                d = decisions[stem][arm][r]
                item['arms'][arm]['rounds'][r]['labels'] = {
                    'decoded_coded_errors': int(np.count_nonzero(d['decoded'] != coded)),
                    'app_hard_coded_errors': int(np.count_nonzero(d['app_hard'] != coded))}
    result = {'schema': 'afdm-innovation-archived-diagnostics/1',
              'evidence_class': 'old exposed developmental cohort; read-only extraction, no receiver calls',
              'diagnostic_scope': 'CE pre-TF Gamma and CE gains; not TF trajectory/JVP or FER certificate',
              'thresholds': {'same_delay_gap': [.25, .5, 1.], 'app_abs': 1.},
              'receiver_calls': 0, 'full_denominator': 1024, 'arms': ['A', 'C'],
              'complete_rows': len(extracted), 'source_roots': list(map(str, (OBS, POP, TRUTH))),
              'source_hashes': {str(p): sha(p) for p in (
                  OBS/'observed_seal.json', OBS/'ledger.jsonl', POP/'observed_seal.json',
                  POP/'ledger.jsonl', TRUTH/'truth_seal.json', TRUTH/'ledger.jsonl')},
              'runtime': {'python': sys.version, 'numpy': np.__version__,
                          'threads': {k: os.environ.get(k) for k in
                                      ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}},
              'rows': extracted}
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
