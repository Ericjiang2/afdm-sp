"""Registered S-01 candidate contrasts on the original development blocks."""
import numpy as np

from .supplement_statistics import FAMILY_ALPHA, paired_delta


SCENE_MAP = {'integer_doppler': 'integer', 'near_overlap': 'overlap'}


def summarize_candidate_metrics(cells, diagnostics, power):
    """Keep score, saved-terminal and regenerated-power denominators separate."""
    if set(power) != set(cells):
        raise ValueError('power audit coverage differs from the score grid')
    if set(diagnostics) - set(cells):
        raise ValueError('diagnostic identity is outside the score grid')
    grouped = {}
    for key in cells:
        block, snr, scene, arm = key
        grouped.setdefault((scene, snr, arm), []).append(key)
    result = {}
    for (scene, snr, arm), keys in grouped.items():
        measured = sorted(key for key in keys if key in diagnostics)
        values = [diagnostics[key] for key in measured]
        result[f'{scene}:{snr}:{arm}'] = dict(
            n=len(keys), frame_errors=sum(cells[key] for key in keys),
            diagnostic_n=len(measured), diagnostic_blocks=[key[0] for key in measured],
            diagnostic_source='saved terminal arrays; no extrapolation to reused score-only records',
            eligibility_n=len(measured),
            ineligible_records=sum(not row['baseline_eligible'] for row in values) if values else None,
            power_n=len(keys), power_violations=sum(not power[key] for key in keys),
            mean_nll=float(np.mean([row['nll'] for row in values])) if values else None,
            mean_brier=float(np.mean([row['brier'] for row in values])) if values else None,
            mean_channel_nmse=float(np.mean([row['nmse'] for row in values])) if values else None)
    return result


def analyze_candidates(cells, freeze, manifest):
    """Analyze the complete measured grid while retaining all F_R alpha slots."""
    aliases = freeze['symbolic_aliases']
    arms = freeze['physical_arms']
    blocks = range(192)
    expected = {(b, s, scene, arm) for b in blocks for s in (7, 8, 9)
                for scene in SCENE_MAP.values() for arm in arms}
    if (freeze['blocks'] != 192 or freeze['split'] != 'counterexample'
            or len(arms) != 12 or len(aliases) != 15 or set(cells) != expected):
        raise ValueError('candidate development identity grid differs from the freeze')
    if any(not isinstance(v, (int, np.integer)) or v not in (0, 1) for v in cells.values()):
        raise ValueError('candidate FER must be binary block outcomes')
    family = manifest['families']['F_R']
    specs = family['contrasts']
    if (manifest['status'] != 'FROZEN_GLOBAL_CONTRAST_SUPERSET'
            or family['m_max'] != 272 or freeze['m'] != 272
            or family['alpha'] != FAMILY_ALPHA or freeze['alpha_family'] != FAMILY_ALPHA
            or family['unused_slots_recycle_alpha'] or len(specs) != 272
            or len({s['id'] for s in specs}) != 272):
        raise ValueError('F_R global reservation changed')
    rows, unmeasured = [], []
    for spec in specs:
        missing = set(spec['arms']) - aliases.keys()
        if spec['scene'] not in SCENE_MAP or missing:
            if spec['scene'] not in ('nominal', *SCENE_MAP) or missing - {'A2', 'B0', 'old_B_star'}:
                raise ValueError('unregistered scene or absent candidate in F_R')
            unmeasured.append(dict(id=spec['id'],
                reason='nominal not in this development grid' if spec['scene'] == 'nominal'
                else 'historical reference obligation retained for CONF-R', missing_arms=sorted(missing)))
            continue
        names = spec['arms']
        if (spec['method'] != 'paired_CP' or spec['coefficients'] != [1, -1]
                or len(names) != 2 or spec['reference_arm'] != names[0]
                or spec['candidate_arm'] != names[1]):
            raise ValueError('registered reference-minus-candidate direction changed')
        scene, snr = SCENE_MAP[spec['scene']], spec['snr_db']
        raw_names = [aliases[name] for name in names]
        ref, candidate = [np.array([cells[(b, snr, scene, arm)] for b in blocks]) for arm in raw_names]
        wins = int(np.count_nonzero((ref == 1) & (candidate == 0)))
        losses = int(np.count_nonzero((ref == 0) & (candidate == 1)))
        bounds = paired_delta(wins, losses, 192, alpha_family=FAMILY_ALPHA, m=272)
        rows.append(dict(id=spec['id'], family='F_R', scene=scene, snr=snr, n=192,
            arms=names, raw_arms=raw_names, exact_configuration_alias=raw_names[0] == raw_names[1],
            reference_arm=names[0], candidate_arm=names[1],
            error_counts=[int(ref.sum()), int(candidate.sum())], wins=wins, losses=losses,
            delta=float(bounds['delta']), interval=[float(bounds['lower']), float(bounds['upper'])],
            delta_definition='FER_reference - FER_candidate; positive means improvement',
            method='paired_CP', m=272, alpha_family=FAMILY_ALPHA, tail_alpha=float(bounds['tail']),
            questions=spec['questions'], planned_confirmation_sample_set=spec['sample_set'],
            actual_split='counterexample', independent_confirmation=False,
            scope='S-01 development; cannot replace independent CONF-R or formal nonharm'))
    if len(rows) != 168 or len(unmeasured) != 104:
        raise ValueError('registered candidate contrast coverage changed')
    return dict(contrasts=rows, unmeasured_registered_contrasts=unmeasured,
                family_m=272, actual_n_per_scene_snr=192, independent_confirmation=False)
