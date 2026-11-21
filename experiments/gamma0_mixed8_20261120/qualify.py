"""Phase 1 only: archive replay, synthetic gates, and three audited smoke frames."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import process_time

from mixed_paired import ARMS, HERE, P1, REFERENCE, close_singletons, context, one, p1

ARCHIVE = REFERENCE/'out/main_20261119'
PINS = {'config.json': 'fd08677b5c53161197489a8d3eb9992f',
        'REMOTE_ROWS_MD5.txt': 'b08c509b8e84ef0117c0701b540771d3',
        'rows.jsonl': '3fb82ceaba80cac43c307b19f95c489e'}


def read(path):
    return json.loads(path.read_bytes())


def archive_panel():
    for name, expected in PINS.items():
        p1.verify_file(ARCHIVE/name, expected)
    config = read(ARCHIVE/'config.json')['_config']
    if (config['fresh_inclusive_block'] != [1000, 1599] or config['rho'] != .5
            or config['snr_db'] != 7 or config['scenario'] != 'MIXED8'
            or (ARCHIVE/'STATUS').read_text().strip() != 'DONE'):
        raise ValueError('Wrong archived MIXED8 panel')
    with (ARCHIVE/'rows.jsonl').open() as handle:
        rows = sorted((json.loads(line) for line in handle), key=lambda row: row['frame'])
    if [r['frame'] for r in rows] != list(range(1000, 1600)):
        raise ValueError('Archive panel coverage differs')
    return rows, config


def g1(loaded, rows):
    ref = loaded[0]
    equal = ref.screen.e2.e1d.e1_lib.deep_equal
    for expected in rows:
        frame = expected['frame']
        got, _ = one(loaded, frame, 7, arms=('CD', 'S'))
        archive = {key: expected[key] for key in got if key != 'arms'}
        same = equal(archive, {key: got[key] for key in archive})
        for old, new in (('F0', 'F0'), ('CD', 'CD'), ('A2', 'S')):
            a = {key: value for key, value in expected['arms'][old].items() if key != 'seconds'}
            same.extend(equal(a, {k: got['arms'][new][k] for k in a}))
        if same:
            raise ValueError(f'Frozen archive parity failed for frame {frame}: {same[:4]}')
    return dict(status='PASS', frames=len(rows), interval=[1000, 1599], arms=['F0', 'CD', 'S'],
                archive_md5=PINS, compared='All saved non-timing fields for F0, CD and A2/S and the paired input identity')


def smoke(loaded, frames, historical_trigger_fraction):
    ref, ctx, *_ = loaded
    records, eligible = [], []
    stage = ref.cstate.stage3
    for frame in frames:
        observed, inputs = p1.detector_observer(stage, ctx)
        row, times = one(loaded, frame, 6, contexts={'CD': observed, 'Z': observed})
        assert len(inputs) in (0, 2)
        assertions = dict(fixed_support=row['arms']['Z-sel']['atoms'] == row['arms']['Z']['atoms'],
                          true_geometry=len(row['arms']['TRUE_GEOMETRY']['atoms']) == 8)
        assert all(assertions.values())
        if inputs:
            diff = ref.screen.e2.e1d.e1_lib.deep_equal(inputs[0], inputs[1])
            if diff:
                raise AssertionError(f'Detector inputs differ beyond paths and gains: {diff}')
            assertions.update(detector_input_parity=True, a2g_guard=True)
            eligible.append(times)
        records.append(dict(frame=frame, assertions=assertions, cpu_seconds=times))
    if not eligible:
        raise AssertionError('Audited smoke timing lacks a measured exchange continuation')
    shared = max(r['cpu_seconds']['shared'] + r['cpu_seconds']['TRUE_GEOMETRY'] for r in records)
    continuation = sum(max(r[arm] for r in eligible) for arm in ARMS if arm not in ('F0', 'TRUE_GEOMETRY'))
    hours = 1.3 * 600 * (shared + historical_trigger_fraction * continuation) / 3600
    return dict(status='PASS', samples=records, snr_db=6, frames_projected=600, multiplier=1.3,
                projection_core_hours=hours, historical_trigger_fraction=historical_trigger_fraction,
                timing_method='Max observed component times, weighted by the archived trigger fraction')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('archive', 'gates'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.mode == 'gates' and args.audit is None:
        parser.error('Smoke qualification requires a completed frame audit')
    started = process_time()
    from phase1 import preflight, synthetic_geometry
    if Path(sys.modules[preflight.__module__].__file__).resolve() != P1/'phase1.py':
        raise ValueError('Imported the wrong Phase 1 gate helper')
    binding = preflight()
    loaded, source = context()
    archive, config = archive_panel()
    if source['rng'] != config['seed']:
        raise ValueError('Frozen generator identity differs from the archived panel')
    script_sha = {p.name: sha256(p.read_bytes()).hexdigest() for p in (HERE/'mixed_paired.py', Path(__file__))}

    def write(name, value):
        loaded[0].cstate.stage3.write_json(args.out/f'{name}.json', value)
        print(f'{name} written', flush=True)

    if args.mode == 'archive':
        write('archive_config', dict(_argv=sys.argv, _config=dict(binding=binding, source=source,
                                                               source_sha256=script_sha)))
        write('g1', g1(loaded, archive))
        write('archive_done', dict(status='DONE', cpu_seconds=process_time() - started))
        return

    g1_config = read(args.out/'archive_config.json')['_config']
    if (read(args.out/'g1.json')['status'] != 'PASS'
            or read(args.out/'archive_done.json')['status'] != 'DONE'
            or g1_config['source'] != source or g1_config['source_sha256']['mixed_paired.py'] != script_sha['mixed_paired.py']):
        raise ValueError('Gate context differs from the G1 replay')
    audit = read(args.audit)
    evidence = tuple(args.audit.parent/name for name in ('frame_audit_local.json', 'frame_audit_deinlab.json'))
    if (audit['status'] != 'PASS'
            or audit['audit_sha256'] != {p.name: sha256(p.read_bytes()).hexdigest() for p in evidence}
            or {field: audit[field] for field in ('entropy', 'domain')} != source['rng']):
        raise ValueError('Frame audit did not pass')
    fresh, frames = audit['fresh'], audit['smoke']
    if (len(fresh) != 2 or fresh[1] - fresh[0] != 599 or fresh[0] < 1600
            or len(frames) != 3 or len(set(frames)) != 3
            or set(frames).intersection(range(fresh[0], fresh[1] + 1))
            or set(frames).intersection((*range(100, 196), *range(1000, 1600)))):
        raise ValueError('Audit chose an invalid fresh or smoke panel')

    write('phase1_config', dict(_argv=sys.argv, _config=dict(
        binding=binding, source=source, source_sha256=script_sha, arms=ARMS, rho=.5, snr_db=7,
        audit_sha256=sha256(args.audit.read_bytes()).hexdigest(), fresh=fresh, smoke=frames)))
    _, _, full, cd, _, slicer = loaded
    receipt = synthetic_geometry(cd, full, slicer)
    assert close_singletons([6, 6, 31, 43],
                            [[6, 0], [6, .1], [31, 0], [31, .25], [43, 0], [43, .2501]]) == 1
    write('g2_g4_synthetic', receipt)
    write('g5_and_detector', smoke(loaded, frames, sum(bool(r['syndrome']) for r in archive)/len(archive)))
    write('phase1_done', dict(status='DONE', cpu_seconds=process_time() - started))


if __name__ == '__main__':
    main()
