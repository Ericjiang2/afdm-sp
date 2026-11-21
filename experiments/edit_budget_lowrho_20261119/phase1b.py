"""Qualify the edit-cap intervention on the previously qualified archived triggers."""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean
import time
from types import SimpleNamespace

import numpy as np

from budget_receiver import ARMS, cstate, decoder_transitions, edit_budget_mechanism, run_at_budget, stage3
from primary import PRIMARY_SNRS
from qualify import ARCHIVE_FRAMES, BRANCHES, archives, gate_keys, miss_bounds, project, qualified_inputs

HERE = Path(__file__).resolve().parent
PHASE1_GATES = HERE / 'out/phase1/qualification3/gates.json'
PHASE1_GATES_SHA = '655c8cb783523923029f4bec58bf7abbc07aaa7acf4d1a2220713e73abd04b1a'
CAPS = (2, 4, 6)


def calibration(rows):
    result = {}
    frames = tuple(ARCHIVE_FRAMES)
    for rho, snrs in PRIMARY_SNRS.items():
        triggers, rescues = Counter(), Counter()
        subgroup_keys = Counter()
        subgroup_frames = {'definite': set(), 'possible': set()}
        bounds = Counter()
        for (_, fraction, snr, frame), row in rows.items():
            if fraction != rho or snr not in snrs or not row['triggered']:
                continue
            triggers[frame] += 1
            if not row['arms']['CD']['errors']:
                rescues[frame] += 1
                continue
            lo, hi = miss_bounds(row)
            bounds[f'{lo}:{hi}'] += 1
            for name, eligible in (('definite', 3 <= lo <= hi <= 4),
                                   ('possible', lo <= 4 and hi >= 3)):
                if eligible:
                    subgroup_keys[name] += 1
                    subgroup_frames[name].add(frame)
        n = len(frames)
        total = sum(triggers.values())
        saved = sum(rescues.values())
        rescue_rate = saved / total
        # Ratio influence at frame level. At the planning null both arm
        # influences have this variance and are assumed uncorrelated.
        residual_squares = sum((rescues[f] - rescue_rate * triggers[f]) ** 2 for f in frames)
        variance = n / (n - 1) * residual_squares / total ** 2
        result[rho] = dict(
            snr_centi_db=snrs, physical_frames=n, triggered_keys=total,
            distinct_triggered_frames=len(triggers), cd2_rescued=saved,
            cd2_failed=total - saved, cd2_rescue_rate=rescue_rate,
            cd2_marginal_se=math.sqrt(variance),
            projected_95_half_width=1.959963984540054 * math.sqrt(2 * variance),
            astra_subgroup=dict(eligible_keys=[subgroup_keys['definite'], subgroup_keys['possible']],
                                eligible_frames=[len(subgroup_frames['definite']),
                                                 len(subgroup_frames['possible'])],
                                missed_delay_bounds=dict(sorted(bounds.items()))),
        )
    return result


def native_stop(step):
    if step['accepted'] is not None:
        return 'continue_allowed'
    return 'no_legal_candidate' if step['selected'] is None else 'no_strict_improvement'


def prefix(result):
    return [
        dict(selected=step['selected'], accepted=step['accepted'], native_stop=native_stop(step))
        for step in result.global_trace[:2]
    ]


def geometry_gate(ctx, kernel, obs, arrays, covariance, budget):
    start, schedule = {}, []
    geometry_cpu = None
    placeholder = np.zeros_like(arrays['r1_check'])

    def geometry(y, x, v, paths, **kwargs):
        nonlocal geometry_cpu
        begin = time.process_time()
        result = kernel.reopen_geometry(y, x, v, paths, **kwargs)
        geometry_cpu = time.process_time() - begin
        options = {key: value for key, value in kwargs.items() if key != 'max_edits'}
        start.update(observation_sha=stage3.digest(y), symbol_mean_sha=stage3.digest(x),
                     symbol_variance_sha=stage3.digest(v), paths=[asdict(path) for path in paths],
                     options=options)
        return result

    # Observe the real wrapper's continuation call sites with inert handlers.
    # The archived F0 prefix has already run. These handlers perform no TF or LDPC work.
    def detector(y, pilot, channel, sigma2, *, prior, **kwargs):
        schedule.append(dict(call='scalar_joint', prior_sha=stage3.digest(prior), **kwargs))
        return dict(extrinsic=placeholder)

    def decoder(code, llr, **kwargs):
        schedule.append(dict(call='decoder_messages', **kwargs))

    gated_ctx = SimpleNamespace(system=ctx.system, code=ctx.code,
                                native=SimpleNamespace(scalar_joint=detector, decoder_messages=decoder))
    result = run_at_budget(gated_ctx, kernel, obs, arrays, covariance, budget, reopen=geometry)['result']
    expected_schedule = [
        dict(call='scalar_joint', prior_sha=stage3.digest(np.clip(arrays['r1_check'], -20, 20)),
             pd=1 - ctx.system.rho, iterations=20, damping=.3, gain_mode='joint'),
        dict(call='decoder_messages', maxiter=50),
    ]
    if schedule != expected_schedule or start['options']['local_passes'] != 2:
        raise AssertionError('Frozen local-pass count or downstream call schedule changed')
    local = [(step['pass_index'], step['slot']) for step in result.local_trace]
    expected_local = [(i, j) for i in range(2) for j in range(len(result.paths))]
    if local != expected_local:
        raise AssertionError('Executed local refinement differs from the two-pass schedule')
    stops = [native_stop(step) for step in result.global_trace]
    if (not stops or len(stops) > budget or any(stop != 'continue_allowed' for stop in stops[:-1])
            or (stops[-1] == 'continue_allowed' and len(stops) != budget)
            or len(result.edits) != stops.count('continue_allowed')):
        raise AssertionError('Global search continued past the native stopping rule or cap')
    if len(stops) > 2 and stops[:2] != ['continue_allowed', 'continue_allowed']:
        raise AssertionError('A third attempt requires two accepted edits')
    receipt = dict(cpu_seconds=geometry_cpu, steps=len(stops), edits=len(result.edits),
                   stops=stops, terminal_reason='cap_exhausted' if stops[-1] == 'continue_allowed' else stops[-1],
                   fallback_reason=result.diagnostics['fallback_reason'], local_passes=2,
                   local_slot_visits=len(local))
    return result, start, schedule, receipt


def gates(ctx, kernels, rows, old_cases):
    selected = [case for case in old_cases if case['row']['triggered']]
    prior_keys = [tuple(case['key']) for case in selected]
    if len(prior_keys) != 14 or prior_keys != [key for key in gate_keys(rows) if rows[key]['triggered']]:
        raise archives.FrozenEvidenceError('Phase 1 archive gate inventory differs')

    new_cases = []
    for case, key in zip(selected, prior_keys, strict=True):
        scenario, rho, snr, frame = key
        if frame not in ARCHIVE_FRAMES:
            raise AssertionError(f'Rejecting a Phase 1b key outside the archived sweep: {key}')
        base = stage3.inputs(ctx, frame, scenario, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
        ref = rows[key]
        if (syndrome != ref['syndrome'] or not syndrome
                or stage3.input_record(raw, obs) != ref['inputs']
                or stage3.truth_record(obs, truth) != ref['truth']
                or any(ref['arms']['F0'][field] != value
                       for field, value in stage3.decoded(ctx, dec, truth).items())):
            raise archives.FrozenEvidenceError(f'{key}: archived F0 evidence differs')
        entering = set(arrays['r1_delays'].tolist())
        true_delays = set(truth['l_i'].tolist())
        branches = {}
        record_cpu = 0.
        for base_name, (covariance, _) in ((name, ARMS[name]) for name in BRANCHES):
            results = [geometry_gate(ctx, kernels[covariance], obs, arrays, covariance, cap)
                       for cap in CAPS]
            baseline, expected_start, expected_schedule, base_receipt = results[0]
            identity = cstate._geometry_record(baseline)
            if any(case['row']['arms'][base_name][field] != val for field, val in identity.items()):
                raise AssertionError(f'{key} {base_name}: cap-2 geometry differs from Phase 1')
            # Canonical bytes include signed float representation as well as action identity.
            expected_prefix = json.dumps(prefix(baseline), sort_keys=True, allow_nan=False)
            receipts = {}
            for cap, (result, start, schedule, receipt) in zip(CAPS, results, strict=True):
                observed_prefix = json.dumps(prefix(result), sort_keys=True, allow_nan=False)
                if (observed_prefix != expected_prefix or start != expected_start
                        or schedule != expected_schedule
                        or receipt['fallback_reason'] != base_receipt['fallback_reason']):
                    raise AssertionError(f'{key} {base_name}/{cap}: cap changed the starting state, prefix or route')
                if (base_receipt['terminal_reason'] != 'cap_exhausted'
                        and cstate._geometry_record(result) != identity):
                    raise AssertionError(f'{key} {base_name}/{cap}: geometry differs after native stop')
                begin = time.process_time()
                mechanism = edit_budget_mechanism(result, cap, entering, true_delays)
                elapsed = time.process_time() - begin
                # A2 cap 4 is a gate probe and is absent from the main schedule.
                if (covariance, cap) in ARMS.values():
                    record_cpu += elapsed
                receipts[cap] = receipt | dict(mechanism=mechanism)
            branches[base_name] = dict(input=expected_start, schedule=expected_schedule,
                                       prefix=prefix(baseline), caps=receipts)

        # Time outcome-label serialization work without inventing a new arm outcome.
        old_errors = {name: ref['arms']['CD' if covariance == 'A1' else 'A2']
                      for name, (covariance, _) in ARMS.items()}
        begin = time.process_time()
        edit_budget_mechanism(None, 0, entering, true_delays)
        decoder_transitions({'F0': ref['arms']['F0'], **old_errors})
        record_cpu += time.process_time() - begin
        new_cases.append(dict(key=key, branches=branches, mechanism_cpu_seconds=record_cpu))
    return new_cases


def recost(rows, old_cases, cases):
    measured = {tuple(case['key']): case for case in cases}
    updated = []
    for old in old_cases:
        if not old['row']['triggered']:
            updated.append(old)
            continue
        branches = measured[tuple(old['key'])]['branches']
        timings = {arm: old['branches_cpu'][arm] | dict(
            extended_geometry={cap: branches[arm]['caps'][cap]
                               for cap in (4, 6) if (ARMS[arm][0], cap) in ARMS.values()})
            for arm in BRANCHES}
        updated.append(old | dict(branches_cpu=timings))
    result = project(rows, updated)
    mechanism_overhead = mean(case['mechanism_cpu_seconds'] for case in cases) * len(rows)
    result['mechanism_cpu_seconds'] = mechanism_overhead
    result['projected_core_hours'] += mechanism_overhead * result['multiplier'] / 3600
    result['cap_result'] = 'PASS' if result['projected_core_hours'] <= result['cap_core_hours'] else 'STOP'
    return result


def main(out):
    archives.verify(PHASE1_GATES, PHASE1_GATES_SHA)
    old_cases = json.loads(PHASE1_GATES.read_text())['cases']
    ctx, kernels, sources, rows, common = qualified_inputs()
    config = common['_config']
    config.update(phase='1b', phase1_gates=str(PHASE1_GATES), phase1_gates_sha256=PHASE1_GATES_SHA,
                  primary_snr_centi_db=PRIMARY_SNRS, caps=CAPS)
    config['code_sha256'].update(
        {name: sha256((HERE / name).read_bytes()).hexdigest() for name in ('phase1b.py', 'primary.py')})
    stage3.write_json(out / 'calibration.json', common | dict(
        half_width_model='95% normal, archive CD2 clustered ratio residuals, equal uncorrelated arm influences',
        by_rho=calibration(rows)))
    cases = gates(ctx, kernels, rows, old_cases)
    stage3.write_json(out / 'cap_gate.json', common | dict(
        passed=True, gate_keys=len(cases), continuation_detector_calls=0, continuation_decoder_calls=0,
        cases=cases, sources=sources))
    stage3.write_json(out / 'cost.json', common | recost(rows, old_cases, cases))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.out)
