"""Read and verify Phase 1 reference evidence on deinlab."""

import gzip
import hashlib
import json
from pathlib import Path

from verdict import CSTATE_GAP, SBL_GAP, estimates, linear_summary, ratio_summary

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / 'experiments'
SPECTRAL = EXP / 'sbl_spectral_split_20261119'
STAGE3 = EXP / 'cstate_codelay_sbl_stage3_20261118'
SPLIT = EXP / 'tf_split_prosp_20261018'
SPECTRAL_MAIN = SPECTRAL / 'out/main_20261119'
SPLIT_MAIN = SPLIT / 'out/main'
STAGE3_MAIN = STAGE3 / 'out'
SPECTRAL_SMOKE = SPECTRAL / 'out/phase1_20261119_attempt02/g2_smoke.json'
# SHA-256 pins from Stage 3 commit 1508c12e15ccc8615ec26f6cab4dd01310066a00 and local archive manifests.
STAGE3_FILES = {
    'cstate_codelay_sbl_stage3_20261118/run.py': '85350a81961d8d6c8b35b4dab1827fe01fcd011fbfc670feb9764405aed06c5d',
    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'a5af12d5f0131f70793904b255d83d9db1edc8c7e9443158f150d61335b4f929',
    'tf_cstate_e1_20261017/e1_driver.py': 'b95e29ebf75361912cc03cf71701efbd38bc4c1df5ea1ac8b5b82d9c426acd12',
    'tf_cstate_e1_20261017/geometry_validation_variant.py': 'bbcd98a8fd65614d37378d7f1f6b7d65ba05cce39b1ea4ffdc9f6fc2d25187b0',
}
PINS = {
    'spectral_freeze': 'c52292cbdabf5e57916437fd331c2529cdc94465ee3c647a8bb08ce90e4435bd',
    'spectral_rows': '82036e8f9bde8dd3652e232f37e889f98ef44f95670c05dee55d46c55068a462',
    'stage3_rows': '3457a62acbfdf10d7b3ba890d62126526bbae19bb90c400838d574fbc1e59f31',
    'split_rows': '75ec3889a0aa24f223249e376ce771b2806b04079bed9d75940cc02aaeb9c872',
    'split_smoke': '5075abd2c45796f8e82af9de1994e37da3e29394ef7e506aaf106e1baf934671',
}


class FrozenEvidenceError(RuntimeError):
    """The reference bytes or rows differ from their archived identity."""


def verify(path, expected):
    algorithm = 'md5' if len(expected) == 32 else 'sha256'
    checksum = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            checksum.update(block)
    digest = checksum.hexdigest()
    if digest != expected:
        raise FrozenEvidenceError(f'{path}: expected {expected}, got {digest}')
    return digest


def read_rows(path):
    opener = gzip.open if path.name.endswith('.gz') else open
    with opener(path, 'rt') as handle:
        for line in handle:
            yield json.loads(line)


def manifest_rows(directory, name, expected, prefix):
    manifest = directory / name
    verify(manifest, expected)
    paths = []
    for line in manifest.read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            digest, filename = line.split()
            path = directory / filename.lstrip('*')
            if path.name.startswith(prefix):
                verify(path, digest)
                paths.append(path)
    if not paths:
        raise FrozenEvidenceError(f'{manifest}: missing {prefix} rows')
    return [row for path in paths for row in read_rows(path)]


def key(row):
    return tuple(row[k] for k in ('scenario', 'rho_permille', 'snr_centi_db', 'frame'))


def unique(rows, expected):
    by_key = {key(row): row for row in rows}
    if len(by_key) != len(rows) or by_key.keys() != expected:
        raise FrozenEvidenceError(f'Archive has {len(rows)} rows/{len(by_key)} keys; '
                                  f'expected {len(expected)} distinct registered keys')
    return by_key


def load_preflight(sbl, cstate, split_arm_shape):
    # Verify source and outcome artifacts before the first receiver call.
    import phase1

    e3c = sbl.e3c
    spectral_freeze = json.loads((SPECTRAL / 'FREEZE.json').read_text())
    verify(SPECTRAL / 'FREEZE.json', PINS['spectral_freeze'])
    for name, digest in spectral_freeze['sources_sha256'].items():
        verify(SPECTRAL / name, digest)
    verify(SPECTRAL_SMOKE, spectral_freeze['phase1_receipts_sha256'][
        'out/phase1_20261119_attempt02/g2_smoke.json'])
    for path, digest in STAGE3_FILES.items():
        verify(EXP / path, digest)
    ctx, full, cd, source_checks = cstate.context()
    if e3c.p1ctx is not cstate.stage3.e1.p1ctx:
        raise FrozenEvidenceError('E-3c and Stage 3 did not load the same P1 context provider')
    sbl_identity = phase1.frozen_identity(ctx)
    if sbl_identity != spectral_freeze['frozen_e3c_sources_sha256']:
        raise FrozenEvidenceError('Actual loaded E-3c source differs from spectral freeze')
    if Path(full.reopen_geometry.__code__.co_filename).resolve() != (
            EXP / 'tf_cstate_e1_20261017/geometry_validation_variant.py').resolve():
        raise FrozenEvidenceError('Stage 3 loaded an unexpected E-1 geometry module')

    all_sbl = set(e3c.lib.main_keys())
    e3c_rows, e3c_receipt = phase1.load_archive(all_sbl)
    spectral_rows = unique(manifest_rows(SPECTRAL_MAIN, 'REMOTE_ROWS_MD5.txt',
                                         PINS['spectral_rows'], 'rows_shard'), all_sbl)
    for unit, row in spectral_rows.items():
        if row['status'] != 'ok':
            raise FrozenEvidenceError(f'Failed spectral reference row: {unit}')
        for name in ('R0', 'R1'):
            before = e3c_rows[unit]['variants'][name]
            after = row['budgets']['100'][name]
            fields = ('fer', 'info_errors', 'decoded_sha256', 'nmse', 'n_atoms', 'n_pair')
            if any(phase1.canonical(before[f]) != phase1.canonical(after[f]) for f in fields):
                raise FrozenEvidenceError(f'Spectral join differs from E-3c: {unit}/{name}')

    stage_rows = unique(manifest_rows(STAGE3_MAIN, 'MAIN_ROWS_MD5.txt',
                                      PINS['stage3_rows'], 'main-'), cstate.stage3.main_keys())
    split_keys = {(s, rho, snr, frame) for s in ('U', 'G') for rho in (300, 500)
                  for snr in range(450, 801, 50) for frame in range(7000, 7200)}
    split_rows = unique(manifest_rows(SPLIT_MAIN, 'REMOTE_ROWS_MD5.txt',
                                      PINS['split_rows'], 'rows_K_shard'), split_keys)
    split_smoke = sorted((SPLIT / 'out/smoke').glob('rows_K_shard*.jsonl*'))
    if not split_smoke or len(split_smoke) != 4:
        raise FrozenEvidenceError('Split-prosp K smoke archive inventory mismatch')
    smoke_manifest = SPLIT / 'out/smoke/REMOTE_MD5.txt'
    verify(smoke_manifest, PINS['split_smoke'])
    digests = {filename.lstrip('*'): digest for digest, filename in
               (line.split() for line in smoke_manifest.read_text().splitlines() if line.strip())}
    for path in split_smoke:
        verify(path, digests[path.name])
    cstate_smoke = sorted((row for path in split_smoke for row in read_rows(path)), key=key)
    if any(not row['smoke'] or row['status'] != 'ok' for row in cstate_smoke):
        raise FrozenEvidenceError('Invalid split-prosp K smoke rows')
    if set(map(key, cstate_smoke)) != split_arm_shape:
        raise FrozenEvidenceError('Split-prosp K smoke key set changed')
    return dict(e3c_rows=e3c_rows, spectral_rows=spectral_rows, stage_rows=stage_rows,
                split_rows=split_rows, cstate_smoke=cstate_smoke,
                identity=dict(spectral_sources_sha256=sbl_identity, stage3_sources=source_checks,
                              stage3_producing_source_sha256=STAGE3_FILES,
                              e3c_archive=e3c_receipt, manifests_sha256=PINS))


def leverage(spectral_rows, split_rows):
    sbl = {arm: [r['budgets']['100'][arm]['fer'] for r in spectral_rows.values()]
           for arm in ('R0', 'R1', 'S-lo')}
    p, b, n = estimates(sbl, [k[3] for k in spectral_rows])
    low = ratio_summary(p, b, {'R1': 1, 'S-lo': -1}, SBL_GAP)
    halfwidth = low['ci_width'] / 2

    outcomes = {'A2': [], 'CD': []}
    for unit, row in split_rows.items():
        if (row['status'] != 'ok' or row['smoke'] or row['family'] != 'K'
                or row['triggered'] != (row['f0']['syndrome'] != 0)):
            raise FrozenEvidenceError(f'Invalid split-prosp K row: {unit}')
        for name, old in (('A2', 'K-diag'), ('CD', 'K-prod')):
            decision = row['arms'][old] if row['triggered'] else row['f0']
            outcomes[name].append(int(decision['info_errors'] > 0))
    q, s, m = estimates(outcomes, [k[3] for k in split_rows])
    return dict(sbl=dict(**low, halfwidth_1200=halfwidth, halfwidth_2400=halfwidth / 2**.5,
                         keys=len(spectral_rows), clusters=n, archive=str(SPECTRAL_MAIN),
                         sbl_gap=linear_summary(p, b, SBL_GAP)),
                cstate=dict(**linear_summary(q, s, CSTATE_GAP), keys=len(split_rows), clusters=m,
                            arms='K-diag (A2) minus K-prod (A1/FULL); nontriggers use F0',
                            grid='U/G × rho .3/.5 × 4.5–8 dB by .5 × frames 7000–7199',
                            archive=str(SPLIT_MAIN), fer=dict(A2=q['A2'], A1=q['CD'])))
