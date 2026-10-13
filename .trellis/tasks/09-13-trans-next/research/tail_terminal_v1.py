"""Frozen observed-input terminal interventions; truth belongs to the scorer."""
from __future__ import annotations

import time

import numpy as np
import torch

import tail_completion_v2 as tail
from afdm_sp_joint_unrolled import direction_receiver
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    build_A_for_DALS_torch, reconstruct_H_torch)

ARMS = ('ORIGINAL', 'TAIL', 'RIDGE_T')
TERMINAL_FIELDS = ('mu', 'var', 'raw_llr', 'llr', 'decoded', 'info_hat',
                   'x_hard', 'decode_ok')
SCOPE = 'saved actual-terminal H intervention; exposed development; not full receiver or CONF/COST'


def _validate(H, y, pilot, x_soft, delays, dopplers, c1, c2, arm):
    H, y, pilot, x_soft, delays, dopplers = map(
        np.asarray, (H, y, pilot, x_soft, delays, dopplers))
    n = len(y) if y.ndim == 1 else 0
    if (arm not in ARMS or n < 16 or H.shape != (n, n) or not np.iscomplexobj(H)
            or pilot.shape != (n,) or x_soft.shape != (n,)
            or delays.dtype.kind not in 'iu' or dopplers.dtype.kind not in 'iu'
            or not np.isfinite([c1, c2]).all() or abs(2*n*c1-tail.STRIDE) > 1e-10
            or any(not np.isfinite(a).all() for a in (H, y, pilot, x_soft))):
        raise ValueError('invalid observed terminal inputs or frozen geometry')
    support, tail_atoms = tail.support_and_tail(delays, dopplers, n=n)
    return H, y, pilot, x_soft, support, tail_atoms


def _geometry(atoms):
    pairs = np.asarray(atoms, dtype=np.int64)
    return torch.as_tensor(pairs[:, 0]), torch.as_tensor(pairs[:, 1])


def _reconstruct(n, atoms, gains, c1, c2):
    delays, dopplers = _geometry(atoms)
    return reconstruct_H_torch(n, delays, dopplers,
        torch.as_tensor(np.asarray(gains, dtype=np.complex128)), c1, c2,
        tail.K_TAIL, torch.complex128).numpy()


def _ridge_tail(H, y, signal, atoms, previous_tail, c1, c2):
    n = len(y)
    delays, dopplers = _geometry(atoms)
    A = build_A_for_DALS_torch(n, delays, dopplers,
        torch.as_tensor(np.asarray(signal, dtype=np.complex128)), c1, c2,
        tail.K_TAIL, torch.complex128).numpy()
    lam = .1 * float(np.vdot(A, A).real) / len(atoms)
    if not np.isfinite(lam) or lam <= 0:
        raise ValueError('tail ridge requires a nonzero finite legal sensing signal')
    residual = y - H @ signal + A @ previous_tail
    lhs = A.conj().T @ A + lam*np.eye(len(atoms))
    rhs = A.conj().T @ residual
    gains = np.linalg.solve(lhs, rhs)
    normal = float(np.linalg.norm(lhs @ gains - rhs)
                   / max(1., np.linalg.norm(lhs)*np.linalg.norm(gains) + np.linalg.norm(rhs)))
    error = residual - A @ gains
    objective = float(np.vdot(error, error).real + lam*np.vdot(gains, gains).real)
    if not np.isfinite(gains).all() or not np.isfinite(objective) or normal > 2e-10:
        raise FloatingPointError('tail ridge normal equation or objective invalid')
    return gains, dict(lambda_value=lam, objective=objective,
                       normal_relative_residual=normal, design_shape=list(A.shape))


def make_candidate(*, H, y, pilot, x_soft, delays, dopplers, c1, c2, arm,
                   predictor_cache=None):
    """Keep actual H outside T and replace T by one frozen observed estimate.

    In particular this never reconstructs the baseline from the saved,
    undamped CE solution. ORIGINAL retains its input dtype and exact operation.
    """
    started = time.perf_counter()
    H, y, pilot, x_soft, support, atoms = _validate(
        H, y, pilot, x_soft, delays, dopplers, c1, c2, arm)
    n = len(y)
    counts = dict(Frobenius_atom_projections=0, F_matrix_solves=0, F_cache_hits=0,
                  tail_refit_solves=0, tail_design_builds=0, H_reconstructions=0,
                  diagnostic_Frobenius_projections=0)
    times = dict(projection=0., prediction_or_refit=0., reconstruction=0., cancellation=0.)
    core = previous_tail = target = np.zeros(0, dtype=np.complex128)
    centres = np.empty((0, 2), dtype=np.int64)
    ridge = None
    invariants = dict(core_projection_absolute_error=0., tail_projection_absolute_error=0.)
    if arm == 'ORIGINAL':
        result_H = H.copy()
    else:
        begin = time.perf_counter()
        original = np.asarray(H, dtype=np.complex128)
        projected = tail.direct_projection(original, n, c1, c2, support + atoms)
        core, previous_tail = projected[:len(support)], projected[len(support):]
        counts['Frobenius_atom_projections'] = len(projected)
        times['projection'] = time.perf_counter() - begin

        begin = time.perf_counter()
        if arm == 'TAIL':
            actual = tail.actual_centres(support, core)
            centres = np.asarray(sorted(actual.items()), dtype=np.int64)
            cache = {} if predictor_cache is None else predictor_cache
            target = tail.completed_tail(support, atoms, core, actual, n=n,
                                         cache=cache, calls=counts)
        else:
            target, ridge = _ridge_tail(original, y, pilot+x_soft, atoms,
                                       previous_tail, c1, c2)
            counts['tail_refit_solves'] = 1
            counts['tail_design_builds'] = 1
        times['prediction_or_refit'] = time.perf_counter() - begin

        begin = time.perf_counter()
        result_H = original + _reconstruct(n, atoms, target-previous_tail, c1, c2)
        counts['H_reconstructions'] = 1
        times['reconstruction'] = time.perf_counter() - begin
        after = tail.direct_projection(result_H, n, c1, c2, support+atoms)
        counts['diagnostic_Frobenius_projections'] = len(after)
        np.testing.assert_allclose(after[:len(support)], core, atol=2e-12, rtol=2e-10)
        np.testing.assert_allclose(after[len(support):], target, atol=2e-12, rtol=2e-10)
        invariants = dict(core_projection_absolute_error=float(np.linalg.norm(after[:len(support)]-core)),
                          tail_projection_absolute_error=float(np.linalg.norm(after[len(support):]-target)))

    begin = time.perf_counter()
    z = y - result_H @ pilot
    times['cancellation'] = time.perf_counter() - begin
    if not np.isfinite(result_H).all() or not np.isfinite(z).all():
        raise FloatingPointError('nonfinite completed terminal channel or cancellation')
    return dict(arm=arm, H=result_H, z=z, support=np.asarray(support, dtype=np.int64),
                tail_atoms=np.asarray(atoms, dtype=np.int64), core_gains=core,
                tail_before=previous_tail, tail_gains=target, centres=centres, ridge=ridge,
                counts=counts, component_seconds=times,
                preprocessing_seconds=float(sum(times.values())),
                instrumented_transform_seconds=time.perf_counter()-started,
                invariants=invariants)


def check_terminal(value, candidate, sigma2, prior):
    """Check the actual consumer graph and likelihood, without truth inputs."""
    H = np.asarray(candidate['H'], dtype=np.complex128)
    if len(value['graphs']) != 1:
        raise ValueError('expected one actual terminal BP graph')
    graph = value['graphs'][0]
    if (graph['stage'] != 'final_bp' or graph['threshold'] != 1e-4 or graph['operator'] != '>='
            or graph['dtype'] != 'torch.complex128' or graph['H_hash'] != array_hash(H)
            or graph['edges'] != int(np.count_nonzero(abs(H) >= 1e-4))
            or value['actual_edges'] != graph['edges'] or value['sigma2_terminal'] != float(sigma2)):
        raise ValueError('terminal consumer graph or physical variance differs')
    np.testing.assert_array_equal(value['H'], candidate['H'])
    np.testing.assert_array_equal(value['z'], candidate['z'])
    np.testing.assert_array_equal(value['finite_message']['prior_llr'], prior)
    np.testing.assert_array_equal(value['llr'], np.clip(value['raw_llr'], -20., 20.))
    if value['resource_counts'] != dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0):
        raise ValueError('unexpected terminal resource count')


def check_profile(operators):
    """The experiment runner owns profiling; the numeric primitive does not."""
    if (sorted(row['operator'] for row in operators) != ['LDPC', 'terminal_BP']
            or any(row['status'] != 'complete' for row in operators)):
        raise ValueError('incomplete or extra terminal operators')


def decode_candidate(candidate, sigma2, constellation, prior, code):
    """Use the existing BP/channel-LLR/LDPC implementation, with frozen controls."""
    counts = []
    value = direction_receiver.terminal_decode(candidate['z'], candidate['H'], sigma2,
        constellation, code, audit=True, code_prior=prior, bp_temperature=1.,
        bp_iterations=20, edge_count_observer=counts.append)
    if len(counts) != 1:
        raise ValueError('actual terminal edge count missing')
    value.update(candidate)
    value.update(actual_edges=counts[0], sigma2_terminal=float(sigma2),
                 last_check_prior=np.array(prior, copy=True),
                 resource_counts=dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0),
                 scope=SCOPE, baseline_eligible=False)
    check_terminal(value, candidate, sigma2, prior)
    return value
