"""Read saved rows and compute 95% intervals."""

import gzip
import hashlib
import json
import re
from math import sqrt

import numpy as np


ROW_PATTERN = r'rows(?:_shard\d+)?\.jsonl(?:\.gz)?'


def read_rows(run_dir, pattern=ROW_PATTERN):
    """Yield JSON lines after verifying each selected shard against its manifest."""
    files = sorted(path for path in run_dir.iterdir() if re.fullmatch(pattern, path.name))
    if not files:
        raise ValueError(f'No saved rows in {run_dir} matching {pattern}')
    for name in ('REMOTE_ROWS_MD5.txt', 'RAW_SHARDS_MD5.txt'):
        manifest = run_dir / name
        if manifest.is_file():
            break
    else:
        raise FileNotFoundError(f'Saved row manifest missing in {run_dir}')
    entries = [line.split()[:2] for line in manifest.read_text().splitlines() if line.strip()]
    selected = [(digest, name) for digest, name in entries if re.fullmatch(pattern, name)]
    if sorted(name for _, name in selected) != [path.name for path in files]:
        raise ValueError(f'Row inventory differs from {manifest}')
    expected = {name: digest for digest, name in selected}
    for path in files:
        digest = hashlib.md5()
        with path.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != expected[path.name]:
            raise ValueError(f'Saved row digest mismatch: {path}')
        open_text = gzip.open if path.suffix == '.gz' else open
        with open_text(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                yield json.loads(line)


def interval(samples):
    samples = np.asarray(samples)
    if samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError('Expected nonempty finite bootstrap samples')
    return np.quantile(samples, [.025, .975], axis=0).tolist()


def wilson(success, n):
    if not 0 <= success <= n or n == 0:
        raise ValueError(f'Invalid binomial counts: {success}/{n}')
    z = 1.959963984540054
    p = success / n
    scale = 1 + z * z / n
    center = (p + z * z / (2 * n)) / scale
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / scale
    return [max(0., center - half), min(1., center + half)]
