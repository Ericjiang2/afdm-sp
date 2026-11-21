"""Project Section 7 interval widths from the paired .30/.50 Stage 3 curves."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import analysis

HERE = Path(__file__).resolve().parent
OLD_RHOS = (300, 500)
LEVERAGE_SHA256 = '043e57d4dfc67996c6f291c6cf88d99a51714765ccd0a1a492c70461bbf165ad'


def project(rows, grid, costs, cap):
    errors = analysis._indexed_errors(rows)
    projections = {}
    for n in (400, 600):
        crossings, _ = analysis._crossings(errors, grid, analysis.OLD_FRAMES, sample_size=n)
        projections[str(n)] = analysis.confirmatory(crossings, rhos=OLD_RHOS)
    width = projections['400']['P1']['half_width_db']
    precision_trigger = width == '+inf' or width > .6
    affordable = costs['600'] <= cap
    if costs['400'] > cap:
        raise ValueError('The 400-frame full grid exceeds the main budget')
    use = 600 if precision_trigger and affordable else 400
    return dict(projections=projections, frame_decision=dict(
        p1_half_width_threshold_db=.6, p1_precision_triggers_extension=precision_trigger,
        candidate_600_within_budget=affordable, retained_frames=use,
        retained_block=[5400, 5400 + use - 1], full_grid_core_hours=costs, main_cap_core_hours=cap))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', required=True, type=Path)
    parser.add_argument('--qualification', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    counts = HERE.parent / 'cstate_codelay_sbl_stage3_20261118' / 'out' / 'accuracy.json'
    summary = json.loads(counts.read_text())['cells']
    grid = {(s, rho): tuple(map(int, summary[f'{s}_{rho}']['own_fer']))
            for s in analysis.SCENARIOS for rho in OLD_RHOS}
    if hashlib.sha256(args.rows.read_bytes()).hexdigest() != LEVERAGE_SHA256:
        raise ValueError('Phase 1 joined Stage 3 row archive digest differs')
    cost = json.loads(args.qualification.read_text())['cost']
    with args.rows.open() as handle:
        result = project((json.loads(line) for line in handle), grid, cost['full_grid_core_hours'],
                         cost['main_core_hour_cap'])
    # These old observations drive a precision projection, never the new pilot-ratio verdicts.
    for projection in result['projections'].values():
        for contrast in projection.values():
            contrast.pop('verdict')
    with args.out.open('x') as handle:
        json.dump(dict(_argv=sys.argv, _config=dict(
            stage3_frames_inclusive=[4000, 4399], rows_sha256=LEVERAGE_SHA256,
            stage3_crossing_inventory_sha256=hashlib.sha256(counts.read_bytes()).hexdigest(),
            analysis_sha256=hashlib.sha256((HERE / 'analysis.py').read_bytes()).hexdigest(),
            bootstrap_seed=analysis.BOOT_SEED, bootstrap_draws=analysis.BOOT_DRAWS,
            archived_rho_permille=OLD_RHOS, p3_scope='two-point proxy using the six-point tail budget'),
            **result), handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
