"""Analyze development blocks with the single frozen global contrast registry.

This reuses the campaign CP engine. It never turns development data into
independent confirmation, including when a numerical interval clears a gate.
"""
import numpy as np

from .supplement_statistics import linear_contrast, paired_delta


FAMILIES = {'H-01': 'F_H', 'M-01': 'F_M', 'A-01': 'F_A', 'I-02': 'F_I'}


def arm_map(stage, detectors):
    if stage not in FAMILIES:
        raise ValueError('unknown development stage')
    if len(detectors) != 2 or detectors[0] != 'BP' or detectors[1] in ('BP', 'EP10'):
        raise ValueError('development requires BP and its distinct frozen reference')
    if stage == 'I-02':
        return dict(scalar_base='I02-baseline', scalar_calibrated='I02-scalar',
                    diagonal='I02-diagonal', low_rank='I02-lowrank')
    result = {}
    for symbolic, detector in zip(('BP', 'REF'), detectors):
        if stage == 'H-01':
            for c, cancel in enumerate(('estimated', 'true')):
                for d, data in enumerate(('estimated', 'true')):
                    result[f'{symbolic}:C{c}D{d}'] = f'cancel_{cancel}__data_{data}__{detector}'
        elif stage == 'M-01':
            for arm in ('free', 'group', 'link', 'sham'):
                result[f'{symbolic}:{arm}'] = f'{arm}__{detector}'
        else:
            for g, geometry in enumerate(('est', 'true')):
                for c, constraint in enumerate(('none', 'soft', 'hard')):
                    for d, data in enumerate(('xsoft', 'xtrue')):
                        result[f'{symbolic}:core:g{g}c{c}d{d}'] = (
                            f'{geometry}-{constraint}-{data}__{detector}')
            for mask in ('S0', 'I'):
                for constraint in ('soft', 'hard'):
                    result[f'{symbolic}:bridge:{mask}:{constraint}'] = (
                        f'{mask}-{constraint}__{detector}')
    return result


def development_table(stage, cells, detectors, blocks):
    """Bind every raw record before selecting per-arm paired block vectors."""
    names = arm_map(stage, detectors).values()
    expected = {(snr, name, block) for snr in (7, 8, 9)
                for name in names for block in blocks}
    if set(cells) != expected:
        raise ValueError('raw development identity grid differs from the frozen design')
    return {(snr, name): [cells[(snr, name, block)] for block in blocks]
            for snr in (7, 8, 9) for name in names}


def analyze_development(stage, table, detectors, blocks, manifest):
    mapping = arm_map(stage, detectors)
    n = len(blocks)
    if (not n or len(set(blocks)) != n or
            any(type(b) is not int or b < 0 for b in blocks)):
        raise ValueError('unique nonnegative independent block identities required')
    expected = {(snr, raw) for snr in (7, 8, 9) for raw in mapping.values()}
    if set(table) != expected:
        raise ValueError('development cell identities differ from the complete frozen arm grid')
    arrays = {}
    for key, values in table.items():
        vector = np.asarray(values)
        if vector.shape != (n,) or vector.dtype.kind not in 'iu' or np.any((vector < 0) | (vector > 1)):
            raise ValueError('each development cell must contain n binary block outcomes')
        arrays[key] = vector
    family_id = FAMILIES[stage]
    family = manifest['families'][family_id]
    specs, m, alpha = family['contrasts'], family['m_max'], family['alpha']
    if (manifest['status'] != 'FROZEN_GLOBAL_CONTRAST_SUPERSET' or
            len(specs) != m or len({s['id'] for s in specs}) != m or
            family['unused_slots_recycle_alpha']):
        raise ValueError('global manifest contrast reservation mismatch')
    rows = []
    for spec in specs:
        # Other components use different development records but retain their alpha slots.
        if stage == 'A-01' and spec['id'].startswith('legal:'):
            continue
        if stage == 'I-02' and not spec['id'].startswith('cov:'):
            continue
        names, coefficients = spec['arms'], spec['coefficients']
        if any(name not in mapping for name in names):
            raise ValueError('global manifest arm has no declared development binding')
        columns = [arrays[(spec['snr_db'], mapping[name])] for name in names]
        counts = [int(v.sum()) for v in columns]
        pairing = {}
        if spec['method'] == 'paired_CP':
            if coefficients != [1, -1] or len(columns) != 2:
                raise ValueError('paired global manifest contrast requires reference minus candidate')
            ref, arm = columns
            wins = int(np.count_nonzero((ref == 1) & (arm == 0)))
            losses = int(np.count_nonzero((ref == 0) & (arm == 1)))
            bounds = paired_delta(wins, losses, n, alpha_family=alpha, m=m)
            pairing = dict(reference_arm=names[0], candidate_arm=names[1], wins=wins, losses=losses,
                           delta_definition='FER_reference - FER_candidate; positive means improvement')
        elif spec['method'] == 'linear_CP':
            bounds = linear_contrast(counts, coefficients, n, alpha_family=alpha, m=m)
            pairing = dict(delta_definition='sum(coefficients * FER_arms), in the recorded arm order')
        else:
            raise ValueError('unsupported frozen development contrast method')
        rows.append(dict(
            id=spec['id'], family=family_id, snr=spec['snr_db'], n=n,
            arms=list(names), raw_cells=[mapping[name] for name in names],
            coefficients=list(coefficients), error_counts=counts,
            delta=float(bounds['delta']), interval=[float(bounds['lower']), float(bounds['upper'])],
            method=spec['method'], m=m, alpha_family=alpha, tail_alpha=float(bounds['tail']),
            questions=list(spec['questions']), planned_confirmation_sample_set=spec['sample_set'],
            actual_split='design' if stage == 'I-02' else 'mechanism',
            independent_confirmation=False,
            scope=f'{stage} development; frozen global contrasts; not independent {family_id} confirmation',
            **pairing))
    return rows
