"""Phase 1 only: archive checks, old-key parity and repeated known smoke cases."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import resource
import statistics
import sys

import numpy as np

import sbl
import cstate
import archives

HERE = Path(__file__).resolve().parent
THREADS = ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
           'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
C_SMOKE = {(s, rho, snr, 8600) for s in ('U', 'G') for rho in (300, 500) for snr in (450, 800)}
S_PARITY_FIELDS = ('decoded_sha256', 'info_errors', 'n_atoms', 'n_pair', 'nmse')
S_TIMES = ('seconds', 'elapsed_seconds', 'gen_seconds', 'timings', 'fit_seconds')


def write(out, name, payload):
    with (out / name).open('x') as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def stable(x):
    if isinstance(x, dict):
        return {k: stable(v) for k, v in x.items()
                if k not in S_TIMES and not k.endswith('_seconds')}
    if isinstance(x, list):
        return [stable(v) for v in x]
    return x


def canonical(x):
    return json.dumps(x, sort_keys=True, allow_nan=False, separators=(',', ':'))


def compare(want, got, label, *, archive=False):
    if canonical(want) != canonical(got):
        error = archives.FrozenEvidenceError if archive else AssertionError
        raise error(f'{label}: expected {canonical(want)[:3000]}, got {canonical(got)[:3000]}')


def init_worker():
    global s_ctx, s_grid, c_ctx, full, cd
    # Imports and p1ctx identities are qualified separately in load_preflight.
    c_ctx, full, cd, _ = cstate.context()
    s_ctx = c_ctx
    s_grid = sbl.e3c.sbl.full_grid(int(s_ctx.system.l_max_cap))


def s_run(key, *, include_u2=True, force_empty=False):
    return sbl.process_key(s_ctx, sbl.e3c.e3d.PilotCache(), s_grid, key,
                           include_u2=include_u2, force_empty=force_empty)


def c_run(key, **options):
    s, rho, snr, frame = key
    return cstate.one(c_ctx, full, cd, cstate.stage3.inputs(c_ctx, frame, s, rho), *key, **options)


def selected(row, names):
    return {name: row[name] for name in names}


def g1_sbl(item):
    key, old_e3c, old_split = item
    live = s_run(key, include_u2=False)
    receipt = {}
    for name in sbl.GATE_ARMS:
        ref = old_e3c['variants'][name] if name in ('R0', 'R1') else old_split['budgets']['100'][name]
        actual = selected(live['variants'][name], S_PARITY_FIELDS)
        compare(selected(ref, S_PARITY_FIELDS), actual, f'G1 SBL {key} {name}', archive=True)
        receipt[name] = actual
    return live, dict(key=key, matches=receipt)


def g1_cstate(item, arms=('F0', 'CD', 'U')):
    key, old = item
    new = c_run(key, tau=0, arms=arms)
    compare(old['syndrome'], new['syndrome'], f'G1 CSTATE syndrome {key}', archive=True)
    compare(old['inputs'], new['inputs'], f'G1 CSTATE inputs {key}', archive=True)
    for a, b in (('F0', 'F0'), ('CD', 'CODELAY')):
        compare(old['arms'][b], selected(new['arms'][a], ('errors', 'decoded_sha')),
                f'G1 CSTATE {key} {a}', archive=True)
    state = new['arms']['CD']['state']
    compare(old['codelay_geometry']['paths'], state['paths'],
            f'G1 CSTATE saved support {key}', archive=True)
    decisions = [a for _, a in new['arms']['CD']['decision'] if a is not None]
    old_decisions = [[edit['slot'], edit['new']] for edit in old['codelay_geometry']['edits']]
    compare(old_decisions, decisions, f'G1 CSTATE saved edits {key}', archive=True)
    compare(stable(new['arms']['CD']), stable(new['arms']['U']), f'G2 tau=0 {key}')
    return new, dict(key=key, syndrome=new['syndrome'], f0=new['arms']['F0']['decoded_sha'],
                     cd=new['arms']['CD']['decoded_sha'], tau0_reduction=True)


def g1_a2(old):
    key = archives.key(old)
    new = c_run(key, arms=('F0', 'A2'))
    if not old['triggered']:
        raise ValueError('Archived A2 gate key must trigger')
    compare(old['f0']['syndrome'], new['syndrome'], f'G1 A2 syndrome {key}', archive=True)
    for arm, prior in (('F0', old['f0']), ('A2', old['arms']['K-diag'])):
        compare((prior['decoded_sha256'], prior['info_errors']),
                (new['arms'][arm]['decoded_sha'], new['arms'][arm]['errors']),
                f'G1 split-prosp {key} {arm}', archive=True)
    a2 = new['arms']['A2']
    compare(list(zip(old['arms']['K-diag']['final_delays'], old['arms']['K-diag']['final_dopplers'])),
            [tuple(path) for path in a2['state']['paths']], f'G1 A2 support {key}', archive=True)
    expected_a2 = old['arms']['K-diag']
    expected_edits = [[e['slot'], e['new']] for e in expected_a2['edits']]
    compare(expected_edits, [a for _, a in a2['decision'] if a is not None],
            f'G1 A2 accepted edits {key}', archive=True)
    compare(expected_a2['objective_after'], a2['state']['objective'],
            f'G1 A2 final objective {key}', archive=True)
    return new, dict(key=key, archive=f"tf_split_prosp_20261018/out/{'smoke' if old['smoke'] else 'main'} K-diag",
                     decoded_sha=a2['decoded_sha'], errors=a2['errors'])


def smoke_sbl(key):
    one, two = s_run(key), s_run(key)
    compare(stable(one), stable(two), f'G3 SBL {key}')
    stripped = s_run(key, force_empty=True)['variants']['U2']
    lo = one['variants']['S-lo']
    # R0–S-isolo use the frozen metadata layout; U2 uses the same layout plus
    # the added-refinement trace field, always zero for the forced-empty run.
    fields = (*S_PARITY_FIELDS, 'atoms', 'atoms_ongrid', 'sbl', 'sbl_gain_sha256', 'sbl_state_sha256',
              'gain_sha256', 'refine', 'pairs')
    compare(selected(lo, fields), selected(stripped, fields), f'G2 empty U2 {key}')
    return one, two, dict(key=key, repeat=True, empty_refinement=True)


def smoke_cstate(old):
    key = archives.key(old)
    one, two = c_run(key), c_run(key)
    compare(stable(one), stable(two), f'G3 CSTATE {key}')
    compare(old['f0']['syndrome'], one['syndrome'], f'Archived smoke syndrome {key}', archive=True)
    return one, two, dict(key=key, repeat=True, triggered=bool(one['syndrome']))


def synthetic_trials():
    return cstate.synthetic_gate(full, cd)


def smoke_trials(key):
    row = c_run(key, arms=('F0', 'U'), check_scores=True)
    check = row['census']
    if check['checked_trials'] == 0 or check['max_relative_score_error'] > 1e-10:
        raise AssertionError(f'G2 smoke must check scored trial supports: {key} {check}')
    return dict(key=key, **check)


def append_rows(out, name, rows):
    with (out / name).open('a') as handle:
        for row in rows:
            print(canonical(row), file=handle)


def costs(srows, crows, stage_rows):
    s_arm = {arm: statistics.mean(row['variants'][arm]['seconds']['total'] for row in srows)
             for arm in sbl.ARMS}
    s_prep = statistics.mean(row['seconds']['total'] for row in srows)
    trigger_rate = statistics.mean(row['syndrome'] != 0 for row in stage_rows.values())
    triggered = [row for row in crows if row['syndrome']]
    if not triggered:
        raise AssertionError('CSTATE timing smoke needs a triggered key')
    c_trigger = {arm: statistics.mean(row['arms'][arm]['seconds'] for row in triggered)
                 for arm in cstate.ARMS[1:]}
    c_arm = {'F0': statistics.mean(row['arms']['F0']['seconds'] for row in crows),
             **{arm: seconds * trigger_rate for arm, seconds in c_trigger.items()}}
    c_h = sum(c_arm.values()) * 6800 * 1.3 / 3600
    s_h = (s_prep + sum(s_arm.values())) * 2400 * 1.3 / 3600
    reduced = s_h + c_h > 25
    return dict(sbl_seconds_per_key=s_arm, sbl_shared_prep_seconds_per_key=s_prep,
                cstate_seconds_per_key=c_arm, cstate_incremental_seconds_when_triggered=c_trigger,
                cstate_archive_trigger_rate=trigger_rate, cstate_smoke_trigger_keys=len(triggered),
                sbl_smoke_keys=len(srows), cstate_smoke_keys=len(crows),
                margin=1.3, full_core_hours=s_h + c_h,
                projected_core_hours=(s_h * .75 + c_h if reduced else s_h + c_h),
                full_sbl_core_hours=s_h, cstate_core_hours=c_h, reduced=reduced,
                selected_sbl_keys=1800 if reduced else 2400, cstate_keys=6800)


def cpu_hours():
    usage = [resource.getrusage(t) for t in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    return sum(u.ru_utime + u.ru_stime for u in usage) / 3600


def run(args):
    out = args.out.resolve()
    if not out.is_relative_to(HERE / 'out') or not out.is_dir():
        raise ValueError('Phase 1 output must be a new directory under the experiment out/')
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('Expected the deinlab CPU environment')
    if any(os.environ.get(name) != '1' for name in THREADS):
        raise ValueError('Set all numerical thread caps to 1 before Python starts')
    threads = {name: os.environ[name] for name in THREADS}
    fresh = json.loads(args.fresh.read_text())
    if fresh['status'] != 'PASS':
        raise ValueError('Requires completed archive blindness preflight')
    first, last = fresh['selected_inclusive']
    s_gate_keys = sbl.e3c.lib.gate_keys()
    s_smoke_keys = sbl.e3c.lib.smoke_keys()
    declared = [*s_gate_keys, *s_smoke_keys, *C_SMOKE]
    if (any(first <= key[3] <= last for key in declared)
            or any(not 4000 <= k[3] <= 4399 for k in s_gate_keys)
            or set(k[3] for k in s_smoke_keys) != set(range(8400, 8412))):
        raise AssertionError('Configured Phase 1 keys violate blindness')

    preflight = archives.load_preflight(sbl, cstate, C_SMOKE)
    stage_archive = preflight['stage_rows']
    c_gate_keys = sorted(key for key, row in stage_archive.items()
                         if row['syndrome'] and 4000 <= key[3] <= 4399)[:8]
    if len(c_gate_keys) < 8 or any(first <= key[3] <= last for key in c_gate_keys):
        raise archives.FrozenEvidenceError('Missing eight admissible Stage 3 triggered keys')
    split_smoke = preflight['cstate_smoke']
    a2 = next(r for r in split_smoke if r['triggered'])
    config = dict(workers=args.workers, threads=threads, host=platform.node(),
                  python=platform.python_version(), numpy=np.__version__,
                  stage3_gate_keys=c_gate_keys, sbl_gate_keys=s_gate_keys,
                  sbl_smoke_keys=s_smoke_keys, cstate_smoke_keys=sorted(C_SMOKE),
                  a2_gate_key=archives.key(a2), legal_old_interval=[4000, 4399],
                  fresh_preflight_sha256=hashlib.sha256(args.fresh.read_bytes()).hexdigest(),
                  own_sources_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted(HERE.glob('*.py'))},
                  cpu_cap_core_hours=3, sources=preflight['identity'])
    write(out, 'config.json', dict(_argv=sys.argv, _config=config))
    leverage = archives.leverage(preflight['spectral_rows'], preflight['split_rows'])
    write(out, 'leverage.json', leverage)
    print('Frozen sources, archived rows and leverage checked', flush=True)

    results = {}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        s_items = [(key, preflight['e3c_rows'][key], preflight['spectral_rows'][key])
                   for key in s_gate_keys]
        g1 = {'SBL': [], 'CSTATE': []}
        for row, receipt in pool.map(g1_sbl, s_items):
            append_rows(out, 'g1_sbl_rows.jsonl', [row])
            g1['SBL'].append(receipt)
        for row, receipt in pool.map(g1_cstate, [(k, stage_archive[k]) for k in c_gate_keys]):
            append_rows(out, 'g1_cstate_rows.jsonl', [row])
            g1['CSTATE'].append(receipt)
        row, g1['A2'] = pool.submit(g1_a2, a2).result()
        append_rows(out, 'g1_cstate_rows.jsonl', [row])
        write(out, 'g1.json', dict(passed=True, **g1))
        print('G1 passed: 20 SBL, 8 Stage 3 and 1 split-prosp A2 parity keys', flush=True)

        synthetic = pool.submit(synthetic_trials).result()
        score_gate = pool.submit(smoke_trials, archives.key(a2))
        srows, crows, s_checks, c_checks = [], [], [], []
        for one, two, result in pool.map(smoke_sbl, s_smoke_keys):
            srows.extend((one, two))
            s_checks.append(result)
            append_rows(out, 'smoke_sbl_rows.jsonl', [one, two])
        for one, two, result in pool.map(smoke_cstate, split_smoke):
            crows.extend((one, two))
            c_checks.append(result)
            append_rows(out, 'smoke_cstate_rows.jsonl', [one, two])
        smoke = score_gate.result()
        results['G1'] = dict(passed=True, sbl_keys=len(g1['SBL']), stage3_keys=len(g1['CSTATE']), a2_keys=1)
        results['G2'] = dict(passed=True, synthetic=synthetic, cstate_trial_scores=smoke,
                             sbl_empty_keys=len(s_checks), cstate_tau0_keys=len(g1['CSTATE']))
        results['G3'] = dict(passed=True, sbl=s_checks, cstate=c_checks)
        write(out, 'g2.json', results['G2'])
        write(out, 'g3.json', results['G3'])
        results['cost'] = costs(srows, crows, stage_archive)
        results['cost']['sbl_unique_smoke_keys'] = len(s_smoke_keys)
        results['cost']['cstate_unique_smoke_keys'] = len(split_smoke)

    results.update(_argv=sys.argv, _config=config, fresh=fresh, leverage=leverage, core_hours_used=cpu_hours())
    write(out, 'results.json', results)
    print(f"G2/G3 passed; projection {results['cost']['projected_core_hours']:.3f} core-hours", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--fresh', required=True, type=Path)
    p.add_argument('--workers', required=True, type=int, choices=range(1, 8))
    args = p.parse_args()
    run(args)


if __name__ == '__main__':
    main()
