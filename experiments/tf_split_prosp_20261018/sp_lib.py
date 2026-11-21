"""Split-principle prospective test: shared helpers.  Path setup (the frozen E-3 / E-3b code, the E-1 driver and variant kernels, the covariance-audit bootstrap and the
E-3c provenance resolver are imported read-only, never copied), the frozen key sets, the old-row loaders with md5 checks, source identity.  numpy + stdlib only.

Fresh frames: P1 stream frames 7000..7199 (200 clusters, one per RNG frame).  PROTOCOL.md section 1 holds the audit (verify_frames.py) that no P1-stream observation
ever used them.  Key tuple = (scenario, rho_permille, snr_centi_db, frame).
  Family S: U/G x rho .3 x SNR 6..11 dB x 200 frames = 2400 keys     (data-aided SBL, E-3 pipeline)
  Family K: U/G x rho {.3, .5} x SNR 4.5..8.0 dB x 200 frames = 6400 keys (F0 on every key; the triggered units run the four K arms)
Smoke keys live on frames >= 8600 (never main frames).  Gate keys are OLD keys (E-3 frames 4000..4099, E-1 frames 0..19): G1 replays them against stored rows and
never touches a new frame.
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
E1_DIR = EXPERIMENTS / 'tf_cstate_e1_20261017'
AUDIT_DIR = EXPERIMENTS / 'tf_covariance_audit_20261018'
for _p in (str(HERE), str(E3B_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import e3b_lib as b3lib  # noqa: E402  (frozen E-3b helper; its import also puts the E-3 directory, the E-1 directory and the frozen math modules on sys.path)

md5_file = b3lib.md5_file
deep_equal = b3lib.deep_equal
key_of = b3lib.key_of
verify_manifest = b3lib.verify_manifest

SCENARIOS = b3lib.SCENARIOS                              # ('U', 'G')
FRAMES = (7000, 7200)
N_FRAMES = FRAMES[1] - FRAMES[0]                         # 200 = the bootstrap clusters
S_RHO_PM = 300
S_SNRS = b3lib.SNRS                                      # centi-dB 600..1100
K_RHOS = (300, 500)
K_SNRS = (450, 500, 550, 600, 650, 700, 750, 800)        # centi-dB 4.5..8.0 dB
N_KEYS_S = len(SCENARIOS) * len(S_SNRS) * N_FRAMES       # 2400
N_KEYS_K = len(SCENARIOS) * len(K_RHOS) * len(K_SNRS) * N_FRAMES   # 6400
SMOKE_FRAME_MIN = 8600
GATE_N = 20
ZERO_V_EVERY = 3                                         # G2 zero-v re-run on every 3rd S gate key (7 of 20)
SEED = 20261018
E3_ROWS = b3lib.E3_ROWS
E1_ROWS = E1_DIR / 'out' / 'main'
E1_SELECT = E1_DIR / 'out' / 'select'
E1_GATE_FRAMES = 20                                      # E-1 gate states = frames 0..19
E1_FRAMES = 2000                                         # E-1 ledger = P1 frames 0..1999
S_ARMS = ('S-D', 'S-C', 'S-H')
K_ARMS = ('K-prod', 'K-diag', 'K-fullfix', 'K-isofix', 'K-diag-fullfix', 'K-diag-isofix')   # the last two: amendment A1 (A2 geometry, fixed gains)
FIXED_ARMS = {'K-prod': ('K-fullfix', 'K-isofix', ''), 'K-diag': ('K-diag-fullfix', 'K-diag-isofix', 'diag_')}   # geometry arm -> (full-gain arm, iso-gain arm, check-key prefix)
BASE_ARMS = {'S-D': 'L-diag', 'S-C': 'L-cov'}            # S arm -> the E-3 variant it must reproduce bit for bit
OLD_K_ARMS = {'K-prod': 'A1', 'K-diag': 'A2'}            # K arm -> the E-1 arm it must reproduce bit for bit
TIMING_KEYS = ('seconds', 'stages', 'elapsed_seconds', 'gen_seconds')


# ----------------------------------------------------------------------------- key sets
def s_keys():
    """The 2400 frozen S keys, ordered (frame, scenario, SNR) (a cost-stopped run therefore leaves whole frames)."""
    return [(sc, S_RHO_PM, snr, f) for f in range(*FRAMES) for sc in SCENARIOS for snr in S_SNRS]


def k_keys():
    """The 6400 frozen K keys, ordered (frame, scenario, rho, SNR)."""
    return [(sc, rho, snr, f) for f in range(*FRAMES) for sc in SCENARIOS for rho in K_RHOS for snr in K_SNRS]


def s_smoke_keys():
    """8 S smoke keys: frames 8600 and 8601, U and G, SNR 6 and 11 dB (4 groups)."""
    return [(sc, S_RHO_PM, snr, SMOKE_FRAME_MIN + i) for i in range(2) for sc in SCENARIOS for snr in (S_SNRS[0], S_SNRS[-1])]


def k_smoke_keys():
    """8 K smoke keys: ONE frame (8600) shared by all four (scenario, rho) cells and SNR 4.5 / 8.0 dB (4 groups): exercises the base-frame reuse and, in the
    aggregator's smoke check, the exogenous-hash invariance across scenario / rho / SNR."""
    return [(sc, rho, snr, SMOKE_FRAME_MIN) for sc in SCENARIOS for rho in K_RHOS for snr in (K_SNRS[0], K_SNRS[-1])]


def groups_of(keys):
    """Consecutive keys that share (scenario, rho, frame) form one group: the base frame is generated once and re-used across the SNR levels."""
    out = []
    for k in keys:
        if out and (out[-1][0][0], out[-1][0][1], out[-1][0][3]) == (k[0], k[1], k[3]):
            out[-1].append(k)
        else:
            out.append([k])
    return out


def shard_keys(keys, shard, nshard):
    """Keys of the groups dealt to ``shard`` (group g belongs to shard g mod nshard: exact, balanced, frame-ordered)."""
    return [k for g in groups_of(keys)[shard::nshard] for k in g]


def e3_keys():
    """The E-3c / GSO key set (frames 4000..4099, rho .3, SNR 6..11 dB; ordered (frame, scenario, SNR)); a subset of the E-3 main run."""
    return [(sc, S_RHO_PM, snr, f) for f in range(4000, 4100) for sc in SCENARIOS for snr in S_SNRS]


def s_gate_keys(n=GATE_N, seed=SEED):
    """n OLD keys drawn uniformly without replacement (seeded) from the E-3c key set, in key order (the same call as GSO / E-3c gate_keys)."""
    keys = e3_keys()
    pick = np.random.default_rng(seed).choice(len(keys), n, replace=False)
    return [keys[i] for i in sorted(int(j) for j in pick)]


def zero_v_keys():
    """S gate keys that are re-run with v := 0 (G2)."""
    return s_gate_keys()[::ZERO_V_EVERY]


def load_e1_select(select_dir=E1_SELECT):
    """(triggered_keys.json document, md5) with the md5 checked against REMOTE_KEYS_MD5.txt."""
    select_dir = Path(select_dir)
    digest = md5_file(select_dir / 'triggered_keys.json')
    recorded = (select_dir / 'REMOTE_KEYS_MD5.txt').read_text().split()
    if recorded[0] != digest:
        raise RuntimeError('E-1 triggered_keys.json md5 differs from REMOTE_KEYS_MD5.txt')
    return json.loads((select_dir / 'triggered_keys.json').read_text()), digest


def k_gate_units(select=None, n=GATE_N, seed=SEED):
    """n OLD E-1 gate-state triggered units (frames 0..19 = the E-1 gate frames; seeded draw without replacement, in unit order)."""
    select = load_e1_select()[0] if select is None else select
    pool = [u for u in select['units'] if u['frame'] < E1_GATE_FRAMES]
    pick = np.random.default_rng(seed).choice(len(pool), n, replace=False)
    return [pool[i] for i in sorted(int(j) for j in pick)]


def expected_triggered_units(select=None):
    """Expected number of triggered units in the K main set: the E-1 ledger rate (16379 of 64000 keys on the same 32-cell grid) times the key count."""
    select = load_e1_select()[0] if select is None else select
    return select['n_triggered'] * N_FRAMES / E1_FRAMES


# ----------------------------------------------------------------------------- old rows (read-only baselines)
def slim_e3(r):
    """The fields of an E-3 row that the S family needs: shared stages and the bit-exact reproduction of L-diag (= S-D) and L-cov (= S-C)."""
    out = dict(stage1_atoms=r['stage1']['atoms'], round1_sha=r['round1']['decoded_sha256'], n_cand2=r['n_candidates_stage2'], variants={})
    for arm, old in BASE_ARMS.items():
        x = r['variants'][old]
        out['variants'][arm] = dict(fer=int(x['fer']), info_errors=int(x['info_errors']), decoded_sha256=x['decoded_sha256'], nmse=float(x['nmse']),
                                    n_pair=int(x['n_pair']), n_atoms=int(x['n_atoms']), atoms=x['atoms'],
                                    sbl={k: x['sbl'][k] for k in ('iterations', 'converged', 'beta', 'n_final')})
    return out


def _iter_rows(rows_dir, frames):
    """Parsed rows of rows_shard*.jsonl[.gz] in ``rows_dir`` whose frame is in ``frames`` (cheap pre-filter on the serialised frame field)."""
    wanted = {str(f) for f in frames}
    for p in sorted(Path(rows_dir).glob('rows_shard*.jsonl*')):
        op = gzip.open if p.suffix == '.gz' else open
        with op(p, 'rt') as handle:
            for line in handle:
                m = re.search(r'"frame": (\d+),', line)
                if m is not None and m.group(1) not in wanted:
                    continue
                yield json.loads(line)


def load_e3_rows(rows_dir, keys):
    """({key: slim E-3 row}, manifest info) for ``keys``; the REMOTE_ROWS_MD5.txt manifest must match; rows unique, complete, not failed."""
    n_files, bad = verify_manifest(rows_dir)
    if bad:
        raise RuntimeError(f'E-3 rows manifest mismatch: {bad[:5]}')
    info = dict(files=n_files, mismatches=bad, dir=str(rows_dir))
    want = set(keys)
    out = {}
    if not want:
        return out, info
    for r in _iter_rows(rows_dir, {k[3] for k in want}):
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


def strip_timing(value):
    """Recursively drop wall-clock fields (any key in TIMING_KEYS or ending with 'seconds')."""
    if isinstance(value, dict):
        return {k: strip_timing(x) for k, x in value.items() if k not in TIMING_KEYS and not k.endswith('seconds')}
    if isinstance(value, list):
        return [strip_timing(x) for x in value]
    return value


def slim_e1(r):
    """The fields of an E-1 row that the K family needs: the F0 state, the round-1 geometry and the A1 / A2 arm records without timing."""
    arms = {}
    for new, old in OLD_K_ARMS.items():
        a = r['arms'][old]
        if a.get('status') != 'ok':
            raise RuntimeError(f'E-1 arm {old} not ok')
        arms[new] = strip_timing(a)
    f0 = r['f0']
    return dict(f0=dict(syndrome=f0['syndrome'], info_errors=f0['info_errors'], decoded_sha256=f0['decoded_sha256'], ldpc_iters=f0['ldpc_iters']),
                r1=r['r1'], g4a_ok=bool(r['g4a_ok']), arms=arms)


def load_e1_rows(rows_dir, keys):
    """({key: slim E-1 row}, manifest info) for the OLD triggered ``keys``; manifest checked; rows unique, complete, F0-triggered."""
    n_files, bad = verify_manifest(rows_dir)
    if bad:
        raise RuntimeError(f'E-1 rows manifest mismatch: {bad[:5]}')
    info = dict(files=n_files, mismatches=bad, dir=str(rows_dir))
    want = set(keys)
    out = {}
    for r in _iter_rows(rows_dir, {k[3] for k in want}):
        k = key_of(r)
        if k not in want:
            continue
        if k in out:
            raise RuntimeError(f'duplicate E-1 row {k}')
        out[k] = slim_e1(r)
    if set(out) != want:
        raise RuntimeError(f'missing E-1 keys: {sorted(want - set(out))[:5]}')
    if not all(v['g4a_ok'] for v in out.values()):
        raise RuntimeError('an E-1 gate unit is not F0-triggered')
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
    if 'sp_sampling' not in sys.modules:
        load_module('sp_sampling', AUDIT_DIR / 'sampling.py')
    return sys.modules['sp_sampling']


def provenance():
    """The frozen E-3c resolver (binds canonical source identities to the actually imported bytes)."""
    if 'sp_e3c_provenance' not in sys.modules:
        load_module('sp_e3c_provenance', E3C_DIR / 'e3c_provenance.py')
    return sys.modules['sp_e3c_provenance']


# ----------------------------------------------------------------------------- source identity
IDENTITY_SUFFIXES = ('.py', '.sh')


def own_files():
    """Files of this directory that define the computation (code + launcher + frozen-source table).  PROTOCOL.md and CODE_MD5.txt are documentation / the md5 table
    of these files and are therefore outside the identity (CODE_MD5.txt, checked by the launcher, covers every file)."""
    return sorted([p for p in HERE.iterdir() if p.is_file() and p.suffix in IDENTITY_SUFFIXES] + [HERE / 'SOURCE_MD5.txt'])


def source_identity(ctx):
    """({relative path: sha256}, resolutions): this directory's files plus the frozen-source table resolved against the loaded context (every md5 must equal the
    recorded one, otherwise raise) and the resolved actual bytes."""
    if not getattr(ctx, 'source_paths', None):
        raise RuntimeError('loaded context must expose actual source_paths')
    resolutions = provenance().resolve_frozen(EXPERIMENTS, HERE / 'SOURCE_MD5.txt', getattr(ctx, 'source_md5', None), ctx.source_paths)
    identity = {str(p.relative_to(EXPERIMENTS)): hashlib.sha256(p.read_bytes()).hexdigest() for p in own_files()}
    identity.update({rel: val['sha256'] for rel, val in resolutions.items()})
    return identity, resolutions


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
