"""Score the new 2,400 MIXED8 frames, with a separate historical description."""

import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import numpy as np

PRIOR = Path(__file__).resolve().parents[1] / 'gamma0_mixed8_20261120'
PRIOR_RESULTS = PRIOR / 'out/main_20261120/results.json'
PRIOR_VERDICT_SHA256 = '16f1502d93cf2dde2904161246c2fd1833321148d0dfbfb6fc2d7a00d139ce30'
PRIOR_RESULTS_SHA256 = '41658090666b154d3ec7fe9a34dbc63578b980188e0678b1e82fdabc652c8a28'
SAMPLING = PRIOR.parent / 'tf_covariance_audit_20261018/sampling.py'
SAMPLING_SHA256 = 'b27b70ef42c247b4dfc81d382131880c08ca630b3b9d675f67730946be9b97a3'
PRIOR_FRAMES = (2200, 2799)
N_FRAMES = 2400
ARMS = ('F0', 'CD', 'Z', 'H', 'S', 'Z-sel')
FER_PAIRS = (('H', 'CD'), ('Z-sel', 'Z'))


def checked_bytes(path, expected):
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError(f'Frozen checksum mismatch: {path}')
    return data


checked_bytes(PRIOR / 'verdict.py', PRIOR_VERDICT_SHA256)
checked_bytes(SAMPLING, SAMPLING_SHA256)
spec = spec_from_file_location('gamma0_mixed8_leg2_verdict', PRIOR / 'verdict.py')
leg2 = module_from_spec(spec)
spec.loader.exec_module(leg2)
read_rows = leg2.read_rows
MARGIN = leg2.P_F[0]
if Path(leg2.bootstrap_means.__code__.co_filename).resolve() != SAMPLING:
    raise ValueError('Unexpected paired bootstrap implementation')


def classify(lo, hi, anchors_pass):
    if not anchors_pass:
        return dict(Q1='ANCHOR_FAIL', Q2='ANCHOR_FAIL')
    q1 = 'CD_BETTER' if lo > 0 else 'Z_BETTER' if hi < 0 else 'NO_DIFFERENCE_SHOWN'
    q2 = 'EQUIVALENT' if -MARGIN <= lo <= hi <= MARGIN else 'NOT_EQUIVALENT'
    return dict(Q1=q1, Q2=q2)


def paired_difference(z, cd):
    both = int(np.count_nonzero(z & cd))
    z_only = int(z.sum()) - both
    cd_only = int(cd.sum()) - both
    return leg2.newcombe10(both, z_only, cd_only, len(z) - both - z_only - cd_only)


def historical_panel(path=PRIOR_RESULTS):
    """Recover paired counts from the verified, committed leg-2 aggregate."""
    result = json.loads(checked_bytes(path, PRIOR_RESULTS_SHA256))
    config = result['_config']
    panel = (tuple(config['frames_inclusive']), config['scenario'], config['rho'], config['snr_db'])
    if panel != (PRIOR_FRAMES, 'MIXED8', .5, 7) or result['frames'] != leg2.N_FRAMES:
        raise ValueError('Unexpected historical MIXED8 panel')
    cells = result['primary']['P-F']['cells']
    if (sum(cells.values()) != leg2.N_FRAMES
            or cells['both'] + cells['z_only'] != result['secondary']['fer']['Z']['count']
            or cells['both'] + cells['cd_only'] != result['secondary']['fer']['CD']['count']):
        raise ValueError('Inconsistent historical MIXED8 failure counts')
    return dict(frames=leg2.N_FRAMES, frames_inclusive=list(PRIOR_FRAMES), cells=cells,
                producing_revision=config['producing_revision'], freeze_revision=config['freeze_revision'],
                results_sha256=PRIOR_RESULTS_SHA256)


def pooled_description(new_cells, historical):
    cells = {name: value + historical['cells'][name] for name, value in new_cells.items()}
    n = sum(cells.values())
    if n != N_FRAMES + leg2.N_FRAMES:
        raise ValueError('Expected a 3,000-frame descriptive pool')
    return dict(frames=n, point=(cells['z_only'] - cells['cd_only']) / n, cells=cells,
                historical=historical, use='descriptive only')


def ordered_rows(rows, frames):
    frames = tuple(sorted(frames))
    if (len(frames) != N_FRAMES or type(frames[0]) is not int or frames[0] <= PRIOR_FRAMES[-1]
            or frames != tuple(range(frames[0], frames[0] + N_FRAMES))):
        raise ValueError(f'Expected {N_FRAMES} contiguous frame IDs after the historical panel')
    available, indexed = set(frames), {}
    for row in rows:
        frame, arms, syndrome = row['frame'], row['arms'], row['syndrome']
        if (type(frame) is not int or frame not in available or frame in indexed
                or row['scenario'] != 'MIXED8' or row['snr_db'] != 7 or set(arms) != set(ARMS)
                or type(syndrome) is not int or syndrome < 0 or row.get('status') == 'error'):
            raise ValueError(f'Unexpected, duplicate or failed MIXED8 replication row: {frame!r}')
        if arms['Z-sel']['atoms'] != arms['Z']['atoms']:
            raise ValueError(f'Z-sel changed Z support on frame {frame}')
        for name, arm in arms.items():
            errors = arm['info_errors']
            if type(errors) is not int or errors < 0:
                raise ValueError(f'Invalid information errors on frame {frame}, arm {name}')
            if not syndrome and any(arm[key] != arms['F0'][key] for key in ('info_errors', 'decoded_sha', 'atoms')):
                raise ValueError(f'Nontriggered frame {frame} did not pass F0 through on {name}')
        indexed[frame] = row
    if indexed.keys() != available:
        raise ValueError(f'Expected {N_FRAMES} MIXED8 replication rows, got {len(indexed)}')
    return [indexed[frame] for frame in frames], frames


def analyze(rows, frames):
    """Apply frozen inference to the new rows only, then pool counts descriptively."""
    historical = historical_panel()
    rows, frames = ordered_rows(rows, frames)
    records = {arm: [leg2.support(row['arms'][arm]) for row in rows] for arm in ARMS}
    values = {(arm, name): np.asarray([row[name] for row in panel])
              for arm, panel in records.items() for name in panel[0]}

    def metric(arm, name):
        return values[arm, name]

    anchors = leg2.check_anchors(metric('CD', 'fer'), metric('S', 'fer'))
    fer = paired_difference(metric('Z', 'fer'), metric('CD', 'fer'))
    primary = dict(fer, margin=MARGIN, **classify(fer['ci_lo'], fer['ci_hi'], anchors['passed']))
    occupancy = paired_difference(metric('Z', 'two_atoms_0.35'), metric('CD', 'two_atoms_0.35'))
    phantoms = ('singleton_phantom', 'close_phantom', 'singleton_phantom_le_025')
    drawn = {(arm, name): data for (arm, name), data in values.items()
             if name in ('fer', 'two_atoms_0.35', 'two_atoms_0.75', *(f'{p}_frame' for p in phantoms))
             or name.startswith('omitted_')}
    contrasts = {(arm, ref, 'fer'): metric(arm, 'fer') - metric(ref, 'fer') for arm, ref in FER_PAIRS}
    drawn.update(contrasts)
    for gap in leg2.GAPS:
        label = f'power_{gap}'
        power = metric('CD', label)
        if any(not np.array_equal(metric(arm, label), power) for arm in ARMS):
            raise ValueError(f'Unpaired true energy at separation {gap}')
        drawn['truth', label] = power
    draws, n = leg2.bootstrap_means(drawn, frames, n_boot=leg2.N_BOOT, seed=leg2.SEED)
    points = {key: float(data.mean()) for key, data in drawn.items()}

    def estimate(key):
        return dict(point=points[key], **leg2.interval(draws[key]))

    secondary_fer = {}
    for key, delta in contrasts.items():
        arm, ref, _ = key
        secondary_fer[f'{arm}_minus_{ref}'] = dict(estimate(key), only_first_failed=int((delta == 1).sum()),
                                                 only_second_failed=int((delta == -1).sum()))
    geometry = {}
    for arm in ARMS:
        geometry[arm] = {
            label: dict(count=int(metric(arm, label).sum()), **estimate((arm, label)))
            for label in ('two_atoms_0.35', 'two_atoms_0.75', *(f'{p}_frame' for p in phantoms))
        }
        geometry[arm].update({f'{p}_delay_groups': int(metric(arm, p).sum()) for p in phantoms})
        geometry[arm]['omitted_energy_fraction'] = {
            gap: leg2.ratio_summary(points, draws, {(arm, f'omitted_{gap}'): 1}, {('truth', f'power_{gap}'): 1})
            for gap in leg2.GAPS}
    return dict(
        frames=n, triggered=sum(row['syndrome'] > 0 for row in rows),
        bootstrap=dict(draws=leg2.N_BOOT, seed=leg2.SEED, unit='physical frame', use='secondary readouts only'),
        anchors=anchors, primary=primary,
        secondary=dict(fer={arm: dict(count=int(metric(arm, 'fer').sum()), **estimate((arm, 'fer'))) for arm in ARMS},
                       fer_contrasts=secondary_fer, geometry=geometry,
                       occupancy_z_minus_cd_035=occupancy,
                       occupancy_discordance_035=leg2.occupancy_discordance(rows),
                       pooled_fer_z_minus_cd=pooled_description(fer['cells'], historical)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rows', nargs='+', type=Path)
    parser.add_argument('--frame-start', required=True, type=int)
    parser.add_argument('--out', required=True, type=Path)
    cli = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(cli)
    frames = range(args.frame_start, args.frame_start + N_FRAMES)
    result = analyze(read_rows(args.rows), frames)
    config = dict(frames_inclusive=[frames.start, frames.stop - 1], scenario='MIXED8', snr_db=7, rho=.5,
                  rows=[str(path) for path in args.rows], out=str(args.out),
                  historical_results=str(PRIOR_RESULTS), historical_results_sha256=PRIOR_RESULTS_SHA256)
    with args.out.open('x') as handle:
        json.dump(dict(_argv=list(cli), _config=config, **result), handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
