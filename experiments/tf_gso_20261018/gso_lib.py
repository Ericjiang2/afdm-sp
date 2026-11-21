"""GSO shared helpers: path setup (the frozen E-3 / E-3b code, the E-1 variant kernel, the covariance-audit bootstrap and the E-3c provenance resolver are
imported read-only, never copied), the frozen key set, the E-3 row loader with md5 check, source identity.  numpy + stdlib only.

Keys = U/G x rho .3 x SNR 6..11 dB x frames 4000..4099 = the 1200 keys of E-3c (a subset of the E-3 main run).  Key tuple = (scenario, rho_permille,
snr_centi_db, frame).  Smoke / gate keys never overlap a main key except the G1 gate keys, which ARE main keys on purpose (G1 replays them against the E-3 rows).
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E3_DIR = EXPERIMENTS / 'tf_e3_sbl_20261017'
E3B_DIR = EXPERIMENTS / 'tf_e3b_offgrid_20261017'
E3C_DIR = EXPERIMENTS / 'tf_e3c_shrink_20261018'
AUDIT_DIR = EXPERIMENTS / 'tf_covariance_audit_20261018'
for _p in (str(HERE), str(E3B_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import e3b_lib as b3lib  # noqa: E402  (frozen E-3b helper; its import also puts the E-3 directory, the E-1 directory and the frozen math modules on sys.path)

md5_file = b3lib.md5_file
deep_equal = b3lib.deep_equal
key_of = b3lib.key_of
verify_manifest = b3lib.verify_manifest

SCENARIOS = b3lib.SCENARIOS
RHO_PM = b3lib.RHO_PM
SNRS = b3lib.SNRS                                        # centi-dB 600..1100
FRAMES = (4000, 4100)
N_KEYS = len(SCENARIOS) * len(SNRS) * (FRAMES[1] - FRAMES[0])   # 1200
N_FRAMES = FRAMES[1] - FRAMES[0]                          # 100 = the bootstrap clusters
SMOKE_FRAME_MIN = 8500
SMOKE_N = 8
GATE_N = 20
ZERO_V_EVERY = 3                                          # G2 zero-v re-run on every 3rd gate key (7 of 20)
SEED = 20261018
E3_ROWS = b3lib.E3_ROWS
BASE_ARMS = {'D-sbl': 'L-diag', 'C-sbl': 'L-cov'}         # GSO arm -> the E-3 variant it must reproduce bit for bit


def main_keys():
    """The 1200 frozen keys, ordered (frame, scenario, SNR) (a cost-stopped run therefore leaves whole frames)."""
    return [(sc, RHO_PM, snr, f) for f in range(*FRAMES) for sc in SCENARIOS for snr in SNRS]


def smoke_keys(n=SMOKE_N):
    """Smoke keys on frames >= 8500 (never main frames), one frame per key, SNR cycling 6..11 dB, U/G alternating."""
    return [('UG'[i % 2], RHO_PM, SNRS[i % len(SNRS)], SMOKE_FRAME_MIN + i) for i in range(n)]


def gate_keys(n=GATE_N, seed=SEED):
    """n main keys drawn uniformly without replacement (seeded), in key order (same call as E-3c.gate_keys)."""
    keys = main_keys()
    pick = np.random.default_rng(seed).choice(len(keys), n, replace=False)
    return [keys[i] for i in sorted(int(j) for j in pick)]


def zero_v_keys():
    """Gate keys that are re-run with v := 0 (G2)."""
    return gate_keys()[::ZERO_V_EVERY]


def shard_keys(keys, shard, nshard):
    """Interleaved partition: key i belongs to shard i mod nshard (exact, balanced; the frame-major key order keeps a cost-stopped run frame-contiguous)."""
    return keys[shard::nshard]


# ----------------------------------------------------------------------------- E-3 rows (the paired D-sbl / C-sbl baselines, read-only)
def slim_e3(r):
    """The fields of an E-3 row that GSO needs: shared stages and the bit-exact reproduction of L-diag (= D-sbl) and L-cov (= C-sbl)."""
    out = dict(stage1_atoms=r['stage1']['atoms'], round1_sha=r['round1']['decoded_sha256'], n_cand2=r['n_candidates_stage2'], variants={})
    for arm, old in BASE_ARMS.items():
        x = r['variants'][old]
        out['variants'][arm] = dict(fer=int(x['fer']), info_errors=int(x['info_errors']), decoded_sha256=x['decoded_sha256'], nmse=float(x['nmse']),
                                    n_pair=int(x['n_pair']), n_atoms=int(x['n_atoms']), atoms=x['atoms'],
                                    sbl={k: x['sbl'][k] for k in ('iterations', 'converged', 'beta', 'n_final')})
    return out


def load_e3_rows(rows_dir, keys):
    """({key: slim E-3 row}, manifest info) for ``keys`` from rows_shard*.jsonl[.gz] in ``rows_dir``; the REMOTE_ROWS_MD5.txt manifest must match; rows must be
    unique, complete and not failed."""
    rows_dir = Path(rows_dir)
    n_files, bad = verify_manifest(rows_dir)
    if bad:
        raise RuntimeError(f'E-3 rows manifest mismatch: {bad[:5]}')
    info = dict(files=n_files, mismatches=bad, dir=str(rows_dir))
    want = set(keys)
    if not want:
        return {}, info
    frames = {str(k[3]) for k in want}
    out = {}
    for p in sorted(rows_dir.glob('rows_shard*.jsonl*')):
        op = gzip.open if p.suffix == '.gz' else open
        with op(p, 'rt') as handle:
            for line in handle:
                m = re.search(r'"frame": (\d+),', line)
                if m is not None and m.group(1) not in frames:
                    continue                                              # cheap pre-filter before the json parse
                r = json.loads(line)
                k = key_of(r)
                if k not in want:
                    continue
                if r.get('status') == 'error':
                    raise RuntimeError(f'failed E-3 row {k}')
                if k in out:
                    raise RuntimeError(f'duplicate E-3 row {k}')
                out[k] = slim_e3(r)
    if set(out) != want:
        raise RuntimeError(f'missing E-3 keys: {sorted(want - set(out))[:5]}')
    return out, info


# ----------------------------------------------------------------------------- read-only imports by explicit path (no name shadowing)
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def sampling():
    """The frozen cluster-bootstrap module (tf_covariance_audit_20261018/sampling.py), loaded from its exact path."""
    if 'gso_sampling' not in sys.modules:
        load_module('gso_sampling', AUDIT_DIR / 'sampling.py')
    return sys.modules['gso_sampling']


def provenance():
    """The frozen E-3c resolver (binds canonical source identities to the actually imported bytes)."""
    if 'gso_e3c_provenance' not in sys.modules:
        load_module('gso_e3c_provenance', E3C_DIR / 'e3c_provenance.py')
    return sys.modules['gso_e3c_provenance']


# ----------------------------------------------------------------------------- source identity
IDENTITY_SUFFIXES = ('.py', '.sh')


def own_files():
    """GSO files that define the computation (code + launcher + frozen-source table).  PROTOCOL.md and CODE_MD5.txt are documentation / the md5 table of these
    files and are therefore outside the identity (CODE_MD5.txt, checked by the launcher, covers every file)."""
    return sorted([p for p in HERE.iterdir() if p.is_file() and p.suffix in IDENTITY_SUFFIXES] + [HERE / 'SOURCE_MD5.txt'])


def source_identity(ctx):
    """{relative path: sha256}: the GSO files, the frozen-source table resolved against the loaded context (md5 must equal the recorded one, otherwise raise),
    and the resolved actual bytes.  Returns (identity, resolutions)."""
    if not getattr(ctx, 'source_paths', None):
        raise RuntimeError('loaded context must expose actual source_paths')
    resolutions = provenance().resolve_frozen(EXPERIMENTS, HERE / 'SOURCE_MD5.txt', getattr(ctx, 'source_md5', None), ctx.source_paths)
    identity = {str(p.relative_to(EXPERIMENTS)): hashlib.sha256(p.read_bytes()).hexdigest() for p in own_files()}
    identity.update({rel: val['sha256'] for rel, val in resolutions.items()})
    return identity, resolutions


# ----------------------------------------------------------------------------- unit-test receipts
def write_receipt(out_dir, name, test_result):
    """Engineering-gate receipt of a unittest run: {all_pass, tests, failures, sources_sha256}; the source identity is that of the real receiver context so that
    unit / gate / smoke / main snapshots can be compared without waivers."""
    import e3_driver  # lazy: heavy, needs the frozen P1 context
    identity, _ = source_identity(e3_driver.p1ctx.load())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = dict(all_pass=bool(test_result.wasSuccessful()), tests=int(test_result.testsRun), failures=len(test_result.failures), errors=len(test_result.errors),
                   sources_sha256=identity)
    (out_dir / f'{name}.json').write_text(json.dumps(receipt, indent=1, sort_keys=True) + '\n')
    return receipt
