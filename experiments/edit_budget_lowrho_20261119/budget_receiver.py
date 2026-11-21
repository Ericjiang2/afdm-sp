"""Budgeted continuations over the frozen rho-sweep F0 and CSTATE receiver."""
# Adapt tf_cstate_e1_20261017/geometry_validation_variant.py::_validate to allow 6 edits because the frozen guard rejects more than 2.

import inspect
from itertools import combinations
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

HERE = Path(__file__).resolve().parent
SWEEP = HERE.parent / 'rho_sweep_20261119'
sys.path.insert(0, str(SWEEP))
import phase1 as sweep  # noqa: E402

stage3, archives, cstate = sweep.stage3, sweep.archives, sweep.cstate
ARMS = {'CD2': ('A1', 2), 'CD4': ('A1', 4), 'CD6': ('A1', 6),
        'A2-2': ('A2', 2), 'A2-6': ('A2', 6)}


def budget_kernel(kernel):
    validation = kernel._validate
    source = inspect.getsource(validation)
    guard = 'max_edits > 2:'
    if source.count(guard) != 1:
        raise archives.FrozenEvidenceError('E-1 geometry validator budget guard changed')
    scope = dict(validation.__globals__)
    exec(compile(source.replace(guard, 'max_edits > 6:'), inspect.getsourcefile(validation),
                 'exec'), scope)
    reopen = kernel.reopen_geometry
    budgeted = FunctionType(reopen.__code__, dict(reopen.__globals__, _validate=scope['_validate']),
                            reopen.__name__, reopen.__defaults__, reopen.__closure__)
    budgeted.__kwdefaults__ = reopen.__kwdefaults__
    return SimpleNamespace(Path=kernel.Path, reopen_geometry=budgeted)


def context():
    ctx, full, cd, checks = stage3.context()
    return ctx, {'A1': budget_kernel(cd), 'A2': budget_kernel(full)}, checks


def new_edits(result, true_delays):
    edits = []
    for step in result.global_trace:
        edit = step['accepted']
        if edit is None:
            continue
        entered = {path['delay'] for i, path in enumerate(step['entering_paths'])
                   if i != edit['slot']}
        incoming = edit['new']['delay']
        if incoming in entered:
            label = 'phantom'
        elif incoming in true_delays and incoming != edit['old']['delay']:
            label = 'true_delay'
        else:
            label = 'other'
        edits.append(dict(step=step['step'] + 1, slot=edit['slot'], old=edit['old'],
                          new=edit['new'], label=label))
    return edits


def edit_budget_mechanism(result, budget, entering_delays, true_delays):
    if result is None:
        return dict(cap_exhausted=False, attempted_3_4=0, accepted_3_4=0,
                    attempted_5_6=0, accepted_5_6=0, net_true_delay_gain=0)
    steps = result.global_trace
    final_delays = {path.delay for path in result.paths}
    return dict(
        cap_exhausted=len(result.edits) == budget,
        attempted_3_4=len(steps[2:4]),
        accepted_3_4=sum(step['accepted'] is not None for step in steps[2:4]),
        attempted_5_6=len(steps[4:6]),
        accepted_5_6=sum(step['accepted'] is not None for step in steps[4:6]),
        net_true_delay_gain=len(true_delays & final_delays) - len(true_delays & entering_delays),
    )


def decoder_transitions(arms):
    state = {name: 'success' if row['errors'] == 0 else 'fail' for name, row in arms.items()}
    return {f'{left}->{right}': f'{state[left]}_{state[right]}'
            for left, right in combinations(arms, 2)}


def run_at_budget(ctx, kernel, obs, arrays, covariance_arm, budget, *, reopen=None):
    """Set the cap at the only point where the frozen continuation consumes it."""
    if reopen is None:
        reopen = kernel.reopen_geometry

    def with_budget(*args, **kwargs):
        return reopen(*args, **dict(kwargs, max_edits=budget))

    return stage3.e1.run_branch(
        ctx, SimpleNamespace(Path=kernel.Path, reopen_geometry=with_budget), obs, arrays, covariance_arm)


def run_key(ctx, kernels, base, key, *, gate_timing=None):
    """Share one F0 state. With a gate timing receipt, only decode budget-2 arms."""
    scenario, rho, snr, frame = key
    start = time.process_time()
    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
    f0 = dict(**stage3.decoded(ctx, dec, truth), first_edit_type=None, state=None, decision=[])
    entering = [[int(delay), float(doppler)] for delay, doppler in
                zip(arrays['r1_delays'], arrays['r1_dopplers'], strict=True)]
    true_delays = set(truth['l_i'].tolist())
    entering_delays = {delay for delay, _ in entering}
    missed = sorted(true_delays - entering_delays)
    arms = {'F0': f0}
    mechanism = {'F0': edit_budget_mechanism(None, 0, entering_delays, true_delays)}
    for name, (covariance_arm, budget) in ARMS.items():
        if gate_timing is not None and budget != 2:
            continue
        if not syndrome:
            arms[name] = f0
            mechanism[name] = mechanism['F0']
            continue

        kernel = kernels[covariance_arm]
        geometry_input = None

        def reopen(*args, **kwargs):
            nonlocal geometry_input
            begin = time.process_time()
            result = kernel.reopen_geometry(*args, **kwargs)
            geometry_input = args, kwargs, time.process_time() - begin
            return result

        begin = time.process_time()
        branch = run_at_budget(ctx, kernel, obs, arrays, covariance_arm, budget, reopen=reopen)
        branch_cpu = time.process_time() - begin
        result = branch['result']
        arms[name] = dict(**stage3.decoded(ctx, branch['decoder'], truth),
                          **cstate._geometry_record(result), accepted_edits=new_edits(result, true_delays))
        mechanism[name] = edit_budget_mechanism(result, budget, entering_delays, true_delays)
        if gate_timing is not None:
            args, kwargs, geometry_cpu = geometry_input
            larger_budgets = (4, 6) if covariance_arm == 'A1' else (6,)
            by_budget = {}
            for larger in larger_budgets:
                begin = time.process_time()
                extended = kernel.reopen_geometry(*args, **dict(kwargs, max_edits=larger))
                elapsed = time.process_time() - begin
                if cstate._decision(extended)[:len(result.global_trace)] != cstate._decision(result):
                    raise AssertionError(f'{key} {name}/{larger}: exchange prefix differs')
                if len(extended.edits) < len(result.edits) or len(extended.global_trace) > larger:
                    raise AssertionError(f'{key} {name}/{larger}: invalid edit budget or stopping')
                if (len(result.edits) < 2
                        and cstate._geometry_record(result) != cstate._geometry_record(extended)):
                    raise AssertionError(f'{key} {name}/{larger}: early-stop geometry changed')
                by_budget[larger] = dict(cpu_seconds=elapsed, edits=len(extended.edits),
                                         steps=len(extended.global_trace))
            gate_timing[name] = dict(geometry_cpu_seconds=geometry_cpu,
                                     non_geometry_cpu_seconds=branch_cpu - geometry_cpu,
                                     extended_geometry=by_budget)

    return dict(scenario=scenario, rho_permille=rho, snr_centi_db=snr, frame=frame,
                syndrome=syndrome, triggered=bool(syndrome), entering_paths=entering,
                missed_true_delays=missed, truth=stage3.truth_record(obs, truth),
                inputs=stage3.input_record(raw, obs), arms=arms,
                budget_mechanism=mechanism, decoder_transitions=decoder_transitions(arms),
                cpu_seconds=time.process_time() - start)
