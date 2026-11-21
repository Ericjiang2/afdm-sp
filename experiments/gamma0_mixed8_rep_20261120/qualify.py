"""Verify leg-2 identity and time the six replication arms on audited smoke frames."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import process_time

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
LEG2 = EXP/'gamma0_mixed8_20261120'
MAIN = LEG2/'out/main_20261120'
P1 = EXP/'gamma0_exchange_20261120'
REVISION = '5051bcbaac5143589f32d90d017e3f7942ab55c0'
MAIN_SHA = '41658090666b154d3ec7fe9a34dbc63578b980188e0678b1e82fdabc652c8a28'
MANIFEST_SHA = 'e280de3bbd7bce72162ffee6ee92f6d0bf4f837b7ee792895fe25cda82a480be'
ARMS = ('F0', 'CD', 'Z', 'H', 'S', 'Z-sel')
WORKERS = 23


def checked_bytes(path, expected):
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError(f'Leg-2 source or receipt checksum differs: {path}')
    return data


def verify_leg2():
    result = json.loads(checked_bytes(MAIN/'results.json', MAIN_SHA))
    config = result['_config']
    if (config['producing_revision'] != REVISION or config['frames_inclusive'] != [2200, 2799]
            or result['frames'] != 600 or (MAIN/'STATUS').read_text().strip() != 'DONE'
            or config['arms'] != ['F0', 'CD', 'Z', 'H', 'S', 'A2g', 'Z-sel', 'TRUE_GEOMETRY']):
        raise ValueError('Unexpected leg-2 producing revision, panel, or arms')
    manifest = {name: digest for digest, name in
                (line.split() for line in checked_bytes(MAIN/'SOURCE_SHA256.txt', MANIFEST_SHA).decode().splitlines())}
    if manifest != config['source_sha256']:
        raise ValueError('Leg-2 source manifest differs from the producing receipt')
    for name, expected in manifest.items():
        checked_bytes(LEG2/name, expected)
    bound = config['source']['bound_source_sha256']
    for name, expected in bound.items():
        checked_bytes(EXP/name, expected)
    for name in ('g1', 'g2_g4_synthetic', 'g5_and_detector'):
        if json.loads((LEG2/f'out/{name}.json').read_bytes())['status'] != 'PASS':
            raise ValueError(f'Reused qualification did not pass: {name}')
    return result


def verify_audit(path, rng):
    audit = json.loads(path.read_bytes())
    fresh, smoke = audit['fresh'], audit['smoke']
    if (audit['status'] != 'PASS' or len(fresh) != 2 or fresh[1] - fresh[0] != 2399 or fresh[0] < 2800
            or len(smoke) != 3 or len(set(smoke)) != 3 or not all(211 <= n < 1000 for n in smoke)
            or {field: audit[field] for field in ('entropy', 'domain')} != rng):
        raise ValueError('Invalid fresh or smoke frame audit')
    evidence = {name: sha256((path.parent/name).read_bytes()).hexdigest()
                for name in ('frame_audit_local.json', 'frame_audit_deinlab.json')}
    if audit['audit_sha256'] != evidence:
        raise ValueError('Frame audit does not bind both receipts')
    return audit


def write(path, payload):
    with path.open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if (args.out.resolve() != HERE/'out' or args.audit.resolve() != HERE/'out/g3.json'
            or os.environ.get('CUDA_VISIBLE_DEVICES') != ''
            or any(os.environ.get(key) != '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                                          'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))):
        raise ValueError('Expected the study output directory and CPU-only single-thread binding')

    result = verify_leg2()
    producing = result['_config']
    audit = verify_audit(args.audit, producing['source']['rng'])
    sys.path[:0] = [str(LEG2), str(P1)]
    from phase1 import preflight
    import mixed_paired
    if (Path(sys.modules[preflight.__module__].__file__).resolve() != P1/'phase1.py'
            or Path(mixed_paired.__file__).resolve() != LEG2/'mixed_paired.py'
            or Path(mixed_paired.p1.__file__).resolve() != P1/'paired.py'):
        raise ValueError('Wrong leg-2 receiver or P1 wrapper import')
    binding = preflight()
    started = process_time()
    loaded, source = mixed_paired.context()
    startup = process_time() - started
    if source != producing['source']:
        raise ValueError('Actual receiver context differs from leg 2')
    config = dict(_argv=sys.argv, _config=dict(
        arms=ARMS, phase1_snr_db=6, main_snr_db=7, rho=.5, scenario='MIXED8',
        fresh=audit['fresh'], smoke=audit['smoke'], binding=binding,
        source=source, leg2_producing_revision=REVISION, leg2_results_sha256=MAIN_SHA,
        leg2_source_manifest_sha256=MANIFEST_SHA,
        leg2_bound_files=producing['source_sha256'],
        audit_sha256=sha256(args.audit.read_bytes()).hexdigest(),
        phase1_code_sha256={name: sha256((HERE/name).read_bytes()).hexdigest()
                            for name in ('audit.py', 'qualify.py', 'launch_phase1.sh')}))
    write(args.out/'phase1_config.json', config)
    write(args.out/'identity.json', dict(status='PASS', checked_main_files=len(producing['source_sha256']),
          checked_receiver_sha256_files=len(source['bound_source_sha256']),
          checked_frozen_md5_files=len(source['frozen_source_md5']),
          gates={gate: 'PASS by leg-2 receipt and source identity' for gate in ('G1', 'G2', 'G4')},
          producing_revision=REVISION))

    samples, continuation_times = [], []
    for frame in audit['smoke']:
        row, times = mixed_paired.one(loaded, frame, 6, arms=ARMS)
        assert set(row['arms']) == set(ARMS)
        assert row['arms']['Z-sel']['atoms'] == row['arms']['Z']['atoms']
        assert set(times) == {'shared', *ARMS[1:]}
        if row['syndrome']:
            continuation_times.append(times)
        samples.append(dict(frame=frame, cpu_seconds=times, six_arm_schema=True, z_sel_support_parity=True))
    if not continuation_times:
        raise ValueError('No timed smoke frame exercised the receiver continuation')
    shared = max(sample['cpu_seconds']['shared'] for sample in samples)
    branches = sum(max(t[arm] for t in continuation_times) for arm in ARMS[1:])
    old_trigger_fraction = result['triggered'] / result['frames']
    seconds = 2400 * (shared + old_trigger_fraction * branches) + WORKERS * startup
    write(args.out/'g5.json', dict(
        status='PASS', samples=samples, frames_projected=2400, multiplier=1.3,
        projection_core_hours=1.3 * seconds/3600, startup_cpu_seconds=startup,
        startup_workers=WORKERS, leg2_trigger_fraction=old_trigger_fraction,
        timing_method='Peak measured component times, weighted by leg-2 7 dB trigger fraction'))


if __name__ == '__main__':
    main()
