"""Qualify §9–§10 on vetted old and smoke keys only."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import platform
import sys

import admission_gate
import run_phase1 as p1
import verdict

MIRRORS = ('C-hi', 'C-lo')
ACTIVE = ('U', *MIRRORS)
OLD_ARMS = p1.cstate.ARMS
LEVERAGE_FRAMES = range(4000, 4200)


def mirror_reduction(item):
    row, receipt = p1.g1_cstate(item, arms=p1.cstate.ARMS)
    for arm, reference in (('C-hi', 'CD'), ('C-lo', 'A2')):
        p1.compare(p1.stable(row['arms'][reference]), p1.stable(row['arms'][arm]),
                   f"G2 tau=0 {receipt['key']} {arm}")
    return row, receipt | {'mirror_tau0': {'C-hi': 'CD', 'C-lo': 'A2'}}


def synthetic():
    return dict(geometry=p1.cstate.synthetic_gate(p1.full, p1.cd),
                isolated=admission_gate.synthetic_gate(p1.full, p1.cd))


def smoke_scores(key):
    row = p1.c_run(key, arms=('F0', *ACTIVE), check_scores=True)
    checks = row['census']['by_arm']
    for arm in ACTIVE:
        c = checks[arm]
        if not (c['checked_trials'] > 0 and c['max_relative_score_error'] <= 1e-10):
            raise AssertionError(f'Full trial-score parity failed on {key}/{arm}: {c}')
    return dict(key=key, by_arm=checks)


def smoke_cstate(old):
    key = p1.archives.key(old)
    a, b = (p1.c_run(key, admission=True) for _ in range(2))
    p1.compare(old['f0']['syndrome'], a['syndrome'], f'Archived smoke syndrome {key}', archive=True)
    p1.compare(p1.stable(a), p1.stable(b), f'Phase 1b G3 {key}')
    return a, b, dict(key=key, repeat=True, triggered=bool(a['syndrome']),
                      admission_qualified=a['admission'] is not None)


def replay_old(item):
    key, old = item
    row = p1.c_run(key, arms=OLD_ARMS, admission=True)
    p1.compare(old['syndrome'], row['syndrome'], f'Old leverage syndrome {key}', archive=True)
    p1.compare(old['inputs'], row['inputs'], f'Old leverage inputs {key}', archive=True)
    for arm, reference in (('F0', 'F0'), ('CD', 'CODELAY')):
        p1.compare(old['arms'][reference], p1.selected(row['arms'][arm], ('errors', 'decoded_sha')),
                   f'Old leverage {key}/{arm}', archive=True)
    fer = {name: int(row['arms'][name]['errors'] > 0) for name in OLD_ARMS}
    return row, fer


def old_leverage(pool, out, stage, archive_gap, g2_adm_coverage):
    cohort = {key: row for key, row in sorted(stage.items()) if key[3] in LEVERAGE_FRAMES}
    trigger = {key: row for key, row in cohort.items() if row['syndrome']}
    if len(cohort) != len(LEVERAGE_FRAMES) * 34 or not trigger:
        raise p1.archives.FrozenEvidenceError('Expected complete old Stage 3 leverage grid')
    counts = dict(qualified=0, diagnostic_calls=0, diagnostic_seconds=0.,
                  qualified_seconds=0., folded_nontriggers=len(cohort) - len(trigger))
    outcomes, adm_frames = {}, []
    preferences = {name: [] for name in verdict.ADMISSION_ARMS}
    with (out / 'leverage_trigger_rows.jsonl').open('x') as handle:
        results = pool.map(replay_old, trigger.items())
        for idx, (row, fer) in enumerate(results, 1):
            key = p1.archives.key(row)
            outcomes[key] = fer
            timing = row['admission_seconds']
            counts['diagnostic_calls'] += 1
            counts['diagnostic_seconds'] += timing
            if row['admission'] is not None:
                counts['qualified'] += 1
                counts['qualified_seconds'] += timing
                adm_frames.append(key[3])
                for name, scores in row['admission']['by_arm'].items():
                    if scores['preference'] != (scores['phantom_gain'] > scores['new_delay_gain']):
                        raise AssertionError(f'Invalid admission preference for {key}/{name}')
                    preferences[name].append(scores['preference'])
            print(p1.canonical(row), file=handle)
            if idx % 100 == 0:
                print(f'Old leverage trigger replays {idx}/{len(trigger)}', flush=True)
    if g2_adm_coverage == 0 and counts['qualified'] == 0:
        raise AssertionError('V5-adm evaluated no eligible old or smoke units')
    for key, row in cohort.items():
        if key not in outcomes:
            fail = int(row['arms']['F0']['errors'] > 0)
            outcomes[key] = dict.fromkeys(OLD_ARMS, fail)
    if set(outcomes) != set(cohort):
        raise p1.archives.FrozenEvidenceError('Old whole-grid leverage keys differ from the archive')
    frames = [key[3] for key in outcomes]
    p, draws, n = verdict.estimates({name: [r[name] for r in outcomes.values()] for name in OLD_ARMS}, frames)
    mirror = verdict.mirror_ratios(p, draws)
    halfwidths = {arm: ci['ci_width'] / 2 if ci['evaluable'] else None for arm, ci in mirror.items()}
    max_width = None if None in halfwidths.values() else max(halfwidths.values())
    observed_gap = verdict.linear_summary(p, draws, verdict.CSTATE_GAP)
    return dict(margin=min(.005, .25 * archive_gap['point']), margin_archive=archive_gap,
                same_grid_margin=min(.005, .25 * observed_gap['point']),
                old_admission=verdict.admission_summary(preferences, adm_frames), psi=mirror, halfwidth_by_arm=halfwidths, max_psi_halfwidth=max_width,
                v5_primary=verdict.select_v5_primary(max_width), old_grid=dict(keys=len(cohort),
                clusters=n, inclusive=[min(frames), max(frames)], triggered=len(trigger),
                observed_gap=observed_gap), expected_adm_per_200=counts['qualified'],
                admission=counts)


def projection(sbl_rows, cstate_rows, old_rows, leverage):
    timings = p1.costs(sbl_rows, cstate_rows, old_rows)
    counts = leverage['admission']
    # Each archived triggered key paid the eligibility check. The same-grid
    # old replay has enough units to time the conditional diagnostic.
    rate = timings['cstate_archive_trigger_rate']
    adm_seconds = counts['diagnostic_seconds'] / counts['diagnostic_calls'] * rate
    adm_hours = adm_seconds * 6800 * 1.3 / 3600
    s200 = timings['full_sbl_core_hours']
    c200 = timings['cstate_core_hours']
    total200 = s200 + c200 + adm_hours
    total300 = 1.5 * s200 + c200 + adm_hours
    return dict(cstate_200_core_hours=c200, cstate_seconds_per_key=timings['cstate_seconds_per_key'],
                cstate_triggered_seconds=timings['cstate_incremental_seconds_when_triggered'],
                cstate_archive_trigger_rate=rate, sbl_200_core_hours=s200,
                sbl_300_core_hours=s200*1.5, sbl_seconds_per_key=timings['sbl_seconds_per_key'],
                sbl_shared_prep_seconds=timings['sbl_shared_prep_seconds_per_key'],
                v5_adm_core_hours=adm_hours, v5_adm_seconds_per_key=adm_seconds,
                total_200_core_hours=total200, total_300_core_hours=total300,
                sbl_selected_frames=300 if total300 <= 25 else 200,
                projected_core_hours=total300 if total300 <= 25 else total200, factor=1.3)


def archived_a2(rows):
    eligible = {key: row for key, row in rows.items() if row['triggered'] and 'K-diag' in row['arms']}
    first_by_cell = []
    for scenario, rho in (('G', 300), ('G', 500), ('U', 300), ('U', 500)):
        first_by_cell.extend(sorted((k for k in eligible if k[:2] == (scenario, rho)),
                                    key=lambda k: (k[3], k[2]))[:2])
    chosen = first_by_cell + sorted(eligible.keys() - set(first_by_cell))
    return [eligible[key] for key in chosen[:8]], len(eligible)


def fresh_guard(fresh, groups):
    if fresh['status'] != 'PASS' or fresh['eligible_inclusive'] != [4400, 4699]:
        raise ValueError('Phase 1b requires the extended blinded-frame audit')
    first, last = fresh['eligible_inclusive']
    if any(first <= key[3] <= last for group in groups for key in group):
        raise AssertionError('A Phase 1b execution group overlaps the fresh block')


def run(args):
    out = args.out.resolve()
    if not out.is_relative_to(p1.HERE/'out') or not out.is_dir():
        raise ValueError('Phase 1b output must be a new directory under the experiment out/')
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('Expected deinlab CPU environment')
    if any(os.environ.get(name) != '1' for name in p1.THREADS):
        raise ValueError('Expected one numerical thread per process')
    fresh = json.loads(args.fresh.read_text())
    a = p1.archives.load_preflight(p1.sbl, p1.cstate, p1.C_SMOKE)
    s_keys = p1.sbl.e3c.lib.gate_keys()
    s_smoke = p1.sbl.e3c.lib.smoke_keys()
    split, stage = a['split_rows'], a['stage_rows']
    c_keys = sorted(key for key, row in stage.items() if row['syndrome'])[:8]
    a2, a2_available = archived_a2(split)
    c_smoke = a['cstate_smoke']
    c_score = next(p1.archives.key(r) for r in c_smoke if r['triggered'])
    old_keys = [k for k, r in stage.items() if k[3] in LEVERAGE_FRAMES and r['syndrome']]
    fresh_guard(fresh, (s_keys, c_keys, s_smoke, map(p1.archives.key, c_smoke),
                        map(p1.archives.key, a2), old_keys))
    if len(c_keys) < 8 or not a2:
        raise p1.archives.FrozenEvidenceError('Archive is missing required triggered keys')
    config = dict(stage='Phase 1b', sources=a['identity'], workers=args.workers,
                  threads={name: os.environ[name] for name in p1.THREADS}, host=platform.node(),
                  python=platform.python_version(), numpy=p1.np.__version__, cpu_cap_core_hours=3,
                  leverage_frames_inclusive=[LEVERAGE_FRAMES.start, LEVERAGE_FRAMES.stop - 1],
                  sbl_gate_keys=s_keys, cstate_gate_keys=c_keys, sbl_smoke_keys=s_smoke,
                  cstate_smoke_keys=sorted(p1.C_SMOKE), a2_archive_keys=list(map(p1.archives.key, a2)),
                  fresh_preflight_sha256=sha256(args.fresh.read_bytes()).hexdigest(),
                  own_sources_sha256={path.name: sha256(path.read_bytes()).hexdigest()
                                      for path in sorted(p1.HERE.glob('*.py'))})
    p1.write(out, 'config.json', dict(_argv=sys.argv, _config=config))
    archived_gap = p1.archives.leverage(a['spectral_rows'], split)['cstate']
    print('Frozen sources, archives and blindness checked', flush=True)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=p1.init_worker,
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        s_items = [(k, a['e3c_rows'][k], a['spectral_rows'][k]) for k in s_keys]
        g1 = dict(passed=True, sbl=[], cstate=[], a2=[], a2_archive_triggered_available=a2_available)
        for row, receipt in pool.map(p1.g1_sbl, s_items):
            p1.append_rows(out, 'g1_sbl_rows.jsonl', [row])
            g1['sbl'].append(receipt)
        for row, receipt in pool.map(mirror_reduction, [(k, stage[k]) for k in c_keys]):
            p1.append_rows(out, 'g1_cstate_rows.jsonl', [row])
            g1['cstate'].append(receipt)
        for row, receipt in pool.map(p1.g1_a2, a2):
            p1.append_rows(out, 'g1_cstate_rows.jsonl', [row])
            g1['a2'].append(receipt)
        p1.write(out, 'g1.json', g1)
        print(f"G1 passed, including {len(g1['a2'])} archived A2 keys", flush=True)

        mathematical = pool.submit(synthetic).result()
        score = pool.submit(smoke_scores, c_score)
        ss, cs, sg, cg = [], [], [], []
        for one, two, receipt in pool.map(p1.smoke_sbl, s_smoke):
            p1.append_rows(out, 'smoke_sbl_rows.jsonl', [one, two])
            ss.extend((one, two))
            sg.append(receipt)
        for one, two, receipt in pool.map(smoke_cstate, c_smoke):
            p1.append_rows(out, 'smoke_cstate_rows.jsonl', [one, two])
            cs.extend((one, two))
            cg.append(receipt)
        g2 = dict(passed=True, mathematical=mathematical, score_smoke=score.result(),
                  tau0_keys=len(g1['cstate']), empty_u2_keys=len(sg))
        g3 = dict(passed=True, sbl=sg, cstate=cg)
        p1.write(out, 'g2.json', g2)
        p1.write(out, 'g3.json', g3)
        print('G2 and G3 passed', flush=True)
        lv = old_leverage(pool, out, stage, archived_gap, sum(r['admission_qualified'] for r in cg))
        p1.write(out, 'leverage.json', lv)
        cost = projection(ss, cs, stage, lv)
    r = dict(_argv=sys.argv, _config=config, fresh=fresh, core_hours_used=p1.cpu_hours(),
             G1=dict(passed=True, sbl_keys=len(g1['sbl']), cstate_keys=len(g1['cstate']),
                     a2_keys=len(g1['a2'])), G2=g2, G3=g3, leverage=lv, cost=cost)
    p1.write(out, 'results.json', r)
    print(f"Done: {lv['v5_primary']} primary, {cost['sbl_selected_frames']} SBL frames, "
          f"{cost['projected_core_hours']:.3f} projected core-hours", flush=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out', required=True, type=Path)
    cli.add_argument('--fresh', required=True, type=Path)
    cli.add_argument('--workers', required=True, type=int, choices=range(1, 8))
    run(cli.parse_args())
