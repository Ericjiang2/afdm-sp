"""E-3c shared helpers: path setup (E-3b / E-3 code and the frozen math modules are imported read-only), the frozen key sets, E-3b row loading with md5 check.

Keys = U/G x rho .3 x SNR 6..11 dB x frames 4000..4099 (1200 keys, a subset of the 2400 E-3b keys).  Key tuple = (scenario, rho_permille, snr_centi_db, frame).
numpy + stdlib only.
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
E3B_DIR = EXPERIMENTS / 'tf_e3b_offgrid_20261017'
for _p in (str(HERE), str(E3B_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import e3b_lib as b3lib  # noqa: E402  (frozen E-3b helper; its import also puts the E-3 directory and the frozen math modules on sys.path)

md5_file = b3lib.md5_file
deep_equal = b3lib.deep_equal
key_of = b3lib.key_of
shard_block = b3lib.shard_block
verify_manifest = b3lib.verify_manifest

SCENARIOS = b3lib.SCENARIOS
RHO_PM = b3lib.RHO_PM
SNRS = b3lib.SNRS                                   # centi-dB 600..1100
FRAMES = (4000, 4100)
N_KEYS = len(SCENARIOS) * len(SNRS) * (FRAMES[1] - FRAMES[0])   # 1200
SMOKE_FRAME_MIN = 8400
SMOKE_N = 12
GATE_N = 20
SEED = 20261018
E3B_ROWS = E3B_DIR / 'out' / 'main'
CHECK_ARMS = ('diag-off', 'cov-off')


def main_keys():
    """The 1200 frozen keys, ordered (frame, scenario, SNR)."""
    return [(sc, RHO_PM, snr, f) for f in range(*FRAMES) for sc in SCENARIOS for snr in SNRS]


def smoke_keys(n=SMOKE_N):
    """Smoke keys on frames >= 8400 (never the main frames): every SNR once with U and once with G, one frame per key."""
    keys = []
    for rep in range(-(-n // len(SNRS))):
        for i, snr in enumerate(SNRS):
            keys.append(('UG'[(rep + i) % 2], RHO_PM, snr, SMOKE_FRAME_MIN + len(keys)))
    return keys[:n]


def gate_keys(n=GATE_N, seed=SEED):
    """n keys drawn uniformly without replacement (seeded) from the 1200 main keys, in key order (G1 re-runs diag-off / cov-off against the E-3b rows)."""
    keys = main_keys()
    pick = np.random.default_rng(seed).choice(len(keys), n, replace=False)
    return [keys[i] for i in sorted(int(j) for j in pick)]


# ----------------------------------------------------------------------------- E-3b rows (paired diag-off / cov-off results, read-only)
def slim_e3b(r):
    """Fields of an E-3b row that E-3c needs: pairing (FER, NMSE, pairs) and the bit-exact reproduction check (G1 and the main-run check)."""
    out = dict(stage1_atoms=r['stage1']['atoms'], round1_sha=r['round1']['decoded_sha256'], n_cand2=r['n_candidates_stage2'], variants={})
    for a in CHECK_ARMS:
        x = r['variants'][a]
        out['variants'][a] = dict(fer=int(x['fer']), info_errors=int(x['info_errors']), decoded_sha256=x['decoded_sha256'], n_pair=int(x['n_pair']), nmse=float(x['nmse']),
                                  atoms_ongrid=x['atoms_ongrid'], atoms=x['atoms'], dnus=[float(p['dnu']) for p in x['pairs']])
    return out


def load_e3b_rows(rows_dir, keys, verify=True):
    """({key: slim E-3b row}, manifest info) for ``keys`` from the E-3b main rows (rows_shard*.jsonl.gz); with ``verify`` the md5 manifest must match."""
    rows_dir = Path(rows_dir)
    info = dict(files=None, mismatches=[])
    if verify:
        info['files'], info['mismatches'] = verify_manifest(rows_dir)
        if info['mismatches']:
            raise RuntimeError(f'E-3b rows manifest mismatch: {info["mismatches"][:5]}')
    want = set(keys)
    if not want:
        return {}, info
    frames = {k[3] for k in want}
    lo, hi = min(frames), max(frames)
    out = {}
    for p in sorted(glob.glob(str(rows_dir / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if not lo <= r['frame'] <= hi or key_of(r) not in want:
                    continue
                key = key_of(r)
                if key in out:
                    raise RuntimeError(f'duplicate E3b row: {key}')
                if r.get('status') == 'error':
                    raise RuntimeError(f'failed E3b row: {key}')
                out[key] = slim_e3b(r)
    if set(out) != want:
        raise RuntimeError(f'missing E3b keys: {sorted(want-set(out))[:5]}')
    return out, info


def load_e3_grid_rows(rows_dir, keys):
    """Strict E3 on-grid join; reject failed, duplicate or incomplete old rows."""
    rows_dir=Path(rows_dir)
    files,bad=verify_manifest(rows_dir)
    if bad:
        raise RuntimeError(f'E3 manifest mismatch: {bad[:5]}')
    want=set(keys)
    out={}
    for p in sorted(rows_dir.glob('rows_shard*.jsonl*')):
        op=gzip.open if p.suffix=='.gz' else open
        with op(p,'rt') as handle:
            for line in handle:
                r=json.loads(line)
                key=key_of(r)
                if key not in want:
                    continue
                if key in out or r.get('status')=='error':
                    raise RuntimeError(f'duplicate or failed E3 row {key}')
                out[key]=b3lib.slim_e3(r)
    if set(out)!=want:
        raise RuntimeError(f'missing E3 on-grid keys {sorted(want-set(out))[:5]}')
    return out,dict(files=files,mismatches=bad)
