"""Phase 1 receipts for SBL archive parity, construction and repeatability."""

from functools import lru_cache, partial
from hashlib import md5, sha256
import json
from types import SimpleNamespace

import numpy as np

import s_arm

ARCHIVE = s_arm.EXPERIMENTS / s_arm.UNIFIED / 'out' / 'main_20261119'
SCREEN_RESULT = s_arm.EXPERIMENTS / s_arm.SCREEN / 'out' / 'screen.json'
SCREEN_RESULT_SHA256 = '86f0b012adfd0ab4697d6ef130f92a6aca59bba9f45e90c4640498bcd8e6f02f'
SEED = 20261119


class FrozenEvidenceError(RuntimeError):
    """A frozen reference or archived replay failed verification."""


@lru_cache(maxsize=1)
def screen_s2():
    s_arm.gate_source()
    s_arm.frozen_module(s_arm.SCREEN, 'soft_replay', '5c4ccf3ad3a99707a7436074f30bb98501a7b2d61575c1063d51ea2f205eaa57')
    return s_arm.frozen_module(s_arm.SCREEN, 's2', '3d9b014f4994ca36e4abcc400d28a54a933adc297f357391b8ecc63a571e565e')


def load_archive():
    """Load exactly the checksummed res-03 SBL keys with complete saved rows."""
    s2 = screen_s2()
    config_raw = (ARCHIVE / 'config.json').read_bytes()
    manifest = (ARCHIVE / 'REMOTE_ROWS_MD5.txt').read_bytes()
    if ((ARCHIVE / 'STATUS').read_text().strip() != 'DONE'
            or sha256(config_raw).hexdigest() != s2.CONFIG_SHA256
            or sha256(manifest).hexdigest() != s2.ROWS_MANIFEST_SHA256):
        raise FrozenEvidenceError('res-03 completion status, config or row manifest differs')
    config = json.loads(config_raw)['_config']
    if (ARCHIVE / 'PRODUCING_COMMIT.txt').read_text().strip() != config['producing_commit']:
        raise FrozenEvidenceError('res-03 producing commit differs from the pinned config')
    rows = {}
    for digest, name in map(str.split, manifest.decode().splitlines()):
        path = ARCHIVE / name
        raw = path.read_bytes()
        if md5(raw).hexdigest() != digest:
            raise FrozenEvidenceError(f'res-03 row shard mismatch: {path}')
        for line in raw.splitlines():
            entry = json.loads(line)
            if entry['leg'] != 'sbl':
                continue
            key, row = tuple(entry['key']), entry['row']
            if (entry['snapshot_sha256'] != config['snapshot_sha256']
                    or entry['launch_commit'] != config['producing_commit']
                    or tuple(row['key']) != key or key in rows):
                raise FrozenEvidenceError(f'Unexpected res-03 row identity: {key}')
            rows[key] = row
    if rows.keys() != {(sc, 300, snr, frame) for sc in ('G', 'U')
                       for snr in s2.SNRS for frame in s2.FRAMES}:
        raise FrozenEvidenceError('res-03 archive does not cover the registered 2,400-key grid')
    provenance = dict(archive=str(ARCHIVE), config_sha256=s2.CONFIG_SHA256,
                      manifest_sha256=s2.ROWS_MANIFEST_SHA256, keys=len(rows),
                      producing_commit=config['producing_commit'], snapshot_sha256=config['snapshot_sha256'],
                      source_identity=config['sources']['spectral_sources_sha256'])
    return rows, provenance


@lru_cache(maxsize=1)
def context(source_identity):
    s_arm.receiver()
    return screen_s2().make_context(dict(source_identity=dict(source_identity)))


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items()
                if k != 'seconds' and not k.endswith('_seconds')}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def fingerprint(value):
    return sha256(canonical(value).encode()).hexdigest()


def match_archive(expected, actual, key, component):
    if canonical(expected) != canonical(actual):
        changed = [k for k in sorted(expected.keys() | actual.keys())
                   if k not in expected or k not in actual
                   or canonical(expected[k]) != canonical(actual[k])]
        raise FrozenEvidenceError(f'res-03 mismatch for {key} {component}: {changed}')
    return fingerprint(actual)


def archive_parity(item, *, source_identity):
    key, old = item
    ctx, _, _, _, _, grid, _ = context(source_identity)
    actual = s_arm.run_key(ctx, grid, key, replace_with_low=True)
    old_common = stable({k: v for k, v in old.items() if k != 'variants'})
    actual_common = stable({k: v for k, v in actual.items() if k != 'variants'})
    common_sha = match_archive(old_common, actual_common, key, 'shared E-3c row')
    arm_sha = {}
    for name in s_arm.ARM_NAMES:
        score = actual['variants'][name]
        saved = old['variants']['S-lo' if name == 'G' else name]
        archive_fields = stable({k: v for k, v in score.items() if k != 'decoded'})
        arm_sha[name] = match_archive(stable(saved), archive_fields, key, name)
    return dict(key=key, common_sha256=common_sha, arm_sha256=arm_sha), actual


def construct_only(item, *, source_identity):
    key, old, reference = item
    if key[3] not in range(4400, 4600):
        raise ValueError(f'Phase 1 S2 construction key disallowed: {key}')
    archive_input = dict(
        sigma2=old['sigma2'], ldpc_sweeps=old['round1']['ldpc_iters'], sum_v=old['sum_v'],
        inputs={name: old['input_sha256'][name] for name in ('y', 'pilot', 'soft_mean', 'app_v')},
        candidate_sha=old['candidates_sha256'], candidates=old['n_candidates_stage2'],
        s_lo_rank=old['census']['projector_rank'], rng=(old['rng_entropy'], old['rng_domain']),
    )
    ctx, e3c, moments, daft, dkernel, grid, cache = context(source_identity)

    def capture_columns(*args):
        nonlocal columns
        columns = e3c.sbl.columns(*args)
        return columns

    def capture_candidates(*args):
        nonlocal candidates
        candidates = e3c.sbl.candidate_union(*args)
        return candidates

    def capture_moments(*args):
        nonlocal variances
        result = moments(*args)
        variances = result[1]
        return result

    # S2 verifies the entering soft state and stops before stage-2 EM.
    # Capture its actual inputs to verify the entire arm constructor.
    columns = candidates = variances = None
    captured_sbl = SimpleNamespace(**dict(vars(e3c.sbl), columns=capture_columns,
                                         candidate_union=capture_candidates))
    captured_e3c = SimpleNamespace(**dict(vars(e3c), sbl=captured_sbl))
    screen_s2().run_key((ctx, captured_e3c, capture_moments, daft, dkernel, grid, cache),
                        (key, archive_input))
    delays, dopplers = (values[candidates] for values in grid)
    sigma2, u = old['sigma2'], old['sum_v']
    _, _, _, low_blocks, _ = s_arm.receiver().spectral.arm_settings(
        variances, sigma2, delays, dopplers, ctx.system.c1, True)
    _, blocks = s_arm.initial_gate(columns[:, candidates], delays, dopplers, low_blocks, u, sigma2)
    if len(reference['blocks']) != len(blocks):
        raise FrozenEvidenceError(f'S2 {key}: number of co-delay blocks differs')
    errors = []
    for expected, got in zip(reference['blocks'], blocks, strict=True):
        if expected['atoms'] != got['size']:
            raise FrozenEvidenceError(f'S2 {key} delay {expected["delay"]}: block size differs')
        for field in ('delay', 'gate_rank', 's_lo_rank'):
            if expected[field] != got[field]:
                raise FrozenEvidenceError(f'S2 {key} delay {expected["delay"]}: {field} differs')
        error = abs(expected['overlap_trace'] - got['overlap_trace'])
        if error > s_arm.PROJECTOR_ATOL:
            raise FrozenEvidenceError(f'S2 {key} delay {expected["delay"]}: overlap differs by {error}')
        errors.append(error)
    return dict(key=key, verified=True, blocks=blocks, max_overlap_abs_error=max(errors))


def repeat_key(key, *, source_identity):
    ctx, _, _, _, _, grid, _ = context(source_identity)
    first = s_arm.run_key(ctx, grid, key)
    second = s_arm.run_key(ctx, grid, key)
    first_stable = stable(first)
    if canonical(first_stable) != canonical(stable(second)):
        raise AssertionError(f'Complete non-timing row differed on SBL smoke key {key}')
    return dict(key=key, sha256=fingerprint(first_stable),
                cpu_seconds=[r['seconds']['cpu_total'] for r in (first, second)]), first, second


def synthetic():
    gate = s_arm.gate_source()
    cases = [(np.eye(1), np.zeros((1, 1))),
             (np.array([[1., .9j], [-.9j, 1.]]), np.zeros((2, 2))),
             (np.array([[1., .9j], [-.9j, 1.]]), 100 * np.eye(2)),
             (np.full((4, 4), .9) + .1 * np.eye(4), np.diag([0., .1, 1., 100.]))]
    ranks = []
    for d, gram in cases:
        projector, rank = s_arm.gate_projector(gram, d, 1., .5)
        values, modes = np.linalg.eigh(d)
        low_modes = modes[:, values < .5]
        census = s_arm.block_census(projector, rank, low_modes @ low_modes.conj().T, low_modes.shape[1])
        canonical(census)
        ref = gate.compare_block(gram, d, 1., .5)
        if (ref[:2] != (rank, census['s_lo_rank'])
                or abs(ref[2] - census['overlap_trace']) > s_arm.PROJECTOR_ATOL
                or not np.allclose(projector, projector.conj().T, rtol=0, atol=s_arm.PROJECTOR_ATOL)
                or not np.allclose(projector @ projector, projector, rtol=0, atol=s_arm.PROJECTOR_ATOL)):
            raise AssertionError('Synthetic projector differs from the frozen gate or is not orthogonal')
        ranks.append(rank)
    if ranks[:3] != [0, 1, 0] or not 0 < ranks[3] < 4:
        raise AssertionError(f'Expected singleton, positive/negative pair and nontrivial larger-block tests: {ranks}')
    return dict(cases=len(cases), ranks=ranks)


def choose(items, count, seed):
    rng = np.random.default_rng(seed)
    return [items[i] for i in sorted(rng.choice(len(items), count, replace=False))]


def write_json(out, filename, payload):
    data = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)
    with (out / filename).open('x') as handle:
        handle.write(data + '\n')


def run(pool, rows, provenance, out):
    """Qualify G1/G2 and G3 before decoding real G on the twelve smoke keys."""
    raw = SCREEN_RESULT.read_bytes()
    if sha256(raw).hexdigest() != SCREEN_RESULT_SHA256:
        raise FrozenEvidenceError('Archived S2 screen checksum differs from a818bf99')
    s2_rows = json.loads(raw)['S2']['keys']
    reference = {tuple(row['key']): row for row in s2_rows}
    if len(reference) != 200 or reference.keys() - rows.keys() or not all(row['verified'] for row in s2_rows):
        raise FrozenEvidenceError('Archived S2 screen is missing verified res-03 keys')
    archive_keys = choose(sorted(rows), 20, SEED)
    construction_keys = [key for snr in screen_s2().SNRS
                         for key in choose(sorted(k for k in reference if k[2] == snr), 4, SEED + snr)]
    smoke_keys = s_arm.receiver().e3c.lib.smoke_keys()
    source_identity = tuple(sorted(provenance['source_identity'].items()))
    report = {}
    print('SBL G1/G2: 20 archived controls and gate-to-S-lo reductions', flush=True)
    parity = []
    with (out / 'sbl_archive_replay_rows.jsonl').open('x') as handle:
        for receipt, row in pool.map(partial(archive_parity, source_identity=source_identity),
                                     ((key, rows[key]) for key in archive_keys)):
            print(canonical(row), file=handle, flush=True)
            parity.append(receipt)
    for gate, names in [('G1', ('R0', 'S-lo')), ('G2', ('G',))]:
        report[gate] = dict(passed=True, keys=len(parity), seed=SEED, receipts=[
            dict(key=r['key'], common_sha256=r['common_sha256'],
                 arm_sha256={name: r['arm_sha256'][name] for name in names}) for r in parity])
        write_json(out, f'sbl_{gate.lower()}.json', report[gate])

    print('SBL G3: soft-only initial grid construction on 24 archived S2 keys', flush=True)
    construction = list(pool.map(partial(construct_only, source_identity=source_identity),
                                 ((k, rows[k], reference[k]) for k in construction_keys)))
    report['G3'] = dict(passed=True, keys=len(construction), screen_sha256=SCREEN_RESULT_SHA256,
                        blocks=sum(len(r['blocks']) for r in construction), receipts=construction,
                        max_overlap_abs_error=max(r['max_overlap_abs_error'] for r in construction))
    write_json(out, 'sbl_g3.json', report['G3'])

    print('SBL G4: repeat full non-timing rows on the 12 E-3c smoke keys', flush=True)
    repeated = []
    with (out / 'sbl_smoke_rows.jsonl').open('x') as handle:
        for receipt, first, second in pool.map(partial(repeat_key, source_identity=source_identity), smoke_keys):
            print(canonical(first), file=handle, flush=True)
            print(canonical(second), file=handle, flush=True)
            repeated.append(receipt)
    report['G4'] = dict(passed=True, keys=len(repeated), receipts=repeated, synthetic=synthetic())
    write_json(out, 'sbl_g4.json', report['G4'])
    report['smoke_cpu_seconds'] = [s for r in repeated for s in r['cpu_seconds']]
    return report
