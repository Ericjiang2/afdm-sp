"""MIXED8 qualification against the frozen doublet-conflict archive."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from s_arm import gate_source
from x_arm import ARCHIVE_FRAMES, EXPERIMENTS, SOURCE, canonical_bytes, cstate, frozen, gated_route, one, resolution

ARCHIVE = SOURCE / 'out/main_20261119'
ROWS_MD5 = '3fb82ceaba80cac43c307b19f95c489e'
CONFIG_SHA256 = '02dc557e6d2e7023ecc56b39c02b8f2bc57f0cfce5decff503a1330f65d45cb4'
FRAME_FIELDS = ('scenario', 'frame', 'snr_db', 'syndrome', 'closure', 'entering_slots',
                'info_sha', 'noise_sha', 'doublet_separations', 'inputs', 'truth')


def _archive_and_context():
    if (ARCHIVE / 'STATUS').read_text().strip() != 'DONE':
        raise RuntimeError('MIXED8 requires a completed archive')
    raw = (ARCHIVE / 'rows.jsonl').read_bytes()
    config_raw = (ARCHIVE / 'config.json').read_bytes()
    if hashlib.md5(raw).hexdigest() != ROWS_MD5 or hashlib.sha256(config_raw).hexdigest() != CONFIG_SHA256:
        raise RuntimeError('MIXED8 archive rows or configuration differ from res-20261119-04')
    config = json.loads(config_raw)['_config']
    if (config['scenario'], config['rho'], config['snr_db'], config['tau'], config['fresh_inclusive_block']) != (
            frozen.SCENARIO, frozen.screen.RHO, frozen.MAIN_SNR_DB, frozen.TAU, [1000, 1599]):
        raise RuntimeError('MIXED8 archive has a different design')
    source = Path(frozen.__file__).resolve()
    root = EXPERIMENTS.parent
    if (source != SOURCE / 'mixed8_receiver.py' or
            hashlib.sha256(source.read_bytes()).hexdigest() != config['sha256'][source.relative_to(root).as_posix()]):
        raise RuntimeError(f'Loaded MIXED8 receiver differs from archive: {source}')
    for name, expected in config['frozen_source_md5'].items():
        if hashlib.md5((root / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'MIXED8 dependency differs from archive: {name}')
    context = frozen.context()
    if (context[-1] != config['loaded_source_checks'] or
            dict(entropy=frozen.screen.ENTROPY, domain=frozen.screen.DOMAIN) != config['seed']):
        raise RuntimeError('Loaded MIXED8 source inventory or RNG differs from archive')
    loaded_paths = frozen.source_files()
    for name, actual in loaded_paths.items():
        if name not in config['frozen_source_md5'] or Path(actual).resolve() != root / name:
            raise RuntimeError(f'Unexpected loaded MIXED8 dependency: {name} from {actual}')
    gate = gate_source()
    rows = {}
    for line in raw.splitlines():
        row = json.loads(line)
        frame = row['frame']
        if (type(frame) is not int or frame not in frozen.MAIN_FRAMES or frame in rows
                or row['scenario'] != frozen.SCENARIO or row['snr_db'] != frozen.MAIN_SNR_DB
                or any(row[key] != config[key] for key in ('freeze_commit', 'launch_commit'))):
            raise RuntimeError(f'MIXED8 archive row identity mismatch on frame {frame}')
        rows[frame] = row
    if set(rows) != set(frozen.MAIN_FRAMES):
        raise RuntimeError('MIXED8 archive does not cover its complete frozen cohort')
    provenance = dict(archive_path=str(ARCHIVE), archive_rows_md5=ROWS_MD5,
                      archive_config_sha256=CONFIG_SHA256, producing_commit=config['freeze_commit'],
                      launch_commit=config['launch_commit'], archive_trigger_count=sum(bool(row['syndrome'])
                                                                                   for row in rows.values()),
                      archive_frames=len(rows), frozen_source_md5=config['frozen_source_md5'],
                      frozen_gate_path=gate.__file__, loaded_paths=loaded_paths,
                      receiver_sha256=config['sha256'][source.relative_to(root).as_posix()])
    return context[:3], {frame: rows[frame] for frame in ARCHIVE_FRAMES}, provenance


def _archive_match(row, archive, arms):
    for field in FRAME_FIELDS:
        if canonical_bytes(row[field]) != canonical_bytes(archive[field]):
            raise RuntimeError(f'MIXED8 frozen archive mismatch on frame {row["frame"]}, frame field {field}')
    fingerprints = {}
    for candidate, reference in arms.items():
        expected = {key: value for key, value in archive['arms'][reference].items() if key != 'seconds'}
        actual = row['arms'][candidate]
        encoded = canonical_bytes(actual)
        if encoded != canonical_bytes(expected):
            keys = sorted(expected.keys() | actual.keys())
            changed = [key for key in keys if key not in actual or key not in expected
                       or canonical_bytes(actual[key]) != canonical_bytes(expected[key])]
            raise RuntimeError(f'MIXED8 frozen archive mismatch on frame {row["frame"]}, '
                               f'{candidate} vs {reference}, fields {changed}')
        fingerprints[candidate] = hashlib.sha256(encoded).hexdigest()
    return fingerprints


def synthetic(full, cd):
    """Check active direct scores and independent no-op geometry on synthetic inputs."""
    n = 32
    rng = np.random.default_rng(42713)
    y = rng.normal(size=n) + 1j * rng.normal(size=n)
    x = .2 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    v = np.linspace(.05, .4, n)
    opts = dict(c1=.02, c2=.01, ridge=.1, max_delay=4, max_edits=2,
                chunk_size=64, local_passes=2, gamma_mode='full', strategy='compact')
    initial = [cd.Path(0, .001), cd.Path(0, .103), cd.Path(2, .25)]
    route = gated_route(full, cd, check_scores=True)
    activated = route.reopen_geometry(y, x, v, initial, **opts)
    assert route.census['checked_trials'] > 0 and route.census['nonempty_trials'] > 0
    assert route.census['passes_checked'] == opts['local_passes']
    assert np.linalg.eigvalsh(activated.diagnostics['gamma']).min() >= -1e-12

    single_path = [cd.Path(0, .001)]
    reference = cd.reopen_geometry(y, x, v, single_path, **opts)
    route_noop = gated_route(full, cd, cd_result=reference)
    no_op = route_noop.reopen_geometry(y, x, v, single_path, **opts)
    assert route_noop.census['used_cd_noop'] and not route_noop.census['nonempty_trials']
    assert canonical_bytes(cstate._geometry_record(no_op)) == canonical_bytes(cstate._geometry_record(reference))
    for actual, expected in zip(no_op.global_trace, reference.global_trace, strict=True):
        np.testing.assert_array_equal(actual['scores'], expected['scores'])

    truth = dict(l_i=[6, 6, 22, 22], k_real=[0, .35, 0, .75])
    assert resolution(truth, [[6, .44], [6, -.10], [6, .9]])['resolved']
    assert not resolution(truth, [[6, 0], [6, .451]])['resolved']
    assert not resolution(truth, [[6, 0], [6, 0], [22, .35]])['resolved']
    return dict(pass_=True, checked_trials=route.census['checked_trials'],
                max_relative_score_error=route.census['max_relative_score_error'],
                no_op_scores_equal=True, assignment_checks=3)


def _save_rows(out, name, rows):
    if out is not None:
        with (Path(out) / name).open('xb') as handle:
            for row in rows:
                handle.write(canonical_bytes(row) + b'\n')


def run(out=None):
    context, archive, provenance = _archive_and_context()
    synthetic_checks = synthetic(*context[1:])
    qualified, substitution_rows = [], []
    for frame in ARCHIVE_FRAMES:
        row = one(*context, frame, gate='low')
        reference = archive[frame]
        fingerprints = _archive_match(row, reference, {'F0': 'F0', 'CD': 'CD', 'G-ex': 'U'})
        census = {key: value for key, value in reference['census'].items() if key != 'decisions_differ'}
        if (canonical_bytes(row['gate_census']) != canonical_bytes(census) or
                (row['arms']['CD']['decision'] != row['arms']['G-ex']['decision']) !=
                reference['census']['decisions_differ']):
            raise RuntimeError(f'MIXED8 frozen U census differs on frame {frame}')
        qualified.append(dict(frame=frame, source_sha256=fingerprints, trigger=bool(row['syndrome'])))
        substitution_rows.append(row)
    _save_rows(out, 'x_substitution_rows.jsonl', substitution_rows)
    g2 = dict(pass_=True, frames=len(qualified), byte_identical_to_U=len(qualified),
              compared_arm_fields='all archive non-timing fields', synthetic=synthetic_checks, samples=qualified)

    trials, projected, gate_rows = [], [], []
    for frame in ARCHIVE_FRAMES:
        row = one(*context, frame, gate='actual')
        _archive_match(row, archive[frame], {'F0': 'F0', 'CD': 'CD'})
        census = row['gate_census']
        fingerprints = row['output_fingerprints']
        same = fingerprints['G-ex'] == fingerprints['CD']
        active_elsewhere = (bool(census['active_refits']) or
                            any(block['gate_rank'] for blocks in census['local_pass_blocks'] for block in blocks) or
                            any(block['gate_rank'] for block in census['final_blocks']))
        all_empty = not (census['nonempty_trials'] or active_elsewhere)
        if all_empty and not same:
            raise AssertionError(f'G-ex and CD differ with empty effective projectors on frame {frame}: {census}')
        trials.append(dict(frame=frame, byte_identical_to_CD=same, all_effective_projectors_empty=all_empty,
                           active_outside_legal_trials=active_elsewhere, gate_census=census,
                           output_fingerprints=fingerprints, arm_diagnostics=row['arm_diagnostics']))
        projected.append(dict(frame=frame, triggered=bool(row['syndrome']), seconds=row['cpu_seconds'],
                              by_arm=row['arm_cpu_seconds']))
        gate_rows.append(row)
    _save_rows(out, 'x_gate_rows.jsonl', gate_rows)

    g5 = dict(pass_=True, frames=len(trials), byte_identical_to_CD=sum(row['byte_identical_to_CD'] for row in trials),
              frames_with_firing=sum(row['gate_census']['nonempty_trials'] > 0 for row in trials),
              frames_all_projectors_empty=sum(row['all_effective_projectors_empty'] for row in trials),
              frames_fired_only_outside_legal_trials=sum(not row['gate_census']['nonempty_trials']
                                                         and row['active_outside_legal_trials'] for row in trials),
              fired_trial_supports=sum(row['gate_census']['nonempty_trials'] for row in trials),
              legal_trial_supports=sum(row['gate_census']['valid_trials'] for row in trials),
              fired_scored_supports=sum(row['gate_census']['nonempty_scored_trials'] for row in trials),
              scored_supports=sum(row['gate_census']['scored_trials'] for row in trials), samples=trials)
    trigger_rate = provenance['archive_trigger_count'] / provenance['archive_frames']
    means = {label: float(np.mean([row['seconds'] for row in projected if row['triggered'] == flag]))
             for label, flag in (('triggered', True), ('untriggered', False))}
    cpu_per_frame = trigger_rate * means['triggered'] + (1 - trigger_rate) * means['untriggered']
    cost = dict(sample_frames=len(projected), measured_cpu_seconds=sum(row['seconds'] for row in projected),
                archive_trigger_rate=trigger_rate, mean_cpu_seconds=means, projected_cpu_seconds_per_frame=cpu_per_frame,
                projected_600_core_hours_x1p3=cpu_per_frame * 600 * 1.3 / 3600, samples=projected)
    return dict(_argv=sys.argv, _config=dict(frames=list(ARCHIVE_FRAMES), snr_db=frozen.MAIN_SNR_DB,
                                           rho=frozen.screen.RHO, cost_multiplier=1.3),
                G2=g2, G5=g5, cost=cost, source=provenance)


if __name__ == '__main__':
    from s_gates import write_json

    out = Path(sys.argv[1]).resolve()
    if out.parent != Path(__file__).resolve().parent / 'out' or not out.name.startswith('phase1_'):
        raise ValueError('MIXED8 receipts require a Phase 1 output directory')
    qualification = run(out)
    for gate in ('G2', 'G5'):
        write_json(out, f'x_{gate.lower()}.json', qualification.pop(gate))
    write_json(out, 'x_qualification.json', qualification)
