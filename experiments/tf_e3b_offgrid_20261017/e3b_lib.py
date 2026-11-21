"""E-3b shared helpers: path setup (E-3 code and the frozen E-1 helper are imported read-only), the frozen key sets, E-3 row loading with md5 check.

Keys = U/G x rho .3 x SNR 6..11 dB x frames 4000..4199 (2400 keys, all contained in the E-3 main run).  Key tuple = (scenario, rho_permille, snr_centi_db, frame),
the same as E-3.  numpy + stdlib only.
"""
from __future__ import annotations

import glob
import gzip
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E3_DIR = EXPERIMENTS / 'tf_e3_sbl_20261017'
for _p in (str(HERE), str(E3_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import e3_lib  # noqa: E402  (frozen E-3 helper: sys.path setup for the frozen math modules, md5_file, deep_equal)

e3_lib.prepare_paths()
md5_file = e3_lib.md5_file
deep_equal = e3_lib.deep_equal

SCENARIOS = ('U', 'G')
RHO_PM = 300
SNRS = (600, 700, 800, 900, 1000, 1100)          # centi-dB
FRAMES = (4000, 4200)
N_KEYS = len(SCENARIOS) * len(SNRS) * (FRAMES[1] - FRAMES[0])   # 2400
SMOKE_FRAME_MIN = 8300
SMOKE_N = 16
GATE_N = 20
SEED = 20261017
OFF = ('hard-off', 'diag-off', 'cov-off', 'genie-off')
ONGRID = dict(zip(OFF, ('L-hard', 'L-diag', 'L-cov', 'L-genie')))
E3_ROWS = E3_DIR / 'out' / 'main'


def main_keys():
    """The 2400 frozen keys, ordered (frame, scenario, SNR)."""
    return [(sc, RHO_PM, snr, f) for f in range(*FRAMES) for sc in SCENARIOS for snr in SNRS]


def smoke_keys(n=SMOKE_N):
    """Smoke keys on frames >= 8300 (never the main frames): every SNR twice (once U, once G) first, then the first SNRs again; one frame per key."""
    keys = []
    for rep in range(-(-n // len(SNRS))):
        for i, snr in enumerate(SNRS):
            keys.append(('UG'[(rep + i) % 2], RHO_PM, snr, SMOKE_FRAME_MIN + len(keys)))
    return keys[:n]


def gate_keys(n=GATE_N, seed=SEED):
    """n keys drawn uniformly without replacement (seeded) from the 2400 main keys, in key order; G1 re-runs them against the E-3 rows."""
    keys = main_keys()
    pick = np.random.default_rng(seed).choice(len(keys), n, replace=False)
    return [keys[i] for i in sorted(int(j) for j in pick)]


def shard_block(keys, shard, nshard):
    """Contiguous block of the key list owned by ``shard`` (exact partition)."""
    n = len(keys)
    return keys[n * shard // nshard: n * (shard + 1) // nshard]


def key_of(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


# ----------------------------------------------------------------------------- E-3 rows (paired on-grid results, read-only)
def verify_manifest(rows_dir):
    """Check every file of REMOTE_ROWS_MD5.txt in ``rows_dir`` against its md5; returns (n_files, mismatching names)."""
    rows_dir = Path(rows_dir)
    lines = [x.split() for x in (rows_dir / 'REMOTE_ROWS_MD5.txt').read_text().splitlines() if x.strip()]
    bad = [name for digest, name in lines if not (rows_dir / name).exists() or md5_file(rows_dir / name) != digest]
    return len(lines), bad


def slim_e3(r):
    """The fields of an E-3 row that E-3b needs (pairing and on-grid consistency)."""
    return dict(stage1_atoms=r['stage1']['atoms'], round1_sha=r['round1']['decoded_sha256'], n_cand2=r['n_candidates_stage2'],
                variants={v: dict(fer=int(x['fer']), info_errors=int(x['info_errors']), n_pair=int(x['n_pair']), nmse=float(x['nmse']), atoms=x['atoms'],
                                  decoded_sha256=x['decoded_sha256'], n_atoms=int(x['n_atoms'])) for v, x in r['variants'].items()})


def load_e3_rows(rows_dir, keys, verify=True):
    """{key: slim E-3 row} for ``keys`` from rows_shard*.jsonl[.gz] in ``rows_dir`` (E-3 main rows).  With ``verify`` the md5 manifest must match.
    Returns (rows, manifest_info)."""
    rows_dir = Path(rows_dir)
    info = dict(files=None, mismatches=[])
    if verify:
        info['files'], info['mismatches'] = verify_manifest(rows_dir)
        if info['mismatches']:
            raise RuntimeError(f'E-3 rows manifest mismatch: {info["mismatches"][:5]}')
    want = set(keys)
    snrs = {k[2] for k in want}
    out = {}
    for p in sorted(glob.glob(str(rows_dir / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            for line in handle:
                if f'"rho_permille": {RHO_PM},' not in line or not any(f'"snr_centi_db": {s},' in line for s in snrs):
                    continue                                                    # cheap pre-filter before the json parse
                r = json.loads(line)
                if r.get('status') == 'error' or key_of(r) not in want:
                    continue
                out[key_of(r)] = slim_e3(r)
    return out, info
