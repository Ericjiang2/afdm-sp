"""Pair the missing old-shell V(T1) cell with its three frozen controls."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import numpy as np


def read_tar(path):
    with tarfile.open(path) as t:
        return {m.name: t.extractfile(m).read() for m in t.getmembers() if m.isfile()}


def analyze(archive, smoke_archive, historical_root, output):
    raw = read_tar(archive); smoke = read_tar(smoke_archive)
    queue = json.loads(raw['queue-status.json'])
    assert queue['complete'] and len(queue['runs']) == 3 and all(r['exit_code'] == 0 for r in queue['runs'])
    smoke_rows = [json.loads(s) for s in smoke['vt1-smoke/frames.jsonl'].splitlines()]
    labels = ['meanT1', 'meanT2', 'VT1', 'VT2']
    matrices, cells, records = [], [], []
    for rep in range(3):
        status = json.loads(raw[f'rep{rep}/status.json'])
        old_status = json.loads((historical_root/f'capacity-dev-rep{rep}/status.json').read_text())
        rows = [json.loads(s) for s in raw[f'rep{rep}/frames.jsonl'].splitlines()]
        assert status['complete'] and not status.get('failure')
        assert status['completed_frames'] == len(rows) == (62 if rep == 0 else 64)
        if rep == 0: rows = smoke_rows + rows
        old_rows = [json.loads(s) for s in (historical_root/f'capacity-dev-rep{rep}/frames.jsonl').read_text().splitlines()]
        assert len(rows) == len(old_rows) == 64
        for key in ['source_sha256', 'checkpoint_sha256', 'calibration_sha256', 'ldpc_sha256', 'device']:
            assert status[key] == old_status[key]
        matrix = []
        for i, (r, old) in enumerate(zip(rows, old_rows)):
            assert (r['replicate'], r['frame_index'], r['split'], r['snr']) == (rep, i, 'D_dev', 8)
            assert r['input_hashes'] == old['input_hashes']
            assert r['nomination_cap'] == 8 and r['active_cap'] == 40
            new = r['arms']['covariance']
            assert new['dals_mode'] == 'covariance' and new['dals_temperature'] == 1
            arms = [old['arms']['baseline'], old['arms']['temperature_mean'], new, old['arms']['covariance']]
            assert [a['dals_temperature'] for a in arms] == [1, 2, 1, 2]
            assert [a['dals_mode'] for a in arms] == ['mean', 'mean', 'covariance', 'covariance']
            assert all(a['finite'] and len(a['support']['expanded']) <= 40 for a in arms)
            assert all(a['rounds'] == arms[0]['rounds'] and a['support']['raw'] == arms[0]['support']['raw'] for a in arms)
            failures = [int(a['info_errors'] > 0) for a in arms]
            matrix.append(failures)
            records.append(dict(replicate=rep, frame_index=i, input_hashes=r['input_hashes'],
                frame_errors=dict(zip(labels, failures)),
                info_bit_errors={label: a['info_errors'] for label, a in zip(labels, arms)},
                decode_ok={label: a['decode_ok'] for label, a in zip(labels, arms)}))
        matrices.append(np.array(matrix, dtype=float))
        cells.append(dict(replicate=rep, n=64, frame_errors=dict(zip(labels, np.sum(matrix, axis=0).astype(int).tolist()))))
    matrix = np.concatenate(matrices)
    weights = dict(V_at_T1=[-1, 0, 1, 0], V_at_T2=[0, -1, 0, 1],
        temperature_at_mean=[-1, 1, 0, 0], temperature_at_V=[0, 0, -1, 1],
        V_main_effect=[-.5, -.5, .5, .5], temperature_main_effect=[-.5, .5, -.5, .5],
        interaction=[1, -1, -1, 1])
    rng = np.random.default_rng(2026090604)
    boot = sum(m[rng.integers(0, 64, size=(20000, 64))].mean(axis=1) for m in matrices)/3
    contrasts = {}
    for name, weights_ in weights.items():
        w = np.array(weights_)
        contrasts[name] = dict(FER_difference=float(matrix.mean(axis=0)@w),
            paired_stratified_bootstrap95=np.quantile(boot@w, [.025, .975]).tolist(),
            per_replicate=[float(m.mean(axis=0)@w) for m in matrices])
    result = dict(scope='old nomination8/cap40 exploratory attribution only; not direct40 or confirmatory',
        cells=cells, pooled_frame_errors=dict(zip(labels, matrix.sum(axis=0).astype(int).tolist())),
        pooled_FER=dict(zip(labels, matrix.mean(axis=0).tolist())), n=192, contrasts=contrasts,
        bootstrap=dict(draws=20000, seed=2026090604, unit='paired frame, resample within each of 3 streams',
                       scope='descriptive percentile intervals, no multiplicity or formal coverage claim'),
        paired_VT1_win=int(((matrix[:, 0] == 1) & (matrix[:, 2] == 0)).sum()),
        paired_VT1_harm=int(((matrix[:, 0] == 0) & (matrix[:, 2] == 1)).sum()),
        frame_records=records, queue=queue, smoke_reused=2, new_receiver_evaluations=190,
        subprocess_seconds=sum(r['ended_at']-r['started_at'] for r in queue['runs']),
        artifact_sha256={k: hashlib.sha256(v).hexdigest() for k, v in raw.items()})
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    output.with_suffix('.tar.gz').write_bytes(gzip.compress(Path(archive).read_bytes(), mtime=0))
    print(json.dumps({k: result[k] for k in ['pooled_frame_errors', 'pooled_FER', 'contrasts', 'paired_VT1_win', 'paired_VT1_harm']}, indent=2))


if __name__ == '__main__':
    analyze(*map(Path, sys.argv[1:]))
