"""Verify and summarize the compressed Phase 2 archive without receiver calls."""

import argparse
import gzip
import hashlib
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from phase3_crossings import CAPS, CELLS, read_crossings
from phase3_q2 import read_q2

FROZEN_COMMIT = '9b633ce9df020158d51621600d7b6eab3b65395d'
FIRST_FRAME = 10_000
N_FRAMES = 1_000
FRAMES_PER_SHARD = 5
N_BOOT = 20_000
SEED = 20261019
SNRS = list(range(450, 801, 50))
TRUE_PATHS = {'M': 8, 'T6': 6, 'T10': 10, 'N': 8}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_archive(run):
    config = json.loads((run / 'RUN_CONFIG.json').read_text())['_config']
    receipt = json.loads((run / 'main_receipt.json').read_text())
    n_shards = N_FRAMES // FRAMES_PER_SHARD
    require(config['commit'] == receipt['_config']['commit'] == FROZEN_COMMIT,
            'The main archive does not match the frozen commit')
    require(config['scope'] == 'complete' and config['snr_centi_db'] == SNRS
            and config['frame_range'] == [FIRST_FRAME, FIRST_FRAME + N_FRAMES - 1]
            and config['expected_keys'] == 104_000 and config['frames_per_shard'] == FRAMES_PER_SHARD
            and config['workers'] == 24 and config['budget_core_hours'] == 40,
            'The archive configuration differs from the frozen complete run')
    require(receipt['planned_shards'] == receipt['completed_shards'] == n_shards
            and not receipt['failures'] and receipt['reason'] is None and receipt['core_hours'] <= 40,
            'The main receipt does not record complete execution within the cap')
    manifest = (run / 'REMOTE_ROWS_MD5.txt').read_bytes()
    entries = [line.split() for line in manifest.decode().splitlines()]
    expected_files = [f'rows_shard{i:03d}.jsonl.gz' for i in range(n_shards)]
    require([name for _, name in entries] == expected_files, 'Unexpected raw shard inventory')
    rows = []
    for shard, (digest, name) in enumerate(entries):
        compressed = run / name
        shard_receipt = json.loads((run / f'shard{shard:03d}.json').read_text())
        start = FIRST_FRAME + shard * FRAMES_PER_SHARD
        end = start + FRAMES_PER_SHARD
        require(shard_receipt['status'] == 'complete' and shard_receipt['commit'] == FROZEN_COMMIT
                and shard_receipt['frames'] == [start, end - 1] and shard_receipt['shard'] == shard,
                f'Invalid receipt for {name}')
        require(hashlib.md5(compressed.read_bytes()).hexdigest() == digest, f'MD5 mismatch for {name}')
        expected = {(family, *key) for family in CAPS
                    for key in itertools.product(range(start, end),
                                                 [('G', 300)] if family == 'N' else CELLS, SNRS)}
        with gzip.open(compressed, 'rt') as source:
            for line in source:
                row = json.loads(line)
                family = row['family']
                key = (family, row['frame'], (row['scenario'], row['rho_permille']), row['snr_centi_db'])
                require(key in expected, f'Unexpected or duplicate archive key {key}')
                expected.remove(key)
                require(row['P_true'] == TRUE_PATHS[family] == len(row['truth']['delays'])
                        and set(row['s']) == {str(cap) for cap in CAPS[family]}
                        and (row['noise'] is not None) == (family == 'N'), f'Invalid receiver inputs at {key}')
                for cap, record in row['s'].items():
                    require(record['triggered'] == bool(record['f0']['syndrome'])
                            and set(record['arms']) == ({'A1c', 'A2'} if record['triggered'] else set()),
                            f'Missing or unexpected continuation at {key} cap {cap}')
                rows.append(row)
        require(not expected, f'Missing {len(expected)} receiver keys in {name}')
    counts = Counter(row['family'] for row in rows)
    require(counts == receipt['keys_by_family'], 'Archive counts disagree with the main receipt')
    return rows, counts, hashlib.sha256(manifest).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows, counts, manifest_sha = read_archive(args.run)
    rng = np.random.default_rng(SEED)
    weights = np.empty((N_BOOT, N_FRAMES), dtype=np.float32)
    for draw in weights:
        sample = rng.integers(0, N_FRAMES, N_FRAMES)
        draw[:] = np.bincount(sample, minlength=N_FRAMES)
    scripts = ('phase3_readout.py', 'phase3_crossings.py', 'phase3_q2.py')
    result = dict(
        _argv=sys.argv,
        _config=dict(frozen_commit=FROZEN_COMMIT, receiver_keys=counts, first_frame=FIRST_FRAME,
                     n_frames=N_FRAMES, snr_centi_db=SNRS, n_boot=N_BOOT, seed=SEED,
                     numpy=np.__version__, manifest_sha256=manifest_sha,
                     readout_sha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in scripts}),
        q1=read_crossings(rows, weights), q2=read_q2(rows, weights),
    )
    with args.out.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
